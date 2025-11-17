# Prerequisite: set up LLM in your Aethergraph .env with the fields:

"""
This script implements the ReAct (Reason + Act + Observe) agent pattern - an iterative loop where an LLM reasons about a problem, chooses tools to use, and observes results:

What it does:

Given a question, the agent runs a loop (max 6 steps):
    Thought: LLM reasons about the current situation
    Action: LLM chooses a tool: Search, Calculator, or Finish
    Action Input: Parameters for the tool (query, expression, or final answer)
    Observation: Result from executing the tool
    History accumulates and is fed back to the LLM

Two toy tools available:
    Search: Looks up terms in a tiny in-memory knowledge base (_FAKE_WIKI)
    Calculator: Evaluates simple math expressions using restricted eval()

Termination:
    When LLM chooses Action: Finish, returns the answer immediately
    If max steps reached without finish, asks LLM for a final answer based on accumulated observations

Key features:
    LLM-driven tool selection: Model decides which tool to use at each step
    Iterative refinement: Each tool result informs the next reasoning step
    Full trace logging: Returns complete step history for transparency
    Text-based parsing: Expects LLM to output structured Thought:, Action:, Action Input: format

Advanced Multi-agent evolution (not implemented):
    Could replace Python tools with full @graph_fn specialist agents
    Router agent orchestrates calls to sub-agents instead of simple functions
    Each specialist has its own context, memory, and services

This is a foundational pattern for building autonomous agents that can use tools to solve multi-step problems requiring both information retrieval and computation.

"""


from __future__ import annotations
import math
from typing import Any, Dict, List, Tuple

from aethergraph import graph_fn, NodeContext


# ---------------------------------------------------------------------------
# Toy tools
# ---------------------------------------------------------------------------

# A tiny "knowledge base" for the Search tool
_FAKE_WIKI: Dict[str, str] = {
    "aethergraph": "AetherGraph is an agentic DAG execution framework for building AI-powered workflows.",
    "python": "Python is a popular high-level programming language.",
    "react": "ReAct is a pattern that interleaves reasoning and acting with tools.",
}


async def tool_search(query: str) -> str:
    """
    Very small toy "search" tool.

    - Looks for an exact key match in _FAKE_WIKI.
    - If no match, returns a generic 'not found' message.

    This is just to illustrate tool calling and very likely will fail to find the right info.
    In a real system, this could call a vector store, web search, or RAG over artifacts.
    """
    query_norm = query.strip().lower()
    for k, v in _FAKE_WIKI.items():
        if query_norm == k.lower():
            return f"[Search result for '{k}']: {v}"
    return f"[Search] No direct result for '{query}'. Try a more specific query."


async def tool_calculator(expression: str) -> str:
    """
    Very minimal calculator tool.

    For demo purposes, this only allows digits, spaces, and the operators + - * / ( ).
    DO NOT use this as-is in production; it's only to illustrate tool calling.

    In a real system, you'd use a robust math parser instead of eval.
    """
    allowed_chars = set("0123456789+-*/(). ")
    if any(ch not in allowed_chars for ch in expression):
        return "[Calculator] Expression contains unsupported characters."

    try:
        # Unsafe in general, but restricted by allowed_chars above.
        result = eval(expression, {"__builtins__": {}}, {"math": math})
        return f"[Calculator] {expression} = {result}"
    except Exception as e:
        return f"[Calculator] Error evaluating expression '{expression}': {e}"


# Registry for tools the LLM is allowed to call
TOOLS = {
    "Search": tool_search,
    "Calculator": tool_calculator,
}


# ---------------------------------------------------------------------------
# Helper: parsing ReAct-style LLM output
# ---------------------------------------------------------------------------

def parse_react_output(text: str) -> Tuple[str, str, str]:
    """
    Parse a simple ReAct-style output into (thought, action, action_input).

    We expect the model to respond with lines like:

        Thought: I should look up AetherGraph.
        Action: Search
        Action Input: aethergraph

    or to finish:

        Thought: I now know the answer.
        Action: Finish
        Action Input: AetherGraph is ...

    This is intentionally naive and text-based; in a real system, you
    might ask the model to output structured JSON instead.
    """
    thought = ""
    action = ""
    action_input = ""

    for line in text.splitlines():
        line = line.strip()
        if line.startswith("Thought:"):
            thought = line[len("Thought:"):].strip()
        elif line.startswith("Action:"):
            action = line[len("Action:"):].strip()
        elif line.startswith("Action Input:"):
            action_input = line[len("Action Input:"):].strip()

    return thought, action, action_input


