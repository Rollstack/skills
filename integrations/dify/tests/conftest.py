"""Shared test helpers: a stand-in for the HTTP session, and the plugin folder on the import path."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from requests.structures import CaseInsensitiveDict

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PLUGIN_ROOT.parents[1]

# The plugin runs with its folder as the working directory, so its modules import from there
sys.path.insert(0, str(PLUGIN_ROOT))


@pytest.fixture
def plugin_root(monkeypatch: pytest.MonkeyPatch) -> Path:
    """Run a test from the plugin folder, as Dify runs the plugin: its YAML files name each other from there."""
    monkeypatch.chdir(PLUGIN_ROOT)
    return PLUGIN_ROOT


class FakeResponse:
    """What the client reads of an HTTP response."""

    def __init__(
        self,
        status: int = 200,
        body: Any = None,
        *,
        headers: dict[str, str] | None = None,
        lines: list[bytes] | None = None,
        raw: bytes | None = None,
    ) -> None:
        self.status_code = status
        self.headers = CaseInsensitiveDict({"Content-Type": "application/json", **(headers or {})})
        self.content = raw if raw is not None else (b"" if body is None else json.dumps(body).encode())
        self._lines = lines or []
        self.closed = False

    def iter_lines(self):
        return iter(self._lines)

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *exc: object) -> bool:
        self.closed = True
        return False


class FakeSession:
    """Answers each request with the next scripted reply: a response, an exception to raise, or a function of the call."""

    def __init__(self, *replies: Any) -> None:
        self.headers: dict[str, str] = {}
        self.replies = list(replies)
        self.calls: list[SimpleNamespace] = []
        self.closed = False

    def close(self) -> None:
        self.closed = True

    def _next(self, method: str, url: str, **kwargs: Any) -> FakeResponse:
        call = SimpleNamespace(method=method, url=url, **kwargs)
        self.calls.append(call)
        assert self.replies, f"unexpected request: {method} {url}"
        reply = self.replies.pop(0)
        if callable(reply):
            reply = reply(call)
        if isinstance(reply, Exception):
            raise reply
        return reply

    def post(self, url: str, **kwargs: Any) -> FakeResponse:
        return self._next("POST", url, **kwargs)

    def get(self, url: str, **kwargs: Any) -> FakeResponse:
        return self._next("GET", url, **kwargs)


def rpc(result: dict[str, Any] | None = None, *, error: dict[str, Any] | None = None, status: int = 200, **kwargs: Any):
    """A JSON-RPC answer to whichever request it replies to."""

    def reply(call: SimpleNamespace) -> FakeResponse:
        body: dict[str, Any] = {"jsonrpc": "2.0", "id": call.json.get("id")}
        if error is not None:
            body["error"] = error
        else:
            body["result"] = result if result is not None else {}
        return FakeResponse(status, body, **kwargs)

    return reply


def tool_answer(value: Any, *, is_error: bool = False, structured: dict[str, Any] | None = None):
    """A tool's answer: ``value`` as its text block, JSON unless it is already text."""
    text = value if isinstance(value, str) else json.dumps(value)
    result: dict[str, Any] = {"content": [{"type": "text", "text": text}]}
    if is_error:
        result["isError"] = True
    if structured is not None:
        result["structuredContent"] = structured
    return rpc(result)
