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