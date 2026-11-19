"""The plugin's tools against Rollstack's reference, and the files generated from it.

tests/fixtures/mcp_tools.json holds every tool Rollstack's MCP server lists, and tests/fixtures/openapi_outputs.json
what each one answers (tests/update_fixture.py refreshes both). tests/generate_tools.py writes the plugin's tool files
from them. These tests fail when the files differ from what it writes, when the plugin's tools aren't the server's,
and when a tool's name, inputs or descriptions aren't Rollstack's own.
"""

from __future__ import annotations

import json
import re
from typing import Any

import pytest
import yaml

import generate_tools
from conftest import PLUGIN_ROOT
from generate_tools import CONFIRMATION_VIEW, EMAILS_OR_DELETES, EXCLUDED, JSON_NOTE, LIST_NOTE, NULL_NOTE, RESERVED_OUTPUTS
from rollstack_client.operations import BOOLEAN, INTEGER, JSON, LIST, NUMBER, OPERATIONS, SELECT, TEXT

REFERENCE = json.loads((PLUGIN_ROOT / "tests/fixtures/mcp_tools.json").read_text())["tools"]
BY_NAME = {tool["name"]: tool for tool in REFERENCE}
DIFY_TYPES = {TEXT: "string", SELECT: "select", INTEGER: "number", NUMBER: "number", BOOLEAN: "boolean", LIST: "string", JSON: "string"}


def load_yaml(path: str) -> dict[str, Any]:
    return yaml.safe_load((PLUGIN_ROOT / path).read_text(encoding="utf-8"))


PROVIDER = load_yaml("provider/rollstack.yaml")
TOOLS = {tool["identity"]["name"]: tool for tool in (load_yaml(path) for path in PROVIDER["tools"])}


def inputs(name: str) -> list[tuple[str, str, dict[str, Any]]]:
    """Every input of a Rollstack tool: its part, its name and its schema, with shared definitions resolved.

    The inputs of params, query and body, then idempotencyKey, which sits beside them, in the part "".
    """
    schema = BY_NAME[name]["inputSchema"]
    found = []
    for part in ("params", "query", "body"):
        for field, field_schema in (schema.get("properties", {}).get(part, {}).get("properties") or {}).items():
            found.append((part, field, generate_tools.resolve(field_schema, schema.get("$defs") or {})))
    if "idempotencyKey" in schema.get("properties", {}):
        found.append(("", "idempotencyKey", schema["properties"]["idempotencyKey"]))
    return found


def view(name: str) -> dict[str, Any]:
    return (BY_NAME[name].get("_meta") or {}).get("ui") or {}


def test_the_generated_files_are_up_to_date():
    assert generate_tools.check() == [], "run python tests/generate_tools.py, which writes them from the fixtures"


def test_the_plugin_has_every_tool_the_server_lists_but_the_excluded_ones():
    listed = [tool["name"] for tool in REFERENCE]

    assert list(OPERATIONS) == [name for name in listed if name not in EXCLUDED]
    assert list(TOOLS) == list(OPERATIONS)
    assert set(EXCLUDED) <= set(listed), "an excluded tool the server no longer lists: remove it from EXCLUDED"
    assert len(PROVIDER["tools"]) == len(set(PROVIDER["tools"])) == len(TOOLS)


def test_only_the_tools_that_only_a_view_calls_are_left_out():
    # The server marks them as visible to its views alone: the model never calls them, in any client
    called_by_a_view = {tool["name"] for tool in REFERENCE if view(tool["name"]).get("visibility") == ["app"]}

    assert set(EXCLUDED) == called_by_a_view
    for reason in EXCLUDED.values():
        assert reason.endswith(".") and "Dify" in reason


@pytest.mark.parametrize("name", list(OPERATIONS))
def test_a_tool_is_named_labelled_and_described_as_in_the_reference(name):
    tool, reference = TOOLS[name], BY_NAME[name]

    assert tool["identity"] == {"name": name, "author": "rollstack", "label": {"en_US": reference["title"]}}
    assert tool["description"]["llm"] == reference["description"]
    human = tool["description"]["human"]["en_US"]
    assert human and reference["description"].replace("`", "").startswith(human)


@pytest.mark.parametrize("name", list(OPERATIONS))
def test_parameters_are_the_inputs_of_the_reference(name):
    spec = OPERATIONS[name]
    schema = BY_NAME[name]["inputSchema"]
    declared = {parameter["name"]: parameter for parameter in TOOLS[name]["parameters"]}
    reference = inputs(name)

    # One parameter per input, under the input's own name, which no two inputs of a tool share
    assert [field for _, field, _ in reference] == list(declared) == [param.name for param in spec.params]
    for (part, field, field_schema), param in zip(reference, spec.params):
        parameter = declared[field]
        kind, source = generate_tools.classify(field_schema)
        assert param.kind == kind, field
        required = (
            field in schema.get("required", [])
            if part == ""
            else part in schema.get("required", []) and field in schema["properties"][part].get("required", [])
        )
        assert param.part == part
        assert parameter["required"] is param.required is required, field
        assert parameter["form"] == "llm"
        assert parameter["type"] == DIFY_TYPES[param.kind], field

        own = field_schema.get("description")
        if own:
            assert parameter["llm_description"].startswith(own), field
            assert own.replace("`", "").startswith(parameter["human_description"]["en_US"]), field
        if param.kind == SELECT:
            assert [option["value"] for option in parameter["options"]] == source["enum"]
        if param.kind in (INTEGER, NUMBER):
            assert parameter.get("min") == source.get("minimum") and parameter.get("max") == source.get("maximum")
        if param.kind == LIST:
            assert LIST_NOTE in parameter["llm_description"]
        if param.kind == JSON:
            note, given = parameter["llm_description"].rsplit("\n", 1)
            assert note.endswith(JSON_NOTE)
            # The schema the input follows, as JSON, with the shared definitions it refers to
            described = json.loads(given)
            for reference_name in re.findall(r'"#/\$defs/([^"]+)"', given):
                assert reference_name in described["$defs"]
        if param.kind not in (LIST, JSON):
            assert LIST_NOTE not in parameter["llm_description"] and JSON_NOTE not in parameter["llm_description"]
        # The text null sends null, for an input that takes it, and the description says so
        takes_null = generate_tools.nullable(field_schema)
        assert param.nullable is takes_null, field
        assert (NULL_NOTE in parameter["llm_description"]) is takes_null, field


