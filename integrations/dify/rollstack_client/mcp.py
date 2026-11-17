"""Client for Rollstack's MCP server and its key check.

Every tool of this plugin is one ``tools/call`` on Rollstack's MCP server: a JSON-RPC message sent over HTTPS with
the API key as a bearer token. Calls go through the MCP server rather than the REST API because there Rollstack
makes the user confirm, in Rollstack, any call that emails people, whatever the kind of key.
"""

from __future__ import annotations

import json
import time
import uuid
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from typing import Any

import requests

MCP_URL = "https://api.rollstack.com/public/v1/mcp"
ME_URL = "https://api.rollstack.com/public/v1/me"
PROTOCOL_VERSION = "2025-06-18"
PLUGIN_VERSION = "0.0.1"
CLIENT_NAME = "rollstack-dify-plugin"

# A call waits up to 30 seconds on Rollstack's side (waitSeconds) and importing a deck can take a minute, so the
# time allowed to read an answer leaves room for both
CONNECT_TIMEOUT_SECONDS = 10
READ_TIMEOUT_SECONDS = 90

# Gateway answers worth another try: reads are safe to repeat, and writes carry an idempotency key
RETRY_STATUSES = frozenset({502, 503, 504})
RETRY_DELAYS_SECONDS = (1.0, 2.0)

# The code of a call that waits for the user to confirm it in Rollstack, such as a run that emails the report
CONFIRMATION_REQUIRED = "confirmation-required"


