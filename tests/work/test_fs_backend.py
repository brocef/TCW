"""What only the filesystem backend shows: the files it writes and reads
(TCW-70 Design 3-5; the backend half of AC 2-4 and 6-8)."""

import os
from datetime import date, datetime, timezone

import pytest
import yaml

from tcw.errors import BackendError, MovedWithoutNote, Refused, UsageError
from tcw.work import fs_backend
from tcw.work.backend import Query
from tcw.work.config import MIGRATION_GUIDE, parse_work_config
from tcw.work.fs_backend import FsWorkBackend, read_all, work_store_problems
from tcw.work.model import Changes, Slug

TODAY = date(2026, 10, 2)


class Clock:
    def __init__(self):
        self.at = datetime(2026, 10, 2, 12, 0, 0, tzinfo=timezone.utc)

    def __call__(self):
        return self.at


def config(**work):
    work.setdefault("tags", ["bug", "ui", "old"])
    parsed, problems = parse_work_config(work)
    assert problems == []
    return parsed


@pytest.fixture
def work(tmp_path):
    return tmp_path / "work"


def backend_for(work, cfg=None, report=None, clock=None):
    return FsWorkBackend("tcw", work, cfg or config(),
                         report=report if report is not None else (lambda l: None),
                         today=lambda: TODAY, now=clock or Clock())


@pytest.fixture
def backend(work):
    return backend_for(work)


def new(backend, title, request=None, stage="request", **props):
    return backend.create(title, Changes(**props), stage=stage, request=request)


def item_yaml(work, folder):
    return (work / folder / "item.yaml").read_text()


def write_item(work, folder, data):
    (work / folder).mkdir(parents=True, exist_ok=True)
    text = data if isinstance(data, str) else yaml.safe_dump(data, sort_keys=False)
    (work / folder / "item.yaml").write_text(text)


# -- AC 2: create ---------------------------------------------------------------

def test_create_writes_exactly_title_stage_priority(backend, work):
    item = new(backend, "Add a widget")
    assert item.slug == Slug("tcw", "2026-10-02-add-a-widget")
    assert item_yaml(work, item.slug.folder) == (
        "title: Add a widget\nstage: request\npriority: medium\n")
    assert sorted(p.name for p in (work / item.slug.folder).iterdir()) == ["item.yaml"]


def test_a_second_create_the_same_day_is_refused(backend, work):
    new(backend, "Add a widget")
    with pytest.raises(Refused, match="2026-10-02-add-a-widget"):
        new(backend, "Add a widget")
    assert sorted(p.name for p in work.iterdir()) == ["2026-10-02-add-a-widget"]


def test_a_title_with_no_words_is_untitled(backend):
    assert new(backend, "!!!").slug.folder == "2026-10-02-untitled"


def test_properties_are_written_in_order(backend, work):
    parent = new(backend, "parent")
    item = new(backend, "child", priority="high", effort="low",
               complexity="very-high", add_tags=("ui",), assignee="sam",
               parent=parent.slug.folder, add_blocked_by=("other/x",))
    assert item_yaml(work, item.slug.folder) == (
        "title: child\nstage: request\npriority: high\neffort: low\n"
        "complexity: very-high\ntags:\n- ui\nassignee: sam\n"
        f"parent: tcw/{parent.slug.folder}\nblocked-by:\n- other/x\n")


def test_create_validates_its_properties(backend, work):
    with pytest.raises(UsageError):
        new(backend, "x", add_tags=("nosuch",))
    assert not work.exists() or list(work.iterdir()) == []


# -- AC 3: the request -------------------------------------------------------------

def test_the_request_is_written_verbatim(backend, work):
    item = new(backend, "X", request="line one\n")
    path = work / item.slug.folder / "request" / "request.md"
    assert path.read_text() == "line one\n"
    assert backend.read_request(item.slug.folder) == "line one\n"


def test_an_inbox_item_keeps_its_text_in_the_same_place(backend, work):
    item = new(backend, "Y", request="line one\n", stage="inbox")
    assert "stage: inbox\n" in item_yaml(work, item.slug.folder)
    assert (work / item.slug.folder / "request" / "request.md").read_text() == "line one\n"
    assert not list(work.rglob("intake.md"))


