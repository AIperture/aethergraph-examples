from aethergraph import graph_fn, NodeContext, Service  
from aethergraph import start_server
from aethergraph.runtime import register_context_service   

from typing import Dict

class Materials(Service):
    def __init__(self, table: Dict[str, Dict[float, float]]):
        super().__init__()
        self._table = table                 # shared mutable

    # FAST sync read (eventual consistency; no lock)
    def get_n(self, name: str, wl: float) -> float:
        d = self._table.get(name, {})
        if not d:
            raise KeyError(name)
        wl0 = min(d.keys(), key=lambda x: abs(x - wl))
        return float(d[wl0])

    # Write path: async + guarded with a mutex; no need to use _lock if you run graphs sequentially
    async def add_sample(self, name: str, wl: float, n: float) -> None:
        async with self._lock:
            self._table.setdefault(name, {})[float(wl)] = float(n)

@graph_fn(name="materials_demo")
async def materials_demo(*, context: NodeContext):
    n = context.materials().get_n(name="BK7", wl=550.0)             # sync OK
    await context.materials().add_sample("BK7", 600.0, 1.516)  # async write
    await context.channel().send_text(f"BK7@550nm={n:.6f}")
    return {"n_550nm": n}


if __name__ == "__main__":
    from aethergraph.runner import run 

    start_server()

    # start the server before registering services
    register_context_service("materials", Materials({"BK7": {550.0: 1.5168}}))
    
    run(materials_demo)