# Prerequisite: none

"""
This script demonstrates creating a custom service with shared mutable state (a materials database):

What it does:

Defines a custom Materials service that:
    Stores refractive index data: {material_name: {wavelength: refractive_index}}
    Provides sync reads via get_n() - fast, lock-free access (eventual consistency)
    Provides async writes via add_sample() - mutex-protected for thread safety
    Registers the service globally so agents can access it via context.materials()

Demo agent (materials_demo) that:
    Reads BK7 glass refractive index at 550nm wavelength    
    Adds a new data point for 600nm
    Sends the result to the channel

Key concepts:
    Custom services extend AetherGraph runtime with domain-specific capabilities
    Shared mutable state across multiple agents/graph runs
    Hybrid sync/async API: Fast reads without locks, safe writes with mutex protection
    Service registration: Makes context.materials() available to all agents

This pattern is useful for shared databases, caches, or any stateful resource that multiple agents need to access.
"""

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