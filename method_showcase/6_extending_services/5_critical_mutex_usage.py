# Prerequisite: None 

"""
This script demonstrates thread-safe concurrent access to shared mutable state using the critical() decorator (mutex protection):

What it does:

Defines CounterService with shared mutable state:
    Maintains an internal counter _value
    Wraps the incr() method with self.critical() to make it thread-safe
    The critical() decorator ensures the entire method runs under the service's built-in mutex (self._lock)

The incr() method:
    Increments the counter by n
    Has an await asyncio.sleep(0) to simulate async operations that could cause race conditions
    Returns the updated value

Demo agent (counter_demo) that:
    Spawns 10 concurrent workers
    Each worker calls incr(1) 100 times
    Expected final value: 1000 (10 workers × 100 increments)
    Without the mutex, race conditions would cause lost updates

Key concepts:
    critical() decorator: Automatically wraps methods with mutex protection
    Race condition prevention: Multiple concurrent agents can safely modify shared state
    Service-wide mutex: self._lock is inherited from the Service base class
    Proof of correctness: Final value should always be exactly 1000, not some random lower number

This pattern is essential when multiple concurrent graph executions need to safely read/write shared state (counters, caches, queues, etc.).
"""


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