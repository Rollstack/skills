"""The Rollstack tools this plugin exposes, and how Dify's flat tool parameters map onto them.

A Rollstack tool takes its inputs in up to three parts: ``params`` (the ids of what it acts on), ``query`` (options
such as filters or how long to wait) and ``body`` (what it creates, changes or sends). A Dify tool takes a flat list
of parameters, so each parameter keeps the name of the Rollstack field it fills, and this module puts it in its part.
Dify has no list or object parameters for a plugin's tools: a list of strings comes as text separated by commas, and
any other structured input as JSON text.

The map is rollstack_client/tools.json, which tests/generate_tools.py writes from Rollstack's own tool definitions:
https://docs.rollstack.com/api/mcp-server
"""

from __future__ import annotations

import json
import math
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

PARTS = ("params", "query", "body")

TEXT = "text"
SELECT = "select"
INTEGER = "integer"
NUMBER = "number"
BOOLEAN = "boolean"
LIST = "list"  # a list of strings, given as text separated by commas, or as a JSON array
JSON = "json"  # any other structured input, given as JSON text

TRUE = {"true", "yes", "1"}
FALSE = {"false", "no", "0"}


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
    # The parts Rollstack requires, sent even when empty: createReport, for one, requires its body
    parts: tuple[str, ...] = ()
    # Whether the tool takes an idempotencyKey, which makes sending the call again safe
    takes_idempotency_key: bool = False
    # The type of each workflow variable the tool returns, by name, in the order its tool file declares them
    variable_types: Mapping[str, str] = field(default_factory=dict)
    # The variable that holds an answer that is a list, when the tool answers one
    list_variable: str | None = None


def _load(path: Path) -> dict[str, Operation]:
    spec = json.loads(path.read_text(encoding="utf-8"))
    return {
        name: Operation(
            params=tuple(Param(**param) for param in entry["params"]),
            parts=tuple(entry["parts"]),
            takes_idempotency_key=entry["idempotencyKey"],
            variable_types=entry["variables"],
            list_variable=entry["listVariable"],
        )
        for name, entry in spec.items()
    }


OPERATIONS: dict[str, Operation] = _load(Path(__file__).with_name("tools.json"))


def build_arguments(operation: str, tool_parameters: Mapping[str, Any]) -> dict[str, Any]:
    """The arguments of a Rollstack tool, from the parameters Dify passed to the tool of the same name."""
    spec = OPERATIONS[operation]
    arguments: dict[str, Any] = {part: {} for part in spec.parts}
    for param in spec.params:
        value = _convert(param, tool_parameters.get(param.name))
        if value is None:
            if param.required:
                raise InputError(f"{param.name} is required.")
            continue
        arguments.setdefault(param.part, {})[param.name] = value
    return arguments


def _convert(param: Param, value: Any) -> Any:
    """The value to send for ``param``, or None when Dify passed nothing for it."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    if param.kind == INTEGER:
        return _integer(param.name, value)
    if param.kind == NUMBER:
        return _number(param.name, value)
    if param.kind == BOOLEAN:
        return _boolean(param.name, value)
    if param.kind == LIST:
        return _list(param.name, value)
    if param.kind == JSON:
        return _json(param.name, value)
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


def _number(name: str, value: Any) -> int | float:
    if isinstance(value, bool):
        raise InputError(f"{name} must be a number.")
    if isinstance(value, (int, float)) and math.isfinite(value):
        return value
    if isinstance(value, str):
        text = value.strip()
        if re.fullmatch(r"[+-]?\d+", text):
            return int(text)
        try:
            number = float(text)
        except ValueError:
            pass
        else:
            if math.isfinite(number):
                return number
    raise InputError(f"{name} must be a number.")


def _boolean(name: str, value: Any) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in TRUE:
        return True
    if text in FALSE:
        return False
    raise InputError(f"{name} must be true or false.")


def _list(name: str, value: Any) -> list[str] | None:
    if isinstance(value, str) and value.strip().startswith("["):
        value = _json(name, value)
    items = re.split(r"[,\n]+", value) if isinstance(value, str) else value
    if (
        not isinstance(items, (list, tuple))
        or not all(isinstance(item, str) for item in items)
        or any(item.strip().startswith("{") for item in items)
    ):
        raise InputError(f"{name} must be values separated by commas, or a JSON array of strings.")
    values = [item.strip() for item in items if item.strip()]
    return values or None


def _json(name: str, value: Any) -> Any:
    # An empty list is a value of its own: it is how updateReportSchedules removes every schedule
    if not isinstance(value, str):
        return value
    try:
        return json.loads(value)
    except ValueError as error:
        raise InputError(f"{name} must be JSON text, and it isn't valid JSON: {error}.") from error
