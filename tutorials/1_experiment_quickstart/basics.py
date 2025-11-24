from __future__ import annotations

import asyncio
from typing import Dict, Any

from aethergraph import graph_fn, NodeContext, start_server
from aethergraph.runner import run_async
from aethergraph.runtime import set_default_channel 


@graph_fn(name="experiment_quickstart")
async def experiment_quickstart(*, context: NodeContext) -> Dict[str, Any]:
    """
    Minimal channel demo: an interactive experiment launcher.

    Flow:
      1) Ask for experiment name.
      2) Ask for run mode: ["Quick sanity check", "Full run"].
      3) If full run, ask for number of steps.
      4) Show summary and ask: ["Run", "Cancel"].
      5) If "Run", simulate a tiny run with step updates.

    This example is meant to showcase:
      - send_text
      - ask_text
      - ask_approval

    It works with the console channel out of the box.
    If you set a Slack channel as default, the same graph
    will run interactively in Slack (with the usual setup).
    """
    chan = context.channel()

    # Intro
    await chan.send_text("🧪 Welcome to the *Experiment Quickstart* demo!")
    await chan.send_text("I'll ask you a couple of questions and then simulate a tiny run.")

    # 1) Experiment name
    raw_name = await chan.ask_text(
        prompt="Experiment name? (text anything you like)",
        timeout_s=600,
    )
    name = (raw_name or "").strip() or "demo-experiment"

    # 2) Run mode
    mode_res = await chan.ask_approval(
        prompt="What kind of run do you want?",
        options=["Quick sanity check", "Full run"],
        timeout_s=600,
    )
    mode = mode_res.get("choice", "Quick sanity check")

    # 3) Steps (only if Full run)
    if mode == "Quick sanity check":
        steps = 3
    else:
        while True:
            steps_str = (await chan.ask_text(
                prompt="How many steps should I run? (e.g. 10)",
                timeout_s=600,
            )).strip()
            try:
                steps = int(steps_str)
                if steps <= 0:
                    raise ValueError
                break
            except Exception:
                await chan.send_text(
                    f"⚠️ Could not read '{steps_str}' as a positive integer. Please try again."
                )

    config = {"name": name, "mode": mode, "steps": steps}

    # 4) Show summary and ask to run
    await chan.send_text(
        "Here is the configuration I will use:\n"
        f"- name: `{name}`\n"
        f"- mode: `{mode}`\n"
        f"- steps: `{steps}`"
    )

    decision_res = await chan.ask_approval(
        prompt="Should I start this run?",
        options=["Run", "Cancel"],
        timeout_s=600,
    )
    decision = decision_res.get("choice", "Cancel")

    if decision != "Run":
        await chan.send_text("❌ Cancelled. No run executed.")
        return {"status": "cancelled", "config": config}

    # 5) Simulate the run
    await chan.send_text("✅ Starting run...\n")

    for i in range(1, steps + 1):
        # In real code this would be your work; we just sleep a bit.
        await asyncio.sleep(0.2)
        await chan.send_text(f"Step {i}/{steps} complete.")

    await chan.send_text("🏁 Run finished. Thanks for trying the channel demo!")

    return {"status": "ok", "config": config}


if __name__ == "__main__":
    import os

    # Start the sidecar server (for channels like Slack, etc.)
    url = start_server(port=0)
    print("AetherGraph sidecar server started at:", url)

    # ----------------------------------------
    # Option 1 – Console channel (no setup)
    # ----------------------------------------
    # Works out of the box; good for local testing and videos.
    set_default_channel("console:local")

    # ----------------------------------------
    # Option 2 – Slack channel (requires setup)
    # ----------------------------------------
    # Uncomment this block once you have the Slack app configured
    # and replace the placeholders or use environment variables.
    #
    # SLACK_TEAM_ID = os.environ.get("SLACK_TEAM_ID", "<your-slack-team-id>")
    # SLACK_CHANNEL_ID = os.environ.get("SLACK_CHANNEL_ID", "<your-slack-channel-id>")
    # slack_channel_key = f"slack:team/{SLACK_TEAM_ID}:chan/{SLACK_CHANNEL_ID}"
    # set_default_channel(slack_channel_key)
    #
    # Then the same graph will run as an interactive Slack conversation,
    # so you can manage your experiments away from your desktop.

    # Run the graph once
    result = asyncio.run(run_async(experiment_quickstart))
    print("Result:", result)
