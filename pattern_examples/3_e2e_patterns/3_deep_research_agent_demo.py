# Prerequisite: general LLM setup in AetherGraph

"""
This script demonstrates a parallel multi-perspective research agent that breaks down complex questions into specialized angles and combines the results:

What it does:

Receives a research question (e.g., "How do diffusion models compare to GANs?")

Spawns 3 parallel specialist agents (deep_research_angle), each focusing on a different perspective:
    "High-level overview" - Big picture understanding
    "Limitations and open problems" - Critical analysis
    "Practical implementation tips" - Applied knowledge
    All three run concurrently (fan-out pattern)

Each specialist agent:
    Sends progress update to channel: [angle] Starting work on: <question>
    Calls LLM with specialized system prompt focused on their angle
    Asks for 3-7 bullet points addressing that perspective
    Sends completion message: [angle] Finished
    Returns summary text

Aggregator combines reports (combine_research_reports):
    Waits for all 3 specialists to complete (fan-in pattern)
    In test_mode: Simply concatenates the reports
    In real mode: Uses LLM to merge reports into a coherent answer with:
        Short high-level summary (2-3 sentences)
        Integrated key points (bullet list)
        Concrete next steps

Sends final answer back to channel (Slack/console)

Key concepts:
    Parallel specialization: Multiple LLM calls run concurrently, each with different expertise
    Fan-out/fan-in pattern: Distribute work → wait for all → combine results
    Progressive updates: Real-time status messages keep user informed
    Test mode: Can stub out LLM calls for fast demo/development
    Channel-agnostic: Works with console, Slack, or any channel adapter
    Max concurrency: max_concurrency=3 allows all 3 specialists to run simultaneously

Benefits over single-agent approach:
    Faster: Parallel execution vs sequential
    More comprehensive: Each agent focuses deeply on its angle
    Better quality: Specialized prompts > one generic prompt
    Transparent: User sees progress from each specialist

This pattern scales to many specialists (5-10+) analyzing different aspects of complex questions, making it powerful for research synthesis, multi-faceted analysis, and comprehensive Q&A systems.
"""


from __future__ import annotations

import asyncio
from typing import Dict, Any

from aethergraph import graphify, tool, NodeContext
from aethergraph.core.tools import send_text


# -------------------------------------------------------------------
# Helper: call LLM only when test_mode=False
# -------------------------------------------------------------------
async def _maybe_llm(
    *,
    system_prompt: str,
    user_prompt: str,
    context: NodeContext,
    test_mode: bool,
    angle: str,
) -> str:
    chan = context.channel()  # bound to current session/channel

    if test_mode:
        # Stubbed mode: no real LLM, just sleep + fake content
        await chan.send_text(f"[{angle}] (test_mode) Simulating LLM call...")
        await asyncio.sleep(1.0)
        return (
            f"[TEST MODE] {angle} notes for your question.\n\n"
            f"System prompt:\n{system_prompt[:200]}...\n\n"
            f"User prompt:\n{user_prompt[:200]}..."
        )

    await chan.send_text(f"[{angle}] Calling LLM...")
    client = context.llm()

    llm_text, usage = await client.chat(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
    )
    # llm_text is already a string in your API
    return llm_text


# -------------------------------------------------------------------
# 1) One “angle” worker: overview / limitations / implementation
# -------------------------------------------------------------------
@tool(outputs=["summary"])
async def deep_research_angle(
    question: str,
    angle: str,
    test_mode: bool = True,
    channel: str | None = None,
    *,
    context: NodeContext,
) -> Dict[str, Any]:
    """
    One specialized worker:
      - 'angle' describes the perspective (e.g. "high-level overview").
      - Uses context.llm().chat(...) unless test_mode is True.
      - Sends progress updates to the channel.
    """
    chan = context.channel(channel)

    await chan.send_text(f"[{angle}] Starting work on:\n{question}")

    system_prompt = (
        "You are a highly capable research assistant. "
        f"You focus specifically on: {angle}."
    )
    user_prompt = (
        f"User question:\n{question}\n\n"
        "Provide 3–7 bullet points that address this angle. "
        "Be precise, concise, and technically accurate."
    )

    summary = await _maybe_llm(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        context=context,
        test_mode=test_mode,
        angle=angle,
    )
    await chan.send_text(f"[{angle}] Finished.")
    return {"summary": summary}