def format_history_for_prompt(history: List[Dict[str, str]]) -> str:
    """
    Format the (Thought, Action, Action Input, Observation) history
    into a text block for the LLM prompt.
    """
    if not history:
        return "No previous steps.\n"

    lines: List[str] = []
    for i, step in enumerate(history, start=1):
        lines.append(f"Step {i}:")
        lines.append(f"  Thought: {step.get('thought', '')}")
        lines.append(f"  Action: {step.get('action', '')}")
        lines.append(f"  Action Input: {step.get('action_input', '')}")
        lines.append(f"  Observation: {step.get('observation', '')}")
        lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# ReAct agent
# ---------------------------------------------------------------------------

@graph_fn(name="react_agent")
async def react_agent(question: str, *, context: NodeContext):
    """
    Minimal ReAct-style agent.

    Inputs
    ------
    question : str
        The user question or task description to solve using ReAct.

    Behavior
    --------
    - Runs a loop for up to `max_steps`.
    - Each iteration:
        - Sends the question + history to the LLM.
        - Expects 'Thought', 'Action', and 'Action Input' lines.
        - If Action == one of the tool names, executes the tool and records an Observation.
        - If Action == 'Finish', stops and returns the final answer.
    - Returns the final answer plus the full step history.
    """

    logger = context.logger()
    chan = context.channel()
    llm = context.llm()

    logger.info("react_agent started")
    await chan.send_text(f"🤖 ReAct agent started.\nQuestion: {question}")

    max_steps = 6
    history: List[Dict[str, str]] = []
    final_answer: str | None = None

    system_prompt = (
        "You are a ReAct-style agent that solves problems by interleaving reasoning and tool use.\n"
        "You have access to the following tools:\n\n"
        "1) Search\n"
        "   - Use this to look up short descriptions in a small knowledge base.\n\n"
        "2) Calculator\n"
        "   - Use this to evaluate basic math expressions using +, -, *, /, parentheses.\n\n"
        "At each step, you MUST respond with exactly these three lines:\n\n"
        "Thought: <your step-by-step reasoning>\n"
        "Action: <one of: Search, Calculator, Finish>\n"
        "Action Input: <tool input or final answer text>\n\n"
        "If you already know the answer, choose Action: Finish and put the final answer in Action Input.\n"
    )

    for step_idx in range(1, max_steps + 1):
        logger.info("ReAct step %d", step_idx)

        history_block = format_history_for_prompt(history)

        user_prompt = (
            f"Question:\n{question}\n\n"
            f"History of previous steps:\n{history_block}\n"
            f"Now decide on the next Thought, Action, and Action Input."
        )

        react_text, usage = await llm.chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
        )

        thought, action, action_input = parse_react_output(react_text)
        logger.info("Parsed ReAct output -> Thought=%r, Action=%r, Action Input=%r", thought, action, action_input)

        if not action:
            logger.warning("No action parsed; stopping early.")
            break

        # Finish: we are done, treat Action Input as final answer
        if action.lower() == "finish":
            final_answer = action_input or "No answer provided."
            history.append(
                {
                    "thought": thought,
                    "action": action,
                    "action_input": action_input,
                    "observation": "[Finished]",
                }
            )
            logger.info("ReAct agent finished with answer: %s", final_answer)
            break

        # Tool call: Search, Calculator, etc.
        tool = TOOLS.get(action)
        if tool is None:
            observation = f"[Error] Unknown tool '{action}'."
            logger.warning("Unknown tool requested: %s", action)
        else:
            observation = await tool(action_input)

        history.append(
            {
                "thought": thought,
                "action": action,
                "action_input": action_input,
                "observation": observation,
            }
        )

    # Fallback: if we reached max_steps without Finish, call LLM once more for a final answer
    if final_answer is None:
        logger.info("Max steps reached without Finish; asking LLM for a final answer directly.")
        history_block = format_history_for_prompt(history)
        final_answer, _usage_final = await llm.chat(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an expert assistant. Based on the question and the step history, "
                        "give a final concise answer. Ignore any clearly incorrect observations."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Question:\n{question}\n\n"
                        f"Step history:\n{history_block}\n\n"
                        "Now provide a final answer in 1–3 sentences."
                    ),
                },
            ]
        )

    # Show final answer to the user
    await chan.send_text("✅ Final answer:\n" + final_answer)

    logger.info("react_agent finished")

    return {
        "question": question,
        "final_answer": final_answer,
        "steps": history,
    }


if __name__ == "__main__":
    from aethergraph import start_server
    from aethergraph.runner import run

    # 1) Boot the sidecar so channel() works (console by default).
    url = start_server(port=0, log_level="info") # to print out thinking steps
    print("AetherGraph sidecar server started at:", url)

    # 2) Run the ReAct agent once with a sample question.
    #    In practice you might call this from another graph or use CLI args.
    example_question = "What is AetherGraph, and what is 2 + 3 * 4?"
    result = run(react_agent, inputs={"question": example_question})
    # print("Result:", result)
