from __future__ import annotations
from aethergraph import graph_fn, NodeContext, run
from aethergraph.server import start

"""
typed outputs for fast lookups with memory().write_result(...) + memory().last_by_name(...) + memory().last_outputs_by_topic(...)
What it does: writes a normalized tool_result with typed inputs/outputs ({"name","kind","value"}), and updates indices so you can query:
last_by_name("greeting") → the latest value for that output name (across the session)
last_outputs_by_topic("demo.pipeline") → the latest output map for a tool/flow
When to use: you want stable, named values that downstream code, dashboards, or tests will read without scanning logs (e.g., “what’s the latest loss?”).
"""

# Sidecar up
url = start()
print("AetherGraph sidecar server started at:", url)

@graph_fn(name="memory_write_result_and_query_demo")
async def memory_write_result_and_query_demo(topic: str = "demo.pipeline", *, context: NodeContext):
    """
    Demonstrates:
      - memory().write_result(topic, inputs, outputs, tags, metrics, message)
      - memory().last_by_name(name)
      - memory().last_outputs_by_topic(topic)

    Conventions for typed I/O (Value-like dicts):
      {"name": <str>, "kind": <str>, "value": <any-json-serializable>}

    Returns:
      {
        "last_greeting_by_name": <value or None>,
        "last_outputs_for_topic": <dict[str, any]>
      }
    """
    mem = context.memory()

    # 1) Write a typed result (this also updates fast indices)
    upper = "HELLO WORLD"
    evt = await mem.write_result(
        topic=topic,
        inputs=[{"name": "input_text", "kind": "text", "value": "hello world"}],
        outputs=[
            {"name": "greeting", "kind": "text", "value": upper},
            {"name": "length", "kind": "number", "value": len(upper)},
        ],
        tags=["demo", "result"],
        metrics={"tokens": 0},
        message="Uppercased greeting",
        severity=3,
    )

    # 2) Query fast indices
    last_greeting = await mem.last_by_name("greeting")             # → "HELLO WORLD"
    last_outputs_map = await mem.last_outputs_by_topic(topic)      # → {"greeting": "...", "length": 11, ...}

    await context.channel().send_text(
        f"[mem] wrote tool_result evt={evt.event_id}; last_by_name('greeting')={last_greeting!r}"
    )

    return {
        "last_greeting_by_name": last_greeting,
        "last_outputs_for_topic": last_outputs_map,
    }

if __name__ == "__main__":
    result = run(memory_write_result_and_query_demo, inputs={"topic": "demo.pipeline"})
    print("Result:", result)
