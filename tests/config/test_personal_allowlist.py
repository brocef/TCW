"""What a personal file may set (TCW-72 AC 6, 7, 15, 18, and Design 4.6)."""

from __future__ import annotations

import pytest

from tcw.config import PERSONAL_KEYS, load_config
from tests.config.conftest import problem_lines
from tests.work.jira.conftest import jira_config


def nested(dotted: str, value) -> dict:
    """`a.b.c: v` as `{a: {b: {c: v}}}`."""
    out = value
    for key in reversed(dotted.split(".")):
        out = {key: out}
    return out


SHARED = [
    ("id", "other"),
    ("work.backend", "jira"),
    ("work.path", "elsewhere"),
    ("work.tags", ["a"]),
    ("work.documentation", []),
    ("work.hooks.timeout", 5),
    ("work.hooks.output-cap", 10),
    ("work.stages.spec.enabled", False),
    ("work.stages.spec.pre", [{"command": "true"}]),
    ("work.stages.spec.status", "Doing"),
    ("taxonomy.extends", ["up"]),
    ("capabilities.extends", ["up"]),
    ("projects.x.path", "../x"),
    ("projects.x.jira.credentials.email-env", "MINE"),
    ("work.jira.site", "https://example.atlassian.net"),
    ("work.jira.timeout", 3),
    ("display", "compact"),
]


@pytest.mark.parametrize("key, value", SHARED, ids=[k for k, _ in SHARED])
def test_a_shared_key_in_a_personal_file_is_one_problem(personal, key, value):
    personal.local(nested(key, value))
    config = load_config(personal.root)
    lines = problem_lines(config)
    assert len(lines) == 1, lines
    assert lines[0].startswith(f"tcw-config.local.yaml: {key}: "), lines
    assert [s.key_path for s in config.refused] == [tuple(key.split("."))]


def test_a_refused_value_is_not_merged(personal):
    personal.local({"id": "other"})
    assert load_config(personal.root).values["id"] == "p"


def test_the_stages_mapping_must_be_a_mapping(personal):
    personal.local({"work": {"stages": ["a"]}})
    lines = problem_lines(load_config(personal.root))
    assert lines == ["tcw-config.local.yaml: work.stages: must be a mapping"]


def test_the_overridable_keys_are_accepted(personal):
    personal.local({"user": {"name": "Brian"},
                    "work": {"stages": {"spec": {"prompt": [{"blob": "x"}],
                                                 "post": [{"command": "true"}]}},
                             "procedures": {"audit-backlog": [{"blob": "y"}]}}})
    assert problem_lines(load_config(personal.root)) == []


def test_credential_names_are_accepted_in_a_jira_mode_project(personal):
    personal.project({"work": jira_config("p")})
    personal.local(nested("work.jira.credentials", {"email-env": "MY_EMAIL",
                                                     "token-env": "MY_TOKEN"}))
    config = load_config(personal.root)
    assert problem_lines(config) == []
    assert (config.jira.email_env, config.jira.token_env) == ("MY_EMAIL", "MY_TOKEN")
    assert config.values["work"]["jira"]["site"] == jira_config("p")["jira"]["site"]


def test_credential_names_are_skipped_outside_jira_mode(personal):
    personal.user(nested("work.jira.credentials.email-env", "MY_EMAIL"))
    config = load_config(personal.root)
    assert config.problems == []
    assert "jira" not in config.values["work"]
    assert [(s.key_path, s.value) for s in config.skipped] == \
        [(("work", "jira", "credentials", "email-env"), "MY_EMAIL")]


def test_a_credential_name_that_is_not_a_name_is_reported_without_its_value(personal):
    personal.project({"work": jira_config("p")})
    personal.local(nested("work.jira.credentials.token-env", "abc def/123"))
    lines = problem_lines(load_config(personal.root))
    assert len(lines) == 1, lines
    assert lines[0].startswith(
        "tcw-config.local.yaml: work.jira.credentials.token-env: ")
    assert "abc def/123" not in lines[0]


def test_user_in_the_project_file_is_a_problem(personal):
    personal.project({"user": {"name": "a"}})
    config = load_config(personal.root)
    lines = problem_lines(config)
    assert len(lines) == 1 and lines[0].startswith("tcw-config.yaml: user: ")
    assert "tcw-config.local.yaml" in lines[0]
    assert str(personal.user_file) in lines[0]
    assert config.user_name is None


@pytest.mark.parametrize("user, words", [
    ({"name": " a"}, "user.name"),
    ({"name": ""}, "user.name"),
    ({"name": 5}, "user.name"),
    ({"email": "a"}, "user.email"),
])
def test_a_bad_user_entry_is_a_problem(personal, user, words):
    personal.local({"user": user})
    lines = problem_lines(load_config(personal.root))
    assert len(lines) == 1 and words in lines[0], lines


@pytest.mark.parametrize("mapping", [
    {"user": None},
    {"user": {"name": None}},
    {"work": None},
    {"work": {"stages": {"spec": {"prompt": None}}}},
])
def test_null_in_a_personal_file_is_a_problem(personal, mapping):
    personal.local(mapping)
    lines = problem_lines(load_config(personal.root))
    assert len(lines) == 1 and "null" in lines[0], lines


def test_the_allowlist_is_importable_and_exact():
    assert PERSONAL_KEYS == (
        "user.name",
        "work.stages.*.prompt",
        "work.stages.*.post",
        "work.procedures.*",
        "work.jira.credentials.email-env",
        "work.jira.credentials.token-env",
    )
    assert isinstance(PERSONAL_KEYS, tuple)
