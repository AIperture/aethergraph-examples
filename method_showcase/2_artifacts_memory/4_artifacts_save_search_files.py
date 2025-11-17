# Prerequisite: None

from aethergraph import graph_fn, NodeContext
from aethergraph import start_server 

url = start_server(port=0)

@graph_fn(name="save_image_file")
async def save_image_file(*, context: NodeContext):
    arts = context.artifacts()

    # create a sample image file (a small red dot PNG)
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(1, 1), dpi=10)
    ax.plot([0.5], [0.5], 'ro', markersize=10)
    ax.axis('off')
    tmp_path = await arts.tmp_path(suffix=".png") # create a temp file path; You can create your own file path as well
    plt.savefig(tmp_path, format='png', bbox_inches='tight', pad_inches=0)

    # Save the image artifact
    art_image = await arts.save(
        tmp_path,   # path to the image file
        kind="image",
        suggested_uri="./red_dot.png",
        labels={"experiment": "exp001", "step": "100"},  # Optional, can be used for search
        metrics={"val_loss": 0.55},    # Optional, can be used for search
        pin=True  # pin the artifact with a flag. Optional
    )

    print("Saved image artifact with location:", art_image.uri)
    return {"image_uri": art_image.uri}

@graph_fn(name="search_image_file")
async def search_image_file( *, context: NodeContext):
    arts = context.artifacts()

    # 1) Search for artifacts with the given label
    results = await arts.search(
        kind="image",
        scope="run",  # scope can be "run" (current run_id, default), "graph", "node", "all" (all storage artifacts)
    )
    
    # 2) Search with label filter: useful for finding artifacts from specific experiments
    results = await arts.search(
        kind="image",
        labels={"experiment": "exp001"},  # filter by label "experiment" == "exp001"
        scope="run",
    )

    # 3) Search with metric filter: useful for finding best/worst artifacts; You can add labels + metrics for finer search
    results = await arts.search(
        kind="image",
        metric="val_loss",   # filter artifacts that have "val_loss" metric
        mode="min",          # get artifacts with minimum val_loss
        scope="run",
    )
    # Alternatively, you can use arts.best() to get a single best artifact
    best_art = await arts.best(
        kind="image",
        metric="val_loss",
        mode="min",
        filters={"experiment": "exp001"},  # optional label filters
    )



    for art in results:
        print("Found artifact URI:", art.uri)
        print("Labels:", art.labels)
        print("Metrics:", art.metrics)

    # to load file content, you can use:
    # data = await arts.load_bytes(art.uri) -> return bytes
    # or path = arts.to_local_path(art.uri) -> return local file path and load manually

    return {"found_count": len(results), "artifacts": [art.uri for art in results]}

if __name__ == "__main__":
    from aethergraph.runner import run_async
    import asyncio
    run_id = "tutorial_artifact_save_search_files" # fixed run_id for demo purposes so artifacts are stored consistently
    print("Running save_image_file...")
    uri = asyncio.run(run_async(save_image_file, run_id=run_id))

    print("Running search_image_file...")
    search_results = asyncio.run(run_async(search_image_file, run_id=run_id))