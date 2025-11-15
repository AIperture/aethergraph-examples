from aethergraph import graph_fn, NodeContext
from aethergraph.runtime import register_llm_client, set_rag_llm_client
from aethergraph import start_server

from aethergraph import graph_fn, NodeContext

"""
llm.chat() and llm.embed() cover most use cases using typical OpenAI format and parse the responses, 
but sometimes you need to go lower-level with provider-specific APIs.

Use context.llm().raw() when you need full control of a provider’s HTTP endpoint—e.g., 
trying a brand-new feature, sending multimodal blocks, or calling a nonstandard route—while still 
reusing your configured base URL, auth headers, and retry logic. You can pass either a path 
(joined to the client’s base_url) or a full url, plus json, params, and extra headers. 
By default it returns r.json(); set return_response=True to get the raw httpx.Response 
(useful for bytes/headers). This makes it ideal as an “escape hatch”: keep your normal 
profiles and credentials, but ship exactly the payload the provider expects—no adapters, 
no waiting on wrapper updates.

You’re responsible for the exact payload shape (messages, contents, blocks, etc.) that are sent to the API. 
Perfect for cutting-edge features or VLMs. However, you have to parse the raw response yourself.
"""

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