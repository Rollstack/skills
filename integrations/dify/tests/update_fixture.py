"""Refresh tests/fixtures/mcp_tools.json from Rollstack's MCP server, which lists its tools without a key.

Run it when tests/test_live.py says the reference changed, then review the diff: the Dify tool files in tools/ and
the map in rollstack_client/operations.py must follow it. Run from integrations/dify: python tests/update_fixture.py
"""

from __future__ import annotations

import json
from pathlib import Path

import requests

MCP_URL = "https://api.rollstack.com/public/v1/mcp"
FIXTURE = Path(__file__).parent / "fixtures" / "mcp_tools.json"
KEPT = ("name", "title", "description", "inputSchema", "annotations")


def main() -> None:
    saved = json.loads(FIXTURE.read_text())
    headers = {"Accept": "application/json, text/event-stream"}
    listing = requests.post(MCP_URL, json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"}, headers=headers, timeout=60)
    listing.raise_for_status()
    live = {tool["name"]: tool for tool in listing.json()["result"]["tools"]}
    saved["tools"] = [{field: live[tool["name"]][field] for field in KEPT} for tool in saved["tools"]]
    FIXTURE.write_text(json.dumps(saved, indent=2, ensure_ascii=False) + "\n")
    print(f"Saved {len(saved['tools'])} tools to {FIXTURE}")


if __name__ == "__main__":
    main()
