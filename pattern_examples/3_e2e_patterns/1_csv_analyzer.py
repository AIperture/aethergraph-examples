from __future__ import annotations

import csv
from typing import Dict, Any, List

from aethergraph import graphify, tool, NodeContext
from aethergraph.server.start import start
from aethergraph.core.tools import ask_files, send_text


# -------------------------------------------------------------------
# 1) Helper tool: pick the first file's URI from ask_files
# -------------------------------------------------------------------
@tool(outputs=["uri"])
async def pick_first_file_uri(
    *,
    context: NodeContext,
    files: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Graphify can't index into lists directly (files[0]), so we expose
    the first file's URI as a separate node output.
    """
    if not files:
        raise RuntimeError("No files uploaded")

    f0 = files[0]
    await context.channel().send_text(f"Using file: {f0['name']}")
    return {"uri": f0["uri"]}


# -------------------------------------------------------------------
# 2) Tool: summarize a CSV file (rows, columns, first few headers)
# -------------------------------------------------------------------
@tool(outputs=["summary_text"])
async def summarize_csv(file_uri: str, *, context: NodeContext) -> Dict[str, Any]:
    """
    Load a CSV from the artifact store and return a small text summary.
    """
    # Convert artifact URI → local path using the artifacts service
    path = context.artifacts().to_local_path(file_uri)

    row_count = 0
    headers: List[str] = []

    await context.channel().send_text(f"Summarizing CSV at: {path}")

    try:
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            for i, row in enumerate(reader):
                if i == 0:
                    headers = row
                row_count += 1
    except Exception as e:
        return {"summary_text": f"Failed to read CSV at {path}: {e}"}

    col_count = len(headers)
    header_preview = ", ".join(headers[:5]) if headers else "(no header)"

    summary = (
        "CSV summary:\n"
        f"- Path: {path}\n"
        f"- Rows (including header): {row_count}\n"
        f"- Columns: {col_count}\n"
        f"- Header preview: {header_preview}"
    )
    return {"summary_text": summary}


# -------------------------------------------------------------------
# 3) Static graph:
#    1) ask_files         (user uploads CSV via Slack)
#    2) pick_first_file_uri
#    3) summarize_csv
#    4) send_text summary back to channel
# -------------------------------------------------------------------
@graphify(
    name="csv_upload_and_summary",
    inputs=["channel"],       # optional: target a specific channel (None → default)
    outputs=["summary"],
)
def csv_upload_and_summary(channel: str | None = None):
    # 1) Ask user to upload a CSV (dual-stage: suspends until files arrive)
    files = ask_files(
        prompt="Please upload a CSV file with your data.",
        # This is a hint for clients; AetherGraph does not enforce it
        accept=["text/csv", ".csv"],
        multiple=False,
        channel=channel,
    )
    # Note: if you used ask_files, you don't need get_latest_uploads here;
    # ask_files already wires the uploaded files into files.files.

    # 2) Pick the first file's URI via a dedicated node
    first = pick_first_file_uri(files=files.files, _after=files)

    # 3) Summarize the CSV
    summary = summarize_csv(file_uri=first.uri, _after=first)

    # 4) Send the summary back to the same channel
    send_text(text=summary.summary_text, channel=channel, _after=summary)

    # Graph output
    return {"summary": summary.summary_text}


# -------------------------------------------------------------------
# 4) Optional runner
# -------------------------------------------------------------------
if __name__ == "__main__":
    import asyncio
    from aethergraph.core.runtime.graph_runner import run_async
    from aethergraph.core.runtime.runtime_services import current_services

    # Boot sidecar so channel().* and ask_* tools are wired
    url = start(port=0, log_level="info")
    print("sidecar:", url)

    # For Slack, either:
    #   - configure a default Slack channel in settings, then use channel=None
    #   - or pass an explicit channel key here
    SLACK_TEAM_ID = "<your-slack-team-id>"
    SLACK_CHANNEL_ID = "<your-slack-channel-id>"
    channel_key = f"slack:team/{SLACK_TEAM_ID}:chan/{SLACK_CHANNEL_ID}"

    tg = csv_upload_and_summary()

    out = asyncio.run(
        run_async(
            tg,
            inputs={"channel": channel_key},
            max_concurrency=2,
        )
    )
    print("FINAL:", out)
