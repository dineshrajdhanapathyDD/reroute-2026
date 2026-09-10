"""Launch the Re:Route AI backend with the reinvent2026-mcp integration enabled.

This sets the MCP env vars in-process (so they reach the app reliably), then
starts uvicorn. Sessions are served by the standalone reinvent2026-mcp server.

Usage:  python run_with_mcp.py
Optional env overrides: REROUTE_MCP_CMD, REROUTE_MCP_ARGS, REROUTE_MCP_PYTHONPATH
"""
import os
import shutil

os.environ.setdefault("REROUTE_USE_MCP", "1")

# Prefer the pip-installed console script (the recommended setup once you run
# `pip install reinvent2026-mcp`).
if shutil.which("reinvent2026-mcp") and not os.getenv("REROUTE_MCP_CMD"):
    os.environ["REROUTE_MCP_CMD"] = "reinvent2026-mcp"
else:
    # Dev fallback: run the module from the standalone package folder. The
    # package now lives OUTSIDE this project; override with REROUTE_MCP_PACKAGE
    # if you keep it elsewhere.
    os.environ.setdefault("REROUTE_MCP_CMD", "python")
    os.environ.setdefault("REROUTE_MCP_ARGS", "-m reinvent2026_mcp.server")
    _default_pkg = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "reinvent2026-mcp")
    )
    os.environ.setdefault(
        "REROUTE_MCP_PYTHONPATH", os.getenv("REROUTE_MCP_PACKAGE", _default_pkg)
    )

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.api:app", host="127.0.0.1", port=8000)