def test_an_empty_request_writes_nothing(backend, work):
    item = new(backend, "Z", request="")
    assert not (work / item.slug.folder / "request").exists()
    assert backend.read_request(item.slug.folder) is None


def test_a_failed_create_removes_its_folder(backend, work, monkeypatch):
    real = fs_backend._replace_file

    def fail_on_the_request(path, text):
        if path.name == "request.md":
            raise OSError("disk full")
        real(path, text)

    monkeypatch.setattr(fs_backend, "_replace_file", fail_on_the_request)
    with pytest.raises(OSError):
        new(backend, "X", request="text")
    assert list(work.iterdir()) == []


# -- AC 4: reading -----------------------------------------------------------------

@pytest.mark.parametrize("text, key", [
    ("title: t\nstage: request\ncreated: 2026-01-01\n", "created"),
    ("stage: request\n", "title"),
    ("title: t\nstage: request\npriority: 3\n", "priority"),
    ("title: t\nstage: [request\n", None),
    ("- a list\n", None),
    ("title: t\nstage: request\ntags: ui\n", "tags"),
    ("title: t\nstage: request\nparent: a/b/c\n", "parent"),
    ("title: t\nstage: request\neffort: huge\n", "effort"),
])
def test_strict_reading(backend, work, text, key):
    write_item(work, "2026-10-01-x", text)
    with pytest.raises(BackendError) as error:
        backend.read("2026-10-01-x")
    assert "item.yaml" in str(error.value)
    if key:
        assert key in str(error.value)


@pytest.mark.parametrize("stage", ["verify", "postmortem", "plan"])
def test_a_stage_that_is_not_enabled_reads_as_no_stage(work, stage):
    backend = backend_for(work, config(stages={"plan": {"enabled": False}}))
    write_item(work, "2026-10-01-x", {"title": "t", "stage": stage})
    assert backend.read("2026-10-01-x").stage is None


def test_an_absent_priority_reads_as_medium(backend, work):
    write_item(work, "2026-10-01-x", {"title": "t", "stage": "spec"})
    assert backend.read("2026-10-01-x").priority == "medium"


def test_a_bare_reference_reads_as_this_project(backend, work):
    write_item(work, "2026-10-01-x", {"title": "t", "stage": "spec",
                                      "parent": "2026-10-01-p",
                                      "blocked-by": ["2026-10-01-q", "o/r"]})
    item = backend.read("2026-10-01-x")
    assert item.parent == Slug("tcw", "2026-10-01-p")
    assert item.blocked_by == (Slug("tcw", "2026-10-01-q"), Slug("o", "r"))


def test_an_edit_keeps_a_stage_that_reads_as_none(backend, work):
    write_item(work, "2026-10-01-x", {"title": "t", "stage": "verify"})
    backend.update("2026-10-01-x", Changes(priority="high"))
    data = yaml.safe_load(item_yaml(work, "2026-10-01-x"))
    assert data["stage"] == "verify" and data["priority"] == "high"


def test_a_tag_removed_from_the_registry_is_kept_and_can_be_removed(work):
    write_item(work, "2026-10-01-x", {"title": "t", "stage": "spec",
                                      "tags": ["gone"]})
    backend = backend_for(work)
    assert backend.read("2026-10-01-x").tags == ("gone",)
    assert backend.update("2026-10-01-x", Changes(priority="high")).tags == ("gone",)
    assert backend.update("2026-10-01-x", Changes(remove_tags=("gone",))).tags == ()
    with pytest.raises(UsageError):
        backend.update("2026-10-01-x", Changes(add_tags=("nosuch",)))


# -- listing -------------------------------------------------------------------------

def test_list_skips_what_is_not_an_item(backend, work):
    item = new(backend, "x")
    (work / "notes").mkdir()
    (work / "README.md").write_text("hi")
    (work / "2026-13-01-bad-date").mkdir()
    (work / "2026-10-01-no-item-yaml").mkdir()
    assert [i.slug for i in backend.list(Query())] == [item.slug]


