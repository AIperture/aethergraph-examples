from aethergraph import graph_fn, NodeContext
from aethergraph import start_server 

url = start_server(port=0)

@graph_fn(name="memory_record_graph")
async def memory_record_graph(context: NodeContext):
    """A simple graph that demonstrates memory recording and retrieval."""
    mem = context.memory()
    
    # Record an event 
    evt = await mem.record( 
        kind="note",
        data={"text_note": "This is a test note."},
        tags=["test", "note"],
        severity=2, # optional severity level
        stage="initial" 
    )

    print("Event id:", evt.event_id)
    print("Event kind:", evt.kind)
    print("Event text payload (JSON String):", evt.text) 
    return {"event_id": evt.event_id}


@graph_fn(name="memory_retrieve_graph")
async def memory_retrieve_graph(context: NodeContext):
    """A simple graph that demonstrates memory retrieval."""
    mem = context.memory()
    
    # Retrieve events with tag "test"
    events = await mem.recent(
        kinds=["note"],    # filter by kind
        limit=5,          # max number of events to retrieve
    )

    for evt in events:
        print("Event id:", evt.event_id)
        print("Event kind:", evt.kind)
        print("Event text payload (JSON String):", evt.text) 

    # To access data, you will need to parse the JSON string like this:
    # import json
    # data = json.loads(evt.text)
    # print("Event data field 'text_note':", data.get("text_note"))

    # Alternatively, if you just need data fields, you can 
    event_data = await mem.recent_data(
        kinds=["note"],    # filter by kind
        limit=5,          # max number of events to retrieve    
    )

    return {"retrieved_count": len(events), "event_data": event_data}


if __name__ == "__main__":
    from aethergraph.runner import run_async
    import asyncio
    run_id = "tutorial_memory_record" # fixed run_id for demo purposes so memory is shared

    print("Running memory_record_graph...")
    result_record = asyncio.run(run_async(memory_record_graph, inputs={}, run_id=run_id))
    print("memory_record_graph result:", result_record)

    print("Running memory_retrieve_graph...")
    result_retrieve = asyncio.run(run_async(memory_retrieve_graph, inputs={}, run_id=run_id))
    print("memory_retrieve_graph result:", result_retrieve)
