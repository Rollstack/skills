"""Refresh the reference the plugin's tools are generated from, then generate them again.

Two files, both in tests/fixtures:

- mcp_tools.json: every tool Rollstack's MCP server lists, as it lists it. The server answers a request only when it
  carries a key, and lists for a key only the tools that key may call, so this needs ROLLSTACK_API_KEY in the
  environment: a Rollstack API key with every scope, made by an owner or admin of the organization (listMembers
  needs `users:read`, which only they can grant). When the server leaves out a tool that was saved before, nothing
  is saved and the message names the scope that tool needs. tests/test_live.py reads the list the same way, through
  current().
- openapi_outputs.json: what each tool answers and which part of the API it belongs to, read from Rollstack's
  OpenAPI document, which needs no key.

Then tests/generate_tools.py writes the plugin's tool files from them. Run from integrations/dify:
python tests/update_fixture.py, and review the diff.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

import requests

MCP_URL = "https://api.rollstack.com/public/v1/mcp"
OPENAPI_URL = "https://api.rollstack.com/public/v1/openapi.json"
FIXTURE = Path(__file__).parent / "fixtures" / "mcp_tools.json"
OUTPUTS = Path(__file__).parent / "fixtures" / "openapi_outputs.json"
KEY_VARIABLE = "ROLLSTACK_API_KEY"
KEPT = ("name", "title", "description", "inputSchema", "annotations")
# Of a tool's _meta: the scopes a key needs to be shown it, and the viewer it opens or whether only a viewer calls it
KEPT_META = ("securitySchemes", "ui")


class ReferenceUnavailable(Exception):
    """Why the server's list can't be read as the reference, in words for the maintainer. Never holds the key."""


def kept(tool: dict[str, Any]) -> dict[str, Any]:
    """What the fixture keeps of a tool the server lists: its definition, its scopes and its viewer, if any."""
    meta = tool.get("_meta") or {}
    return {**{field: tool.get(field) for field in KEPT}, "_meta": {key: meta[key] for key in KEPT_META if key in meta}}


def scopes(tools: list[dict[str, Any]]) -> list[str]:
    """The scopes the saved definitions of ``tools`` ask of a key, each once, in the order they first appear."""
    schemes = [scheme for tool in tools for scheme in _schemes(tool) or []]
    return list(dict.fromkeys(scope for scheme in schemes for scope in scheme.get("scopes") or []))


def key_to_set(saved: list[dict[str, Any]]) -> str:
    """The key that the server shows every saved tool to, in words."""
    return f"a Rollstack API key with the scopes {_in_words(scopes(saved))}, made by an owner or admin"


def current(saved: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Every tool Rollstack's server lists now, in its order, as the fixture keeps them.

    Raises ReferenceUnavailable when no key is set, when the server doesn't list its tools for it, or when its list
    leaves out a saved tool. Saving the tools that are left would drop the others from the plugin without a word.
    """
    listed = _list_tools(key_to_set(saved))
    left_out = [tool for tool in saved if tool["name"] not in listed]
    if left_out:
        names = _in_words([f"{tool['name']} ({', '.join(scopes([tool])) or 'any key'})" for tool in left_out])
        raise ReferenceUnavailable(
            f"Rollstack's server left {names} out of the list it gave the key in {KEY_VARIABLE}. It lists for a key "
            f"only the tools that key may call, so use {key_to_set(saved)}. If the key has them, these tools were "
            "renamed or removed on Rollstack's side: see https://docs.rollstack.com/api/mcp-server."
        )
    return [kept(tool) for tool in listed.values()]


