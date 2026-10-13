"""Defects the first adversarial review of TCW-70 found, each pinned by a test
that failed before its fix."""

import io
import os
import stat
import sys
from datetime import date

import pytest
import yaml

from tcw.cli import main
from tcw.errors import Refused
from tcw.work.open import delegate
from tests.work.projects import commit_all, connect, git, make_project, write_item

TODAY = date.today().isoformat()


def run(monkeypatch, capsys, cwd, *argv, stdin=""):
    monkeypatch.chdir(cwd)
    monkeypatch.setattr(sys, "stdin", io.StringIO(stdin))
    try:
        code = main(list(argv))
    except SystemExit as stop:
        code = stop.code if isinstance(stop.code, int) else 1
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def item_yaml(root, folder):
    return yaml.safe_load((root / "docs" / "work" / folder / "item.yaml").read_text())


@pytest.fixture
def pq(tmp_path):
    p = make_project(tmp_path, "p")
    q = make_project(tmp_path, "q")
    connect(p, q, "children")
    connect(q, p, "parent")
    write_item(q, "2026-10-01-x", {"title": "x", "stage": "spec"})
    write_item(p, "2026-10-01-a", {"title": "a", "stage": "spec"})
    commit_all(p)
    commit_all(q)
    return p, q


# -- init deletes nothing but an empty store ------------------------------------------


@pytest.mark.parametrize("leftover", ["README.md", "notes/plan.md",
                                      "completed/2025-01-01-old/outcome.md",
                                      "Not-An-Item/item.yaml"])
def test_init_refuses_to_move_a_store_holding_anything(tmp_path, monkeypatch, capsys,
                                                       leftover):
    root = make_project(tmp_path, "p")
    path = root / "docs" / "work" / leftover
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("keep me")
    code, _, err = run(monkeypatch, capsys, root, "init", "work",
                       "--work-path", "elsewhere")
    assert code == 1, err
    assert path.read_text() == "keep me"
    assert not (root / "elsewhere").exists()


# -- a refused edit changes nothing ------------------------------------------------------


def test_a_refused_blocks_target_leaves_the_item_unchanged(pq, monkeypatch, capsys):
    p, q = pq
    (q / "docs" / "work" / "stray.md").write_text("x")
    code, out, _ = run(monkeypatch, capsys, p, "work", "edit", "2026-10-01-a",
                       "--priority", "high", "--blocks", "q/2026-10-01-x")
    assert (code, out) == (3, "")
    assert "priority" not in item_yaml(p, "2026-10-01-a")


@pytest.mark.parametrize("target", ["q/2026-10-01-nothing", "2026-10-01-nothing"])
def test_a_missing_blocks_target_leaves_the_item_unchanged(pq, monkeypatch, capsys,
                                                           target):
    p, _ = pq
    code, _, _ = run(monkeypatch, capsys, p, "work", "edit", "2026-10-01-a",
                     "--priority", "high", "--blocks", target)
    assert code == 4
    assert "priority" not in item_yaml(p, "2026-10-01-a")


def test_a_second_refused_target_leaves_the_first_unchanged(pq, monkeypatch, capsys):
    p, q = pq
    write_item(p, "2026-10-01-b", {"title": "b", "stage": "spec"})
    code, _, _ = run(monkeypatch, capsys, p, "work", "edit", "2026-10-01-a",
                     "--blocks", "2026-10-01-b", "--blocks", "q/2026-10-01-nothing")
    assert code == 4
    assert "blocked-by" not in item_yaml(p, "2026-10-01-b")


# -- files TCW writes are readable by others ---------------------------------------------


def test_item_files_take_the_usual_mode(tmp_path, monkeypatch, capsys):
    root = make_project(tmp_path, "p")
    old = os.umask(0o022)
    try:
        code, out, err = run(monkeypatch, capsys, root, "work", "new", "T",
                             stdin="request text\n")
    finally:
        os.umask(old)
    assert code == 0, err
    folder = root / "docs" / "work" / f"{TODAY}-t"
    for path in (folder / "item.yaml", folder / "request" / "request.md"):
        assert stat.S_IMODE(path.stat().st_mode) == 0o644, path


# -- a comment is written whole, or the move reports exit 6 ---------------------------------


