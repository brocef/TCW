"""The output contract, held for every command (TCW-73 Design 10; AC 8, 9, 10,
11, 12, 20, 26, 28).

Filesystem cases run `python -m tcw.cli` as a subprocess, in a project made by
`tcw init --id fx` itself, so what is checked is what a shell sees: the two
streams and the exit code. Jira cases run in-process (plan choice 1): TCW-71's
fake replaces the client inside the running interpreter, which a subprocess
cannot receive.

`ROWS` names every leaf command with arguments that parse. A command added
without a row fails `test_every_leaf_command_has_a_row`, and every row is run
outside a project, so a new command is held to that case without anyone
remembering to add it.
"""

from __future__ import annotations

import argparse
import io
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pytest
import yaml

import tcw
from tcw.cli import build_parser, main
from tcw.errors import BackendError, Refused
from tcw.work.jira.backend import JiraBackend
from tcw.work.model import Item, Slug
from tests.work.jira.conftest import EMAIL_ENV, TOKEN_ENV, fake, jira_config  # noqa: F401
from tests.work.jira.fake import SITE

TODAY = date.today().isoformat()
SOURCE = str(Path(tcw.__file__).resolve().parent.parent)

# Every leaf command, with arguments that parse, and the exit code outside a
# project. `init` is left out of the outside run: making a project is what it
# does there. `procedure` reads TCW's own text and works anywhere (plan choice 3).
ROWS: dict[str, tuple[list[str], int]] = {
    "init": (["init", "--id", "fx"], 0),
    "provision": (["provision", "--dry-run"], 1),
    "validate": (["validate"], 1),
    "serve": (["serve", "--no-open", "--port", "1"], 1),
    "projects list": (["projects", "list"], 1),
    "taxonomy list": (["taxonomy", "list"], 1),
    "taxonomy add": (["taxonomy", "add", "Widget"], 1),
    "taxonomy show": (["taxonomy", "show", "widget"], 1),
    "taxonomy path": (["taxonomy", "path"], 1),
    "taxonomy rm": (["taxonomy", "rm", "widget"], 1),
    "taxonomy search": (["taxonomy", "search", "w"], 1),
    "taxonomy extends add": (["taxonomy", "extends", "add", "up"], 1),
    "taxonomy extends rm": (["taxonomy", "extends", "rm", "up"], 1),
    "capabilities list": (["capabilities", "list"], 1),
    "capabilities show": (["capabilities", "show", "ns/a"], 1),
    "capabilities path": (["capabilities", "path"], 1),
    "capabilities add": (["capabilities", "add", "ns/a"], 1),
    "capabilities set": (["capabilities", "set", "ns/a", "--status", "Supported"], 1),
    "capabilities reset": (["capabilities", "reset", "ns/a"], 1),
    "capabilities rm": (["capabilities", "rm", "ns/a"], 1),
    "capabilities search": (["capabilities", "search", "a"], 1),
    "capabilities extends add": (["capabilities", "extends", "add", "up"], 1),
    "capabilities extends rm": (["capabilities", "extends", "rm", "up"], 1),
    "capabilities drift": (["capabilities", "drift"], 1),
    "work new": (["work", "new", "A b"], 1),
    "work list": (["work", "list"], 1),
    "work show": (["work", "show", "fx/2026-10-01-a"], 1),
    "work path": (["work", "path"], 1),
    "work edit": (["work", "edit", "fx/2026-10-01-a", "--priority", "high"], 1),
    "work advance": (["work", "advance", "fx/2026-10-01-a"], 1),
    "work discard": (["work", "discard", "fx/2026-10-01-a", "--reason", "r"], 1),
    "work comment": (["work", "comment", "fx/2026-10-01-a"], 1),
    "work rename": (["work", "rename", "fx/2026-10-01-a", "b"], 1),
    "work stage prompt": (["work", "stage", "prompt", "spec"], 1),
    "work procedure": (["work", "procedure", "audit-backlog"], 0),
    "work lifecycle": (["work", "lifecycle"], 1),
    "work docs": (["work", "docs"], 1),
    "work tags list": (["work", "tags", "list"], 1),
    "work tags add": (["work", "tags", "add", "a"], 1),
    "work tags rm": (["work", "tags", "rm", "a"], 1),
    "work tickets list": (["work", "tickets", "list"], 1),
    "work tickets adopt": (["work", "tickets", "adopt", "TCW-1"], 1),
}


