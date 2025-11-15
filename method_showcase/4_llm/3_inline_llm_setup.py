from aethergraph import graph_fn, NodeContext
from aethergraph import start_server 

"""
Prerequisite:
- You have an llm provider, model, and API key you want to use (e.g., OpenAI's gpt-4o-mini).

If you need to set up LLM clients inline (e.g., for testing or quick demos), you can do so directly in the context.llm() call by providing the necessary parameters.
Here's an example of how to set up an OpenAI LLM client inline within a graph function.

Note: this llm client setup is ephemeral and only lasts for the duration of the graph function execution.
"""

@graph_fn(name="inline_llm_setup_demo")
async def inline_llm_setup_demo(*, context: NodeContext):
    llm_client = context.llm(
        profile="runtime_openai",
        provider="openai",
        model="gpt-4o-mini",
        api_key="sk-...",  # replace with your OpenAI API key
        timeout=60.0,  # optional timeout in seconds
    )

    messages = [
        {"role": "system", "content": "You are a concise assistant."},
        {"role": "user", "content": "In one sentence, what is attention layer in neural networks?"},
    ]
    reply, usage = await llm_client.chat(messages)
    return {
        "answer": reply,
        "usage": usage,
    }

if __name__ == "__main__":
    # 1) Boot the sidecar so context/services are wired
    url = start_server(port=0)
    print("AetherGraph sidecar server started at:", url)

    # 2) Run the graph function once. You can also call `await inline_llm_setup_demo(...)`
    #    directly inside another graph or an async context.
    from aethergraph.runner import run

    result = run(inline_llm_setup_demo, inputs={})
    print("inline_llm_setup_demo result:", result)