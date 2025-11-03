# aethergraph/examples/services/materials.py
from __future__ import annotations
from typing import Dict
from aethergraph.v3.core.runtime.base_service import Service
from aethergraph.server import start
from aethergraph import graph_fn, NodeContext
from aethergraph.v3.core.runtime.runtime_services import register_context_service

start()

class Materials(Service):
    def __init__(self, table: Dict[str, Dict[float, float]]):
        super().__init__()
        self._table = table                 # shared mutable
        self._rw = None                     # set to AsyncRWLock if you want strong read consistency

    # FAST sync read (eventual consistency; no lock)
    def get_n(self, name: str, wl: float) -> float:
        d = self._table.get(name, {})
        if not d:
            raise KeyError(name)
        wl0 = min(d.keys(), key=lambda x: abs(x - wl))
        return float(d[wl0])

    # Write path: async + guarded with a mutex
    # @Service.critical(None)  # static access; or use self.critical() pattern
    async def add_sample(self, name: str, wl: float, n: float) -> None:
        async with self._lock:
            self._table.setdefault(name, {})[float(wl)] = float(n)

    # # Write path: async + guarded with a mutex
    # @Service.critical  # static access; or use self.critical() pattern
    # async def add_sample(self, name: str, wl: float, n: float) -> None:
    #     self._table.setdefault(name, {})[float(wl)] = float(n)

    # If you want strict read consistency under concurrency, add an async getter using RW-lock:
    # async def get_n_strict(self, name: str, wl: float) -> float:
    #     if self._rw is None:
    #         from aethergraph.v3.core.runtime.base_service import AsyncRWLock
    #         self._rw = AsyncRWLock()
    #     async with await self._rw.read():
    #         d = self._table.get(name, {})
    #         if not d: raise KeyError(name)
    #         wl0 = min(d.keys(), key=lambda x: abs(x - wl))
    #         return float(d[wl0])

register_context_service("materials", Materials({"BK7": {550.0: 1.5168}}))

@graph_fn(name="materials_demo")
async def materials_demo(*, context: NodeContext):
    n = context.materials.get_n(name="BK7", wl=550.0)             # sync OK
    await context.materials.add_sample("BK7", 600.0, 1.516)  # async write
    await context.channel().send_text(f"BK7@550nm={n:.6f}")
    return {"n_550nm": n}


if __name__ == "__main__":
    materials_demo.sync()