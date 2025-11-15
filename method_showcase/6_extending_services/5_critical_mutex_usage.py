from aethergraph import graph_fn, NodeContext, Service
from aethergraph import start_server
from aethergraph.runtime import register_context_service

import asyncio 


# Variant: bind the decorator at runtime (clearer and supports inheritance):
class CounterService(Service):
    def __init__(self):
        super().__init__()
        self._value = 0
        # decorate incr with a bound `critical()` so `self` exists
        # This entire function is protected by the service-wide mutex
        self.incr = self.critical()(self.incr)  # type: ignore

    async def incr(self, n: int = 1) -> int:
        self._value += n
        await asyncio.sleep(0)
        return self._value
    

@graph_fn(name="counter_demo")
async def counter_demo(*, context: NodeContext):
    counter = context.counter() # get the CounterService: Need to register first 
    async def worker():
        for _ in range(100):
            await counter.incr(1)
    await asyncio.gather(*[worker() for _ in range(10)])

    print("Final value (should be 1000):", await counter.incr(0))
    return {"final_value": await counter.incr(0)}

if __name__ == "__main__":
    from aethergraph.runner import run 

    start_server()

    # register the service before running graphs
    register_context_service("counter", CounterService())

    run(counter_demo)