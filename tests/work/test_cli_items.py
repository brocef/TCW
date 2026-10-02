"""The 3.0 `tcw work` item commands, run in-process (TCW-70 Design 7; the
in-process half of AC 2-9 and 11)."""

import io
import os
import re
import shutil
import sys
from dataclasses import dataclass
from datetime import date

import pytest
import yaml

from tcw.work import cli_next
from tests.work.projects import commit_all, connect, git, make_project, write_item

TODAY = date.today().isoformat()


@dataclass
class Result:
    code: int
    out: str
    err: str


@pytest.fixture
def tcw(monkeypatch, capsys):
    def run(argv, cwd, stdin=""):
        monkeypatch.chdir(cwd)
        monkeypatch.setattr(sys, "stdin", io.StringIO(stdin))
        code = cli_next.run(["work", *argv])
        captured = capsys.readouterr()
        return Result(code, captured.out, captured.err)
    return run


def item_yaml(root, folder):
    return yaml.safe_load((root / "docs" / "work" / folder / "item.yaml").read_text())


@pytest.fixture
def p(tmp_path):
    return make_project(tmp_path, "p", config={"tags": ["ui", "api", "old"]})


# -- AC 2: new --------------------------------------------------------------------------

def test_new_prints_the_slug_and_writes_three_keys(tcw, p):
    r = tcw(["new", "Add a widget"], p)
    assert (r.code, r.out) == (0, f"p/{TODAY}-add-a-widget\n")
    folder = p / "docs" / "work" / f"{TODAY}-add-a-widget"
    assert (folder / "item.yaml").read_text() == (
        "title: Add a widget\nstage: request\npriority: medium\n")
    assert not (folder / "request").exists()


def test_a_second_new_the_same_day_is_refused(tcw, p):
    tcw(["new", "Add a widget"], p)
    r = tcw(["new", "Add a widget"], p)
    assert r.code == 3 and f"{TODAY}-add-a-widget" in r.err
    assert not list((p / "docs" / "work").glob("*-2"))


def test_untitled(tcw, p):
    assert tcw(["new", "!!!"], p).out == f"p/{TODAY}-untitled\n"


# -- AC 3: request text ------------------------------------------------------------------

def test_piped_request_text(tcw, p):
    r = tcw(["new", "X"], p, stdin="line one\n")
    folder = r.out.strip().split("/")[1]
    assert (p / "docs/work" / folder / "request/request.md").read_text() == "line one\n"


def test_inbox_stage(tcw, p):
    r = tcw(["new", "Y", "--stage", "inbox"], p, stdin="line one\n")
    folder = r.out.strip().split("/")[1]
    assert item_yaml(p, folder)["stage"] == "inbox"
    assert (p / "docs/work" / folder / "request/request.md").read_text() == "line one\n"
    assert not list(p.rglob("intake.md"))


def test_only_the_first_flow_stage_is_accepted(tcw, p):
    assert tcw(["new", "Z", "--stage", "spec"], p).code == 2


# -- AC 4: reading ---------------------------------------------------------------------------

@pytest.mark.parametrize("text, key", [
    ("title: t\nstage: request\ncreated: 2026-01-01\n", "created"),
    ("stage: request\n", "title"),
    ("title: t\nstage: request\npriority: 3\n", "priority"),
    ("title: [t\n", None),
])
def test_show_of_an_unreadable_item(tcw, p, text, key):
    write_item(p, "2026-10-01-x", text)
    r = tcw(["show", "2026-10-01-x"], p)
    assert r.code == 1 and "item.yaml" in r.err
    if key:
        assert key in r.err


@pytest.mark.parametrize("config, stage", [({}, "verify"),
                                           ({"stages": {"plan": {"enabled": False}}}, "plan")])
