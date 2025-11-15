# ---------------------------------------------------------
# Example: Simple Copilot – Tool-Using Router
# ---------------------------------------------------------
#
# GOAL
# ----
# Implement a minimal “copilot” agent that:
#   - Talks to the user via console (channel()).
#   - Routes each request to:
#       * a calculator tool,
#       * a summarizer tool (LLM),
#       * or a direct answer mode (LLM),
#     based on a small LLM-based classifier.
#
# WHAT THIS EXAMPLE SHOWS
# -----------------------
# - Using a single @graph_fn as a "copilot" loop.
# - Calling small tools from that loop.
# - Letting an LLM decide which tool to use.
# - (Optionally) logging which tool was chosen per turn.
#
# DESIGN NOTES
# ------------
# - Tools are just plain Python/async functions:
#     * calculate(expression: str) -> str
#     * summarize_text(text: str, context: NodeContext) -> str
# - The copilot:
#     * uses `context.llm()` once to classify the query,
#     * then calls the appropriate tool or answers directly.
#
# This is intentionally small and "friendly", so users can imagine:
#     - replacing tools with their own domain-specific helpers,
#     - extending the router with more actions,
#     - plugging this copilot into different channels (Slack, web, etc.)
#       without touching the core logic.
#
# ---------------------------------------------------------
# ADVANCED VARIANTS (IDEAS ONLY)
# -------------------------------
# This example keeps everything in one @graph_fn with tools as plain functions.
# In a more advanced copilot, you might:
#
# 1) Turn each action into its own graph_fn agent
#    --------------------------------------------
#    - Instead of plain functions, define:
#        @graph_fn(name="calculator_agent")
#        @graph_fn(name="summarizer_agent")
#        @graph_fn(name="search_agent")
#        ...
#    - The router copilot would then:
#        * classify the query,
#        * call the appropriate graph_fn as a sub-agent (e.g., run(calculator_agent, ...)),
#        * integrate its result into the final reply.
#    - Each specialist agent can have its own:
#        * prompts,
#        * services (RAG, job_manager, etc.),
#        * memory/artifacts.
#
# 2) Use memory and artifacts to steer routing
#    -----------------------------------------
#    - Log each turn to memory or artifacts, e.g.:
#        * query, chosen mode, tool outputs, error flags.
#    - On the next request, the router can:
#        * look at recent history (e.g., “user is in a math-heavy session, bias toward calculator”),
#        * avoid repeating the same explanation (check prior summaries),
#        * detect stuck loops (e.g., tool failures) and switch strategy.
#    - This makes the copilot feel more “session-aware” and persistent over time.
#
# 3) Multi-step tool sequences instead of single-step calls
#    ------------------------------------------------------
#    - For complex tasks, the router can:
#        * first call a “planner” graph_fn to break a request into sub-tasks,
#        * then call multiple specialist agents in sequence (calc → summarize → explain),
#        * finally compose a single response for the user.
#    - All of these steps can be separate graph_fns wired together with normal Python control flow.
#
# 4) Channel-agnostic copilot
#    ------------------------
#    - The same copilot loop can run over:
#        * console (this example),
#        * Slack / Discord,
#        * a web UI,
#        * or an API endpoint,
#      by changing only the channel adapter / config, not the core logic.
#
# These patterns are the same core idea:
#   - keep the copilot loop as a small router/brain,
#   - move specialized behavior into separate graphs + services,
#   - let memory/artifacts provide long-term context and introspection.
# ---------------------------------------------------------


from __future__ import annotations

import re
from typing import Literal

from aethergraph import graph_fn, NodeContext


# ---------------------------------------------------------
# 1) Helper tools
# ---------------------------------------------------------

async def calculate(expression: str) -> str:
    """
    Very small "calculator" tool.

    For demo purposes, only allows digits, spaces, and + - * / ( ).
    This is NOT a production-safe evaluator; it's just enough to
    show tool routing and keep the example self-contained.
    """
    allowed = set("0123456789+-*/(). ")
    filtered = "".join(ch for ch in expression if ch in allowed)

    if not filtered.strip():
        return "[Calculator] I couldn't find a valid expression."

    try:
        # We deliberately use a restricted eval environment.
        result = eval(filtered, {"__builtins__": {}}, {})
        return f"[Calculator] {filtered} = {result}"
    except Exception as exc:
        return f"[Calculator] Error evaluating expression {filtered!r}: {exc}"


async def summarize_text(text: str, context: NodeContext) -> str:
    """
    Summarizer tool: calls the LLM via context.llm() to produce a short summary.
    """
    llm = context.llm()
    prompt = (
        "Summarize the following text in 2–3 sentences. "
        "Focus on the key ideas and keep it clear for a non-expert.\n\n"
        f"Text:\n{text}"
    )

    summary, _usage = await llm.chat(
        messages=[
            {"role": "system", "content": "You summarize text clearly and concisely."},
            {"role": "user", "content": prompt},
        ]
    )
    return summary


