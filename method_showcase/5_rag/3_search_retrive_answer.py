from aethergraph import graph_fn, NodeContext
from aethergraph import start_server 

"""Prerequisite: ingest some corpora using rag_ingest_files and/or rag_ingest_inline from 1_ingest_files.py"""

@graph_fn(name="rag_search_demo")
async def rag_search_demo(
    corpus_id: str,
    query: str,
    k: int = 5,
    *,
    context: NodeContext
):
    rag = context.rag()
    hits = await rag.search(corpus_id, query, k=k, mode="hybrid")

    if not hits:
        await context.channel().send_text(f"No hits for '{query}' in corpus '{corpus_id}'.")
        return {"hits": []}

    lines = []
    for i, h in enumerate(hits, start=1):
        snippet = h.text.replace("\n", " ")
        if len(snippet) > 160:
            snippet = snippet[:160] + "…"
        lines.append(
            f"[{i}] score={h.score:.3f} doc_id={h.doc_id} chunk_id={h.chunk_id}\n    {snippet}"
        )

    await context.channel().send_text(
        f"Search results for '{query}' in '{corpus_id}':\n\n" + "\n".join(lines)
    )

    return {
        "query": query,
        "hits": [h.__dict__ for h in hits],
    }


@graph_fn(name="rag_retrieve_demo")
async def rag_retrieve_demo(
    corpus_id: str,
    query: str,
    k: int = 6,
    *,
    context: NodeContext
):
    rag = context.rag()
    hits = await rag.retrieve(corpus_id, query, k=k, rerank=True)

    lines = []
    for i, h in enumerate(hits, start=1):
        snippet = h.text.replace("\n", " ")
        if len(snippet) > 200:
            snippet = snippet[:200] + "…"
        lines.append(f"[{i}] {snippet}")

    await context.channel().send_text(
        f"Top-{k} retrieved chunks for '{query}' in '{corpus_id}':\n\n" + "\n".join(lines)
    )

    return {
        "query": query,
        "hits": [h.__dict__ for h in hits],
    }


@graph_fn(name="rag_answer_demo")
async def rag_answer_demo(
    corpus_id: str,
    question: str,
    style: str = "concise",
    *,
    context: NodeContext
):
    rag = context.rag()

    # Use default LLM configured on the facade
    result = await rag.answer(
        corpus_id=corpus_id,
        question=question,
        style=style,
        with_citations=True,
        k=6,
    )

    answer = result["answer"]
    resolved = result.get("resolved_citations", [])

    # Make a small citation footer
    if resolved:
        lines = ["", "Sources:"]
        for r in resolved:
            lines.append(
                f"[{r['rank']}] {r['title']} (doc_id={r['doc_id']}, chunk={r['chunk_id']})"
            )
        answer_with_sources = answer + "\n\n" + "\n".join(lines)
    else:
        answer_with_sources = answer

    await context.channel().send_text(answer_with_sources)

    return result


@graph_fn(name="rag_answer_with_profile")
async def rag_answer_with_profile(
    corpus_id: str,
    question: str,
    llm_profile: str = "default", # prerequired LLM profile name (default in .env)
    *,
    context: NodeContext
):
    rag = context.rag()

    # Get a specific LLM client (e.g. context.llm(profile="qa_profile"))
    qa_llm = context.llm(profile=llm_profile)

    result = await rag.answer(
        corpus_id=corpus_id,
        question=question,
        llm=qa_llm,
        style="detailed",
        with_citations=True,
        k=8,
    )

    await context.channel().send_text(result["answer"])
    return result


if __name__ == "__main__":
    from aethergraph.runner import run

    # Start sidecar so RAG/service contexts are wired
    url = start_server()
    print("AetherGraph sidecar server started at:", url)

    # --- Search demo ---
    r1 = run(
        rag_search_demo,
        inputs={"corpus_id": "demo-corpus-files", "query": "What is AetherGraph?", "k": 4},
    )
    print("Search demo result:", r1)

    # --- Retrieve demo ---
    r2 = run(
        rag_retrieve_demo,
        inputs={"corpus_id": "demo-corpus-files", "query": "Explain AetherGraph RAG facade.", "k": 3},
    )
    print("Retrieve demo result:", r2)

    # --- Answer demo ---
    r3 = run(
        rag_answer_demo,
        inputs={
            "corpus_id": "demo-corpus-files",
            "question": "Give me an overview of AetherGraph and its RAG features.",
            "style": "detailed",
        },
    )
    print("Answer demo result:", r3)

    # --- Answer with LLM profile demo ---
    r4 = run(
        rag_answer_with_profile,
        inputs={
            "corpus_id": "demo-corpus-files",
            "question": "How does RAG work in AetherGraph?",
            "llm_profile": "default",
        },
    )
    print("Answer with profile demo result:", r4)

