from aethergraph import graph_fn, NodeContext
from aethergraph import start_server
from aethergraph.core.runtime.graph_runner import run_async 

"""
When no LLM profile is specified, context.llm() uses the "default" profile.
To set up the default profile you can set up the variables in .env file with the following format:

AETHERGRAPH_LLM__DEFAULT__PROVIDER=openai
AETHERGRAPH_LLM__DEFAULT__MODEL=gpt-4o-mini
AETHERGRAPH_LLM__DEFAULT__TIMEOUT=60
AETHERGRAPH_LLM__DEFAULT__API_KEY=sk-...
AETHERGRAPH_LLM__DEFAULT__EMBED_MODEL=text-embedding-3-small # only needed if you use llm().embed() or rag()

"""

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