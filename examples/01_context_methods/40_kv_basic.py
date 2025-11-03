# kv_basic.py
from __future__ import annotations
import time
from aethergraph import graph_fn, NodeContext, run
from aethergraph.server import start

# Start sidecar so logger/contexts are wired
url = start()
print("AetherGraph sidecar server started at:", url)

KV_KEY = "demo:greeting"

@graph_fn(name="kv.writer_basic", version="0.1.0")
async def kv_writer_basic(*, context: NodeContext):
    """
    Agent A: write a small value into EphemeralKV with a short TTL.
    """
    log = context.logger()
    kv  = context.kv()
    value = "hello from writer"
    await kv.set(KV_KEY, value)

    log.info(f"[writer] set {KV_KEY!r}='{value}'")
    return {"set": True, "key": KV_KEY, "session_id": getattr(context, "session_id", None)}

@graph_fn(name="kv.reader_basic", version="0.1.0")
async def kv_reader_basic(*, context: NodeContext):
    """
    Agent B: read the value; returns default if missing/expired.
    """
    log = context.logger()
    kv  = context.kv()

    got = await kv.get(KV_KEY, default="<missing>")
    log.info(f"[reader] get {KV_KEY!r} -> {got!r}")
    return {"key": KV_KEY, "value": got, "session_id": getattr(context, "session_id", None)}

if __name__ == "__main__":
    # --- 1) Writer puts a value with TTL ---
    r1 = run(kv_writer_basic, inputs={})
    print("Writer result:", r1)

    # --- 2) Reader sees the value (same process/session) ---
    r2 = run(kv_reader_basic, inputs={})
    print("Reader (before TTL) result:", r2)
