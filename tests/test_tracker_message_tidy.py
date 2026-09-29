"""Tracker messages say what happened, and no response value crashes a command
(spec: 2026-09-26-tidy-three-tracker-messages-left-by-the-binding-hardening-review)."""

from __future__ import annotations

import json
import subprocess

import pytest

from tcw.store.fs import FsWorkStore
from test_tracker_cli import (ON_NEW_TRACKER, OK_RESPONSES, _create_responses,
                              _created_node, _responses, _run, node)  # noqa: F401
from test_tracker_strict import strict  # noqa: F401
from test_tracker_sync import cli, fake  # noqa: F401


# ── criterion 1: staged paths are real paths ─────────────────────────────────

def test_staged_paths_are_unquoted_and_from_the_top(tmp_path):
    from tcw.work.cli import _staged_paths
    top = tmp_path / "repo"
    (top / "nöde" / "sub").mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(top)], check=True)
    subprocess.run(["git", "-C", str(top), "config", "diff.relative", "true"], check=True)
    (top / "nöde" / "sub" / "tracker.yaml").write_text("x: 1\n")
    subprocess.run(["git", "-C", str(top), "add", "-A"], check=True)
    assert _staged_paths(top) == ["nöde/sub/tracker.yaml"]


def test_a_nested_item_under_a_non_ascii_path_is_found(tmp_path):
    """`ls-tree` quotes the same way; `_nested_in_commit` compared its lines
    with real paths and so found no child in a store at a path like this."""
    from pathlib import Path

    from tcw.store.fs import init
    top = root = tmp_path / "repo"
    root.mkdir()
    for args in (["init", "-q"], ["config", "user.email", "t@t"], ["config", "user.name", "t"]):
        subprocess.run(["git", "-C", str(top), *args], check=True)
    init(["work"], root, "n", Path("wörk"))
    st = FsWorkStore.open(root)
    parent = st.create("Parent", created="2026-01-01").slug
    child = st.create("Child", created="2026-01-01").slug
    st.path(child).rename(st.path(parent) / child)       # as earlier versions nested
    subprocess.run(["git", "-C", str(top), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(top), "commit", "-qm", "c"], check=True)
    folder = st.path(parent).relative_to(st.store_git_root)
    assert [found[0] for found in st._nested_in_commit(folder)] == [child]


# ── criterion 2: a create answer of any shape warns the ticket may exist ────

@pytest.mark.parametrize("answer", [[], "ok", {"key": None, "id": None}],
                         ids=["list", "string", "nulls"])
def test_an_odd_create_answer_says_the_ticket_may_exist(node, monkeypatch, answer):
    _root, slug = _created_node(node, monkeypatch, status="backlog")
    _create_responses(monkeypatch, __create__=(200, {}, json.dumps(answer).encode()))
    code, _out, err = _run(["work", "tracker", "create", slug])
    assert code == 1
    assert "It may exist; look for a ticket titled" in err, err


# ── criterion 3: a failed binding after creation gives a real reason ─────────

def test_filing_says_why_the_binding_did_not_follow(node, monkeypatch):
    root, configure = node
    configure(ON_NEW_TRACKER)
    _create_responses(monkeypatch)
    real = FsWorkStore.write_sidecar

    def refuse_the_binding(self, slug_, name, content, *a, **kw):
        if "ticket:" in content:
            raise OSError("disk is full")
        return real(self, slug_, name, content, *a, **kw)

    monkeypatch.setattr(FsWorkStore, "write_sidecar", refuse_the_binding)
    code, _out, err = _run(["work", "new", "Filed"])
    assert code == 0, err
    assert "binding did not follow" in err, err
    assert "creating it did not succeed" not in err, err


# ── criterion 4: a value of the wrong type is a shape error ──────────────────

def test_a_status_name_that_is_not_text_is_reported_not_crashed(node, monkeypatch):
    _root, configure = node
    configure()
    issue = {"key": "A-1", "fields": {"status": {"name": 5}}}
    _responses(monkeypatch, {**OK_RESPONSES, "/issue/": (200, {}, json.dumps(issue).encode())})
    code, _out, err = _run(["work", "tracker", "show", "A-1"])
    assert code == 1
    assert "unexpected shape" in err and "Traceback" not in err, err


# ── criterion 5: strict drop of an unreadable binding says so ────────────────

def test_strict_drop_of_an_unreadable_binding_says_it_cannot_be_read(strict):  # noqa: F811
    st = FsWorkStore.open(strict)
    slug = st.create("Damaged").slug
    (st.path(slug) / "tracker.yaml").write_bytes(b"ticket: \xff\n")
    code, _out, err = cli(strict, "work", "drop", slug, "--confirm")
    assert code == 1
    assert "cannot be read" in err and "is, or was, bound" not in err, err
    assert FsWorkStore.open(strict).get(slug) is not None
    from tcw.serve import _strict_refuses
    web = _strict_refuses(FsWorkStore.open(strict), "drop", slug)
    assert "cannot be read" in web and "is, or was, bound" not in web, web
