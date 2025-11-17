# Prerequisite: Make sure you have transformers library installed (pip install transformers)

"""
This script demonstrates integrating HuggingFace models as a custom service with lazy loading and thread-safe execution:

What it does:

Defines HFText service that wraps HuggingFace transformers:
    Lazy initialization: Model loads only when first needed (via _ensure_loaded())
    Fallback mode: If transformers isn't installed, uses a stub implementation
    Thread-safe blocking calls: Uses run_blocking() to run CPU-heavy model operations without blocking the async event loop

Provides analyze() method for sentiment analysis:
    Takes a list of text strings
    Returns sentiment labels (POSITIVE/NEGATIVE) with confidence scores
    Runs model inference in a thread pool

Demo agent (hf_text_demo) that:
    Analyzes 3 sample texts
    Sends results to the channel (shows input + sentiment output)
    Returns all outputs

Key concepts:
    Heavy ML models as services: Share expensive models across multiple agents
    Lazy loading: Defer initialization until first use
    run_blocking(): Execute CPU-bound/synchronous code without blocking async agents
    Graceful degradation: Fallback stub when dependencies aren't available

This pattern is useful for integrating any CPU-intensive or synchronous library (ML models, image processing, scientific computing) into AetherGraph's async runtime.

"""

from aethergraph import graph_fn, NodeContext, Service 
from aethergraph import start_server
from aethergraph.runtime import register_context_service 

from typing import List, Any 

class HFText(Service):
    """
    Minimal HF wrapper with lazy load and fallback.
    Methods are async-friendly; heavy work can go via run_blocking().
    """
    def __init__(self, task: str = "sentiment-analysis", model: str | None = None):
        super().__init__()
        self._task = task
        self._model = model
        self._pipe = None

    async def _ensure_loaded(self):
        if self._pipe is not None:
            return
        try:
            from transformers import pipeline
        except Exception:
            self._pipe = "fallback"  # mark that we’ll use a stub
            return

        def _load():
            return pipeline(self._task, model=self._model) if self._model else pipeline(self._task)
        # load in thread to avoid blocking loop
        self._pipe = await self.run_blocking(_load)

    async def analyze(self, texts: List[str]) -> Any:
        await self._ensure_loaded()
        if self._pipe == "fallback":
            # simple stub: positive if length is even (demo only)
            return [{"label": ("POSITIVE" if len(t) % 2 == 0 else "NEGATIVE"), "score": 0.5} for t in texts]

        def _call():
            return self._pipe(texts)
        return await self.run_blocking(_call)
    
@graph_fn(name="hf_text_demo")
async def hf_text_demo(*, context: NodeContext):
    texts = ["AetherGraph is elegant.", "I am not sure about this.", "It just works!"]
    out = await context.hftext().analyze(texts)

    for i in range(len(texts)):
        await context.channel().send_text(f"\n \t Input: {texts[i]} \n \t Output: {out[i]}")
    return {"outputs": out}

if __name__ == "__main__":
    from aethergraph.runner import run 
    start_server()

    # start the server before registering services
    register_context_service("hftext", HFText())
    
    run(hf_text_demo)