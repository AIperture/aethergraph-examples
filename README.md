# AetherGraph Examples

Welcome to the **AetherGraph (AG) Examples** repo. This is the companion repository for runnable demos and pattern snippets.

For a narrative overview of everything here, read the **Examples of AetherGraph Usage** guide:


> This catalog **evolves over time**. We add new demos, refine existing ones, and occasionally adjust paths as the repo grows.

---

## Requirements

* Python **3.10+**
* macOS, Linux, or Windows
* *(Optional)* LLM API keys (OpenAI, Anthropic, Google, etc.)
* *(Optional extras)* Slack adapter for Slack-based interaction

We strongly recommend using a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip
```

---

## Install AetherGraph

```bash
pip install aethergraph

# Optional extras
pip install "aethergraph[slack]"   # Slack adapter
pip install "aethergraph[dev]"     # Dev tooling (linting, tests, types)
```


---

## Configure `.env` (optional)

Most examples run without an LLM, but many demos become more interesting with one. Set credentials via environment variables or a local `.env` file **in the root of this examples repo** (the directory you run commands from).

**Minimal `.env` example (OpenAI):**

```dotenv
# .env (example)
AETHERGRAPH_LLM__ENABLED=true
AETHERGRAPH_LLM__DEFAULT__PROVIDER=openai
AETHERGRAPH_LLM__DEFAULT__MODEL=gpt-4o-mini
AETHERGRAPH_LLM__DEFAULT__API_KEY=sk-...your-key...
```

You can override the location with `AETHERGRAPH_ENV_FILE=/path/to/.env`.

**Inline setup (on‑demand keys)**

```python
from aethergraph.runtime import register_llm_client

open_ai_client = register_llm_client(
    profile="my_llm",
    provider="openai",
    model="gpt-4o-mini",
    api_key="sk-...your-key...",
)
```

> Channel adapters (Slack/Telegram/Web) are optional; all demos default to the **console channel**. See the main AG docs for adapter setup.

---

## Repo layout (selected)

```
demo_examples/
method_showcase/
pattern_examples/
```

---

## Quick start — run a demo

1. Install AG (PyPI or source) and activate your virtualenv.
2. *(Optional)* Create a `.env` with your LLM key(s) in the examples repo root. (see `.env.example`)
3. Run any script directly with `python`.

```bash
# Chat agent that remembers and summarizes
python demo_examples/1_chat_with_memory.py

# One-function interactive setup wizard
python demo_examples/2_channel_wizard_interactive_workflow.py