def test_a_reason_that_cannot_be_written_is_a_usage_error(tmp_path, monkeypatch, capsys):
    root = make_project(tmp_path, "p")
    write_item(root, "2026-10-01-a", {"title": "a", "stage": "spec"})
    bad = "bad \udcff byte"           # what argv holds for an undecodable byte
    code, out, _ = run(monkeypatch, capsys, root, "work", "advance", "2026-10-01-a",
                       "--to", "implement", "--force", "--reason", bad)
    assert (code, out) == (2, "")
    assert item_yaml(root, "2026-10-01-a")["stage"] == "spec"
    assert not (root / "docs" / "work" / "2026-10-01-a" / "comments").exists()


@pytest.mark.parametrize("links", [True, False])
def test_a_failed_comment_write_leaves_no_file(tmp_path, monkeypatch, links):
    """The write fails partway, with and without hard links: the item has
    moved, the command says the trace is missing, and no comment file is
    left half-written."""
    import errno
    from tcw.errors import MovedWithoutNote
    from tcw.work import fs_backend
    from tcw.work.open import open_backend
    root = make_project(tmp_path, "p")
    write_item(root, "2026-10-01-a", {"title": "a", "stage": "spec"})
    backend = open_backend(root)
    real = fs_backend.os.fdopen

    class Failing:
        def __init__(self, handle):
            self.handle = handle

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            self.handle.close()

        def write(self, _text):
            raise OSError(errno.ENOSPC, "No space left on device")

    # With hard links the temporary file's write fails; without them that
    # write succeeds and the fallback's own write fails.
    opened = []

    def fdopen(*a, **k):
        opened.append(1)
        handle = real(*a, **k)
        return Failing(handle) if links or len(opened) > 1 else handle

    monkeypatch.setattr(fs_backend.os, "fdopen", fdopen)
    if not links:
        def refuse(*_a, **_k):
            raise OSError(errno.ENOTSUP, "ENOTSUP")
        monkeypatch.setattr(fs_backend.os, "link", refuse)
    with pytest.raises(MovedWithoutNote):
        backend.set_stage("2026-10-01-a", "plan", "why")
    comments = root / "docs" / "work" / "2026-10-01-a" / "comments"
    assert list(comments.iterdir()) == []


# -- delegation messages -------------------------------------------------------------------


def test_the_uncommitted_message_names_the_project_once(pq):
    p, q = pq
    (q / "docs" / "work" / "stray.md").write_text("x")
    with pytest.raises(Refused) as error:
        delegate("q", "T", None, None, here=p)
    message = str(error.value)
    assert message.startswith("the work store of 'q' has uncommitted changes")
    assert message.count("'q'") == 1


def test_delegation_names_the_repository_holding_the_store(tmp_path, monkeypatch,
                                                           capsys):
    p = make_project(tmp_path, "p")
    q = make_project(tmp_path, "q")
    store = tmp_path / "store"
    store.mkdir()
    git(store, "init", "-q")
    (store / "work").mkdir()
    (store / "work" / ".gitkeep").write_text("")
    git(store, "-c", "user.name=t", "-c", "user.email=t@t", "add", "-A")
    git(store, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "s")
    doc = yaml.safe_load((q / "tcw-config.yaml").read_text())
    doc.setdefault("work", {})["path"] = str(store / "work")
    (q / "tcw-config.yaml").write_text(yaml.safe_dump(doc))
    connect(p, q, "children")
    connect(q, p, "parent")
    commit_all(p)
    commit_all(q)
    code, _, err = run(monkeypatch, capsys, p, "work", "new", "T", "--project", "q")
    assert code == 0, err
    assert f"uncommitted in {store.resolve()}" in err


# -- flags -----------------------------------------------------------------------------------


@pytest.mark.parametrize("flag", ["--assignee", "--effort"])
def test_an_empty_property_with_project_is_a_usage_error(pq, monkeypatch, capsys, flag):
    p, q = pq
    code, _, err = run(monkeypatch, capsys, p, "work", "new", "T", "--project", "q",
                       flag, "")
    assert code == 2 and flag in err


@pytest.mark.parametrize("stage", ["bogus", "Request"])
def test_list_of_an_unknown_stage_is_a_usage_error(tmp_path, monkeypatch, capsys,
                                                    stage):
    root = make_project(tmp_path, "p")
    code, out, err = run(monkeypatch, capsys, root, "work", "list", "--stage", stage)
    assert (code, out) == (2, "") and stage in err