def leaf_commands(parser: argparse.ArgumentParser, path: tuple[str, ...] = ()):
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            for name, child in action.choices.items():
                here = (*path, name)
                if any(isinstance(a, argparse._SubParsersAction) for a in child._actions):
                    yield from leaf_commands(child, here)
                else:
                    yield " ".join(here)


def missing_rows(parser: argparse.ArgumentParser) -> set[str]:
    return set(leaf_commands(parser)) - set(ROWS)


# -- running it ---------------------------------------------------------------------


@dataclass
class Result:
    code: int
    out: str
    err: str

    @property
    def lines(self) -> list[str]:
        return self.out.splitlines()


def run(cwd: Path, *argv: str, stdin: str = "") -> Result:
    env = {**os.environ, "PYTHONPATH": SOURCE}
    done = subprocess.run([sys.executable, "-m", "tcw.cli", *argv], cwd=cwd, env=env,
                          input=stdin, capture_output=True, text=True, timeout=60)
    return Result(done.returncode, done.stdout, done.stderr)


def ok(cwd: Path, *argv: str, stdin: str = "") -> Result:
    result = run(cwd, *argv, stdin=stdin)
    assert result.code == 0, (argv, result)
    return result


def snapshot(root: Path) -> dict[str, bytes | None]:
    """Every path under `root`, a file with its bytes, a folder as None."""
    found = {}
    for path in root.rglob("*"):
        if ".git" in path.relative_to(root).parts:
            continue
        found[path.relative_to(root).as_posix()] = (
            path.read_bytes() if path.is_file() else None)
    return found


NAMED = re.compile(r"^(wrote|removed|created) (.+?)/?$")


def named(err: str) -> set[str]:
    return {m.group(2) for line in err.splitlines() if (m := NAMED.match(line))}


def unnamed(before: dict, after: dict, err: str) -> tuple[set[str], set[str]]:
    """What changed but stderr does not name, and what stderr names that did
    not change. Every file created, changed or removed must be named. A
    folder created or removed is named either itself or by a file under it,
    since a removed folder is named one file per line (Design 1.2)."""
    gone = object()
    changed = {p for p in before.keys() | after.keys()
               if before.get(p, gone) != after.get(p, gone)}
    said = named(err)
    missing = set()
    for path in changed:
        is_folder = after.get(path, before.get(path)) is None
        if path in said:
            continue
        if is_folder and any(s.startswith(path + "/") for s in said):
            continue
        missing.add(path)
    return missing, said - changed


@pytest.fixture
def fx(tmp_path):
    root = tmp_path / "fx"
    root.mkdir()
    ok(root, "init", "--id", "fx")
    return root


def configure(root: Path, **work) -> None:
    path = root / "tcw-config.yaml"
    document = yaml.safe_load(path.read_text())
    document.setdefault("work", {}).update(work)
    path.write_text(yaml.safe_dump(document, sort_keys=False))


def new(root: Path, title: str = "A b", *flags: str, stdin: str = "") -> str:
    return ok(root, "work", "new", title, *flags, stdin=stdin).out.strip()


# -- AC 20: every command has a row ---------------------------------------------------


def test_every_leaf_command_has_a_row():
    assert missing_rows(build_parser()) == set()


def test_a_command_without_a_row_is_caught():
    parser = build_parser()
    work = next(a for a in parser._actions
                if isinstance(a, argparse._SubParsersAction)).choices["work"]
    verbs = next(a for a in work._actions if isinstance(a, argparse._SubParsersAction))
    verbs.add_parser("dummy", help="a command nobody gave a row")
    assert missing_rows(parser) == {"work dummy"}


# -- AC 10: outside a project ------------------------------------------------------


@pytest.mark.parametrize("command", sorted(set(ROWS) - {"init"}))
def test_every_command_outside_a_project(tmp_path, command):
    argv, expected = ROWS[command]
    result = run(tmp_path, *argv)
    assert result.code == expected, (command, result)
    if expected == 1:
        assert result.out == ""
        assert result.err.startswith(f"tcw {command}: "), result.err
    assert snapshot(tmp_path) == {}


def test_version_help_and_a_parse_error_outside_a_project(tmp_path):
    assert run(tmp_path, "--version").code == 0
    assert run(tmp_path, "--help").code == 0
    assert run(tmp_path, "work", "list", "--nonsense").code == 2


