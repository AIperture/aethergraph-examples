# Prerequisite: None 

"""
This script demonstrates monitoring long-running external jobs with error handling and human-in-the-loop retry logic:

What it does:

Defines JobManagerService - a custom service that simulates external job execution:
    submit_job() - Submits a job and returns a job_id
    poll_status() - Polls job status (pending → running → succeeded/failed)
    reset_for_retry() - Creates a new job attempt with the same spec
    Error artifact creation: On failure, uses self.ctx() to save error logs as artifacts

long_job_monitor agent orchestrates the workflow:
    Submits job via service
    Polling loop with exponential backoff (1s → 2s → 4s → 8s max)
    Sends status updates to user via channel
    On success: Returns job results
    On failure:
        Shows error message + artifact URI
        Asks user "Retry or Abort?"
        Retry: Submits new job and continues polling
        Abort: Exits with failure status

Simulation behavior:
    First attempt: Job runs for 4 polls, then fails
    Retry attempt: Job succeeds
    Demonstrates the retry workflow pattern

Key concepts:
    Centralized job orchestration: Service abstracts external job systems (Kubernetes, cloud batch, etc.)
    Exponential backoff polling: Efficient status checking without hammering the service
    Human-in-the-loop error recovery: User decides whether to retry or give up
    Service-created artifacts: Services can participate in artifact/channel ecosystem via self.ctx()
    Production pattern: Separates agent logic from infrastructure details

This pattern is essential for workflows involving long-running compute jobs, batch processing, or any external system that requires monitoring and error recovery.
"""

from __future__ import annotations

import asyncio
import uuid
import pathlib
from dataclasses import dataclass, field
from typing import Any, Dict, Literal

from aethergraph import graph_fn, NodeContext
from aethergraph.core.runtime.base_service import Service
from aethergraph.core.runtime.runtime_services import register_context_service


# ---------------------------------------------------------
# 1) Job manager service (dummy implementation)
# ---------------------------------------------------------

JobStatus = Literal["pending", "running", "succeeded", "failed"]


@dataclass
class JobState:
    job_spec: str
    status: JobStatus = "pending"
    poll_count: int = 0
    max_polls_before_done: int = 4
    fail_first_attempt: bool = True
    error_message: str | None = None
    error_artifact_uri: str | None = None   # where we store error logs (if any)


@dataclass
class JobManagerService(Service):
    """
    Minimal in-memory job manager.

    In a real system this would talk to:
      - a cloud batch service,
      - a queue + worker fleet,
      - a Kubernetes job API, etc.

    Here we simulate:
      - submit_job() -> returns a job_id.
      - poll_status(job_id) -> returns changing status over time.
      - On failure, we also create an error artifact (if context is available).
    """

    jobs: Dict[str, JobState] = field(default_factory=dict)

    async def submit_job(self, job_spec: str) -> str:
        job_id = str(uuid.uuid4())
        self.jobs[job_id] = JobState(job_spec=job_spec)
        print(f"[JobManager] Submitted job {job_id} spec={job_spec!r}")
        return job_id

    async def poll_status(self, job_id: str) -> Dict[str, Any]:
        job = self.jobs.get(job_id)
        if job is None:
            # Unknown job; we can’t really log more than this
            return {"status": "failed", "error_message": "Unknown job_id", "error_artifact_uri": None}

        job.poll_count += 1

        # If the job is already terminal, just return its last status.
        if job.status in ("succeeded", "failed"):
            return {
                "status": job.status,
                "error_message": job.error_message,
                "error_artifact_uri": job.error_artifact_uri,
            }

        # Simulate progress: running for a few polls, then finish.
        if job.poll_count < job.max_polls_before_done:
            job.status = "running"
            return {"status": "running", "error_message": None, "error_artifact_uri": None}

        # On the final poll, decide success or failure.
        if job.fail_first_attempt:
            job.status = "failed"
            job.error_message = "Simulated job failure (first attempt)."
            # BONUS: record a failure artifact via NodeContext, if available.
            await self._record_failure_artifact(job_id, job)
        else:
            job.status = "succeeded"
            job.error_message = None

        return {
            "status": job.status,
            "error_message": job.error_message,
            "error_artifact_uri": job.error_artifact_uri,
        }

    async def reset_for_retry(self, job_id: str) -> str:
        """
        Simulate a "retry" by submitting a new job with the same spec,
        but configured to succeed.
        """
        old_job = self.jobs.get(job_id)
        if old_job is None:
            raise ValueError(f"Unknown job_id {job_id}")

        new_job_id = str(uuid.uuid4())
        self.jobs[new_job_id] = JobState(
            job_spec=old_job.job_spec,
            status="pending",
            poll_count=0,
            max_polls_before_done=old_job.max_polls_before_done,
            fail_first_attempt=False,  # succeed on retry
        )
        print(f"[JobManager] Retrying job {job_id} as new job {new_job_id}")
        return new_job_id

    async def _record_failure_artifact(self, job_id: str, job: JobState) -> None:
        """
        When a job fails, use self.ctx() to:
          - create a small error log file,
          - save it as an artifact,
          - optionally notify the user via channel().

        This shows how a service can participate in the artifact + channel ecosystem.
        """
        try:
            ctx: NodeContext | None = self.ctx()  # may raise or be None if no context
        except Exception:
            ctx = None

        if ctx is None:
            # Service is being used outside a node context; nothing we can do.
            return

        arts = ctx.artifacts()
        chan = ctx.channel()

        # 1) Write a tiny error log file
        out_path = pathlib.Path(f"./job_error_{job_id}.txt")
        content_lines = [
            f"Job ID: {job_id}",
            f"Job Spec: {job.job_spec}",
            f"Status: {job.status}",
            f"Error: {job.error_message or 'N/A'}",
        ]
        out_path.write_text("\n".join(content_lines), encoding="utf-8")

        # 2) Save as an artifact
        saved = await arts.save(
            str(out_path),
            kind="job_error",
            labels={"example": "long_job_monitor", "job_id": job_id},
            suggested_uri=f"./artifacts/job_error_{job_id}.txt",
            pin=True,
        )
        job.error_artifact_uri = saved.uri

        # 3) Let the user know we saved an error report (if channel is active)
        try:
            await chan.send_text(
                f"📝 Saved error report for job {job_id} as artifact:\n{saved.uri}"
            )
        except Exception:
            # Channel may not be configured (e.g., headless usage).
            pass


