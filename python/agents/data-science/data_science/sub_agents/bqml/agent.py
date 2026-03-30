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

"""BigQuery ML Agent."""

import logging
import os
from typing import Any

from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.tools import BaseTool, ToolContext
from google.adk.tools.bigquery import BigQueryToolset
from google.adk.tools.bigquery.config import BigQueryToolConfig, WriteMode

from data_science.sub_agents.bigquery.agent import bigquery_agent
from data_science.sub_agents.bigquery.tools import (
    get_database_settings as get_bq_database_settings,
)
from data_science.sub_agents.analytics.agent import analytics_agent
from data_science.sub_agents.bqml.tools import check_bq_models, rag_response

from ...utils.utils import USER_AGENT
from .prompts import return_instructions_bqml

logger = logging.getLogger(__name__)

# BigQuery built-in tools in ADK
# https://google.github.io/adk-docs/tools/built-in-tools/#bigquery
ADK_BUILTIN_BQ_EXECUTE_SQL_TOOL = "execute_sql"


def setup_before_agent_call(callback_context: CallbackContext):
    """Setup the agent."""

    if "database_settings" in callback_context.state:
        return

    # setting up database settings in session.state
    db_settings = {
        "bigquery": get_bq_database_settings(),
    }
    callback_context.state["database_settings"] = db_settings

    schema = callback_context.state["database_settings"]["bigquery"]["schema"]

    callback_context._invocation_context.agent.instruction = (
        return_instructions_bqml()
        + f"""

   </BQML Reference for this query>

    <The BigQuery schema of the relevant data with a few sample rows>
    {schema}
    </The BigQuery schema of the relevant data with a few sample rows>
    """
    )


def store_results_in_context(
    tool: BaseTool,
    args: dict[str, Any],
    tool_context: ToolContext,
    tool_response: dict,
) -> dict | None:
    """Store execute_sql results in state for the analytics agent to use."""
    if tool.name == ADK_BUILTIN_BQ_EXECUTE_SQL_TOOL:
        if tool_response.get("status") == "SUCCESS" and tool_response.get("rows"):
            tool_context.state["bigquery_query_result"] = tool_response["rows"]
    return None


async def call_analytics_agent(
    question: str,
    tool_context: ToolContext,
):
    """Tool to call the analytics agent for data visualization and analysis.

    Use this tool when the user asks to visualize, plot, chart, or graph
    data such as BQML forecast results. Pass the data and a description
    of the desired visualization.
    """

    bigquery_data = ""
    if "bigquery_query_result" in tool_context.state:
        bigquery_data = tool_context.state["bigquery_query_result"]

    question_with_data = f"""
  Question to answer: {question}

  IMPORTANT: If you create any matplotlib plots, you MUST call plt.show()
  as the final step to ensure the plot is captured and visible to the user.

  Actual data to analyze this question is available in the following data
  tables:

  <BIGQUERY>
  {bigquery_data}
  </BIGQUERY>
  """

    from data_science.tools import run_analytics_agent_with_artifacts

    result = await run_analytics_agent_with_artifacts(
        agent=analytics_agent,
        request=question_with_data,
        tool_context=tool_context,
    )
    tool_context.state["analytics_agent_output"] = result
    return result


async def call_db_agent(
    question: str,
    tool_context: ToolContext,
):
    """Tool to call database (nl2sql) agent."""
    from google.adk.tools.agent_tool import AgentTool

    agent_tool = AgentTool(agent=bigquery_agent)
    db_agent_output = await agent_tool.run_async(
        args={"request": question}, tool_context=tool_context
    )
    tool_context.state["db_agent_output"] = db_agent_output
    return db_agent_output


bigquery_tool_filter = [ADK_BUILTIN_BQ_EXECUTE_SQL_TOOL]
bigquery_tool_config = BigQueryToolConfig(
    write_mode=WriteMode.ALLOWED,  # to execute CREATE MODEL statement
    max_query_result_rows=80,
    application_name=USER_AGENT,
)
bq_execute_sql = BigQueryToolset(
    tool_filter=bigquery_tool_filter, bigquery_tool_config=bigquery_tool_config
)

root_agent = Agent(
    model=os.getenv("BQML_AGENT_MODEL"),
    name="bq_ml_agent",
    instruction=return_instructions_bqml(),
    before_agent_callback=setup_before_agent_call,
    after_tool_callback=store_results_in_context,
    tools=[
        bq_execute_sql,
        check_bq_models,
        call_db_agent,
        rag_response,
        call_analytics_agent,
    ],
)
