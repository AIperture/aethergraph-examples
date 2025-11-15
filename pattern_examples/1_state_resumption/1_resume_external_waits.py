"""
Prerequisite: set up a Slack or Telegram channel
See 3_channel_setup.py and Docs for channel setup instructions.
NOTE: Console channel does not support interruption & resume yet.
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