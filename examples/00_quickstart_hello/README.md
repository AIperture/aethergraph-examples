# Quickstart · Hello World + `graph_fn` & `NodeContext` intro

> Run an agent in under 90 seconds, understand what each line does, then jump straight to context methods.

---

## TL;DR — Run it

```bash
python examples/00_quickstart_hello/run.py
```

**Expected output**

* `AetherGraph sidecar server started at: http://127.0.0.1:...`
* Two channel messages (hello + LLM reply)
* Final print: `Result: {'final_output': 'HELLO WORLD'}`

---

## What this example shows

* **Start the sidecar**: `start()` — brings up default services (channel, LLM, memory, logging) so you don’t wire anything manually.
* **Turn a function into an agent**: `@graph_fn` — a normal async Python function becomes a first‑class agent step.
* **Use built‑in services via context**: `context.channel()`, `context.llm("default")`, `context.logger()` — consistent API across local/remote providers.
* **Return structured outputs**: return a `dict` so steps compose cleanly.
* **Run conveniently**: `run(my_fn, inputs={...})` — a helper that executes the step with a fresh context.

---

## Code anatomy (line‑by‑line mental model)

```python
from aethergraph import graph_fn, NodeContext, run
from aethergraph.server import start

url = start()               # 1) Boot the sidecar (default channel/LLM/memory/logger)
print("AetherGraph sidecar server started at:", url)

@graph_fn(name="hello_world") # 2) Decorate a normal async function → agent step
async def hello_world(input_text: str, *, context: NodeContext):
    context.logger().info("hello_world started")         # 3) Structured logs

    await context.channel().send_text(                   # 4) Channel = user I/O
        f"👋 Hello! You sent: {input_text}")

    llm_text, _usage = await context.llm("default").chat( # 5) LLM access by name
        messages=[
            {"role": "system", "content": "Be brief."},
            {"role": "user", "content": f"Say hi back to: {input_text}"},
        ]
    )
    await context.channel().send_text(f"LLM replied: {llm_text}")

    output = input_text.upper()                          # 6) Your own logic
    context.logger().info("hello_world finished")
    return {"final_output": output}                     # 7) Always return a dict

result = run(hello_world, inputs={"input_text": "hello world"}) # 8) One‑liner runner
print("Result:", result)
```

**Why it matters**

* You write ordinary Python; AetherGraph provides the **ambient runtime** (channel/LLM/memory/logging) through `NodeContext`.
* The return `dict` keeps composition explicit (great for fan‑in/fan‑out later).

---

## `graph_fn` in one minute

* **What it is**: a decorator that turns an async function into an **agent step**.
* **Signature**: your parameters are your inputs; you also receive `context: NodeContext`.
* **Contract**: return a `dict` of named outputs.
* **Why**: easy to test, chain, and visualize; no hidden globals.

> Think: *“a function with superpowers”* — it runs with a consistent service set wherever you execute it.

---

## `NodeContext` (essentials you’ll use immediately)

`NodeContext` is your **service hub**. In this example you used:

| Method              | What it gives you                        | Core calls (keep it small)                                             |
| ------------------- | ---------------------------------------- | ---------------------------------------------------------------------- |
| `context.channel()` | User I/O (console/Slack/GUI via sidecar) | `send_text(text)`, `ask_text(prompt)`, `ask_approval(prompt, options)` |
| `context.llm(name)` | An LLM client by name                    | `chat(messages) -> (text, usage)`                                      |
| `context.logger()`  | Structured logging                       | `info(msg)`, `warning(msg)`, `error(msg)`                              |
| `context.memory()`  | Lightweight recent records               | `record(kind, value)`, `recent(kinds=[...])`                           |

> You don’t need to configure providers here. The sidecar supplies sensible defaults; later you can swap in Slack/Telegram or your preferred LLM.

---

## Next: minimal **Context Methods** tour

Move on to short, runnable snippets that focus on one method at a time:

* `examples/02_context_methods_min/01_channel_send_text.py` — send a message
* `examples/02_context_methods_min/02_channel_ask_approval.py` — human‑in‑the‑loop
* `examples/02_context_methods_min/10_llm_chat.py` — single‑turn chat
* `examples/02_context_methods_min/20_artifacts_put_json.py` / `21_artifacts_get_json.py` — (if you enable artifacts)
* `examples/02_context_methods_min/30_kv_set_get.py` — ephemeral state
* `examples/02_context_methods_min/40_mem_lifecycle.py` — lifecycle breadcrumbs

Each file is ≤12 lines and runs offline with the in‑memory defaults.

---

## Troubleshooting

* **No sidecar URL printed?** Ensure `start()` is called before running your step.
* **LLM reply looks like an echo/stub?** That’s expected in dev; flip your sidecar to a real provider later.
* **Interactive prompts block CI?** Comment out `ask_text/ask_approval` in quickstart; keep them for the context tour.

---

## Why this layout scales

* New users succeed in minutes with zero credentials.
* The same code runs on console or Slack by swapping sidecar config — **no code changes**.
* The mental model (function → agent, `context.*` services, dict outputs) stays the same as you add graphifying, tools, and bigger demos.
