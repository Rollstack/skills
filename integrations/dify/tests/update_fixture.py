"""Refresh tests/fixtures/mcp_tools.json from Rollstack's MCP server.

The server answers a request only when it carries a key, and lists for a key only the tools that key may call. So
this needs ROLLSTACK_API_KEY in the environment: a Rollstack API key with the scope of every tool the plugin has.
When the server leaves one of them out of its list, nothing is saved and the message names the scope that tool
needs. tests/test_live.py reads the list the same way, through current().

Run it when tests/test_live.py says the reference changed, then review the diff: the Dify tool files in tools/ and
the map in rollstack_client/operations.py must follow it. Run from integrations/dify: python tests/update_fixture.py
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import requests

MCP_URL = "https://api.rollstack.com/public/v1/mcp"
FIXTURE = Path(__file__).parent / "fixtures" / "mcp_tools.json"
KEY_VARIABLE = "ROLLSTACK_API_KEY"
KEPT = ("name", "title", "description", "inputSchema", "annotations")


class ReferenceUnavailable(Exception):
    """Why the server's list can't be read as the reference, in words for the maintainer. Never holds the key."""


def kept(tool: dict[str, Any]) -> dict[str, Any]:
    """What the fixture keeps of a tool the server lists: its definition, and the scopes a key needs to be shown it."""
    return {**{field: tool.get(field) for field in KEPT}, "_meta": {"securitySchemes": _schemes(tool)}}


def scopes(tools: list[dict[str, Any]]) -> list[str]:
    """The scopes the saved definitions of ``tools`` ask of a key, each once, in the order they first appear."""
    schemes = [scheme for tool in tools for scheme in _schemes(tool) or []]
    return list(dict.fromkeys(scope for scheme in schemes for scope in scheme.get("scopes") or []))


def key_to_set(saved: list[dict[str, Any]]) -> str:
    """The key that the server shows every saved tool to, in words."""
    return f"a Rollstack API key with the scopes {_in_words(scopes(saved))}"


def current(saved: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The saved tools as Rollstack's server lists them now, in the saved order.

    Raises ReferenceUnavailable when no key is set, when the server doesn't list its tools for it, or when its list
    leaves out a saved tool. Going on with the tools that are left would pass over the others without a word.
    """
    listed = _list_tools(key_to_set(saved))
    left_out = [tool for tool in saved if tool["name"] not in listed]
    if left_out:
        names = _in_words([f"{tool['name']} ({', '.join(scopes([tool]))})" for tool in left_out])
        raise ReferenceUnavailable(
            f"Rollstack's server left {names} out of the list it gave the key in {KEY_VARIABLE}. It lists for a key "
            f"only the tools that key may call, so use {key_to_set(saved)}. If the key has them, these tools were "
            "renamed or removed on Rollstack's side, or now take an admin's key: see "
            "https://docs.rollstack.com/api/mcp-server."
        )
    return [kept(listed[tool["name"]]) for tool in saved]


def _list_tools(wanted: str) -> dict[str, dict[str, Any]]:
    """The tools the server lists for the key in the environment, by name. ``wanted`` says which key to set."""
    api_key = os.environ.get(KEY_VARIABLE, "").strip()
    if not api_key:
        raise ReferenceUnavailable(f"Set {KEY_VARIABLE} to {wanted}: Rollstack's server lists its tools only for a key.")
    headers = {"Accept": "application/json, text/event-stream", "Authorization": f"Bearer {api_key}"}
    message = {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}
    try:
        listing = requests.post(MCP_URL, json=message, headers=headers, timeout=60)
    except requests.RequestException as error:
        raise ReferenceUnavailable(f"Could not reach Rollstack's server: {type(error).__name__}.") from None
    if listing.status_code != 200:
        raise ReferenceUnavailable(
            f"Rollstack's server did not list its tools for the key in {KEY_VARIABLE}: it answered "
            f"HTTP {listing.status_code}{_code(listing)}."
        )
    return {tool["name"]: tool for tool in listing.json()["result"]["tools"]}


def _schemes(tool: dict[str, Any]) -> list[dict[str, Any]] | None:
    """How the server says which scopes a tool needs: the ``securitySchemes`` of its ``_meta``."""
    return (tool.get("_meta") or {}).get("securitySchemes")


def _code(response: requests.Response) -> str:
    """Rollstack's error code in an answer, as " (code)", or nothing when the answer has none."""
    try:
        code = response.json().get("code")
    except (ValueError, AttributeError):
        return ""
    return f" ({code})" if isinstance(code, str) else ""


def _in_words(items: list[str]) -> str:
    return " and ".join([", ".join(items[:-1]), items[-1]] if len(items) > 1 else items)


def main() -> None:
    saved = json.loads(FIXTURE.read_text())
    try:
        saved["tools"] = current(saved["tools"])
    except ReferenceUnavailable as error:
        raise SystemExit(f"{error} Nothing was saved.") from None
    FIXTURE.write_text(json.dumps(saved, indent=2, ensure_ascii=False) + "\n")
    print(f"Saved {len(saved['tools'])} tools to {FIXTURE}")


if __name__ == "__main__":
    main()
