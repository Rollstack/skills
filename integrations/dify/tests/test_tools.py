"""Each Dify tool end to end, loaded the way Dify loads it, against scripted answers from Rollstack."""

from __future__ import annotations

import base64
import json
import uuid
from typing import Any

import pytest
from dify_plugin import Tool
from dify_plugin.core.utils.class_loader import load_single_subclass_from_source
from dify_plugin.entities.tool import ToolInvokeMessage
from dify_plugin.errors.tool import ToolProviderCredentialValidationError
from dify_plugin.interfaces.tool import ToolProvider

import generate_tools
from conftest import FakeResponse, FakeSession, rpc, tool_answer
from rollstack_client import mcp
from rollstack_client.mcp import RollstackError
from rollstack_client.operations import BOOLEAN, INTEGER, JSON, LIST, NUMBER, OPERATIONS, InputError
from rollstack_client.tooling import IMAGE_SENT, IMAGE_UNREADABLE

MessageType = ToolInvokeMessage.MessageType

FILES = {operation: generate_tools.file_name(operation) for operation in OPERATIONS}

# A value of each kind of input that the plugin accepts, to call every tool with its required parameters
SAMPLES = {INTEGER: 1, NUMBER: 1, BOOLEAN: True, LIST: "a", JSON: "[]"}


@pytest.fixture
def rollstack(monkeypatch: pytest.MonkeyPatch, plugin_root):
    """Script Rollstack's answers: returns a function that sets them and gives back the session that records calls."""
    sessions: list[FakeSession] = []

    def script(*replies: Any) -> FakeSession:
        session = FakeSession(*replies)
        sessions.append(session)
        return session

    monkeypatch.setattr(mcp.requests, "Session", lambda: sessions[-1])
    return script


def load(operation: str) -> Tool:
    """The tool for ``operation``, loaded from its source file as the plugin runtime loads it."""
    name = FILES[operation]
    tool_class = load_single_subclass_from_source(
        module_name=f"tools.{name}", script_path=f"tools/{name}.py", parent_type=Tool
    )
    return tool_class.from_credentials({"rollstack_api_key": "rsk_test_only"})


def run(operation: str, parameters: dict[str, Any]) -> list[ToolInvokeMessage]:
    return list(load(operation).invoke(parameters))


def of_type(messages: list[ToolInvokeMessage], kind: MessageType) -> list[Any]:
    return [message.message for message in messages if message.type == kind]


def variables(messages: list[ToolInvokeMessage]) -> dict[str, Any]:
    return {m.variable_name: m.variable_value for m in of_type(messages, MessageType.VARIABLE)}


def sent(session: FakeSession) -> dict[str, Any]:
    (call,) = session.calls
    return call.json["params"]


def test_every_tool_has_a_class_that_calls_its_own_rollstack_tool(rollstack):
    for operation, spec in OPERATIONS.items():
        session = rollstack(tool_answer({}))
        parameters = {param.name: SAMPLES.get(param.kind, "x") for param in spec.params if param.required}
        run(operation, parameters)
        assert sent(session)["name"] == operation


def test_find_reports(rollstack):
    page = {"data": [{"id": "rep-1", "name": "Q3 Business Review", "type": "SlideDeck"}], "nextCursor": "next-1"}
    session = rollstack(tool_answer(page))

    messages = run("listReports", {"name": "review", "type": "SlideDeck", "limit": 10})

    assert sent(session) == {"name": "listReports", "arguments": {"query": {"name": "review", "type": "SlideDeck", "limit": 10}}}
    assert [m.json_object for m in of_type(messages, MessageType.JSON)] == [page]
    assert of_type(messages, MessageType.TEXT) == []
    assert variables(messages) == {"data": page["data"], "nextCursor": "next-1"}


def test_a_variable_is_always_returned_and_empty_when_the_answer_has_no_value(rollstack):
    rollstack(tool_answer({"data": [], "nextCursor": None}))

    # A workflow node that reads nextCursor finds it on the last page too
    assert variables(run("listReports", {})) == {"data": [], "nextCursor": ""}


