"""The graveyard: a record that a slug *was* a work item, after its documents go.

A resolved item's folder leaves the tracked tree (`.gitignore` ignores
`completed/` and `discarded/` by default), so in any clone but the one that ran
the transition, `get()` stops answering for it. Without a record that survives
into other clones, a reference to finished work is indistinguishable from a
typo — and `tcw validate`'s verdict depends on which machine runs it.

The record deliberately carries **no locator**. Where the documents went is a
promise that does not survive a squash-merge, a rebase, or a shallow clone, and
a pointer that silently stops working is worse than no pointer at all.
"""

import shutil
import subprocess
from datetime import date
from pathlib import Path

import pytest

from tcw.cli import main
from tcw.store.base import Tombstone
from tcw.store.fs import FsWorkStore, init


def node(tmp_path: Path, name: str = "repo") -> Path:
    root = tmp_path / name
    root.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "t"], check=True)
    init(["work"], root, name)
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(root), "commit", "-qm", "seed"], check=True)
    return root


def write_graveyard(root: Path, text: str) -> Path:
    st = FsWorkStore.open(root)
    p = st.root / "graveyard.yaml"
    p.write_text(text)
    return p


# ── reading ───────────────────────────────────────────────────────────────────

def test_an_entry_is_returned_with_its_fields(tmp_path):
    root = node(tmp_path)
    write_graveyard(root, '2026-01-01-a-thing:\n'
                          '  resolution: done\n'
                          '  resolved: "2026-01-02"\n')
    assert FsWorkStore.open(root).tombstone("2026-01-01-a-thing") == Tombstone(
        slug="2026-01-01-a-thing", resolution="done", resolved="2026-01-02")


def test_a_slug_absent_from_the_mapping_is_none(tmp_path):
    root = node(tmp_path)
    write_graveyard(root, '2026-01-01-a-thing:\n  resolution: done\n')
    assert FsWorkStore.open(root).tombstone("2026-01-01-something-else") is None


def test_no_graveyard_file_at_all_is_none(tmp_path):
    """The overwhelmingly common case: a store that has resolved nothing yet.
    It must not be an error, and must not create the file as a side effect."""
    root = node(tmp_path)
    st = FsWorkStore.open(root)
    assert st.tombstone("2026-01-01-a-thing") is None
    assert not (st.root / "graveyard.yaml").exists()


def test_malformed_yaml_degrades_to_none_rather_than_raising(tmp_path):
    """`_safe_yaml`'s stated rule. `resolve_tcw_ref` is contractually forbidden
    from propagating a store exception to a caller scanning many links, so a
    graveyard someone hand-edited badly must not take validation down with it."""
    root = node(tmp_path)
    write_graveyard(root, "not: [valid: yaml\n")
    assert FsWorkStore.open(root).tombstone("2026-01-01-a-thing") is None


def test_a_non_mapping_document_degrades_to_none(tmp_path):
    """Well-formed YAML that is not a slug mapping — a list, a bare scalar —
    is the other shape a hand-edit produces."""
    root = node(tmp_path)
    write_graveyard(root, "- just\n- a list\n")
    assert FsWorkStore.open(root).tombstone("2026-01-01-a-thing") is None


def test_an_entry_missing_its_fields_still_answers_that_the_slug_existed(tmp_path):
    """The question is *did this slug exist*. An entry with no resolution is
    degraded, not absent — answering None would report a typo."""
    root = node(tmp_path)
    write_graveyard(root, "2026-01-01-a-thing: {}\n")
    ts = FsWorkStore.open(root).tombstone("2026-01-01-a-thing")
    assert ts is not None and ts.slug == "2026-01-01-a-thing"


def test_an_entry_that_is_not_a_mapping_still_answers_that_the_slug_existed(tmp_path):
    """`slug:` with nothing under it parses to None, not to an empty mapping —
    a different shape from `slug: {}` and the one a hand-edit actually produces.
    Neither makes the slug a typo, so both must answer that it existed."""
    root = node(tmp_path)
    write_graveyard(root, "2026-01-01-a-thing:\n")
    ts = FsWorkStore.open(root).tombstone("2026-01-01-a-thing")
    assert ts is not None and ts.slug == "2026-01-01-a-thing"
    assert ts.resolution == "" and ts.resolved == ""


# ── writing: resolving an item records one ────────────────────────────────────

def git(root: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(root), *args],
                          capture_output=True, text=True, check=True).stdout


def resolve_item(root: Path, title: str, resolution: str = "done") -> str:
    st = FsWorkStore.open(root)
    slug = st.create_work(title).item.slug
    st.start(slug, owner="t")
    st.complete(slug, resolution, [])
    return slug


def test_completing_records_a_tombstone(tmp_path):
    root = node(tmp_path)
    slug = resolve_item(root, "A thing")
    assert FsWorkStore.open(root).tombstone(slug) == Tombstone(
        slug=slug, resolution="done", resolved=date.today().isoformat())