class RollstackError(Exception):
    """An answer from Rollstack that a tool cannot return as its result."""

    def __init__(self, message: str, *, code: str | None = None, status: int | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.status = status


@dataclass(frozen=True)
class ToolResult:
    """What a tool answered: its text blocks, and its structured content when the server sends one."""

    texts: tuple[str, ...] = ()
    structured: dict[str, Any] | None = None

    @property
    def payload(self) -> Any:
        """The answer as JSON: the structured content, or else the first text block that is JSON."""
        if self.structured is not None:
            return self.structured
        for text in self.texts:
            value = parse_json(text)
            if isinstance(value, (dict, list)):
                return value
        return None

    @property
    def code(self) -> str | None:
        payload = self.payload
        code = payload.get("code") if isinstance(payload, dict) else None
        return code if isinstance(code, str) else None


@dataclass(frozen=True)
class _Reply:
    status: int
    body: Any = None
    session_id: str | None = None
    retry_after: str | None = None


def parse_json(text: str | bytes) -> Any:
    """The JSON value in ``text``, or None when it isn't JSON."""
    try:
        return json.loads(text)
    except (ValueError, UnicodeDecodeError):
        return None


class RollstackClient:
    """Calls Rollstack as the user the API key belongs to."""

    def __init__(
        self,
        api_key: str | None,
        *,
        session: requests.Session | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        api_key = (api_key or "").strip()
        if not api_key:
            raise RollstackError(
                "The Rollstack API key is missing. Add one in this plugin's credentials: "
                "create it in Rollstack under Settings > Connected apps.",
                code="api-key-missing",
            )
        self._session = session if session is not None else requests.Session()
        self._session.headers.update(
            {"Authorization": f"Bearer {api_key}", "User-Agent": f"{CLIENT_NAME}/{PLUGIN_VERSION}"}
        )
        self._sleep = sleep

    def __enter__(self) -> RollstackClient:
        return self

    def __exit__(self, *exc: object) -> None:
        self._session.close()

    def get_me(self) -> dict[str, Any]:
        """The user, organization, role and scopes the key acts with. Rollstack's check that a key works."""
        reply = self._with_retries(self._get_me_once)
        if reply.status != 200 or not isinstance(reply.body, dict):
            raise _http_error(reply)
        return reply.body

    def call_tool(self, name: str, arguments: Mapping[str, Any]) -> ToolResult:
        """Run one Rollstack tool and return what it answered. Raises RollstackError when it failed."""
        message = _request("tools/call", {"name": name, "arguments": dict(arguments)})
        reply = self._post(message, {"MCP-Protocol-Version": PROTOCOL_VERSION})
        if reply.status in (400, 404) and _is_rpc_error(reply.body):
            # Rollstack's server answers each call on its own, without a session. Should it start to ask for one,
            # which a server does with this answer, open a session and send the call again
            reply = self._post(message, self._open_session())
        return _tool_result(reply)

    def _open_session(self) -> dict[str, str]:
        """Start an MCP session and return the headers that continue it."""
        client = {"name": CLIENT_NAME, "version": PLUGIN_VERSION}
        opening = {"protocolVersion": PROTOCOL_VERSION, "capabilities": {}, "clientInfo": client}
        reply = self._post(_request("initialize", opening), {})
        result = reply.body.get("result") if isinstance(reply.body, dict) else None
        if reply.status != 200 or not isinstance(result, dict):
            raise _http_error(reply)
        headers = {"MCP-Protocol-Version": str(result.get("protocolVersion") or PROTOCOL_VERSION)}
        if reply.session_id:
            headers["Mcp-Session-Id"] = reply.session_id
        self._post({"jsonrpc": "2.0", "method": "notifications/initialized"}, headers)
        return headers

    def _post(self, message: dict[str, Any], headers: Mapping[str, str]) -> _Reply:
        return self._with_retries(lambda: self._post_once(message, headers))

    def _post_once(self, message: dict[str, Any], headers: Mapping[str, str]) -> _Reply:
        # The server answers a call as JSON or as an event stream, and refuses a client that doesn't accept both
        headers = {"Accept": "application/json, text/event-stream", **headers}
        timeout = (CONNECT_TIMEOUT_SECONDS, READ_TIMEOUT_SECONDS)
        with self._session.post(MCP_URL, json=message, headers=headers, timeout=timeout, stream=True) as response:
            if response.headers.get("Content-Type", "").startswith("text/event-stream"):
                body = _read_event_stream(response.iter_lines(), message.get("id"))
            else:
                body = parse_json(response.content)
            return _reply(response, body)

    def _get_me_once(self) -> _Reply:
        timeout = (CONNECT_TIMEOUT_SECONDS, READ_TIMEOUT_SECONDS)
        with self._session.get(ME_URL, headers={"Accept": "application/json"}, timeout=timeout) as response:
            return _reply(response, parse_json(response.content))

    def _with_retries(self, send: Callable[[], _Reply]) -> _Reply:
        for delay in (*RETRY_DELAYS_SECONDS, None):
            try:
                reply = send()
            except requests.ReadTimeout as error:
                # Not sent again: the call may be running, and waiting another 90 seconds helps nobody
                raise RollstackError(
                    f"Rollstack did not answer within {READ_TIMEOUT_SECONDS} seconds. The call may still have run: "
                    "check in Rollstack before you send it again.",
                    code="timeout",
                ) from error
            except requests.ConnectionError as error:
                if delay is None:
                    raise RollstackError(
                        "Could not reach Rollstack. Check that this Dify instance can make HTTPS requests to "
                        "api.rollstack.com.",
                        code="connection-error",
                    ) from error
            except requests.RequestException as error:
                raise RollstackError(f"The request to Rollstack failed: {type(error).__name__}.") from error
            else:
                if delay is None or reply.status not in RETRY_STATUSES:
                    return reply
            self._sleep(delay)
        raise AssertionError("unreachable")  # the last turn of the loop always returns or raises


def _request(method: str, params: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": str(uuid.uuid4()), "method": method, "params": params}


def _reply(response: requests.Response, body: Any) -> _Reply:
    return _Reply(
        status=response.status_code,
        body=body,
        session_id=response.headers.get("Mcp-Session-Id"),
        retry_after=response.headers.get("Retry-After"),
    )


def _read_event_stream(lines: Iterable[bytes | str], request_id: Any) -> Any:
    """The JSON-RPC answer to ``request_id`` in a stream of server-sent events, or None when it has none."""
    data: list[str] = []
    for raw in lines:
        line = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else raw
        if line:
            if line.startswith("data:"):
                data.append(line[5:].removeprefix(" "))
            continue
        # A blank line ends an event
        message = parse_json("\n".join(data))
        data = []
        if _answers(message, request_id):
            return message
    message = parse_json("\n".join(data))
    return message if _answers(message, request_id) else None


def _answers(message: Any, request_id: Any) -> bool:
    return (
        request_id is not None
        and isinstance(message, dict)
        and message.get("id") == request_id
        and ("result" in message or "error" in message)
    )


def _is_rpc_error(body: Any) -> bool:
    """Whether ``body`` is an error of the MCP transport itself, rather than one of Rollstack's API."""
    return isinstance(body, dict) and "jsonrpc" in body and isinstance(body.get("error"), dict)


def _tool_result(reply: _Reply) -> ToolResult:
    body = reply.body
    result = body.get("result") if isinstance(body, dict) else None
    if reply.status != 200 or not isinstance(result, dict):
        raise _http_error(reply)

    blocks = result.get("content")
    texts = tuple(
        block["text"]
        for block in (blocks if isinstance(blocks, list) else [])
        if isinstance(block, dict) and block.get("type") == "text" and isinstance(block.get("text"), str)
    )
    structured = result.get("structuredContent")
    answer = ToolResult(texts=texts, structured=structured if isinstance(structured, dict) else None)

    # A call that waits for the user's confirmation didn't fail: its answer carries the link they confirm it at
    if result.get("isError") and answer.code != CONFIRMATION_REQUIRED:
        raise RollstackError(_error_text(answer), code=answer.code, status=reply.status)
    return answer


def _error_text(answer: ToolResult) -> str:
    payload = answer.payload
    if isinstance(payload, dict) and isinstance(payload.get("message"), str) and payload["message"]:
        return _with_code(payload["message"], answer.code)
    return "\n".join(answer.texts).strip() or "Rollstack answered an error without a message."


def _http_error(reply: _Reply) -> RollstackError:
    """The error for an answer that isn't a tool result: Rollstack's ``{code, message}`` or a JSON-RPC error."""
    body = reply.body if isinstance(reply.body, dict) else {}
    rpc_error = body.get("error") if isinstance(body.get("error"), dict) else None
    source = rpc_error if rpc_error is not None else body
    described = source.get("message") if isinstance(source.get("message"), str) else None
    code = source.get("code")
    code = str(code) if isinstance(code, (str, int)) and not isinstance(code, bool) else None

    if reply.status == 401:
        text = "Rollstack did not accept the API key"
        text += f": {described}." if described else "."
        text += (
            " Check the key in this plugin's credentials, or create a new one in Rollstack under "
            "Settings > Connected apps."
        )
    elif described:
        text = described
    elif reply.status >= 500:
        text = f"Rollstack is unavailable right now (HTTP {reply.status}). Try again in a moment."
    elif reply.status < 300:
        text = "Rollstack sent an answer this plugin cannot read."
    else:
        text = f"Rollstack answered HTTP {reply.status} without a message."
    if reply.status == 429 and reply.retry_after:
        text += f" Wait {reply.retry_after} seconds before you call again."
    return RollstackError(_with_code(text, code), code=code, status=reply.status)


def _with_code(text: str, code: str | None) -> str:
    return f"{text} ({code})" if code else text