def test_message_the_slides_agent_then_read_its_reply(rollstack):
    queued = {"chatId": "chat-1", "messageId": "msg-1", "status": "running", "appUrl": "https://rollstack.example/chat"}
    session = rollstack(tool_answer(queued))

    messages = run("sendReportMessage", {"id": "rep-1", "content": "Add a slide on churn", "slideIds": "s-1, s-2"})

    arguments = sent(session)["arguments"]
    assert arguments["params"] == {"id": "rep-1"}
    assert arguments["body"] == {"content": "Add a slide on churn", "slideIds": ["s-1", "s-2"]}
    # A write carries a fresh idempotency key, so sending it again after a gateway error runs it once
    assert uuid.UUID(arguments["idempotencyKey"]).version == 4
    assert variables(messages) == queued

    reply = {"id": "reply-1", "status": "completed", "type": "result", "content": "Added.", "changedSlideIds": ["s-9"]}
    done = {**queued, "status": "completed", "stage": None, "replies": [reply]}
    session = rollstack(tool_answer(done))

    messages = run("getReportMessage", {"id": "rep-1", "messageId": "msg-1", "waitSeconds": 30})

    assert sent(session)["arguments"] == {"params": {"id": "rep-1", "messageId": "msg-1"}, "query": {"waitSeconds": 30}}
    assert "idempotencyKey" not in sent(session)["arguments"]
    assert variables(messages)["status"] == "completed"
    assert variables(messages)["replies"] == [reply]


def test_create_a_report_in_a_template(rollstack):
    created = {"id": "rep-2", "name": "Weekly sales", "type": "SlideDeck", "folderId": None, "appUrl": "https://rollstack.example/slides/rep-2"}
    session = rollstack(tool_answer(created))

    messages = run("createReport", {"name": "Weekly sales", "templateId": "tpl-1"})

    assert sent(session)["arguments"]["body"] == {"name": "Weekly sales", "templateId": "tpl-1"}
    returned = variables(messages)
    # Every field of the answer is a variable, empty when the answer has no value for it
    assert list(returned) == list(OPERATIONS["createReport"].variable_types)
    assert {name: returned[name] for name in created} == {**created, "folderId": ""}
    assert (returned["owner"], returned["running"], returned["sharedWith"], returned["fileUrl"]) == ({}, False, [], "")


def test_refresh_a_report(rollstack):
    session = rollstack(tool_answer({"runId": "run-1", "started": True}))

    messages = run("startReportRun", {"id": "rep-1"})

    arguments = sent(session)["arguments"]
    assert arguments["params"] == {"id": "rep-1"} and "body" not in arguments
    assert variables(messages) == {"runId": "run-1", "started": True, "code": "", "message": ""}


def test_a_run_that_would_email_people_waits_for_the_user(rollstack):
    waiting = {"code": "confirmation-required", "message": "Confirm it in Rollstack: https://rollstack.example/confirm"}
    rollstack(tool_answer(waiting, is_error=True))

    messages = run("startReportRun", {"id": "rep-1"})

    # Nothing ran. The tool answers what Rollstack said, with the link the user confirms at as text too
    assert [m.json_object for m in of_type(messages, MessageType.JSON)] == [waiting]
    assert [m.text for m in of_type(messages, MessageType.TEXT)] == [waiting["message"]]
    assert variables(messages) == {"runId": "", "started": False, **waiting}


def test_read_then_replace_schedules(rollstack):
    schedule = {"id": "sch-1", "frequency": "weekly", "cronExpression": "0 9 * * 1", "timezone": "Europe/Paris"}
    rollstack(tool_answer([schedule]))

    messages = run("getReportSchedules", {"id": "rep-1"})

    # A list answers one JSON message per item, which is the list in the tool's json output
    assert [m.json_object for m in of_type(messages, MessageType.JSON)] == [schedule]
    assert variables(messages) == {"schedules": [schedule]}

    session = rollstack(tool_answer([schedule]))
    new = '[{"frequency": "weekly", "cronExpression": "0 9 * * 1", "startDate": "2026-11-23T09:00:00Z", "timezone": "Europe/Paris"}]'

    run("updateReportSchedules", {"id": "rep-1", "schedules": new})

    assert sent(session)["arguments"]["body"] == {
        "schedules": [{"frequency": "weekly", "cronExpression": "0 9 * * 1", "startDate": "2026-11-23T09:00:00Z", "timezone": "Europe/Paris"}]
    }


def test_a_report_without_schedules_answers_an_empty_list(rollstack):
    rollstack(tool_answer([]))

    messages = run("getReportSchedules", {"id": "rep-1"})

    assert of_type(messages, MessageType.JSON) == []
    assert [m.text for m in of_type(messages, MessageType.TEXT)] == ["[]"]
    assert variables(messages) == {"schedules": []}