# -- AC 8 and 9: stdout per command, and every file named ---------------------------


def written(root: Path, *argv: str, stdin: str = "", code: int = 0) -> Result:
    """Run a writing command and check that stderr names exactly what changed."""
    before = snapshot(root)
    result = run(root, *argv, stdin=stdin)
    assert result.code == code, (argv, result)
    assert unnamed(before, snapshot(root), result.err) == (set(), set()), \
        (argv, result.err)
    return result


def test_init_prints_nothing_and_names_everything(tmp_path):
    result = written(tmp_path, "init", "--id", "fx")
    assert result.out == "" and named(result.err)


def test_the_work_commands(fx):
    made = written(fx, "work", "new", "A b", stdin="Need X\n")
    assert re.fullmatch(r"fx/[0-9]{4}-[0-9]{2}-[0-9]{2}-a-b\n", made.out), made.out
    slug = made.out.strip()

    assert ok(fx, "work", "advance", slug, "--dry-run").out == "spec\n"
    assert written(fx, "work", "advance", slug).out == "spec\n"
    assert written(fx, "work", "edit", slug, "--priority", "high").out == ""
    assert written(fx, "work", "comment", slug, stdin="one\n").out == ""
    assert written(fx, "work", "comment", slug, stdin="two\n").out == ""

    shown = ok(fx, "work", "show", slug).lines
    request, comments = shown.index("request:"), shown.index("comments:")
    assert 0 < request < comments
    assert "Need X" in "\n".join(shown[request:comments])
    tail = "\n".join(shown[comments:])
    assert tail.index("two") < tail.index("one")

    data = json.loads(ok(fx, "work", "show", slug, "--json").out)
    assert data["schema"] == 1 and "Need X" in data["request"]
    assert [c["text"].strip() for c in data["comments"]] == ["two", "one"]
    assert data["item"]["untracked"] == []

    assert ok(fx, "work", "list").lines == [slug]


def test_an_item_with_no_request(fx):
    slug = new(fx, "Quiet")
    assert "request: none" in ok(fx, "work", "show", slug).lines
    assert json.loads(ok(fx, "work", "show", slug, "--json").out)["request"] is None


def test_a_refused_dry_run_prints_nothing(fx):
    configure(fx, stages={"spec": {"pre": [{"command": "false"}]}})
    slug = new(fx)
    before = snapshot(fx)
    result = run(fx, "work", "advance", slug, "--dry-run")
    assert (result.code, result.out) == (3, "")
    assert snapshot(fx) == before


def test_list_by_tag(fx):
    configure(fx, tags=["a", "b"])
    tagged_a = new(fx, "First", "--tag", "a")
    tagged_b = new(fx, "Second", "--tag", "b")
    new(fx, "Third")
    assert sorted(ok(fx, "work", "list", "--tag", "a", "--tag", "b").lines) == \
        sorted([tagged_a, tagged_b])
    ok(fx, "work", "advance", tagged_a)
    assert ok(fx, "work", "list", "--tag", "a", "--tag", "b", "--stage", "spec").lines \
        == [tagged_a]
    unknown = run(fx, "work", "list", "--tag", "zzz")
    assert (unknown.code, unknown.out) == (0, "")
    assert any(line.startswith("warning: ") and "zzz" in line
               for line in unknown.err.splitlines())


def test_the_tree_commands(fx):
    assert written(fx, "taxonomy", "add", "Widget").out == "widget\n"
    assert written(fx, "capabilities", "add", "ns/do-a-thing").out == "ns/do-a-thing\n"
    assert written(fx, "capabilities", "set", "ns/do-a-thing",
                   "--status", "Supported").out == ""
    removed = written(fx, "taxonomy", "rm", "widget")
    assert removed.out == ""
    assert len([l for l in removed.err.splitlines() if l.startswith("removed ")]) == 2


def test_extends_add_prints_nothing(tmp_path, fx):
    up = tmp_path / "up"
    up.mkdir()
    ok(up, "init", "--id", "up")
    document = yaml.safe_load((fx / "tcw-config.yaml").read_text())
    document["projects"] = {"upstream": {"up": "../up"}}
    (fx / "tcw-config.yaml").write_text(yaml.safe_dump(document))
    assert written(fx, "taxonomy", "extends", "add", "up").out == ""