# ---------------------------------------------------------
# 2) LLM-based router (classification)
# ---------------------------------------------------------

async def classify_query(query: str, context: NodeContext) -> Literal["calculator", "summarize", "direct_answer"]:
    """
    Ask the LLM to classify the user's query into one of three buckets:

      - "calculator"    → compute an expression.
      - "summarize"     → summarize content in the query.
      - "direct_answer" → answer directly without tools.

    The model is instructed to ONLY reply with one of those labels.
    """
    llm = context.llm()

    system_prompt = (
        "You are a routing assistant for a copilot.\n\n"
        "Given the user's message, choose exactly ONE of these modes:\n"
        "  - calculator    (if the user asks to compute a math expression)\n"
        "  - summarize     (if the user asks you to summarize a piece of text)\n"
        "  - direct_answer (for everything else: questions, instructions, etc.)\n\n"
        "Respond with exactly one word: calculator, summarize, or direct_answer."
    )

    classification, _usage = await llm.chat(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query},
        ]
    )

    mode = classification.strip().lower()
    if mode not in ("calculator", "summarize", "direct_answer"):
        # Fallback if the model does something unexpected
        mode = "direct_answer"

    return mode  # type: ignore[return-value]


def extract_expression_from_query(query: str) -> str:
    """
    Very simple heuristic to pull a math expression out of the user's text.

    Strategy:
      - Keep only digits, parentheses, and +-*/.
      - Use that as the expression.

    Examples:
      "what is 2+3?" -> "2+3"
      "calculate (10 - 3) * 4 please" -> "(10-3)*4"
    """
    allowed = set("0123456789+-*/().")
    expr = "".join(ch for ch in query if ch in allowed)
    return expr or query


# ---------------------------------------------------------
# 3) Copilot graph function
# ---------------------------------------------------------

@graph_fn(name="simple_copilot")
async def simple_copilot(*, context: NodeContext):
    """
    Simple copilot loop that talks via context.channel():

      - Greets the user.
      - In a loop:
          * reads a message ("You:"),
          * routes to a tool or direct answer using an LLM classifier,
          * responds with the result.
      - Exits on 'quit' / 'exit'.

    This shows how a user can design a copilot that "works with them" by:
      - delegating routine tasks (math, summarization) to tools,
      - keeping more open-ended queries in "direct answer" mode,
      - making routing logic explicit and easy to extend.
    """
    logger = context.logger()
    chan = context.channel()

    logger.info("simple_copilot started")

    await chan.send_text(
        "🧭 Simple Copilot ready.\n"
        "I can answer questions, do quick math, or summarize text.\n"
        "Type 'quit' or 'exit' to stop."
    )

    while True:
        query = await chan.ask_text("You:")
        if not query:
            await chan.send_text("No input received. Type 'quit' to exit.")
            continue

        if query.strip().lower() in ("quit", "exit"):
            await chan.send_text("👋 Copilot session ended. Bye!")
            logger.info("simple_copilot ended by user request.")
            break

        # Decide which mode to use
        mode = await classify_query(query, context)
        logger.info("Router classified query as mode=%s", mode)

        # Optional: log to memory or artifacts (pseudo-code; adjust to your API)
        mem = context.memory()  # type: ignore[attr-defined]
        await mem.record(
            kind="copilot_routing",
            data={"query": query, "mode": mode},
        )


        # Route to tools / direct answer
        if mode == "calculator":
            expr = extract_expression_from_query(query)
            result = await calculate(expr)
            await chan.send_text(f"🧮 Calculator mode\n{result}")

        elif mode == "summarize":
            summary = await summarize_text(query, context)
            await chan.send_text("📝 Summary mode\n" + summary)

        else:  # "direct_answer"
            llm = context.llm()
            answer, _usage = await llm.chat(
                messages=[
                    {"role": "system", "content": "You are a helpful, concise assistant."},
                    {"role": "user", "content": query},
                ]
            )
            await chan.send_text("💬 Direct answer mode\n" + answer)

    logger.info("simple_copilot finished")
    return {"status": "finished"}


# ---------------------------------------------------------
# 4) Demo runner
# ---------------------------------------------------------

if __name__ == "__main__":
    from aethergraph import start_server
    from aethergraph.runner import run

    # Start sidecar so context.llm(), context.channel(), etc. are available.
    url = start_server(port=0)
    print("AetherGraph sidecar server started at:", url)

    # Run the copilot once. It'll keep interacting on the console
    # until the user types 'quit' or 'exit'.
    result = run(simple_copilot, inputs={})
    print("Result:", result)