def test_no_stage(tcw, tmp_path, config, stage):
    root = make_project(tmp_path, "p", config=config)
    write_item(root, "2026-10-01-x", {"title": "t", "stage": stage})
    r = tcw(["show", "2026-10-01-x", "--json"], root)
    assert r.code == 0 and '"stage": null' in r.out
    assert tcw(["advance", "2026-10-01-x"], root).code == 3
    r = tcw(["advance", "2026-10-01-x", "--to", "spec", "--force", "--reason", "r"], root)
    assert (r.code, r.out) == (0, "spec\n")
    assert item_yaml(root, "2026-10-01-x")["stage"] == "spec"


def test_edit_keeps_a_stage_it_cannot_read(tcw, p):
    write_item(p, "2026-10-01-x", {"title": "t", "stage": "verify"})
    r = tcw(["edit", "2026-10-01-x", "--priority", "high"], p)
    assert (r.code, r.out) == (0, "")
    assert item_yaml(p, "2026-10-01-x") == {"title": "t", "stage": "verify",
                                            "priority": "high"}


def test_a_tag_removed_from_the_registry(tcw, tmp_path):
    root = make_project(tmp_path, "p", config={"tags": ["ui"]})
    write_item(root, "2026-10-01-x", {"title": "t", "stage": "spec", "tags": ["old"]})
    assert tcw(["edit", "2026-10-01-x", "--priority", "high"], root).code == 0
    assert item_yaml(root, "2026-10-01-x")["tags"] == ["old"]
    assert tcw(["edit", "2026-10-01-x", "--untag", "old"], root).code == 0
    assert "tags" not in item_yaml(root, "2026-10-01-x")
    assert tcw(["edit", "2026-10-01-x", "--tag", "nosuch"], root).code == 2


def test_show_with_another_item_unreadable(tcw, p):
    write_item(p, "2026-10-01-a", {"title": "a", "stage": "spec"})
    write_item(p, "2026-10-01-b", {"title": "b", "stage": "spec",
                                  "parent": "p/2026-10-01-a",
                                  "blocked-by": ["p/2026-10-01-a"]})
    write_item(p, "2026-10-01-bad", "title: [x\n")
    r = tcw(["show", "2026-10-01-a", "--json"], p)
    assert r.code == 0
    record = yaml.safe_load(r.out)
    assert record["children"] == ["p/2026-10-01-b"]
    assert record["blocks"] == ["p/2026-10-01-b"]
    [line] = r.err.strip().splitlines()
    assert "2026-10-01-bad/item.yaml" in line


def test_plain_show_has_one_line_per_field(tcw, p):
    write_item(p, "2026-10-01-a", {"title": "a", "stage": "spec"})
    r = tcw(["show", "2026-10-01-a"], p)
    assert "title: a" in r.out.splitlines() and "stage: spec" in r.out.splitlines()


# -- AC 5: listing ---------------------------------------------------------------------------

def slugs(r):
    return r.out.split()


def test_the_default_list(tcw, p):
    for folder, stage in (("2026-10-01-inbox", "inbox"), ("2026-10-01-lost", "verify"),
                          ("2026-10-01-done", "completed"), ("2026-10-01-gone", "discarded"),
                          ("2026-10-01-open", "spec")):
        write_item(p, folder, {"title": folder, "stage": stage})
    (p / "docs/work/notes").mkdir()
    (p / "docs/work/README.md").write_text("hi")
    assert slugs(tcw(["list"], p)) == ["p/2026-10-01-inbox", "p/2026-10-01-lost",
                                       "p/2026-10-01-open"]
    assert slugs(tcw(["list", "--stage", "inbox"], p)) == ["p/2026-10-01-inbox"]
    assert len(slugs(tcw(["list", "--all"], p))) == 5
    assert tcw(["list", "--stage", "inbox", "--all"], p).code == 2


def test_an_unreadable_item_fails_list(tcw, p):
    write_item(p, "2026-10-01-bad", "title: [x\n")
    r = tcw(["list"], p)
    assert r.code == 1 and "2026-10-01-bad" in r.err


