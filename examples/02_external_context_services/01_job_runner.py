# aethergraph/examples/services/job_runner.py
from __future__ import annotations
import asyncio, time, uuid, random
from typing import Dict, Any
from aethergraph.v3.core.runtime.base_service import Service
from aethergraph.v3.core.runtime.runtime_services import register_context_service
from aethergraph.server import start
from aethergraph import graph_fn, NodeContext

start()

class JobRunner(Service):
    """Submit long jobs and monitor their status (dummy orchestration)."""
    def __init__(self, queue_max: int = 2048):
        super().__init__()
        self._q: asyncio.Queue = asyncio.Queue(maxsize=queue_max)
        self._jobs: Dict[str, Dict[str, Any]] = {}
        self._loop_task: asyncio.Task | None = None
        self._closed = False

    async def start(self) -> None:
        # Actor loop: serializes state mutations
        self._loop_task = asyncio.create_task(self._scheduler_loop())

    async def close(self) -> None:
        self._closed = True
        await self._q.put(None)  # sentinel
        if self._loop_task:
            await self._loop_task

    async def _scheduler_loop(self):
        while not self._closed:
            item = await self._q.get()
            if item is None: break
            job_id = item["job_id"]
            spec = item["spec"]
            # Simulate picking a backend and launching
            self._jobs[job_id] = {"status": "queued", "spec": spec, "result_uri": None}
            asyncio.create_task(self._run_job(job_id))

    async def _run_job(self, job_id: str):
        # Dummy “work” (simulate run, success/fail)
        self._jobs[job_id]["status"] = "running"
        await asyncio.sleep(random.uniform(0.6, 1.6))
        ok = random.random() > 0.1
        self._jobs[job_id]["status"] = "succeeded" if ok else "failed"
        self._jobs[job_id]["result_uri"] = f"artifact://jobs/{job_id}/result.json" if ok else None

    # --------- Public API (edge) ----------
    async def submit(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        job_id = uuid.uuid4().hex[:12]
        try:
            self._q.put_nowait({"job_id": job_id, "spec": spec})
        except asyncio.QueueFull:
            raise RuntimeError("Job queue is full; retry later")
        return {"job_id": job_id}

    def status(self, job_id: str) -> Dict[str, Any]:
        return self._jobs.get(job_id, {"status": "unknown"})

    async def wait(self, job_id: str, poll_s: float = 0.5, timeout_s: float = 60.0) -> Dict[str, Any]:
        t0 = time.time()
        while time.time() - t0 < timeout_s:
            st = self.status(job_id)
            if st.get("status") in {"succeeded", "failed"}:
                return st
            await asyncio.sleep(poll_s)
        return {"status": "timeout"}

register_context_service("jobs", JobRunner())

@graph_fn(name="job_demo")
async def job_demo(*, context: NodeContext):
    spec = {"task": "simulate", "params": {"n": 3}}
    j = await context.jobs.submit(spec)
    await context.channel().send_text(f"Submitted job {j['job_id']}")
    st = await context.jobs.wait(j["job_id"], poll_s=0.25, timeout_s=5.0)
    await context.channel().send_text(f"Job {j['job_id']} -> {st['status']}")
    return {"job": j, "final": st}

if __name__ == "__main__":
    job_demo.sync()
