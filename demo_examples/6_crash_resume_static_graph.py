# Prerequisite: None

"""
This script demonstrates crash recovery and resumption in static graphs using checkpoints:

What it does:

Defines a 3-node static graph (@graphify):
    fast_ok_1 - Quick computation (x * 3)
    resumable_2 - Long-running loop with periodic checkpoints (simulates heavy work)
    combine_3 - Combines results from both nodes

Checkpoint mechanism:
    resumable_2 saves its state {i, acc} to ./.ckpt/<run_id>__resumable_2.json every 8 iterations
    On restart with the same run_id, it loads the checkpoint and continues from where it left off

Crash simulation (two options):
    Set CRASH_AT=17 env var to crash at iteration 17
    Or manually press Ctrl+C during execution

Recovery demo:
    First run: Process crashes/interrupted → checkpoints saved
    Second run (same run_id): Resumes from checkpoint instead of starting over

Key concept: By reusing the same run_id, long-running nodes can recover their state and avoid repeating expensive work after crashes—critical for production workflows with hours-long computations.
"""

# Graph structure:
#
#           +------------------+
#           |   fast_ok_1      |  (fast)
#           |  x -> value      |
#           +---------+--------+
#                     |
#                     v
#                a.value
#
#           +------------------+
#           |  resumable_2     |  (slow, checkpointed)
#           |    n -> value    |
#           +---------+--------+
#                     |
#                     v
#                b.value
#
#                     a, b
#                     |
#                     v
#           +------------------+
#           |   combine_3      |  (depends on both)
#           |  (a + b) -> sum  |
#           +------------------+


from __future__ import annotations

import os
import sys
import json
import asyncio
import time
from typing import Dict, Any

from aethergraph import graphify, tool
from aethergraph.core.runtime.graph_runner import run_async
from aethergraph.core.runtime.node_context import NodeContext


# ---------- time helper (for nicer logs) ----------

def now() -> str:
    return f"{time.perf_counter():.3f}s"


# ---------- checkpoint helper ----------

def _ckpt_path(run_id: str, node_id: str) -> str:
    """
    Compute a checkpoint path for a given (run_id, node_id) pair.

    We store checkpoints under ./.ckpt so multiple runs can coexist:
      ./.ckpt/<run_id>__<node_id>.json
    """
    d = os.path.join(os.getcwd(), ".ckpt")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, f"{run_id}__{node_id}.json")


# ---------- tools (nodes) ----------

@tool(outputs=["value"])
async def fast_ok(x: int) -> Dict[str, Any]:
    """
    A small, fast node. This is intentionally trivial to show that
    re-running it is cheap compared to the slow, resumable node.
    """
    await asyncio.sleep(0.2)
    return {"value": x * 3}


@tool(outputs=["value"])
async def resumable_work(n: int = 40, *, context: NodeContext) -> Dict[str, Any]:
    """
    Long-running node with periodic checkpoints.

    It simulates work in a loop:
      - Uses (run_id, node_id) from NodeContext to find its checkpoint file.
      - On each checkpoint, saves {"i": current_iteration, "acc": accumulator}.
      - On restart (same run_id), it loads the checkpoint and continues
        instead of starting from i = 0.

    Crash demo:
      - If env var CRASH_AT is set to an integer k, the node will raise
        a RuntimeError when i == k, simulating a server crash.
      - Alternatively, you can just hit Ctrl+C in the terminal during the
        first run; any checkpoints written before the interrupt will be
        used on the next run.
    """
    run_id, node_id = context.run_id, context.node_id
    path = _ckpt_path(run_id, node_id)

    # Load checkpoint if it exists
    state = {"i": 0, "acc": 0}
    if os.path.exists(path):
        try:
            state = json.load(open(path, "r", encoding="utf-8"))
            print(f"[{now()}] {node_id} loaded ckpt:", state)
        except Exception:
            print(f"[{now()}] {node_id} ckpt unreadable; starting fresh")

    i, acc = int(state["i"]), int(state["acc"])

    # Optional crash-once for demo: set CRASH_AT to an iteration index
    crash_at_env = os.getenv("CRASH_AT")
    crash_at = int(crash_at_env) if crash_at_env and crash_at_env.isdigit() else None

    while i < n:
        # Pretend this loop is real work
        await asyncio.sleep(0.3)
        acc += i
        i += 1

        # Checkpoint every few steps (or at the end)
        if i % 8 == 0 or i == n:
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"i": i, "acc": acc}, f)
            print(f"[{now()}] {node_id} ckpt ->", {"i": i, "acc": acc})

        # Simulate crash at a chosen iteration
        if crash_at is not None and i == crash_at:
            print(f"[{now()}] {node_id} simulating crash at i={i}")
            raise RuntimeError("Simulated failure")

    # Optional cleanup once finished
    # os.remove(path)

    return {"value": acc}


