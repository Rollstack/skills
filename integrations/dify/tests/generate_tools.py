"""Write the plugin's tool files from Rollstack's tool definitions.

It reads tests/fixtures/mcp_tools.json (every tool Rollstack's MCP server lists) and tests/fixtures/openapi_outputs.json
(what each one answers), which tests/update_fixture.py refreshes, and writes:

- tools/<name>.yaml and tools/<name>.py: one Dify tool per Rollstack tool, with Rollstack's name, title, description
  and inputs, and its answer's fields as workflow variables;
- rollstack_client/tools.json: how the plugin turns the tool's Dify parameters into the Rollstack tool's arguments;
- the list of tools in provider/rollstack.yaml, and the table of tools in README.md.

Dify has no list or object parameters for a plugin's tools, so a list of strings becomes text separated by commas, and
any other structured input JSON text, whose JSON Schema the description gives. Run from integrations/dify:
python tests/generate_tools.py. tests/test_contract.py fails when the files differ from what it writes.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "mcp_tools.json"
OUTPUTS = ROOT / "tests" / "fixtures" / "openapi_outputs.json"
SPEC = ROOT / "rollstack_client" / "tools.json"
PROVIDER = ROOT / "provider" / "rollstack.yaml"
README = ROOT / "README.md"
AUTHOR = "rollstack"

# Tools the server lists that the plugin leaves out, and why. Each is called by a view Rollstack's server shows in
# clients that support MCP Apps, never by the model, and Dify shows no such view
EXCLUDED = {
    "getTemplatePickerCovers": "Called only by the template picker that showTemplates opens in clients that can show "
    "it. Dify can't, and showTemplates answers the templates in its place.",
    "getReportMessageProgress": "Called only by the progress view that sendReportMessage opens in clients that can "
    "show it. Dify can't, and getReportMessage answers the same progress.",
    "getReportViewerSlideImages": "Called only by the report viewer that showReport opens in clients that can show "
    "it. Dify can't, and getReportSlideImages renders the same slides.",
    "confirmAction": "Called only by the confirmation card Rollstack's server shows before a call that emails people "
    "or deletes reports, with a token only that card has. In Dify, the user confirms such a call in Rollstack, at "
    "the link the tool answers.",
}

# The group of a tool Rollstack's OpenAPI document doesn't describe, because only its MCP server has it
GROUPS = {"showReport": "Content", "showTemplates": "Templates", "submitFeedback": "Feedback"}

# The tools that email people or delete or remove something, and whether Rollstack holds the call until the user
# confirms it in Rollstack. Read from each tool's description on 2026-11-18. Over MCP, Rollstack's server holds every
# call that emails people or deletes reports, whatever the key: those are the tools that open its confirmation card
# (a `ui` of confirmation-v1), and tests/test_contract.py checks this list against that mark
EMAILS_OR_DELETES = {
    "approveReportMessageProposal": "When it sends an email",
    "startReportRun": "When the run would email the report",
    "batchStartReportRuns": "When a run would email a report",
    "sendReportEmail": "Yes",
    "startBurstRun": "When a run would email a variant",
    "sendBurstEmailConfig": "Yes",
    "sendBurstVariantEmails": "Yes",
    "deleteBurst": "Yes",
    "removeBurstVariants": "Yes",
    "shareReport": "No: the member gets an email",
    "batchShareReports": "No: each member gets an email",
    "shareFolder": "No: a member new to the folder gets an email",
    "sendReportTestEmail": "No: it goes to you alone",
    "sendBurstEmailConfigTest": "No: it goes to you alone",
    "deleteTemplate": "No",
    "deleteMemory": "No",
    "deleteDataset": "No",
    "removeReportDatasheet": "No",
    "deleteReportParameter": "No",
    "deleteBurstEmailConfig": "No",
    "unshareReport": "No",
    "unshareFolder": "No",
    "arrangeReportSlides": "No: restoreReportVersion brings removed slides back",
    "updateReportSchedules": "No",
    "batchUpdateReportSchedules": "No",
}
CONFIRMATION_VIEW = "ui://rollstack/confirmation-v1.html"
# The fields a call answers when Rollstack holds it until the user confirms it, which a workflow can branch on
CONFIRMATION_VARIABLES = {
    "code": "`confirmation-required` when Rollstack holds the call until you confirm it in Rollstack. Empty when it ran.",
    "message": "What you are asked to confirm, with the link you confirm it at. Set with `code`.",
}

# Scopes only the organization's owners and admins can give a key (https://rollstack.com/auth.md)
ADMIN_SCOPES = {"organization:write", "users:read", "users:write"}

# Names Dify gives every tool's outputs, which a workflow variable can't take. Such a field is still in the json output
RESERVED_OUTPUTS = {"text", "json", "files"}

PARTS = ("params", "query", "body")
TEXT, SELECT, INTEGER, NUMBER, BOOLEAN, LIST, JSON = "text", "select", "integer", "number", "boolean", "list", "json"

LIST_NOTE = "Pass them as text, separated by commas, or as a JSON array."
JSON_NOTE = "Pass it as JSON text, as this JSON Schema describes:"
NULL_NOTE = "To send null, pass the text null."
# The input that makes retrying a call safe sits beside the parts, not in one of them
TOP_LEVEL = ""
IDEMPOTENCY_KEY = "idempotencyKey"
ACRONYMS = {
    "id": "ID", "ids": "IDs", "url": "URL", "urls": "URLs", "csv": "CSV", "sql": "SQL", "smtp": "SMTP",
    "html": "HTML", "cc": "CC", "bcc": "BCC", "api": "API", "llm": "LLM", "pdf": "PDF",
}  # fmt: skip
SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9`\"'(\[])")
README_START, README_END = "<!-- tools:start -->", "<!-- tools:end -->"
CAREFUL_START, CAREFUL_END = "<!-- careful:start -->", "<!-- careful:end -->"


def load() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    return json.loads(FIXTURE.read_text())["tools"], json.loads(OUTPUTS.read_text())


def plugin_tools(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The tools the plugin has: every tool the server lists, in its order, but the excluded ones."""
    return [tool for tool in tools if tool["name"] not in EXCLUDED]


