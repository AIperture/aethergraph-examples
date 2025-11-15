# ---------------------------------------------------------
# Example: Optimization Loop with Artifacts & Memory
# ---------------------------------------------------------
#
# GOAL
# ----
# Show a small optimization loop (gradient descent on a toy function) that:
#   - logs metrics over time,
#   - saves checkpoints & metrics as artifacts,
#   - uses another agent to summarize the run with an LLM.
#
# WHAT THIS EXAMPLE SHOWS
# -----------------------
# 1. Long-running loop structured in a @graph_fn.
# 2. Using context.artifacts() to:
#      - save checkpoints during training,
#      - save a final metrics file,
#      - save an LLM-generated summary.
# 3. Using context.memory() to log per-step metrics.
# 4. Using context.llm() to "look at the training curve" and describe trends. Extendable to other analyses (e.g., plotting). 
#
# SCENARIO
# --------
# - Objective: minimize f(x, y) = (x - 3)^2 + (y + 1)^2.
# - Start from (x, y) = (0, 0).
# - Gradient descent with a fixed learning rate.
#
# In a real project this pattern scales to:
#   - complex simulations or training loops,
#   - multiple metrics and checkpoints,
#   - post-hoc analysis agents that read artifacts and generate reports.
# ---------------------------------------------------------

from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass
from typing import Dict, List, Any

from aethergraph import graph_fn, NodeContext


# ---------------------------------------------------------
# 1) Toy objective and optimizer
# ---------------------------------------------------------

@dataclass
class Params2D:
    x: float
    y: float


def simulate(params: Params2D) -> Dict[str, float]:
    """
    Toy objective:
        f(x, y) = (x - 3)^2 + (y + 1)^2

    Returns a dict with:
        - "loss"
        - "grad_x"
        - "grad_y"
    """
    dx = params.x - 3.0
    dy = params.y + 1.0
    loss = dx * dx + dy * dy
    grad_x = 2.0 * dx
    grad_y = 2.0 * dy
    return {"loss": loss, "grad_x": grad_x, "grad_y": grad_y}


def apply_gradient_step(params: Params2D, grads: Dict[str, float], lr: float) -> Params2D:
    """
    Basic gradient descent update:
        x <- x - lr * grad_x
        y <- y - lr * grad_y
    """
    return Params2D(
        x=params.x - lr * grads["grad_x"],
        y=params.y - lr * grads["grad_y"],
    )


# ---------------------------------------------------------
# 2) Optimization loop graph_fn
# ---------------------------------------------------------

