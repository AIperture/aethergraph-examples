# rag_basic.py
from __future__ import annotations
from aethergraph import graph_fn, NodeContext, run
from aethergraph.server import start

start()  # wire services

@graph_fn(name="rag.basic", version="0.1.0")
async def rag_basic(*, context: NodeContext):
    """
    Minimal RAG demo via context.rag():
      1) Upsert one inline doc into a corpus
      2) Ask a question and return answer + resolved citations
    """
    rag = context.rag()

    corpus = "demo-corpus"
    # Ingest a tiny inline doc (you can also pass {"path": ".../paper.pdf"}). See later examples for more complex ingestion.
    await rag.upsert_docs(corpus, docs=[{
        "title": "MTF quick note",
        "labels": {"topic": "optics"},
        "text": "MTF50 is often used as an edge-acuity metric; higher is sharper, "
                "but acceptable ranges depend on sensor pitch and lens design."
    }])

    # Ask a question using the default LLM bound in RAGFacade
    qa = await rag.answer(corpus, "What is MTF50 and how is it used?", k=4)

    # qa = {"answer": "...", "citations": [...], "resolved_citations": [...], "usage": {...}}
    return {
        "answer": qa["answer"],
        "citations": qa.get("resolved_citations", qa.get("citations", []))
    }

if __name__ == "__main__":
    print(run(rag_basic, inputs={}))
