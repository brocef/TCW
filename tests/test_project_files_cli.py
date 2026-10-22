"""The `.tcw/` folder and the version every file records, as a person meets
them on the command line (TCW-106 acceptance criteria 1-14c).

Each test is named after the criterion it proves. Most run `tcw` as a shell
runs it, from a folder the test builds; the few that need a running version
other than this checkout's own call `tcw.cli.main` in-process with the
version patched, since no lower 4.x minor version exists while TCW is 4.0.

The unit tests of the module these rest on are `tests/test_project_files.py`.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest
import yaml

from tcw import __version__
from tests.projectfiles import config_file, local_config_file, write_config, write_local_config

SOURCE = str(Path(__file__).resolve().parent.parent)

LEGACY = ("is a TCW 3.x project (tcw-config.yaml at its root, no .tcw/ folder); "
          "run 'tcw migrate' in it to move it to TCW 4")
NO_PROJECT = "no TCW project here"
NAMING = "must be lowercase letters and digits joined by single hyphens"


@dataclass
class Ran:
    code: int
    out: str
    err: str


def tcw(cwd: Path, *argv: str, env: dict | None = None, stdin: str = "") -> Ran:
    """`tcw` from `cwd`, with this checkout's code. Personal files stay off
    unless `env` turns them on (`personal_env`)."""
    full = {**os.environ, "PYTHONPATH": SOURCE, **(env or {})}
    full = {k: v for k, v in full.items() if v is not None}
    done = subprocess.run([sys.executable, "-m", "tcw.cli", *argv], cwd=cwd, env=full,
                          input=stdin, capture_output=True, text=True, timeout=60)
    return Ran(done.returncode, done.stdout, done.stderr)


def personal_env(tmp_path: Path) -> dict:
    """Personal files on, with the user-wide file and home inside the test."""
    (tmp_path / "home").mkdir(exist_ok=True)
    return {"TCW_NO_PERSONAL_CONFIG": None, "XDG_CONFIG_HOME": str(tmp_path / "xdg"),
            "HOME": str(tmp_path / "home")}


def git(root: Path, *argv: str) -> str:
    return subprocess.run(["git", "-C", str(root), *argv], check=True,
                          capture_output=True, text=True).stdout


def repository(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    git(root, "init", "-q")
    return root


def project(root: Path, project_id: str, extra: str = "") -> Path:
    """A 4.0 project at `root` with a work store and one item, so that
    `tcw work list` shows which project a command acted on."""
    root.mkdir(parents=True, exist_ok=True)
    write_config(root, f"id: {project_id}\n{extra}")
    (root / "docs" / "work").mkdir(parents=True, exist_ok=True)
    made = tcw(root, "work", "new", f"Item of {project_id}")
    assert made.code == 0, made
    return root


def legacy_project(root: Path, project_id: str = "old") -> Path:
    """A 3.x project: `tcw-config.yaml` at its root and no `.tcw/`."""
    root.mkdir(parents=True, exist_ok=True)
    (root / "tcw-config.yaml").write_text(f"id: {project_id}\n")
    return root


def listed_ids(ran: Ran) -> set[str]:
    """The project IDs `tcw work list` printed, from the slugs' prefixes."""
    assert ran.code == 0, ran
    return {line.split("/", 1)[0] for line in ran.out.splitlines() if line}


def snapshot(root: Path) -> dict[str, bytes | None]:
    """Every path under `root` and, for a file, its bytes."""
    return {str(p.relative_to(root)): (p.read_bytes() if p.is_file() else None)
            for p in sorted(root.rglob("*"))}


def assert_refused_as_legacy(ran: Ran, folder: Path) -> None:
    """Design 4.1's one line: exit 1, naming the folder and `tcw migrate`."""
    assert ran.code == 1, ran
    assert f"{folder.resolve()} {LEGACY}" in ran.err, ran
    assert NO_PROJECT not in ran.err, ran


# -- AC 1, 2: tcw init -------------------------------------------------------------


