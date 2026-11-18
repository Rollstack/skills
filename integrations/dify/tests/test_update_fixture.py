"""How the reference is read from Rollstack's server, by tests/update_fixture.py and by the live test.

The server lists its tools only for a key, and for a key only the tools it may call. These tests answer for it: what
is sent, what is kept of its list, and what happens when the key is missing, refused or not shown every tool.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
import requests

import update_fixture
from update_fixture import KEY_VARIABLE, ReferenceUnavailable, current, key_to_set, scopes

KEY = "rsk_test_only"
SAVED_BYTES = update_fixture.FIXTURE.read_bytes()
SAVED = json.loads(SAVED_BYTES)["tools"]
# The scopes the README and DEVELOPMENT.md tell people to give a key: when this changes, they change too
SCOPES = "slide_decks:read, slide_decks:write and slide_decks:run"


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
    """The server's list of ``tools``, each with the fields the fixture doesn't keep."""
    view = {"ui": {"resourceUri": "ui://rollstack/view-v1.html"}}
    listed = [{**tool, "_meta": {**tool["_meta"], **view}, "outputSchema": {"type": "object"}} for tool in tools]
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
def fixture_copy(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """A copy of the fixture for the updater to write to."""
    copy = tmp_path / "mcp_tools.json"
    copy.write_bytes(SAVED_BYTES)
    monkeypatch.setattr(update_fixture, "FIXTURE", copy)
    return copy


def test_the_list_is_asked_for_with_the_key_and_read_as_the_fixture_keeps_it(rollstack):
    not_in_the_plugin = {**SAVED[0], "name": "deleteBurst"}
    calls = rollstack(listing([not_in_the_plugin, *reversed(SAVED)]))

    assert current(SAVED) == SAVED
    (call,) = calls
    assert call.url == "https://api.rollstack.com/public/v1/mcp"
    assert call.json == {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}
    assert call.headers == {"Accept": "application/json, text/event-stream", "Authorization": f"Bearer {KEY}"}


def test_every_saved_tool_says_which_scope_it_needs():
    for tool in SAVED:
        assert scopes([tool]), tool["name"]
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
    # What the server lists for a key that has only slide_decks:read
    rollstack(listing([tool for tool in SAVED if scopes([tool]) == ["slide_decks:read"]]))

    with pytest.raises(ReferenceUnavailable) as raised:
        current(SAVED)

    assert str(raised.value).startswith(
        "Rollstack's server left createReport (slide_decks:write), sendReportMessage (slide_decks:run), "
        "startReportRun (slide_decks:run) and updateReportSchedules (slide_decks:write) out of the list it gave the "
        "key in ROLLSTACK_API_KEY. It lists for a key only the tools that key may call, so use a Rollstack API key "
        f"with the scopes {SCOPES}. If the key has them, these tools were renamed or removed"
    )


def test_the_updater_saves_nothing_when_a_tool_is_left_out(rollstack, fixture_copy):
    rollstack(listing(SAVED[1:]))

    with pytest.raises(SystemExit, match=r"left listReports \(slide_decks:read\) out of the list .* Nothing was saved\.$"):
        update_fixture.main()

    assert fixture_copy.read_bytes() == SAVED_BYTES


def test_the_updater_saves_what_the_server_lists_now(rollstack, fixture_copy, capsys):
    changed = {**SAVED[0], "description": "A new description."}
    rollstack(listing([changed, *SAVED[1:]]))

    update_fixture.main()

    assert json.loads(fixture_copy.read_text())["tools"] == [changed, *SAVED[1:]]
    assert KEY not in fixture_copy.read_text() + capsys.readouterr().out


def test_the_updater_writes_the_file_back_as_it_was_when_nothing_changed(rollstack, fixture_copy):
    rollstack(listing(SAVED))

    update_fixture.main()

    # So the diff of a refresh shows only what Rollstack changed
    assert fixture_copy.read_bytes() == SAVED_BYTES
