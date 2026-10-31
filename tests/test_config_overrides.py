"""Reading the override variables (TCW-109 Design 4.2-4.7), on literal
mappings, so every rule is tested without a project."""

from __future__ import annotations

import pytest

from tcw.config_keys import read_overrides

SHARED = "is a shared key; an environment variable cannot set it"


def read(**variables):
    found, problems = read_overrides(variables)
    return found, [p.message for p in problems]


def one_problem(**variables) -> str:
    found, problems = read(**variables)
    assert found == {}, found
    assert len(problems) == 1, problems
    return problems[0]


@pytest.mark.parametrize("name", ["TCW_PROCEDURE_X", "TCW_PROJECT_CORE", "TCW_JIRA_EMAIL",
                                  "TCW_STDIN_TIMEOUT", "TCW_CONFIG_DIR",
                                  "TCW_NO_PERSONAL_CONFIG", "PATH", "XTCW_A__B"])
def test_design_4_2_other_variables_are_not_overrides(name):
    assert read(**{name: "1"}) == ({}, [])


@pytest.mark.parametrize("name", ["TCW__ALL__WORK_TAGS", "TCW_WORK__", "TCW_WORK___APP",
                                  "TCW_user_NAME__APP"])
def test_ac20_a_malformed_name(name):
    message = one_problem(**{name: "x"})
    assert message.startswith(f"{name}: ")
    assert "TCW_<KEY>__<PROJECT>" in message


@pytest.mark.parametrize("name", ["TCW_WORK_STAGES_SPEC_PROMPTS__APP", "TCW_TCW_VERSION__APP",
                                  "TCW_WORK_STAGES_DESIGN_PROMPT__APP"])
def test_ac20_an_unknown_key(name):
    message = one_problem(**{name: "x"})
    assert message.startswith(f"{name}: no configuration key is written ")


def test_design_4_4_the_project_part():
    found, problems = read(TCW_USER_NAME__MY_PROJ="Robin")
    assert problems == []
    assert [(o.project, o.key_path, o.value) for o in found["my-proj"]] == [
        ("my-proj", ("user", "name"), "Robin")]


@pytest.mark.parametrize("name, value, key", [
    ("TCW_ID__APP", "x", "id"), ("TCW_PARENTS__APP", "[core]", "parents"),
    ("TCW_CHILDREN__APP", "[kid]", "children"), ("TCW_WORK_PATH__APP", "/tmp/x", "work.path"),
    ("TCW_WORK_REPOSITORY__APP", "x", "work.repository"),
    ("TCW_TAXONOMY_PATH__APP", "x", "taxonomy.path"),
    ("TCW_WORK_BACKEND__APP", "jira", "work.backend"), ("TCW_WORK_TAGS__APP", "[a]", "work.tags"),
    ("TCW_WORK_JIRA_SITE__APP", "https://x.example.net", "work.jira.site"),
    ("TCW_WORK_STAGES_SPEC_STATUS__APP", "x", "work.stages.spec.status"),
    ("TCW_WORK_STAGES_SPEC_PRE__APP", "[]", "work.stages.spec.pre"),
])
def test_ac21_only_allowed_keys(name, value, key):
    assert one_problem(**{name: value}) == f"{name}: {key} {SHARED}"


def test_ac21_a_mapping_keeps_what_is_allowed():
    found, problems = read(TCW_WORK_STAGES_SPEC__APP="{prompt: [{blob: p}], status: x}")
    assert problems == [f"TCW_WORK_STAGES_SPEC__APP: work.stages.spec.status {SHARED}"]
    # A variable with a problem is not applied at all: it stops every command.
    assert found == {}


@pytest.mark.parametrize("value", ["no", "null", "1.0", "on"])
def test_ac22_text_is_read_as_written(value):
    found, problems = read(TCW_USER_NAME__APP=value)
    assert problems == []
    assert found["app"][0].value == value


@pytest.mark.parametrize("name, value, words", [
    ("TCW_WORK_STAGES_SPEC_PROMPT__APP", "hello", "work.stages.spec.prompt must be a list"),
    ("TCW_WORK_STAGES_SPEC_PROMPT__APP", "[unclosed", "is not valid YAML"),
    ("TCW_WORK_STAGES_SPEC_PROMPT__APP", "null",
     "null has no meaning in an environment variable"),
    ("TCW_WORK_STAGES_SPEC__APP", "[a]", "work.stages.spec must be a mapping"),
    ("TCW_WORK_STAGES_SPEC__APP", "{prompt: [], prompt: []}", "a key appears twice"),
    ("TCW_USER_NAME__APP", " x", "must be a name"),
    ("TCW_WORK_JIRA_CREDENTIALS_EMAIL_ENV__APP", "lower", "must name an environment variable"),
])
def test_ac22_values_by_kind(name, value, words):
    message = one_problem(**{name: value})
    assert message.startswith(f"{name}: ")
    assert words in message


@pytest.mark.parametrize("name", ["TCW_WORK_STAGES_SPEC_PROMPT__APP",
                                  "TCW_WORK_JIRA_CREDENTIALS_TOKEN_ENV__APP",
                                  "TCW_WORK_STAGES_SPEC__APP", "TCW_WORK_TAGS__APP",
                                  "TCW_X__APP", "TCW_WORK_STAGES_SPEC_PROMPTS__APP"])
@pytest.mark.parametrize("value", ["s3cr3t-token", "[s3cr3t-token", "{s3cr3t-token: [}"])
def test_no_message_holds_the_value(name, value):
    _, problems = read(**{name: value})
    assert problems
    assert not any("s3cr3t" in p for p in problems)


def test_ac22_a_chain_list_may_inherit():
    found, problems = read(TCW_WORK_STAGES_SPEC_PROMPT__APP="[{blob: hello}, {inherit: true}]")
    assert problems == []
    assert found["app"][0].value == [{"blob": "hello"}, {"inherit": True}]


def test_ac23_fewest_parts_first_whatever_the_order():
    for order in ([("TCW_WORK_STAGES_SPEC_PROMPT__APP", "[{blob: one}]"),
                   ("TCW_WORK_STAGES_SPEC__APP", "{prompt: [{blob: whole}]}")],
                  [("TCW_WORK_STAGES_SPEC__APP", "{prompt: [{blob: whole}]}"),
                   ("TCW_WORK_STAGES_SPEC_PROMPT__APP", "[{blob: one}]")]):
        found, problems = read_overrides(dict(order))
        assert problems == []
        assert [o.name for o in found["app"]] == ["TCW_WORK_STAGES_SPEC__APP",
                                                  "TCW_WORK_STAGES_SPEC_PROMPT__APP"]
