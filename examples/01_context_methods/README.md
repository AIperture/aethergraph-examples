# AetherGraph Context: quick intro

**Context** is the tiny “service backpack” every `graph_fn` gets via `NodeContext`.
It gives you batteries‑included primitives—**logger, kv, llm, rag, mcp, artifacts, memory**—so you can write research flows in plain Python without wiring.

---

## Why use `context.*`?

* **Zero boilerplate:** call `context.llm().chat(...)`, `context.kv().set(...)`, etc.
* **Swappable backends:** same API; change providers (OpenAI/Azure/Anthropic/…); swap KV, RAG index, MCP transport.
* **Traceable by default:** plays nicely with Memory/Artifacts so runs are easy to debug and summarize.
* **Research‑friendly:** short, readable functions; add power when needed, not upfront.

---

## The essentials (one screen)

### Logger

```python
@graph_fn(name="log.basic")
async def log_basic(*, context: NodeContext):
    log = context.logger()
    log.info("start")
    log.warning("a demo warning")
    try: 1/0
    except Exception as e: log.error(f"handled: {e!r}")
    return {"ok": True}
```

### Channel (send & ask)

```python
@graph_fn(name="channel.basic")
async def channel_basic(*, context: NodeContext):
    # send a message to your configured channel (console/Slack/etc.)
    await context.channel().send_text("Hello from AetherGraph 👋")
    # ask for free‑form text
    ans = await context.channel().ask_text("What dataset should we analyze?")
    return {"reply": ans}
```

### Ask for Approval (yes/no style)

```python
@graph_fn(name="channel.approval")
async def channel_approval(*, context: NodeContext):
    ok = await context.channel().ask_approval("Publish report to #team?")
    return {"approved": bool(ok)}
```

### Artifacts (save + lightweight search)

```python
@graph_fn(name="artifacts.basic")
async def artifacts_basic(*, context: NodeContext):
    afs = context.artifacts()
    # save a small text blob (or use save_file for real files)
    uri = await afs.save_text("experiment log v1
loss=0.12
")
    # simple label/keyword search if your store supports it
    hits = await afs.search({"q": "loss"})
    return {"uri": getattr(uri, "uri", uri), "hits": hits[:3]}
```

### Ephemeral KV (process‑local)

```python
@graph_fn(name="kv.writer")
async def kv_writer(*, context: NodeContext):
    await context.kv().set("demo:greet", "hello", ttl_s=3)
    return {"wrote": True}

@graph_fn(name="kv.reader")
async def kv_reader(*, context: NodeContext):
    val = await context.kv().get("demo:greet", "<missing>")
    return {"value": val}
```

### Memory (record events + typed results)

```python
@graph_fn(name="memory.record")
async def memory_record(*, context: NodeContext):
    mem = context.memory()
    await mem.record(kind="note", data="starting pipeline", tags=["demo"])  # HotLog + durable
    return {"ok": True}

@graph_fn(name="memory.result_and_query")
async def memory_result_and_query(*, context: NodeContext):
    mem = context.memory()
    evt = await mem.write_result(
        topic="demo.pipeline",
        outputs=[{"name":"greeting","kind":"text","value":"hello"}]
    )
    last_greeting = await mem.last_by_name("greeting")
    last_outputs = await mem.last_outputs_by_topic("demo.pipeline")
    return {"event_id": evt.event_id, "last_greeting": last_greeting, "last_outputs": last_outputs}
```

### LLM (multi‑provider via `LLMService`)

```python
@graph_fn(name="llm.basic")
async def llm_basic(*, context: NodeContext):
    # Optionally set key inline (or use env like OPENAI_API_KEY):
    # context.llm_set_key(provider="openai", api_key="sk-...")
    client = context.llm()  # default profile
    msgs = [
      {"role":"system","content":"Be concise."},
      {"role":"user","content":"In one sentence, what is MTF50?"}
    ]
    text, _ = await client.chat(msgs, model="gpt-4o-mini", temperature=0.2)
    return {"answer": text}
```

### RAG (ingest → answer)

```python
@graph_fn(name="rag.basic")
async def rag_basic(*, context: NodeContext):
    rag = context.rag()
    corpus = "demo-corpus"
    await rag.upsert_docs(corpus, docs=[{"title":"MTF note","text":"MTF50 measures edge acuity..."}])
    qa = await rag.answer(corpus, "What is MTF50 used for?", k=4)
    return {"answer": qa["answer"], "citations": qa.get("resolved_citations", [])}
```

### MCP (Model Context Protocol) — local stdio teaser

```python
@graph_fn(name="mcp.local_list", inputs=["path"])
async def mcp_local_list(path:str, *, context: NodeContext):
    # Register once at startup:
    # mcp = MCPService(); mcp.register("local", StdioMCPClient([sys.executable,"-m","aethergraph.v3.plugins.mcp.fs_server"]))
    # current_services()._mcp_service = mcp
    tools = await context.mcp("local").list_tools()
    listing = await context.mcp("local").call("listDir", {"path": path})
    return {"tools": tools[:5], "list_dir": listing}
```

---

## Design principles

* **Small surface, big swap:** keep call sites tiny (`context.rag().answer(...)`), let backends vary (FAISS/SQLite/…; OpenAI/Azure/…; stdio/WS/HTTP MCP).
* **Local first, cloud when ready:** start with ephemeral KV + stdio MCP; later switch to Redis/S3/WS/HTTP without changing your `graph_fn`s.
* **Composable with Memory/Artifacts:** logs, results, and URIs flow into your run history for later distillation and RAG.

---

## Quick start tips

* Start the sidecar once at program entry to wire services:

  ```python
  from aethergraph.server import start
  start()
  ```
* Keys: set via env (e.g., `OPENAI_API_KEY`) or override inline with `context.llm_set_key(...)`.
* RAG corpora live under your configured `corpus_root`; ingest inline text or files.
* MCP: for the intro, use the bundled **local stdio server**; add WS/HTTP later if you need remote tools.

---

## What’s in the examples

Tiny runnable files you can skim & run:

* `log_basic.py` – minimal logger usage
* `kv_basic.py` – writer/reader with TTL
* `llm_basic.py` – one‑shot chat (optional inline key)
* `rag_basic.py` – ingest + answer with citations
* `mcp_local_basic.py` – local stdio MCP (list/read)

Each one is less than a page and mirrors the snippets above.

---

**Mental model:** *Write research logic as plain Python functions. Reach for `context.*` when you need services. Swap backends later without touching your task code.*
