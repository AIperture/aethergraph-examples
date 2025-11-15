# ---------------------------------------------------------
# Example: Extending Services – Prompt Store & LLM Observer
# ---------------------------------------------------------
#
# GOAL
# ----
# Show how to define external runtime services and use them from agents via:
#
#   - context.prompt_store()
#   - context.llm_observer()
#
# so that:
#
# - Prompts are managed centrally (versioned, reusable).
# - LLM calls are logged centrally (for debugging, analytics, compliance).
# - Agent code stays small and focused on business logic.
#
# WHY A PROMPT STORE?
# -------------------
# Without a prompt store, each agent typically hard-codes its prompts:
#
#   - Harder to keep multiple agents consistent.
#   - Harder to A/B test prompt versions.
#   - Harder to audit or update prompts without touching code.
#
# With a PromptStoreService:
#
#   - Prompts are registered once (in setup / config code).
#   - Agents just say: template = context.prompt_store().get_prompt("support_agent").
#   - You can later load prompts from:
#       * a JSON/YAML file,
#       * a database,
#       * a remote config service,
#       * a UI that non-engineers can edit.
#
# WHY AN LLM OBSERVER?
# --------------------
# LLMObserverService centralizes logging of:
#
#   - Which agent called the LLM,
#   - Which prompt was used,
#   - What the model responded with,
#   - Any tags (experiment IDs, user IDs, etc.).
#
# That enables:
#
#   - Debugging: inspect prompts/responses for a specific run.
#   - Analytics: measure usage, latency, token counts, etc.
#   - Safety/compliance: audit what the model actually said.
#
# BIG PICTURE
# -----------
# Agents only know:
#
#   template = context.prompt_store().get_prompt("some_agent")
#   context.llm_observer().record(...)
#
# The actual storage / logging implementation can change later
# without modifying the agents.
# ---------------------------------------------------------

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from aethergraph import graph_fn, NodeContext
from aethergraph.core.runtime.base_service import Service
from aethergraph.core.runtime.runtime_services import register_context_service


# ---------------------------------------------------------
# 1) Define services
# ---------------------------------------------------------

@dataclass
class PromptStoreService(Service):
    """
    Simple in-memory prompt store with versioning.

    Prompts are keyed by (agent_name, version).
    'latest' is resolved via `latest_versions`.
    """

    prompts: Dict[str, Dict[str, str]] = field(default_factory=dict)
    latest_versions: Dict[str, str] = field(default_factory=dict)

    def register_prompt(self, agent_name: str, version: str, template: str, *, is_latest: bool = True) -> None:
        self.prompts.setdefault(agent_name, {})[version] = template
        if is_latest or agent_name not in self.latest_versions:
            self.latest_versions[agent_name] = version

    def get_prompt(self, agent_name: str, version: str = "latest") -> str:
        if version == "latest":
            version = self.latest_versions.get(agent_name, "default")
        agent_prompts = self.prompts.get(agent_name, {})
        if version not in agent_prompts:
            raise KeyError(f"No prompt found for agent={agent_name!r}, version={version!r}")
        return agent_prompts[version]


@dataclass
class LLMObserverService(Service):
    """
    Minimal LLM observer that collects prompt/response pairs in memory.

    In a real system, this could:
      - stream JSON to a file,
      - push to a logging/metrics system,
      - write to a database, etc.
    """

    records: List[Dict[str, Any]] = field(default_factory=list)

    def record(
        self,
        agent_name: str,
        prompt: str,
        response: str,
        *,
        tags: Optional[Dict[str, Any]] = None,
    ) -> None:
        entry = {
            "agent_name": agent_name,
            "prompt": prompt,
            "response": response,
            "tags": tags or {},
        }
        self.records.append(entry)

        # For the example we just print a short line:
        print(
            f"[LLMObserver] agent={agent_name}, tags={entry['tags']}, "
            f"prompt_preview={prompt[:60]!r}, response_preview={response[:60]!r}"
        )




# ---------------------------------------------------------
# 2) Agents that consume the services
# ---------------------------------------------------------