def test_tags_work_without_a_work_folder(tmp_path, monkeypatch, capsys):
    root = make_project(tmp_path, "p", config={"tags": ["ui"]})
    for child in (root / "docs" / "work").iterdir():
        child.unlink()
    (root / "docs" / "work").rmdir()
    assert run(monkeypatch, capsys, root, "work", "tags", "list")[:2] == (0, "ui\n")
    assert run(monkeypatch, capsys, root, "work", "tags", "add", "api")[0] == 0
    assert run(monkeypatch, capsys, root, "work", "tags", "rm", "api")[0] == 0


def test_new_with_its_own_project_is_a_usage_error(pq, monkeypatch, capsys):
    p, _ = pq
    code, out, err = run(monkeypatch, capsys, p, "work", "new", "T", "--project", "p")
    assert (code, out) == (2, "") and "--project" in err
    assert sorted(x.name for x in (p / "docs" / "work").iterdir()) == [
        ".gitkeep", "2026-10-01-a"]


def test_a_filesystem_error_is_a_message_not_a_traceback(tmp_path, monkeypatch, capsys):
    from tcw.work import fs_backend
    root = make_project(tmp_path, "p")

    def fail(*_a, **_k):
        raise PermissionError(13, "Permission denied", str(root))

    monkeypatch.setattr(fs_backend.os, "mkdir", fail)
    code, out, err = run(monkeypatch, capsys, root, "work", "new", "T")
    assert (code, out) == (1, "")
    assert "Permission denied" in err and "Traceback" not in err


# -- round three ------------------------------------------------------------------------------


@pytest.mark.parametrize("error", ["ENOTSUP", "EPERM", "EXDEV", "EMLINK"])
def test_comments_work_where_hard_links_do_not(tmp_path, monkeypatch, error):
    """FAT and exFAT volumes and SMB mounts refuse hard links."""
    import errno
    from tcw.work import fs_backend
    from tcw.work.open import open_backend
    root = make_project(tmp_path, "p")
    write_item(root, "2026-10-01-a", {"title": "a", "stage": "spec"})
    backend = open_backend(root)

    def refuse(*_a, **_k):
        raise OSError(getattr(errno, error), error)

    monkeypatch.setattr(fs_backend.os, "link", refuse)
    backend.comment("2026-10-01-a", "first")
    backend.comment("2026-10-01-a", "second")
    assert backend.set_stage("2026-10-01-a", "plan", "why") == "plan"
    comments = sorted((root / "docs/work/2026-10-01-a/comments").iterdir())
    assert [c.read_text() for c in comments] == ["first", "second", "why"]


@pytest.mark.parametrize("argv", [["new", "X \udcff"],
                                  ["edit", "2026-10-01-a", "--assignee", "z\udcff"],
                                  ["edit", "2026-10-01-a", "--title", "t\udcff"]])
def test_undecodable_text_is_a_usage_error(tmp_path, monkeypatch, capsys, argv):
    root = make_project(tmp_path, "p")
    write_item(root, "2026-10-01-a", {"title": "a", "stage": "spec"})
    before = sorted(p.name for p in (root / "docs" / "work").iterdir())
    text = (root / "docs/work/2026-10-01-a/item.yaml").read_text()
    code, out, _ = run(monkeypatch, capsys, root, "work", *argv)
    assert (code, out) == (2, "")
    assert sorted(p.name for p in (root / "docs" / "work").iterdir()) == before
    assert (root / "docs/work/2026-10-01-a/item.yaml").read_text() == text


def test_init_refuses_to_move_a_store_holding_a_hidden_file_with_content(
        tmp_path, monkeypatch, capsys):
    root = make_project(tmp_path, "p")
    notes = root / "docs" / "work" / ".notes"
    notes.write_text("my notes")
    code, _, _ = run(monkeypatch, capsys, root, "init", "work", "--work-path", "elsewhere")
    assert code == 1 and notes.read_text() == "my notes"


def test_init_moves_a_store_holding_only_empty_or_finder_files(tmp_path, monkeypatch,
                                                              capsys):
    root = make_project(tmp_path, "p")
    (root / "docs" / "work" / ".DS_Store").write_bytes(b"\0\0\0\1Bud1")
    code, _, err = run(monkeypatch, capsys, root, "init", "work", "--work-path", "elsewhere")
    assert code == 0, err
    assert not (root / "docs" / "work").exists()
