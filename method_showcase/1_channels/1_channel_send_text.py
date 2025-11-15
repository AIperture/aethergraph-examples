from aethergraph import graph_fn, graphify, tool, NodeContext
from aethergraph import start_server 


# in graph_fn
@graph_fn(name="channel_send_demo")
async def channel_send_demo(*, context: NodeContext):
    await context.channel().send_text("Hello from AetherGraph!")
    return {"status": "message sent"}


# in graphfy
@tool(name="chan_send", outputs=["ok"])
async def chan_send_tool(context: NodeContext):
    await context.channel().send_text("Hello from AetherGraph tool!")
    return {"ok": True}



@graphify(name="channel_send_graph")
def channel_send_graph():
    res = chan_send_tool() # return NodeHandler, not awaited
    return {"tool_result": res}

if __name__ == "__main__":
    from aethergraph.runner import run
    result = run(channel_send_demo)
    print("channel_send_demo result:", result)

    graph_result = run(channel_send_graph)
    print("channel_send_graph result:", graph_result)