def test_the_tag_filter(tcw, p):
    for name, tags in (("a", ["ui"]), ("b", ["api", "ui"]), ("c", ["api"]), ("d", [])):
        write_item(p, f"2026-10-01-{name}", {"title": name, "stage": "request",
                                            **({"tags": tags} if tags else {})})
    write_item(p, "2026-10-01-e", {"title": "e", "stage": "completed", "tags": ["ui"]})
    ab = ["p/2026-10-01-a", "p/2026-10-01-b"]
    r = tcw(["list", "--tag", "ui"], p)
    assert slugs(r) == ab and r.err == ""
    assert slugs(tcw(["list", "--tag", "ui", "--tag", "api"], p)) == ab + ["p/2026-10-01-c"]
    assert slugs(tcw(["list", "--tag", "ui,api"], p)) == ab + ["p/2026-10-01-c"]
    assert slugs(tcw(["list", "--tag", "ui", "--all"], p)) == ab + ["p/2026-10-01-e"]
    r = tcw(["list", "--tag", "nosuch"], p)
    assert (r.code, r.out) == (0, "")
    [line] = r.err.splitlines()
    assert line.startswith("warning:") and "nosuch" in line


def test_list_json_is_an_array_of_records(tcw, p):
    write_item(p, "2026-10-01-a", {"title": "a", "stage": "spec"})
    [record] = yaml.safe_load(tcw(["list", "--json"], p).out)
    assert record["slug"] == "p/2026-10-01-a" and record["untracked"] == []


# -- AC 6: comments --------------------------------------------------------------------------

def test_comment(tcw, p):
    write_item(p, "2026-10-01-a", {"title": "a", "stage": "spec"})
    r = tcw(["comment", "2026-10-01-a"], p, stdin="hi\n")
    assert (r.code, r.out) == (0, "")
    [path] = (p / "docs/work/2026-10-01-a/comments").iterdir()
    assert re.fullmatch(r"\d{8}T\d{6}Z\.md", path.name) and path.read_text() == "hi\n"
    assert tcw(["comment", "2026-10-01-a"], p, stdin="  \n").code == 2


# -- AC 7: the trace -------------------------------------------------------------------------

def test_a_forced_move_writes_one_comment(tcw, p):
    write_item(p, "2026-10-01-a", {"title": "a", "stage": "request"})
    r = tcw(["advance", "2026-10-01-a", "--to", "plan", "--force", "--reason", "skip"], p)
    assert (r.code, r.out) == (0, "plan\n")
    assert item_yaml(p, "2026-10-01-a")["stage"] == "plan"
    [comment] = (p / "docs/work/2026-10-01-a/comments").iterdir()
    assert "skip" in comment.read_text()


def test_a_trace_that_cannot_be_written(tcw, p):
    folder = write_item(p, "2026-10-01-a", {"title": "a", "stage": "request"})
    (folder / "comments").write_text("in the way")
    r = tcw(["advance", "2026-10-01-a", "--to", "plan", "--force", "--reason", "skip"], p)
    assert r.code == 6
    assert item_yaml(p, "2026-10-01-a")["stage"] == "plan"
    assert "trace was not recorded" in r.err


def test_a_pre_hook_runs_in_the_project_root(tcw, tmp_path):
    out = tmp_path / "hook.txt"
    root = make_project(tmp_path, "p", config={"stages": {"spec": {"pre": [
        {"command": f'echo "$PWD $TCW_SLUG" > {out}'}]}}})
    folder = write_item(root, "2026-10-01-a", {"title": "a", "stage": "request"})
    (folder / "request").mkdir()
    (folder / "request/request.md").write_text("Do it.\n")
    sub = root / "docs"
    r = tcw(["advance", "2026-10-01-a"], sub)
    assert (r.code, r.out) == (0, "spec\n"), r.err
    where, slug = out.read_text().split()
    assert os.path.realpath(where) == os.path.realpath(root)
    assert slug == "p/2026-10-01-a"


