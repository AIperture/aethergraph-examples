# Prerequisite: Interactive channel setup (e.g., Slack, Telegram)
# See: https://aiperture.github.io/aethergraph-docs/channel-setup/introduction/ for channel setup instructions.
# See 4_channel_setup.py for example of channel setup with multiple channels and aliases.
# NOTE: console channel does NOT support WAITING_HUMAN state resumption; use Slack/Telegram for testing.


"""
This script demonstrates state persistence and resumption for long-running workflows with human-in-the-loop interactions:

What it does:

Creates a static graph (hello_resume) that:
    Sends a greeting message via channel (Slack/Telegram)
    Asks for the user's name (ask_text()) → enters WAITING_HUMAN state
    Formats a personalized message
    Sends the final message

State persistence mechanism:
    Each node has a stable _id (e.g., "ask_text_6") for resumption
    When waiting for user input, the graph state is saved with the same run_id
    The process can be interrupted (Ctrl+C) while waiting

Two-phase execution pattern:
    First run (fresh run_id):
        Graph starts, sends greeting, asks for name
        Interrupt with Ctrl+C before answering
        State snapshot saved to disk with WAITING_HUMAN continuation
    Second run (same run_id):
        Graph cold-resumes from saved state
        User provides the answer in Slack/Telegram
        Graph completes and returns final message

Run ID management:
    Can pass via CLI arg, env var RUN_ID, or auto-generate new one
    Same run_id = resume; different run_id = fresh start

Key concepts:
    Durable execution: Workflows survive process crashes/restarts
    WAITING_HUMAN state: Graph pauses awaiting external input
    Cold resumption: Restart the process days later and continue where it left off
    Real channel required: Console doesn't support this pattern; needs Slack/Telegram/etc.

This pattern is crucial for long-running approval workflows, multi-day human-AI collaboration, or any scenario where the process might be interrupted while waiting for external events.

"""
from __future__ import annotations
import os, sys, time, asyncio
from aethergraph import graphify, tool
from aethergraph import start_server 


from aethergraph.core.tools import (
    ask_text, ask_approval, ask_files, send_text,
    get_latest_uploads
)

@tool(outputs=["msg"])
async def format_message(greeting: str, name: str) -> dict:
    return {"msg": f"{greeting} Nice to meet you, {name}."}

# -------------------------
# Static graph
# -------------------------
@graphify(name="hello_resume", inputs=["channel_key"], outputs=["final"])
def hello_resume(channel_key):
    g = send_text(text="Starting the resume demo...", channel=channel_key)
    a = ask_text(prompt="What's your name?", _after=g, channel=channel_key)                  # → WAITING_HUMAN the first time
    msg = format_message(greeting="ok", name=a.text, _after=a)
    done = send_text(text=msg.msg, _after=msg, channel=channel_key)
    return {"final": msg.msg}

@graphify(name="hello_resume", inputs=["channel_key"], outputs=["final"])
def hello_resume(channel_key):
    g = send_text(text="Starting the resume demo...", channel=channel_key, _id="send_text_5")  # stable IDs for nodes
    a = ask_text(prompt="What's your name?", _after=g, channel=channel_key, _id="ask_text_6")                  # → WAITING_HUMAN the first time
    msg = format_message(greeting="ok", name=a.text, _after=a, _id="format_message_7")
    done = send_text(text=msg.msg, _after=msg, channel=channel_key, _id="send_text_8")
    return {"final": msg.msg}
# -------------------------
# Runner usage
# -------------------------
"""
How to test interruption & resume:

1) First run (fresh RUN_ID):
   $ python demo_interruption_resume.py
   - It will print the RUN_ID and ask for your name in the console/web channel.
   - BEFORE replying, press Ctrl+C to simulate an interruption.
   - At this point, state_store has a snapshot and a WAITING continuation.

2) Resume run (same RUN_ID):
   $ RUN_ID=<the-printed-id> python demo_interruption_resume.py
   - The run will cold-resume. Now reply to the prompt in your channel.
   - The graph completes and prints FINAL output.

(You can also pass as an argument: `python demo_interruption_resume.py <RUN_ID>`.)
"""

def _resolve_run_id() -> str:
    # Prefer CLI arg, then env var, else mint a new one
    if len(sys.argv) >= 2 and sys.argv[1].strip():
        return sys.argv[1].strip()
    rid = os.getenv("RUN_ID")
    if rid and rid.strip():
        return rid.strip()
    import uuid
    return f"run-{uuid.uuid4().hex[:8]}"

if __name__ == "__main__":
    import asyncio
    from aethergraph.runner import run_async 

    # Start sidecar for channel communication (console/web/slack/etc.)
    url = start_server(port=0, log_level="info")
    print("sidecar:", url)

    run_id = _resolve_run_id()
    print(f"RUN_ID: {run_id}")

    # Materialize the static graph and RUN (sync wrapper).
    # Your runner will:
    #   - recover graph state if snapshots exist for run_id
    #   - keep WAITING_* nodes waiting (continuations persist)
    #   - finish once you respond to the prompt on resume

    tg = hello_resume()    
    SLACK_TEAM_ID = "<your-slack-team-id>"
    SLACK_CHANNEL_ID = "<your-slack-channel-id>"
    channel_key = f"slack:team/{SLACK_TEAM_ID}:chan/{SLACK_CHANNEL_ID}" 

    # use asyncio.run to run the async main function so that we can kill with Ctrl+C/cmd+C
    async def main():
        try:
            result = await run_async(tg, inputs={"channel_key": channel_key}, run_id=run_id, max_concurrency=1)
            print("FINAL:", result)
        except KeyboardInterrupt:
            print("\n(Interrupted) You can resume with the same RUN_ID:")
            print(f"  RUN_ID={run_id} python demo_interruption_resume.py\n")

    asyncio.run(main())