def test_a_clean_validate_prints_nothing(fx):
    assert ok(fx, "validate").out == ""


def test_every_json_output_is_one_object_with_schema_1(fx):
    configure(fx, tags=["a"])
    slug = new(fx)
    ok(fx, "taxonomy", "add", "Widget")
    ok(fx, "capabilities", "add", "ns/do-a-thing")
    for argv in (["work", "list", "--json"], ["work", "show", slug, "--json"],
                 ["work", "lifecycle", "--json"], ["work", "docs", "--json"],
                 ["projects", "list", "--json"], ["taxonomy", "list", "--json"],
                 ["taxonomy", "show", "widget", "--json"],
                 ["taxonomy", "search", "w", "--json"],
                 ["capabilities", "list", "--json"],
                 ["capabilities", "show", "ns/do-a-thing", "--json"],
                 ["capabilities", "search", "thing", "--json"]):
        data = json.loads(ok(fx, *argv).out)
        assert isinstance(data, dict) and next(iter(data)) == "schema", argv
        assert data["schema"] == 1, argv


# -- AC 10: exit codes ------------------------------------------------------------


def test_naming_an_item(fx):
    slug = new(fx)
    folder = slug.split("/", 1)[1]
    assert run(fx, "work", "show", "fx/no-such").code == 4
    assert run(fx, "work", "show", "a/b/c").code == 2
    assert run(fx, "work", "show", folder[:10]).code == 4
    assert run(fx, "work", "advance", slug, "--to", "nonsense").code == 2
    renamed = ok(fx, "work", "rename", slug, "other").out.strip()
    assert renamed == f"fx/{TODAY}-other"
    assert run(fx, "work", "show", slug).code == 4


def test_list_flag_shapes(fx):
    comma = run(fx, "work", "list", "--tag", "a,b")
    assert comma.code == 2 and "repeat" in comma.err
    assert run(fx, "work", "list", "--tags", "a").code == 2


def test_hooks(fx):
    record = fx / "hook.txt"
    configure(fx, stages={
        "spec": {"pre": [{"command": f'printf "%s %s" "$TCW_SLUG" "$PWD" > {record}'}],
                 "post": [{"command": "false"}]}})
    slug = new(fx)
    sub = fx / "docs"
    result = run(sub, "work", "advance", slug)
    assert (result.code, result.out) == (6, "spec\n")
    tcw_slug, cwd = record.read_text().split(" ", 1)
    assert tcw_slug == slug and Path(cwd).resolve() == fx.resolve()

    configure(fx, stages={"plan": {"pre": [{"command": "false"}]}})
    assert run(fx, "work", "advance", slug).code == 3


def test_tree_exit_codes(fx):
    ok(fx, "taxonomy", "add", "Widget")
    assert run(fx, "taxonomy", "add", "Widget").code == 3
    assert run(fx, "taxonomy", "show", "nosuch").code == 4
    assert run(fx, "capabilities", "show", "nosuch").code == 4
    ok(fx, "taxonomy", "add", "Gadget")
    meta = fx / "docs" / "taxonomy" / "gadget" / "meta.yaml"
    meta.write_text(meta.read_text().replace("relatesTo: []", "relatesTo: [widget]"))
    assert run(fx, "taxonomy", "rm", "widget").code == 3

    ok(fx, "capabilities", "add", "ns/do-a-thing")
    thing = ("capabilities", "set", "ns/do-a-thing")
    assert run(fx, *thing, "--field", "Subject=nosuch").code == 2
    assert run(fx, "capabilities", "reset", "ns/do-a-thing").code == 3
    ok(fx, "taxonomy", "add", "A")
    ok(fx, "taxonomy", "add", "B")
    ok(fx, *thing, "--field", "Subject=a,b")
    assert "Subject: a, b" in ok(fx, "capabilities", "show", "ns/do-a-thing").out
    for fields in (["--field", "Status=Supported", "--field", "Status=Missing"],
                   ["--field", "Status"], ["--field", "Planning doc=x"],
                   ["--field", "Tracker=x"]):
        assert run(fx, *thing, *fields).code == 2, fields


def test_filesystem_mode_usage_errors(fx):
    slug = new(fx)
    assert run(fx, "work", "tickets", "list").code == 2
    assert run(fx, "validate", "--remote").code == 2
    assert run(fx, "work", "comment", slug, stdin="").code == 2


# -- AC 26: a late failure still names what it made -------------------------------