def outputs(api: dict[str, Any], tools: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """What each tool answers, from Rollstack's OpenAPI document, by tool name.

    ``group`` is the part of the API the tool belongs to, ``answer`` the shape of its answer: an ``object`` with
    ``fields``, a ``list``, several ``variants`` of an object whose fields are merged, ``none`` when it answers no
    content, and ``unknown`` for a tool the document doesn't describe, such as one only the MCP server has.
    """
    operations = {
        operation["operationId"]: operation
        for item in api["paths"].values()
        for operation in item.values()
        if isinstance(operation, dict) and "operationId" in operation
    }
    described = {}
    for tool in tools:
        operation = operations.get(tool["name"])
        if operation is None:
            described[tool["name"]] = {"group": None, "answer": "unknown", "fields": {}}
            continue
        tags = operation.get("tags") or [None]
        described[tool["name"]] = {"group": tags[0], **_answer(api, operation)}
    return described


def _answer(api: dict[str, Any], operation: dict[str, Any]) -> dict[str, Any]:
    success = [_deref(api, response) for code, response in operation["responses"].items() if code.startswith("2")]
    content = (success[0].get("content") or {}).get("application/json") if success else None
    if not content:
        return {"answer": "none", "fields": {}}
    schema = _deref(api, content["schema"])
    if schema.get("type") == "array":
        return {"answer": "list", "items": _deref(api, schema.get("items") or {}).get("type") or "object", "fields": {}}
    variants = schema.get("oneOf") or schema.get("anyOf")
    if variants:
        fields: dict[str, Any] = {}
        for variant in variants:
            for name, field in _fields(api, _deref(api, variant)).items():
                fields.setdefault(name, field)
        return {"answer": "variants", "fields": fields}
    return {"answer": "object", "fields": _fields(api, schema)}


def _fields(api: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
    """The top-level fields of an object schema: each one's JSON type and the first sentence of its description."""
    fields = {}
    for name, field in (schema.get("properties") or {}).items():
        field = _deref(api, field)
        kinds = field.get("type")
        if kinds is None:
            kinds = [_deref(api, option).get("type") for option in field.get("anyOf", []) + field.get("oneOf", [])]
        kinds = [kind for kind in (kinds if isinstance(kinds, list) else [kinds]) if kind not in (None, "null")]
        if len(set(kinds)) != 1:
            continue
        description = re.split(r"(?<=[.!?])\s", (field.get("description") or "").strip().split("\n")[0])[0]
        fields[name] = {"type": kinds[0], "description": description}
        if kinds[0] == "array":
            items = _deref(api, field.get("items") or next(
                (option.get("items") for option in field.get("anyOf", []) if isinstance(option, dict) and option.get("items")), {}
            ))
            fields[name]["items"] = items.get("type") or "object"
    return fields


def _deref(api: dict[str, Any], schema: Any) -> Any:
    while isinstance(schema, dict) and "$ref" in schema:
        target: Any = api
        for key in schema["$ref"].split("/")[1:]:
            target = target[key]
        schema = target
    return schema


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


def _openapi() -> dict[str, Any]:
    try:
        document = requests.get(OPENAPI_URL, headers={"Accept": "application/json"}, timeout=60)
    except requests.RequestException as error:
        raise ReferenceUnavailable(f"Could not reach Rollstack's OpenAPI document: {type(error).__name__}.") from None
    if document.status_code != 200:
        raise ReferenceUnavailable(f"Rollstack's OpenAPI document answered HTTP {document.status_code}.")
    return document.json()


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


def _write(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def main() -> None:
    saved = json.loads(FIXTURE.read_text())
    before = {tool["name"] for tool in saved["tools"]}
    try:
        saved["tools"] = current(saved["tools"])
        described = outputs(_openapi(), saved["tools"])
    except ReferenceUnavailable as error:
        raise SystemExit(f"{error} Nothing was saved.") from None
    _write(FIXTURE, saved)
    _write(OUTPUTS, described)
    added = [tool["name"] for tool in saved["tools"] if tool["name"] not in before]
    print(f"Saved {len(saved['tools'])} tools to {FIXTURE}" + (f", new: {', '.join(added)}" if added else ""))

    import generate_tools

    generate_tools.main()


if __name__ == "__main__":
    main()
