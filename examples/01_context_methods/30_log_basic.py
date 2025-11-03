from __future__ import annotations
from aethergraph import graph_fn, NodeContext, run
from aethergraph.server import start

# Start sidecar so logger is wired
url = start()
print("AetherGraph sidecar server started at:", url)

@graph_fn(name="log_basic")
async def log_basic(*, context: NodeContext):
    """
    Minimal demo of context.logger():
      - info / warning / error levels
      - return a small dict for easy testing
    """
    log = context.logger()

    log.info("log_basic: start")
    log.info("Working on a tiny task…")

    # Example warning
    log.warning("This is a demo warning (nothing to worry about).")

    # Example error capture without crashing the step
    try:
        _ = 1 / 0  # deliberate error for demonstration
    except Exception as e:
        log.error(f"Caught an error gracefully: {e!r}")

    log.info("log_basic: end")
    return {"ok": True, "notes": "Logged info, warning, and an error example."}

if __name__ == "__main__":
    result = run(log_basic, inputs={})
    print("Result:", result)
