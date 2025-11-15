from aethergraph import graph_fn, NodeContext
from aethergraph import start_server 

from aethergraph.runtime import register_llm_client, set_rag_llm_client 

"""
Prerequisite:
You need to have API keys for the LLM providers you want to use (e.g., OpenAI, Anthropic, Google Gemini, LMStudio, etc.) 

To use different profile, we can set up them via .env variables like below:

AETHERGRAPH_LLM__MY_OPENAI__PROVIDER=openai
AETHERGRAPH_LLM__MY_OPENAI__MODEL=gpt-4o-mini
AETHERGRAPH_LLM__MY_OPENAI__TIMEOUT=60
AETHERGRAPH_LLM__MY_OPENAI__API_KEY=sk-...
AETHERGRAPH_LLM__MY_OPENAI__EMBED_MODEL=text-embedding-3-small # only needed if you use llm().embed() or rag()

And then we can use them in the graph function like:
    llm = context.llm(profile="my_openai")

Alternatively, we can set up the profiles in the code like below.
"""

# First we need to start the sidecar so context/services are wired
url = start_server(port=0)

openai_profile = "my_openai"
api_key = "sk-..." # replace with your OpenAI API key
open_ai_client = register_llm_client(
    profile=openai_profile,
    provider="openai",
    model="gpt-4o-mini",
    api_key=api_key,
)

lmstudio_profile = "my_lmstudio"
register_llm_client(
    profile=lmstudio_profile,
    provider="lmstudio",
    model="qwen/qwen2.5-vl-7b",
    base_url="http://localhost:1234/v1", # "v1" is required for LMStudio
)

anthropic_profile = "my_anthropic"
anthropic_api_key = "sk-..." # replace with your Anthropic API key
register_llm_client(
    profile=anthropic_profile,
    provider="anthropic",
    model="claude-3",
    api_key=anthropic_api_key,
)


gemini_profile = "my_gemini"
gemini_api_key = "AIzaSy..." # replace with your Google Gemini API key
register_llm_client(
    profile=gemini_profile,
    provider="google",
    model="gemini-2.5-flash-lite",
    api_key=gemini_api_key,
)

# Set up RAG LLM client for document retrieval. If not set, defaults to "default" profile. 
set_rag_llm_client(
    client=open_ai_client, 
)

# or we can create it via parameters:
set_rag_llm_client(
    provider="openai",
    model="gpt-4o-mini",
    embed_model="text-embedding-3-small",
    api_key=api_key,
)

@graph_fn(name="llm.multiple.profile.demo")
async def llm_multiple_profile_demo(profile: str, *,  context: NodeContext):
    llm_client = context.llm(profile=profile)

    messages = [
        {"role": "system", "content": "You are a concise and helpful assistant."},
        {
            "role": "user",
            "content": "In one sentence, what is an attention layer in neural networks?",
        },
    ]
    llm_text, llm_usage = await llm_client.chat(messages)

    # if you use GPT-5 model you can tune the reasoning style like below:
    # llm_text, llm_usage = await llm_client.chat(messages, reasoning_effort="low")

    return {
        "profile": profile,
        "answer": llm_text,
        "usage": llm_usage,
    }



if __name__ == "__main__":
    print("AetherGraph sidecar server started at:", url)

    # 2) Run the graph function once. You can also call `await llm_multiple_profile_demo(...)`
    #    directly inside another graph or an async context.
    from aethergraph.runner import run

    result = run(llm_multiple_profile_demo, inputs={"profile": openai_profile})
    print("llm_multiple_profile_demo result:", result)