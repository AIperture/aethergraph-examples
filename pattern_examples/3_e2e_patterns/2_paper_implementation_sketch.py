# demo_paper_to_code_run.py
#
# D.1 Paper → Code → Run → Image (minimal, stubbed)
#
# Flow:
#   1) Ask user to upload a text file (method description from a paper).
#   2) Extract method text and (stub) “parse” parameters.
#   3) Generate Python code based on those parameters and save it via artifacts.
#   4) Run the generated Python script (locally).
#   5) The script writes a result image (e.g., simple plot) to disk.
#   6) Load the image bytes and send back to the channel via send_file,
#      plus a short text summary via send_text.
#
# NOTE: This is a demo flow; parsing and code generation are stubs.
#       Running arbitrary code is dangerous – for real use, you’d want
#       proper sandboxing.

from __future__ import annotations

import asyncio
import sys
import textwrap
import subprocess
from typing import Dict, Any, List

from aethergraph import graphify, tool, NodeContext
from aethergraph.server.start import start
from aethergraph.core.tools import ask_files, send_text


# -------------------------------------------------------------------
# 1) Pick first uploaded file (URI + name)
# -------------------------------------------------------------------
@tool(outputs=["uri", "name"])
async def pick_first_file(
    *,
    context: NodeContext,
    files: List[Dict[str, Any]],
) -> Dict[str, Any]:
    if not files:
        raise RuntimeError("No files uploaded")

    f0 = files[0]
    await context.channel().send_text(f"Using uploaded file: {f0['name']}")
    return {"uri": f0["uri"], "name": f0["name"]}


# -------------------------------------------------------------------
# 2) Extract method text from uploaded file (assume plain text)
# -------------------------------------------------------------------
@tool(outputs=["text"])
async def extract_method_text(file_uri: str, *, context: NodeContext) -> Dict[str, Any]:
    """
    For this demo, we assume the file is plain text and load it
    through the artifacts service.
    """
    path = context.artifacts().to_local_path(file_uri)
    try:
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
    except Exception as e:
        text = f"[error reading file at {path}: {e}]"

    await context.channel().send_text("Loaded method text from file.")
    return {"text": text}


