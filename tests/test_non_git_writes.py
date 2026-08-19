"""Writes outside a git repository refuse before touching the filesystem.

TCW's contract is that **reads** work anywhere and **writes** need a repository.
The refusal used to be inconsistent: `tcw init` said so in one line, while every
store write died in `git_stage` with an unhandled `CalledProcessError` — after
creating the item, moving it, or rewriting the config it was about to stage.

The guard is a filesystem-adapter precondition (`require_repository`), not a
model concept: a remote store has no repository to require. It sits in two
places — the `_stage`/`_rm`/`_mv` funnel, so no git failure can escape as a
traceback, and the public write methods whose first mutation *precedes* their
staging call, so nothing lands before the refusal.
"""
import hashlib
import shutil
import subprocess
from pathlib import Path

import pytest

from tcw.store.fs import (
    NOT_A_REPOSITORY, FsCapabilitiesStore, FsTaxonomyStore, FsTreeStore,
    FsWorkStore, init,
    require_repository,
)

REFUSED = "not inside a git repository"


def repo(tmp_path: Path, name: str = "repo") -> Path:
    """A committed TCW node inside a git repository."""
    root = tmp_path / name
    root.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", "-b", "main", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "t"], check=True)
    init(["taxonomy", "capabilities", "work"], root, name.lower())
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(root), "commit", "-qm", "init"], check=True)
    return root


def manifest(root: Path) -> dict[str, str]:
    """Every path under `root`, **directories included**.

    A file-only map would call a run clean that left `docs/work/.claiming/`
    behind — `FsWorkStore.start` creates that directory before it renames
    anything. An empty directory is a partial write too.
    """
    out: dict[str, str] = {}
    for p in sorted(root.rglob("*")):
        rel = str(p.relative_to(root))
        out[rel] = "<dir>" if p.is_dir() else hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def refuses(store, call) -> None:
    """`call` is refused, and nothing under the store's node moved."""
    before = manifest(store.node_root)
    with pytest.raises(ValueError, match=REFUSED):
        call()
    assert manifest(store.node_root) == before


