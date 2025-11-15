from aethergraph import tool, graphify 

@tool(outputs=["result"])
async def pick(items: list[int], index: int):
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
    results = [pick(items=vals, index=i) for i in range(len(vals))]  # example of using pick tool
    outs = [work(x=v.result) for v in results]       # fan‑out
    total = reduce_sum(xs=[o.out for o in outs])   # fan‑in
    return {"sum": total.sum}

if __name__ == "__main__":

    from aethergraph import start_server 
    from aethergraph.runner import run

    start_server(port=0)
    result = run(
        map_reduce,
        inputs={"vals": [1, 2, 3, 4, 5]},
    )