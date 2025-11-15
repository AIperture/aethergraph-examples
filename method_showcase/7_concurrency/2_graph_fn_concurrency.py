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