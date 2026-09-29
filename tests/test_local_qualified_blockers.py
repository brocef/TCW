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


# ── review fold-in ───────────────────────────────────────────────────────────

@pytest.mark.parametrize("form", ["pa/{}", "backlog/{}", "external: pa/{}"])
def test_the_text_that_added_a_blocker_removes_it(pa, capsys, form):
    root, alpha, beta = pa
    assert edit(capsys, beta, "--blocked-by", f"pa/{alpha}")[0] == 0
    code, err = edit(capsys, beta, "--unblocked-by", form.format(alpha))
    assert code == 0, err
    assert blocked_by(root, beta) == []


@pytest.mark.parametrize("old", ["pa/{}", "backlog/{}"])
def test_re_adding_an_item_stored_as_text_replaces_the_text(pa, capsys, old):
    """Stored before this change read it as the local item; `backlog/<slug>`
    as text blocked forever, so keeping it beside the slug kept the bug."""
    root, alpha, beta = pa
    st = FsWorkStore.open(root)
    st.set_field(beta, "blocked_by", [{"external": old.format(alpha)}])
    assert edit(capsys, beta, "--blocked-by", f"pa/{alpha}")[0] == 0
    assert blocked_by(root, beta) == [{"slug": alpha}]


def test_a_folder_path_under_a_status_stays_text(pa, capsys):
    root, alpha, beta = pa
    assert edit(capsys, beta, "--blocked-by", f"backlog/zzz/{alpha}")[0] == 0
    assert blocked_by(root, beta) == [{"external": f"backlog/zzz/{alpha}"}]


def test_a_registered_siblings_item_with_a_local_slug_stays_external(tmp_path):
    """`pb/<slug>` resolves — to pb's item. That this node holds an item with
    the same slug must not make it this node's."""
    from test_cross_node_blockers import node
    root = node(tmp_path / "root", "root", children={"pa": "pa", "pb": "pb"})
    node(root / "pa", "pa", parent="root")
    node(root / "pb", "pb", parent="root")
    a, b = FsWorkStore.open(root / "pa"), FsWorkStore.open(root / "pb")
    dep = a.create("Dep", created="2026-01-01").slug
    assert b.create("Dep", created="2026-01-01").slug == dep
    needs = a.create("Needs", created="2026-01-01").slug
    a.add_blocker(needs, f"pb/{dep}")
    assert a.get(needs).blocked_by == [{"external": f"pb/{dep}"}]
