from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass, asdict
from typing import Any, Dict

from aethergraph import graph_fn, NodeContext


# ---------------------------------------------------------
# Example: Channel Wizard – interactive experiment setup
# ---------------------------------------------------------
#
# GOAL
# ----
# Demonstrate a “wizard-style” interactive flow using:
#   - channel().send_text(...)
#   - channel().ask_text(...)
#   - channel().ask_approval(...)
# and save the resulting config as an artifact.
#
# KEY POINT ABOUT ask_approval(...)
# ----------------------------------
#   result = await chan.ask_approval("...", options=["A", "B"])
#
# Returns a dict:
#   {
#     "approved": bool,   # True if the first option is chosen, or a positive choice
#     "choice":   str     # the exact button label the user clicked, e.g. "A"
#   }
#
# In this example we mostly switch on `choice`, since we define
# explicit options like ["Yes", "No"] or ["Confirm", "Restart", "Cancel"].
# ---------------------------------------------------------


@dataclass
class ExperimentConfig:
    project: str
    steps: int
    advanced_mode: bool
    learning_rate: float | None = None
    debug_logging: bool = False


@graph_fn(name="channel_wizard")
async def channel_wizard(*, context: NodeContext):
    """
    Interactive “experiment setup wizard” driven entirely by channel().

    Flow:
      1) Ask for basic config (project name, number of steps).
      2) Ask whether to enable advanced mode.
         - If yes, ask for learning rate + debug flag.
      3) Show summary and ask for confirmation:
         ["Confirm", "Restart", "Cancel"].
      4) On confirm, save config as an artifact and return it.

    This example is meant as the canonical walkthrough of:
      - send_text
      - ask_text
      - ask_approval
    """
    logger = context.logger()
    chan = context.channel()
    artifacts = context.artifacts()

    logger.info("channel_wizard started")

    await chan.send_text("🧙 Welcome to the experiment setup wizard!")
    await chan.send_text("I’ll ask a few questions and then save a run configuration for you.")

    config: ExperimentConfig | None = None

    while True:
        # -------------------------------
        # Step 1 – basic config
        # -------------------------------
        await chan.send_text("Step 1/3 – Basic configuration")

        project = await chan.ask_text("Project name?")
        while not project.strip():
            await chan.send_text("Project name cannot be empty. Please try again.")
            project = await chan.ask_text("Project name?")

        # Ask for number of steps; validate as int
        while True:
            steps_str = await chan.ask_text("Number of steps (e.g. 10)?")
            steps_str = steps_str.strip()
            try:
                steps = int(steps_str)
                if steps <= 0:
                    raise ValueError("steps must be positive")
                break
            except Exception:
                await chan.send_text(
                    f"⚠️ Could not parse '{steps_str}' as a positive integer. Please try again."
                )

        # -------------------------------
        # Step 2 – advanced mode
        # -------------------------------
        await chan.send_text("Step 2/3 – Advanced options")

        adv_res = await chan.ask_approval(
            "Enable advanced mode?",
            options=["Yes", "No"],
        )
        # adv_res looks like: {"approved": bool, "choice": "Yes"|"No"}
        advanced = adv_res["choice"] == "Yes"

        learning_rate: float | None = None
        debug_logging = False

        if advanced:
            # Ask for learning rate
            while True:
                lr_str = await chan.ask_text("Learning rate (e.g. 0.001)?")
                lr_str = lr_str.strip()
                try:
                    learning_rate = float(lr_str)
                    if learning_rate <= 0:
                        raise ValueError("lr must be positive")
                    break
                except Exception:
                    await chan.send_text(
                        f"⚠️ Could not parse '{lr_str}' as a positive float. Please try again."
                    )

            # Ask for debug logging
            dbg_res = await chan.ask_approval(
                "Enable debug logging?",
                options=["Yes", "No"],
            )
            debug_logging = dbg_res["choice"] == "Yes"

        # Build candidate configuration
        config = ExperimentConfig(
            project=project.strip(),
            steps=steps,
            advanced_mode=advanced,
            learning_rate=learning_rate,
            debug_logging=debug_logging,
        )

        # -------------------------------
        # Step 3 – confirmation
        # -------------------------------
        await chan.send_text("Step 3/3 – Review configuration")

        pretty_config = json.dumps(asdict(config), indent=2)
        await chan.send_text(
            "Here is the configuration I’ve collected:\n"
            f"```json\n{pretty_config}\n```"
        )

        confirm_res = await chan.ask_approval(
            "Does this look correct?",
            options=["Confirm", "Restart", "Cancel"],
        )
        choice = confirm_res["choice"]

        if choice == "Confirm":
            await chan.send_text("✅ Great! I’ll save this configuration.")
            break  # exit the wizard loop with final config
        elif choice == "Restart":
            await chan.send_text("🔁 Okay, let’s start over from Step 1.")
            config = None
            continue
        else:  # "Cancel" or anything else
            await chan.send_text("🛑 Wizard cancelled. No configuration was saved.")
            logger.info("channel_wizard cancelled by user")
            return {
                "status": "cancelled",
                "config": None,
            }

    # -------------------------------
    # Finalize – save as artifact
    # -------------------------------
    assert config is not None, "Config should be set when we reach finalize step."

    config_dict: Dict[str, Any] = asdict(config)

    # Write to local JSON file
    path = pathlib.Path("./run_config.json")
    path.write_text(json.dumps(config_dict, indent=2), encoding="utf-8")

    # Save as an artifact (kind + labels help later search)
    saved = await artifacts.save(
        str(path),
        kind="run_config",
        labels={
            "project": config.project,
            "advanced_mode": str(config.advanced_mode).lower(),
        },
        suggested_uri=f"./configs/{config.project}_run_config.json",
        pin=True,
    )

    await chan.send_text(
        "📦 Configuration saved as an artifact.\n"
        f"URI: `{saved.uri}`\n\n"
        "You can now launch your run using this configuration."
    )

    logger.info("channel_wizard finished")

    return {
        "status": "ok",
        "config": config_dict,
        "artifact_uri": saved.uri,
    }


# ---------------------------------------------------------
# Demo runner
# ---------------------------------------------------------

if __name__ == "__main__":
    # Boot the sidecar so channel methods are available.
    # Default channel is console (stdin/stdout), but the same code works
    # for Slack, web UI, etc. depending on adapters.
    from aethergraph import start_server
    from aethergraph.runner import run
    url = start_server(port=0) # auto-select free port
    print("AetherGraph sidecar server started at:", url)

    result = run(channel_wizard, inputs={})
    print("\n=== Wizard Result ===")
    print(result)
