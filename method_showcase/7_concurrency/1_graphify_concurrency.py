# Prerequisite: None 

"""
This script demonstrates parallel execution in static graphs using @graphify with fan-out/fan-in pattern:

What it does:

Defines three tools:
    pick() - Extracts an item from a list by index
    work() - Doubles a number (simulates parallel work)
    reduce_sum() - Sums a list of numbers

Creates a map-reduce graph (map_reduce):
    Fan-out: Creates 5 parallel pick nodes to extract each value from input list [1,2,3,4,5]
    Parallel work: Creates 5 parallel work nodes, each doubling its input
    Fan-in: Collects all results and sums them with reduce_sum

Execution flow:
    All pick nodes run in parallel
    All work nodes run in parallel (each depends on its corresponding pick)
    reduce_sum waits for all work nodes to complete
    Final result: (1×2) + (2×2) + (3×2) + (4×2) + (5×2) = 2 + 4 + 6 + 8 + 10 = 30

    Key concept: @graphify automatically detects dependencies and runs independent nodes concurrently, making it easy to build parallel data processing pipelines without explicit threading or async coordination.
"""

from aethergraph import tool, graphify 

MAX_WORKERS = 5  # fixed fan-out size for the graph


@tool(outputs=["result"])
async def pick(items: list[int], index: int):
    print(f"Picking index {index} from {items}...")
    return {"result": items[index]}


@tool(outputs=["out"])
async def work(x: int):
    print(f"Working on {x}...")
    return {"out": x * 2}


@tool(outputs=["sum"])
async def reduce_sum(xs: list[int]):
    return {"sum": sum(xs)}


@graphify(name="map_reduce", inputs=["vals"], outputs=["sum"])
def map_reduce(vals):
    # Fixed-width fan-out: we always create MAX_WORKERS pick+work nodes.
    # At runtime, vals must have length >= MAX_WORKERS.
    indices = list(range(MAX_WORKERS))

    # Fan-out: pick each element by fixed index
    results = [pick(items=vals, index=i) for i in indices]

    # Fan-out: apply work() to each picked result
    outs = [work(x=r.result) for r in results]

    # Fan-in: reduce all outputs into a single sum
    total = reduce_sum(xs=[o.out for o in outs])
    return {"sum": total.sum}


if __name__ == "__main__":
    from aethergraph import start_server
    from aethergraph.runner import run

    start_server(port=0)

    # Input length should be >= MAX_WORKERS, otherwise pick() will IndexError.
    vals = [1, 2, 3, 4, 5]
    result = run(
        map_reduce,
        inputs={"vals": vals},
        max_concurrency=MAX_WORKERS, # -> change this from 1 to MAX_WORKERS to see concurrency in action
    )
    print("Map-reduce result:", result)