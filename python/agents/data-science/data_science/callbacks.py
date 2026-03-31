# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Shared callbacks for the Data Science Agent."""

import base64
import logging
import re

from google.adk.agents.callback_context import CallbackContext
from google.genai import types

logger = logging.getLogger(__name__)

_IMAGE_REF_RE = re.compile(
    r"!\[([^\]]*)\]\s*\(\s*`?_IMAGE_REFERENCE_[^)\s]+`?\s*\)"
)


def inject_images_after_model(callback_context: CallbackContext, llm_response):
    """Replace ``_IMAGE_REFERENCE_*`` markdown with embedded data-URI images.

    The Gemini code-execution convention emits text like::

        ![caption](_IMAGE_REFERENCE_CODE_EXECUTION_IMAGE_1.PNG)

    ``adk web`` *sometimes* resolves these against ``artifact_delta``, but the
    resolution is fragile (breaks locally too) and does not exist at all in
    Agent Engine Playground or Gemini Enterprise.

    This callback makes the response self-contained by:

    1. Finding every ``![…](_IMAGE_REFERENCE_…)`` markdown reference.
    2. Replacing each reference with a ``data:`` URI built from the actual
       image bytes captured earlier by ``call_analytics_agent``.
    3. Appending ``inline_data`` parts as well (for UIs like ``adk web``
       that render those natively).
    """
    pending_images = callback_context.state.get("_pending_images", [])
    if not pending_images:
        return None

    # Only process text responses, not function-call responses.
    if not llm_response.content or not llm_response.content.parts:
        return None
    has_text = any(
        p.text
        for p in llm_response.content.parts
        if not getattr(p, "thought", False)
    )
    if not has_text:
        return None

    # Build a queue of data-URIs from the captured artifacts.
    image_data_uris = []
    for img in pending_images:
        mime = img.get("mime_type", "image/png")
        image_data_uris.append(f"data:{mime};base64,{img['data_b64']}")

    # Walk through parts, replacing _IMAGE_REFERENCE_ markdown with data URIs
    # and dropping any parts that consist *only* of an image reference.
    new_parts = []
    uri_idx = 0
    for part in llm_response.content.parts:
        if not part.text or "_IMAGE_REFERENCE_" not in part.text:
            new_parts.append(part)
            continue

        def _replace_ref(match):
            nonlocal uri_idx
            alt_text = match.group(1) or "image"
            if uri_idx < len(image_data_uris):
                uri = image_data_uris[uri_idx]
                uri_idx += 1
                return f"![{alt_text}]({uri})"
            return match.group(0)  # no image available, keep original

        replaced = _IMAGE_REF_RE.sub(_replace_ref, part.text)

        stripped = replaced.strip()
        if stripped:
            new_parts.append(types.Part.from_text(text=replaced))

    # Also append inline_data parts for UIs that render them natively
    # (e.g. adk web's generated-image-container).
    for img in pending_images:
        image_bytes = base64.b64decode(img["data_b64"])
        mime = img.get("mime_type", "image/png")
        new_parts.append(types.Part.from_bytes(data=image_bytes, mime_type=mime))

    logger.info(
        "Injected %d image(s) into model response (data-URI + inline_data)",
        len(pending_images),
    )

    llm_response.content.parts = new_parts
    callback_context.state["_pending_images"] = []
    return llm_response
