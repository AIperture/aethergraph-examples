# Prerequisite: Make sure you have LLM set up in your Aethergraph .env with the fields:
# AETHERGRAPH_LLM__ENABLED=true
# AETHERGRAPH_LLM__DEFAULT__PROVIDER=openai   # e.g., openai, anthropic, google, lmstudio, etc.
# AETHERGRAPH_LLM__DEFAULT__MODEL=gpt-4o-mini # e.g., gpt-4o-mini, claude-2, gemini-2.5-flash-lite, qwen/qwen2.5-vl-7b, etc.
# AETHERGRAPH_LLM__DEFAULT__API_KEY=          # your API key
#
# Also set up RAG index backend
# AETHERGRAPH_RAG__BACKEND=sqlite            # e.g., faiss and sqlite, etc.
# If you set up faiss, make sure to `pip install faiss` or `faiss-cpu` first. 
# Otherwise, the default sqlite backend will be used.

"""
In this example, we also ingest files from local paths into a RAG corpus.
The files to be ingested are located in the `docs/` folder next to this script.
"""

from aethergraph import graph_fn, NodeContext

from pathlib import Path

HERE = Path(__file__).resolve().parent  # folder containing rag.py; to make sure it works when run from elsewhere
DOCS = HERE / "docs"

@graph_fn(name="rag_ingest_files")
async def rag_ingest_files(
    corpus_id: str = "demo-corpus-files",
    txt_path: str = str(DOCS / "notes.txt"),
    md_path: str = str(DOCS / "guide.md"),
    pdf_path: str = str(DOCS / "paper.pdf"),
    *,
    context: NodeContext
):
    rag = context.rag()

    docs = [
        {
            "path": txt_path,
            "labels": {"format": "txt", "source": "local_files"}, # you can add custom labels
        },
        {
            "path": md_path,
            "labels": {"format": "md", "source": "local_files"},
        },
        {
            "path": pdf_path,
            "labels": {"format": "pdf", "source": "local_files"},
        },
    ]

    result = await rag.upsert_docs(corpus_id, docs) # this will create and ingest into the corpus

    await context.channel().send_text(
        f"[RAG ingest] corpus={corpus_id} added_docs={result['added']} chunks={result['chunks']}"
    )

    return result


@graph_fn(name="rag_ingest_inline")
async def rag_ingest_inline(
    corpus_id: str = "demo-corpus-inline",
    *,
    context: NodeContext
):
    rag = context.rag()

    docs = [
        {
            "title": "AetherGraph overview",
            "text": "AetherGraph is a Python-first framework for agentic graphs and R&D workflows.",
            "labels": {"topic": "aethergraph", "kind": "overview"},
        },
        {
            "title": "RAGFacade notes",
            "text": "The RAGFacade manages corpora, ingestion, vector indexing, and QA from context.rag().",
            "labels": {"topic": "rag", "kind": "notes"},
        },
    ]

    result = await rag.upsert_docs(corpus_id, docs)

    await context.channel().send_text(
        f"[RAG ingest] corpus={corpus_id} inline_docs={result['added']} chunks={result['chunks']}"
    )

    return result


if __name__ == "__main__":
    from aethergraph import start_server 
    from aethergraph.runner import run

    # Start sidecar so RAG is wired
    url = start_server()
    print("AetherGraph sidecar server started at:", url)

    # Ingest files
    result_files = run(rag_ingest_files, inputs={})
    print("Ingest files result:", result_files)
    print()

    # Ingest inline docs
    result_inline = run(rag_ingest_inline, inputs={})
    print("Ingest inline result:", result_inline)