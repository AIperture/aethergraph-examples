"""
This script demonstrates using a @graph_fn as a Reinforcement Learning (RL) policy - showing how to integrate AetherGraph agents into external control loops:

What it does:

Defines a toy RL environment (GridWorld1D):

1D gridworld with positions 0-4
    Start at 0, goal at 4
    Actions: "left" or "right"
    Rewards: -1 per step, +10 at goal
    Episode ends at goal or after 20 steps

Implements policy as a @graph_fn (gridworld_policy):
    Input: Current position (observation)
    Output: Action ("left" or "right")
    Uses simple heuristic: if position < goal, move right; else move left
    Could easily swap to LLM-based policy (code commented out):

Outer RL loop (standard Python, not AG):
    Resets environment
    Loop:
        Calls run(gridworld_policy, inputs={"observation": obs}) to get action
        Executes action in environment
        Gets (next_obs, reward, done)
        Logs transition
    Returns total reward and trajectory

Optional trajectory logger (log_trajectory):
    Shows where you'd save trajectories to artifacts/memory
    Could trigger analysis graphs for multi-run evaluation

Key benefits of using AetherGraph for RL policies:

Policy has full NodeContext access:
    Can use LLM for reasoning (context.llm())
    Can call tools/simulators before choosing action
    Can log to memory/artifacts for analysis
    Can do multi-step reasoning (CoT/ReAct)

Easy evolution:
    Start with simple heuristic (as shown)
    Swap to LLM-based policy without changing RL loop
    Add memory/RAG for experience replay
    Use multi-agent coordination

Integration flexibility:
    Environment stays "just Python"
    Policy becomes a composable graph node
    Can embed into larger orchestrations (hyperparameter sweeps, evaluation jobs)

This pattern shows how to use AetherGraph agents in traditional RL/control scenarios while gaining access to LLMs, tools, memory, and all AG services.
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
