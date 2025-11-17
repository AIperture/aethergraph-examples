# Prerequisite: None

from aethergraph import graph_fn, NodeContext, tool, graphify 
from aethergraph.tools import  ask_text 

# in graph_fn
@graph_fn(name="channel_ask_text_demo")
async def channel_ask_text_demo(*, context: NodeContext):

    # ask_text with prompt
    user_input = await context.channel().ask_text(
        prompt="Please enter some text input: \n"
    )
    await context.channel().send_text(
        f"You entered: {user_input}"
    )

    # If you use non-console channels, you can uncomment the following to test wait_text
    # user_inputs = await context.channel().wait_text()
    # await context.channel().send_text(
    #     f"You entered (wait_text): {user_inputs}"
    # )

    return {
        "normal_input": user_input,
    }

# in graphfy
@tool(name="send_user_input", outputs=["ok"])
async def send_user_input(*, context: NodeContext, user_input: str):
    await context.channel().send_text(f"You entered: {user_input}")
    return {"ok": True}

@graphify(name="channel_ask_text_graph")
def channel_ask_text_graph():
    user_input = ask_text(
        prompt="Please enter some text input: \n"
    )  # returns NodeHandler, not awaited

    send_res = send_user_input(
        user_input=user_input.text, _after=user_input
    )  # use context method to send result with more flexibility

    # If you use non-console channels, you can uncomment the following to test wait_text
    # user_inputs = wait_text(
    #     _after=send_res
    # )  # returns NodeHandler, not awaited
    # send_res2 = send_user_input(
    #     user_input=user_inputs.text, _after=user_inputs
    # )  # use context method to send result with more flexibility
    return {
        "user_input": user_input,
    }



if __name__ == "__main__":
    from aethergraph import start_server
    from aethergraph.runner import run_async
    import asyncio
    url = start_server(port=0) # start sidecar server at random port
    print("AetherGraph sidecar server started at:", url)

    result = asyncio.run(run_async(channel_ask_text_demo))
    print("Result:", result)

    # graph_result = asyncio.run(run_async(channel_ask_text_graph))
    # print("channel_ask_text_graph result:", graph_result)