def test_ac1_init_writes_the_versioned_configuration_in_the_tcw_folder(tmp_path):
    root = tmp_path / "p"
    root.mkdir()
    ran = tcw(root, "init", "--id", "demo")
    assert ran.code == 0, ran
    version = tcw(root, "--version").out.split()[-1]
    assert version == __version__
    text = (root / ".tcw" / "tcw-config.yaml").read_text()
    assert text.splitlines()[0] == f"tcw-version: {version}"
    assert yaml.safe_load(text)["id"] == "demo"
    assert not (root / "tcw-config.yaml").exists(), "nothing at the root"


def test_ac2_init_writes_the_ignore_rule_in_the_tcw_folder_once(tmp_path):
    root = repository(tmp_path / "p")
    assert tcw(root, "init", "--id", "demo").code == 0
    ignore = root / ".tcw" / ".gitignore"
    assert ignore.read_text().splitlines() == ["/tcw-config.local.yaml"]
    assert not (root / ".gitignore").exists(), "no root .gitignore"
    assert tcw(root, "init").code == 0
    assert ignore.read_text().splitlines() == ["/tcw-config.local.yaml"]


def test_ac2_outside_a_repository_the_note_names_the_new_place(tmp_path):
    root = tmp_path / "p"
    root.mkdir()
    ran = tcw(root, "init", "--id", "demo")
    assert ran.code == 0, ran
    assert ("keep .tcw/tcw-config.local.yaml out of version control yourself"
            in ran.err), ran
    assert "keep tcw-config.local.yaml" not in ran.err, ran
    assert not (root / ".tcw" / ".gitignore").exists()


# -- AC 3, 4, 14a: finding the active project ---------------------------------------


def test_ac3_a_subfolder_acts_on_the_project_above_it(tmp_path):
    root = project(tmp_path / "root", "top")
    deep = root / "a" / "b"
    deep.mkdir(parents=True)
    assert listed_ids(tcw(deep, "work", "list")) == {"top"}


def test_ac3_in_a_monorepo_the_nearest_project_wins(tmp_path):
    root = project(tmp_path / "mono", "mono")
    server = project(root / "apps" / "server", "server")
    src = server / "src"
    src.mkdir()
    assert listed_ids(tcw(src, "work", "list")) == {"server"}
    assert listed_ids(tcw(root / "apps", "work", "list")) == {"mono"}


