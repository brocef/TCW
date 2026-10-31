"""`tcw project config [--origin]` (TCW-72 Design 8; AC 12 and AC 8's case)."""

from __future__ import annotations

import re

import pytest
import yaml

from tcw.config import load_config
from tcw.config_cli import render
from tests.config.conftest import tcw
from tests.projectfiles import write_config_file

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
    result = tcw(root, "project", "config")
    assert result.code == 0, result
    values = load_config(root).values
    assert yaml.safe_load(result.out) == values
    assert {"builtin": True} in values["work"]["stages"]["spec"]["prompt"]
    assert "        - builtin: true  # tcw/work/prompts/spec.md" in result.out.splitlines()
    assert "      - builtin: true  # tcw/work/procedures/search.md" in \
        result.out.splitlines()


def test_origin_comments_without_personal_files(personal):
    root = project(personal, {"tags": ["a"]})
    result = tcw(root, "project", "config", "--origin")
    assert result.code == 0, result
    assert yaml.safe_load(result.out) == load_config(root).values
    found = comments(result.out)
    assert found and all(c.split(",")[0] == "built-in"
                         or c == "p, project .tcw/tcw-config.yaml" for c in found), found
    assert "p, project .tcw/tcw-config.yaml" in found


@pytest.mark.parametrize("flags", [(), ("--origin",)])
def test_the_same_output_every_run(personal, flags):
    root = project(personal, {"tags": ["b", "a"]})
    personal.local({"work": {"stages": {"spec": {"prompt": [{"blob": "x"}]}}}})
    first = tcw(root, "project", "config", *flags)
    assert first.code == 0, first
    assert tcw(root, "project", "config", *flags).out == first.out


def test_a_refused_key_stops_plain_show(personal):
    root = project(personal)
    personal.local({"id": "other",
                    "work": {"stages": {"spec": {"prompt": [{"blob": "x"}]}}}})
    result = tcw(root, "project", "config")
    assert (result.code, result.out) == (1, ""), result
    assert result.err.startswith("tcw project config: .tcw/tcw-config.local.yaml: id: ")


def test_origin_still_prints_and_marks_the_refused_key(personal):
    root = project(personal)
    personal.local({"id": "other",
                    "work": {"stages": {"spec": {"prompt": [{"blob": "x"}]}}}})
    result = tcw(root, "project", "config", "--origin")
    assert result.code == 1, result
    assert yaml.safe_load(result.out) == load_config(root).values
    assert yaml.safe_load(result.out)["id"] == "p"
    refused = [l for l in result.out.splitlines() if l.startswith("# refused:")]
    assert len(refused) == 1
    assert all(w in refused[0] for w in ("id", "other", ".tcw/tcw-config.local.yaml"))
    [blob] = [l for l in result.out.splitlines() if "blob: x" in l]
    assert blob.endswith("  # p, local .tcw/tcw-config.local.yaml"), blob
    assert ".tcw/tcw-config.local.yaml: id: " in result.err


def test_credential_names_outside_jira_mode_are_listed_as_skipped(personal):
    root = project(personal)
    personal.user({"work": {"jira": {"credentials": {"email-env": "MY_EMAIL"}}}})
    config = load_config(root)
    assert config.problems == [] and "jira" not in config.values["work"]
    result = tcw(root, "project", "config", "--origin")
    assert result.code == 0, result
    skipped = [l for l in result.out.splitlines() if l.startswith("# skipped:")]
    assert len(skipped) == 1
    assert "work.jira.credentials.email-env" in skipped[0]
    # A value under a key ending in `-env` is never echoed.
    assert "MY_EMAIL" not in skipped[0] and "(value not shown)" in skipped[0]


def test_credential_names_from_a_variable_name_the_variable(personal, monkeypatch):
    """A variable has no file, so the `# skipped:` line names the variable, in
    the form the values' own comments use."""
    root = project(personal)
    name = "TCW_WORK_JIRA_CREDENTIALS_EMAIL_ENV__P"
    monkeypatch.setenv(name, "MY_EMAIL")
    result = tcw(root, "project", "config", "--origin")
    assert result.code == 0, result
    [skipped] = [l for l in result.out.splitlines() if l.startswith("# skipped:")]
    assert skipped.endswith(f"Jira-mode project, environment {name})"), skipped
    assert "MY_EMAIL" not in skipped

def test_an_unreadable_personal_file_contributes_nothing(personal):
    root = project(personal)
    personal.local("work: [unclosed\n")
    result = tcw(root, "project", "config", "--origin")
    assert result.code == 1, result
    assert yaml.safe_load(result.out) == load_config(root).values
    assert ".tcw/tcw-config.local.yaml" in result.err


def test_an_unreadable_project_file_prints_nothing(personal):
    root = project(personal)
    write_config_file(personal.project_file, "id: [unclosed\n")
    result = tcw(root, "project", "config", "--origin")
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
    result = tcw(tmp_path, "project", "config")
    assert (result.code, result.out) == (1, "")
    assert result.err.startswith("tcw project config: ")


# -- A secret pasted where a variable's name belongs (review finding C1) -----------------

