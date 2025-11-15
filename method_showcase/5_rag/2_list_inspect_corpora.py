from aethergraph import graph_fn, NodeContext
from aethergraph import start_server 

# Prerequisite: ingest some corpora using rag_ingest_files and/or rag_ingest_inline from 1_ingest_files.py


@graph_fn(name="rag_list_corpora")
async def rag_list_corpora(*, context: NodeContext):
    rag = context.rag()
    corpora = await rag.list_corpora()

    if not corpora:
        await context.channel().send_text("No corpora found.")
        return {"corpora": []}

    lines = []
    for c in corpora:
        meta = c.get("meta", {})
        lines.append(f"- {c['corpus_id']}")

    await context.channel().send_text("Available corpora:\n" + "\n".join(lines))
    return {"corpora": corpora}



@graph_fn(name="rag_list_docs")
async def rag_list_docs(
    corpus_id: str,
    limit: int = 50,
    *,
    context: NodeContext
):
    rag = context.rag()
    docs = await rag.list_docs(corpus_id, limit=limit)

    if not docs:
        await context.channel().send_text(f"No docs in corpus '{corpus_id}'.")
        return {"docs": []}

    lines = []
    for d in docs:
        lines.append(f"- {d['doc_id']} :: {d.get('title','(untitled)')}")

    await context.channel().send_text(
        f"Docs in corpus '{corpus_id}' (limit={limit}):\n" + "\n".join(lines)
    )
    return {"docs": docs}


@graph_fn(name="rag_stats")
async def rag_stats(
    corpus_id: str,
    *,
    context: NodeContext
):
    rag = context.rag()
    s = await rag.stats(corpus_id)
    msg = (
        f"RAG corpus stats:\n"
        f"- corpus_id: {s['corpus_id']}\n"
        f"- docs:      {s['docs']}\n"
        f"- chunks:    {s['chunks']}"
    )
    await context.channel().send_text(msg)
    return s

@graph_fn(name="rag_delete_docs")
async def rag_delete_docs(
    corpus_id: str,
    doc_ids: list[str],
    *,
    context: NodeContext
):
    rag = context.rag()
    result = await rag.delete_docs(corpus_id, doc_ids)

    await context.channel().send_text(
        f"Deleted from '{corpus_id}': "
        f"{result['removed_docs']} docs, {result['removed_chunks']} chunks."
    )

    return result

@graph_fn(name="rag_reembed_docs")
async def rag_reembed_docs(
    corpus_id: str,
    doc_ids: list[str] | None = None,
    *,
    context: NodeContext
):
    rag = context.rag()
    result = await rag.reembed(
        corpus_id,
        doc_ids=doc_ids,
        batch=64,
    )

    await context.channel().send_text(
        f"Re-embedded {result['reembedded']} chunks "
        f"for corpus '{corpus_id}' with model {result.get('model')}."
    )
    return result


if __name__ == "__main__":
    from aethergraph.runner import run

    # List corpora
    result = run(rag_list_corpora, inputs={})
    print(f"List corpora result: {result}\n")

    # List docs in a corpus
    result = run(rag_list_docs, inputs={"corpus_id": "demo-corpus-files", "limit": 10})
    print(f"List docs result: {result}\n")


    # Get stats
    result = run(rag_stats, inputs={"corpus_id": "demo-corpus-files"})
    print(f"Corpus stats result: {result}\n")

    # Re-embed docs
    result = run(rag_reembed_docs, inputs={"corpus_id": "demo-corpus-files"})
    print(f"Re-embed docs result: {result}\n")