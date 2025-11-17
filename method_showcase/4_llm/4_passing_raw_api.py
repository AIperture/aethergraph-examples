# # Prerequisite: Make sure you have LLM set up in your Aethergraph .env with the fields:
# AETHERGRAPH_LLM__ENABLED=true
# AETHERGRAPH_LLM__DEFAULT__PROVIDER=openai   # e.g., openai, anthropic, google, lmstudio, etc.
# AETHERGRAPH_LLM__DEFAULT__MODEL=gpt-4o-mini # this will be overridden in the example below
# AETHERGRAPH_LLM__DEFAULT__API_KEY=          # your API key

"""
Use context.llm().raw() for direct access to provider-specific LLM APIs. 
This lets you send custom payloads and call any endpoint, while reusing your configured base URL and authentication.
You handle the request format and response parsing yourself—ideal for new features or nonstandard APIs.
"""

from aethergraph import graph_fn, NodeContext
from aethergraph import start_server

@graph_fn(name="raw_openai_responses_demo")
async def raw_openai_responses_demo(*, context: NodeContext):
    openai = context.llm(profile="default")  # assumes base_url+api key set

    payload = {
        "model": "gpt-4o-mini",
        "input": [
            {"role": "system", "content": "You are concise."},
            {"role": "user", "content": "What is attention layer in neural networks?"}
        ],
        "max_output_tokens": 128,
        "temperature": 0.3,
    }

    data = await openai.raw(path="/responses", json=payload)  # base_url + /responses
    # data is the raw JSON; extract text per your needs:
    out = data.get("output")
    text = ""
    if isinstance(out, dict) and out.get("type") == "message":
        parts = (out.get("message") or out).get("content") or []
        text = "".join(p.get("text","") for p in parts if "text" in p)
    elif isinstance(out, list) and out:
        parts = out[0].get("content", [])
        text = "".join(p.get("text","") for p in parts if "text" in p)

    await context.channel().send_text(text or "<no text>")
    return {"raw_response": data, "extracted_text": text}

if __name__ == "__main__":
    from aethergraph.runner import run_async

    import asyncio
    url = start_server(port=0)

    asyncio.run(run_async(raw_openai_responses_demo, inputs={}))