# mcp_local_basic.py
from __future__ import annotations
import os, sys
from aethergraph import graph_fn, NodeContext, run
from aethergraph.server import start
from aethergraph.v3.services.mcp.service import MCPService
from aethergraph.v3.services.mcp.stdio_client import StdioMCPClient
from aethergraph.v3.core.runtime.runtime_services import set_mcp_service

# 1) Wire sidecar + register a local stdio MCP (no auth, no network)
start()
svc = MCPService()
svc.register("local", StdioMCPClient(cmd=[sys.executable, "-m", "aethergraph.v3.plugins.mcp.fs_server"]))
set_mcp_service(svc)

@graph_fn(name="mcp.local_list", version="0.1.0", inputs=["path"])
async def mcp_local_list(path: str, *, context: NodeContext):
    """
    Calls the local MCP 'fs_server' over stdio:
      - tools: listDir, readFile, writeFile, stat (your server may expose a subset)
    """
    # A) discover tools
    tools = await context.mcp("local").list_tools()
    # B) list directory
    listing = await context.mcp("local").call("listDir", {"path": path})
    return {"tools": tools[:5], "list_dir": listing}

@graph_fn(name="mcp.local_read", version="0.1.0", inputs=["path"])
async def mcp_local_read(path: str, *, context: NodeContext):
    out = await context.mcp("local").call("readFile", {"path": path})
    text = out.get("text") or out.get("content") or ""
    return {"path": path, "bytes": len(text), "preview": text[:200]}

if __name__ == "__main__":
    # Demo: list current directory, then (optionally) read this file if it exists
    print(run(mcp_local_list, inputs={"path": os.getcwd()}))
    sample = os.path.abspath(__file__)
    if os.path.exists(sample):
        print(run(mcp_local_read, inputs={"path": sample}))
