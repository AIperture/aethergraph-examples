from __future__ import annotations
import asyncio
from aethergraph import graph_fn, NodeContext, run
from aethergraph.server import start

# 1) Boot the sidecar (default params; provides channel etc.)
url = start()
print("AetherGraph sidecar server started at:", url)

# 2) Minimal agent: log → channel → LLM → return
@graph_fn(name="hello_world")
async def hello_world(input_text: str, *, context: NodeContext):
    context.logger().info("hello_world started")

    # Send a greeting to the channel. Default channel is console. More channels set up will be introduced in later examples.
    await context.channel().send_text(f"👋 Hello! You sent: {input_text}")

    # LLM call (env vars or config file should set API key)
    llm_text, _usage = await context.llm().chat(
        messages=[
            {"role": "system", "content": "Be brief."},
            {"role": "user", "content": f"Say hi back to: {input_text}"},
        ]
    )
    await context.channel().send_text(f"LLM replied: {llm_text}")

    output = input_text.upper()
    context.logger().info("hello_world finished")
    return {"final_output": output}

# 3) Run the graph function. We can also use await hello_world(...) in async context.
if __name__ == "__main__":
    result = run(hello_world, inputs={"input_text": "hello world"})
    print("Result:", result)
