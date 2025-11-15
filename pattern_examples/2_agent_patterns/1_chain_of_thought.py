"""
Example: Chain-of-Thought Agent

This example shows a minimal Chain-of-Thought (CoT) pattern in AetherGraph:

1. Ask the user for a question via `channel()`.
2. First LLM call: generate a step-by-step reasoning trace (CoT) ONLY.
3. Optionally store that reasoning trace in memory or artifacts for debugging.
4. Second LLM call: generate a concise final answer based on the reasoning.
5. Send the answer (and optionally the reasoning trace) back to the user.

In practice, a **more sophisticated CoT agent** built on the same pattern might:

- **Hide CoT from end-users by default**
  - Store the reasoning trace in memory / artifacts for debugging, audits, or research.
  - Provide a “developer mode” or special flag that reveals CoT only when needed.

- **Use multiple reasoning phases**
  - Phase 1: rough brainstorming (list possibilities, assumptions, ambiguities).
  - Phase 2: structured reasoning (step-by-step derivation, intermediate results).
  - Phase 3: final decision + compact explanation.
  - Each phase can be a separate LLM call with its own system prompt and constraints.

- **Incorporate tools and checks**
  - Call calculators, search, or domain-specific simulators to verify intermediate steps.
  - Use extra LLM calls for self-check:
    - “Scan the reasoning for arithmetic or logical errors.”
    - “Verify each step against the given constraints or facts.”
  - If a check fails, revise the reasoning and re-derive the answer.

- **Log and analyze reasoning over many runs**
  - Write CoT traces and final answers into artifacts (e.g. JSONL).
  - Use another AG graph to:
    - Cluster common failure modes.
    - Summarize how the model typically solves certain classes of problems.
    - Build dashboards for CoT quality/consistency.

- **Adapt depth of reasoning to difficulty**
  - For simple questions: skip the full CoT and answer directly.
  - For complex multi-step questions: automatically switch into CoT mode.
  - This can be controlled by a small classifier (another LLM call or heuristic).

This file focuses on the **basic building block**:
two LLM calls (reasoning → answer) wired through `NodeContext`,
with an obvious place to plug in memory or artifact logging.
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