def test_one_unreadable_item_fails_list_and_read_all_returns_the_rest(backend, work):
    good = new(backend, "good")
    write_item(work, "2026-10-01-bad", "title: [x\n")
    with pytest.raises(BackendError, match="2026-10-01-bad"):
        backend.list(Query())
    items, bad = read_all(work, "tcw", backend.enabled)
    assert [i.slug for i in items] == [good.slug]
    assert [b.path.parent.name for b in bad] == ["2026-10-01-bad"]


def test_list_is_in_folder_name_order(backend, work):
    write_item(work, "2026-09-01-b", {"title": "b", "stage": "spec"})
    write_item(work, "2026-09-01-a", {"title": "a", "stage": "spec"})
    write_item(work, "2026-08-01-z", {"title": "z", "stage": "spec"})
    assert [i.slug.folder for i in backend.list(Query())] == [
        "2026-08-01-z", "2026-09-01-a", "2026-09-01-b"]


# -- atomic writes ---------------------------------------------------------------------

def test_a_failed_replace_leaves_the_old_file(backend, work, monkeypatch):
    item = new(backend, "x")
    before = item_yaml(work, item.slug.folder)

    def boom(src, dst):
        raise OSError("interrupted")

    monkeypatch.setattr(os, "replace", boom)
    with pytest.raises(OSError):
        backend.update(item.slug.folder, Changes(priority="high"))
    assert item_yaml(work, item.slug.folder) == before
    assert sorted(p.name for p in (work / item.slug.folder).iterdir()) == ["item.yaml"]


# -- AC 6: comments ----------------------------------------------------------------------

def test_a_comment_is_a_timestamped_file(backend, work):
    folder = new(backend, "x").slug.folder
    backend.comment(folder, "hi\n")
    [path] = (work / folder / "comments").iterdir()
    assert path.name == "20261002T120000Z.md" and path.read_text() == "hi\n"


def test_two_comments_in_one_second_do_not_overwrite(backend, work):
    folder = new(backend, "x").slug.folder
    backend.comment(folder, "first")
    backend.comment(folder, "second")
    files = sorted((work / folder / "comments").iterdir())
    assert [p.name for p in files] == ["20261002T120000Z.md", "20261002T120001Z.md"]
    assert files[0].read_text() == "first"


def test_an_empty_comment_is_a_usage_error(backend):
    with pytest.raises(UsageError):
        backend.comment(new(backend, "x").slug.folder, "  \n")


def test_read_comments(work):
    clock = Clock()
    backend = backend_for(work, clock=clock)
    folder = new(backend, "x").slug.folder
    for second, text in enumerate(("one", "two", "three")):
        clock.at = clock.at.replace(second=second)
        backend.comment(folder, text)
    (work / folder / "comments" / "notes.txt").write_text("not a comment")
    newest = backend.read_comments(folder, 2)
    assert [(c.text, c.at.second, c.author) for c in newest] == [
        ("three", 2, None), ("two", 1, None)]


def test_a_comment_that_is_not_utf8_is_an_error(backend, work):
    folder = new(backend, "x").slug.folder
    (work / folder / "comments").mkdir()
    (work / folder / "comments" / "20261002T120000Z.md").write_bytes(b"\xff\xfe")
    with pytest.raises(BackendError, match="20261002T120000Z"):
        backend.read_comments(folder)


# -- AC 7: the trace -----------------------------------------------------------------------

def test_a_note_that_cannot_be_written_leaves_the_move(backend, work):
    folder = new(backend, "x").slug.folder
    (work / folder / "comments").write_text("in the way")
    with pytest.raises(MovedWithoutNote):
        backend.set_stage(folder, "plan", "skip")
    assert yaml.safe_load(item_yaml(work, folder))["stage"] == "plan"


# -- AC 8: rename ---------------------------------------------------------------------------

