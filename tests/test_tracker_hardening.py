"""Tracker commands refuse what they cannot read, and the Jira client refuses a
response of the wrong shape, instead of passing silently or printing a
traceback (spec: 2026-09-15-harden-tracker-binding-reads-and-writes-and-jira-response-parsing)."""

from __future__ import annotations

import json
import subprocess

import pytest

from tcw.store.fs import FsWorkStore
from tcw.work.jira import client as jira
from tcw.work.jira.client import TrackerError
from tests.work.jira.test_client import CONFIG, Recorder, _client, _credentials  # noqa: F401
from test_tracker_strict import REFUSED, strict  # noqa: F401
from test_tracker_sync import (KEY, STATUSES, TICKET_ID, cli, fake,  # noqa: F401
                               make_node)


# ── criterion 1: a tracker.yaml that is not a regular file ──────────────────

def folder_binding(root, title="Odd item") -> str:
    st = FsWorkStore.open(root)
    slug = st.create(title).slug
    (st.path(slug) / "tracker.yaml").mkdir()
    return slug


@pytest.fixture()
def node(tmp_path, fake):  # noqa: F811
    return make_node(tmp_path, statuses=STATUSES)


@pytest.mark.parametrize("argv", [
    ("link", KEY), ("unlink", "--reason", "x"), ("sync",),
], ids=["link", "unlink", "sync"])
def test_a_folder_named_tracker_yaml_is_unreadable_to_every_command(node, argv):
    slug = folder_binding(node)
    verb, *rest = argv
    code, _out, err = cli(node, "work", "tracker", verb, slug, *rest)
    assert code == 1, err
    assert "Traceback" not in err and "not a readable text file" in err, err
    assert (FsWorkStore.open(node).path(slug) / "tracker.yaml").is_dir()


def test_strict_drop_refuses_an_item_whose_binding_cannot_be_read(strict):  # noqa: F811
    slug = folder_binding(strict)
    code, _out, err = cli(strict, "work", "drop", slug, "--confirm")
    assert code == 1 and REFUSED in err, err
    assert FsWorkStore.open(strict).get(slug) is not None


def test_read_sidecar_raises_for_a_name_that_is_not_a_regular_file(node):
    slug = folder_binding(node)
    with pytest.raises(OSError, match="not a regular file"):
        FsWorkStore.open(node).read_sidecar(slug, "tracker.yaml")
    other = FsWorkStore.open(node).create("Plain").slug
    assert FsWorkStore.open(node).read_sidecar(other, "tracker.yaml") is None


# ── criterion 3: link refuses an item waiting for deletion ──────────────────

def test_link_refuses_an_item_waiting_for_deletion(tmp_path, fake):  # noqa: F811
    root = make_node(tmp_path, statuses=STATUSES, retain={"completed": False})
    st = FsWorkStore.open(root)
    slug = st.create("Done item").slug
    st.start(slug)
    st.complete(slug, "done", ["acked"])
    assert st.pending_deletion(slug)
    before = len(fake.requests)
    code, _out, err = cli(root, "work", "tracker", "link", slug, KEY)
    assert code == 1 and "waiting for deletion" in err, err
    assert len(fake.requests) == before
    assert not (st.path(slug) / "tracker.yaml").exists()


# ── criterion 4: a merge-back refused by any staged file names it ────────────

def test_a_merge_back_blocked_by_another_items_staged_file_names_it(tmp_path, fake):  # noqa: F811
    root = make_node(tmp_path, statuses=None, tracker=False)
    st = FsWorkStore.open(root)
    slug = st.create("Worked").slug
    other = st.create("Other").slug
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(root), "commit", "-qm", "items"], check=True)
    assert cli(root, "work", "start", slug, "--worktree")[0] == 0
    tree = root / ".worktrees" / slug
    (tree / "docs" / "work" / "active" / slug / "outcome.md").write_text("done\n")
    (tree / "docs" / "work" / "backlog" / other / "notes.md").write_text("theirs\n")
    subprocess.run(["git", "-C", str(tree), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(tree), "commit", "-qm", "work"], check=True)
    staged = root / "docs" / "work" / "backlog" / other / "notes.md"
    staged.write_text("mine\n")
    subprocess.run(["git", "-C", str(root), "add", str(staged)], check=True)
    code, _out, err = cli(root, "work", "complete", slug, "--resolution", "done",
                          "--confirm", "--force")
    assert code == 1, err
    assert f"docs/work/backlog/{other}/notes.md" in err and "staged" in err, err


def test_the_web_sidecar_route_names_a_folder_it_cannot_read(node):
    import threading
    from urllib.error import HTTPError
    from urllib.request import urlopen

    from tcw.serve import TcwServer
    slug = folder_binding(node)
    httpd = TcwServer(("127.0.0.1", 0), node)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    try:
        with pytest.raises(HTTPError) as got:
            urlopen(f"http://127.0.0.1:{httpd.server_port}/api/work/{slug}/sidecars/tracker.yaml")
        assert got.value.code == 400 and b"not a regular file" in got.value.read()
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_a_dangling_link_at_the_sidecar_name_is_not_absence(node):
    st = FsWorkStore.open(node)
    slug = st.create("Linked").slug
    (st.path(slug) / "tracker.yaml").symlink_to("nowhere.yaml")
    with pytest.raises(OSError, match="not a regular file"):
        st.read_sidecar(slug, "tracker.yaml")
