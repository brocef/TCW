"""The override variables, through the loader and the command line (TCW-109
Design 4, 5.3, 7.2; AC 19-25, 27, 28). Each test sets its variables itself,
after the suite's fixture has removed every override and switched personal
configuration off; `on` switches it back on."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from tcw.config import load_config
from tests.projectfiles import config_file, write_config_file
from tests.test_inherited_config import made, run  # noqa: F401  (a fixture)
from tests.test_project_files_cli import tcw


@pytest.fixture
def on(tmp_path, monkeypatch):
    """Personal configuration on, every file of it inside the test. Returns
    the environment to give a `tcw` run in a separate process."""
    monkeypatch.delenv("TCW_NO_PERSONAL_CONFIG")
    (tmp_path / "home").mkdir()
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    return {"TCW_NO_PERSONAL_CONFIG": None}


@pytest.fixture
def app(tmp_path):
    return made(tmp_path, "app")


_TITLES = iter(range(1000))


def item_of(root: Path, env) -> str:
    made_item = tcw(root, "work", "new", f"thing {next(_TITLES)}", env=env)
    assert made_item.code == 0, made_item
    return made_item.out.strip()


def spec_prompt(root: Path, env) -> "tuple[int, str, str]":
    ran = tcw(root, "work", "stage", "prompt", "spec", item_of(root, env), env=env)
    return ran.code, ran.out, ran.err


def test_ac19_the_name_of_an_override(app, on, monkeypatch, tmp_path):
    monkeypatch.setenv("TCW_USER_NAME__APP", "Robin")
    assert load_config(app).user_name == "Robin"
    mine = made(tmp_path, "my-proj", work={"backend": "jira"})
    monkeypatch.setenv("TCW_WORK_JIRA_CREDENTIALS_TOKEN_ENV__MY_PROJ", "MY_TOKEN")
    config = load_config(mine)
    assert config.values["work"]["jira"]["credentials"]["token-env"] == "MY_TOKEN"
    origin = config.origins[("work", "jira", "credentials", "token-env")]
    assert str(origin) == "environment: TCW_WORK_JIRA_CREDENTIALS_TOKEN_ENV__MY_PROJ"
    for name, value in (("TCW_PROCEDURE_X", "1"), ("TCW_PROJECT_CORE", str(tmp_path)),
                        ("TCW_JIRA_EMAIL", "x"), ("TCW_STDIN_TIMEOUT", "3")):
        monkeypatch.setenv(name, value)
    assert load_config(app).problems == []


@pytest.mark.parametrize("name, words", [
    ("TCW__ALL__WORK_TAGS", "TCW_<KEY>__<PROJECT>"), ("TCW_WORK__", "TCW_<KEY>__<PROJECT>"),
    ("TCW_WORK___APP", "TCW_<KEY>__<PROJECT>"), ("TCW_user_NAME__APP", "TCW_<KEY>__<PROJECT>"),
    ("TCW_WORK_STAGES_SPEC_PROMPTS__APP", "no configuration key is written"),
    ("TCW_TCW_VERSION__APP", "no configuration key is written"),
    ("TCW_WORK_STAGES_DESIGN_PROMPT__APP", "no configuration key is written"),
])
def test_ac20_malformed_names_and_unknown_keys(app, on, name, words):
    ran = tcw(app, "work", "list", env={**on, name: "x"})
    assert ran.code == 1, ran
    message = ran.err.split(": ", 1)[1]
    assert message.startswith(name) and words in message, ran.err


SHARED = "is a shared key; an environment variable cannot set it"


@pytest.mark.parametrize("name, value", [
    ("TCW_ID__APP", "x"), ("TCW_PARENTS__APP", "[core]"), ("TCW_CHILDREN__APP", "[kid]"),
    ("TCW_WORK_PATH__APP", "/tmp/x"), ("TCW_WORK_REPOSITORY__APP", "x"),
    ("TCW_TAXONOMY_PATH__APP", "x"), ("TCW_WORK_BACKEND__APP", "jira"),
    ("TCW_WORK_TAGS__APP", "[a]"), ("TCW_WORK_JIRA_SITE__APP", "https://x.example.net"),
    ("TCW_WORK_STAGES_SPEC_STATUS__APP", "x"), ("TCW_WORK_STAGES_SPEC_PRE__APP", "[]"),
    ("TCW_WORK_TAGS__ELSEWHERE", "[a]"),
])
def test_ac21_only_allowed_keys(app, on, name, value):
    ran = tcw(app, "work", "list", env={**on, name: value})
    assert ran.code == 1 and SHARED in ran.err, ran


def test_ac21_a_mapping_with_one_shared_key(app, on):
    ran = tcw(app, "work", "list",
              env={**on, "TCW_WORK_STAGES_SPEC__APP": "{prompt: [{blob: p}], status: x}"})
    assert ran.code == 1, ran
    assert ran.err.count(SHARED) == 1 and "work.stages.spec.status" in ran.err, ran


def test_ac21_an_allowed_key_of_a_project_not_read_changes_nothing(app, on):
    before = tcw(app, "config", "show", env=on)
    ran = tcw(app, "config", "show", env={**on, "TCW_USER_NAME__ELSEWHERE": "x"})
    assert ran.code == 0 and ran.out == before.out, ran
    assert tcw(app, "work", "list", env={**on, "TCW_USER_NAME__ELSEWHERE": "x"}).code == 0


def test_ac22_values_by_type(app, on, monkeypatch):
    for text in ("no", "null"):
        monkeypatch.setenv("TCW_USER_NAME__APP", text)
        assert load_config(app).user_name == text
    monkeypatch.delenv("TCW_USER_NAME__APP")
    code, out, _ = spec_prompt(app, {**on, "TCW_WORK_STAGES_SPEC_PROMPT__APP":
                                     "[{blob: hello}]"})
    built_in = spec_prompt(app, on)[1]
    assert code == 0 and "hello" in out
    marker = next(line for line in built_in.splitlines() if line.startswith("#"))
    assert marker not in out
    code, out, _ = spec_prompt(app, {**on, "TCW_WORK_STAGES_SPEC_PROMPT__APP":
                                     "[{blob: hello}, {inherit: true}]"})
    assert code == 0 and "hello" in out and marker in out


@pytest.mark.parametrize("name, value, words", [
    ("TCW_WORK_STAGES_SPEC_PROMPT__APP", "hello", "must be a list"),
    ("TCW_WORK_STAGES_SPEC_PROMPT__APP", "[unclosed", "is not valid YAML"),
    ("TCW_WORK_STAGES_SPEC_PROMPT__APP", "null", "null has no meaning in an environment"),
    ("TCW_WORK_STAGES_SPEC__APP", "[a]", "must be a mapping"),
    ("TCW_WORK_STAGES_SPEC__APP", "{prompt: [], prompt: []}", "a key appears twice"),
])
def test_ac22_a_value_of_the_wrong_kind(app, on, name, value, words):
    ran = tcw(app, "work", "list", env={**on, name: value})
    assert ran.code == 1 and words in ran.err, ran


def test_ac22_no_message_holds_the_value(app, on):
    ran = tcw(app, "work", "list",
              env={**on, "TCW_WORK_STAGES_SPEC_PROMPT__APP": "s3cr3t-token"})
    assert ran.code == 1 and "s3cr3t-token" not in ran.err, ran


@pytest.mark.parametrize("first", ["whole", "one"])
def test_ac23_the_more_specific_variable_wins(app, on, first):
    variables = {"TCW_WORK_STAGES_SPEC__APP": "{prompt: [{blob: whole-marker}]}",
                 "TCW_WORK_STAGES_SPEC_PROMPT__APP": "[{blob: one-marker}]"}
    if first == "one":
        variables = dict(reversed(list(variables.items())))
    code, out, _ = spec_prompt(app, {**on, **variables})
    assert code == 0 and "one-marker" in out and "whole-marker" not in out


def test_ac23_a_mapping_merges(tmp_path, on):
    from tests.test_inherited_config import jira_mode
    # The spec writes the `pre` binding as `blob: gate`, but a `pre` list
    # takes only commands; a command stands in for it.
    app = made(tmp_path, "app", work={"stages": {"spec": {"pre": [{"command": "gate"}]}}})
    env = {**on, "TCW_WORK_STAGES_SPEC__APP": "{prompt: [{blob: p}]}"}
    listed = tcw(app, "work", "lifecycle", "--stage", "spec", env=env)
    assert listed.code == 0 and "gate" in listed.out, listed
    code, out, _ = spec_prompt(app, env)
    assert code == 0 and "p" in out.split()
    jira = made(tmp_path, "jira-app", work=jira_mode())
    import os
    os.environ.pop("TCW_NO_PERSONAL_CONFIG", None)
    os.environ["TCW_WORK_STAGES_SPEC__JIRA_APP"] = "{prompt: [{blob: p}]}"
    try:
        config = load_config(jira)
    finally:
        del os.environ["TCW_WORK_STAGES_SPEC__JIRA_APP"]
    assert config.work.stage("spec").status == "Specifying"


def test_ac24_bindings_and_notes_from_a_variable(app, on, tmp_path):
    (app / "notes.md").write_text("from the notes file\n")
    name = "TCW_WORK_STAGES_SPEC_PROMPT__APP"
    code, out, err = spec_prompt(app, {**on, name: "[{file: notes.md}]"})
    assert code == 0 and "from the notes file" in out
    assert any(line.startswith("note: this prompt was changed by personal configuration:")
               and name in line for line in err.splitlines()), err
    (tmp_path / "outside.md").write_text("x\n")
    ran = tcw(app, "work", "list", env={**on, name: "[{file: ../outside.md}]"})
    assert ran.code == 1 and "resolves outside" in ran.err and name in ran.err, ran


def test_ac24_a_post_hook_from_a_variable(app, on, tmp_path):
    seen = tmp_path / "seen.txt"
    (app / "record.sh").write_text(f'printf "%s" "$TCW_CONFIG_DIR" > {seen}\n')
    name = "TCW_WORK_STAGES_SPEC_POST__APP"
    env = {**on, name: "[{command: sh record.sh}]"}
    item = item_of(app, env)
    moved = tcw(app, "work", "advance", item, env=env)
    assert moved.code == 0, moved
    assert Path(seen.read_text()).resolve() == app
    item = item_of(app, env)
    failed = tcw(app, "work", "advance", item, env={**on, name: "[{command: exit 3}]"})
    assert f"from {name}" in failed.err, failed


def test_ac25_no_personal_config_turns_the_variables_off(app):
    env = {"TCW_USER_NAME__APP": "Robin", "TCW_WORK_TAGS__APP": "[a]", "TCW__ALL__X": "1"}
    assert tcw(app, "work", "list", env=env).code == 0
    shown = tcw(app, "config", "show", env=env)
    assert "Robin" not in shown.out
    ran = tcw(app, "work", "list", env={"TCW_NO_PERSONAL_CONFIG": "true",
                                       "TCW_USER_NAME__APP": "Robin"})
    assert ran.code == 1 and "TCW_NO_PERSONAL_CONFIG must be 1" in ran.err, ran


def test_ac27_a_single_project_pays_nothing(app, on, monkeypatch):
    unrelated = {"TCW_PROJECT_X": "/nowhere", "TCW_JIRA_EMAIL": "x",
                 "TCW_STDIN_TIMEOUT": "3"}
    for argv in (("work", "list"), ("work", "tags", "list"),
                 ("config", "show", "--origin"), ("validate",)):
        plain = tcw(app, *argv, env=on)
        busy = tcw(app, *argv, env={**on, **unrelated})
        assert (plain.code, plain.out, plain.err) == (busy.code, busy.out, busy.err), argv
    import tcw.store.project as project
    opened: list = []
    real = project.FsProjectRegistry.open
    monkeypatch.setattr(project.FsProjectRegistry, "open",
                        classmethod(lambda cls, root: opened.append(root) or real(root)))
    load_config(app)
    assert opened == []


def test_ac28_validate_reports_a_variables_problem(app, on):
    ran = tcw(app, "validate", env={**on, "TCW_WORK_TAGS__APP": "[a]"})
    assert ran.code == 1, ran
    assert any(line.startswith("error: environment: TCW_WORK_TAGS__APP")
               for line in ran.out.splitlines()), ran


def test_ac28_a_variable_naming_a_project_read_for_itself(tmp_path, on, run):
    from tests.test_capabilities_rm import write_cap
    lib = made(tmp_path, "lib")
    item = run(lib, "work", "new", "lib thing").out.strip()
    app = made(tmp_path, "app", children=["lib"])
    document = yaml.safe_load(config_file(lib).read_text())
    document["parents"] = ["app"]
    write_config_file(config_file(lib), yaml.safe_dump(document))
    write_cap(app, "cli", Status="Supported")
    (app / "docs" / "capabilities" / "cli" / "description.md").write_text(
        f"See [this](tcw://{item}).\n")
    ran = tcw(app, "validate", env={**on, "TCW_WORK_TAGS__LIB": "[a]"})
    assert ran.code == 1, ran
    errors = [line for line in ran.out.splitlines() if line.startswith("error:")]
    assert len(errors) == 1 and errors[0].startswith("error: environment: "
                                                     "TCW_WORK_TAGS__LIB"), ran


@pytest.mark.parametrize("name, value, words", [
    ("TCW_WORK_STAGES_SPEC_PROMPT__APP", "[5]", "a binding must be a mapping"),
    ("TCW_WORK_STAGES_SPEC_PROMPT__APP", "[{blob: a, file: b}]", "choose one"),
    ("TCW_WORK_STAGES_SPEC_PROMPT__APP", "[{bogus: a}]", "unknown binding key"),
    ("TCW_WORK_STAGES_SPEC_PROMPT__APP", "[{blob: 5}]", "must be a non-blank string"),
    ("TCW_WORK_STAGES_SPEC_PROMPT__APP", "[{file: ../../x}]", "resolves outside"),
    ("TCW_WORK_STAGES_SPEC_PROMPT__APP", "[{inherit: 5}]", "takes only the value true"),
    ("TCW_WORK_STAGES_SPEC_POST__APP", "[{blob: x}]", "is not allowed in a post list"),
    ("TCW_WORK_STAGES_SPEC__APP", "{prompt: 5}", "expected a list of bindings"),
    ("TCW_WORK_STAGES__APP", "{bogus: {prompt: []}}", "unknown stage"),
    ("TCW_WORK_PROCEDURES_SEARCH__APP", "[5]", "a binding must be a mapping"),
    ("TCW_WORK_PROCEDURES__APP", "{bogus: []}", "unknown procedure"),
    ("TCW_USER_NAME__APP", "", "must be a name"),
    ("TCW_USER__APP", "{name: 5}", "must be a name"),
])
def test_ac28_every_problem_in_a_value_starts_with_the_variable(app, on, name, value,
                                                                words):
    """Design 7.2: a problem found in a variable's value, by the checks made
    while reading it or by the parser after the fold, starts with its name."""
    ran = tcw(app, "validate", env={**on, name: value})
    assert ran.code == 1, ran
    errors = [line for line in ran.out.splitlines() if line.startswith("error:")]
    assert len(errors) == 1 and words in errors[0], ran
    assert errors[0].startswith(f"error: environment: {name}: "), ran
    listed = tcw(app, "work", "list", env={**on, name: value})
    assert listed.code == 1 and listed.err.split(": ", 1)[1].startswith(name), listed