# -------------------------------------------------------------------
# 2) Aggregator: combine all angle reports into a single answer
# -------------------------------------------------------------------
@tool(outputs=["answer"])
async def combine_research_reports(
    question: str,
    overview: str,
    limitations: str,
    implementation: str,
    test_mode: bool = True,
    channel: str | None = None,
    *,
    context: NodeContext,
) -> Dict[str, Any]:
    """
    Merge multiple angle reports into a single coherent answer using the LLM,
    or just concatenate in test_mode.
    """
    chan = context.channel(channel)
    await chan.send_text("[aggregator] Combining reports...")

    if test_mode:
        combined = (
            f"# Deep research summary (TEST MODE)\n\n"
            f"## Question\n{question}\n\n"
            "## High-level overview\n"
            f"{overview}\n\n"
            "## Limitations & open problems\n"
            f"{limitations}\n\n"
            "## Practical implementation tips\n"
            f"{implementation}\n"
        )
        await chan.send_text("[aggregator] Done (test_mode, no real LLM).")
        return {"answer": combined}

    system_prompt = (
        "You are a research summarization expert. "
        "You receive partial reports from different specialist agents and "
        "must merge them into a single, clear answer."
    )
    user_prompt = (
        f"User question:\n{question}\n\n"
        "You are given three partial reports:\n\n"
        "== OVERVIEW ==\n"
        f"{overview}\n\n"
        "== LIMITATIONS ==\n"
        f"{limitations}\n\n"
        "== IMPLEMENTATION ==\n"
        f"{implementation}\n\n"
        "Task: produce a single, well-structured answer with:\n"
        "1. A short high-level summary (2–3 sentences).\n"
        "2. Key points (bullet list) that integrate all three perspectives.\n"
        "3. Concrete next steps for the user.\n"
    )

    client = context.llm()
    llm_text, usage = await client.chat(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
    )

    await chan.send_text("[aggregator] Done.")
    return {"answer": llm_text}


# -------------------------------------------------------------------
# 3) Static graph: deep_research_agent
# -------------------------------------------------------------------
@graphify(
    name="deep_research_agent",
    inputs=["question", "channel", "test_mode"],
    outputs=["answer"],
)
def deep_research_agent(
    question: str,
    channel: str | None = None,
    test_mode: bool = True,
):
    """
    Deep research pipeline:
      - Run multiple specialized “angles” in parallel.
      - Combine their reports into a single answer.
      - Stream progress updates to the channel.
    """

    # Kickoff message
    start = send_text(
        text=f"🔍 Starting deep research on:\n{question}",
        channel=channel,
    )

    # 3 worker angles – they can run in parallel (all depend only on 'start')
    overview = deep_research_angle(
        question=question,
        angle="high-level overview",
        test_mode=test_mode,
        channel=channel,
        _after=start,
    )

    limitations = deep_research_angle(
        question=question,
        angle="limitations and open problems",
        test_mode=test_mode,
        channel=channel,
        _after=start,
    )

    implementation = deep_research_angle(
        question=question,
        angle="practical implementation tips",
        test_mode=test_mode,
        channel=channel,
        _after=start,
    )

    # Aggregator waits for all 3 angles
    combined = combine_research_reports(
        question=question,
        overview=overview.summary,
        limitations=limitations.summary,
        implementation=implementation.summary,
        test_mode=test_mode,
        channel=channel,
        _after=[overview, limitations, implementation],
    )

    # Final message to user
    send_text(
        text=combined.answer,
        channel=channel,
        _after=combined,
    )

    return {"answer": combined.answer}



# -------------------------------------------------------------------
# 4) Optional runner
# -------------------------------------------------------------------
if __name__ == "__main__":
    from aethergraph import start_server
    from aethergraph.core.runtime.graph_runner import run_async

    # 1) Boot sidecar so channel().* and context.llm() are wired
    url = start_server(port=0, log_level="info")
    print("sidecar:", url)

    # 2) Example question
    question = (
        "How do diffusion models compare to GANs for image generation, "
        "in terms of sample quality, training stability, and compute cost?"
    )

    # 3) Choose channel:
    #    - None → default channel (e.g., console or default Slack)
    #    - or a specific channel key like:
    #      channel_key = 'slack:team/T123:chan/C456'
    SLACK_TEAM_ID = "<your-slack-team-id>"
    SLACK_CHANNEL_ID = "<your-slack-channel-id>"
    channel_key = f"slack:team/{SLACK_TEAM_ID}:chan/{SLACK_CHANNEL_ID}"

    from aethergraph.core.runtime.runtime_services import current_services

    svc = current_services()
    svc.channels.set_default_channel_key(channel_key)
    # 4) Choose mode:
    #    - test_mode=True  → no real LLM calls (stubbed, fast, good for demo)
    #    - test_mode=False → call context.llm().chat(...)
    test_mode = True

    tg = deep_research_agent()

    out = asyncio.run(
        run_async(
            tg,
            inputs={
                "question": question,
                "channel": channel_key,
                "test_mode": test_mode,
            },
            max_concurrency=3,
        )
    )
    print("FINAL ANSWER:\n", out)
