from aethergraph import graph_fn, NodeContext
from aethergraph import start_server


@graph_fn(name="file_log_demo")
async def file_log_demo(*, context: NodeContext):
    """
    Simple demo: log a few messages to a file channel.
    """
    # Choose a file channel key; everything after "file:" is relative to the adapter's root
    log_chan = context.channel("file:runs/demo_run.log")

    await log_chan.send_text("=== Demo run started ===")
    await log_chan.send_text("Running some imaginary steps...")
    await log_chan.send_text("Step 1: loaded data ✅")
    await log_chan.send_text("Step 2: trained model ✅")
    await log_chan.send_text("Step 3: evaluated metrics ✅")
    await log_chan.send_text("=== Demo run finished successfully 🎉 ===")

    return {"status": "ok"}


if __name__ == "__main__":
    from aethergraph.runner import run

    # 1) Boot the sidecar
    url = start_server(port=8000)
    print("AetherGraph sidecar server started at:", url)

    result = run(file_log_demo, inputs={})
    print("Result:", result)
    print("Check your logs file: runs/demo_run.log (under workspace_root/channel_files)")