# -- AC 8: rename ----------------------------------------------------------------------------

def test_rename(tcw, tmp_path):
    root = make_project(tmp_path, "p")
    other = make_project(tmp_path, "q")
    connect(root, other, "children")
    connect(other, root, "parent")
    a = write_item(root, "2026-09-01-a", {"title": "a", "stage": "spec"})
    (a / "spec").mkdir()
    (a / "spec/spec.md").write_text("intro\nsee 2026-09-01-a\n")
    write_item(root, "2026-09-01-b", {"title": "b", "stage": "spec",
                                     "parent": "p/2026-09-01-a"})
    write_item(root, "2026-09-01-c", {"title": "c", "stage": "spec",
                                     "blocked-by": ["2026-09-01-a"]})
    write_item(other, "2026-09-01-x", {"title": "x", "stage": "spec",
                                      "blocked-by": ["p/2026-09-01-a"]})
    before = (other / "docs/work/2026-09-01-x/item.yaml").read_text()
    r = tcw(["rename", "2026-09-01-a", "new-words"], root)
    assert (r.code, r.out) == (0, "p/2026-09-01-new-words\n")
    assert item_yaml(root, "2026-09-01-b")["parent"] == "p/2026-09-01-new-words"
    assert item_yaml(root, "2026-09-01-c")["blocked-by"] == ["p/2026-09-01-new-words"]
    assert "spec.md:2" in r.err
    assert not list(root.rglob("renames.yaml"))
    assert (other / "docs/work/2026-09-01-x/item.yaml").read_text() == before
    write_item(root, "2026-09-01-d", {"title": "d", "stage": "spec"})
    assert tcw(["rename", "2026-09-01-d", "new-words"], root).code == 3
    assert tcw(["rename", "2026-09-01-d", "New Words"], root).code == 2
    assert tcw(["rename", "2026-09-01-d", "2026-01-01-d"], root).code == 2
    write_item(root, "2026-09-01-bad", "title: [x\n")
    assert tcw(["rename", "2026-09-01-d", "other"], root).code == 1
    assert (root / "docs/work/2026-09-01-d").is_dir()


# -- AC 9: delegation through the commands ----------------------------------------------------

@pytest.fixture
def pq(tmp_path):
    root = make_project(tmp_path, "p")
    q = make_project(tmp_path, "q", config={"tags": ["ui"]})
    connect(root, q, "children")
    connect(q, root, "parent")
    commit_all(root)
    commit_all(q)
    return root, q


def test_new_into_another_project(tcw, pq):
    root, q = pq
    head = git(q, "rev-parse", "HEAD")
    r = tcw(["new", "T", "--priority", "high", "--project", "q"], root)
    assert (r.code, r.out) == (0, f"q/{TODAY}-t\n")
    assert item_yaml(q, f"{TODAY}-t") == {"title": "T", "stage": "inbox",
                                          "priority": "high"}
    assert "uncommitted" in r.err and "item.yaml" in r.err
    assert git(q, "rev-parse", "HEAD") == head


def test_new_with_project_takes_only_priority(tcw, pq):
    root, q = pq
    r = tcw(["new", "T", "--project", "q", "--tag", "ui"], root)
    assert r.code == 2 and "--tag" in r.err
    assert sorted(os.listdir(q / "docs/work")) == [".gitkeep"]


def test_new_into_an_undeclared_project(tcw, pq):
    root, _ = pq
    assert tcw(["new", "T", "--project", "nobody"], root).code == 3


def test_edit_blocks_into_another_project(tcw, pq):
    root, q = pq
    write_item(q, "2026-10-01-x", {"title": "x", "stage": "spec"})
    commit_all(q)
    write_item(root, "2026-10-01-a", {"title": "a", "stage": "spec"})
    r = tcw(["edit", "2026-10-01-a", "--blocks", "q/2026-10-01-x"], root)
    assert (r.code, r.out) == (0, ""), r.err
    assert item_yaml(q, "2026-10-01-x")["blocked-by"] == ["p/2026-10-01-a"]
    assert sorted(os.listdir(q / "docs/work")) == [".gitkeep", "2026-10-01-x"]


