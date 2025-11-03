from aethergraph import graph_fn, NodeContext, run
from aethergraph.server import start
start()  # wire services

@graph_fn(name="memory_rag_bind_and_upsert_demo")
async def memory_rag_bind_and_upsert_demo(*, context: NodeContext):
    """
    What it does:
    - Demonstrates how to bind a project-scoped corpus, upsert documents into it, and perform a search.

    Demonstrates:
      - memory().rag_bind(scope=...)
      - memory().rag_upsert(corpus_id, docs=[...])
      - memory().rag_search(corpus_id, query, k=...)
    Returns:
      {
        "corpus_id": str,
        "hits": [
          {"chunk_id": str, "doc_id": str, "score": float, "snippet": str}
        ]
      }
    """
    mem = context.memory()

    # 1) Bind or create a project-scoped corpus
    corpus = await mem.rag_bind(scope="project", labels={"project":"Quickstart"})

    # 2) Upsert two inline docs (notes + pseudo SOP)
    await mem.rag_upsert(
        corpus_id=corpus,
        docs=[
            {"title":"Week 42 Notes", "text":"We tried achromatic design; near-IR shows better MTF at low NA."},
            {"title":"SOP: Optimize", "text":"Always sweep thickness and re-run tolerance before final export."},
        ],
        topic="docs.manual_upsert"
    )

    # 3) Search
    hits = await mem.rag_search(corpus_id=corpus, query="achromatic near-IR MTF low NA", k=4)
    short = [{"chunk_id":h["chunk_id"], "doc_id":h["doc_id"], "score":float(h["score"]),
              "snippet": (h["text"][:160] + "…") if len(h["text"])>160 else h["text"]} for h in hits]

    await context.channel().send_text(f"[rag] corpus={corpus} hits={len(short)} for 'achromatic near-IR'")
    return {"corpus_id": corpus, "hits": short}



# ---------------- DEMO 2: promote events → corpus --------------------------

@graph_fn(name="memory_rag_promote_events_demo")
async def memory_rag_promote_events_demo(*, context: NodeContext):
    """
    What it does:
    - Demonstrates how to write a tool_result event and promote recent significant events into a RAG corpus.

    Demonstrates:
      - memory().write_result(...)     (produce an event)
      - memory().rag_promote_events(corpus_id, where/policy)
    Returns:
      {"added_docs": int, "chunks": int}
    """
    mem = context.memory()
    corpus = await mem.rag_bind(scope="project", labels={"project":"Promotions"})

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
        corpus_id=corpus,
        where={"kinds":["tool_result"], "limit": 50},
        policy={"min_signal": 0.2, "dedup":"by_run_tool"}
    )

    await context.channel().send_text(f"[rag] promoted into {corpus}: {stats}")

    return {"added_docs": stats.get("added",0), "chunks": stats.get("chunks",0)}


# ---------------- DEMO 3: answer with citations ----------------------------

@graph_fn(name="memory_rag_search_and_answer_demo")
async def memory_rag_search_and_answer_demo(question: str = "What improved MTF50 at f/2?", *, context: NodeContext):
    """
    What it does:
    - Demonstrates how to use RAG to answer a question with citations.

    Demonstrates:
      - memory().rag_answer(corpus_id, question, style="concise", with_citations=True)
    Returns:
      {
        "answer": str,
        "citations": [{"rank": int, "title": str, "uri": str | None, "snippet": str}]
      }
    """
    mem = context.memory()
    corpus = await mem.rag_bind(scope="project",  labels={"project":"Answering"})

    ans = await mem.rag_answer(corpus_id=corpus, question=question, style="concise", with_citations=True, k=6)

    # Nice channel output
    cites = ans.get("resolved_citations", [])[:3]
    cite_lines = [f"[{c['rank']}] {c.get('title','(untitled)')}: {c.get('snippet','')}" for c in cites]
    await context.channel().send_text(
        "[rag] " + (ans.get("answer","")[:400] + ("…" if len(ans.get('answer',''))>400 else "")) +
        ("\n\nTop citations:\n" + "\n".join(cite_lines) if cite_lines else "")
    )

    return {"answer": ans.get("answer",""), "citations": cites}


if __name__ == "__main__":
    
  
    result = run(memory_rag_bind_and_upsert_demo, inputs={})
    print("Result:", result)

    result = run(memory_rag_promote_events_demo, inputs={})
    print("Result:", result)

    result = run(memory_rag_search_and_answer_demo, inputs={"question":"What is improved sagittal MTF50 in near-IR?"})
    print("Result:", result) 