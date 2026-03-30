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

"""Top level agent for data agent multi-agents.

-- it get data from database (e.g., BQ) using NL2SQL
-- then, it use NL2Py to do further data analysis as needed
"""

import base64
import json
import logging
import os
import re
from datetime import date

from google.adk.agents import LlmAgent
from google.adk.agents.callback_context import CallbackContext

# from google.adk.tools import load_artifacts
from google.genai import types
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
    OTLPSpanExporter,
)
from opentelemetry.sdk import trace as trace_sdk
from opentelemetry.sdk.trace.export import SimpleSpanProcessor

from .prompts import return_instructions_root
from .sub_agents import bqml_agent
from .sub_agents.alloydb.tools import (
    get_database_settings as get_alloydb_database_settings,
)
from .sub_agents.bigquery.tools import (
    get_database_settings as get_bq_database_settings,
)
from .tools import call_alloydb_agent, call_analytics_agent, call_bigquery_agent

# Configure Weave endpoint and authentication
_WANDB_BASE_URL = "https://trace.wandb.ai"
_WANDB_PROJECT_ID = os.getenv("WANDB_PROJECT_ID")
_OTEL_EXPORTER_OTLP_ENDPOINT = f"{_WANDB_BASE_URL}/otel/v1/traces"

# Set up authentication
_WANDB_API_KEY = os.getenv("WANDB_API_KEY")
_WANDB_AUTH = base64.b64encode(f"api:{_WANDB_API_KEY}".encode()).decode()

_OTEL_EXPORTER_OTLP_HEADERS = {
    "Authorization": f"Basic {_WANDB_AUTH}",
    "project_id": _WANDB_PROJECT_ID,
}

# Create the OTLP span exporter with endpoint and headers
exporter = OTLPSpanExporter(
    endpoint=_OTEL_EXPORTER_OTLP_ENDPOINT,
    headers=_OTEL_EXPORTER_OTLP_HEADERS,
)

# Create a tracer provider and add the exporter
_tracer_provider = trace_sdk.TracerProvider()
_tracer_provider.add_span_processor(SimpleSpanProcessor(exporter))

# Set the global tracer provider BEFORE importing/using ADK
trace.set_tracer_provider(_tracer_provider)

# Set up logging
# Note this level can be overridden by adk web on the command line;
# e.g. running `adk web --log_level DEBUG` or `adk web -v`
logging.basicConfig(level=logging.INFO)
_logger = logging.getLogger(__name__)

# Initialize module-level config variables
_dataset_config = {}
_database_settings = {}
_supported_dataset_types = ["bigquery", "alloydb"]
_required_dataset_config_params = ["name", "description"]


def load_dataset_config():
    """Load the dataset configurations for the agent from the config file"""

    dataset_config_file = os.getenv("DATASET_CONFIG_FILE", "")
    if not dataset_config_file:
        _logger.fatal("DATASET_CONFIG_FILE env var not set")

    # Resolve relative paths (e.g. "./foo.json") relative to this file's
    # directory so the config is found correctly regardless of CWD — both
    # when running locally from deployment/ and inside the deployed container.
    if not os.path.isabs(dataset_config_file):
        dataset_config_file = os.path.join(
            os.path.dirname(__file__), dataset_config_file
        )
        dataset_config_file = os.path.normpath(dataset_config_file)

    with open(dataset_config_file, encoding="utf-8") as f:
        dataset_config = json.load(f)

    if "datasets" not in dataset_config:
        _logger.fatal("No 'datasets' entry in dataset config")

    for dataset in dataset_config["datasets"]:
        if "type" not in dataset:
            _logger.fatal("Missing dataset type")
        if dataset["type"] not in _supported_dataset_types:
            _logger.fatal("Dataset type '%s' not supported", dataset["type"])

        for p in _required_dataset_config_params:
            if p not in dataset:
                _logger.fatal(
                    "Missing required param '%s' from %s dataset config",
                    p,
                    dataset["type"],
                )

    return dataset_config


def get_database_settings(db_type: str) -> dict:
    """Wrapper function to get database settings by type"""
    assert db_type in _supported_dataset_types
    if db_type == "bigquery":
        return get_bq_database_settings()
    else:
        return get_alloydb_database_settings()


def init_database_settings(dataset_config: dict) -> dict:
    """Initializes the database settings for the configured datasets"""
    db_settings = {}
    for dataset in dataset_config["datasets"]:
        db_settings[dataset["type"]] = get_database_settings(dataset["type"])
    return db_settings


def get_dataset_definitions_for_instructions() -> str:
    """Returns the dataset definitions instructions block"""

    dataset_definitions = """
<DATASETS>
"""
    for dataset in _dataset_config["datasets"]:
        dataset_type = dataset["type"]
        dataset_definitions += f"""
<{dataset_type.upper()}>
<DESCRIPTION>
{dataset["description"]}
</DESCRIPTION>
<SCHEMA>
--------- The schema of the relevant database with a few sample rows. --------
{_database_settings[dataset_type]["schema"]}
</SCHEMA>
</{dataset_type.upper()}>

"""
    dataset_definitions += """
</DATASETS>
"""

    if "cross_dataset_relations" in _dataset_config:
        dataset_definitions += f"""
<CROSS_DATASET_RELATIONS>
--------- The cross dataset relations between the configured datasets. ---------
{_dataset_config["cross_dataset_relations"]}
</CROSS_DATASET_RELATIONS>
"""

    return dataset_definitions


def load_database_settings_in_context(callback_context: CallbackContext):
    """Load database settings into the callback context on first use."""
    if "database_settings" not in callback_context.state:
        callback_context.state["database_settings"] = _database_settings


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

        # If the part was *only* the image reference (now a data URI), keep it.
        # If it was mixed text + reference, keep the whole thing.
        stripped = replaced.strip()
        if stripped:
            new_parts.append(types.Part.from_text(text=replaced))

    # Also append inline_data parts for UIs that render them natively
    # (e.g. adk web's generated-image-container).
    for img in pending_images:
        image_bytes = base64.b64decode(img["data_b64"])
        mime = img.get("mime_type", "image/png")
        new_parts.append(types.Part.from_bytes(data=image_bytes, mime_type=mime))

    _logger.info(
        "Injected %d image(s) into model response (data-URI + inline_data)",
        len(pending_images),
    )

    llm_response.content.parts = new_parts
    callback_context.state["_pending_images"] = []
    return llm_response


def get_root_agent() -> LlmAgent:
    tools = [call_analytics_agent]
    sub_agents = []
    for dataset in _dataset_config["datasets"]:
        if dataset["type"] == "bigquery":
            tools.append(call_bigquery_agent)
            sub_agents.append(bqml_agent)
        elif dataset["type"] == "alloydb":
            tools.append(call_alloydb_agent)

    agent = LlmAgent(
        model=os.getenv("ROOT_AGENT_MODEL", "gemini-2.5-flash"),
        name="data_science_root_agent",
        instruction=return_instructions_root()
        + get_dataset_definitions_for_instructions(),
        global_instruction=(
            f"""
            You are a Data Science and Data Analytics Multi Agent System.
            Todays date: {date.today()}
            """
        ),
        sub_agents=sub_agents,  # type: ignore
        tools=tools,  # type: ignore
        before_agent_callback=load_database_settings_in_context,
        after_model_callback=inject_images_after_model,
        generate_content_config=types.GenerateContentConfig(temperature=0.01),
    )

    return agent


# Initialize dataset configurations and database info before the agent starts
_dataset_config = load_dataset_config()
_database_settings = init_database_settings(_dataset_config)


# Fetch the root agent
root_agent = get_root_agent()
