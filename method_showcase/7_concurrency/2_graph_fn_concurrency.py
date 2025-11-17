# Prerequisite: None 

"""
This script demonstrates manual concurrency control in @graph_fn agents using asyncio primitives:

What it does:

Creates a semaphore (asyncio.Semaphore(4)) to limit concurrent tasks to 4 at a time

Defines run_capped() helper that wraps any async function with semaphore protection

batch_agent processes items in parallel:
    Takes a list of items (7 fruits in the demo)
    Spawns concurrent tasks for each item (uppercase conversion)
    Semaphore ensures max 4 run simultaneously (even though 7 are submitted)
    Uses asyncio.gather() to wait for all tasks to complete
    Returns all uppercase results

Execution flow:
    Input: ["apple", "banana", "cherry", "date", "elderberry", "fig", "grape"]
    4 tasks run at once, then next 3 run as slots free up
    Output: {"ys": ["APPLE", "BANANA", "CHERRY", "DATE", "ELDERBERRY", "FIG", "GRAPE"]}

Key concepts:
    Manual concurrency control in dynamic @graph_fn agents using standard asyncio tools
    Rate limiting to avoid overwhelming external resources (APIs, databases, etc.)
    Combines AetherGraph context services (channel) with native Python async patterns
"""


import asyncio
from aethergraph import graph_fn

sem = asyncio.Semaphore(4)  # cap concurrent jobs (user-managed)

async def run_capped(fn, **kw):
    async with sem:
        return await fn(**kw)

@graph_fn(name="batch_agent")
async def batch_agent(items: list[str], *, context):
    async def one(x):
        await context.channel().send_text(f"processing {x}")
        return {"y": x.upper()}

    # fan‑out with manual cap
    tasks = [run_capped(one, x=v) for v in items]
    results = await asyncio.gather(*tasks)

    # fan‑in
    return {"ys": [r["y"] for r in results]}

if __name__ == "__main__":
    from aethergraph import start_server 
    from aethergraph.runner import run

    start_server(port=0)
    result = run(
        batch_agent,
        inputs={"items": ["apple", "banana", "cherry", "date", "elderberry", "fig", "grape"]},
    )
    print("Batch agent result:", result)