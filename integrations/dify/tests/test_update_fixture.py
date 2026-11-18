"""How the reference is read from Rollstack, by tests/update_fixture.py and by the live test.

The server lists its tools only for a key, and for a key only the tools it may call. These tests answer for it: what
is sent, what is kept of its list, and what happens when the key is missing, refused or not shown every tool. They
also cover how the answers of the tools are read from Rollstack's OpenAPI document.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
import requests

import generate_tools
import update_fixture
from update_fixture import KEY_VARIABLE, ReferenceUnavailable, current, key_to_set, outputs, scopes

KEY = "rsk_test_only"
SAVED_BYTES = update_fixture.FIXTURE.read_bytes()
SAVED = json.loads(SAVED_BYTES)["tools"]
# Every scope a key needs to be shown every tool: when this changes, DEVELOPMENT.md and the README change too
SCOPES = (
    "slide_decks:read, slide_decks:write, slide_decks:run, slide_decks:email, connections:read, smtp:read and "
    "users:read, made by an owner or admin"
)


class Answer:
    """What the updater reads of an HTTP response."""

    def __init__(self, status: int, body: Any) -> None:
        self.status_code = status
        self._body = body

    def json(self) -> Any:
        if self._body is None:
            raise ValueError("not JSON")
        return self._body


def listing(tools: list[dict[str, Any]]) -> Answer:
    """The server's list of ``tools``, each with fields the fixture doesn't keep."""
    listed = [{**tool, "_meta": {**tool["_meta"], "openai/outputTemplate": "x"}, "outputSchema": {"type": "object"}} for tool in tools]
    return Answer(200, {"jsonrpc": "2.0", "id": 1, "result": {"tools": listed}})


@pytest.fixture
def rollstack(monkeypatch: pytest.MonkeyPatch):
    """Answer the request for the list with ``answer``, the key being set unless ``key`` is None. Returns the calls."""

    def install(answer: Answer | Exception | None = None, *, key: str | None = KEY) -> list[SimpleNamespace]:
        calls: list[SimpleNamespace] = []

        def post(url: str, **kwargs: Any) -> Answer:
            calls.append(SimpleNamespace(url=url, **kwargs))
            assert answer is not None, f"unexpected request: POST {url}"
            if isinstance(answer, Exception):
                raise answer
            return answer

        monkeypatch.setattr(update_fixture.requests, "post", post)
        if key is None:
            monkeypatch.delenv(KEY_VARIABLE, raising=False)
        else:
            monkeypatch.setenv(KEY_VARIABLE, key)
        return calls

    return install


@pytest.fixture
def files(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> SimpleNamespace:
    """Copies of the fixtures for the updater to write to, an OpenAPI document, and a generator that records runs."""
    tools, answers = tmp_path / "mcp_tools.json", tmp_path / "openapi_outputs.json"
    tools.write_bytes(SAVED_BYTES)
    monkeypatch.setattr(update_fixture, "FIXTURE", tools)
    monkeypatch.setattr(update_fixture, "OUTPUTS", answers)
    monkeypatch.setattr(update_fixture, "_openapi", lambda: OPENAPI)
    generated: list[bool] = []
    monkeypatch.setattr(generate_tools, "main", lambda: generated.append(True))
    return SimpleNamespace(tools=tools, answers=answers, generated=generated)


def test_the_list_is_asked_for_with_the_key_and_kept_whole(rollstack):
    new = {**SAVED[0], "name": "brandNewTool"}
    calls = rollstack(listing([new, *SAVED]))

    # Every tool the server lists, in its order, new ones included, with only what the fixture keeps
    assert current(SAVED) == [new, *SAVED]
    (call,) = calls
    assert call.url == "https://api.rollstack.com/public/v1/mcp"
    assert call.json == {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}
    assert call.headers == {"Accept": "application/json, text/event-stream", "Authorization": f"Bearer {KEY}"}


def test_every_saved_tool_says_which_scope_it_needs():
    # submitFeedback works with any key, so it names no scope
    assert [tool["name"] for tool in SAVED if not scopes([tool])] == ["submitFeedback", "confirmAction"]
    assert key_to_set(SAVED) == f"a Rollstack API key with the scopes {SCOPES}"


@pytest.mark.parametrize("key", [None, "", "  "])
def test_without_a_key_nothing_is_sent(rollstack, key):
    calls = rollstack(key=key)

    with pytest.raises(ReferenceUnavailable, match=f"^Set ROLLSTACK_API_KEY to a Rollstack API key with the scopes {SCOPES}: "):
        current(SAVED)

    assert calls == []


def test_a_refused_key_is_reported_with_rollstacks_code(rollstack):
    rollstack(Answer(401, {"code": "api-key-invalid", "message": "Invalid API key"}))

    with pytest.raises(ReferenceUnavailable) as raised:
        current(SAVED)

    assert str(raised.value) == (
        "Rollstack's server did not list its tools for the key in ROLLSTACK_API_KEY: it answered HTTP 401 (api-key-invalid)."
    )


@pytest.mark.parametrize(
    ("answer", "said"),
    [
        (Answer(503, None), "it answered HTTP 503."),
        (requests.ConnectionError(f"sent with Bearer {KEY}"), "Could not reach Rollstack's server: ConnectionError."),
    ],
)
def test_a_server_that_does_not_answer_is_reported_without_the_key(rollstack, answer, said):
    rollstack(answer)

    with pytest.raises(ReferenceUnavailable) as raised:
        current(SAVED)

    assert str(raised.value).endswith(said)
    assert KEY not in str(raised.value)
    # Nor does the report go on to an error underneath, which could quote the request
    assert raised.value.__context__ is None or raised.value.__suppress_context__


def test_a_tool_the_key_is_not_shown_is_named_with_the_scope_it_needs(rollstack):
    # What the server lists for a key that isn't an admin's: everything but listMembers
    rollstack(listing([tool for tool in SAVED if tool["name"] != "listMembers"]))

    with pytest.raises(ReferenceUnavailable) as raised:
        current(SAVED)

    assert str(raised.value).startswith(
        "Rollstack's server left listMembers (users:read) out of the list it gave the key in ROLLSTACK_API_KEY. It "
        f"lists for a key only the tools that key may call, so use a Rollstack API key with the scopes {SCOPES}."
    )


def test_the_updater_saves_nothing_when_a_tool_is_left_out(rollstack, files):
    rollstack(listing(SAVED[1:]))

    with pytest.raises(SystemExit, match=r"left listReports \(slide_decks:read\) out of the list .* Nothing was saved\.$"):
        update_fixture.main()

    assert files.tools.read_bytes() == SAVED_BYTES
    assert not files.answers.exists() and files.generated == []


def test_the_updater_saves_what_rollstack_says_now_and_generates_the_tools(rollstack, files, capsys):
    changed = {**SAVED[0], "description": "A new description."}
    new = {**SAVED[1], "name": "brandNewTool"}
    rollstack(listing([changed, new, *SAVED[1:]]))

    update_fixture.main()

    assert json.loads(files.tools.read_text())["tools"] == [changed, new, *SAVED[1:]]
    assert json.loads(files.answers.read_text())["listReports"] == {
        "group": "Reports",
        "answer": "object",
        "fields": {"data": {"type": "array", "description": "The reports on this page.", "items": "object"}},
    }
    assert files.generated == [True]
    out = capsys.readouterr().out
    assert "new: brandNewTool" in out
    assert KEY not in files.tools.read_text() + out


def test_the_updater_writes_the_file_back_as_it_was_when_nothing_changed(rollstack, files):
    rollstack(listing(SAVED))

    update_fixture.main()

    # So the diff of a refresh shows only what Rollstack changed
    assert files.tools.read_bytes() == SAVED_BYTES


# A small OpenAPI document with each shape of answer the plugin reads
OPENAPI = {
    "paths": {
        "/reports": {
            "get": {
                "operationId": "listReports",
                "tags": ["Reports"],
                "responses": {
                    "200": {"$ref": "#/components/responses/Page"},
                    "default": {"content": {"application/json": {"schema": {"type": "object"}}}},
                },
            }
        },
        "/reports/{id}/schedules": {
            "get": {
                "operationId": "getReportSchedules",
                "tags": ["Schedules"],
                "responses": {"200": {"content": {"application/json": {"schema": {"type": "array", "items": {"type": "object"}}}}}},
            }
        },
        "/memories/{id}": {"delete": {"operationId": "deleteMemory", "tags": ["Memories"], "responses": {"204": {"description": "Deleted"}}}},
        "/reports/{id}/theme": {
            "patch": {
                "operationId": "updateReportTheme",
                "tags": ["Content"],
                "responses": {
                    "200": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "oneOf": [
                                        {"properties": {"changed": {"type": "boolean", "description": "Whether it changed."}}},
                                        {"properties": {"reason": {"type": ["string", "null"], "description": "Why not. Only then."}}},
                                    ]
                                }
                            }
                        }
                    }
                },
            }
        },
    },
    "components": {
        "responses": {
            "Page": {
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": {
                                "data": {"type": "array", "items": {"$ref": "#/components/schemas/Report"}, "description": "The reports on this page."},
                                "mixed": {"anyOf": [{"type": "string"}, {"type": "array"}], "description": "Kept out."},
                            },
                        }
                    }
                }
            }
        },
        "schemas": {"Report": {"type": "object"}},
    },
}


def test_what_each_tool_answers_is_read_from_the_openapi_document():
    names = ["listReports", "getReportSchedules", "deleteMemory", "updateReportTheme", "showReport"]

    described = outputs(OPENAPI, [{"name": name} for name in names])

    assert described == {
        # A field that can be of more than one type is left to the json output
        "listReports": {"group": "Reports", "answer": "object", "fields": {"data": {"type": "array", "description": "The reports on this page.", "items": "object"}}},
        "getReportSchedules": {"group": "Schedules", "answer": "list", "items": "object", "fields": {}},
        "deleteMemory": {"group": "Memories", "answer": "none", "fields": {}},
        "updateReportTheme": {
            "group": "Content",
            "answer": "variants",
            "fields": {"changed": {"type": "boolean", "description": "Whether it changed."}, "reason": {"type": "string", "description": "Why not."}},
        },
        "showReport": {"group": None, "answer": "unknown", "fields": {}},
    }
