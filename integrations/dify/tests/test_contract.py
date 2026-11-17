"""The plugin's tools against Rollstack's reference.

tests/fixtures/mcp_tools.json holds the definitions of the tools this plugin exposes, as Rollstack's MCP server lists
them (tests/update_fixture.py refreshes it). These tests keep the Dify tool files and the parameter map true to it:
the same names, the same inputs, and descriptions made only of the reference's own sentences.
"""

from __future__ import annotations

import json
import re
from typing import Any

import pytest
import yaml

from conftest import PLUGIN_ROOT
from rollstack_client.operations import IDS, INTEGER, OBJECTS, OPERATIONS, TEXT

REFERENCE = {tool["name"]: tool for tool in json.loads((PLUGIN_ROOT / "tests/fixtures/mcp_tools.json").read_text())["tools"]}

# What the plugin says in its own words, because it is about the plugin and not about Rollstack
NOTES = {
    "Pass the ids as text, separated by commas.",
    "Pass it as JSON text: an array of objects with these fields.",
    "This plugin has no tool to approve or reject a proposal: the user decides it in Rollstack, at the message's appUrl.",
}

# Where one sentence ends and the next starts, and the label that starts the line of an object's field
SENTENCE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9`\"'(\[])")
FIELD_LINE = re.compile(r"^- `\w+` \((?:required|optional)(?:; one of [\w, ]+)?\): ")
RESERVED_OUTPUTS = {"text", "json", "files"}


def load_yaml(path: str) -> dict[str, Any]:
    return yaml.safe_load((PLUGIN_ROOT / path).read_text(encoding="utf-8"))


PROVIDER = load_yaml("provider/rollstack.yaml")
TOOLS = {tool["identity"]["name"]: tool for tool in (load_yaml(path) for path in PROVIDER["tools"])}


def sentences(text: str) -> list[str]:
    return [sentence for line in text.split("\n") for sentence in SENTENCE.split(FIELD_LINE.sub("", line.strip())) if sentence]


def descriptions(schema: Any) -> list[str]:
    """Every description in a JSON schema, at any depth."""
    found: list[str] = []
    if isinstance(schema, dict):
        if isinstance(schema.get("description"), str):
            found.append(schema["description"])
        for value in schema.values():
            found.extend(descriptions(value))
    elif isinstance(schema, list):
        for value in schema:
            found.extend(descriptions(value))
    return found


def reference_sentences(name: str) -> set[str]:
    tool = REFERENCE[name]
    return {s for text in [tool["description"], *descriptions(tool["inputSchema"])] for s in sentences(text)}


def input_schema(name: str, part: str, field: str) -> dict[str, Any]:
    return REFERENCE[name]["inputSchema"]["properties"][part]["properties"][field]


def test_the_plugin_exposes_exactly_the_tools_it_maps():
    assert list(TOOLS) == list(OPERATIONS)
    assert set(TOOLS) <= set(REFERENCE)
    assert len(PROVIDER["tools"]) == len(set(PROVIDER["tools"])) == len(TOOLS)


@pytest.mark.parametrize("name", list(OPERATIONS))
def test_a_tool_is_named_and_labelled_as_in_the_reference(name):
    tool = TOOLS[name]

    assert tool["identity"]["name"] == REFERENCE[name]["name"]
    assert tool["identity"]["label"]["en_US"] == REFERENCE[name]["title"]
    assert tool["identity"]["author"] == PROVIDER["identity"]["author"] == "rollstack"


@pytest.mark.parametrize("name", list(OPERATIONS))
def test_parameters_are_the_inputs_of_the_reference(name):
    spec = OPERATIONS[name]
    schema = REFERENCE[name]["inputSchema"]
    declared = {parameter["name"]: parameter for parameter in TOOLS[name].get("parameters") or []}

    assert list(declared) == [param.name for param in spec.params]
    for param in spec.params:
        field = input_schema(name, param.part, param.name)
        parameter = declared[param.name]
        part = schema["properties"][param.part]
        required = param.part in schema.get("required", []) and param.name in part.get("required", [])
        assert parameter["required"] is param.required is required, param.name
        assert parameter["form"] == "llm"

        kinds = {field.get("type")} | {option.get("type") for option in field.get("anyOf", [])}
        if param.kind == INTEGER:
            assert field["type"] == "integer"
            assert (parameter["type"], parameter["min"], parameter["max"]) == ("number", field["minimum"], field["maximum"])
        elif param.kind == IDS:
            assert "array" in kinds and (field.get("items") or field["anyOf"][1]["items"])["type"] == "string"
            assert parameter["type"] == "string"
        elif param.kind == OBJECTS:
            assert field["type"] == "array" and field["items"]["type"] == "object"
            assert parameter["type"] == "string"
        elif "enum" in field:
            assert param.kind == TEXT and parameter["type"] == "select"
            assert [option["value"] for option in parameter["options"]] == field["enum"]
        else:
            assert param.kind == TEXT and field["type"] == "string" and parameter["type"] == "string"


@pytest.mark.parametrize("name", list(OPERATIONS))
def test_nothing_the_reference_requires_is_left_out(name):
    spec = OPERATIONS[name]
    schema = REFERENCE[name]["inputSchema"]
    mapped = {(param.part, param.name) for param in spec.params}

    assert set(schema.get("properties", {})) - {"idempotencyKey"} == {param.part for param in spec.params}
    for part in schema.get("required", []):
        for field in schema["properties"][part].get("required", []):
            assert (part, field) in mapped
    # An idempotency key is sent to the tools that take one, and only to them
    assert spec.takes_idempotency_key is ("idempotencyKey" in schema.get("properties", {}))


@pytest.mark.parametrize("name", list(OPERATIONS))
def test_descriptions_are_made_of_the_references_sentences(name):
    tool = TOOLS[name]
    allowed = reference_sentences(name) | NOTES
    plain = {sentence.replace("`", "") for sentence in allowed}

    texts = [tool["description"]["llm"]] + [parameter["llm_description"] for parameter in tool.get("parameters") or []]
    for text in texts:
        for sentence in sentences(text):
            assert sentence in allowed, f"not in Rollstack's reference for {name}: {sentence!r}"

    # What people read in Dify is the first sentence, without the code marks
    shown = [tool["description"]["human"]["en_US"]] + [p["human_description"]["en_US"] for p in tool.get("parameters") or []]
    for text in shown:
        assert text in plain, f"not in Rollstack's reference for {name}: {text!r}"


