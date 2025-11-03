from __future__ import annotations
import pathlib
from aethergraph import graph_fn, NodeContext, run
from aethergraph.server import start

# Boot the sidecar so artifacts/index are available (in-memory or your configured backend)
url = start()
print("AetherGraph sidecar server started at:", url)

@graph_fn(name="artifacts_save_and_search")
async def artifacts_save_and_search(
    *, context: NodeContext,
    kind: str = "text",                      # keep this simple for the demo
):
    """
    Demonstrates ArtifactFacade.save(...) + ArtifactFacade.search(...)

    Returns a dict:
      {
        "saved_uri": str,            # URI of the saved artifact (content-addressed / pretty)
        "search_count": int,         # number of artifacts matching our search
        "pretty": str | None         # suggested pretty URI if you provided one
      }
    """
    # 1) Create a tiny local file
    out_path = pathlib.Path("./demo_artifact.txt")
    out_path.write_text("hello, artifact store 👋", encoding="utf-8")

    # 2) Save it as an artifact (and index it)
    arts = context.artifacts()
    saved = await arts.save(
        str(out_path),
        kind=kind,
        labels={"demo": "artifacts", "example": "save+search"},
        suggested_uri="./artifacts/hello.txt",   # optional: human-friendly link
        pin=True,                                # optional: keep it around
    )

    # 3) Search it back (scoped to current run by default)
    results = await arts.search(kind=kind, labels={"demo": "artifacts"})

    # 4) Tell the user & return structured outputs
    await context.channel().send_text(
        f"Saved artifact → uri={saved.uri}  (found {len(results)} matching artifacts in this run)"
    )
    return {
        "saved_uri": saved.uri,
        "search_count": len(results),
        "pretty": "artifacts/hello.txt",
    }

if __name__ == "__main__":
    result = run(artifacts_save_and_search, inputs={})
    print("Result:", result)
