# Prerequisite: Make sure you have LLM set up in your Aethergraph .env with the fields:
# AETHERGRAPH_LLM__ENABLED=true
# AETHERGRAPH_LLM__DEFAULT__PROVIDER=openai   # e.g., openai, anthropic, google, lmstudio, etc.
# AETHERGRAPH_LLM__DEFAULT__MODEL=gpt-4o-mini # e.g., gpt-4o-mini, claude-2, gemini-2.5-flash-lite, qwen/qwen2.5-vl-7b, etc.
# AETHERGRAPH_LLM__DEFAULT__API_KEY=          # your API key


"""
This script demonstrates a chat agent with persistent memory that remembers conversations across sessions:

What it does:

Seeds memory with fake chat history (seed_chat_memory_demo):
    Records 2 example chat turns to memory:
        User: "We talked about integrating AetherGraph..."
        Assistant: "I suggested starting with a simple graph_fn..."
    Tagged with kind="chat_turn" for easy retrieval
    Simulates prior conversation context

Chat agent with memory loading (chat_agent_with_memory):
    Startup phase:
        Loads up to 50 previous chat turns from memory using mem.recent_data()
        Injects loaded history into conversation buffer
        Tells user: "🧠 I loaded X previous chat turns into context"
    Chat loop:
        User types messages (channel input)
        Each turn (user + assistant) recorded to:
            Memory (mem.record()) - persistent storage
            Local buffer (conversation) - current session
        LLM gets last 10 turns as context (including loaded history)
        Agent can reference past conversations: "what have we talked about?"
        Type 'quit'/'exit' to end

Wrap-up:
    Summarizes entire conversation using LLM
    Saves conversation + summary as JSON artifact
    Shows summary to user

Key features:
    Persistent memory: Conversations survive across runs (same run_id)
    Automatic history loading: Past context injected at startup
    Dual logging: Both memory (persistent) and local buffer (session)
    Context-aware responses: LLM sees both old and new messages
    Session summary: AI-generated summary at end
    Artifact storage: Full conversation saved for later analysis

This pattern enables stateful chatbots that maintain continuity across sessions, remember user preferences, and provide coherent long-term interactions.
"""


from __future__ import annotations

import json
from typing import Any, Dict, List

from aethergraph import graph_fn, NodeContext


@graph_fn(name="seed_chat_memory_demo")
async def seed_chat_memory_demo(*, context: NodeContext):
    """
    Seed the memory with a couple of fake chat turns so that
    chat_agent_with_memory can show prior context on first run.

    In real usage, these would come from past sessions.
    """
    mem = context.memory()
    logger = context.logger()

    # Log this turn into Memory:
    # - kind="chat_turn" lets us query all chat messages by kind.
    # - `data` is a small dict; mem.record() will JSON-encode it
    #   and store it in Event.text, so later we can reconstruct it with json.loads(evt.text).
    # - to retrieve the data, use mem.recent_data(kinds=["chat_turn"]) which
    #   will return a list of decoded dicts.
    await mem.record(
        kind="chat_turn",
        data={"role": "user", "text": "We talked about integrating AetherGraph into my project."},
        tags=["chat", "user", "seed"],
        severity=2,
        stage="observe",
    )
    await mem.record(
        kind="chat_turn",
        data={"role": "assistant", "text": "I suggested starting with a simple graph_fn and adding services later."},
        tags=["chat", "assistant", "seed"],
        severity=2,
        stage="act",
    )
    logger.info("Seeded demo chat memory with two turns.")
    return {"seeded": True}


