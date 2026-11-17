"""The client: what it sends to Rollstack's MCP server, and how it reads each kind of answer."""

from __future__ import annotations

import json

import pytest
import requests

from conftest import FakeResponse, FakeSession, rpc, tool_answer
from rollstack_client import mcp
from rollstack_client.mcp import RollstackClient, RollstackError

KEY = "rsk_test_only"


def client(session: FakeSession, sleeps: list[float] | None = None) -> RollstackClient:
    return RollstackClient(KEY, session=session, sleep=(sleeps if sleeps is not None else []).append)


def test_a_tool_call_is_one_json_rpc_request():
    session = FakeSession(tool_answer({"data": [], "nextCursor": None}))

    answer = client(session).call_tool("listReports", {"query": {"limit": 5}})

    assert answer.payload == {"data": [], "nextCursor": None}
    (call,) = session.calls
    assert (call.method, call.url) == ("POST", "https://api.rollstack.com/public/v1/mcp")
    assert call.json["jsonrpc"] == "2.0"
    assert call.json["method"] == "tools/call"
    assert call.json["params"] == {"name": "listReports", "arguments": {"query": {"limit": 5}}}
    assert call.headers == {"Accept": "application/json, text/event-stream", "MCP-Protocol-Version": "2025-06-18"}
    assert call.timeout == (10, 90)
    assert session.headers["Authorization"] == f"Bearer {KEY}"
    assert session.headers["User-Agent"] == "rollstack-dify-plugin/0.0.1"


def test_structured_content_is_the_answer_when_the_server_sends_it():
    session = FakeSession(tool_answer("Started.", structured={"runId": "r1", "started": True}))

    answer = client(session).call_tool("startReportRun", {"params": {"id": "a"}})

    assert answer.payload == {"runId": "r1", "started": True}
    assert answer.texts == ("Started.",)


def test_an_answer_sent_as_an_event_stream_is_read():
    def stream(call):
        answer = {"jsonrpc": "2.0", "id": call.json["id"], "result": {"content": [{"type": "text", "text": '{"ok": 1}'}]}}
        lines = [
            b": keep-alive",
            b"event: message",
            b'data: {"jsonrpc": "2.0", "method": "notifications/progress", "params": {}}',
            b"",
            b"event: message",
            # An event's data can span lines, and its text is UTF-8 whatever the response says
            *(f"data: {line}".encode() for line in json.dumps(answer, indent=1).split("\n")),
            b"",
            b"data: never read",
        ]
        return FakeResponse(headers={"Content-Type": "text/event-stream"}, lines=lines)

    assert client(FakeSession(stream)).call_tool("getReport", {"params": {"id": "a"}}).payload == {"ok": 1}


def test_an_event_stream_that_ends_without_an_answer_is_an_error():
    stream = FakeResponse(headers={"Content-Type": "text/event-stream"}, lines=[b"data: {}", b""])

    with pytest.raises(RollstackError, match="cannot read"):
        client(FakeSession(stream)).call_tool("getReport", {"params": {"id": "a"}})


def test_a_tool_error_raises_with_rollstacks_message_and_code():
    refusal = {"code": "api-key-missing-scope", "message": "This call needs the slide_decks:run scope."}
    session = FakeSession(tool_answer(refusal, is_error=True))

    with pytest.raises(RollstackError) as raised:
        client(session).call_tool("startReportRun", {"params": {"id": "a"}})

    assert str(raised.value) == "This call needs the slide_decks:run scope. (api-key-missing-scope)"
    assert raised.value.code == "api-key-missing-scope"


def test_a_tool_error_that_is_plain_text_raises_with_that_text():
    with pytest.raises(RollstackError, match="^Report not found$"):
        client(FakeSession(tool_answer("Report not found", is_error=True))).call_tool("getReport", {"params": {"id": "a"}})


@pytest.mark.parametrize("is_error", [True, False])
def test_a_call_waiting_for_confirmation_is_an_answer_not_an_error(is_error):
    waiting = {"code": "confirmation-required", "message": "Confirm it in Rollstack: https://rollstack.example/confirm"}
    session = FakeSession(tool_answer(waiting, is_error=is_error))

    answer = client(session).call_tool("startReportRun", {"params": {"id": "a"}})

    assert answer.code == "confirmation-required"
    assert answer.payload == waiting


def test_a_refused_key_says_what_to_do_and_never_shows_the_key():
    refused = FakeResponse(401, {"code": "api-key-invalid", "message": "Invalid API key"})

    with pytest.raises(RollstackError) as raised:
        client(FakeSession(refused)).call_tool("listReports", {"query": {}})

    assert raised.value.status == 401
    assert raised.value.code == "api-key-invalid"
    assert "Invalid API key" in str(raised.value)
    assert "Settings > Connected apps" in str(raised.value)
    assert KEY not in str(raised.value)


def test_an_api_error_passes_on_rollstacks_message():
    invalid = FakeResponse(400, {"code": "data-validation-error", "message": "query.limit: Too big"})
    session = FakeSession(invalid)

    with pytest.raises(RollstackError, match=r"^query\.limit: Too big \(data-validation-error\)$"):
        client(session).call_tool("listReports", {"query": {"limit": 999}})

    # Rollstack's own 400 is not a request for a session, so nothing else is sent
    assert len(session.calls) == 1


