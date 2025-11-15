from aethergraph import graph_fn, NodeContext, tool
from aethergraph import start_server 


@tool(name="logger_usage_example_tool", outputs=["tool_logged"])
async def logger_usage_example_tool(*, context: NodeContext):
    """
    Use logger inside a tool to show node_id in logs.
    """
    log = context.logger()
    log.info(f"[tool] This is a log message from tool in node {context.node_id}")
    # another log after tool done will also show before exiting the tool in execution
    return {"tool_logged": True}
    

@graph_fn(name="logger_usage_example")
async def logger_usage_example(*, context: NodeContext):
    """
    Example demonstrating usage of context.logger() to log messages
    at different severity levels: info, warning, and error.
    """
    log = context.logger() # logger in graph_fn context will show node_id as __graph_inputs__

    log.info("logger_usage_example: Starting the logging demonstration.")
    log.info("This is an informational message.")

    log.warning("This is a warning message indicating something to be cautious about.")

    try:
        # Simulate an operation that raises an exception
        result = 10 / 0
    except Exception as e:
        log.error(f"An error occurred during computation: {e!r}")

    await logger_usage_example_tool() # logger in tool context will show actual node_id

    log.info("logger_usage_example: Logging demonstration completed.") 
    return {"status": "completed"}

if __name__ == "__main__":
    # Start sidecar so logger is wired
    url = start_server()
    print("AetherGraph sidecar server started at:", url)

    from aethergraph.runner import run

    result = run(logger_usage_example, inputs={})
    print("Result:", result)