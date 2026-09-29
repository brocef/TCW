"""A blocker naming an item of this very node — qualified with the node's own
project id, or as `<status>/<slug>` — is recorded as that local item (spec:
2026-09-27-refuse-a-blocker-that-names-its-own-item-by-qualified-ref-and-settle-status-path-blockers)."""

import subprocess
from pathlib import Path

import pytest

from tcw.cli import main
from tcw.store.fs import FsWorkStore, init


@pytest.fixture
def pa(tmp_path, monkeypatch, capsys):
    root = tmp_path / "pa"
    root.mkdir()
    for args in (["init", "-q"], ["config", "user.email", "t@t"], ["config", "user.name", "t"]):
        subprocess.run(["git", "-C", str(root), *args], check=True)
    init(["work"], root, "pa")
    st = FsWorkStore.open(root)
    alpha = st.create("Alpha", created="2026-01-01").slug
    beta = st.create("Beta", created="2026-01-01").slug
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(root), "commit", "-qm", "items"], check=True)
    monkeypatch.chdir(root)
    capsys.readouterr()
    return root, alpha, beta


def edit(capsys, slug, *args):
    code = main(["work", "edit", slug, *args])
    return code, capsys.readouterr().err


def blocked_by(root, slug):
    return FsWorkStore.open(root).get(slug).blocked_by


def test_an_own_qualified_self_reference_is_refused(pa, capsys):
    root, alpha, _beta = pa
    code, err = edit(capsys, alpha, "--blocked-by", f"pa/{alpha}")
    assert code == 1 and "an item cannot block itself" in err, err
    assert blocked_by(root, alpha) == []


def test_an_own_qualified_reference_is_the_local_item(pa, capsys):
    root, alpha, beta = pa
    assert edit(capsys, beta, "--blocked-by", f"pa/{alpha}")[0] == 0
    assert blocked_by(root, beta) == [{"slug": alpha}]


@pytest.mark.parametrize("status", ["backlog", "completed"])
def test_a_status_path_is_the_local_item(pa, capsys, status):
    root, alpha, beta = pa
    if status == "completed":
        st = FsWorkStore.open(root)
        st.start(alpha, owner="me")
        st.complete(alpha, "done", [], force=True)
    assert edit(capsys, beta, "--blocked-by", f"{status}/{alpha}")[0] == 0
    assert blocked_by(root, beta) == [{"slug": alpha}]


def test_a_cycle_through_an_own_qualified_reference_is_refused(pa, capsys):
    root, alpha, beta = pa
    assert edit(capsys, alpha, "--blocked-by", beta)[0] == 0
    code, err = edit(capsys, beta, "--blocked-by", f"pa/{alpha}")
    assert code == 1 and "cycle" in err, err
    assert blocked_by(root, beta) == []


@pytest.mark.parametrize("text", ["vendor/legal-review", "other-node/x"])
def test_other_qualified_text_stays_external(pa, capsys, text):
    root, _alpha, beta = pa
    assert edit(capsys, beta, "--blocked-by", text)[0] == 0
    assert blocked_by(root, beta) == [{"external": text}]


def test_a_stale_status_path_still_names_the_local_item(pa, capsys):
    """The slug is the identity; a status that has moved on since the path was
    copied does not turn the reference into text."""
    root, alpha, beta = pa
    assert edit(capsys, beta, "--blocked-by", f"active/{alpha}")[0] == 0
    assert blocked_by(root, beta) == [{"slug": alpha}]


def test_another_qualifier_naming_a_local_slug_stays_external(pa, capsys):
    root, alpha, beta = pa
    assert edit(capsys, beta, "--blocked-by", f"vendor/{alpha}")[0] == 0
    assert blocked_by(root, beta) == [{"external": f"vendor/{alpha}"}]