def test_rename_rewrites_references_and_reports_mentions(work):
    lines = []
    backend = backend_for(work, report=lines.append)
    a = new(backend, "A")
    write_item(work, "2026-10-01-b", {"title": "b", "stage": "verify",
                                      "parent": f"tcw/{a.slug.folder}"})
    write_item(work, "2026-10-01-c", {"title": "c", "stage": "spec",
                                      "blocked-by": [a.slug.folder]})
    spec = work / a.slug.folder / "spec" / "spec.md"
    spec.parent.mkdir()
    spec.write_text(f"intro\nsee {a.slug.folder}\n")

    renamed = backend.rename(a.slug.folder, "new-words")
    assert renamed.slug.folder == "2026-10-02-new-words"
    b = yaml.safe_load(item_yaml(work, "2026-10-01-b"))
    c = yaml.safe_load(item_yaml(work, "2026-10-01-c"))
    assert b == {"title": "b", "stage": "verify", "priority": "medium",
                 "parent": "tcw/2026-10-02-new-words"}
    assert c["blocked-by"] == ["tcw/2026-10-02-new-words"]
    new_spec = work / "2026-10-02-new-words" / "spec" / "spec.md"
    assert any(line.startswith(f"{new_spec}:2:") and "not rewritten" in line
               for line in lines)
    assert not list(work.rglob("renames.yaml"))


def test_rename_takes_a_full_name_with_the_same_date(backend):
    item = new(backend, "A")
    assert backend.rename(item.slug.folder, "2026-10-02-b").slug.folder == "2026-10-02-b"


@pytest.mark.parametrize("name", ["New Words", "2026-01-01-other", "a_b"])
def test_rename_refuses_a_name_that_is_not_folder_shaped(backend, name):
    with pytest.raises(UsageError):
        backend.rename(new(backend, "A").slug.folder, name)


def test_rename_to_an_existing_name_is_refused(backend):
    a = new(backend, "A")
    new(backend, "B")
    with pytest.raises(Refused):
        backend.rename(a.slug.folder, "b")


def test_rename_refuses_with_an_unreadable_item_and_moves_nothing(backend, work):
    a = new(backend, "A")
    write_item(work, "2026-10-01-bad", "title: [x\n")
    with pytest.raises(BackendError, match="2026-10-01-bad"):
        backend.rename(a.slug.folder, "new-words")
    assert (work / a.slug.folder).is_dir()


# -- the validate checks ----------------------------------------------------------------------

def test_work_store_problems(work):
    cfg = config()
    backend = backend_for(work, cfg)
    new(backend, "fine", add_tags=("ui",))
    write_item(work, "2026-10-01-bad", "title: t\nstage: request\ncreated: x\n")
    write_item(work, "2026-10-01-lost", {"title": "t", "stage": "verify"})
    write_item(work, "2026-10-01-tagged", {"title": "t", "stage": "spec",
                                           "tags": ["gone"]})
    (work / "inbox").mkdir()
    (work / "dod.yaml").write_text("- tests pass\n")
    (work / ".gitkeep").write_text("")

    found = {(f.severity, os.path.basename(os.path.dirname(f.where))
              if f.where.endswith("item.yaml") else os.path.basename(f.where)):
             f.message for f in work_store_problems(work, "tcw", cfg)}
    assert set(found) == {("error", "2026-10-01-bad"), ("error", "2026-10-01-lost"),
                          ("warning", "2026-10-01-tagged"), ("error", "inbox"),
                          ("warning", "dod.yaml")}
    assert "created" in found[("error", "2026-10-01-bad")]
    assert "'verify'" in found[("error", "2026-10-01-lost")]
    assert MIGRATION_GUIDE in found[("error", "inbox")]
    assert MIGRATION_GUIDE in found[("warning", "dod.yaml")]
    assert "gone" in found[("warning", "2026-10-01-tagged")]


def test_every_file_written_is_reported(work):
    lines = []
    backend = backend_for(work, report=lines.append)
    item = new(backend, "x", request="text")
    backend.comment(item.slug.folder, "hi")
    assert any("item.yaml" in l for l in lines)
    assert any("request.md" in l for l in lines)
    assert any("comments" in l for l in lines)