@tool(outputs=["sum"])
async def combine(a: int, b: int) -> Dict[str, Any]:
    """
    Simple aggregation node that depends on both fast_ok and resumable_work.
    """
    await asyncio.sleep(0.05)
    return {"sum": a + b}


# ---------- graph definition ----------

@graphify(name="restart_minimal", inputs=["x", "n"], outputs=["sum"])
def restart_minimal(x: int = 7, n: int = 40):
    """
    Static graph that runs:
      - fast_ok_1   (fast)
      - resumable_2 (slow, checkpointed)
      - combine_3   (depends on both)
    """

    # a and b can run concurrently
    a = fast_ok(x=x, _id="fast_ok_1")
    b = resumable_work(n=n, _id="resumable_2")

    # combine_3 waits for both a and b to finish
    c = combine(a=a.value, b=b.value, _after=[a, b], _id="combine_3")

    return {"sum": c.sum}


# ---------- run helpers & main ----------

def _resolve_run_id() -> str:
    """
    Determine a run_id for this execution.

    Priority:
      1. First CLI argument, if present.
      2. RUN_ID environment variable.
      3. A fresh randomly generated run id.
    """
    if len(sys.argv) >= 2 and sys.argv[1].strip():
        return sys.argv[1].strip()

    rid = os.getenv("RUN_ID")
    if rid and rid.strip():
        return rid.strip()

    import uuid
    return f"run-{uuid.uuid4().hex[:8]}"


async def _main_async(run_id: str) -> None:
    tg = restart_minimal()
    out = await run_async(
        tg,
        inputs={"x": 7, "n": 40},
        run_id=run_id,
        max_concurrency=2,
    )
    print("FINAL (async):", out)


if __name__ == "__main__":
    run_id = _resolve_run_id()
    print("RUN_ID:", run_id)

    # --- How to use this demo --------------------------------------------
    #
    # 1) First run – simulate a crash inside resumable_2
    #
    #   Option A: use CRASH_AT to force a crash at a specific iteration
    #
    #     Choose a crash iteration, e.g. 17:
    #
    #       - PowerShell:
    #           $env:CRASH_AT = 17
    #       - bash/zsh:
    #           export CRASH_AT=17
    #
    #     Then run:
    #         python demo_restart_minimal.py
    #
    #     You should see:
    #       - resumable_2 creating checkpoints under ./.ckpt
    #       - a simulated crash when i == CRASH_AT
    #
    #   Option B: just interrupt manually with Ctrl+C
    #
    #     - Run:
    #         python demo_restart_minimal.py
    #     - Wait until you see a few checkpoint logs from resumable_2.
    #     - Press Ctrl+C in the terminal to stop the process.
    #
    #     Any checkpoints written before the interrupt will be reused
    #     on the next run with the same run_id.
    #
    #   In both options, note the printed RUN_ID (e.g. run-abc12345).
    #
    # 2) Second run – resume from checkpoint
    #
    #   - If you used CRASH_AT, unset it so the node won't crash again:
    #
    #       - PowerShell:
    #           Remove-Item Env:CRASH_AT
    #       - bash/zsh:
    #           unset CRASH_AT
    #
    #   - Re-run with the SAME run_id:
    #
    #         python demo_restart_minimal.py run-abc12345
    #
    #   Now resumable_2 will:
    #     - load its checkpoint from ./.ckpt/run-abc12345__resumable_2.json
    #     - continue from the saved (i, acc)
    #     - finish the remaining iterations instead of starting at 0
    #
    #   combine_3 then runs and prints the final sum.
    #
    # This shows that static graphs + node-local checkpoints let you
    # recover long-running work after crashes by re-running with the
    # same run_id.
    # ---------------------------------------------------------------------

    asyncio.run(_main_async(run_id))
