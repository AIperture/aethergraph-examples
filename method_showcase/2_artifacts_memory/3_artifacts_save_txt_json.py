from aethergraph import graph_fn, NodeContext
from aethergraph import start_server 

url = start_server(port=0)

@graph_fn(name="save_text_json")
async def save_text_json(*, context: NodeContext):
    
    arts = context.artifacts()
    
    sample_text = "This is a sample text to be saved as a JSON artifact."
    art_text = await arts.save_text(
        sample_text,
        suggested_uri = "./sample.txt"  # optional uri to be alias under /work/artifacts/
    )

    sample_json = {"message": "Hello, World!", "value": 42, "items": [1, 2, 3]}
    art_json = await arts.save_json(
        sample_json,
        suggested_uri = "./sample.json"  # optional uri to be alias under /work/artifacts/
    )

    print("Saved text artifact with location:", art_text.uri)
    print("Saved json artifact with location:", art_json.uri)
    return {"text_uri": art_text.uri, "json_uri": art_json.uri}


@graph_fn(name="retrieve_artifacts")
async def retrieve_artifacts_by_uri(text_uri, json_uri, *, context: NodeContext):
    arts = context.artifacts()
    
    # Retrieve previously saved artifacts by their URIs
    art_text = await arts.load_text(text_uri)
    art_json = await arts.load_json(json_uri)
    
    print("Retrieved text content:", art_text)
    print("Retrieved json content:", art_json)

    # Alternatively, you can find the local path and load manually
    # This is preferred if you need to work with files directly
    path_text = arts.to_local_path(text_uri)
    path_json = arts.to_local_path(json_uri)
    with open(path_text, "r") as f:
        art_text = f.read()
    with open(path_json, "r") as f:
        art_json = f.read()

    print("Loaded text from local file:", art_text)
    print("Loaded json from local file:", art_json)

    return {"text_content": art_text, "json_content": art_json}



if __name__ == "__main__":
    from aethergraph.runner import run_async
    import asyncio
    run_id = "tutorial_artifact_save" # fixed run_id for demo purposes so artifacts are stored consistently
    print("Running save_text_json...")
    uris = asyncio.run(run_async(save_text_json, run_id=run_id))

    print("Result:", uris)

    print("\nRunning retrieve_artifacts_by_uri...")
    contents = asyncio.run(
        run_async(retrieve_artifacts_by_uri, inputs=uris, run_id=run_id))
