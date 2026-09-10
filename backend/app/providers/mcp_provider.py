"""MCP-backed SessionProvider.

Fetches the re:Invent 2026 catalog from the standalone `reinvent2026-mcp` server
(a separate, publishable package) over MCP stdio, instead of reading the bundled
file directly. This makes Re:Route AI a real *consumer* of the MCP server — the
same server anyone else can attach to Claude/Kiro/Cursor.

Enabled with REROUTE_USE_MCP=1. Configure the launch command with
REROUTE_MCP_CMD / REROUTE_MCP_ARGS (defaults to the installed console script
`reinvent2026-mcp`, falling back to `python -m reinvent2026_mcp.server`).

Implements the same SessionProvider interface as the demo/catalog providers, so
the agent, engine and UI are unchanged. On any connection error it fails soft:
`available` is False and the caller falls back to the bundled catalog.
"""
from __future__ import annotations

import json
import os
import shutil
from copy import deepcopy

from app.models import Session, SessionStatus
from app.providers.base import SessionProvider
from app.providers.enrich import enrich_session


def _default_command() -> tuple[str, list[str]]:
    cmd = os.getenv("REROUTE_MCP_CMD")
    args_env = os.getenv("REROUTE_MCP_ARGS")
    if cmd:
        return cmd, (args_env.split() if args_env else [])
    # Prefer the installed console script; else run the module.
    if shutil.which("reinvent2026-mcp"):
        return "reinvent2026-mcp", []
    return "python", ["-m", "reinvent2026_mcp.server"]


class McpSessionProvider(SessionProvider):
    """SessionProvider that proxies to the reinvent2026-mcp server over stdio."""

    def __init__(self) -> None:
        self.source = "mcp"
        self.available = False
        self.error: str | None = None
        self._client = None
        self._local: dict[str, Session] = {}  # cache for status mutations
        self._connect()

    # ------------------------------------------------------------------ #
    def _connect(self) -> None:
        try:
            from mcp import StdioServerParameters
            from mcp.client.stdio import stdio_client  # noqa: F401  (availability check)

            self._command, self._args = _default_command()
            # Build the child env. Allow running the server directly from the
            # sibling package folder (dev) via REROUTE_MCP_PYTHONPATH, so the
            # package need not be pip-installed to demo the integration.
            child_env = dict(os.environ)
            extra_pp = os.getenv("REROUTE_MCP_PYTHONPATH")
            if extra_pp:
                child_env["PYTHONPATH"] = extra_pp + os.pathsep + child_env.get("PYTHONPATH", "")
            self._params = StdioServerParameters(
                command=self._command, args=self._args, env=child_env
            )
            # Probe the server with a couple of retries — the first subprocess
            # spawn can be slow/cold and occasionally races the stdio handshake.
            last_exc = None
            for _ in range(3):
                try:
                    status = self._call("catalog_status", {})
                    if status and status.get("session_count", 0) >= 0:
                        self.available = True
                        break
                except Exception as e:  # noqa: BLE001
                    last_exc = e
            if not self.available and last_exc:
                raise last_exc
        except Exception as exc:  # pragma: no cover - env dependent
            self.error = f"{type(exc).__name__}: {exc}"
            self.available = False

    def _call(self, tool: str, args: dict) -> dict | None:
        """Call a tool on the MCP server (fresh short-lived stdio session).

        Always executed on a dedicated thread with its own event loop, so it works
        whether or not the caller (e.g. uvicorn) already has a running loop.
        """
        import concurrent.futures

        async def _run():
            from mcp import ClientSession
            from mcp.client.stdio import stdio_client

            async with stdio_client(self._params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool(tool, args)
                    for block in result.content:
                        text = getattr(block, "text", None)
                        if text:
                            try:
                                return json.loads(text)
                            except Exception:
                                return {"text": text}
                    return {}

        def _thread_target():
            import asyncio

            loop = asyncio.new_event_loop()
            try:
                asyncio.set_event_loop(loop)
                return loop.run_until_complete(_run())
            finally:
                loop.close()

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
            return ex.submit(_thread_target).result(timeout=60)

    def _to_session(self, d: dict) -> Session:
        # The MCP server returns fields matching our Session model closely.
        from datetime import datetime, timedelta

        allowed = set(Session.model_fields.keys())
        payload = {k: v for k, v in d.items() if k in allowed}
        payload.setdefault("id", d.get("id") or d.get("code") or "unknown")
        payload.setdefault("title", d.get("title", ""))
        # Defaults for required fields the MCP payload may omit.
        payload.setdefault("topic", "General")
        payload.setdefault("format", "Breakout")
        payload.setdefault("venue", "TBD")
        payload.setdefault("room", "")
        payload.setdefault("day", "")
        # Session requires start/end datetimes; derive sensible defaults if the
        # MCP payload omits them (unscheduled catalog entries).
        start = payload.get("start") or "2026-12-01T09:00:00"
        payload["start"] = start
        if not payload.get("end"):
            try:
                st = datetime.fromisoformat(str(start).replace("Z", ""))
                payload["end"] = (st + timedelta(minutes=60)).isoformat()
            except Exception:
                payload["end"] = start
        s = Session(**payload)
        return enrich_session(s)

    # ------------------------------------------------------------------ #
    # SessionProvider interface
    # ------------------------------------------------------------------ #
    def search_sessions(self, topics, day=None, venue=None) -> list[Session]:
        res = self._call("search_sessions", {
            "topics": topics or [], "day": day or "", "venue": venue or ""
        }) or {}
        sessions = [self._to_session(s) for s in res.get("sessions", [])]
        # Apply any local status overrides (e.g. demo marked a session full).
        for s in sessions:
            if s.id in self._local:
                s.status = self._local[s.id].status
        return sessions

    def semantic_search(self, query: str, top_k: int = 8) -> list[Session]:
        res = self._call("semantic_search", {"query": query, "top_k": top_k}) or {}
        return [self._to_session(s) for s in res.get("sessions", [])]

    def get_session(self, session_id: str) -> Session | None:
        res = self._call("get_session", {"session_id": session_id}) or {}
        if not res or res.get("error"):
            return None
        s = self._to_session(res)
        if s.id in self._local:
            s.status = self._local[s.id].status
        return deepcopy(s)

    def set_status(self, session_id: str, status) -> None:
        # Availability changes are local to this session (the catalog is read-only).
        s = self.get_session(session_id)
        if s:
            s.status = status if not isinstance(status, str) else SessionStatus(status)
            self._local[session_id] = s

    def status(self) -> dict:
        return {
            "available": self.available,
            "command": " ".join([getattr(self, "_command", ""), *getattr(self, "_args", [])]).strip(),
            "error": self.error,
        }
