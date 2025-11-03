# llm_basic.py
from __future__ import annotations
from aethergraph import graph_fn, NodeContext, run
from aethergraph.server import start

# (Optional) start sidecar so context/services are wired
start()

@graph_fn(name="llm.basic", version="0.1.0")
async def llm_basic(*, context: NodeContext):
    """
    Minimal LLM demo:
      - Uses context.llm().chat() directly
      - API key is expected via env (e.g., OPENAI_API_KEY)
      - Or uncomment the lines below to set one in-process
    """
    # --- Optional: set/override key at runtime (uncomment to use) ---
    # context.llm_set_key(provider="openai", api_key="sk-...", profile="default")

    client = context.llm()  # defaults to profile="default"
    messages = [
        {"role": "system", "content": "You are concise and helpful."},
        {"role": "user", "content": "In one sentence, what is attention layer in neural networks?"},
    ]
    text, usage = await client.chat(messages, model="gpt-4o-mini", temperature=0.2)
    return {"answer": text, "usage": usage}

if __name__ == "__main__":
    print(run(llm_basic, inputs={}))
