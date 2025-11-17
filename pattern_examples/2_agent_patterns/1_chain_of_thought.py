"""
This script demonstrates the Chain-of-Thought (CoT) reasoning pattern where an LLM explicitly shows its step-by-step reasoning before providing a final answer:

What it does:

Asks user for a question via channel (e.g., a math/logic problem)

First LLM call - Generate reasoning trace:
    System prompt: "Think step-by-step, but DON'T give the final answer yet"
    Returns the reasoning process/analysis
    Stores the CoT trace in memory for debugging/auditing

Second LLM call - Generate final answer:
    System prompt: "Based on this analysis, give a concise final answer"
    Receives both the original question AND the reasoning trace
    Produces the final answer based on the explicit reasoning

Returns both outputs to the user:
    Shows the reasoning trace (for transparency/debugging)
    Shows the final answer

Key benefits:
    Improved accuracy: Forcing step-by-step reasoning reduces errors on complex problems
    Transparency: Users/developers can inspect the reasoning process
    Debuggability: CoT traces stored in memory help identify where reasoning went wrong
    Separation of concerns: Reasoning phase vs. answer formatting phase

Advanced patterns (not implemented here):
    Hide CoT from users by default (store only in artifacts)
    Multi-phase reasoning (brainstorm → reason → verify)
    Tool integration (call calculators to verify steps)
    Self-checking (LLM validates its own reasoning)
    Adaptive reasoning depth (skip CoT for simple questions)

This is a foundational pattern for building more reliable AI agents on complex tasks.
"""


from __future__ import annotations
import asyncio

from aethergraph import graph_fn, NodeContext


@graph_fn(name="chain_of_thought_agent")
async def chain_of_thought_agent(*, context: NodeContext):
    logger = context.logger()
    chan = context.channel()
    llm = context.llm()

    logger.info("chain_of_thought_agent started")

    # 1) Ask the user for a question
    await chan.send_text(
        "🧠 Chain-of-Thought demo.\n"
        "Ask me a question that needs reasoning (e.g. a math/logic problem),\n"
        "or type 'quit' to exit."
    )

    question = await chan.ask_text("Your question:")
    if not question:
        await chan.send_text("No question provided. Exiting.")
        logger.info("No question provided; exiting.")
        return {"status": "no_question"}

    if question.strip().lower() in ("quit", "exit"):
        await chan.send_text("Okay, exiting Chain-of-Thought demo. 👋")
        logger.info("User chose to exit.")
        return {"status": "user_exit"}

    # 2) First LLM call: generate reasoning trace (CoT) only
    #    We explicitly instruct the model not to give the final answer yet.
    system_cot = (
        "You are an expert at step-by-step reasoning. "
        "Analyze the user's question carefully and think through the steps in detail. "
        "Do NOT give the final answer yet; only provide your reasoning process."
    )

    logger.info("Requesting chain-of-thought reasoning from LLM...")
    reasoning, usage1 = await llm.chat(
        messages=[
            {"role": "system", "content": system_cot},
            {"role": "user", "content": question},
        ]
    )

    # 3) Optional: store reasoning trace for debugging (memory / artifacts)
    mem = context.memory()  # type: ignore[attr-defined]
    # Example API (adjust or replace with your own):
    await mem.record(
        kind="cot_trace",
        data={"question": question, "reasoning": reasoning, "usage": usage1},
    )

    # 4) Second LLM call: produce a concise final answer based on the reasoning
    system_answer = (
        "You are an expert explainer. Based on the analysis below, "
        "produce a concise, direct final answer to the question. "
        "If relevant, include a brief explanation in 1–3 sentences."
    )

    logger.info("Requesting final answer from LLM...")
    final_answer, usage2 = await llm.chat(
        messages=[
            {"role": "system", "content": system_answer},
            {
                "role": "user",
                "content": (
                    f"Question:\n{question}\n\n"
                    f"Analysis (your reasoning):\n{reasoning}"
                ),
            },
        ]
    )

    # 5) Send both reasoning and answer to the user
    #    In a real app you might choose to hide the CoT and only show it in debug mode.
    await chan.send_text("🔎 Reasoning (chain-of-thought, for debugging):\n" + reasoning)
    await chan.send_text("✅ Final answer:\n" + final_answer)

    logger.info("chain_of_thought_agent finished")

    return {
        "question": question,
        "reasoning": reasoning,
        "final_answer": final_answer,
        "usage": {"cot_call": usage1, "answer_call": usage2},
    }


if __name__ == "__main__":
    from aethergraph import start_server
    from aethergraph.runner import run

    # 1) Boot the sidecar so channel() works (console by default).
    url = start_server(port=0)
    print("AetherGraph sidecar server started at:", url)

    # 2) Run the graph function once. You can also call `await chain_of_thought_agent(...)`
    #    directly inside another graph or an async context.
    result = run(chain_of_thought_agent, inputs={})
