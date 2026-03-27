# ADK Evaluation Guide — Data Science Agent

## Files Created

| File | Purpose |
|------|---------|
| [data_science_demo.test.json](file:///Users/justin/Dropbox/projects/github.com/justinjm/adk-samples/python/agents/data-science/eval/eval_data/data_science_demo.test.json) | Eval dataset — 6 demo questions (fill in `final_response` values) |
| [test_eval_demo.py](file:///Users/justin/Dropbox/projects/github.com/justinjm/adk-samples/python/agents/data-science/eval/test_eval_demo.py) | pytest test file — one test per question + an all-questions test |
| [test_config.json](file:///Users/justin/Dropbox/projects/github.com/justinjm/adk-samples/python/agents/data-science/eval/eval_data/test_config.json) | Evaluation criteria thresholds (already exists) |

---

## Step 1 — Fill In Expected Answers

Open [data_science_demo.test.json](file:///Users/justin/Dropbox/projects/github.com/justinjm/adk-samples/python/agents/data-science/eval/eval_data/data_science_demo.test.json) and replace every `"TODO: Fill in..."` value with the actual response you expect from the agent.

> [!IMPORTANT]
> The `final_response.parts[0].text` field is the **reference answer** used to score the agent. The more precise it is, the more meaningful the evaluation.

You may also want to refine the `tool_uses` entries — the `name` field should match the actual tool the agent calls (e.g. `call_db_agent`, `call_ds_agent`). The `args` are loosely matched, so they don't need to be exact.

### Example — Q1 (filled in)
```json
"final_response": {
  "parts": [
    {
      "text": "I have access to two BigQuery tables: `train` and `test`. Both contain sticker sales data with columns: date, country, store, product, and num_sold."
    }
  ],
  "role": "model"
}
```

---

## Step 2 — Review Evaluation Criteria

[test_config.json](file:///Users/justin/Dropbox/projects/github.com/justinjm/adk-samples/python/agents/data-science/eval/eval_data/test_config.json) currently sets:

```json
{
  "criteria": {
    "tool_trajectory_avg_score": 1.0,
    "response_match_score": 0.1
  }
}
```

| Criteria | What it checks | Notes |
|----------|---------------|-------|
| `tool_trajectory_avg_score` | Exact match of tool call sequence | Set to `0.5` if tool order can vary |
| `response_match_score` | ROUGE-1 text similarity to reference | `0.1` is very lenient; raise to `0.5`+ after refining references |
| `final_response_match_v2` | LLM-judged semantic match | Better than ROUGE for qualitative answers |

> [!TIP]
> For the visualization and BQML questions (Q3, Q5, Q6), consider lowering `response_match_score` further or switching to `final_response_match_v2` since responses will vary and may include dynamic content like plot URLs.

---

## Step 3 — Run Evaluation

### Option A: pytest (recommended for CI/dev iteration)

```bash
cd /Users/justin/Dropbox/projects/github.com/justinjm/adk-samples/python/agents/data-science

# Run all 6 demo questions
pytest eval/test_eval_demo.py -v

# Run a single question (e.g. Q2)
pytest eval/test_eval_demo.py::test_eval_demo_train_table_details -v

# Run with increased output
pytest eval/test_eval_demo.py -v -s
```

### Option B: adk eval CLI

```bash
cd /Users/justin/Dropbox/projects/github.com/justinjm/adk-samples/python/agents/data-science

# Run all evals in the dataset
adk eval \
  data_science \
  eval/eval_data/data_science_demo.test.json \
  --config_file_path=eval/eval_data/test_config.json \
  --print_detailed_results

# Run only specific eval IDs
adk eval \
  data_science \
  "eval/eval_data/data_science_demo.test.json:q1_what_data_do_you_have,q4_bqml_forecasting_models" \
  --config_file_path=eval/eval_data/test_config.json \
  --print_detailed_results
```

### Option C: adk web UI (interactive)

1. Start the server (already running): `adk web` in the project directory
2. Open the browser → select the `data_science` agent
3. Go to the **Eval** tab on the right
4. Click **"Add current session"** after each demo conversation to capture golden answers automatically
5. Click **Run Evaluation** → configure metric thresholds → **Start**

> [!NOTE]
> The web UI is the easiest way to **capture** golden answers — run each demo question interactively, then save the session as an eval case. This auto-fills the `final_response` and `tool_uses` fields for you, which you can then edit to refine.

---

## Step 4 — Interpreting Results

After a pytest run, each test either **passes** or **fails** with a score breakdown:

```
PASSED eval/test_eval_demo.py::test_eval_demo_data_access
  tool_trajectory_avg_score: 1.0  ✅
  response_match_score: 0.72      ✅

FAILED eval/test_eval_demo.py::test_eval_demo_train_arima
  response_match_score: 0.06 < 0.1  ❌
```

**Common failure reasons:**
- Reference answer is too specific (update it to be more general)
- Tool names in `tool_uses` don't match what the agent actually calls
- Agent behavior is non-deterministic — increase `num_runs` and lower thresholds

---

## Schema Reference

The dataset uses the **new Pydantic-backed EvalSet schema** (required for `adk eval` CLI):

```
eval_set_id          → unique ID for the whole eval set
eval_cases[]
  eval_id            → unique ID per question (used with eval_ids= or CLI :filter)
  conversation[]
    invocation_id    → unique string ID per turn
    user_content     → the user's question
    final_response   → ⭐ YOUR EXPECTED ANSWER (fill this in)
    intermediate_data
      tool_uses[]    → expected tool calls (name + args)
      intermediate_responses[]  → sub-agent responses (optional)
  session_input      → app_name, user_id, state
```

> [!WARNING]
> If you see a migration warning when running eval, the dataset format may not match the expected schema. Run:
> ```python
> AgentEvaluator.migrate_eval_data_to_new_schema("eval/eval_data/data_science_demo.test.json")
> ```