def test_export_answers_the_link(rollstack):
    exported = {"url": "https://files.rollstack.example/q3.pdf", "expiresAt": "2026-11-17T16:15:00Z"}
    session = rollstack(tool_answer(exported))

    messages = run("exportReport", {"id": "rep-1", "format": "pdf"})

    assert sent(session)["arguments"]["body"] == {"format": "pdf"}
    assert variables(messages) == exported


def test_structured_content_is_not_repeated_as_text(rollstack):
    content = {"slides": [{"id": "s-1", "title": "Revenue"}]}
    rollstack(tool_answer(content, structured=content))

    messages = run("getReportContent", {"id": "rep-1", "slideIds": "s-1"})

    assert [m.json_object for m in of_type(messages, MessageType.JSON)] == [content]
    assert of_type(messages, MessageType.TEXT) == []


def test_an_answer_that_is_not_json_is_text(rollstack):
    rollstack(tool_answer("The report has no slides yet."))

    messages = run("getReportContent", {"id": "rep-1"})

    assert [m.text for m in of_type(messages, MessageType.TEXT)] == ["The report has no slides yet."]
    assert variables(messages) == {"slides": []}


def test_a_rollstack_error_fails_the_tool(rollstack):
    session = rollstack(tool_answer({"code": "forbidden", "message": "Only editors of the report can message the slides agent."}, is_error=True))

    with pytest.raises(RollstackError, match=r"Only editors of the report .* \(forbidden\)"):
        run("sendReportMessage", {"id": "rep-1", "content": "hi"})

    # The connection is given back whether the call worked or not
    assert session.closed


def test_the_connection_is_closed_after_a_call(rollstack):
    session = rollstack(tool_answer({"data": []}))

    run("listTemplates", {})

    assert session.closed


def test_a_bad_parameter_fails_before_anything_is_sent(rollstack):
    session = rollstack()

    with pytest.raises(InputError, match="schedules must be JSON text"):
        run("updateReportSchedules", {"id": "rep-1", "schedules": "every Monday"})

    assert session.calls == []


def test_an_email_held_for_confirmation_answers_the_link(rollstack):
    waiting = {"code": "confirmation-required", "message": "Confirm it in Rollstack: https://rollstack.example/confirm"}
    session = rollstack(tool_answer(waiting, is_error=True))

    messages = run("sendReportEmail", {"id": "rep-1"})

    assert sent(session)["name"] == "sendReportEmail"
    assert [m.text for m in of_type(messages, MessageType.TEXT)] == [waiting["message"]]
    assert variables(messages) == waiting


def test_upload_a_csv_then_add_it_to_a_deck(rollstack):
    session = rollstack(tool_answer({"id": "ds-1", "name": "Sales", "columns": ["region", "revenue"]}))

    messages = run("createDataset", {"name": "Sales", "csv": "region,revenue\nNorth,120\n"})

    assert sent(session)["arguments"]["body"] == {"name": "Sales", "csv": "region,revenue\nNorth,120"}
    assert variables(messages)["id"] == "ds-1"

    session = rollstack(tool_answer({"datasheetIds": ["dsh-1"]}))

    messages = run("addReportDatasheets", {"id": "rep-1", "sources": '[{"datasetId": "ds-1"}]'})

    assert sent(session)["arguments"]["body"] == {"sources": [{"datasetId": "ds-1"}]}
    assert variables(messages) == {"datasheetIds": ["dsh-1"]}


def test_a_list_answer_is_one_variable(rollstack):
    connections = [{"id": "c-1", "type": "Tableau", "name": "Tableau"}, {"id": "c-2", "type": "Snowflake", "name": "Warehouse"}]
    rollstack(tool_answer(connections))

    messages = run("listConnections", {})

    assert [m.json_object for m in of_type(messages, MessageType.JSON)] == connections
    assert variables(messages) == {"connections": connections}


def test_a_field_dify_names_itself_stays_in_the_json_output(rollstack):
    memory = {"id": "mem-1", "text": "Our fiscal year starts in February.", "category": "general"}
    rollstack(tool_answer(memory))

    messages = run("createMemory", {"text": memory["text"]})

    assert [m.json_object for m in of_type(messages, MessageType.JSON)] == [memory]
    assert "text" not in variables(messages)


