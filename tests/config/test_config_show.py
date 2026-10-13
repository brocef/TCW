"""`tcw config show [--origin]` (TCW-72 Design 8; AC 12 and AC 8's case)."""

from __future__ import annotations

import re

import pytest
import yaml

from tcw.config import load_config
from tcw.config_cli import render
from tests.config.conftest import tcw

COMMENT = re.compile(r"  # (.*)$")


def project(personal, work=None):
    (personal.root / "docs" / "work").mkdir(parents=True, exist_ok=True)
    if work is not None:
        personal.project({"work": work})
    return personal.root


def comments(out: str) -> list[str]:
    return [m.group(1) for line in out.splitlines() if (m := COMMENT.search(line))]


def test_plain_show_reads_back_as_the_merged_values(personal):
    root = project(personal)
    result = tcw(root, "config", "show")
    assert result.code == 0, result
    values = load_config(root).values
    assert yaml.safe_load(result.out) == values
    assert {"builtin": True} in values["work"]["stages"]["spec"]["prompt"]
    assert "        - builtin: true  # tcw/work/prompts/spec.md" in result.out.splitlines()
    assert "      - builtin: true  # tcw/work/procedures/search.md" in \
        result.out.splitlines()


def test_origin_comments_without_personal_files(personal):
    root = project(personal, {"tags": ["a"]})
    result = tcw(root, "config", "show", "--origin")
    assert result.code == 0, result
    assert yaml.safe_load(result.out) == load_config(root).values
    found = comments(result.out)
    assert found and all(c.split(",")[0] in ("built-in", "project") for c in found)
    assert "project" in found


@pytest.mark.parametrize("flags", [(), ("--origin",)])
def test_the_same_output_every_run(personal, flags):
    root = project(personal, {"tags": ["b", "a"]})
    personal.local({"work": {"stages": {"spec": {"prompt": [{"blob": "x"}]}}}})
    first = tcw(root, "config", "show", *flags)
    assert first.code == 0, first
    assert tcw(root, "config", "show", *flags).out == first.out


def test_a_refused_key_stops_plain_show(personal):
    root = project(personal)
    personal.local({"id": "other",
                    "work": {"stages": {"spec": {"prompt": [{"blob": "x"}]}}}})
    result = tcw(root, "config", "show")
    assert (result.code, result.out) == (1, ""), result
    assert result.err.startswith("tcw config show: tcw-config.local.yaml: id: ")


def test_origin_still_prints_and_marks_the_refused_key(personal):
    root = project(personal)
    personal.local({"id": "other",
                    "work": {"stages": {"spec": {"prompt": [{"blob": "x"}]}}}})
    result = tcw(root, "config", "show", "--origin")
    assert result.code == 1, result
    assert yaml.safe_load(result.out) == load_config(root).values
    assert yaml.safe_load(result.out)["id"] == "p"
    refused = [l for l in result.out.splitlines() if l.startswith("# refused:")]
    assert len(refused) == 1
    assert all(w in refused[0] for w in ("id", "other", "tcw-config.local.yaml"))
    [blob] = [l for l in result.out.splitlines() if "blob: x" in l]
    assert blob.endswith("  # local: tcw-config.local.yaml"), blob
    assert "tcw-config.local.yaml: id: " in result.err


def test_credential_names_outside_jira_mode_are_listed_as_skipped(personal):
    root = project(personal)
    personal.user({"work": {"jira": {"credentials": {"email-env": "MY_EMAIL"}}}})
    config = load_config(root)
    assert config.problems == [] and "jira" not in config.values["work"]
    result = tcw(root, "config", "show", "--origin")
    assert result.code == 0, result
    skipped = [l for l in result.out.splitlines() if l.startswith("# skipped:")]
    assert len(skipped) == 1
    assert "work.jira.credentials.email-env" in skipped[0]
    # A value under a key ending in `-env` is never echoed.
    assert "MY_EMAIL" not in skipped[0] and "(value not shown)" in skipped[0]


def test_an_unreadable_personal_file_contributes_nothing(personal):
    root = project(personal)
    personal.local("work: [unclosed\n")
    result = tcw(root, "config", "show", "--origin")
    assert result.code == 1, result
    assert yaml.safe_load(result.out) == load_config(root).values
    assert "tcw-config.local.yaml" in result.err


def test_an_unreadable_project_file_prints_nothing(personal):
    root = project(personal)
    personal.project_file.write_text("id: [unclosed\n")
    result = tcw(root, "config", "show", "--origin")
    assert (result.code, result.out) == (1, ""), result


@pytest.mark.parametrize("value", [
    "plain", "with: colon", "#hash", "- dash", "yes", "1.5", "", " lead", "trail ",
    "multi\nline", 'quote"d', "x, y", "[x]", "{x}", "null", "~", "a #b",
])
def test_any_string_reads_back_as_itself(personal, value):
    root = project(personal, {"tags": ["a"],
                              "stages": {"spec": {"prompt": [{"blob": value},
                                                             {"blob": value,
                                                              "when": {"tags": ["a"]}}]}}})
    config = load_config(root)
    assert config.problems == [], config.problems
    for origin in (False, True):
        assert yaml.safe_load(render(config, origin=origin)) == config.values


def test_config_show_outside_a_project(tmp_path):
    result = tcw(tmp_path, "config", "show")
    assert (result.code, result.out) == (1, "")
    assert result.err.startswith("tcw config show: ")