def test_discarding_records_its_own_resolution(tmp_path):
    """`wontfix` files the item under `discarded/`, and the record says so — the
    graveyard answers "did this exist", but the resolution is what tells a reader
    whether the work shipped or was abandoned."""
    root = node(tmp_path)
    slug = resolve_item(root, "A thing", resolution="wontfix")
    st = FsWorkStore.open(root)
    assert st.tombstone(slug).resolution == "wontfix"
    assert st.get(slug).status == "discarded"


def test_a_second_resolution_leaves_the_first_entry_intact(tmp_path):
    """Read-modify-write, not a blind overwrite. One shared file means every
    resolving transition rewrites it, and a clobber would erase the record of
    everything resolved before it."""
    root = node(tmp_path)
    first = resolve_item(root, "First thing")
    second = resolve_item(root, "Second thing")
    st = FsWorkStore.open(root)
    assert st.tombstone(first) is not None
    assert st.tombstone(second) is not None


def test_the_transition_commit_carries_the_graveyard(tmp_path):
    """The assertion that the record reaches another clone at all, which is the
    entire point of the file."""
    root = node(tmp_path)
    resolve_item(root, "A thing")
    assert "docs/work/graveyard.yaml" in git(root, "show", "--name-only", "--format=", "HEAD")


def test_an_unrelated_dirty_file_is_still_not_swept_in(tmp_path):
    """The transition commit stays scoped. Adding the graveyard to the pathspec
    widens it by exactly one path, not to the whole tree."""
    root = node(tmp_path)
    (root / "unrelated.txt").write_text("do not commit me\n")
    resolve_item(root, "A thing")
    assert "unrelated.txt" not in git(root, "show", "--name-only", "--format=", "HEAD")
    assert "unrelated.txt" in git(root, "status", "--porcelain")


def test_the_epic_route_from_backlog_also_records_one(tmp_path):
    """A completable epic closes straight from `backlog`, bypassing `transition`
    and calling `_effect_transition` directly. A hook on the normal path alone
    would miss it."""
    root = node(tmp_path)
    st = FsWorkStore.open(root)
    epic = st.create_work("An epic", type="epic").item.slug
    child = st.create_work("A child", initiative=epic).item.slug
    # Discarded straight from `backlog`: an initiative child cannot *start* until
    # its epic is active, and an active epic would not take the backlog route
    # this test exists to cover. A discarded child still resolves the epic —
    # "a child nobody will do no longer holds its epic open".
    st.complete(child, "wontfix", [])
    st.complete(epic, "done", [])                     # from backlog, epic route
    assert FsWorkStore.open(root).tombstone(epic) is not None


# ── writing: refusing rather than absorbing ───────────────────────────────────

def test_a_dirty_graveyard_refuses_the_transition_and_moves_nothing(tmp_path):
    """Every graveyard write commits itself, so uncommitted changes in it are
    someone else's in-flight edit. Committing them under *this* item's message
    is the one hole a shared path opens in the scoped-commit promise; refusing
    closes it."""
    root = node(tmp_path)
    resolve_item(root, "First thing")                 # creates and commits it
    st = FsWorkStore.open(root)
    gy = st.root / "graveyard.yaml"
    gy.write_text(gy.read_text() + "someone-elses-edit: {resolution: done}\n")

    slug = st.create_work("Second thing").item.slug
    st.start(slug, owner="t")
    with pytest.raises(ValueError, match="graveyard"):
        st.complete(slug, "done", [])

    assert FsWorkStore.open(root).get(slug).status == "active"    # moved nothing
    assert "graveyard" in git(root, "status", "--porcelain")      # still uncommitted
    assert "someone-elses-edit" in gy.read_text()                 # and untouched


def test_an_unparseable_graveyard_refuses_rather_than_resetting_it(tmp_path):
    """Committed but malformed: the dirty check passes, so only the writer can
    catch it. Parsing it as empty and writing one entry back would silently
    delete the record of everything resolved before."""
    root = node(tmp_path)
    resolve_item(root, "First thing")
    st = FsWorkStore.open(root)
    gy = st.root / "graveyard.yaml"
    gy.write_text("not: [valid: yaml\n")
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(root), "commit", "-qm", "break it"], check=True)

    slug = st.create_work("Second thing").item.slug
    st.start(slug, owner="t")
    with pytest.raises(ValueError, match="graveyard"):
        st.complete(slug, "done", [])
    assert gy.read_text() == "not: [valid: yaml\n"                # not clobbered


