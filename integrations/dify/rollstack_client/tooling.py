"""Runs a Rollstack tool for a Dify tool and returns its answer as Dify messages."""

from __future__ import annotations

import uuid
from collections.abc import Generator, Mapping
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from rollstack_client.mcp import CONFIRMATION_REQUIRED, RollstackClient, ToolResult, parse_json
from rollstack_client.operations import OPERATIONS, Operation, build_arguments

# The name of the provider's credential, as provider/rollstack.yaml declares it
CREDENTIAL_NAME = "rollstack_api_key"


def invoke_operation(
    tool: Tool, operation: str, tool_parameters: Mapping[str, Any]
) -> Generator[ToolInvokeMessage, None, None]:
    """Call the Rollstack tool named ``operation`` with the parameters Dify passed, and yield what it answered."""
    spec = OPERATIONS[operation]
    arguments = build_arguments(operation, tool_parameters)
    if spec.takes_idempotency_key:
        # One key per invocation: if the call is sent again after a gateway error, Rollstack runs it once
        arguments["idempotencyKey"] = str(uuid.uuid4())
    with RollstackClient(tool.runtime.credentials.get(CREDENTIAL_NAME)) as client:
        answer = client.call_tool(operation, arguments)
    yield from _messages(tool, spec, answer)


def _messages(tool: Tool, spec: Operation, answer: ToolResult) -> Generator[ToolInvokeMessage, None, None]:
    """The answer as Dify messages: JSON for agents and the ``json`` output, plus the tool's workflow variables.

    It follows what Dify does with the answer of an MCP tool: a JSON object becomes a JSON message, a list of
    objects one JSON message each, and anything else text.
    """
    if answer.structured is not None:
        yield tool.create_json_message(answer.structured)
    for text in answer.texts:
        value = parse_json(text)
        if isinstance(value, dict):
            if answer.structured is None:
                yield tool.create_json_message(value)
        elif isinstance(value, list) and value and all(isinstance(item, dict) for item in value):
            if answer.structured is None:
                for item in value:
                    yield tool.create_json_message(item)
        else:
            # Not JSON, or a list a JSON message can't hold, such as an empty one
            yield tool.create_text_message(text)

    payload = answer.payload
    if isinstance(payload, list):
        payload = {spec.list_variable: payload} if spec.list_variable else {}
    elif not isinstance(payload, dict):
        payload = {}
    if payload.get("code") == CONFIRMATION_REQUIRED and isinstance(payload.get("message"), str):
        # The message holds the link the user confirms the call at: show it as text too
        yield tool.create_text_message(payload["message"])
    # Every variable the tool declares is returned on every call, empty when the answer doesn't have it, so a
    # workflow node that reads one always finds it
    for name, kind in spec.variable_types.items():
        value = payload.get(name)
        yield tool.create_variable_message(name, _empty(kind) if value is None else value)


def _empty(kind: str) -> Any:
    """What a workflow variable holds when the answer has no value for it, by the type its tool file declares."""
    return {"string": "", "boolean": False, "array": []}[kind]
