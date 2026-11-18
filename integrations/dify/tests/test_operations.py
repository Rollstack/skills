"""How Dify's flat parameters become the arguments of a Rollstack tool."""

from __future__ import annotations

import pytest

from rollstack_client.operations import InputError, build_arguments


def test_parameters_go_to_their_part_under_rollstacks_names():
    arguments = build_arguments("getReportMessage", {"id": "rep-1", "messageId": "msg-1", "waitSeconds": 30})

    assert arguments == {"params": {"id": "rep-1", "messageId": "msg-1"}, "query": {"waitSeconds": 30}}


def test_what_dify_leaves_empty_is_left_out():
    arguments = build_arguments("listReports", {"name": "  ", "type": None, "limit": None, "cursor": ""})

    assert arguments == {}


def test_a_tool_without_inputs_takes_no_arguments():
    assert build_arguments("listTemplates", {}) == {}


def test_a_required_part_is_sent_even_when_empty():
    # createReport requires its body, and every field in it is optional. startReportRun's body is optional
    assert build_arguments("createReport", {}) == {"body": {}}
    assert build_arguments("startReportRun", {"id": "rep-1"}) == {"params": {"id": "rep-1"}}


def test_text_is_trimmed():
    arguments = build_arguments("createReport", {"name": "  Weekly sales ", "templateId": "tpl-1\n"})

    assert arguments == {"body": {"name": "Weekly sales", "templateId": "tpl-1"}}


@pytest.mark.parametrize("given", ["a, b ,c", "a\nb\nc", "a,,b,\nc", '["a", "b", "c"]', ["a", " b", "c"]])
def test_lists_are_read_from_text_or_a_list(given):
    arguments = build_arguments("getReportContent", {"id": "rep-1", "slideIds": given})

    assert arguments["query"] == {"slideIds": ["a", "b", "c"]}


def test_a_list_is_split_on_commas_only():
    # Values hold no comma, but some hold spaces
    arguments = build_arguments("updateReportEmailConfig", {"id": "rep-1", "to": "ada@example.com, grace@example.com"})

    assert arguments["body"]["to"] == ["ada@example.com", "grace@example.com"]


def test_an_empty_list_means_the_field_is_left_out():
    assert build_arguments("getReportContent", {"id": "rep-1", "slideIds": " , "}) == {"params": {"id": "rep-1"}}


@pytest.mark.parametrize("given", ['{"a": 1}', "[1, 2]", "[oops", 7, '[{"id": "a"}]'])
def test_a_list_that_is_not_strings_is_refused(given):
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


@pytest.mark.parametrize(("given", "sent"), [(True, True), (False, False), ("true", True), ("False", False), ("1", True), (0, False)])
def test_booleans_are_read_from_true_or_false(given, sent):
    arguments = build_arguments("startReportRun", {"id": "rep-1", "repairSlides": given})

    assert arguments["body"] == {"repairSlides": sent}


def test_a_boolean_that_is_neither_is_refused():
    with pytest.raises(InputError, match="repairSlides must be true or false"):
        build_arguments("startReportRun", {"id": "rep-1", "repairSlides": "maybe"})


def test_structured_inputs_are_read_from_json_text():
    schedule = {"frequency": "weekly", "cronExpression": "0 9 * * 1", "startDate": "2026-11-23T09:00:00Z", "timezone": "Europe/Paris"}
    text = '[{"frequency": "weekly", "cronExpression": "0 9 * * 1", "startDate": "2026-11-23T09:00:00Z", "timezone": "Europe/Paris"}]'

    for given in (text, [schedule]):
        arguments = build_arguments("updateReportSchedules", {"id": "rep-1", "schedules": given})
        assert arguments == {"params": {"id": "rep-1"}, "body": {"schedules": [schedule]}}


def test_an_empty_list_of_schedules_is_sent_because_it_removes_them():
    assert build_arguments("updateReportSchedules", {"id": "rep-1", "schedules": "[]"})["body"] == {"schedules": []}


def test_a_source_is_added_from_json_text():
    sources = '[{"datasetId": "ds-1"}]'

    arguments = build_arguments("addReportDatasheets", {"id": "rep-1", "sources": sources})

    assert arguments == {"params": {"id": "rep-1"}, "body": {"sources": [{"datasetId": "ds-1"}]}}


def test_structured_input_that_is_not_json_is_refused():
    with pytest.raises(InputError, match="schedules must be JSON text, and it isn't valid JSON"):
        build_arguments("updateReportSchedules", {"id": "rep-1", "schedules": "weekly on Monday"})


@pytest.mark.parametrize(
    ("operation", "given", "missing"),
    [
        ("getReport", {}, "id"),
        ("getReport", {"id": "  "}, "id"),
        ("getReportMessage", {"id": "rep-1"}, "messageId"),
        ("updateReportSchedules", {"id": "rep-1", "schedules": ""}, "schedules"),
        ("exportReport", {"id": "rep-1"}, "format"),
        ("createDataset", {"name": "Sales"}, "csv"),
        ("searchDashboards", {"type": "Tableau"}, "id"),
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


def test_a_connection_search_goes_to_its_connection():
    arguments = build_arguments("searchDashboards", {"type": "Tableau", "id": "conn-1", "query": "Sales"})

    assert arguments == {"params": {"type": "Tableau", "id": "conn-1"}, "query": {"query": "Sales"}}
