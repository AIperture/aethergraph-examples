# Prerequisite: Interactive channel setup (e.g., Slack, Telegram)
# See: https://aiperture.github.io/aethergraph-docs/channel-setup/introduction/ for channel setup instructions.
# See 4_channel_setup.py for example of channel setup with multiple channels and aliases.

"""
This script demonstrates comprehensive channel communication methods through an interactive portfolio monitoring demo:

What it does:

Text interaction:
    Sends greeting message
    Asks for stock symbol (ask_text)
    Checks for uploaded files (get_latest_uploads)
    Asks for buy/sell/hold decision (ask_approval)

File handling:
    Send chart image: Generates matplotlib price chart → sends as PNG via send_file()
    Send data export: Creates CSV file → zips it → sends ZIP via send_file()

Link buttons (send_buttons):
    Sends clickable buttons for "Download Data" and "View Dashboard"
    Uses Button class for interactive links

Streaming output (stream()):
    Live-updates a report with 15 lines
    Shows real-time progress (e.g., "update 1/15: pnl=-0.43%")
    Uses delta() for incremental updates, end() for completion

Key features demonstrated:

send_text() - Send messages
ask_text() - Get text input
ask_approval() - Multiple-choice buttons
send_file() - Send images/files
send_buttons() - Interactive link buttons
stream() - Live streaming updates
get_latest_uploads() - Retrieve uploaded files

This is a comprehensive walkthrough of all major channel methods in one interactive workflow.

NOTE: Accepting file uploads via ask_files() is commented out to avoid user confusion. Uncomment to enable explicit file upload requests.
"""
from aethergraph import graph_fn, NodeContext, tool
from aethergraph import start_server

from aethergraph.runtime import set_default_channel 
from aethergraph import Button # import Button class for link buttons in channels

import random
import io
import csv
import time
import zipfile
import asyncio
from typing import Dict, Any
import matplotlib.pyplot as plt

# Tools for easy plotting and file handling
# ----- send image ----- 
@tool(outputs=["filename"], name="ch_send_price_chart", version="0.1.0")
async def ch_send_price_chart(symbol: str, points: int = 60, *, context: NodeContext):
    # Simulate price series
    px = 100.0
    xs, ys = [], []
    for i in range(points):
        px *= (1 + random.uniform(-0.005, 0.006))
        xs.append(i)
        ys.append(px)

    # Plot to bytes
    fig, ax = plt.subplots()
    ax.plot(xs, ys)  # (frontend rule: no explicit colors/styles)
    ax.set_title(f"{symbol} — Last {points} ticks")
    ax.set_xlabel("t")
    ax.set_ylabel("price")
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    png_bytes = buf.getvalue()

    # send as file (Slack: uploads; Console: prints link-ish line)
    await context.channel().send_file(file_bytes=png_bytes, filename=f"{symbol}_chart.png", title=f"{symbol} price chart")
    return {"filename": f"{symbol}_chart.png"}

# ----- send CSV file and ZIP -----
@tool(outputs=["zip_name"], name="ch_send_export_zip", version="0.1.0")
async def ch_send_export_zip(symbol: str, rows: int = 50, *, context: NodeContext):
    # create csv in memory
    csv_buf = io.StringIO()
    writer = csv.writer(csv_buf)
    writer.writerow(["ts","symbol","price"])
    price = 100.0
    ts0 = int(time.time())
    for i in range(rows):
        price *= (1 + random.uniform(-0.003, 0.004))
        writer.writerow([ts0 - (rows - i)*5, symbol, f"{price:.4f}"])
    csv_bytes = csv_buf.getvalue().encode("utf-8")

    # Zip it
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"{symbol}_ticks.csv", csv_bytes)
    zbytes = zip_buf.getvalue()

    await context.channel().send_file(file_bytes=zbytes, filename=f"{symbol}_export.zip", title=f"{symbol} tick data export")
    return {"zip_name": f"{symbol}_export.zip"} 

# ----- link buttons (download, view online) -----
@tool(outputs=["ok"], name="ch_send_links", version="0.1.0")
async def ch_send_links(text: str, download_url: str, dashboard_url: str, *, context: NodeContext) -> Dict[str, Any]:
    buttons = [
        Button(label="Download Data", value=download_url),
        Button(label="View Dashboard", value=dashboard_url),
    ]
    await context.channel().send_buttons(text=text, buttons=buttons, meta={})
    return {"ok": True}