SECRET = "ATATT3xFfGF0-secret-token"


def _jira_work(token_env=None):
    from tests.work.jira.conftest import jira_config
    work = jira_config()
    if token_env is not None:
        work["jira"]["credentials"]["token-env"] = token_env
    return work


@pytest.mark.parametrize("where", ["project", "local"])
def test_a_pasted_token_is_never_printed(personal, where):
    root = project(personal, _jira_work(SECRET if where == "project" else None))
    if where == "local":
        personal.local({"work": {"jira": {"credentials": {"token-env": SECRET}}}})
    for flags in ((), ("--origin",)):
        result = tcw(root, "project", "config", *flags)
        assert result.code == 1, result
        assert SECRET not in result.out and SECRET not in result.err, result
    shown = tcw(root, "project", "config", "--origin").out
    [line] = [l for l in shown.splitlines() if "token-env:" in l]
    assert '"(value not shown)"' in line, line
    assert yaml.safe_load(shown)["work"]["jira"]["credentials"]["token-env"] == \
        "(value not shown)"


def test_a_variable_name_is_printed_as_itself(personal):
    root = project(personal, _jira_work())
    personal.local({"work": {"jira": {"credentials": {"token-env": "MY_TOKEN"}}}})
    result = tcw(root, "project", "config")
    assert result.code == 0, result
    assert yaml.safe_load(result.out) == load_config(root).values
    assert "token-env: MY_TOKEN" in result.out


def test_a_refused_token_is_never_printed(personal):
    root = project(personal)
    personal.local({"projects": {"x": {"jira": {"credentials": {"token-env": SECRET}}},
                                 "y": [{"token-env": SECRET}]}})
    result = tcw(root, "project", "config", "--origin")
    assert result.code == 1, result
    assert SECRET not in result.out and SECRET not in result.err, result


# -- Every string and value reads back (review findings C2, C3) ------------------------

HOSTILE = [
    "...", "... x", "---", "😀", "a😀b", "a b", "﻿bom", "yes", "No", "~", "null",
    "0x1F", "0o17", "1e3", ".inf", "2026-10-13", "2026-10-13 01:02:03", " lead",
    "trail ", "a: b", "a:b", "#", "a #b", "'single'", '"double"', "both ' and \"",
    "line\nbreak", "tab\there", "\x00", "\x85", "René", "-", "- x", "? x", "!tag", "&a",
    "*a", "%x", "@x", "`x", "|", ">", "a, b", "[x]", "{x}", "",
]


@pytest.mark.parametrize("value", HOSTILE)
def test_a_hostile_string_reads_back_as_itself(personal, value):
    root = project(personal, {"tags": ["a"],
                              "stages": {"spec": {"prompt": [{"blob": value},
                                                             {"blob": value,
                                                              "when": {"tags": ["a"]}}]}}})
    config = load_config(root)
    assert config.problems == [], config.problems
    for origin in (False, True):
        assert yaml.safe_load(render(config, origin=origin)) == config.values


def test_values_of_unknown_keys_keep_their_type(personal):
    import datetime
    root = project(personal)
    write_config_file(personal.project_file,
        "id: p\nx-extra:\n  inf: .inf\n  ninf: -.inf\n  day: 2026-10-13\n"
        "  when: 2026-10-13 01:02:03\n  big: 100000000000000000000\n  f: 1.5\n"
        "  list: [.inf, 2026-10-13, '...']\n")
    config = load_config(root)
    assert config.values["x-extra"]["day"] == datetime.date(2026, 10, 13)
    for origin in (False, True):
        assert yaml.safe_load(render(config, origin=origin)) == config.values


def test_config_show_prints_a_blob_of_three_dots(personal):
    root = project(personal, {"stages": {"spec": {"prompt": [{"blob": "..."}]}}})
    result = tcw(root, "project", "config")
    assert result.code == 0, result
    assert yaml.safe_load(result.out) == load_config(root).values


# -- Ordered maps and pairs (pre-freeze clean-up, P5) -------------------------------------

ORDERED = ("id: p\nx-extra:\n  om: !!omap [{a: 1}, {b: 2}]\n"
           "  pairs: !!pairs [{a: 1}, {a: [2, 3]}]\n"
           "  inside: [!!omap [{x: {y: 1}}], {k: !!pairs [{a: b}]}]\n")


def test_an_ordered_map_and_pairs_read_back_as_themselves(personal):
    """YAML reads both as a list of (key, value) tuples; written as a plain
    list, each tuple came back as a list (`[['a'], ['b']]`)."""
    root = project(personal)
    write_config_file(personal.project_file, ORDERED)
    config = load_config(root)
    assert config.values["x-extra"]["om"] == [("a", 1), ("b", 2)]
    assert config.values["x-extra"]["pairs"] == [("a", 1), ("a", [2, 3])]
    for flags in ((), ("--origin",)):
        result = tcw(root, "project", "config", *flags)
        assert result.code == 0, result
        assert yaml.safe_load(result.out) == config.values, result.out