def test_ac4_a_tcw_folder_without_the_file_is_not_a_project(tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    dotted = tmp_path / "dotted"
    (dotted / ".tcw").mkdir(parents=True)
    (dotted / ".tcw" / "notes.txt").write_text("not configuration\n")
    expected = tcw(empty, "work", "list")
    assert expected.code == 1 and NO_PROJECT in expected.err, expected
    for start in (dotted, dotted / ".tcw"):
        ran = tcw(start, "work", "list")
        assert (ran.code, ran.out, ran.err) == (expected.code, expected.out, expected.err)


def test_ac14a_inside_the_tcw_folder_acts_on_the_project(tmp_path):
    root = project(tmp_path / "p", "outer")
    ran = tcw(root / ".tcw", "work", "list")
    assert listed_ids(ran) == {"outer"}
    assert LEGACY not in ran.err


# -- AC 5, 6, 14, 14c: refusing a 3.x project ----------------------------------------


@pytest.mark.parametrize("argv", [("work", "list"), ("validate",), ("init", "--id", "x"),
                                  ("config", "show")])
def test_ac5_every_command_refuses_a_3x_project_and_writes_nothing(tmp_path, argv):
    old = legacy_project(repository(tmp_path / "old"))
    before = snapshot(old)
    ran = tcw(old, *argv)
    assert_refused_as_legacy(ran, old)
    assert ran.out == ""
    assert snapshot(old) == before, "nothing written"


def test_ac5_a_subfolder_of_a_3x_project_is_refused_naming_its_root(tmp_path):
    old = legacy_project(tmp_path / "old")
    (old / "src").mkdir()
    assert_refused_as_legacy(tcw(old / "src", "work", "list"), old)


@pytest.mark.parametrize("flag", ["--version", "--help"])
def test_ac5_and_14c_version_and_help_are_not_refused_in_a_3x_project(tmp_path, flag):
    old = legacy_project(tmp_path / "old")
    ran = tcw(old, flag)
    assert ran.code == 0, ran
    assert LEGACY not in ran.out + ran.err


def test_ac6_a_4_0_project_nested_in_a_3x_one(tmp_path):
    old = legacy_project(tmp_path / "old")
    inner = project(old / "packages" / "new", "new")
    (inner / "src").mkdir()
    assert listed_ids(tcw(inner / "src", "work", "list")) == {"new"}
    (old / "packages" / "other").mkdir()
    assert_refused_as_legacy(tcw(old / "packages" / "other", "work", "list"), old)


def test_ac14_a_leftover_root_file_is_not_read_and_validate_warns(tmp_path):
    root = project(tmp_path / "p", "new")
    (root / "tcw-config.yaml").write_text("id: old\n")
    assert listed_ids(tcw(root, "work", "list")) == {"new"}
    ran = tcw(root, "validate")
    assert ran.code == 0, ran
    assert ("warning: tcw-config.yaml: a TCW 3.x configuration file at the root of a "
            "TCW 4 project; TCW 4 reads .tcw/tcw-config.yaml only, so delete this one"
            in ran.out.splitlines()), ran


# -- AC 7: the version each file records ---------------------------------------------

ROWS = {
    "a-missing": (None, "has no tcw-version, so it is read as a TCW 3.x file; run "
                        "'tcw migrate' in this project (a file written by hand for "
                        f"TCW 4 starts with 'tcw-version: {__version__}')"),
    "b-a-number": ("4.0", "tcw-version must be a TCW version written as text, such "
                          f"as '{__version__}'"),
    "b-not-a-version": ("'four'", "tcw-version must be a TCW version written as "
                                  f"text, such as '{__version__}'"),
    "c-older": ("'3.0.2'", "tcw-version 3.0.2 is in the format of TCW 3.0; run "
                           "'tcw migrate' in this project"),
    "d-newer": ("99.1.0", "was written by TCW 99.1 (tcw-version 99.1.0), newer than "
                          f"this TCW ({__version__}); upgrade TCW"),
}


def _with_version(value: str | None, body: str) -> str:
    return body if value is None else f"tcw-version: {value}\n{body}"


def _version_case(tmp_path: Path, which: str, value: str | None) -> tuple[Path, Path, dict]:
    """A project whose `which` file (`project` or `local`) records `value`."""
    root = tmp_path / "p"
    (root / "docs" / "work").mkdir(parents=True)
    env = personal_env(tmp_path)
    if which == "project":
        path = config_file(root)
        path.write_text(_with_version(value, "id: p\n"))
    else:
        write_config(root, "id: p\n")
        path = local_config_file(root)
        path.write_text(_with_version(value, "user:\n  name: Someone\n"))
    return root, path, env


@pytest.mark.parametrize("which", ["project", "local"])
@pytest.mark.parametrize("row", sorted(ROWS))
def test_ac7_each_unreadable_version_is_refused(tmp_path, which, row):
    value, message = ROWS[row]
    root, path, env = _version_case(tmp_path, which, value)
    shown = f".tcw/{path.name}"
    before = path.read_bytes()

    listed = tcw(root, "work", "list", env=env)
    assert listed.code == 1, listed
    assert f"{shown}: {message}" in listed.err, listed
    assert "tcw-version: tcw-version" not in listed.err, "the key is not said twice"

    checked = tcw(root, "validate", env=env)
    assert checked.code == 1, checked
    errors = [l for l in checked.out.splitlines() if l.startswith("error: ")]
    assert errors == [f"error: {shown}: {message}"], checked
    assert path.read_bytes() == before


@pytest.mark.parametrize("which", ["project", "local"])
@pytest.mark.parametrize("value", [__version__, "'4.0'", "4.0.99"])
def test_ac7_a_file_at_the_running_version_is_read(tmp_path, which, value):
    root, _, env = _version_case(tmp_path, which, value)
    assert tcw(root, "work", "list", env=env).code == 0
    checked = tcw(root, "validate", env=env)
    assert checked.code == 0, checked


@pytest.mark.parametrize("which", ["project", "local"])
def test_ac7_a_lower_4x_minor_version_is_read(tmp_path, monkeypatch, capsys, which):
    """No lower 4.x minor exists while TCW is 4.0, so the running version is
    patched: TCW 4.3 reads a 4.1 file and refuses a 4.4 one."""
    from tcw.cli import main
    monkeypatch.setattr("tcw.project_files.__version__", "4.3.0")
    monkeypatch.delenv("TCW_NO_PERSONAL_CONFIG", raising=False)
    for value, code in (("4.1.0", 0), ("4.4.0", 1)):
        case = tmp_path / value
        case.mkdir()
        root, _, env = _version_case(case, which, value)
        for key, setting in env.items():
            if setting is not None:
                monkeypatch.setenv(key, setting)
        monkeypatch.chdir(root)
        assert main(["work", "list"]) == code, capsys.readouterr()
        err = capsys.readouterr().err
        assert ("newer than this TCW (4.3.0)" in err) == (code == 1), err


# -- AC 8, 9: the version is file information ----------------------------------------


def test_ac8_config_show_hides_the_version_and_the_allowlist_ignores_it(tmp_path):
    root = tmp_path / "p"
    write_config(root, "id: p\nwork:\n  tags: [bug]\n")
    write_local_config(root, "user:\n  name: Someone\n")
    assert "tcw-version" in local_config_file(root).read_text()
    env = personal_env(tmp_path)
    shown = tcw(root, "config", "show", env=env)
    assert shown.code == 0, shown
    assert "tcw-version" not in shown.out + shown.err, shown
    assert "Someone" in shown.out, "the personal file was read"
    checked = tcw(root, "validate", env=env)
    assert checked.code == 0 and "error:" not in checked.out, checked


def test_ac9_init_gives_an_id_below_the_version_line(tmp_path):
    root = tmp_path / "p"
    write_config(root, "")
    assert config_file(root).read_text() == f"tcw-version: {__version__}\n"
    assert tcw(root, "init", "--id", "demo").code == 0
    lines = config_file(root).read_text().splitlines()
    assert lines[:2] == [f"tcw-version: {__version__}", "id: demo"]


def test_ac9_an_edit_leaves_the_version_line_alone(tmp_path):
    root = repository(tmp_path / "p")
    assert tcw(root, "init", "--id", "demo").code == 0
    before = config_file(root).read_text().splitlines()[0]
    assert tcw(root, "work", "tags", "add", "bug").code == 0
    text = config_file(root).read_text()
    assert "bug" in text
    assert text.splitlines()[0] == before
    assert text.count("tcw-version") == 1


def test_ac9_an_edit_keeps_an_older_4x_version(tmp_path, monkeypatch, capsys):
    """Running TCW 4.3, an edit to a 4.1 file leaves it saying 4.1: only a
    migration changes the version (Design 3.2)."""
    from tcw.cli import main
    monkeypatch.setattr("tcw.project_files.__version__", "4.3.0")
    root = repository(tmp_path / "p")
    (root / "docs" / "work").mkdir(parents=True)
    write_config(root, "tcw-version: 4.1.0\nid: demo\n")
    monkeypatch.chdir(root)
    assert main(["work", "tags", "add", "bug"]) == 0, capsys.readouterr()
    assert main(["taxonomy", "list"]) in (0, 1)
    lines = config_file(root).read_text().splitlines()
    assert lines[0] == "tcw-version: 4.1.0"
    assert yaml.safe_load(config_file(root).read_text())["work"]["tags"] == ["bug"]


# -- AC 10, 14c: paths read from the project root -------------------------------------


PROMPTS = """\
work:
  stages:
    spec:
      prompt:
        - file: docs/x.md
        - generate: 'printf "config-dir=%s\\n" "$TCW_CONFIG_DIR"'
"""


def test_ac10_a_file_binding_and_config_dir_are_the_project_root(tmp_path):
    root = project(tmp_path / "p", "p", PROMPTS)
    (root / "docs" / "x.md").write_text("WORDS FROM THE ROOT\n")
    (root / ".tcw" / "docs").mkdir()
    (root / ".tcw" / "docs" / "x.md").write_text("WORDS FROM INSIDE .TCW\n")
    ran = tcw(root, "work", "stage", "prompt", "spec")
    assert ran.code == 0, ran
    assert "WORDS FROM THE ROOT" in ran.out and "INSIDE .TCW" not in ran.out
    assert f"config-dir={root.resolve()}\n" in ran.out, ran.out
    assert f"config-dir={root.resolve() / '.tcw'}" not in ran.out


def test_ac10_a_file_binding_may_not_leave_the_project_root(tmp_path):
    root = tmp_path / "p"
    root.mkdir()
    (tmp_path / "outside.md").write_text("OUTSIDE\n")
    write_config(root, "id: p\nwork:\n  stages:\n    spec:\n      prompt:\n"
                       "        - file: ../outside.md\n")
    (root / "docs" / "work").mkdir(parents=True)
    ran = tcw(root, "work", "stage", "prompt", "spec")
    assert ran.code == 1, ran
    assert "../outside.md" in ran.err and "OUTSIDE" not in ran.out, ran


def test_ac14c_a_personal_command_binding_sees_the_project_root(tmp_path):
    root = project(tmp_path / "p", "p")
    write_local_config(root, "work:\n  stages:\n    spec:\n      prompt:\n"
                             "        - generate: 'printf \"config-dir=%s\\n\" "
                             "\"$TCW_CONFIG_DIR\"'\n")
    ran = tcw(root, "work", "stage", "prompt", "spec", env=personal_env(tmp_path))
    assert ran.code == 0, ran
    assert f"config-dir={root.resolve()}\n" in ran.out, ran.out


# -- AC 11, 12: the naming rule ---------------------------------------------------------


@pytest.mark.parametrize("key", ["Work", "my_key", "a--b", "-a"])
@pytest.mark.parametrize("which", ["project", "local", "user"])
def test_ac11_a_key_breaking_the_naming_rule_is_a_problem(tmp_path, which, key):
    root = tmp_path / "p"
    (root / "docs" / "work").mkdir(parents=True)
    env = personal_env(tmp_path)
    write_config(root, "id: p\n")
    body = f"work:\n  hooks:\n    {key}: 1\n"
    if which == "project":
        write_config(root, f"id: p\n{body}")
        shown = ".tcw/tcw-config.yaml"
    elif which == "local":
        write_local_config(root, body)
        shown = ".tcw/tcw-config.local.yaml"
    else:
        user = tmp_path / "xdg" / "tcw" / "config.yaml"
        user.parent.mkdir(parents=True)
        user.write_text(body)
        shown = str(user)
    ran = tcw(root, "work", "list", env=env)
    assert ran.code == 1, ran
    assert f"{shown}: work.hooks.{key}: key '{key}' {NAMING}" in ran.err, ran


NOT_TAGS = """\
work:
  tags: [bug]
  stages:
    spec:
      prompt:
        - blob: ONLY-WITHOUT-BUG
          when: {%s: [bug]}
"""


def test_ac12_not_tags_selects_and_is_printed_under_its_new_name(tmp_path):
    root = project(tmp_path / "p", "p", NOT_TAGS % "not-tags")
    buggy = tcw(root, "work", "new", "Buggy", "--tag", "bug")
    assert buggy.code == 0, buggy
    plain = tcw(root, "work", "list").out.split()
    plain = [slug for slug in plain if slug != buggy.out.strip()]
    assert len(plain) == 1
    assert "ONLY-WITHOUT-BUG" in tcw(root, "work", "stage", "prompt", "spec", plain[0]).out
    assert "ONLY-WITHOUT-BUG" not in tcw(root, "work", "stage", "prompt", "spec",
                                         buggy.out.strip()).out
    lifecycle = tcw(root, "work", "lifecycle", "--stage", "spec", "--json")
    assert lifecycle.code == 0, lifecycle
    stage = json.loads(lifecycle.out)["stages"][0]
    assert stage["bindings"]["prompt"] == [
        {"blob": "ONLY-WITHOUT-BUG", "when": {"not-tags": ["bug"]}}]
    assert "not_tags" not in lifecycle.out


def test_ac12_not_tags_with_an_underscore_says_what_to_write(tmp_path):
    root = tmp_path / "p"
    (root / "docs" / "work").mkdir(parents=True)
    write_config(root, "id: p\n" + NOT_TAGS % "not_tags")
    ran = tcw(root, "work", "list")
    assert ran.code == 1, ran
    assert ("work.stages.spec.prompt[0].when.not_tags: key 'not_tags' "
            f"{NAMING}; write 'not-tags'") in ran.err, ran
    checked = tcw(root, "validate")
    assert checked.code == 1, checked
    assert checked.out.splitlines() == [
        "error: .tcw/tcw-config.yaml: work.stages.spec.prompt[0].when.not_tags: "
        f"key 'not_tags' {NAMING}; write 'not-tags'"], "one mistake, one error"


@pytest.mark.parametrize("local", [False, True], ids=["project", "local"])
def test_a_file_with_no_version_gets_only_the_version_problem(tmp_path, local):
    root = tmp_path / "p"
    (root / "docs" / "work").mkdir(parents=True)
    body = "work:\n  my_key: 1\n"
    if local:
        write_config(root, "id: p\n")
        local_config_file(root).write_text(body)
        shown = ".tcw/tcw-config.local.yaml"
    else:
        config_file(root).write_text("id: p\n" + body)
        shown = ".tcw/tcw-config.yaml"
    ran = tcw(root, "validate", env=personal_env(tmp_path))
    assert ran.code == 1, ran
    errors = [line for line in ran.out.splitlines() if line.startswith("error:")]
    assert len(errors) == 1, ran
    assert errors[0].startswith(f"error: {shown}: has no tcw-version"), ran


def test_ac12_a_key_yaml_reads_as_a_boolean_must_be_text(tmp_path):
    root = tmp_path / "p"
    (root / "docs" / "work").mkdir(parents=True)
    write_config(root, "id: p\nwork:\n  on: x\n")
    ran = tcw(root, "work", "list")
    assert ran.code == 1, ran
    assert "work[True]: key True must be text: lowercase letters" in ran.err, ran


# -- AC 13, 13a: other projects -------------------------------------------------------


def test_ac13_a_3x_connection_is_reported_and_not_read(tmp_path):
    # The 3.x file connects a child of its own, whose file is from a newer
    # TCW. Reading the 3.x file at all reports a problem naming it; following
    # its connections reports the child's. Either one shows it was read.
    old = legacy_project(tmp_path / "old")
    (old / "tcw-config.yaml").write_text(
        "id: old\nprojects:\n  children:\n    deeper: ../deeper\n")
    deeper = tmp_path / "deeper"
    write_config(deeper, "tcw-version: 99.0.0\nid: deeper\n")
    ws = tmp_path / "ws"
    write_config(ws, "id: ws\nprojects:\n  children:\n    old: ../old\n")
    for argv in (("projects", "list"), ("validate",)):
        ran = tcw(ws, *argv)
        assert ran.code == 1, ran
        assert f"{old.resolve()}: {LEGACY}" in ran.out + ran.err, ran
        assert f"{old.resolve()}: {old.resolve()}" not in ran.out + ran.err, \
            "the folder is named once"
        assert str(old.resolve() / "tcw-config.yaml") not in ran.out + ran.err, \
            "the 3.x file was read"
        assert str(deeper.resolve()) not in ran.out + ran.err, \
            "the 3.x file's connections were followed"
    ran = tcw(ws, "validate")
    assert ran.out.splitlines() == [f"error: {old.resolve()}: {LEGACY}"], ran
    assert "1 error, 0 warnings, 0 unresolved" in ran.err, ran


def test_ac13_a_variable_naming_a_3x_folder_says_so_once(tmp_path):
    old = legacy_project(tmp_path / "old")
    ws = tmp_path / "ws"
    write_config(ws, "id: ws\nprojects:\n  children:\n    old: ../missing\n")
    ran = tcw(ws, "validate", env={"TCW_PROJECT_OLD": str(old)})
    assert ran.code == 1, ran
    assert ran.out.splitlines() == [f"error: {old.resolve()}: TCW_PROJECT_OLD names {LEGACY.removeprefix('is ')}"], ran


def _json_projects(ran: Ran) -> list[dict]:
    if ran.code != 0:
        return []
    data = json.loads(ran.out)
    return data["projects"] if isinstance(data, dict) else data


def _pair(tmp_path: Path) -> tuple[Path, Path]:
    app = project(tmp_path / "app", "app", "projects:\n  parent:\n    ws: ../ws\n")
    ws = project(tmp_path / "ws", "ws", "projects:\n  children:\n    app: ../app\n")
    return ws, app


def _folders(ran: Ran) -> dict[str, str]:
    assert ran.code == 0, ran
    return {p["id"]: p["path"] for p in _json_projects(ran)}


def test_ac13a_connected_projects_are_listed_by_their_roots(tmp_path):
    ws, app = _pair(tmp_path)
    folders = _folders(tcw(ws, "projects", "list", "--json"))
    assert Path(folders["ws"]).resolve() == ws.resolve()
    assert Path(folders["app"]).resolve() == app.resolve()
    assert not any(Path(f).name == ".tcw" for f in folders.values())


def test_ac13a_a_project_found_through_its_variable_is_listed_by_its_root(tmp_path):
    ws, app = _pair(tmp_path)
    moved = tmp_path / "elsewhere" / "app"
    moved.parent.mkdir()
    app.rename(moved)
    folders = _folders(tcw(ws, "projects", "list", "--json",
                           env={"TCW_PROJECT_APP": str(moved)}))
    assert Path(folders["app"]).resolve() == moved.resolve()


def test_ac13a_a_connected_project_from_a_newer_tcw_is_that_connections_problem(tmp_path):
    ws, app = _pair(tmp_path)
    path = config_file(app)
    path.write_text(path.read_text().replace(f"tcw-version: {__version__}",
                                             "tcw-version: 99.0.0"))
    ran = tcw(ws, "validate")
    assert ran.code == 1, ran
    assert (f"error: {path.resolve()}: was written by TCW 99.0 (tcw-version 99.0.0), "
            f"newer than this TCW ({__version__}); upgrade TCW") in ran.out.splitlines(), ran


def test_ac13a_init_writes_nothing_over_a_file_from_a_newer_tcw(tmp_path):
    root = tmp_path / "p"
    write_config(root, "tcw-version: 99.0.0\n# no id yet\n")
    before = snapshot(root)
    ran = tcw(root, "init", "--id", "demo")
    assert ran.code == 1, ran
    assert "newer than this TCW" in ran.err and "upgrade TCW" in ran.err, ran
    assert snapshot(root) == before


# -- AC 14b: a tracked personal file --------------------------------------------------


def test_ac14b_validate_warns_when_the_personal_file_is_tracked(tmp_path):
    root = repository(tmp_path / "p")
    assert tcw(root, "init", "--id", "p").code == 0
    write_local_config(root, "user:\n  name: Someone\n")
    env = personal_env(tmp_path)
    warning = ("warning: .tcw/tcw-config.local.yaml: tracked; personal configuration "
               "should stay out of version control (stop tracking it and list it in "
               ".tcw/.gitignore)")
    assert warning not in tcw(root, "validate", env=env).out
    git(root, "add", "-f", ".tcw/tcw-config.local.yaml")
    ran = tcw(root, "validate", env=env)
    assert ran.code == 0, ran
    assert warning in ran.out.splitlines(), ran
