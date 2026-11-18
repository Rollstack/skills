"""Runs a Rollstack tool for a Dify tool and returns its answer as Dify messages."""

from __future__ import annotations

import base64
import binascii
import json
import uuid
from collections.abc import Generator, Mapping
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from rollstack_client.mcp import CONFIRMATION_REQUIRED, RollstackClient, ToolResult, parse_json
from rollstack_client.operations import OPERATIONS, Operation, build_arguments

# The name of the provider's credential, as provider/rollstack.yaml declares it
CREDENTIAL_NAME = "rollstack_api_key"

# What an image's base64 data is replaced with in the JSON the tool answers, once the image is sent as a file
IMAGE_SENT = "(sent as an image file)"


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
    """The answer as Dify messages: JSON for agents and the ``json`` output, images as files, and the variables.

    It follows what Dify does with the answer of an MCP tool: a JSON object becomes a JSON message, a list of
    objects one JSON message each, an image an image file, and anything else text.
    """
    images = list(answer.images)
    payload: Any = None
    if answer.structured is not None:
        payload, found = _lift_images(answer.structured)
        images += found
        yield tool.create_json_message(payload)
    for text in answer.texts:
        value = parse_json(text)
        if isinstance(value, (dict, list)) and answer.structured is not None:
            # The same answer as the structured content, already given
            continue
        if isinstance(value, (dict, list)):
            value, found = _lift_images(value)
            images += found
            payload = value if payload is None else payload
        if isinstance(value, dict):
            yield tool.create_json_message(value)
        elif isinstance(value, list) and value and all(isinstance(item, dict) for item in value):
            for item in value:
                yield tool.create_json_message(item)
        else:
            # Not JSON, or a list a JSON message can't hold, such as an empty one
            yield tool.create_text_message(text if not isinstance(value, list) else json.dumps(value))

    for data, mime_type in images:
        try:
            blob = base64.b64decode(data, validate=True)
        except (binascii.Error, ValueError):
            continue
        yield tool.create_blob_message(blob, meta={"mime_type": mime_type})

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


def _lift_images(value: Any) -> tuple[Any, list[tuple[str, str]]]:
    """``value`` with the base64 data of each image in it taken out, and those images.

    An image is an object with a ``mimeType`` that starts with ``image/`` and its base64 ``data``, as in what
    getReportSlideImages answers. The data goes to the user as a file instead of to the model as text.
    """
    if isinstance(value, list):
        lifted = [_lift_images(item) for item in value]
        return [item for item, _ in lifted], [image for _, found in lifted for image in found]
    if not isinstance(value, dict):
        return value, []
    mime_type, data = value.get("mimeType"), value.get("data")
    if isinstance(mime_type, str) and mime_type.startswith("image/") and isinstance(data, str) and data:
        return {**value, "data": IMAGE_SENT}, [(data, mime_type)]
    images: list[tuple[str, str]] = []
    copy = {}
    for key, item in value.items():
        copy[key], found = _lift_images(item)
        images += found
    return copy, images


def _empty(kind: str) -> Any:
    """What a workflow variable holds when the answer has no value for it, by the type its tool file declares."""
    return {"string": "", "integer": 0, "number": 0, "boolean": False, "array": [], "object": {}}[kind]
