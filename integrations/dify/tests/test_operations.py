"""How Dify's flat parameters become the arguments of a Rollstack tool."""

from __future__ import annotations

import pytest

from rollstack_client.operations import InputError, build_arguments


def test_parameters_go_to_their_part_under_rollstacks_names():
    arguments = build_arguments("getReportMessage", {"id": "rep-1", "messageId": "msg-1", "waitSeconds": 30})

    assert arguments == {"params": {"id": "rep-1", "messageId": "msg-1"}, "query": {"waitSeconds": 30}}


def test_what_dify_leaves_empty_is_left_out():
    arguments = build_arguments("listReports", {"name": "  ", "type": None, "limit": None, "cursor": ""})

    assert arguments == {"query": {}}


def test_a_tool_without_inputs_takes_no_arguments():
    assert build_arguments("listTemplates", {}) == {}


def test_a_part_is_sent_even_when_empty():
    # createReport requires its body, and every field in it is optional
    assert build_arguments("createReport", {}) == {"body": {}}
    assert build_arguments("startReportRun", {"id": "rep-1"}) == {"params": {"id": "rep-1"}, "body": {}}


def test_text_is_trimmed():
    arguments = build_arguments("createReport", {"name": "  Weekly sales ", "templateId": "tpl-1\n"})

    assert arguments == {"body": {"name": "Weekly sales", "templateId": "tpl-1"}}


@pytest.mark.parametrize("given", ["a, b ,c", "a\nb\nc", "a b c", '["a", "b", "c"]', ["a", " b", "c"]])
def test_ids_are_read_from_text_or_a_list(given):
    arguments = build_arguments("getReportContent", {"id": "rep-1", "slideIds": given})

    assert arguments["query"] == {"slideIds": ["a", "b", "c"]}


def test_no_ids_means_the_field_is_left_out():
    assert build_arguments("getReportContent", {"id": "rep-1", "slideIds": " , "})["query"] == {}


@pytest.mark.parametrize("given", ['{"a": 1}', "[1, 2]", "[oops", 7])
def test_ids_that_are_not_ids_are_refused(given):
    with pytest.raises(InputError, match="slideIds must be"):
        build_arguments("getReportContent", {"id": "rep-1", "slideIds": given})


@pytest.mark.parametrize(("given", "sent"), [(20, 20), (20.0, 20), ("20", 20), (" 0 ", 0), (0, 0)])
def test_whole_numbers_are_sent_as_integers(given, sent):
    arguments = build_arguments("getReportRun", {"id": "rep-1", "runId": "run-1", "waitSeconds": given})

    assert arguments["query"] == {"waitSeconds": sent}
    assert isinstance(arguments["query"]["waitSeconds"], int)


@pytest.mark.parametrize("given", [2.5, "soon", True, "1e3"])
def test_a_number_that_is_not_whole_is_refused(given):
    with pytest.raises(InputError, match="waitSeconds must be a whole number"):
        build_arguments("getReportRun", {"id": "rep-1", "runId": "run-1", "waitSeconds": given})


def test_a_list_of_objects_is_read_from_json_text():
    schedule = {"frequency": "weekly", "cronExpression": "0 9 * * 1", "startDate": "2026-11-23T09:00:00Z", "timezone": "Europe/Paris"}
    text = '[{"frequency": "weekly", "cronExpression": "0 9 * * 1", "startDate": "2026-11-23T09:00:00Z", "timezone": "Europe/Paris"}]'

    for given in (text, [schedule]):
        arguments = build_arguments("updateReportSchedules", {"id": "rep-1", "schedules": given})
        assert arguments == {"params": {"id": "rep-1"}, "body": {"schedules": [schedule]}}


def test_an_empty_list_of_schedules_is_sent_because_it_removes_them():
    assert build_arguments("updateReportSchedules", {"id": "rep-1", "schedules": "[]"})["body"] == {"schedules": []}


@pytest.mark.parametrize(
    ("given", "problem"),
    [
        ("weekly on Monday", "isn't valid JSON"),
        ('{"frequency": "weekly"}', "must be a JSON array"),
        ('["weekly"]', "must be a JSON array of objects"),
        (3, "must be a JSON array of objects"),
    ],
)
def test_schedules_that_are_not_a_json_array_of_objects_are_refused(given, problem):
    with pytest.raises(InputError, match=problem):
        build_arguments("updateReportSchedules", {"id": "rep-1", "schedules": given})


@pytest.mark.parametrize(
    ("operation", "given", "missing"),
    [
        ("getReport", {}, "id"),
        ("getReport", {"id": "  "}, "id"),
        ("getReportMessage", {"id": "rep-1"}, "messageId"),
        ("updateReportSchedules", {"id": "rep-1", "schedules": ""}, "schedules"),
        ("exportReport", {"id": "rep-1"}, "format"),
    ],
)
def test_a_missing_required_parameter_is_named(operation, given, missing):
    with pytest.raises(InputError, match=f"^{missing} is required\\.$"):
        build_arguments(operation, given)


def test_answers_to_a_clarification_are_sent_with_the_chat():
    answers = '[{"header": "Chart type", "question": "Which chart?", "answers": ["Bar chart"]}]'

    arguments = build_arguments("sendReportMessage", {"id": "rep-1", "chatId": "chat-1", "answers": answers})

    assert arguments == {
        "params": {"id": "rep-1"},
        "body": {"chatId": "chat-1", "answers": [{"header": "Chart type", "question": "Which chart?", "answers": ["Bar chart"]}]},
    }