@graph_fn(name="optimization_loop")
async def optimization_loop(
    *,
    context: NodeContext,
    num_steps: int = 30,
    learning_rate: float = 0.1,
    checkpoint_every: int = 5,
):
    """
    Run a simple gradient descent loop and log its trajectory.

    Behavior:
      - Starts from (x, y) = (0, 0).
      - For num_steps:
          * computes loss and gradients,
          * updates parameters,
          * appends (step, params, loss) to a metrics list,
          * logs each step to memory.
      - Every `checkpoint_every` steps:
          * writes a small checkpoint file,
          * saves it as an artifact (with loss as a metric).
      - At the end:
          * saves final parameters and metrics as artifacts,
          * returns basic summary info.

    Another graph_fn (`optimization_summary`) can then summarize the trajectory.
    """
    logger = context.logger()
    chan = context.channel()
    artifacts = context.artifacts()
    mem = context.memory()

    logger.info(
        "optimization_loop started with num_steps=%d, lr=%.4f",
        num_steps,
        learning_rate,
    )

    # Initial parameters
    params = Params2D(x=0.0, y=0.0)
    metrics: List[Dict[str, float]] = []

    await chan.send_text(
        f"🚀 Starting optimization demo: minimize (x-3)^2 + (y+1)^2\n"
        f"Initial params: x={params.x:.3f}, y={params.y:.3f}, "
        f"steps={num_steps}, lr={learning_rate:.3f}"
    )

    for step in range(1, num_steps + 1):
        results = simulate(params)
        loss = results["loss"]
        grad_x = results["grad_x"]
        grad_y = results["grad_y"]

        metrics.append(
            {
                "step": step,
                "x": params.x,
                "y": params.y,
                "loss": loss,
                "grad_x": grad_x,
                "grad_y": grad_y,
            }
        )

        # Per-step memory log: small, structured event
        await mem.record(
            kind="optimization_step",
            data={
                "step": step,
                "x": params.x,
                "y": params.y,
                "loss": loss,
            },
            metrics={"loss": float(loss)},
            tags=["optimization_loop"],
        )

        # Save checkpoint every `checkpoint_every` steps
        if step % checkpoint_every == 0 or step == num_steps:
            ckpt = {
                "step": step,
                "params": {"x": params.x, "y": params.y},
                "loss": loss,
            }
            ckpt_path = pathlib.Path(f"./checkpoint_step_{step}.json")
            ckpt_path.write_text(json.dumps(ckpt, indent=2), encoding="utf-8")

            # NOTE: we now pass `metrics={"loss": loss}` so the index can later
            # find the "best" checkpoint by minimum loss.
            saved_ckpt = await artifacts.save(
                str(ckpt_path),
                kind="optimization_checkpoint",
                labels={"example": "optimization_loop", "step": str(step)},
                metrics={"loss": float(loss)},
                suggested_uri=f"./checkpoints/step_{step}.json", # under workspaces/artifacts/
                pin=True,
            )
            logger.info("Saved checkpoint artifact at step %d: %s", step, saved_ckpt.uri)

        # Gradient step update
        params = apply_gradient_step(params, results, learning_rate)

    # After the loop: save final parameters & metrics as artifacts.
    final_params = {"x": params.x, "y": params.y}

    final_params_path = pathlib.Path("./final_params.json")
    final_params_path.write_text(json.dumps(final_params, indent=2), encoding="utf-8")
    saved_params = await artifacts.save(
        str(final_params_path),
        kind="optimization_params",
        labels={"example": "optimization_loop", "type": "final_params"},
        suggested_uri="./final_params.json", # under workspaces/artifacts/
        pin=True,
    )

    metrics_path = pathlib.Path("./metrics.json")
    metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    saved_metrics = await artifacts.save(
        str(metrics_path),
        kind="optimization_metrics",
        labels={"example": "optimization_loop", "type": "metrics"},
        suggested_uri="./metrics.json", # under workspaces/artifacts/
        pin=True,
    )

    await chan.send_text(
        "✅ Optimization finished.\n"
        f"Final params: x={params.x:.3f}, y={params.y:.3f}\n"
        f"Final loss: {metrics[-1]['loss']:.6f}\n"
        f"Params artifact: {saved_params.uri}\n"
        f"Metrics artifact: {saved_metrics.uri}"
    )

    logger.info("optimization_loop finished")

    return {
        "final_params": final_params,
        "final_loss": metrics[-1]["loss"],
        "metrics": metrics,
        "params_artifact_uri": saved_params.uri,
        "metrics_artifact_uri": saved_metrics.uri,
    }


# ---------------------------------------------------------
# 3) Summary agent: LLM-based trend description
# ---------------------------------------------------------

