# Prerequisite: None
# Suggested: slack channel or telegram channel for better interactivity
# See: https://aiperture.github.io/aethergraph-docs/channel-setup/introduction/ for channel setup instructions.

from aethergraph import graph_fn, graphify, tool, NodeContext 
from aethergraph.tools import send_text, ask_approval 

# in graph_fn
@graph_fn(name="channel_approve_graph_fn")
async def channel_approve_demo(*, context: NodeContext):

    # 1) basic approval with default options ("Approve", "Reject")
    approved, choice = await context.channel().ask_approval(
        prompt="Do you approve the deployment?"
    )
    # approved is when user selected "Approve" or the first option, choice is the exact label
    await context.channel().send_text(
        f"[default] approved={approved} choice={choice}"
    )

    # 2) custom options + timeout
    approved, choice = await context.channel().ask_approval(
        prompt="Pick a deployment strategy:",
        options=("Canary", "Blue/Green", "Abort"),
        timeout_s=600,              # optional: deadline (seconds)
    )
    await context.channel().send_text(
        f"[custom] approved={approved} choice={choice}"
    )
    return {
        "default": {"approved": approved, "choice": choice},
        "custom": {"approved": approved, "choice": choice},
    }


# in graphfy
@tool(name="send_results", outputs=["ok"])
async def send_results(approval_res, context: NodeContext):
    # NOTE: send_text tool is already defined in aethergraph.tools, it cannot be used inside a tool directly
    await context.channel().send_text(
        text=f"Approval result: approved={approval_res['approved']} choice={approval_res['choice']}"
    )
    return {"ok": True}

# we use dual-stage approval here as an example
@graphify(name="channel_approve_graphify")
def channel_approve_graphify():
    res1 = ask_approval(
        prompt="Do you approve the first stage?",
    )  # returns NodeHandler, not awaited


    sent1 = send_results(res1, _after=res1) # we use context method to send result with more flexibility, since res1 is a NodeHandler

    # The follow CAN run, but it does not resolve the "approved" and "choice" values properly for sending text because res1 is a NodeHandler.
    # sent1 = send_text(
    #     text=f"Approval result: approved={res1['approved']} choice={res1['choice']}",
    #     _after=res1
    # )

    res2 = ask_approval(
        prompt="Which option do you choose?",
        options=("Option 1", "Option 2", "More Info"),
        _after=sent1
    )  # returns NodeHandler, not awaited
    send_results(res2, _after=res2)

    return {
        "stage_1": res1,
        "stage_2": res2,
    }

if __name__ == "__main__":
    from aethergraph.runner import run

    # result_fn = run(channel_approve_demo)
    # print("channel_approve_demo result:", result_fn)

    result_graphify = run(channel_approve_graphify)
    print("channel_approve_graphify result:", result_graphify)