def test_a_value_that_would_not_read_back_is_refused(personal, monkeypatch):
    """Whatever form a value takes, the printed YAML must read back as it:
    one that would not is an error naming its key, and nothing is printed."""
    from tcw import config_cli
    root = project(personal)
    write_config_file(personal.project_file, "id: p\nx-extra:\n  keep: [a, b]\n")
    real = config_cli._entry
    monkeypatch.setattr(config_cli, "_entry",
                        lambda value: "c" if value == "b" else real(value))
    from tcw.errors import BackendError
    config = load_config(root)
    for origin in (False, True):
        with pytest.raises(BackendError) as raised:
            render(config, origin=origin)
        assert str(raised.value) == ("cannot print x-extra.keep[1]: written as YAML, "
                                     "it does not read back as the same value")


# -- TCW-115 AC 7 and AC 8: the origin label, one shape for every layer ----------------

def _ending(out: str, start: str) -> str:
    [line] = [l for l in out.splitlines() if l.strip().startswith(start)]
    return line


def ac7(tmp_path):
    from tests.test_inherited_config import CORE_JIRA, jira_mode, made
    from tests.projectfiles import write_local_config
    core = made(tmp_path, "core", work={"jira": {"site": CORE_JIRA["site"]}})
    app = made(tmp_path, "app", parents=["core"], work=jira_mode(jira={
        "project": "APP", "credentials": CORE_JIRA["credentials"],
        "fields": CORE_JIRA["fields"]}))
    write_local_config(app, "work:\n  procedures:\n    search:\n    - file: docs/s.md\n")
    return core, app


def test_ac7_each_label_names_project_layer_and_file(tmp_path):
    from tests.test_project_files_cli import personal_env, tcw
    core, app = ac7(tmp_path)
    env = {**personal_env(tmp_path), "TCW_USER_NAME__APP": "Robin"}
    shown = tcw(app, "project", "config", "--origin", env=env)
    assert shown.code == 0, shown
    out = shown.out
    assert _ending(out, "site:").endswith(
        f"  # core, project {core / '.tcw' / 'tcw-config.yaml'}"), out
    assert _ending(out, "id:").endswith("  # app, project .tcw/tcw-config.yaml"), out
    assert _ending(out, "- file: docs/s.md").endswith(
        "  # app, local .tcw/tcw-config.local.yaml"), out
    assert _ending(out, "name: Robin").endswith(
        "  # app, environment TCW_USER_NAME__APP"), out
    assert "        - builtin: true  # built-in, tcw/work/prompts/spec.md" in \
        out.splitlines(), out
    plain = tcw(app, "project", "config", env=env)
    assert yaml.safe_load(plain.out) == yaml.safe_load(out)


def test_ac7_a_value_from_the_user_wide_file_is_the_active_projects(tmp_path):
    from tests.projectfiles import write_config_file
    from tests.test_project_files_cli import personal_env, tcw
    _core, app = ac7(tmp_path)
    user = write_config_file(tmp_path / "xdg" / "tcw" / "config.yaml",
                             "user:\n  name: Sam\n")
    shown = tcw(app, "project", "config", "--origin", env=personal_env(tmp_path))
    assert shown.code == 0, shown
    assert _ending(shown.out, "name: Sam").endswith(f"  # app, user {user}"), shown.out


@pytest.mark.parametrize("flags", [(), ("--origin",)])
def test_ac8_core_absent_is_undecided_naming_both(tmp_path, flags):
    import shutil
    from tests.test_project_files_cli import tcw
    from tests.test_inherited_config import jira_mode, made
    made(tmp_path, "core")
    # `app` sets `work.tags` itself, so `work.jira` is the first undecided key.
    app = made(tmp_path, "app", parents=["core"], work=jira_mode(tags=["a"]))
    shutil.rmtree(tmp_path / "core")
    shown = tcw(app, "project", "config", *flags)
    assert (shown.code, shown.out) == (7, ""), shown
    assert "work.jira" in shown.err and "core" in shown.err, shown.err


@pytest.mark.parametrize("flags", [(), ("--origin",)])
def test_ac8_a_broken_inherited_key_names_its_file(tmp_path, flags):
    from tests.test_project_files_cli import tcw
    from tests.test_inherited_config import made
    from tests.projectfiles import config_file
    core = made(tmp_path, "core", work={"tags": ["!!!"]})
    app = made(tmp_path, "app", parents=["core"])
    shown = tcw(app, "project", "config", *flags)
    assert (shown.code, shown.out) == (1, ""), shown
    assert str(config_file(core)) in shown.err, shown.err
    from tests.test_inherited_config import set_work
    set_work(app, {"tags": ["a"]})
    assert tcw(app, "project", "config", *flags).code == 0


def test_ac8_the_projects_own_problem(tmp_path):
    from tests.test_project_files_cli import tcw
    from tests.test_inherited_config import made
    made(tmp_path, "core")
    app = made(tmp_path, "app", parents=["core"], work={"tags": 5})
    plain = tcw(app, "project", "config")
    assert (plain.code, plain.out) == (1, ""), plain
    origin = tcw(app, "project", "config", "--origin")
    assert origin.code == 1 and "id: app" in origin.out, origin