@graph_fn(name="optimization_summary")
async def optimization_summary(
    metrics: List[Dict[str, float]],
    *,
    context: NodeContext,
):
    """
    Summarize the optimization trajectory using an LLM.

    Inputs
    ------
    metrics : List[dict]
        A list of per-step records, each containing:
          - "step", "x", "y", "loss", ...

    Behavior
    --------
    - Computes simple stats (initial/final loss, best loss, etc.).
    - Optionally could reconstruct/augment metrics from MemoryFacade.
    - Uses ArtifactFacade.best(...) to find the best checkpoint by loss.
    - Builds a compact "trajectory sketch" from a subset of steps.
    - Asks the LLM to describe trends + recommendations.
    - Saves the summary as an artifact and returns key stats.
    """
    logger = context.logger()
    chan = context.channel()
    artifacts = context.artifacts()
    llm = context.llm()
    mem = context.memory()

    logger.info("optimization_summary started with %d metrics points", len(metrics))

    # OPTIONAL: if you didn't pass metrics in, you could reconstruct them
    # from memory:
    #
    # events = await mem.recent(kinds=["optimization_step"], limit=1000)
    # metrics_from_mem = []
    # for evt in events:
    #     if evt.text:
    #         try:
    #             metrics_from_mem.append(json.loads(evt.text))
    #         except Exception:
    #             pass
    # # Then use metrics_from_mem instead of `metrics`.
    #
    # For this example we keep `metrics` as the primary input and use memory
    # mainly as a logging mechanism in the loop.

    if not metrics:
        await chan.send_text("No metrics provided; nothing to summarize.")
        return {"summary": "No metrics."}

    losses = [m["loss"] for m in metrics]
    steps = [m["step"] for m in metrics]

    initial_loss = losses[0]
    final_loss = losses[-1]
    best_loss = min(losses)
    best_step = steps[losses.index(best_loss)]

    # Use ArtifactFacade.best(...) to find the best checkpoint artifact
    # by minimum loss within this run.
    best_ckpt_artifact = await artifacts.best(
        kind="optimization_checkpoint",
        metric="loss",
        mode="min",   # minimization objective
        scope="run",
        filters={"example": "optimization_loop"},
    )
    best_ckpt_uri = best_ckpt_artifact.uri if best_ckpt_artifact else None

    # Build a compact textual trajectory: sample a few steps for the prompt.
    max_points = 10
    if len(metrics) <= max_points:
        sampled = metrics
    else:
        indices = [
            int(round(i * (len(metrics) - 1) / (max_points - 1)))
            for i in range(max_points)
        ]
        sampled = [metrics[i] for i in indices]

    trajectory_lines = []
    for m in sampled:
        trajectory_lines.append(
            f"step={m['step']}, x={m['x']:.3f}, y={m['y']:.3f}, loss={m['loss']:.6f}"
        )
    trajectory_text = "\n".join(trajectory_lines)

    prompt = (
        "You are an expert at analyzing optimization and training runs.\n"
        "I will give you sampled points from an optimization trajectory.\n"
        "Each line has: step, x, y, loss.\n\n"
        f"Sampled trajectory:\n{trajectory_text}\n\n"
        "Initial loss: {initial_loss}\n"
        "Final loss: {final_loss}\n"
        "Best loss: {best_loss} at step {best_step}\n"
    ).format(
        initial_loss=initial_loss,
        final_loss=final_loss,
        best_loss=best_loss,
        best_step=best_step,
    )

    if best_ckpt_uri:
        prompt += (
            f"Best checkpoint artifact URI (by loss metric): {best_ckpt_uri}\n\n"
        )

    prompt += (
        "Please describe:\n"
        "1) Whether the loss is generally decreasing.\n"
        "2) If there appears to be a plateau or slowdown.\n"
        "3) Any notable patterns or anomalies.\n"
        "4) A short recommendation (1–2 sentences) for next steps "
        "(e.g., adjust learning rate, run longer, etc.)."
    )

    summary_text, _usage = await llm.chat(
        messages=[
            {"role": "system", "content": "You analyze optimization trajectories for researchers."},
            {"role": "user", "content": prompt},
        ]
    )

    # Save summary as an artifact (we could also use save_text, but keep it
    # consistent with the rest of the example).
    summary_path = pathlib.Path("./optimization_summary.txt")
    summary_path.write_text(summary_text, encoding="utf-8")

    saved_summary = await artifacts.save(
        str(summary_path),
        kind="optimization_summary",
        labels={"example": "optimization_loop", "type": "summary"},
        suggested_uri="./optimization_summary.txt", # under workspaces/artifacts/
        pin=True,
    )

    await chan.send_text(
        "📈 Optimization summary (LLM-generated):\n"
        f"{summary_text}\n\n"
        f"(Saved as artifact: {saved_summary.uri})"
        + (f"\nBest checkpoint artifact: {best_ckpt_uri}" if best_ckpt_uri else "")
    )

    logger.info("optimization_summary finished")

    return {
        "summary": summary_text,
        "summary_artifact_uri": saved_summary.uri,
        "initial_loss": initial_loss,
        "final_loss": final_loss,
        "best_loss": best_loss,
        "best_step": best_step,
        "best_checkpoint_artifact_uri": best_ckpt_uri,
    }


# ---------------------------------------------------------
# 4) Demo runner
# ---------------------------------------------------------

if __name__ == "__main__":
    from aethergraph import start_server
    from aethergraph.runner import run
    
    # Start sidecar for context services, LLM, channel, artifacts, etc.
    url = start_server(port=0)
    print("AetherGraph sidecar server started at:", url)

    # 1) Run the optimization loop to generate metrics & artifacts
    opt_result = run(
        optimization_loop,
        inputs={"num_steps": 30, "learning_rate": 0.1, "checkpoint_every": 5},
    )

    # 2) Feed its metrics into the summary agent
    summary_result = run(
        optimization_summary,
        inputs={"metrics": opt_result["metrics"]},
    )

    print("\n=== Final Params ===")
    print(opt_result["final_params"])
    print("Final loss:", opt_result["final_loss"])

    print("\n=== Summary (artifact) ===")
    print(summary_result["summary_artifact_uri"])
