# Prerequisite: None

from aethergraph import graph_fn, NodeContext
from aethergraph import start_server 

url = start_server(port=0)

@graph_fn(name="write_memory_result_graph")
async def write_memory_result_graph(*, context: NodeContext):
    """A simple graph that writes its result to memory."""
    mem = context.memory()

    # Assuming one of the function tools performed a calculation and we want to store the result    
    inputs = [
        {"name": "expression", "kind": "text", "value": "1 + 2 * 3"},
    ]
    outputs = [
        {"name": "result", "kind": "number", "vtype": "integer", "value": 7},
        {"name": "explanation", "kind": "text", "vtype": "string", "value": "The expression evaluates to 7 because multiplication is performed before addition."}
    ]

    # mem.write_result will save the memory event with kind == "tool_result"
    evt = await mem.write_result(
        topic="tool.calculator",
        inputs=inputs,
        outputs=outputs,
        tags=["tool", "calculation"], 
        metrics={"latency_ms": 12.3},
        message="Evaluated 1 + 2 * 3",
    )
    print("Stored result event id:", evt.event_id)
    print("Event kind", evt.kind)
    return {"event_id": evt.event_id, "status": "result stored in memory"}


@graph_fn(name="read_memory_result_graph")
async def read_memory_result_graph(*, context: NodeContext):
    """A simple graph that reads calculation results from memory."""
    mem = context.memory()
    
    # Retrieve recent calculation results
    events = await mem.recent(
        kinds=["tool_result"],    # filter by kind
        limit=5,                  # max number of events to retrieve
    )

    for evt in events:
        print("Event id:", evt.event_id)
        print("Event kind:", evt.kind)
        print("Event text payload (JSON String):", evt.text) 

    return {"retrieved_count": len(events)}

@graph_fn(name="retrieve_last_calculation_result")
async def retrieve_last_calculation_result(*, context: NodeContext):
    """A simple graph that retrieves the last calculation result from memory."""
    mem = context.memory()
    
    # 1) get last output value by name (fast index lookup)
    last_output_by_name = await mem.last_by_name("result")
    # return a dict with keys: ts, event_id, vtype, value
    print("Last calculation result value:", last_output_by_name)

    # 2) last outputs for a given topic (e.g. "tool.calculator")
    last_calc_outputs = await mem.get_last_outputs_for_topic("tool.calculator") 
    # return a dict with keys: ts, event_id, last_outputs (which contains name->value mapping)
    print("Last calculation outputs for topic 'tool.calculator':", last_calc_outputs)

    return {
        "last_result": last_output_by_name,
        "last_calc_outputs": last_calc_outputs,
    }

if __name__ == "__main__":
    from aethergraph.runner import run_async
    import asyncio
    run_id = "tutorial_memory_write_result" # fixed run_id for demo purposes so memory is shared

    print("Running write_memory_result_graph...")
    result_write = asyncio.run(run_async(write_memory_result_graph, inputs={}, run_id=run_id))
    print("Write result:", result_write)

    print("\nRunning read_memory_result_graph...")
    result_read = asyncio.run(run_async(read_memory_result_graph, inputs={}, run_id=run_id))
    print("Read result:", result_read)

    print("\nRunning retrieve_last_calculation_result...")
    result_retrieve = asyncio.run(run_async(retrieve_last_calculation_result, inputs={}, run_id=run_id))
    print("Retrieve last calculation result:", result_retrieve)