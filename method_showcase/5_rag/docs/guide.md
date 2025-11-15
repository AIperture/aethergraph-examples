# AetherGraph RAG Guide

This document is part of the example corpus used by `context.rag()` demos.

## What is AetherGraph?

AetherGraph is a Python-first framework for building **agentic graphs**:
you define functions, tools, and static graphs that can be orchestrated
for complex R&D workflows.

Key properties:

- **Python-first**: graphs are defined in Python, not a separate DSL.
- **Runtime services**: `context.channel()`, `context.artifacts()`,
  `context.rag()`, `context.llm()`, etc.
- **Resumable execution**: graphs can pause and resume based on external events.

## RAGFacade Overview

The `RAGFacade` is exposed as `context.rag()` inside a node. It handles:

- Corpus management (`add_corpus`, `list_corpora`, `stats`).
- Document ingestion (`upsert_docs`) from:
  - Local files: `.txt`, `.md`, `.pdf`
  - Inline text payloads
- Chunking and embeddings via a `TextSplitter` and an embedding client.
- Retrieval (`search`, `retrieve`) and question answering (`answer`).

## Typical Usage in a Graph

```python
from aethergraph import graph_fn, NodeContext

@graph_fn(name="rag_answer_example")
async def rag_answer_example(
    corpus_id: str,
    question: str,
    *,
    context: NodeContext,
):
    rag = context.rag()
    res = await rag.answer(corpus_id, question, style="concise", with_citations=True)
    await context.channel().send_text(res["answer"])
    return res
