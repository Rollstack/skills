"""Checks against Rollstack's real server, which need no account. Off by default: ROLLSTACK_LIVE=1 turns them on.

They cover what a mocked answer can't: that the reference the plugin was written from is still what the server
lists, and that the client's requests are ones the server accepts, up to the point where it asks for a real key.
"""

from __future__ import annotations

import json
import os

import pytest
import requests

from conftest import PLUGIN_ROOT
from rollstack_client.mcp import MCP_URL, RollstackClient, RollstackError

pytestmark = pytest.mark.skipif(os.environ.get("ROLLSTACK_LIVE") != "1", reason="set ROLLSTACK_LIVE=1 to call Rollstack")

NOT_A_KEY = "rsk_not_a_real_key"


def test_the_reference_has_not_changed():
    saved = json.loads((PLUGIN_ROOT / "tests/fixtures/mcp_tools.json").read_text())["tools"]
    headers = {"Accept": "application/json, text/event-stream"}
    listing = requests.post(MCP_URL, json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"}, headers=headers, timeout=60)
    live = {tool["name"]: tool for tool in listing.json()["result"]["tools"]}

    for tool in saved:
        current = {field: live[tool["name"]].get(field) for field in tool}
        assert current == tool, f"{tool['name']} changed on Rollstack's server: run tests/update_fixture.py and review"


def test_a_tool_call_reaches_rollstack_and_a_wrong_key_is_refused():
    with pytest.raises(RollstackError) as raised:
        RollstackClient(NOT_A_KEY).call_tool("listReports", {"query": {"limit": 1}})

    assert (raised.value.status, raised.value.code) == (401, "api-key-invalid")


def test_the_key_check_refuses_a_wrong_key():
    with pytest.raises(RollstackError) as raised:
        RollstackClient(NOT_A_KEY).get_me()

    assert (raised.value.status, raised.value.code) == (401, "api-key-invalid")


def test_a_session_can_be_opened_if_the_server_ever_asks_for_one():
    client = RollstackClient(NOT_A_KEY)
    # The server lets anyone open a session; only tool calls need a key
    del client._session.headers["Authorization"]

    headers = client._open_session()

    assert headers["MCP-Protocol-Version"] == "2025-06-18"
