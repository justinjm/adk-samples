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

"""
Evaluation tests for the data-science agent using the demo question set.

Dataset: eval_data/data_science_demo.test.json
Config:  eval_data/test_config.json

To run:
    cd /Users/justin/Dropbox/projects/github.com/justinjm/adk-samples/python/agents/data-science
    pytest eval/test_eval_demo.py -v
"""

import os

import pytest
from dotenv import find_dotenv, load_dotenv
from google.adk.evaluation.agent_evaluator import AgentEvaluator

pytest_plugins = ("pytest_asyncio",)

EVAL_DATA_DIR = os.path.join(os.path.dirname(__file__), "eval_data")


@pytest.fixture(scope="session", autouse=True)
def load_env():
    load_dotenv(find_dotenv(".env"))


@pytest.mark.asyncio
async def test_eval_demo_all():
    """Run all 6 demo questions against the data-science agent."""
    await AgentEvaluator.evaluate(
        "data_science",
        os.path.join(EVAL_DATA_DIR, "data_science_demo.test.json"),
        num_runs=1,
    )


@pytest.mark.asyncio
async def test_eval_demo_data_access():
    """Q1: Does the agent correctly describe the data it can access?"""
    await AgentEvaluator.evaluate(
        "data_science",
        os.path.join(EVAL_DATA_DIR, "data_science_demo.test.json"),
        eval_ids=["q1_what_data_do_you_have"],
        num_runs=1,
    )


@pytest.mark.asyncio
async def test_eval_demo_train_table_details():
    """Q2: Does the agent query and return correct train-table metadata?"""
    await AgentEvaluator.evaluate(
        "data_science",
        os.path.join(EVAL_DATA_DIR, "data_science_demo.test.json"),
        eval_ids=["q2_train_table_details"],
        num_runs=1,
    )


@pytest.mark.asyncio
async def test_eval_demo_sales_plot():
    """Q3: Does the agent produce a sales-per-country visualization?"""
    await AgentEvaluator.evaluate(
        "data_science",
        os.path.join(EVAL_DATA_DIR, "data_science_demo.test.json"),
        eval_ids=["q3_plot_total_sales_per_country"],
        num_runs=1,
    )


@pytest.mark.asyncio
async def test_eval_demo_bqml_models():
    """Q4: Does the agent correctly list available BQML forecasting models?"""
    await AgentEvaluator.evaluate(
        "data_science",
        os.path.join(EVAL_DATA_DIR, "data_science_demo.test.json"),
        eval_ids=["q4_bqml_forecasting_models"],
        num_runs=1,
    )


@pytest.mark.asyncio
async def test_eval_demo_train_arima():
    """Q5: Does the agent successfully train an ARIMA_PLUS model?"""
    await AgentEvaluator.evaluate(
        "data_science",
        os.path.join(EVAL_DATA_DIR, "data_science_demo.test.json"),
        eval_ids=["q5_train_arima_plus_model"],
        num_runs=1,
    )


@pytest.mark.asyncio
async def test_eval_demo_forecast_plot():
    """Q6: Does the agent produce a 30-day forecast plot with prediction bounds?"""
    await AgentEvaluator.evaluate(
        "data_science",
        os.path.join(EVAL_DATA_DIR, "data_science_demo.test.json"),
        eval_ids=["q6_forecast_timeseries_plot"],
        num_runs=1,
    )
