# Prerequisite: general Aethergraph setup with LLM

"""
This script demonstrates how custom services can access the full NodeContext to use other AetherGraph services (LLM, artifacts, memory, channel, logger):

What it does:

Defines ExperimentTracker service that orchestrates multiple AetherGraph services:
    Uses self.ctx() to access the bound NodeContext
    Coordinates artifacts, memory, LLM, channel, and logger in a single workflow

The record_result() method performs a complete experiment tracking workflow:
    Artifacts: Saves detailed results as JSON (artifacts.save_json())
    LLM: Optionally summarizes long notes into 3 bullet points and saves as text
    Logger: Logs a structured event with metadata
    Memory: Records a compact searchable event with metrics and tags
    Channel: Conditionally notifies user when key metric exceeds threshold (e.g., score ≥ 0.90)

Demo agent (optimize_and_record) that:
    Simulates an optimization run with metrics (score, loss, time)
    Calls the tracker to persist results with notes
    Gets automatic LLM summarization and channel notification

Key concepts:
    Services accessing Context: Custom services can call self.ctx() to use LLM, artifacts, memory, etc.
    Service composition: Build higher-level services that orchestrate multiple lower-level services
    Complex workflows simplified: One service method handles persistence, summarization, logging, and notifications
    Conditional actions: Smart triggers (e.g., notify only when metrics are good)

This pattern is powerful for building domain-specific APIs (experiment tracking, data pipelines, monitoring) that leverage AetherGraph's full runtime capabilities.
"""

from aethergraph import graph_fn, NodeContext, Service
from aethergraph import start_server    
from aethergraph.runtime import register_context_service

from typing import Dict, Any, Optional, List

class ExperimentTracker(Service):
    def __init__(self, project: str):
        super().__init__()
        self.project = project

    async def record_result(
        self,
        *,
        run_name: str,
        metrics: Dict[str, float],
        notes: Optional[str] = None,
        tags: Optional[List[str]] = None,
        notify_on: float = 0.0,          # notify if a key metric >= threshold
        summarize_notes: bool = False,   # LLM summarize notes if present
        key_metric: str = "score",
    ) -> Dict[str, Any]:
        """
        Persist a result, log it, index it in memory, and optionally notify/summarize.
        Returns artifact URIs and a memory event id.
        """
        ctx = self.ctx()  # <- bound NodeContext (thanks to auto-bind)
        lg = ctx.logger()

        # 1) Write detailed result to artifact store
        payload = {
            "project": self.project,
            "run_name": run_name,
            "metrics": metrics,
            "notes": notes,
        }
        # You can use put_json/put_text/etc. depending on your artifact API
        result_uri = (await ctx.artifacts().save_json(payload, 
                                               suggested_uri=f"{self.project}/{run_name}/result.json")).uri

        # 2) Optional: summarize long notes with LLM and store
        summary_uri = None
        if summarize_notes and notes:
            llm = ctx.llm()   # default profile
            prompt = [
                {"role": "system", "content": "Summarize the following lab notes in 3 bullet points."},
                {"role": "user", "content": notes},
            ]
            summary_text, _usage = await llm.chat(prompt)
            summary_uri = (await ctx.artifacts().save_text(summary_text, 
                                                    suggested_uri=f"{self.project}/{run_name}/summary.txt")).uri

        # 3) Log a concise line
        lg.info("Recorded experiment result",
                extra={"project": self.project, "run": run_name, "metrics": metrics, "artifact": result_uri})

        # 4) Index a compact event in Memory for fast retrieval/aggregation
        evt = await ctx.memory().record(
            kind="exp_result",
            data={"project": self.project, "run": run_name, "metrics": metrics,
                  "result_uri": result_uri, "summary_uri": summary_uri},
            tags=(tags or []) + [self.project, "exp"],
            metrics=metrics,
        )

        # 5) Conditional channel notification (e.g., when key metric is impressive)
        if key_metric in metrics and metrics[key_metric] >= notify_on > 0:
            await ctx.channel().send_text(
                f"✅ {self.project}/{run_name} {key_metric}={metrics[key_metric]:.4f}  •  {result_uri}"
            )

        return {
            "result_uri": result_uri,
            "summary_uri": summary_uri,
            "event_id": evt["id"] if isinstance(evt, dict) and "id" in evt else evt,
        }
    
@graph_fn(name="optimize_and_record")
async def optimize_and_record(*, context: NodeContext):
    # ... your optimization happens here ...
    metrics = {"score": 0.9132, "loss": 34.8, "time_s": 127.3}
    notes = "Raised step size early, then cooled. Aberration term dominated at edges; fixed with aperture tweak."

    out = await context.xptracker().record_result(
        run_name="trial-042",
        metrics=metrics,
        notes=notes,
        tags=["loss", "trial"],
        notify_on=0.90,          # ping the channel when score >= 0.90
        summarize_notes=True,    # LLM summarize and store
        key_metric="score",
    )
    return out


if __name__ == "__main__":
    from aethergraph.runner import run 
    start_server()

    # Register once at startup
    register_context_service("xptracker", ExperimentTracker(project="lens_opt"))

    run(optimize_and_record)