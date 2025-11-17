# Prerequisite: have api keys/base_urls for multiple LLM providers ready.
# You don't need to set them in .env, as we will register clients programmatically in this example.
# Note: the llm client setup method shown in this example is ephemeral and only lasts for the duration of the graph function execution.

from aethergraph import graph_fn, NodeContext
from aethergraph import start_server 

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