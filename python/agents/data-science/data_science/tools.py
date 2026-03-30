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

"""Tools for the ADK Sampmles Data Science Agent."""

import logging

from google.adk.agents import Agent
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.adk.tools import ToolContext
from google.adk.tools._forwarding_artifact_service import ForwardingArtifactService
from google.adk.tools.agent_tool import AgentTool
from google.adk.utils.context_utils import Aclosing
from google.genai import types

from .sub_agents import alloydb_agent, analytics_agent, bigquery_agent

logger = logging.getLogger(__name__)


async def run_analytics_agent_with_artifacts(
    agent: Agent,
    request: str,
    tool_context: ToolContext,
) -> str:
    """Run the analytics agent and capture both text and image artifacts.

    This replaces AgentTool.run_async() for the analytics agent. The standard
    AgentTool only returns text parts (filtering out images). This function
    also captures inline image parts from code execution results and saves
    them as artifacts so they render in the UI.
    """
    content = types.Content(
        role="user",
        parts=[types.Part.from_text(text=request)],
    )

    invocation_context = tool_context._invocation_context
    app_name = invocation_context.app_name or agent.name

    runner = Runner(
        app_name=app_name,
        agent=agent,
        artifact_service=ForwardingArtifactService(tool_context),
        session_service=InMemorySessionService(),
        memory_service=InMemoryMemoryService(),
        credential_service=invocation_context.credential_service,
        plugins=invocation_context.plugin_manager.plugins,
    )

    state_dict = {
        k: v
        for k, v in tool_context.state.to_dict().items()
        if not k.startswith("_adk")
    }
    session = await runner.session_service.create_session(
        app_name=app_name,
        user_id=invocation_context.user_id,
        state=state_dict,
    )

    last_content = None
    image_counter = 0

    async with Aclosing(
        runner.run_async(
            user_id=session.user_id,
            session_id=session.id,
            new_message=content,
        )
    ) as agen:
        async for event in agen:
            # Forward state delta to parent session
            if event.actions.state_delta:
                tool_context.state.update(event.actions.state_delta)
            if event.content and event.content.parts:
                # Save any inline image parts as artifacts
                for part in event.content.parts:
                    if part.inline_data and part.inline_data.mime_type and \
                       part.inline_data.mime_type.startswith("image/"):
                        image_counter += 1
                        ext = part.inline_data.mime_type.split("/")[-1]
                        filename = f"plot_{image_counter}.{ext}"
                        await tool_context.save_artifact(
                            filename=filename,
                            artifact=part,
                        )
                        logger.info(
                            "Saved image artifact: %s (%s)",
                            filename,
                            part.inline_data.mime_type,
                        )
                if event.content:
                    last_content = event.content

    await runner.close()

    if last_content is None or last_content.parts is None:
        return ""

    merged_text = "\n".join(
        p.text for p in last_content.parts if p.text and not p.thought
    )
    return merged_text


async def call_bigquery_agent(
    question: str,
    tool_context: ToolContext,
):
    """Tool to call bigquery database (nl2sql) agent."""
    logger.debug("call_bigquery_agent: %s", question)

    agent_tool = AgentTool(agent=bigquery_agent)

    bigquery_agent_output = await agent_tool.run_async(
        args={"request": question}, tool_context=tool_context
    )
    tool_context.state["bigquery_agent_output"] = bigquery_agent_output
    return bigquery_agent_output


async def call_alloydb_agent(
    question: str,
    tool_context: ToolContext,
):
    """Tool to call alloydb database (nl2sql) agent."""
    logger.debug("call_alloydb_agent: %s", question)

    agent_tool = AgentTool(agent=alloydb_agent)

    alloydb_agent_output = await agent_tool.run_async(
        args={"request": question}, tool_context=tool_context
    )
    tool_context.state["alloydb_agent_output"] = alloydb_agent_output
    return alloydb_agent_output


async def call_analytics_agent(
    question: str,
    tool_context: ToolContext,
):
    """
    This tool can generate Python code to process and analyze a dataset.

    Some of the tasks it can do in Python include:
    * Creating graphics for data visualization;
    * Processing or filtering existing datasets;
    * Combining datasets to create a joined dataset for further analysis.

    The Python modules available to it are:
    * io
    * math
    * re
    * matplotlib.pyplot
    * numpy
    * pandas

    The tool DOES NOT have the ability to retrieve additional data from
    a database. Only the data already retrieved will be analyzed.

    Args:
        question (str): Natural language question or analytics request.
        tool_context (ToolContext): The tool context to use for generating the
            SQL query.

    Returns:
        Response from the analytics agent.

    """
    logger.debug("call_analytics_agent: %s", question)

    bigquery_data = ""
    alloydb_data = ""

    if "bigquery_query_result" in tool_context.state:
        bigquery_data = tool_context.state["bigquery_query_result"]
    if "alloydb_query_result" in tool_context.state:
        alloydb_data = tool_context.state["alloydb_query_result"]

    question_with_data = f"""
  Question to answer: {question}

  IMPORTANT: If you create any matplotlib plots, you MUST call plt.show()
  as the final step to ensure the plot is captured and visible to the user.

  Actual data to analyze this question is available in the following data
  tables:

  <BIGQUERY>
  {bigquery_data}
  </BIGQUERY>

  <ALLOYDB>
  {alloydb_data}
  </ALLOYDB>

  """

    analytics_agent_output = await run_analytics_agent_with_artifacts(
        agent=analytics_agent,
        request=question_with_data,
        tool_context=tool_context,
    )
    tool_context.state["analytics_agent_output"] = analytics_agent_output
    return analytics_agent_output
