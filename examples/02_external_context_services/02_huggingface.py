# aethergraph/examples/services/hf_text.py
from __future__ import annotations
from typing import List, Any
import asyncio
from aethergraph.v3.core.runtime.base_service import Service
from aethergraph.v3.core.runtime.runtime_services import register_context_service
from aethergraph.server import start
from aethergraph import graph_fn, NodeContext

start()

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

register_context_service("hftext", HFText())

@graph_fn(name="hf_text_demo")
async def hf_text_demo(*, context: NodeContext):
    texts = ["AetherGraph is elegant.", "I am not sure about this.", "It just works!"]
    out = await context.hftext.analyze(texts)
    await context.channel().send_text(f"HF results: {out[:1]} ...")
    return {"outputs": out}

if __name__ == "__main__":
    hf_text_demo.sync()