def file_name(tool: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", tool).lower()


def class_name(tool: str) -> str:
    return tool[0].upper() + tool[1:] + "Tool"


def first_sentence(text: str) -> str:
    return SENTENCE_END.split(text.strip().split("\n")[0])[0]


def plain(text: str) -> str:
    """Text as Dify shows it to people, without Markdown's code marks."""
    return text.replace("`", "")


def label(name: str, resource: str) -> str:
    """A parameter's label from its name: ``datasheetIds`` is Datasheet IDs, and ``id`` is the resource's ID."""
    if name == "id":
        return f"{resource} ID"
    words = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", name).split()
    words = [ACRONYMS.get(word.lower(), word.lower()) for word in words]
    return " ".join([words[0][0].upper() + words[0][1:], *words[1:]])


def resolve(field: dict[str, Any], definitions: dict[str, Any]) -> dict[str, Any]:
    """A field whose schema is one of the tool's shared definitions, as that definition with the field's own keys."""
    while "$ref" in field and field["$ref"].startswith("#/$defs/") and field["$ref"][8:] in definitions:
        own = {key: value for key, value in field.items() if key != "$ref"}
        field = {**definitions[field["$ref"][8:]], **own}
    return field


def resource(tool: dict[str, Any]) -> str:
    """What a tool's ``id`` names, from the tool's own words: "The report to act on" is a report."""
    schema = tool["inputSchema"]
    params = schema.get("properties", {}).get("params", {}).get("properties", {})
    described = resolve(params.get("id") or {}, schema.get("$defs") or {}).get("description", "")
    found = re.match(r"The ([a-z]+(?: [a-z]+)?) (?:to |the tool |by |from |whose )", described) or re.match(
        r"Unique identifier for the ([a-z]+)", described
    )
    if not found:
        raise ValueError(f"{tool['name']}: can't tell what its id names from {described[:60]!r}")
    return found.group(1).capitalize()


def classify(field: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """The kind of Dify parameter a Rollstack input becomes, and the schema its options and bounds come from."""
    if "$ref" in field:
        return JSON, field
    options = [option for option in field.get("anyOf") or field.get("oneOf") or [] if option.get("type") != "null"]
    if options:
        if len(options) == 1 and "$ref" not in options[0]:
            return classify({**options[0], "description": field.get("description")})
        types = {option.get("type") for option in options}
        lists = [option for option in options if option.get("type") == "array"]
        if types == {"string", "array"} and all((option.get("items") or {}).get("type") == "string" for option in lists):
            return LIST, lists[0]["items"]
        return JSON, field
    kinds = field.get("type")
    if isinstance(kinds, list):
        kinds = [kind for kind in kinds if kind != "null"]
        if len(kinds) != 1:
            return JSON, field
        kinds = kinds[0]
    if kinds == "string":
        if "enum" in field and all(isinstance(value, str) for value in field["enum"]):
            return SELECT, field
        return TEXT, field
    if kinds in (INTEGER, NUMBER, BOOLEAN):
        return kinds, field
    if kinds == "array" and (field.get("items") or {}).get("type") == "string":
        return LIST, field["items"]
    return JSON, field


def json_schema(field: dict[str, Any], definitions: dict[str, Any]) -> str:
    """The JSON Schema of a structured input, compact, with the shared definitions it refers to."""
    schema = {key: value for key, value in field.items() if key != "description"}
    used: dict[str, Any] = {}
    pending = re.findall(r'"#/\$defs/([^"]+)"', json.dumps(schema))
    while pending:
        name = pending.pop()
        if name not in used and name in definitions:
            used[name] = definitions[name]
            pending += re.findall(r'"#/\$defs/([^"]+)"', json.dumps(definitions[name]))
    if used:
        schema["$defs"] = dict(sorted(used.items()))
    return json.dumps(schema, ensure_ascii=False, separators=(",", ":"))


def inputs(tool: dict[str, Any]) -> list[tuple[str, str, dict[str, Any], bool]]:
    """Every input of a Rollstack tool, in order: its part, its name, its schema and whether it is required.

    The inputs of ``params``, ``query`` and ``body`` come first, then ``idempotencyKey``, which a tool that writes
    takes beside them, so that a call sent again with the same key runs once.
    """
    schema = tool["inputSchema"]
    found = []
    for part in PARTS:
        part_schema = schema.get("properties", {}).get(part)
        if not part_schema:
            continue
        part_required = part in schema.get("required", [])
        for name, field in (part_schema.get("properties") or {}).items():
            found.append((part, name, field, part_required and name in part_schema.get("required", [])))
    if IDEMPOTENCY_KEY in schema.get("properties", {}):
        found.append((TOP_LEVEL, IDEMPOTENCY_KEY, schema["properties"][IDEMPOTENCY_KEY], IDEMPOTENCY_KEY in schema.get("required", [])))
    return found


def nullable(field: dict[str, Any]) -> bool:
    """Whether an input takes null as a value of its own, such as a folder's parent to move it to the top level."""
    kinds = field.get("type")
    options = field.get("anyOf") or field.get("oneOf") or []
    return (isinstance(kinds, list) and "null" in kinds) or any(option.get("type") == "null" for option in options)


def parameters(tool: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """The tool's Dify parameters, and how each one maps onto the Rollstack tool's arguments."""
    definitions = tool["inputSchema"].get("$defs") or {}
    declared, mapped = [], []
    for part, name, field, required in inputs(tool):
        field = resolve(field, definitions)
        kind, source = classify(field)
        shown = label(name, resource(tool) if part == "params" and name == "id" else "")
        described = field.get("description") or source.get("description") or shown
        llm = described
        if kind == LIST:
            llm += " " + LIST_NOTE
            if "enum" in source:
                llm += " Each one of: " + ", ".join(source["enum"]) + "."
        if nullable(field):
            llm += " " + NULL_NOTE
        if kind == JSON:
            llm += "\n" + JSON_NOTE + "\n" + json_schema(field, definitions)
        parameter: dict[str, Any] = {
            "name": name,
            "type": {SELECT: "select", INTEGER: "number", NUMBER: "number", BOOLEAN: "boolean"}.get(kind, "string"),
            "required": required,
            "form": "llm",
            "label": {"en_US": shown},
            "human_description": {"en_US": plain(first_sentence(described))},
            "llm_description": llm,
        }
        if kind in (INTEGER, NUMBER):
            parameter.update({bound: source[key] for bound, key in (("min", "minimum"), ("max", "maximum")) if key in source})
        if kind == SELECT:
            parameter["options"] = [{"value": value, "label": {"en_US": value}} for value in source["enum"]]
        declared.append(parameter)
        entry = {"name": name, "part": part, "kind": kind, "required": required}
        if nullable(field):
            entry["nullable"] = True
        mapped.append(entry)
    return declared, mapped


def list_variable(tool: str) -> str:
    """The workflow variable that holds an answer that is a list: listReportSyncs answers syncs."""
    rest = re.sub(r"^(list|search|get|update)", "", tool)
    rest = re.sub(r"^Report(?=[A-Z])", "", rest)
    return rest[0].lower() + rest[1:]


def variables(tool: dict[str, Any], answer: dict[str, Any]) -> tuple[dict[str, Any], str | None]:
    """The workflow variables of a tool, as its output schema declares them, and the one that holds a list answer."""
    if answer["answer"] == "list":
        name = list_variable(tool["name"])
        return {name: {"type": "array", "items": {"type": answer["items"]}, "description": first_sentence(tool["description"])}}, name
    declared = {}
    for name, field in answer["fields"].items():
        if name in RESERVED_OUTPUTS:
            continue
        declared[name] = {"type": field["type"]}
        if field["type"] == "array":
            declared[name]["items"] = {"type": field.get("items", "object")}
        declared[name]["description"] = field["description"] or label(name, "Item")
    if ((tool.get("_meta") or {}).get("ui") or {}).get("resourceUri") == CONFIRMATION_VIEW:
        for name, description in CONFIRMATION_VARIABLES.items():
            declared.setdefault(name, {"type": "string", "description": description})
    return declared, None


def tool_file(tool: dict[str, Any], answer: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """A tool's YAML file for Dify, and its entry in tools.json."""
    declared, mapped = parameters(tool)
    outputs, holds_list = variables(tool, answer)
    document: dict[str, Any] = {
        "identity": {"name": tool["name"], "author": AUTHOR, "label": {"en_US": tool["title"]}},
        "description": {"human": {"en_US": plain(first_sentence(tool["description"]))}, "llm": tool["description"]},
        "parameters": declared,
    }
    if outputs:
        document["output_schema"] = {"type": "object", "properties": outputs}
    document["extra"] = {"python": {"source": f"tools/{file_name(tool['name'])}.py"}}
    entry = {
        "params": mapped,
        "parts": [part for part in PARTS if part in tool["inputSchema"].get("required", [])],
        "idempotencyKey": "idempotencyKey" in tool["inputSchema"].get("properties", {}),
        "variables": {name: output["type"] for name, output in outputs.items()},
        "listVariable": holds_list,
    }
    return document, entry


class _Dumper(yaml.SafeDumper):
    pass


def _string(dumper: yaml.SafeDumper, value: str) -> yaml.ScalarNode:
    style = "|" if "\n" in value else None
    return dumper.represent_scalar("tag:yaml.org,2002:str", value, style=style)


_Dumper.add_representer(str, _string)


def to_yaml(document: Any) -> str:
    return yaml.dump(document, Dumper=_Dumper, sort_keys=False, allow_unicode=True, width=1_000_000)


PYTHON = '''from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from rollstack_client.tooling import invoke_operation


class {cls}(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        yield from invoke_operation(self, "{name}", tool_parameters)
'''


def scope_of(tool: dict[str, Any]) -> str:
    found = [scope for scheme in (tool.get("_meta") or {}).get("securitySchemes") or [] for scope in scheme.get("scopes") or []]
    if not found:
        return "Any key"
    shown = ", ".join(f"`{scope}`" for scope in found)
    return shown + (" (owners and admins)" if set(found) & ADMIN_SCOPES else "")


def readme_table(tools: list[dict[str, Any]], answers: dict[str, Any]) -> str:
    groups: dict[str, list[dict[str, Any]]] = {}
    for tool in tools:
        group = answers[tool["name"]]["group"] or GROUPS[tool["name"]]
        groups.setdefault(group, []).append(tool)
    lines = [README_START, "", f"The plugin has {len(tools)} tools, in the groups of Rollstack's API reference.", ""]
    for group, members in groups.items():
        lines += [f"#### {group}", "", "| Tool | What it does | Scope of the key |", "| --- | --- | --- |"]
        lines += [f"| `{tool['name']}` | {first_sentence(tool['description']).replace('|', chr(92) + '|')} | {scope_of(tool)} |" for tool in members]
        lines.append("")
    lines.append(README_END)
    return "\n".join(lines)


def careful_table(tools: list[dict[str, Any]]) -> str:
    """The README's table of the tools that email people or delete something, in the server's order."""
    lines = [CAREFUL_START, "", "| Tool | What it does | Held until you confirm it in Rollstack |", "| --- | --- | --- |"]
    for tool in tools:
        if tool["name"] in EMAILS_OR_DELETES:
            what = first_sentence(tool["description"]).replace("|", "\\|")
            lines.append(f"| `{tool['name']}` | {what} | {EMAILS_OR_DELETES[tool['name']]} |")
    lines += ["", CAREFUL_END]
    return "\n".join(lines)


def _between(text: str, start: str, end: str, block: str) -> str:
    begin, finish = text.index(start), text.index(end) + len(end)
    return text[:begin] + block + text[finish:]


def render() -> dict[Path, str]:
    """Every generated file, by path, with its content."""
    all_tools, answers = load()
    tools = plugin_tools(all_tools)
    files: dict[Path, str] = {}
    spec = {}
    for tool in tools:
        document, entry = tool_file(tool, answers[tool["name"]])
        files[ROOT / "tools" / f"{file_name(tool['name'])}.yaml"] = to_yaml(document)
        files[ROOT / "tools" / f"{file_name(tool['name'])}.py"] = PYTHON.format(cls=class_name(tool["name"]), name=tool["name"])
        spec[tool["name"]] = entry
    files[SPEC] = json.dumps(spec, indent=1, ensure_ascii=False) + "\n"

    provider = PROVIDER.read_text()
    listed = "".join(f"  - tools/{file_name(tool['name'])}.yaml\n" for tool in tools)
    files[PROVIDER] = re.sub(r"(?ms)^tools:\n(?:  - .*?\n)*", lambda _: "tools:\n" + listed, provider, count=1)

    readme = _between(README.read_text(), README_START, README_END, readme_table(tools, answers))
    files[README] = _between(readme, CAREFUL_START, CAREFUL_END, careful_table(tools))
    return files


def stale() -> list[Path]:
    """Tool files in tools/ that the generator doesn't write, such as a removed tool's."""
    written = render()
    return sorted(path for path in (ROOT / "tools").iterdir() if path.suffix in (".py", ".yaml") and path not in written)


def check() -> list[str]:
    """The generated files that differ from what the generator writes, as paths relative to the plugin's folder."""
    differ = [path for path, content in render().items() if not path.is_file() or path.read_text() != content]
    return [str(path.relative_to(ROOT)) for path in differ + stale()]


def main() -> None:
    files = render()
    for path in stale():
        path.unlink()
    changed = 0
    for path, content in files.items():
        if not path.is_file() or path.read_text() != content:
            path.write_text(content)
            changed += 1
    print(f"Generated {sum(1 for path in files if path.suffix == '.yaml' and path.parent.name == 'tools')} tools: {changed} files changed")


if __name__ == "__main__":
    sys.exit(main())