def test_auto_commit_off_does_not_refuse_on_its_own_uncommitted_write(tmp_path):
    """With `auto-commit-transitions: false` the user manages commits, so an
    uncommitted graveyard is the expected steady state rather than a conflict.
    Refusing there would make the setting unusable after the first resolution."""
    root = node(tmp_path)
    cfg = root / "tcw-config.yaml"
    cfg.write_text(cfg.read_text() + "work:\n  auto-commit-transitions: false\n")
    resolve_item(root, "First thing")
    slug = resolve_item(root, "Second thing")         # must not raise
    assert FsWorkStore.open(root).tombstone(slug) is not None


# ── `tcw work tombstone add`: recording one after the fact ────────────────────
#
# Required, not a convenience. Every reference written before this feature
# existed names an item resolved before any graveyard did, so without a way to
# record a slug retroactively the whole thing is inert for existing repositories.
# Deriving the entries from git history instead would be the "reconstruct state
# from history" trick the prime directive forbids.

def test_tombstone_add_records_a_slug_with_no_live_item(tmp_path, monkeypatch):
    root = node(tmp_path)
    monkeypatch.chdir(root)
    assert main(["work", "tombstone", "add", "2026-01-01-long-gone"]) == 0
    ts = FsWorkStore.open(root).tombstone("2026-01-01-long-gone")
    assert ts is not None and ts.slug == "2026-01-01-long-gone"


def test_tombstone_add_defaults_the_date_to_today_and_accepts_an_explicit_one(
        tmp_path, monkeypatch):
    root = node(tmp_path)
    monkeypatch.chdir(root)
    assert main(["work", "tombstone", "add", "2026-01-01-a"]) == 0
    assert FsWorkStore.open(root).tombstone("2026-01-01-a").resolved == \
        date.today().isoformat()
    assert main(["work", "tombstone", "add", "2026-01-01-b",
                 "--resolved", "2025-06-01"]) == 0
    assert FsWorkStore.open(root).tombstone("2026-01-01-b").resolved == "2025-06-01"


def test_tombstone_add_records_the_resolution_when_given(tmp_path, monkeypatch):
    root = node(tmp_path)
    monkeypatch.chdir(root)
    assert main(["work", "tombstone", "add", "2026-01-01-a",
                 "--resolution", "wontfix"]) == 0
    assert FsWorkStore.open(root).tombstone("2026-01-01-a").resolution == "wontfix"


def test_tombstone_add_refuses_a_live_slug_and_writes_nothing(tmp_path, monkeypatch):
    """The one guard on a command that otherwise trusts its caller. Recording a
    live item would make `_unique_slug` refuse a slug that is legitimately in
    use, and would claim finished work that is not finished."""
    root = node(tmp_path)
    st = FsWorkStore.open(root)
    slug = st.create_work("A live thing").item.slug
    monkeypatch.chdir(root)
    assert main(["work", "tombstone", "add", slug]) == 1
    assert FsWorkStore.open(root).tombstone(slug) is None
    assert not (FsWorkStore.open(root).root / "graveyard.yaml").exists()


def test_tombstone_add_records_a_resolved_item_whose_folder_is_still_here(
        tmp_path, monkeypatch):
    """The backfill case the command exists for, and the one it used to refuse.

    `get()` answers for `completed/` and `discarded/` too, so on the machine that
    ran the transition a resolved item is still findable — and that is *exactly*
    the machine an adopter backfills from. They read the failing slugs off CI,
    where the folders never arrived, and run this command at home, where they
    did. Refusing there left the documented migration path with no way through:
    the message said "resolve the item instead" of an item already resolved.
    """
    root = node(tmp_path)
    slug = resolve_item(root, "A thing", resolution="done")
    st = FsWorkStore.open(root)
    # An adopter upgrading: the folder is on disk, nothing was ever recorded.
    (st.root / "graveyard.yaml").unlink()
    assert st.get(slug) is not None and st.get(slug).status == "completed"

    monkeypatch.chdir(root)
    assert main(["work", "tombstone", "add", slug, "--resolution", "done"]) == 0
    assert FsWorkStore.open(root).tombstone(slug).resolution == "done"


def test_tombstone_add_leaves_an_existing_record_alone(tmp_path, monkeypatch):
    """A re-run must not degrade what is already recorded.

    `_write_tombstone` assigns `doc[slug]` outright, which is right for a
    transition (a re-resolution should say the new thing) and wrong for a
    backfill: running the command a second time without `--resolution` would
    replace a recorded `done` with an empty string and the real date with today,
    report success, and commit it. A scripted backfill loop re-run over the same
    list is the obvious way to hit it — and it only became reachable once the
    guard above stopped rejecting resolved items outright.
    """
    root = node(tmp_path)
    monkeypatch.chdir(root)
    assert main(["work", "tombstone", "add", "2026-01-01-a",
                 "--resolution", "wontfix", "--resolved", "2025-06-01"]) == 0

    assert main(["work", "tombstone", "add", "2026-01-01-a"]) == 1
    ts = FsWorkStore.open(root).tombstone("2026-01-01-a")
    assert ts.resolution == "wontfix" and ts.resolved == "2025-06-01"