@graph_fn(name="support_agent")
async def support_agent(question: str, *, context: NodeContext):
    """
    Support-style agent:

    - Fetches its template from the prompt store.
    - Fills in the user question.
    - Calls the LLM.
    - Records the call via the LLM observer.
    """
    logger = context.logger()
    llm = context.llm()
    prompt_store: PromptStoreService = context.prompt_store()
    observer: LLMObserverService = context.llm_observer()

    logger.info("support_agent started with question=%r", question)

    template = prompt_store.get_prompt("support_agent", version="latest")
    prompt = template.format(question=question)

    response, usage = await llm.chat(
        messages=[
            {"role": "system", "content": "You are a helpful support assistant."},
            {"role": "user", "content": prompt},
        ]
    )

    observer.record(
        agent_name="support_agent",
        prompt=prompt,
        response=response,
        tags={"kind": "support", "version": "latest"},
    )

    # Optionally send to a channel (console/chat) if configured
    try:
        await context.channel().send_text("💬 Support agent answer:\n" + response)
    except Exception:
        # Channel may not be configured (e.g., running in a bare runtime).
        pass

    logger.info("support_agent finished")
    return {"answer": response, "usage": usage}


@graph_fn(name="analysis_agent")
async def analysis_agent(text: str, *, context: NodeContext):
    """
    Analysis-style agent:

    - Uses a different template from the same prompt store.
    - Logs its own LLM calls with separate tags.
    """
    logger = context.logger()
    llm = context.llm()
    prompt_store: PromptStoreService = context.prompt_store()
    observer: LLMObserverService = context.llm_observer()

    logger.info("analysis_agent started")

    template = prompt_store.get_prompt("analysis_agent", version="latest")
    prompt = template.format(text=text)

    response, usage = await llm.chat(
        messages=[
            {"role": "system", "content": "You are a precise analytical assistant."},
            {"role": "user", "content": prompt},
        ]
    )

    observer.record(
        agent_name="analysis_agent",
        prompt=prompt,
        response=response,
        tags={"kind": "analysis", "version": "latest"},
    )

    try:
        await context.channel().send_text("📊 Analysis agent output:\n" + response)
    except Exception:
        pass

    logger.info("analysis_agent finished")
    return {"analysis": response, "usage": usage}


# ---------------------------------------------------------
# 3) Demo run — prompts registered externally, then used by agents
# ---------------------------------------------------------

if __name__ == "__main__":
    from aethergraph import start_server
    from aethergraph.runner import run

    # Start sidecar so context.services, LLM, channel, etc. are available
    url = start_server(port=0)
    print("AetherGraph sidecar server started at:", url)

    # Create concrete service instances
    PROMPT_STORE = PromptStoreService()
    LLM_OBSERVER = LLMObserverService()

    # Register them so they appear as context.prompt_store() and context.llm_observer()
    # You need to start the sidecar BEFORE registering services
    register_context_service("prompt_store", PROMPT_STORE)
    register_context_service("llm_observer", LLM_OBSERVER)

    # --- External prompt registration step ---
    #
    # In a real application, this could be:
    #   - a startup script loading prompts from JSON/YAML,
    #   - a deployment step applying config from a remote store,
    #   - an admin UI that updates prompts without code changes.
    #
    # The agents DO NOT know about this — they just call get_prompt().
    PROMPT_STORE.register_prompt(
        agent_name="support_agent",
        version="v1",
        template=(
            "You are a friendly support agent.\n"
            "User question:\n{question}\n\n"
            "Provide a clear and concise answer."
        ),
        is_latest=True,
    )

    PROMPT_STORE.register_prompt(
        agent_name="analysis_agent",
        version="v1",
        template=(
            "You are an analytical assistant.\n"
            "Text:\n{text}\n\n"
            "1) List the key points as bullet points.\n"
            "2) Then provide a short summary in 2–3 sentences."
        ),
        is_latest=True,
    )

    # --- Demo inputs ---
    user_question = "How can I start migrating my existing Python scripts to AetherGraph?"
    sample_text = (
        "AetherGraph lets you turn plain Python async functions into agents with a rich runtime "
        "that provides LLMs, channels, memory, and external services."
    )

    # --- Run agents via `run` ---
    support_result = run(support_agent, inputs={"question": user_question})
    analysis_result = run(analysis_agent, inputs={"text": sample_text})

    print("\n=== Support Agent Answer ===")
    print(support_result["answer"])

    print("\n=== Analysis Agent Output ===")
    print(analysis_result["analysis"])

    # --- Observer summary ---
    print("\n=== LLM Observer Records ===")
    print(f"Total recorded calls: {len(LLM_OBSERVER.records)}")
    for rec in LLM_OBSERVER.records:
        print(
            f"- agent={rec['agent_name']}, tags={rec['tags']}, "
            f"prompt≈{rec['prompt'][:40]!r}, response≈{rec['response'][:40]!r}"
        )