@pytest.fixture
def unrepo(tmp_path):
    """A seeded node whose repository was removed after the seeding committed.

    The reachable shape: `tcw init` refuses outside a repository, so a node
    without one arrives by the repository being deleted, by an export, or by a
    `docs/` tree vendored into a plain directory.
    """
    root = repo(tmp_path)
    work = FsWorkStore.open(root)
    work.create("Backlog item", created="2026-01-01")
    active = work.create("Active item", created="2026-01-02")
    work.start(active.slug, owner="t")
    FsTaxonomyStore.open(root).add("Widget", slug="widget")
    FsCapabilitiesStore.open(root).add("seeded/cap", "Seeded cap")
    (root / "docs" / "work" / "inbox" / "raw.md").write_text(
        "# Raw\n\nbody\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(root), "commit", "-qm", "seed"], check=True)
    shutil.rmtree(root / ".git")
    return root


# ── The precondition itself ──────────────────────────────────────────────────


def test_require_repository_accepts_a_repository(tmp_path):
    assert require_repository(repo(tmp_path)) is None


def test_require_repository_refuses_a_plain_directory(tmp_path):
    plain = tmp_path / "plain"
    plain.mkdir()
    with pytest.raises(ValueError) as e:
        require_repository(plain)
    assert str(e.value) == NOT_A_REPOSITORY


def test_each_store_checks_the_repository_it_actually_writes_to(tmp_path):
    """A work store's repository can differ from its node's (`work.path`)."""
    root = repo(tmp_path)
    work = FsWorkStore.open(root)
    assert work._write_git_root() == work.store_git_root
    taxonomy = FsTaxonomyStore.open(root)
    assert taxonomy._write_git_root() == taxonomy.node_root


def test_the_guard_holds_no_state_because_it_could_not_be_initialized(tmp_path):
    """Why `_require_repository` re-probes instead of caching.

    `FsWorkStore.__init__` does not chain to `FsTreeStore.__init__` — it assigns
    `root`/`node_root`/`store_git_root`/`config` itself — so any attribute added
    to the base initializer is simply absent on every work store, and the first
    work write would raise `AttributeError`. If someone makes the guard stateful
    later, this is the test that has to be read first.
    """
    assert FsWorkStore.__init__ is not FsTreeStore.__init__
    root = repo(tmp_path)
    assert FsWorkStore.open(root)._require_repository() is None


# ── The work store ───────────────────────────────────────────────────────────


def test_every_work_write_is_refused_and_writes_nothing(unrepo):
    st = FsWorkStore.open(unrepo)
    backlog = st.query("backlog")[0].slug
    active = st.query("active")[0].slug

    refuses(st, lambda: st.create_work("New", created="2026-01-03"))
    refuses(st, lambda: st.update_work(backlog, title="Renamed"))
    refuses(st, lambda: st.start(backlog, owner="t"))
    refuses(st, lambda: st.submit(active))            # _effect_transition
    refuses(st, lambda: st.set_field(backlog, "priority", 1))
    refuses(st, lambda: st.register_tags(["demo"]))
    refuses(st, lambda: st.unregister_tags(["demo"]))
    refuses(st, lambda: st.inbox_accept("raw.md"))
    refuses(st, lambda: st.write_artifact(backlog, "spec", "# Spec\n"))
    refuses(st, lambda: st.write_draft(backlog, "spec", "# Draft\n"))
    refuses(st, lambda: st.write_sidecar(backlog, "capabilities.yaml", "changed: []\n"))
    refuses(st, lambda: st.write_plan_stage(backlog, "one", "# Stage\n"))
    refuses(st, lambda: st.drop(backlog))             # _delete → _rm (Tier 1 only)


def test_a_no_change_update_still_succeeds_outside_a_repository(unrepo):
    """Placement, not just presence.

    `update_work` returns before writing when nothing changed. A guard at the
    top of the method would turn that read-shaped call into a refusal, so the
    guard sits after the no-change decision and before `_atomic_write_all`.
    """
    st = FsWorkStore.open(unrepo)
    slug = st.query("backlog")[0].slug
    before = manifest(unrepo)
    assert st.update_work(slug).item.slug == slug     # no fields → no write
    assert manifest(unrepo) == before


def test_start_is_refused_before_it_makes_the_claiming_folder(tmp_path):
    """`start` reaches `git_stage` directly, bypassing `_stage`, on both its
    branches, and both rename before they stage — so the guard has to be its
    literal first statement, ahead of the `.claiming/` directory it creates.

    A fresh node rather than the shared fixture: `.claiming/` survives a
    *successful* `start` (nothing removes it), so a node that has ever started
    an item cannot tell "not created" from "already there".
    """
    root = repo(tmp_path)
    st = FsWorkStore.open(root)
    slug = st.create("Task", created="2026-01-01").slug
    shutil.rmtree(root / ".git")
    claiming = root / "docs" / "work" / ".claiming"
    assert not claiming.exists()
    refuses(st, lambda: st.start(slug, owner="t"))
    refuses(st, lambda: st.start(slug, owner="t", take_over=True))
    assert not claiming.exists()


def test_a_repository_removed_after_a_successful_write_still_refuses(tmp_path):
    """Repository membership is not frozen for a store's lifetime.

    The same instance that just wrote successfully must re-check. This is the
    test a memoized guard would fail, and the reason the guard holds no state.
    """
    root = repo(tmp_path)
    st = FsWorkStore.open(root)
    st.create("First", created="2026-01-01")
    shutil.rmtree(root / ".git")
    backlog = root / "docs" / "work" / "backlog"
    before = manifest(backlog)
    with pytest.raises(ValueError, match=REFUSED):
        st.create("Second", created="2026-01-01")
    assert manifest(backlog) == before


def test_reads_do_not_acquire_a_repository_precondition(unrepo):
    """Goal 4: the guard must not leak into a read path through a shared helper."""
    st = FsWorkStore.open(unrepo)
    slug = st.query("backlog")[0].slug
    assert len(st.query()) == 2
    assert st.get(slug).slug == slug
    assert st.get_detail(slug) is not None
    assert st.locate(slug)
    assert st.check() == []
    assert st.board() is not None
    assert st.inbox_list()
    assert st.inbox_show("raw.md") is not None
    assert st.registered_tags() == []
    assert st._validation_resources(slug)          # targeted `tcw validate`


# ── The taxonomy and capabilities stores ─────────────────────────────────────


def test_every_taxonomy_write_is_refused_and_writes_nothing(unrepo):
    st = FsTaxonomyStore.open(unrepo)
    refuses(st, lambda: st.add("Gadget", slug="gadget"))
    assert not (unrepo / "docs" / "taxonomy" / "gadget").exists()
    refuses(st, lambda: st.update_term("widget", name="Renamed"))
    refuses(st, lambda: st.remove("widget"))
    refuses(st, lambda: st.extends_add("other"))
    refuses(st, lambda: st.extends_remove("other"))


def test_every_capability_write_is_refused_and_writes_nothing(unrepo):
    st = FsCapabilitiesStore.open(unrepo)
    refuses(st, lambda: st.add("doing/a-thing", "Do a thing"))
    assert not (unrepo / "docs" / "capabilities" / "doing").exists()
    refuses(st, lambda: st.set("seeded/cap", {"Status": "Supported"}))
    refuses(st, lambda: st.update_capability("seeded/cap", body="new"))
    refuses(st, lambda: st.remove("seeded/cap"))
    # `reset` is not here: it refuses a *local* capability on its own terms
    # ("not an override") before any git path, and reaching its `_rm` needs a
    # federated override. That `_rm` is the same Tier-1 guard `remove` exercises
    # one line above.
    refuses(st, lambda: st.extends_add("other"))
    refuses(st, lambda: st.extends_remove("other"))


def test_tree_store_reads_do_not_acquire_a_repository_precondition(unrepo):
    """Goal 4, the other two stores: `_write_node`'s guard must not reach a read."""
    tax = FsTaxonomyStore.open(unrepo)
    assert [t.slug for t in tax.list_all(local_only=True)] == ["widget"]
    assert tax.get("widget") is not None
    assert tax.get_term_detail("widget") is not None
    assert tax.search("widget")
    assert tax.check() == []
    assert tax.relators("widget") == []
    assert tax.__class__.__mro__          # sanity: store constructed at all
    assert tax._validation_resources("widget")

    cap = FsCapabilitiesStore.open(unrepo)
    assert [c.path for c in cap.list_all(local_only=True)] == ["seeded/cap"]
    assert cap.get("seeded/cap") is not None
    assert cap.get_capability_detail("seeded/cap") is not None
    assert cap.search("cap")
    assert cap.check(taxonomy=tax) == []
    assert cap.unreviewed_inherited() == []
    assert cap._validation_resources("seeded/cap")