# ----- 7) streaming tokens (live report) -----
@tool(outputs=["final_text"], name="ch_stream_report", version="0.1.0")
async def ch_stream_report(lines: int = 10, delay_s: float = 0.2, *, context: NodeContext):
    chunks = []
    async with context.channel().stream() as s: 
        for i in range(lines):
            piece = f"• update {i+1}/{lines}: pnl={random.uniform(-1, 1):+.2f}%\n"
            chunks.append(piece)
            await s.delta(piece)
            await asyncio.sleep(delay_s)
        final = "".join(chunks)
        await s.end(full_text="Live report complete.\n" + final)
    return {"final_text": "Live report complete."} 

@graph_fn(name="portfolio_channel_demo")
async def portfolio_channel_demo(*, context: NodeContext):
    chan = context.channel()

    # Use the default channel to send a message
    await chan.send_text(f"👋 Welcome to Portfolio Monitor.")

    # Ask user for stock symbol to monitor
    sym = (await chan.ask_text(prompt="Which stock symbol would you like to monitor? (e.g., AAPL)", timeout_s=600)).strip().upper() or "AAPL"
    await chan.send_text(f"Great! Monitoring *{sym}* (simulated).")

    # If user update a file with the reply:
    uploads = await chan.get_latest_uploads(clear=True)
    if uploads:
        await chan.send_text(f"Received your uploaded file: {uploads[0]['name']}") 

    # Uncomment the following to enable ask for uploads explicitly -- disable for now as use might be confusing of what to upload
    # uploads_2 = await chan.ask_files(
    #     prompt=f"Please upload any relevant files for *{sym}* (e.g., transaction history).",
    #     accept=[".csv", ".xlsx"], # this only informs the frontend file picker, not enforced in AetherGraph backend
    #     multiple=False, # this only informs the frontend file picker, not enforced in AetherGraph backend
    #     timeout_s=600
    #  )
    
    # if uploads_2.get("files"):
    #     print(uploads_2)
    #     file_uri = uploads_2["files"][0].get("uri","")
    #     await chan.send_text(f"Received your uploaded files and stored at: {file_uri}")
    # else:
    #     await chan.send_text(f"No files were uploaded.")

    # Ask for actions 
    decision = (await chan.ask_approval(
        prompt=f"Do you want to buy, sell, or hold *{sym}*?", 
        options=["Buy", "Sell", "Hold"], timeout_s=600)).get("choice","Hold") 
    
    # Simulate action
    if decision == "Buy":
        await chan.send_text(f"Placing a buy order for *{sym}*... (simulated)")
    elif decision == "Sell":
        await chan.send_text(f"Placing a sell order for *{sym}*... (simulated)")
    else:
        await chan.send_text(f"Holding position on *{sym}*... (simulated)")

    # Send a price chart image (simulated)
    await chan.send_text(f"Generating price chart for *{sym}*...")
    await ch_send_price_chart(symbol=sym) 

    # Send CSV export as ZIP
    await chan.send_text(f"Preparing data export for *{sym}*...")
    await ch_send_export_zip(symbol=sym)

    # Send link buttons
    await chan.send_text(f"Here are some useful links for *{sym}*:")
    await ch_send_links(
        text=f"Choose an action for *{sym}*:",
        download_url=f"https://example.com/downloads/{sym}_data.csv",
        dashboard_url=f"https://example.com/dashboards/{sym}"
    )

    # Stream a live report
    await chan.send_text(f"Starting live report for *{sym}*:")
    await ch_stream_report(lines=15, delay_s=0.3)

    await chan.send_text("🏁 Portfolio monitoring session complete. Thank you!")
    return {"status": "done"}

if __name__ == "__main__":
    url = start_server(port=0) # start sidecar server at random port
    print("AetherGraph sidecar server started at:", url)

    SLACK_TEAM_ID = "<your-slack-team-id>"
    SLACK_CHANNEL_ID = "<your-slack-channel-id>"
    slack_channel_key = f"slack:team/{SLACK_TEAM_ID}:chan/{SLACK_CHANNEL_ID}"

    # Set default channel
    set_default_channel(slack_channel_key)


    from aethergraph.runner import run_async
    result = asyncio.run(run_async(portfolio_channel_demo))
    print("Result:", result)