def test_any_other_write_into_another_project_is_refused(tcw, pq):
    root, q = pq
    write_item(q, "2026-10-01-x", {"title": "x", "stage": "spec"})
    assert tcw(["edit", "q/2026-10-01-x", "--priority", "high"], root).code == 3
    assert tcw(["comment", "q/2026-10-01-x"], root, stdin="hi").code == 3
    assert tcw(["advance", "q/2026-10-01-x"], root).code == 3
    assert tcw(["show", "q/2026-10-01-x"], root).code == 0


def test_show_of_an_absent_or_undeclared_project(tcw, pq):
    root, q = pq
    shutil.rmtree(q)
    assert tcw(["show", "q/2026-10-01-x"], root).code == 5
    assert tcw(["show", "nobody/2026-10-01-x"], root).code == 4


def test_jira_block_delegation_and_blocks(tcw, pq):
    root, q = pq
    shutil.rmtree(q)
    doc = yaml.safe_load((root / "tcw-config.yaml").read_text())
    doc["connected-projects"]["children"]["q"] = {"path": "../q", "jira": {"site": "x"}}
    (root / "tcw-config.yaml").write_text(yaml.safe_dump(doc))
    r = tcw(["new", "T", "--project", "q"], root)
    assert r.code == 1 and "Jira delegation arrives with the Jira backend" in r.err
    write_item(root, "2026-10-01-a", {"title": "a", "stage": "spec"})
    assert tcw(["edit", "2026-10-01-a", "--blocks", "q/2026-10-01-x"], root).code == 3


# -- AC 11: streams and exits ------------------------------------------------------------------

def test_streams_and_exits(tcw, p):
    write_item(p, "2026-10-01-a", {"title": "a", "stage": "review"})
    r = tcw(["path", "2026-10-01-a", "review", "--next"], p)
    assert r.err == "" and r.out.strip().endswith("review/round-1.md")
    assert os.path.isabs(r.out.strip())
    r = tcw(["path", "2026-10-01-a", "spec", "--handoff"], p)
    assert "/2026-10-01-a/spec/" in r.out
    assert not (p / "docs/work/2026-10-01-a/spec").exists()
    assert tcw(["path", "2026-10-01-a", "spec", "--next", "--handoff"], p).code == 2
    assert tcw(["show", "2026-10-01-nothing"], p).code == 4
    r = tcw(["path"], p)
    assert r.out.strip() == str((p / "docs/work").resolve())


def test_dry_run(tcw, p):
    folder = write_item(p, "2026-10-01-a", {"title": "a", "stage": "request"})
    before = sorted(str(x) for x in folder.rglob("*"))
    r = tcw(["advance", "2026-10-01-a", "--to", "plan", "--dry-run"], p)
    assert (r.code, r.out) == (3, "")
    r = tcw(["advance", "2026-10-01-a", "--dry-run"], p)
    assert (r.code, r.out) == (0, "spec\n")
    assert item_yaml(p, "2026-10-01-a")["stage"] == "request"
    assert sorted(str(x) for x in folder.rglob("*")) == before


def test_a_refused_advance_prints_nothing(tcw, p):
    write_item(p, "2026-10-01-a", {"title": "a", "stage": "request"})
    r = tcw(["advance", "2026-10-01-a", "--to", "plan"], p)
    assert (r.code, r.out) == (3, "")


def test_discard_prints_the_stage(tcw, p):
    write_item(p, "2026-10-01-a", {"title": "a", "stage": "spec"})
    r = tcw(["discard", "2026-10-01-a", "--reason", "not needed"], p)
    assert (r.code, r.out) == (0, "discarded\n"), r.err
