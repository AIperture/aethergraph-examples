from __future__ import annotations
from aethergraph import graph_fn, NodeContext, run
from aethergraph.server import start

# 1) Boot the sidecar so channel methods are available (console/Slack/etc.)
url = start(port=8000)
print("AetherGraph sidecar server started at:", url)

# 2) Minimal demo of channel().send_text + channel().ask_text
@graph_fn(name="channel_send_and_ask")
async def channel_send_and_ask(greeting: str = "Hello!", *, context: NodeContext):
    # Send a message to the user
    await context.channel().send_text(f"{greeting} 👋  I can talk through your configured channel.")

    # Ask the user for free-form text input
    name = await context.channel().ask_text("What's your name?")
    await context.channel().send_text(f"Nice to meet you, {name}! 🎉")

    return {"user_name": name}

# 3) One-liner runner (can also be called from tests)
if __name__ == "__main__":
    result = run(channel_send_and_ask, inputs={"greeting": "Hi there"})
    print("Result:", result)