# Tiny gradient-descent with metrics & checkpoints
python demo_examples/3_optimization_loop_with_artifacts.py
```

---

## Hero Demos

Short, polished demos that tell a clear story. Each fits in a single file and returns observable outputs (messages, artifacts, or both).

|  # | Demo                                 | What you’ll see (story)                                                                                                                     | Path                                                     |
| -: | ------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------- |
|  1 | **Chat Agent with Memory**           | Seeds or loads chat memory → you chat → it summarizes the whole session and saves transcript + summary as artifacts.                        | `demo_examples/1_chat_with_memory.py`                    |
|  2 | **Channel Wizard**                   | A one‑function wizard that collects config using `ask_*`, shows a recap, lets you Confirm/Restart/Cancel, then saves `run_config.json`.     | `demo_examples/2_channel_wizard_interactive_workflow.py` |
|  3 | **Optimization Loop**                | A tiny gradient‑descent run that logs step metrics to Memory, writes periodic checkpoints as artifacts, and returns final params.           | `demo_examples/3_optimization_loop_with_artifacts.py`    |
|  4 | **Extend Prompt Services**           | Agents use `context.prompt_store()` to fetch prompts and `context.llm_observer()` to log calls—clean agent code, centralized control.       | `demo_examples/4_external_service_prompt_store.py`       |
|  5 | **Simple Copilot (Tool Router)**     | A console copilot routes each query to a calculator, a summarizer, or a direct answer using a tiny LLM classifier; replies inline.          | `demo_examples/5_simple_copilot_tool_using_router.py`    |
|  6 | **Resume a Static Graph (graphify)** | A static graph with a slow, checkpointed node crashes mid‑run; re‑running with the same `run_id` resumes from the checkpoint and completes. | `demo_examples/6_crash_resume_static_graph.py`           |

---

## Method Showcase — Patterns by Feature

Concise examples organized by capability. Use these as copy‑paste starting points.

### A) Interaction (Channel)

* **A.1 `send_text`** — Minimal "hello" send.
  *Path:* `method_showcase/1_channels/1_channel_send_text.py`
* **A.2 `ask_text`** — Prompt → await user reply → echo.
  *Path:* `method_showcase/1_channels/2_channel_ask_text.py`
* **A.3 `ask_approval`** — Present options, branch on choice.
  *Path:* `method_showcase/1_channels/3_channel_ask_approval.py`
* **A.4 Channel setup** — Configure Slack / Telegram / Webhook adapters and key conventions.
  *Path:* `method_showcase/1_channels/4_channel_setup.py`
* **A.5 Method walk‑through** — Linear tour of all channel methods using a small “portfolio” demo.
  *Path:* `method_showcase/1_channels/5_channel_method_walkthrough.py`
* **A.6 File channel** — Ask for files, read them, return attachments/links.
  *Path:* `method_showcase/1_channels/6_file_channel_example.py`

### B) Memory & Artifacts

* **B.1 Memory — record & query** — Append events and fetch recent history.
  *Path:* `method_showcase/2_artifacts_memory/1_memory_record.py`
* **B.2 Memory — typed results** — Store structured tool results for fast retrieval.
  *Path:* `method_showcase/2_artifacts_memory/2_memory_write_result.py`
* **B.3 Artifacts — save text/JSON** — Persist text/JSON and auto‑index.
  *Path:* `method_showcase/2_artifacts_memory/3_artifacts_save_txt_json.py`
* **B.4 Artifacts — save & search files** — Save arbitrary files and rank/search across agents.
  *Path:* `method_showcase/2_artifacts_memory/4_artifacts_save_search_files.py`
* **B.5 Memory → RAG** — Promote memory events into a vector index and answer with citations.
  *Path:* `method_showcase/2_artifacts_memory/5_memory_rag.py`

### C) Logger & KV

* **C.1 Logger** — Structured logs, levels, and tracing.
  *Path:* `method_showcase/3_logger_kv/1_logger_usage.py`
* **C.2 KV** — Store and fetch run‑level globals.
  *Path:* `method_showcase/3_logger_kv/2_kv_usage.py`

### D) LLM

* **D.1 Chat** — One‑shot and multi‑turn `context.llm().chat(...)`.
  *Path:* `method_showcase/4_llm/1_llm_chat.py`
* **D.2 Multiple profiles** — Configure and use multiple LLM clients.
  *Path:* `method_showcase/4_llm/2_setup_multiple_llm_profiles.py`
* **D.3 Inline profile** — Set keys/models at runtime (no preregistration).
  *Path:* `method_showcase/4_llm/3_inline_llm_setup.py`
* **D.4 Raw API** — Use `.raw()` to pass advanced payloads directly.
  *Path:* `method_showcase/4_llm/4_passing_raw_api.py`

### E) RAG

* **E.1 Ingest files** — Upsert docs into a vector index.
  *Path:* `method_showcase/5_rag/ingest_files.py`
* **E.2 Inspect corpora** — List/inspect existing corpora.
  *Path:* `method_showcase/5_rag/list_inspect_corpora.py`
* **E.3 Search & answer** — Retrieve → synthesize with citations.
  *Path:* `method_showcase/5_rag/search_retrieve_answer.py`

### F) Extending Services

* **F.1 Materials DB** — Register a materials property service for quick lookups.
  *Path:* `method_showcase/6_extending_services/1_material_db.py`
* **F.2 HuggingFace model** — Expose an external model as a service.
  *Path:* `method_showcase/6_extending_services/2_huggingface_model.py`
* **F.3 Rate limiting** — Token‑bucket wrapper with retries/backoff.
  *Path:* `method_showcase/6_extending_services/3_rate_limit.py`
* **F.4 Access NodeContext in a service** — Patterns for using `context` safely inside services.
  *Path:* `method_showcase/6_extending_services/4_access_ctx_in_service.py`
* **F.5 Critical sections / mutex** — Design a thread‑safe service API.
  *Path:* `method_showcase/6_extending_services/5_critical_mutex_usage.py`

### G) Concurrency

* **G.1 `graphify` map‑reduce** — Fan‑out + fan‑in with static graphs.
  *Path:* `method_showcase/7_concurrency/graphify_map_reduce.py`
* **G.2 `graph_fn` concurrency** — Launch concurrent tasks with a concurrency cap.
  *Path:* `method_showcase/7_concurrency/graph_fn_concurrency.py`

---

## Concrete Example Patterns — Advanced Recipes

Bigger compositions that mirror real‑world tasks.

### A) State & Resumption

* **A.1 Crash & Resume (static graph)** — Design a static graph so a long node can checkpoint and resume indefinitely using the same `run_id`.
  *Path:* `pattern_examples/1_state_resumption/1_resume_external_waits.py`
* **A.2 Long Job Monitor** — Submit to `job_manager`, poll with backoff, surface failures via channel, let the user Retry/Abort.
  *Path:* `pattern_examples/1_state_resumption/2_long_job_monitor.py`

### B) Agent Patterns

* **B.1 Chain‑of‑Thought Agent** — Two‑stage flow: CoT reasoning trace → final concise answer (optionally store traces).
  *Path:* `pattern_examples/2_agent_patterns/1_chain_of_thought.py`
* **B.2 ReAct Agent** — Thought → Action (tool) → Observation loop until “Finish”, with a compact history state.
  *Path:* `pattern_examples/2_agent_patterns/2_simple_react.py`
* **B.3 RL Policy as `graph_fn`** — Treat a graph as a policy: observation in, action out; log trajectories via Memory/Artifacts.
  *Path:* `pattern_examples/2_agent_patterns/3_reinforcement_learning_policy.py`

### C) Applied End‑to‑End

* **C.1 CSV Analyzer** *(interactive)* — Ask for a CSV, summarize shape (rows/cols), headers, and simple stats; return findings and artifacts.
  *Path:* `pattern_examples/3_e2e_patterns/1_csv_analyzer.py`
* **C.2 Paper → Implementation Sketch** *(interactive)* — Ask for a text/PDF, sketch a Python implementation, run sandboxed, return logs/files as artifacts.
  *Path:* `pattern_examples/3_e2e_patterns/2_paper_implementation_sketch.py`
* **C.3 Deep Research Agent** — Use `graphify` concurrency to parallelize retrieval/summarization and synthesize findings.
  *Path:* `pattern_examples/3_e2e_patterns/3_deep_research_agent.py`

---

## Troubleshooting

* **No output or hangs?** Ensure your virtualenv is active and that no proxy/firewall blocks network calls.
* **LLM errors?** Double‑check `.env` keys, model names, and rate limits. Try a smaller test like `method_showcase/4_llm/1_llm_chat.py`.
* **Windows path issues?** Use `py` to run scripts (e.g., `py demo_examples/1_chat_with_memory.py`).
* **Slack adapter:** Verify the extra is installed (`pip install "aethergraph[slack]"`) and Slack credentials are configured per the AG docs.

---

## Contributing & Updates

This repo evolves with the framework. PRs and suggestions are welcome!

* Main framework repo: [https://github.com/AIperture/aethergraph](https://github.com/AIperture/aethergraph)
* Examples repo: [https://github.com/AIperture/aethergraph-examples](https://github.com/AIperture/aethergraph-examples)
* Index guide: see the main docs’ **Examples** page (TBD)
