"""KV is global across all graph nodes within the same session/process."""

from aethergraph import graph_fn, NodeContext
from aethergraph import start_server 


KV_KEY = "demo:greeting" 

@graph_fn(name="kv.writer_usage")
async def kv_writer_usage(*, context: NodeContext):
    """
    Write a value into EphemeralKV.
    """
    kv  = context.kv()
    value = "hello from writer_usage"
    await kv.set(KV_KEY, value)

    return {"set": True, "key": KV_KEY}


@graph_fn(name="kv.reader_usage")
async def kv_reader_usage(*, context: NodeContext):
    """
    Read the value from EphemeralKV; returns default if missing.
    """
    kv  = context.kv()

    got = await kv.get(KV_KEY, default="<missing>")
    return {"key": KV_KEY, "value": got}

if __name__ == "__main__":
    # Start sidecar so logger/contexts are wired
    url = start_server()
    print("AetherGraph sidecar server started at:", url)

    from aethergraph.runner import run

    # --- 1) Writer puts a value ---
    r1 = run(kv_writer_usage, inputs={})
    print("Writer result:", r1)

    # --- 2) Reader gets the value ---
    r2 = run(kv_reader_usage, inputs={})
    print("Reader result:", r2)