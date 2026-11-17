"""The Rollstack tools this plugin exposes, and how Dify's flat tool parameters map onto them.

A Rollstack tool takes its inputs in up to three parts: ``params`` (the ids of what it acts on), ``query`` (options
such as filters or how long to wait) and ``body`` (what it creates, changes or sends). A Dify tool takes a flat list
of parameters, so each parameter keeps the name of the Rollstack field it fills, and this module puts it in its part.
Dify has no list parameters either: ids come as text separated by commas, and lists of objects as JSON text.

The tools, their names and their inputs are Rollstack's own: https://docs.rollstack.com/api/mcp-server
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

PARTS = ("params", "query", "body")

TEXT = "text"
INTEGER = "integer"
IDS = "ids"  # a list of ids, given as text separated by commas, or as a JSON array
OBJECTS = "objects"  # a list of objects, given as a JSON array


class InputError(ValueError):
    """A tool parameter this plugin cannot turn into the value Rollstack expects."""


@dataclass(frozen=True)
class Param:
    name: str
    part: str
    kind: str = TEXT
    required: bool = False


@dataclass(frozen=True)
class Operation:
    params: tuple[Param, ...] = ()
    # Whether the tool takes an idempotencyKey, which makes sending the call again safe
    takes_idempotency_key: bool = False
    # The fields of the answer returned as workflow variables, each with its type ("string" unless given), and
    # the variable that holds an answer that is a list
    variables: tuple[str | tuple[str, str], ...] = ()
    list_variable: str | None = None

    @property
    def variable_types(self) -> dict[str, str]:
        """The type of each workflow variable the tool returns, by name, in the order its tool file declares them."""
        types = dict((variable, "string") if isinstance(variable, str) else variable for variable in self.variables)
        if self.list_variable:
            types[self.list_variable] = "array"
        return types


_REPORT = Param("id", "params", required=True)

OPERATIONS: dict[str, Operation] = {
    "listReports": Operation(
        params=(
            Param("name", "query"),
            Param("type", "query"),
            Param("folderId", "query"),
            Param("limit", "query", INTEGER),
            Param("cursor", "query"),
        ),
        variables=(("data", "array"), "nextCursor"),
    ),
    "getReport": Operation(
        params=(_REPORT,),
        variables=("id", "name", "type", "folderId", "appUrl", ("running", "boolean"), "lastRunStatus"),
    ),
    "listTemplates": Operation(variables=(("data", "array"),)),
    "createReport": Operation(
        params=(
            Param("name", "body"),
            Param("templateId", "body"),
            Param("templateDeckId", "body"),
            Param("folderId", "body"),
            Param("link", "body"),
        ),
        takes_idempotency_key=True,
        variables=("id", "name", "type", "folderId", "appUrl"),
    ),
    "sendReportMessage": Operation(
        params=(
            _REPORT,
            Param("content", "body"),
            Param("chatId", "body"),
            Param("slideIds", "body", IDS),
            Param("answers", "body", OBJECTS),
        ),
        takes_idempotency_key=True,
        variables=("chatId", "messageId", "status", "appUrl"),
    ),
    "getReportMessage": Operation(
        params=(_REPORT, Param("messageId", "params", required=True), Param("waitSeconds", "query", INTEGER)),
        variables=("chatId", "messageId", "status", "stage", "appUrl", ("replies", "array")),
    ),
    "getReportContent": Operation(
        params=(_REPORT, Param("slideIds", "query", IDS)),
        variables=(("slides", "array"),),
    ),
    "startReportRun": Operation(
        params=(_REPORT, Param("datasheetIds", "body", IDS), Param("syncIds", "body", IDS)),
        takes_idempotency_key=True,
        # code and message are set when the run waits for the user to confirm it in Rollstack
        variables=("runId", ("started", "boolean"), "code", "message"),
    ),
    "getReportRun": Operation(
        params=(_REPORT, Param("runId", "params", required=True), Param("waitSeconds", "query", INTEGER)),
        variables=("runId", "status", "startedAt", "finishedAt", ("errors", "array")),
    ),
    "getReportSchedules": Operation(params=(_REPORT,), list_variable="schedules"),
    "updateReportSchedules": Operation(
        params=(_REPORT, Param("schedules", "body", OBJECTS, required=True)),
        takes_idempotency_key=True,
        list_variable="schedules",
    ),
    "exportReport": Operation(
        params=(_REPORT, Param("format", "body", required=True), Param("slideIds", "body", IDS)),
        takes_idempotency_key=True,
        variables=("url", "expiresAt"),
    ),
}


def build_arguments(operation: str, tool_parameters: Mapping[str, Any]) -> dict[str, Any]:
    """The arguments of a Rollstack tool, from the parameters Dify passed to the tool of the same name."""
    spec = OPERATIONS[operation]
    # Every part the tool has is sent, even empty: createReport, for one, requires its body
    arguments: dict[str, Any] = {part: {} for part in PARTS if any(param.part == part for param in spec.params)}
    for param in spec.params:
        value = _convert(param, tool_parameters.get(param.name))
        if value is None:
            if param.required:
                raise InputError(f"{param.name} is required.")
            continue
        arguments[param.part][param.name] = value
    return arguments


def _convert(param: Param, value: Any) -> Any:
    """The value to send for ``param``, or None when Dify passed nothing for it."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    if param.kind == INTEGER:
        return _integer(param.name, value)
    if param.kind == IDS:
        return _ids(param.name, value)
    if param.kind == OBJECTS:
        return _objects(param.name, value)
    return value.strip() if isinstance(value, str) else str(value)


def _integer(name: str, value: Any) -> int:
    if isinstance(value, bool):
        raise InputError(f"{name} must be a whole number.")
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str) and re.fullmatch(r"[+-]?\d+", value.strip()):
        return int(value.strip())
    raise InputError(f"{name} must be a whole number.")


def _ids(name: str, value: Any) -> list[str] | None:
    if isinstance(value, str) and value.strip().startswith("["):
        value = _json_array(name, value)
    items = re.split(r"[,\s]+", value) if isinstance(value, str) else value
    if (
        not isinstance(items, (list, tuple))
        or not all(isinstance(item, str) for item in items)
        or any(item.startswith("{") for item in items)
    ):
        raise InputError(f"{name} must be ids separated by commas.")
    ids = [item.strip() for item in items if item.strip()]
    return ids or None


def _objects(name: str, value: Any) -> list[dict[str, Any]]:
    # An empty list is a value of its own here: it is how updateReportSchedules removes every schedule
    items = _json_array(name, value) if isinstance(value, str) else value
    if not isinstance(items, list) or not all(isinstance(item, dict) for item in items):
        raise InputError(f"{name} must be a JSON array of objects.")
    return items


def _json_array(name: str, text: str) -> list[Any]:
    try:
        value = json.loads(text)
    except ValueError as error:
        raise InputError(f"{name} must be a JSON array, and it isn't valid JSON: {error}.") from error
    if not isinstance(value, list):
        raise InputError(f"{name} must be a JSON array.")
    return value