def test_a_rename_that_fails_after_moving_prints_the_new_slug(fx):
    slug = new(fx, "Target")
    child = new(fx, "Child", "--parent", slug)
    folder = fx / "docs" / "work" / child.split("/", 1)[1]
    folder.chmod(0o555)
    (folder / "item.yaml").chmod(0o444)
    try:
        result = run(fx, "work", "rename", slug, "moved")
    finally:
        folder.chmod(0o755)
        (folder / "item.yaml").chmod(0o644)
    assert (result.code, result.out) == (1, f"fx/{TODAY}-moved\n"), result


# -- Jira mode, in-process (plan choice 1) ------------------------------------------


@pytest.fixture
def jira_fx(tmp_path, fake, monkeypatch, capsys):  # noqa: F811
    from tests.work.projects import make_project
    root = make_project(tmp_path, "fx", config=jira_config("fx"))

    def call(*argv: str, stdin: str = "") -> Result:
        monkeypatch.chdir(root)
        monkeypatch.setattr(sys, "stdin", io.StringIO(stdin))
        try:
            code = main(list(argv))
        except SystemExit as stop:
            code = stop.code
        captured = capsys.readouterr()
        return Result(code, captured.out, captured.err)
    call.root = root
    return call


def stub_item(folder: str, **fields) -> Item:
    values = dict(slug=Slug("fx", folder), title="A thing", stage="spec",
                  created=date(2026, 10, 1), priority=None, effort=None,
                  complexity=None, tags=(), assignee=None, parent=None,
                  blocked_by=(), untracked=("EXT-4",))
    values.update(fields)
    return Item(**values)


def test_a_key_names_an_item(jira_fx, monkeypatch):
    monkeypatch.setattr(JiraBackend, "lookup",
                        lambda self, key: "TCW-9-a-thing" if key == "TCW-9" else None)
    monkeypatch.setattr(JiraBackend, "read", lambda self, folder: stub_item(folder))
    monkeypatch.setattr(JiraBackend, "read_request", lambda self, folder: None)
    monkeypatch.setattr(JiraBackend, "read_comments", lambda self, folder, limit=None: [])
    shown = jira_fx("work", "show", "TCW-9")
    assert shown.code == 0, shown
    slugs = re.findall(r"(?<![\w/])\w+/TCW-9-a-thing\b", shown.out)
    assert slugs and set(slugs) == {"fx/TCW-9-a-thing"}
    data = json.loads(jira_fx("work", "show", "TCW-9", "--json").out)
    assert data["item"]["priority"] is None and data["item"]["untracked"] == ["EXT-4"]
    assert jira_fx("work", "show", "TCW-10").code == 4


def test_a_refused_create_prints_the_key_it_left(jira_fx, monkeypatch):
    def create(self, *args, **kwargs):
        raise Refused("created TCW-11, but stopped", name="TCW-11")
    monkeypatch.setattr(JiraBackend, "create", create)
    result = jira_fx("work", "new", "x")
    assert (result.code, result.out) == (3, "TCW-11\n")


def test_a_late_backend_error_prints_the_slug(jira_fx, monkeypatch):
    def create(self, *args, **kwargs):
        raise BackendError("made the folder, then failed", name="fx/2026-10-02-x")
    monkeypatch.setattr(JiraBackend, "create", create)
    result = jira_fx("work", "new", "x")
    assert (result.code, result.out) == (1, "fx/2026-10-02-x\n")


def test_an_early_failure_prints_nothing(jira_fx, monkeypatch):
    def create(self, *args, **kwargs):
        raise BackendError("failed before anything was made")
    monkeypatch.setattr(JiraBackend, "create", create)
    result = jira_fx("work", "new", "x")
    assert (result.code, result.out) == (1, "")


def test_jira_unreachable_and_the_inbox(jira_fx, monkeypatch):
    from tcw.errors import Unreachable

    def down(self, query):
        raise Unreachable("Jira did not answer")
    monkeypatch.setattr(JiraBackend, "list", down)
    assert jira_fx("work", "list").code == 5
    assert jira_fx("work", "new", "x", "--stage", "inbox").code == 2


def test_tickets_list_prints_keys_only(jira_fx, fake):  # noqa: F811
    fake.ticket("Waiting")
    result = jira_fx("work", "tickets", "list")
    assert result.code == 0, result
    assert result.lines and all(re.fullmatch(r"TCW-\d+", l) for l in result.lines)


