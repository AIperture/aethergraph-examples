from __future__ import annotations
from aethergraph import graph_fn, NodeContext, run
from aethergraph.server import start

# Boot the sidecar so channel methods are available (console/Slack/etc.)
url = start(port=8000)
print("AetherGraph sidecar server started at:", url)

@graph_fn(name="channel_ask_approval_demo")
async def channel_ask_approval_demo(
    task: str = "publish report",
    *, context: NodeContext
):
    """
    Demonstrates channel().ask_approval(prompt, options, timeout_s, channel)
    Return schema (dict):
      {
        "approved": bool,          # True/False signal
        "choice":  str            # Exact button label chosen (e.g. "Approve" | "Reject" | custom)
      }
    """

    context.logger().info("ask_approval: begin")

    # 1) Basic approval with default options ("Approve", "Reject")
    res_default = await context.channel().ask_approval(
        prompt=f"Do you approve the action: {task}?"
    )
    await context.channel().send_text(
        f"[default] approved={res_default['approved']} choice={res_default['choice']}"
    )

    # 2) Custom options + timeout
    res_custom = await context.channel().ask_approval(
        prompt="Pick a deployment strategy:",
        options=("Canary", "Blue/Green", "Abort"),
        timeout_s=600,              # optional: deadline (seconds)
    )
    await context.channel().send_text(
        f"[custom] approved={res_custom['approved']} choice={res_custom['choice']}"
    )

    context.logger().info("ask_approval: end")

    # Return the *structured* results (easy to test/chain downstream)
    return {
        "default": res_default,     # {"approved": bool, "choice": str}
        "custom":  res_custom       # {"approved": bool, "choice": str}
    }

if __name__ == "__main__":
    result = run(channel_ask_approval_demo, inputs={"task": "publish report"})
    print("Result:", result)