@pytest.mark.parametrize("name", list(OPERATIONS))
def test_lists_say_how_to_pass_them(name):
    declared = {parameter["name"]: parameter for parameter in TOOLS[name].get("parameters") or []}

    for param in OPERATIONS[name].params:
        text = declared[param.name]["llm_description"]
        if param.kind == IDS:
            assert text.endswith("Pass the ids as text, separated by commas.")
        if param.kind == OBJECTS:
            fields = input_schema(name, param.part, param.name)["items"]
            assert "Pass it as JSON text: an array of objects with these fields." in text
            # Every field of the objects is described, and the required ones are marked
            for field in fields["properties"]:
                marked = "required" if field in fields["required"] else "optional"
                assert f"\n- `{field}` ({marked}" in text


@pytest.mark.parametrize("name", list(OPERATIONS))
def test_workflow_variables_match_what_the_tool_returns(name):
    declared = OPERATIONS[name].variable_types
    properties = TOOLS[name]["output_schema"]["properties"]

    assert TOOLS[name]["output_schema"]["type"] == "object"
    # The same variables, of the same types, in the same order as the tool returns them
    assert [(variable, schema["type"]) for variable, schema in properties.items()] == list(declared.items())
    assert not RESERVED_OUTPUTS & set(properties)
    for schema in properties.values():
        assert schema["type"] in {"string", "boolean", "array"} and schema["description"]
        assert (schema["type"] == "array") is ("items" in schema)


@pytest.mark.parametrize("name", list(OPERATIONS))
def test_a_tools_source_calls_its_own_rollstack_tool(name):
    source = PLUGIN_ROOT / TOOLS[name]["extra"]["python"]["source"]

    assert re.findall(r'invoke_operation\(self, "(\w+)", tool_parameters\)', source.read_text()) == [name]


def test_no_tool_emails_people_or_deletes_anything():
    # Rollstack marks these calls as waiting for the user's confirmation. startReportRun is the one the plugin has,
    # and it goes through the MCP server, where the confirmation always applies
    confirmed_in_rollstack = {
        "approveReportMessageProposal", "startReportRun", "batchStartReportRuns", "sendReportEmail", "startBurstRun",
        "sendBurstEmailConfig", "sendBurstVariantEmails", "deleteBurst", "removeBurstVariants",
    }

    assert set(OPERATIONS) & confirmed_in_rollstack == {"startReportRun"}
    assert not [name for name in OPERATIONS if re.search(r"delete|remove|email|approve", name, re.IGNORECASE)]


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
