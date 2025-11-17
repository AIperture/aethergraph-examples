# Prerequisite: Make sure you have LLM set up in your Aethergraph .env with the fields:
# AETHERGRAPH_LLM__ENABLED=true
# AETHERGRAPH_LLM__DEFAULT__PROVIDER=openai   # e.g., openai, anthropic, google, lmstudio, etc.
# AETHERGRAPH_LLM__DEFAULT__MODEL=gpt-4o-mini # e.g., gpt-4o-mini, claude-2, gemini-2.5-flash-lite, qwen/qwen2.5-vl-7b, etc.
# AETHERGRAPH_LLM__DEFAULT__API_KEY=          # your API key

from aethergraph import graph_fn, NodeContext
from aethergraph import start_server

@graph_fn(name="llm.chat.basic")
async def llm_chat_basic(*, context: NodeContext):
    """
    Basic LLM chat example using context.llm().chat().
    """
    logger = context.logger()
    chan = context.channel()
    llm = context.llm()

    logger.info("llm_chat_basic started")

    messages = [
        {"role": "system", "content": "You are a concise and helpful assistant."},
        {
            "role": "user",
            "content": "In one sentence, what is an attention layer in neural networks?",
        },
    ]

    reply, usage = await llm.chat(messages)

    await chan.send_text(f"🤖 Assistant reply:\n{reply}\n\n🧾 Usage:\n{usage}")

    logger.info("llm_chat_basic finished")

    return {"answer": reply, "usage": usage}

if __name__ == "__main__":
    # 1) Boot the sidecar so context/services are wired
    url = start_server(port=0)
    print("AetherGraph sidecar server started at:", url)

    # 2) Run the graph function once. You can also call `await llm_chat_basic(...)`
    #    directly inside another graph or an async context.
    from aethergraph.runner import run

    result = run(llm_chat_basic, inputs={})
    print("llm_chat_basic result:", result)