# ---------------------------------------------------------
# 2) Long job monitor graph_fn
# ---------------------------------------------------------

@graph_fn(name="long_job_monitor")
async def long_job_monitor(job_spec: str, *, context: NodeContext):
    """
    Monitor a long-running external job using JobManagerService. On failure,
    ask the user whether to retry or abort via channel().

    The JobManagerService may also create an error artifact and return its URI.
    """
    logger = context.logger()
    chan = context.channel()
    job_manager: JobManagerService = context.job_manager()

    logger.info("long_job_monitor started with job_spec=%r", job_spec)

    # Submit the job through the service
    job_id = await job_manager.submit_job(job_spec)
    await chan.send_text(f"🚀 Submitted job: {job_id}\nSpec: {job_spec}")

    # Simple polling with backoff
    base_delay = 1.0  # seconds
    max_delay = 8.0
    delay = base_delay

    while True:
        status_info = await job_manager.poll_status(job_id)
        status: JobStatus = status_info["status"]  # type: ignore[assignment]
        error_message = status_info.get("error_message")
        error_artifact_uri = status_info.get("error_artifact_uri")

        logger.info("Polled job %s -> status=%s", job_id, status)

        if status in ("running", "pending"):
            await chan.send_text(f"⏳ Job {job_id} is {status}. Polling again in {delay:.1f}s...")
            await asyncio.sleep(delay)
            # Exponential-ish backoff with a cap
            delay = min(max_delay, delay * 2.0)
            continue

        if status == "succeeded":
            await chan.send_text(f"✅ Job {job_id} completed successfully!")
            logger.info("Job %s succeeded", job_id)
            return {
                "job_id": job_id,
                "status": status,
                "error": None,
                "error_artifact_uri": None,
            }

        # status == "failed" or unknown
        msg = f"❌ Job {job_id} failed.\nError: {error_message or 'Unknown error'}"
        if error_artifact_uri:
            msg += f"\nError report artifact: {error_artifact_uri}"
        await chan.send_text(msg)

        # Ask the user whether to retry or abort
        response = await chan.ask_approval(
            "The job has failed. What would you like to do?",
            options=["Retry", "Abort"],
        )

        if response['choice'] == "Retry":
            # Reset via service, and start polling again on a new job_id
            new_job_id = await job_manager.reset_for_retry(job_id)
            await chan.send_text(f"🔁 Retrying job as new job ID: {new_job_id}")
            job_id = new_job_id
            delay = base_delay  # reset backoff for the new job
            continue
        else:
            await chan.send_text("🛑 Aborting job after failure as requested.")
            logger.info("Job %s aborted by user choice", job_id)
            return {
                "job_id": job_id,
                "status": "failed",
                "error": error_message,
                "error_artifact_uri": error_artifact_uri,
            }


# ---------------------------------------------------------
# 3) Demo run
# ---------------------------------------------------------

if __name__ == "__main__":
    from aethergraph import start_server
    from aethergraph.runner import run

    # Start sidecar for context services, LLM, channel, etc.
    url = start_server(port=0)
    print("AetherGraph sidecar server started at:", url)

    # Concrete instance and registration with the runtime.
    # (You can also register at import time; here we keep it explicit.)
    JOB_MANAGER = JobManagerService()
    register_context_service("job_manager", JOB_MANAGER)

    # Demo job spec: in a real setup this might be:
    #   - a training command,
    #   - a batch script path,
    #   - a container image + args, etc.
    job_spec = "train_model --dataset=demo --epochs=5"

    # Run the monitor. This will:
    #   - submit a job via JobManagerService,
    #   - poll until success or failure,
    #   - on first failure, save an error artifact and ask the user to Retry or Abort.
    result = run(long_job_monitor, inputs={"job_spec": job_spec})
    print("\n=== Long Job Monitor Result ===")
    print(result)