# -- AC 12: across projects -------------------------------------------------------


@pytest.fixture
def graph(tmp_path, fake):  # noqa: F811
    """`fx` with a present child `other`, an upstream `up`, a declared child
    `absent` not here, and `absentj`, not here but reachable through Jira."""
    roots = {}
    for name in ("fx", "other", "up"):
        roots[name] = tmp_path / name
        roots[name].mkdir()
        ok(roots[name], "init", "--id", name)
    block = {"site": SITE, "project": "TCW", "inbox-status": "To Do",
             "credentials": {"email-env": EMAIL_ENV, "token-env": TOKEN_ENV},
             "fields": {"project": "TCW Project"}}
    document = yaml.safe_load((roots["fx"] / "tcw-config.yaml").read_text())
    document["projects"] = {
        "children": {"other": "../other", "absent": "../absent",
                     "absentj": {"path": "../absentj", "jira": block}},
        "upstream": {"up": "../up"}}
    (roots["fx"] / "tcw-config.yaml").write_text(yaml.safe_dump(document))
    for name in ("other", "up"):
        path = roots[name] / "tcw-config.yaml"
        child = yaml.safe_load(path.read_text())
        if name == "other":
            child["projects"] = {"parent": {"fx": "../fx"}}
        path.write_text(yaml.safe_dump(child))
    return roots


def test_another_projects_item_reads_but_does_not_write(graph):
    item = new(graph["other"], "Theirs")
    assert ok(graph["fx"], "work", "show", item).code == 0
    advanced = run(graph["fx"], "work", "advance", item)
    assert advanced.code == 3 and "other" in advanced.err


def test_naming_projects_that_are_not_here(graph):
    assert run(graph["fx"], "work", "show", "ghost/x").code == 4
    absent = run(graph["fx"], "work", "show", "absent/x")
    assert absent.code == 5 and "tcw provision" in absent.err


@pytest.mark.parametrize("target, says", [("ghost", None), ("absent", None),
                                          ("up", "read-only")])
def test_delegation_that_is_refused_writes_nothing(graph, target, says):
    before = {name: snapshot(root) for name, root in graph.items()}
    result = run(graph["fx"], "work", "new", "x", "--project", target)
    assert result.code == 3, result
    if says:
        assert says in result.err
    assert {name: snapshot(root) for name, root in graph.items()} == before


def test_delegation_through_jira_and_blocks(graph, fake, monkeypatch, capsys):  # noqa: F811
    monkeypatch.chdir(graph["fx"])
    monkeypatch.setattr(sys, "stdin", io.StringIO(""))
    assert main(["work", "new", "x", "--project", "absentj"]) == 0
    key = capsys.readouterr().out.strip()
    assert re.fullmatch(r"TCW-\d+", key) and fake.tickets[key].status == "To Do"

    mine = new(graph["fx"], "Mine")
    monkeypatch.setattr(sys, "stdin", io.StringIO(""))
    assert main(["work", "edit", mine, "--blocks", "absentj/x"]) == 3


# -- AC 28: people in Jira mode ---------------------------------------------------


def test_people_by_name_in_text_and_by_id_in_json(jira_fx, fake, monkeypatch):  # noqa: F811
    fake.account("ada@example.test", "acct-ada", "Ada")
    fake.account("bo@example.test", "acct-bo", "Bo")
    from tcw.work.backend import Comment
    from datetime import datetime, timezone
    monkeypatch.setattr(JiraBackend, "lookup", lambda self, key: "TCW-9-a-thing")
    monkeypatch.setattr(JiraBackend, "read",
                        lambda self, folder: stub_item(folder, assignee="acct-ada"))
    monkeypatch.setattr(JiraBackend, "read_request", lambda self, folder: None)
    monkeypatch.setattr(JiraBackend, "read_comments", lambda self, folder, limit=None: [
        Comment(at=datetime(2026, 10, 2, tzinfo=timezone.utc), author="acct-bo",
                text="hello")])
    text = jira_fx("work", "show", "TCW-9")
    assert text.code == 0, text
    assert "Ada" in text.out and "Bo" in text.out
    data = jira_fx("work", "show", "TCW-9", "--json").out
    assert "acct-ada" in data and "acct-bo" in data
    assert "Ada" not in data and '"Bo"' not in data