def test_a_rate_limit_says_how_long_to_wait():
    limited = FakeResponse(429, {"code": "rate-limit-exceeded", "message": "Too many requests."}, headers={"Retry-After": "12"})

    with pytest.raises(RollstackError, match=r"Too many requests\. Wait 12 seconds before you call again\. \(rate-limit-exceeded\)"):
        client(FakeSession(limited)).call_tool("listReports", {"query": {}})


def test_a_json_rpc_error_raises():
    session = FakeSession(rpc(error={"code": -32602, "message": "Unknown tool: nope"}))

    with pytest.raises(RollstackError) as raised:
        client(session).call_tool("nope", {})

    assert str(raised.value) == "Unknown tool: nope (-32602)"


def test_an_answer_that_is_not_json_raises():
    with pytest.raises(RollstackError, match="cannot read"):
        client(FakeSession(FakeResponse(200, raw=b"<html>"))).call_tool("listReports", {"query": {}})


def test_gateway_errors_are_retried_with_the_same_call():
    session = FakeSession(FakeResponse(503), FakeResponse(502, raw=b"Bad gateway"), tool_answer({"id": "new"}))
    sleeps: list[float] = []

    answer = client(session, sleeps).call_tool("createReport", {"body": {}, "idempotencyKey": "k-1"})

    assert answer.payload == {"id": "new"}
    assert sleeps == [1.0, 2.0]
    # The same message, with the same idempotency key, so Rollstack runs it once
    assert [call.json for call in session.calls] == [session.calls[0].json] * 3


def test_a_gateway_error_that_lasts_is_reported():
    session = FakeSession(FakeResponse(503), FakeResponse(503), FakeResponse(503))

    with pytest.raises(RollstackError, match=r"unavailable right now \(HTTP 503\)") as raised:
        client(session).call_tool("listReports", {"query": {}})

    assert raised.value.status == 503
    assert len(session.calls) == 3


def test_a_connection_error_is_retried_then_reported():
    recovered = FakeSession(requests.ConnectionError("reset"), tool_answer({"ok": True}))
    assert client(recovered).call_tool("listTemplates", {}).payload == {"ok": True}

    down = FakeSession(*(requests.ConnectionError("refused") for _ in range(3)))
    with pytest.raises(RollstackError, match="Could not reach Rollstack") as raised:
        client(down).call_tool("listTemplates", {})
    assert raised.value.code == "connection-error"


def test_a_read_timeout_is_not_retried():
    session = FakeSession(requests.ReadTimeout("slow"))

    with pytest.raises(RollstackError, match="did not answer within 90 seconds") as raised:
        client(session).call_tool("createReport", {"body": {}})

    assert raised.value.code == "timeout"
    assert len(session.calls) == 1


def test_a_session_is_opened_when_the_server_asks_for_one():
    wants_session = rpc(error={"code": -32000, "message": "Bad Request: Mcp-Session-Id header is required"}, status=400)
    opened = rpc({"protocolVersion": "2025-03-26", "capabilities": {}}, headers={"Mcp-Session-Id": "s-1"})
    session = FakeSession(wants_session, opened, FakeResponse(202), tool_answer({"ok": True}))

    answer = client(session).call_tool("getReport", {"params": {"id": "a"}})

    assert answer.payload == {"ok": True}
    first, initialize, initialized, again = session.calls
    assert initialize.json["method"] == "initialize"
    assert initialize.json["params"]["protocolVersion"] == "2025-06-18"
    assert initialize.json["params"]["clientInfo"] == {"name": "rollstack-dify-plugin", "version": "0.0.1"}
    assert initialized.json == {"jsonrpc": "2.0", "method": "notifications/initialized"}
    continuing = {"MCP-Protocol-Version": "2025-03-26", "Mcp-Session-Id": "s-1"}
    assert continuing.items() <= initialized.headers.items()
    assert continuing.items() <= again.headers.items()
    assert again.json == first.json


def test_a_session_that_cannot_be_opened_is_reported():
    wants_session = rpc(error={"code": -32000, "message": "Bad Request: Server not initialized"}, status=400)
    session = FakeSession(wants_session, FakeResponse(401, {"code": "api-key-invalid", "message": "Invalid API key"}))

    with pytest.raises(RollstackError) as raised:
        client(session).call_tool("getReport", {"params": {"id": "a"}})

    assert raised.value.code == "api-key-invalid"


def test_get_me_answers_who_the_key_acts_as():
    me = {"id": 1, "email": "ada@example.com", "name": "Ada", "organization": {"id": "org-1", "name": "Example", "role": "member"}}
    session = FakeSession(FakeResponse(200, me))

    assert client(session).get_me() == me
    (call,) = session.calls
    assert (call.method, call.url) == ("GET", "https://api.rollstack.com/public/v1/me")


def test_get_me_refuses_a_bad_key():
    with pytest.raises(RollstackError) as raised:
        client(FakeSession(FakeResponse(401, {"code": "api-key-expired", "message": "This API key has expired"}))).get_me()

    assert raised.value.code == "api-key-expired"


@pytest.mark.parametrize("key", [None, "", "   "])
def test_a_missing_key_is_refused_before_any_request(key):
    session = FakeSession()

    with pytest.raises(RollstackError, match="API key is missing") as raised:
        RollstackClient(key, session=session)

    assert raised.value.code == "api-key-missing"
    assert session.calls == []


def test_the_plugin_only_calls_rollstacks_api():
    assert mcp.MCP_URL.startswith("https://api.rollstack.com/")
    assert mcp.ME_URL.startswith("https://api.rollstack.com/")
