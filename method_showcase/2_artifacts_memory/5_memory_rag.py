"""
Prerequisite: make sure you have at least llm set up in your Aethergraph .env. 
with the fields:

AETHERGRAPH_LLM__ENABLED=true
AETHERGRAPH_LLM__DEFAULT__PROVIDER=openai   # e.g., openai, anthropic, google, lmstudio, etc.
AETHERGRAPH_LLM__DEFAULT__MODEL=            # e.g., gpt-4o-mini, claude-2, gemini-2.5-flash-lite, qwen/qwen2.5-vl-7b, etc.
AETHERGRAPH_LLM__DEFAULT__EMBED_MODEL=      # e.g., text-embedding-3-small, text-embedding-004, etc. Optional if your use case needs embeddings.
AETHERGRAPH_LLM__DEFAULT__API_KEY=          # your API key 

and optionally 
AETHERGRAPH_RAG__BACKEND=faiss              # e.g., faiss and sqlite, etc. (faiss needs extra dependencies)
AETHERGRAPH_RAG__DIM=1536                   # e.g., 1536 for text embeddings

If you set up faiss, make sure to pip install faiss or faiss-cpu first. Otherwise, the default sqlite backend will be used.

"""

from aethergraph import graph_fn, NodeContext
from aethergraph import start_server

from aethergraph.runtime import set_rag_index_backend 


@graph_fn(name="memory_rag_bind_and_upsert_demo")
async def memory_rag_bind_and_upsert_demo(*, context: NodeContext):

    mem = context.memory()

    # 1) Create a project-scoped corpus (if no corpus_id inputs, creates a new unique corpus);
    # still returns the corpus_id to use for subsequent calls
    corpus_id = await mem.rag_bind(corpus_id="memory_demo", labels={"project":"Quickstart"}) # label is optional, only for metadata

    # 2) Upsert two inline docs (notes + pseudo SOP) -> 
    # The upserted docs will be saved persistently in storage, but can only be accessed via the same corpus_id
    await mem.rag_upsert(
        corpus_id=corpus_id,
        docs=[
            {"title":"Week 42 Notes", "text":"We tried achromatic design; near-IR shows better MTF at low NA."},
            {"title":"SOP: Optimize", "text":"Always sweep thickness and re-run tolerance before final export."},
        ],
        topic="docs.manual_upsert"
    )

    # 3) Search
    hits = await mem.rag_search(corpus_id=corpus_id, query="achromatic near-IR MTF low NA", k=4)
    short = [{"chunk_id":h["chunk_id"], "doc_id":h["doc_id"], "score":float(h["score"]),
              "snippet": (h["text"][:160] + "…") if len(h["text"])>160 else h["text"]} for h in hits]

    await context.channel().send_text(f"[rag] corpus={corpus_id} hits={len(short)} for 'achromatic near-IR'")
    return {"corpus_id": corpus_id, "hits": short}


@graph_fn(name="memory_rag_promote_events_demo")
async def memory_rag_promote_events_demo(*, context: NodeContext):
    
    mem = context.memory()
    # Bind to existing corpus (created in previous demo)
    corpus_id = await mem.rag_bind(corpus_id="memory_demo", labels={"project":"Promotions"})

    # Create a meaningful tool_result
    evt = await mem.write_result(
        topic="optimize.camera",
        inputs=[{"name":"config","kind":"json","value":{"stop":"f/2.0","NA":0.12}}],
        outputs=[{"name":"mtf50","kind":"number","value":0.41}],
        tags=["opt","result"],
        metrics={"sec": 3.8},
        message="Iter 12 improved sagittal MTF50 in near-IR",
        severity=3
    )

    # Promote recent significant events into RAG
    stats = await mem.rag_promote_events(
        corpus_id=corpus_id,
        where={"kinds":["tool_result"], "limit": 50},  # filter recent 50 tool_result events
        policy={"min_signal": 0.2} 
    )

    await context.channel().send_text(f"[rag] promoted into {corpus_id}: {stats}")

    return {"added_docs": stats.get("added",0), "chunks": stats.get("chunks",0)}

@graph_fn(name="memory_rag_search_and_answer_demo")
async def memory_rag_search_and_answer_demo(question: str = "Which iter improved MTF50", *, context: NodeContext):
    """
    """
    mem = context.memory()
    # Bind to existing corpus (created in previous demo)
    corpus_id = await mem.rag_bind(corpus_id="memory_demo", labels={"project":"Answering"}) # label is optional, only for metadata

    ans = await mem.rag_answer(corpus_id=corpus_id, question=question, style="concise", with_citations=True, k=6)

    # Nice channel output
    cites = ans.get("resolved_citations", [])[:3]
    cite_lines = [f"[{c['rank']}] {c.get('title','(untitled)')}: {c.get('snippet','')}" for c in cites]
    await context.channel().send_text(
        "[rag] " + (ans.get("answer","")[:400] + ("…" if len(ans.get('answer',''))>400 else "")) +
        ("\n\nTop citations:\n" + "\n".join(cite_lines) if cite_lines else "")
    )

    return {"answer": ans.get("answer",""), "citations": cites}



if __name__ == "__main__":

    url = start_server(port=0)

    set_rag_index_backend(backend="faiss")  # or "faiss" if you have faiss installed

    from aethergraph.runner import run_async
    import asyncio

    result1 = asyncio.run(run_async(memory_rag_bind_and_upsert_demo, inputs={}))
    print("Result 1:", result1)
    print()

    result2 = asyncio.run(run_async(memory_rag_promote_events_demo, inputs={}))
    print("Result 2:", result2)
    print()

    result3 = asyncio.run(run_async(memory_rag_search_and_answer_demo, inputs={}))
    print("Result 3:", result3)
    print()