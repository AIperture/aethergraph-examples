"""
Example: RL Agent – `graph_fn` as Policy

This example shows how to use an AetherGraph `@graph_fn` as a **policy**
inside an external RL loop.

High-level behavior
-------------------

- We define a tiny 1D gridworld environment in plain Python:
  - Positions: 0, 1, 2, 3, 4
  - Start at 0, goal at 4
  - Actions: "left" or "right"
  - Reward: -1 per step, +10 on reaching the goal, episode ends at goal or max steps.

- We define a policy `@graph_fn`:
  - Input: observation (current position).
  - Output: action ("left" or "right").
  - For demo:
    - The default logic is a simple heuristic (move toward the goal).
    - The comments show how you could swap in an LLM-based policy using `context.llm()`.

- We run an **outer loop** (regular Python) for one episode:
  - At each step:
    - Call `run(policy_graph, inputs={"observation": obs})` to get an action.
    - Apply the action in the environment.
    - Get (next_obs, reward, done) and log the transition.
  - At the end, we show the total reward and trajectory.

What this demonstrates
----------------------

- **Integrating AG graphs into external control loops**:
  - The environment is "just Python", but the policy is a first-class graph/agent.
  - You can swap in a different policy graph without touching the RL loop.

- **Using `graph_fn` as a policy: observation → action**:
  - The policy has access to `NodeContext`:
    - `context.llm()` for LLM-based decisions.
    - `context.logger()`, `context.channel()`, `context.memory()`, `context.artifacts()` etc.
  - That means a policy can:
    - Do multi-step reasoning (CoT / ReAct) before picking an action.
    - Call tools or domain simulators.
    - Log internal traces to memory/artifacts.

- **Trajectory logging and analysis (hook points)**:
  - In this simple example we log transitions in a Python list.
  - A real setup could:
    - Call another `@graph_fn` that writes trajectories to `artifacts` or `memory`.
    - Use AG graphs to analyze trajectories across many runs (e.g., summarization, clustering).

Why AetherGraph helps here
--------------------------

Compared to a "just Python" RL script:

- The policy function is now a **graph node** with context:
  - You can embed it inside larger orchestrations (evaluation jobs, hyperparameter sweeps, etc.).
  - You get consistent logging, LLM services, channels, and external services (prompt store, job manager).

- You can easily evolve from:
  - A deterministic one-step policy (as in this file),
  - To a **multi-step, tool-using, memory-aware policy** (CoT, ReAct, RAG) *without changing* the outer RL loop.

This file focuses on the minimal pattern: "AG graph as policy" in a small toy env,
with clear extension points for more complex agents.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Tuple

from aethergraph import graph_fn, NodeContext


# ---------------------------------------------------------------------------
# Tiny 1D gridworld environment (pure Python, no AG)
# ---------------------------------------------------------------------------

@dataclass
class GridWorld1D:
    """
    A tiny 1D gridworld:
      - States: positions 0, 1, 2, 3, 4
      - Start at 0, goal at 4
      - Actions: "left", "right"
      - Reward: -1 per step, +10 when reaching the goal
    """

    position: int = 0
    goal: int = 4
    max_steps: int = 20
    step_count: int = 0

    def reset(self) -> int:
        self.position = 0
        self.step_count = 0
        return self.position

    def step(self, action: str) -> Tuple[int, float, bool]:
        """
        Apply an action and return (next_obs, reward, done).
        """
        self.step_count += 1

        # Apply action
        if action == "left":
            self.position = max(0, self.position - 1)
        elif action == "right":
            self.position = min(self.goal, self.position + 1)
        else:
            # Invalid actions get a penalty and no movement
            penalty = -5.0
            return self.position, penalty, self._is_done()

        # Compute reward
        if self.position == self.goal:
            reward = 10.0
        else:
            reward = -1.0  # small negative per step to encourage fast solutions

        done = self._is_done()
        return self.position, reward, done

    def _is_done(self) -> bool:
        return self.position == self.goal or self.step_count >= self.max_steps


# ---------------------------------------------------------------------------
# Policy: `graph_fn` as an RL policy
# ---------------------------------------------------------------------------

@graph_fn(name="gridworld_policy")
async def gridworld_policy(observation: int, *, context: NodeContext):
    """
    A minimal policy implemented as an AetherGraph graph function.

    Inputs
    ------
    observation : int
        Current position on the line (0 to 4).

    Behavior
    --------
    - For demo purposes, uses a simple heuristic:
        * If position < goal → move "right"
        * Else                → move "left" (should only happen if we overshoot)
    - Shows where you could replace this with an LLM-based policy using `context.llm()`.

    Returns
    -------
    dict
        - "action": str, the chosen action ("left" or "right")
        - "debug": dict, any debug info you want to keep (here, just logs).
    """
    logger = context.logger()
    logger.info("gridworld_policy called with observation=%s", observation)

    goal_position = 4  # kept in sync with GridWorld1D.goal

    # --- Simple heuristic policy (pure Python) ---
    if observation < goal_position:
        action = "right"
    elif observation > goal_position:
        action = "left"
    else:
        # If we're exactly at the goal, no need to move. Just "stay" logically,
        # but we can pick any action (the env will treat goal as terminal anyway).
        action = "right"

    logger.info("Heuristic policy chose action=%s", action)

    # --- Optional: LLM-based policy (commented, for extension) ---
    # You could replace the heuristic above with something like:
    #
    # llm = context.llm()
    # prompt = (
    #     "You are controlling an agent on a 1D line from 0 to 4.\n"
    #     f"Current position: {observation}\n"
    #     "Goal: reach position 4 in as few steps as possible.\n"
    #     "You can move 'left' or 'right'.\n"
    #     "Just answer with one word: 'left' or 'right'."
    # )
    # action_text, _usage = await llm.chat(
    #     messages=[{"role": "system", "content": "You are a careful controller."},
    #               {"role": "user", "content": prompt}]
    # )
    # action = action_text.strip().lower()
    # logger.info("LLM policy chose action=%s", action)

    return {
        "action": action,
        "debug": {
            "observation": observation,
            "policy_type": "heuristic",  # or "llm" if you switch
        },
    }


# ---------------------------------------------------------------------------
# Optional: trajectory logger `graph_fn` (hook for artifacts/memory)
# ---------------------------------------------------------------------------

@graph_fn(name="log_trajectory")
async def log_trajectory(trajectory: List[Dict[str, float | int | str]], *, context: NodeContext):
    """
    Optional logger graph: demonstrate where you would use artifacts or memory
    to persist trajectories from RL runs.

    Parameters
    ----------
    trajectory : list of dict
        Each dict contains keys like:
        - "step"
        - "obs"
        - "action"
        - "reward"
        - "next_obs"

    Behavior
    --------
    - For now, this just logs the trajectory length.
    - In a real setup, you could:
        - Save it to artifacts as JSON/CSV.
        - Append to a memory timeline.
        - Trigger downstream analysis graphs.
    """
    logger = context.logger()
    logger.info("Logging trajectory with %d transitions", len(trajectory))

    # Pseudo-code for artifact / memory logging, adjust to your API:
    #
    # artifacts = context.artifacts()
    # artifacts.save_json("trajectories/gridworld_episode.json", trajectory)
    #
    # mem = context.memory()
    # mem.append_event(kind="rl_trajectory", data={"env": "gridworld_1d", "trajectory": trajectory})

    # For this minimal example we just return it.
    return {"trajectory_length": len(trajectory)}


# ---------------------------------------------------------------------------
# Outer RL loop (non-AG) that uses the graph policy
# ---------------------------------------------------------------------------

def run_episode_with_graph_policy(max_steps: int = 20) -> Dict[str, Any]:
    """
    Run a single episode of the GridWorld1D environment,
    using `gridworld_policy` (a graph_fn) as the policy.

    Returns a dict with:
    - "total_reward": float
    - "trajectory": list of transitions
    """
    env = GridWorld1D(max_steps=max_steps)
    obs = env.reset()

    trajectory: List[Dict[str, float | int | str]] = []
    total_reward = 0.0

    step = 0
    while True:
        step += 1

        # 1) Call the AetherGraph policy graph with the current observation
        policy_result = run(gridworld_policy, inputs={"observation": obs})
        action = policy_result["action"]

        # 2) Apply action in the environment
        next_obs, reward, done = env.step(action)
        total_reward += reward

        # 3) Log transition
        trajectory.append(
            {
                "step": step,
                "obs": obs,
                "action": action,
                "reward": reward,
                "next_obs": next_obs,
            }
        )

        obs = next_obs

        if done:
            break

    return {
        "total_reward": total_reward,
        "trajectory": trajectory,
    }


if __name__ == "__main__":
    from aethergraph import start_server
    from aethergraph.runner import run

    # 1) Boot the sidecar so context services (logger, llm, channel, etc.) are available.
    url = start_server(port=0, log_level="info") # to print out action steps
    print("AetherGraph sidecar server started at:", url)

    # 2) Run a single episode using the graph-based policy
    episode_result = run_episode_with_graph_policy(max_steps=20)
    print("Episode total reward:", episode_result["total_reward"])
    print("Episode trajectory:")
    for t in episode_result["trajectory"]:
        print(t)

    # 3) Optionally, log the trajectory via the `log_trajectory` graph.
    #    In a real workflow you might call this inside a training loop or a batch job.
    log_result = run(log_trajectory, inputs={"trajectory": episode_result["trajectory"]})
    print("Logged trajectory:", log_result)
