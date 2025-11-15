"""
This demo shows how to extend AetherGraph with a custom service that
implements rate-limited API calls with retries using the token bucket algorithm.

Algorithm reference: https://en.wikipedia.org/wiki/Token_bucket
"""


from aethergraph import graph_fn, NodeContext, Service 
from aethergraph import start_server
from aethergraph.runtime import register_context_service

import asyncio, time, random
from typing import Dict, Any, Tuple 

class TokenBucket:
    def __init__(self, rate_per_sec: float, burst: int):
        self.rate = rate_per_sec
        self.burst = burst
        self.tokens = burst
        self.ts = time.time()

    def take(self, n=1) -> float:
        now = time.time()
        self.tokens = min(self.burst, self.tokens + (now - self.ts) * self.rate)
        self.ts = now
        if self.tokens >= n:
            self.tokens -= n
            return 0.0
        # need to wait
        short = n - self.tokens
        return short / self.rate
    
class ApiBroker(Service):
    """
    Centralizes calls to external APIs with tenant-aware rate limits and retries.
    Replace `_call_vendor` with real HTTP requests.
    """
    def __init__(self, rate_per_sec: float = 5.0, burst: int = 10):
        super().__init__()
        self._buckets: Dict[Tuple[str, str], TokenBucket] = {}
        self._rate = rate_per_sec
        self._burst = burst

    def _bucket(self, tenant: str, vendor: str) -> TokenBucket:
        key = (tenant, vendor)
        b = self._buckets.get(key)
        if b is None:
            b = TokenBucket(self._rate, self._burst)
            self._buckets[key] = b
        return b

    async def _call_vendor(self, vendor: str, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        # Dummy behavior: random transient errors
        await asyncio.sleep(0.05)
        if random.random() < 0.2:
            raise RuntimeError("Transient vendor error")
        return {"vendor": vendor, "endpoint": endpoint, "echo": payload}

    async def call(self, tenant: str, vendor: str, endpoint: str, payload: Dict[str, Any], *, retries: int = 3) -> Dict[str, Any]:
        # Rate limit per (tenant,vendor)
        b = self._bucket(tenant, vendor)
        delay = b.take(1)
        if delay > 0:
            await asyncio.sleep(delay)

        attempt, backoff = 0, 0.15
        while True:
            try:
                return await self._call_vendor(vendor, endpoint, payload)
            except Exception as e:
                attempt += 1
                if attempt > retries:
                    raise
                await asyncio.sleep(backoff)
                backoff *= 2.0

@graph_fn(name="api_broker_demo")
async def api_broker_demo(*, context: NodeContext):
    # Fire a few calls rapidly; broker will smooth via token bucket + retries
    outs = []
    for i in range(8):
        outs.append(await context.apibroker().call(
            tenant="acme", vendor="example", endpoint="/v1/search", payload={"q": f"item-{i}"}
        ))
    await context.channel().send_text(f"API broker called {len(outs)} times.")
    return {"count": len(outs), "sample": outs[:2]}

if __name__ == "__main__":
    from aethergraph.runner import run 
    start_server()

    # start the server before registering services
    register_context_service("apibroker", ApiBroker(rate_per_sec=3.0, burst=6))
    
    run(api_broker_demo)