@pytest.mark.parametrize("name", list(OPERATIONS))
def test_parts_and_idempotency_follow_the_reference(name):
    spec = OPERATIONS[name]
    schema = BY_NAME[name]["inputSchema"]

    assert list(spec.parts) == [part for part in ("params", "query", "body") if part in schema.get("required", [])]
    assert spec.takes_idempotency_key is ("idempotencyKey" in schema.get("properties", {}))
    # The agent can pass its own key, as Rollstack's descriptions tell it to, so that a call sent again runs once
    assert spec.takes_idempotency_key is any(param.name == "idempotencyKey" and param.part == "" for param in spec.params)
    assert set(schema.get("properties", {})) - {"idempotencyKey"} <= {"params", "query", "body"}


@pytest.mark.parametrize("name", list(OPERATIONS))
def test_workflow_variables_match_what_the_tool_returns(name):
    spec = OPERATIONS[name]
    properties = (TOOLS[name].get("output_schema") or {}).get("properties", {})

    # The same variables, of the same types, in the same order as the tool returns them
    assert [(variable, schema["type"]) for variable, schema in properties.items()] == list(spec.variable_types.items())
    assert not RESERVED_OUTPUTS & set(properties)
    for schema in properties.values():
        assert schema["type"] in {"string", "integer", "number", "boolean", "array", "object"} and schema["description"]
        assert (schema["type"] == "array") is ("items" in schema)
    if spec.list_variable:
        assert list(properties) == [spec.list_variable] and properties[spec.list_variable]["type"] == "array"


@pytest.mark.parametrize("name", list(OPERATIONS))
def test_a_tools_source_calls_its_own_rollstack_tool(name):
    source = PLUGIN_ROOT / TOOLS[name]["extra"]["python"]["source"]

    assert re.findall(r'invoke_operation\(self, "(\w+)", tool_parameters\)', source.read_text()) == [name]


def test_the_calls_held_for_confirmation_are_the_ones_the_server_holds():
    # Over MCP, the server holds a call that emails people or deletes reports until the user confirms it in
    # Rollstack, and it says which tools those are: the ones that open its confirmation card
    held = {tool["name"] for tool in REFERENCE if view(tool["name"]).get("resourceUri") == CONFIRMATION_VIEW}

    assert set(EMAILS_OR_DELETES) <= set(OPERATIONS)
    assert {name for name, waits in EMAILS_OR_DELETES.items() if not waits.startswith("No")} == held


def test_every_tool_that_emails_or_deletes_is_in_the_readme_table():
    # Read from the descriptions: a tool whose name says it deletes, removes, unshares or sends must be listed
    named = {name for name in OPERATIONS if re.match(r"(delete|remove|unshare|share|batchShare)|send\w*Email", name)}

    assert named <= set(EMAILS_OR_DELETES)


def test_the_readme_names_only_tools_the_plugin_has_or_leaves_out():
    readme = (PLUGIN_ROOT / "README.md").read_text()
    named = set(re.findall(r"`((?:list|get|create|update|delete|send|start|show|search|add|remove|share|unshare|batch|"
                           r"approve|reject|cancel|apply|save|restore|render|arrange|export|convert|duplicate|query|"
                           r"preview|resolve|replace|confirm|submit|rename|reapply)[A-Z]\w*)`", readme))

    assert named <= set(OPERATIONS) | set(EXCLUDED)


def test_the_package_is_described_consistently():
    manifest = load_yaml("manifest.yaml")
    requirements = (PLUGIN_ROOT / "requirements.txt").read_text().split()

    assert manifest["author"] == PROVIDER["identity"]["author"] == "rollstack"
    assert manifest["name"] == PROVIDER["identity"]["name"] == "rollstack"
    assert manifest["plugins"]["tools"] == ["provider/rollstack.yaml"]
    assert manifest["network"]["domains"] == ["api.rollstack.com"]
    assert manifest["privacy"] == "PRIVACY.md" and (PLUGIN_ROOT / "PRIVACY.md").is_file()
    assert manifest["icon"] == PROVIDER["identity"]["icon"]
    # Every dependency is pinned to one version, and the SDK is at least the 0.9.0 the Marketplace asks for
    pins = dict(re.fullmatch(r"([\w-]+)==([\d.]+)", requirement).groups() for requirement in requirements)
    assert set(pins) == {"dify_plugin", "requests"}
    assert tuple(int(part) for part in pins["dify_plugin"].split(".")) >= (0, 9, 0)


def test_the_client_reports_the_plugins_version():
    from rollstack_client.mcp import PLUGIN_VERSION

    assert PLUGIN_VERSION == load_yaml("manifest.yaml")["version"]


def test_the_icon_is_rollstacks():
    icon = PLUGIN_ROOT / "_assets" / load_yaml("manifest.yaml")["icon"]

    assert icon.read_bytes() == (PLUGIN_ROOT.parents[1] / "assets/icon.png").read_bytes()