@pytest.mark.parametrize("bad", ["", "   ", "completed/2026-01-01-a"])
def test_tombstone_add_refuses_a_slug_that_names_no_item(bad, tmp_path, monkeypatch):
    """There is no `tcw work tombstone rm`, so a junk key is permanent short of
    the hand-edit the graveyard exists to make unnecessary. Blank and path-shaped
    are the two that can never name an item; anything stricter would refuse a
    legitimate slug minted by an older version of this tool."""
    root = node(tmp_path)
    monkeypatch.chdir(root)
    assert main(["work", "tombstone", "add", bad]) == 1
    assert not (FsWorkStore.open(root).root / "graveyard.yaml").exists()


def test_tombstone_add_normalizes_the_resolved_date(tmp_path, monkeypatch):
    """`date.fromisoformat` accepts `20260601` on 3.11+, so validating without
    normalizing would store a shape nothing else in the store writes or reads."""
    root = node(tmp_path)
    monkeypatch.chdir(root)
    assert main(["work", "tombstone", "add", "2026-01-01-a",
                 "--resolved", "20260601"]) == 0
    assert FsWorkStore.open(root).tombstone("2026-01-01-a").resolved == "2026-06-01"


def test_a_graveyard_that_is_not_utf8_reads_as_absent(tmp_path):
    """`_safe_yaml` catches a YAML syntax error and nothing else. An unreadable
    file must not surface inside `_unique_slug`, where it would turn `tcw work
    new` into a traceback about a file the user never touched."""
    root = node(tmp_path)
    st = FsWorkStore.open(root)
    (st.root / "graveyard.yaml").write_bytes(b"\xff\xfe not utf-8 at all")
    assert st.tombstone("2026-01-01-a") is None
    assert st.create_work("A new thing").item.slug        # slug minting survives


def test_tombstone_add_refuses_an_unknown_resolution(tmp_path, monkeypatch):
    root = node(tmp_path)
    monkeypatch.chdir(root)
    assert main(["work", "tombstone", "add", "2026-01-01-a",
                 "--resolution", "banana"]) == 1
    assert FsWorkStore.open(root).tombstone("2026-01-01-a") is None


def test_tombstone_add_commits_its_own_write(tmp_path, monkeypatch):
    """Spec criterion 13. The graveyard's whole job is to reach other clones,
    and an uncommitted one reaches none of them. It also keeps the invariant the
    transition guard relies on: a dirty graveyard means something went wrong."""
    root = node(tmp_path)
    monkeypatch.chdir(root)
    assert main(["work", "tombstone", "add", "2026-01-01-a"]) == 0
    assert "graveyard" not in git(root, "status", "--porcelain")
    assert "docs/work/graveyard.yaml" in git(root, "show", "--name-only", "--format=", "HEAD")


def test_auto_commit_off_suppresses_the_tombstone_add_commit(tmp_path, monkeypatch):
    """Exactly as it does for a transition — one setting, one meaning."""
    root = node(tmp_path)
    cfg = root / "tcw-config.yaml"
    cfg.write_text(cfg.read_text() + "work:\n  auto-commit-transitions: false\n")
    monkeypatch.chdir(root)
    assert main(["work", "tombstone", "add", "2026-01-01-a"]) == 0
    assert FsWorkStore.open(root).tombstone("2026-01-01-a") is not None
    assert "graveyard" in git(root, "status", "--porcelain")


# ── slug assignment ───────────────────────────────────────────────────────────

def test_a_new_item_never_reuses_a_tombstoned_slug(tmp_path):
    """`_unique_slug` loops over *live* items, so in a clone without the ignored
    `completed/` folder nothing stopped a new item from being handed a resolved
    item's slug — after which every reference to the resolved item resolved,
    silently, to a different item. A dangling reference is loud and harmless;
    this is neither.

    Forward-only: slugs are assumed unique to date, so there is no audit of
    existing items. This is what keeps the assumption true from here on.
    """
    root = node(tmp_path)
    st = FsWorkStore.open(root)
    slug = st.create_work("A thing", created="2026-01-01").item.slug
    st.start(slug, owner="t")
    st.complete(slug, "done", [])
    # The clone's condition, reproduced in place: the record survives, the
    # folder does not.
    subprocess.run(["git", "-C", str(root), "rm", "-r", "-q", "--ignore-unmatch",
                    f"docs/work/completed/{slug}"], check=True)
    shutil.rmtree(root / "docs" / "work" / "completed" / slug, ignore_errors=True)

    again = FsWorkStore.open(root).create_work("A thing", created="2026-01-01").item.slug
    assert again != slug
    assert FsWorkStore.open(root).tombstone(slug) is not None   # still recorded