# -------------------------------------------------------------------
# 3) Stub “parameter extraction” from method text
# -------------------------------------------------------------------
@tool(outputs=["params"])
async def extract_params(method_text: str, *, context: NodeContext) -> Dict[str, Any]:
    """
    Stub: parse the method text and extract parameters.

    In a real implementation, you’d use an LLM (or regexes) to extract
    experimental parameters (e.g., num_points, slope, intercept, etc.).

    Here we just:
      - count words,
      - set a line slope/intercept,
      - choose number of points based on text length.
    """
    word_count = len(method_text.split())
    num_points = max(10, min(200, word_count // 5))

    params = {
        "slope": 0.5,
        "intercept": 1.0,
        "num_points": num_points,
    }

    await context.channel().send_text(
        f"Extracted parameters (stub): slope={params['slope']}, "
        f"intercept={params['intercept']}, num_points={params['num_points']}"
    )
    return {"params": params}


# -------------------------------------------------------------------
# 4) Generate Python code based on params and save via artifacts
# -------------------------------------------------------------------
@tool(outputs=["code_uri", "code_path"])
async def generate_and_save_code(params: Dict[str, Any], *, context: NodeContext) -> Dict[str, Any]:
    """
    Generate a small Python script that:
      - uses matplotlib to plot y = slope * x + intercept,
      - saves result.png in the same directory.

    Then save the script via artifacts and return both the artifact URI
    and local path.
    """
    slope = params.get("slope", 0.5)
    intercept = params.get("intercept", 1.0)
    num_points = params.get("num_points", 50)

    code = textwrap.dedent(f"""\
        # generated_experiment.py
        import matplotlib.pyplot as plt

        def run():
            slope = {slope}
            intercept = {intercept}
            num_points = {num_points}

            xs = list(range(num_points))
            ys = [slope * x + intercept for x in xs]

            plt.figure()
            plt.plot(xs, ys)
            plt.title("Generated experiment: y = slope * x + intercept")
            plt.xlabel("x")
            plt.ylabel("y")
            plt.tight_layout()
            plt.savefig("result.png")

        if __name__ == "__main__":
            run()
    """)

    artifacts = context.artifacts()
    # Use a temp local path and then save it as an artifact
    tmp_path = await artifacts.tmp_path(suffix="_generated_experiment.py")
    with open(tmp_path, "w", encoding="utf-8") as f:
        f.write(code)

    await context.channel().send_text("Generated Python code and saved to artifacts.")

    # Save into artifact store for traceability
    art = await artifacts.save(
        path=tmp_path,
        kind="generated",
        labels={"role": "generated_code"},
    )

    code_uri = getattr(art, "uri", None) or getattr(art, "path", None) or tmp_path
    code_path = artifacts.to_local_path(code_uri)
    return {"code_uri": code_uri, "code_path": code_path}


# -------------------------------------------------------------------
# 5) Run the generated Python script (locally)
# -------------------------------------------------------------------
@tool(outputs=["stdout", "returncode"])
async def run_generated_code(code_path: str, *, context: NodeContext) -> Dict[str, Any]:
    """
    Run the generated Python script in a subprocess.

    WARNING: running arbitrary code is dangerous.
    Only do this in trusted/local environments.
    """
    await context.channel().send_text(f"Running generated code: {code_path}")

    # Run with working directory = script directory so result.png ends up there
    import os
    code_dir = os.path.dirname(code_path) or "."

    proc = await asyncio.create_subprocess_exec(
        sys.executable,
        code_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        cwd=code_dir,
    )
    stdout_bytes, _ = await proc.communicate()
    stdout = stdout_bytes.decode("utf-8", errors="replace")
    rc = proc.returncode

    return {"stdout": stdout, "returncode": rc}


# -------------------------------------------------------------------
# 6) Load the generated result image and send via send_file
# -------------------------------------------------------------------
@tool(outputs=["ok"])
async def send_result_image_and_summary(
    code_path: str,
    stdout: str,
    returncode: int,
    source_file_name: str,
    *,
    context: NodeContext,
) -> Dict[str, Any]:
    """
    Assume the generated script wrote result.png in the same directory
    as code_path. Load that image, send it via send_file, and also send
    a text summary via send_text.
    """
    import os

    code_dir = os.path.dirname(code_path) or "."
    img_path = os.path.join(code_dir, "result.png")

    # Load image bytes (if present)
    try:
        with open(img_path, "rb") as f:
            img_bytes = f.read()
        has_image = True
    except FileNotFoundError:
        img_bytes = b""
        has_image = False

    # 1) Send result image if available
    if has_image and img_bytes:
        await context.channel().send_file(
            file_bytes=img_bytes,
            filename="result.png",
            title="Generated result image",
        )
    else:
        await context.channel().send_text("No result image was produced (result.png not found).")

    # 2) Send a short summary message
    summary = (
        "Paper → Code → Run summary:\n"
        f"- Source file: {source_file_name}\n"
        f"- Generated script path: {code_path}\n"
        f"- Exit code: {returncode}\n"
        "---\n"
        "Stdout preview:\n"
        f"{stdout[:500]}"
    )
    await context.channel().send_text(summary)

    return {"ok": True}


# -------------------------------------------------------------------
# 7) Static graph: paper_to_code_run_image
# -------------------------------------------------------------------
@graphify(
    name="paper_to_code_run_image",
    inputs=["channel"],   # optional: specific channel; None → default
    outputs=["code_uri", "stdout", "returncode"],
)
def paper_to_code_run_image(channel: str | None = None):
    # 1) Ask user to upload a method description (text file)
    files = ask_files(
        prompt="Please upload a text file containing the method section of your paper.",
        accept=["text/plain", ".txt", ".md"],
        multiple=False,
        channel=channel,
    )

    # 2) Pick the first file (URI + name)
    picked = pick_first_file(files=files.files, _after=files)

    # 3) Extract method text
    method = extract_method_text(file_uri=picked.uri, _after=picked)

    # 4) Extract parameters (stub)
    params = extract_params(method_text=method.text, _after=method)

    # 5) Generate and save code via artifacts
    code = generate_and_save_code(params=params.params, _after=params)

    # 6) Run the generated code
    run_res = run_generated_code(code_path=code.code_path, _after=code)

    # 7) Send result image + summary back to channel
    _send = send_result_image_and_summary(
        code_path=code.code_path,
        stdout=run_res.stdout,
        returncode=run_res.returncode,
        source_file_name=picked.name,
        _after=run_res,
    )

    # Graph outputs (artifacts + run info)
    return {
        "code_uri": code.code_uri,
        "stdout": run_res.stdout,
        "returncode": run_res.returncode,
    }


# -------------------------------------------------------------------
# 8) Optional runner
# -------------------------------------------------------------------
if __name__ == "__main__":
    from aethergraph.core.runtime.graph_runner import run_async
    from aethergraph.core.runtime.runtime_services import current_services

    # Boot sidecar so channel().*, ask_files, send_text, send_file work
    url = start(port=0, log_level="info")
    print("sidecar:", url)

    # For Slack, either:
    #   - configure a default Slack channel in settings, then use channel=None
    #   - or pass an explicit channel key, e.g.:
    #
    # SLACK_TEAM_ID = "T..."; SLACK_CHANNEL_ID = "C..."
    # channel_key = f"slack:team/{SLACK_TEAM_ID}:chan/{SLACK_CHANNEL_ID}"
    #
    # Here we just use the default channel:
    SLACK_TEAM_ID = "<your-slack-team-id>"
    SLACK_CHANNEL_ID = "<your-slack-channel-id>"
    channel_key = f"slack:team/{SLACK_TEAM_ID}:chan/{SLACK_CHANNEL_ID}"


    svc = current_services()
    svc.channels.set_default_channel_key(channel_key)

    tg = paper_to_code_run_image()
    out = asyncio.run(
        run_async(
            tg,
            inputs={"channel": channel_key},
            max_concurrency=2,
        )
    )
    print("FINAL:", out)