@graph_fn(name="chat_agent_with_memory")
async def chat_agent_with_memory(*, context: NodeContext):
    """
    Simple chat agent that:
      - talks via context.channel(),
      - remembers turns via context.memory(),
      - loads prior chat turns into its context seamlessly,
      - summarizes the session at the end,
      - saves conversation+summary as an artifact.

    If you ask things like "what have we talked about?"
    the LLM can answer from the combined history (seeded + live),
    because prior turns are injected into the conversation buffer.
    """
    logger = context.logger()
    chan = context.channel()
    mem = context.memory()
    artifacts = context.artifacts()
    llm = context.llm()

    logger.info("chat_agent_with_memory started")

    # Local log to save as an artifact later.
    # We will PRE-SEED this with prior chat_turns from memory.
    conversation: List[Dict[str, Any]] = []

    # ---------- Warmup: load prior chat history into conversation ----------
    try:
        # recent_data() returns whatever you passed as `data=` to mem.record(...)
        # In this example, that's dicts like {"role": "user"|"assistant", "text": "..."}.
        previous_turns = await mem.recent_data(kinds=["chat_turn"], limit=50)
        logger.info(
            "🧠 [ChatAgent] Loaded %d decoded chat_turn records from memory",
            len(previous_turns),
        )
    except Exception as e:
        logger.warning("Failed to read recent chat_turn data: %s", e)
        previous_turns = []

    if previous_turns:
        loaded = 0
        for d in previous_turns:
            # Guard against unexpected shapes
            if not isinstance(d, dict):
                continue
            role = d.get("role")
            text = d.get("text")
            if role in ("user", "assistant") and text:
                conversation.append({"role": role, "text": text})
                loaded += 1

        await chan.send_text(
            f"🧠 I loaded {loaded} previous chat turns into context.\n"
            "I’ll use them as part of our conversation history."
        )
    else:
        await chan.send_text("👋 New session. I’ll remember this conversation as we go.")

    await chan.send_text("Type 'quit' or 'exit' to end the session.")

    # ---------- Main chat loop ----------
    while True:
        user = await chan.ask_text("You:")
        if not user:
            # empty line, just keep going
            continue

        normalized = user.strip().lower()
        if normalized in ("quit", "exit"):
            await chan.send_text("👋 Ending session. Let me summarize what we discussed...")
            break

        # Record user turn in memory + local buffer
        conversation.append({"role": "user", "text": user})
        await mem.record(
            kind="chat_turn",
            data={"role": "user", "text": user},
            tags=["chat", "user"],
            severity=2,
            stage="observe",
        )

        # Build context for LLM from the last few turns (including seeded ones)
        history_tail = conversation[-10:]  # user/assistant pairs, up to 10 turns

        messages = [{"role": "system", "content": "You are a helpful, concise assistant."}]
        for turn in history_tail:
            messages.append(
                {
                    "role": turn["role"],
                    "content": turn["text"],
                }
            )

        reply, _usage = await llm.chat(messages=messages)

        # Record assistant turn
        conversation.append({"role": "assistant", "text": reply})
        await mem.record(
            kind="chat_turn",
            data={"role": "assistant", "text": reply},
            tags=["chat", "assistant"],
            severity=2,
            stage="act",
        )

        await chan.send_text(reply)

    # ---------- Wrap-up summary from local conversation ----------
    hist_text = "\n".join(
        f"{turn['role']}: {turn['text']}" for turn in conversation[-20:]
    )
    summary_prompt = (
        "Summarize the following conversation between a user and an assistant. "
        "Focus on main topics, decisions, and any TODOs.\n\n"
        f"{hist_text}"
    )
    summary_text, _ = await llm.chat(
        messages=[
            {"role": "system", "content": "You write clear, concise summaries."},
            {"role": "user", "content": summary_prompt},
        ]
    )

    await chan.send_text("📌 Session summary:\n" + summary_text)

    # ---------- Optional: save conversation + summary as an artifact ----------
    try:
        payload = {
            "conversation": conversation,
            "summary": summary_text,
        }
        saved = await artifacts.save_json(
            payload, suggested_uri="./chat_session_with_memory.json"
        )
        logger.info("Saved chat session artifact: %s", saved.uri)
    except Exception as e:
        logger.warning("Failed to save chat session artifact: %s", e)

    logger.info("chat_agent_with_memory finished")

    return {
        "turns": len(conversation),
        "summary": summary_text,
    }


if __name__ == "__main__":
    import asyncio
    from aethergraph.runner import run_async
    from aethergraph import start_server

    # Start sidecar for channel communication (console/web/slack/etc.)
    url = start_server(port=8000, log_level="warning")
    print("AetherGraph sidecar server started at:", url)

    async def main():
        # 1) Seed some prior memory so the agent has history on first run
        await run_async(
            seed_chat_memory_demo,
            inputs={},
            run_id="demo_chat_with_memory",
        )

        # 2) Start the chat agent (same run_id to share memory)
        result = await run_async(
            chat_agent_with_memory,
            inputs={},
            run_id="demo_chat_with_memory",
        )
        print("Result:", result)

    asyncio.run(main())
