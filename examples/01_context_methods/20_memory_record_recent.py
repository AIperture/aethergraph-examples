from __future__ import annotations
from aethergraph import graph_fn, NodeContext, run
from aethergraph.server import start

"""
free-form event logging with memory().record(...) + memory().recent(...)
What it does: appends a lightweight, schemaless event (kind, text/metrics/tags…) to HotLog + Persistence, then fetches with recent(kinds=[...]).
When to use: notes, traces, breadcrumbs, ad-hoc metrics—anything you’d otherwise print() or logger.info() but want durable + queryable.
Why it’s flexible: data can be any JSON-ish blob; no naming convention required.
"""

# Bring up sidecar (hotlog + persistence are wired by your runtime)
url = start()
print("AetherGraph sidecar server started at:", url)

@graph_fn(name="memory_record_recent_demo")
async def memory_record_recent_demo(*, context: NodeContext):
    """
    Demonstrates:
      - memory().record(kind, data, tags, entities, severity, metrics)
      - memory().recent(kinds=[...], limit=...)
    Returns:
      {
        "event_id": str,
        "signal": float,
        "recent_count": int
      }
    """
    mem = context.memory()

    # 1) Record a small, structured event (free-form data allowed)
    evt = await mem.record(
        kind="user_msg",
        data={"text": "hello world", "lang": "en"},
        tags=["demo", "quickstart"], # Optional tags for filtering
    )

    # 2) Fetch recent events of this kind (most recent last)
    recent = await mem.recent(kinds=["user_msg"], limit=10)

    # Tell the user and return a compact summary
    await context.channel().send_text(
        f"[mem] recorded event_id={evt.event_id} signal={evt.signal:.2f}; recent(user_msg)={len(recent)}"
    )
    return {
        "event_id": evt.event_id,
        "signal": float(getattr(evt, "signal", 0.0)),
        "recent_count": len(recent),
    }

if __name__ == "__main__":
    result = run(memory_record_recent_demo, inputs={})
    print("Result:", result)