def test_slide_images_in_the_answer_are_sent_as_image_files(rollstack):
    jpeg = b"\xff\xd8\xff\xe0 a slide"
    slide = {"id": "s-1", "mimeType": "image/jpeg", "data": base64.b64encode(jpeg).decode()}
    rollstack(tool_answer({"slides": [slide, {**slide, "id": "s-2", "data": "not base64!"}]}))

    messages = run("getReportSlideImages", {"id": "rep-1", "slideIds": "s-1, s-2"})

    # The model gets the slides without their base64 data, and the user each one as a file. A slide whose data
    # isn't base64 goes out as no file, and says so
    (shown,) = [m.json_object for m in of_type(messages, MessageType.JSON)]
    assert [item["data"] for item in shown["slides"]] == [IMAGE_SENT, IMAGE_UNREADABLE]
    blobs = [m for m in messages if m.type == MessageType.BLOB]
    assert [(m.message.blob, m.meta) for m in blobs] == [(jpeg, {"mime_type": "image/jpeg"})]
    assert variables(messages)["slides"][0]["data"] == IMAGE_SENT


def test_an_image_block_that_is_not_base64_is_reported(rollstack):
    rollstack(rpc({"content": [{"type": "image", "data": "not base64!", "mimeType": "image/png"}]}))

    messages = run("getReportSlideImages", {"id": "rep-1", "slideIds": "s-1"})

    assert [m.text for m in of_type(messages, MessageType.TEXT)] == ["Rollstack sent an image (image/png) that could not be read."]
    assert [m for m in messages if m.type == MessageType.BLOB] == []


def test_an_idempotency_key_the_agent_gives_is_sent_as_it_is(rollstack):
    # Rollstack's descriptions tell the agent to send one, so that a call it sends again runs once
    session = rollstack(tool_answer({"id": "rep-2"}))

    run("convertReport", {"id": "rep-1", "idempotencyKey": "convert-rep-1"})

    assert sent(session)["arguments"]["idempotencyKey"] == "convert-rep-1"


def test_null_moves_a_folder_to_the_top_level(rollstack):
    session = rollstack(tool_answer({"id": "fold-1", "parentFolderId": None}))

    run("updateFolder", {"id": "fold-1", "parentFolderId": " null "})

    assert sent(session)["arguments"]["body"] == {"parentFolderId": None}


def test_an_image_block_is_sent_as_an_image_file(rollstack):
    png = b"\x89PNG a slide"
    blocks = [{"type": "text", "text": "Slide 1"}, {"type": "image", "data": base64.b64encode(png).decode(), "mimeType": "image/png"}]
    rollstack(rpc({"content": blocks}))

    messages = run("getReportSlideImages", {"id": "rep-1", "slideIds": "s-1"})

    assert [m.text for m in of_type(messages, MessageType.TEXT)] == ["Slide 1"]
    assert [(m.message.blob, m.meta) for m in messages if m.type == MessageType.BLOB] == [(png, {"mime_type": "image/png"})]


def test_a_boolean_and_a_select_reach_rollstack(rollstack):
    session = rollstack(tool_answer({"runId": "run-1", "started": True}))

    run("startReportRun", {"id": "rep-1", "repairSlides": "false"})

    assert sent(session)["arguments"]["body"] == {"repairSlides": False}

    session = rollstack(tool_answer([]))

    run("searchDashboards", {"type": "Tableau", "id": "conn-1", "query": "Sales"})

    assert sent(session)["arguments"] == {"params": {"type": "Tableau", "id": "conn-1"}, "query": {"query": "Sales"}}


def load_provider() -> ToolProvider:
    provider_class = load_single_subclass_from_source(
        module_name="provider.rollstack", script_path="provider/rollstack.py", parent_type=ToolProvider
    )
    return provider_class()


def test_a_working_key_is_accepted(rollstack):
    me = {"id": 1, "email": "ada@example.com", "name": "Ada", "organization": {"id": "org-1", "name": "Example", "role": "member"}}
    session = rollstack(FakeResponse(200, {**me, "apiKey": {"id": "key-1", "scopes": ["slide_decks:read"]}}))

    load_provider().validate_credentials({"rollstack_api_key": "rsk_test_only"})

    (call,) = session.calls
    assert (call.method, call.url) == ("GET", "https://api.rollstack.com/public/v1/me")


def test_a_refused_key_fails_validation_with_what_to_do(rollstack):
    rollstack(FakeResponse(401, {"code": "api-key-invalid", "message": "Invalid API key"}))

    with pytest.raises(ToolProviderCredentialValidationError, match="Settings > Connected apps") as raised:
        load_provider().validate_credentials({"rollstack_api_key": "rsk_test_only"})

    assert "rsk_test_only" not in str(raised.value)


def test_a_missing_key_fails_validation(rollstack):
    with pytest.raises(ToolProviderCredentialValidationError, match="API key is missing"):
        load_provider().validate_credentials({})
