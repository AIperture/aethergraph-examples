"""Prerequisite: pip install transformers"""

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