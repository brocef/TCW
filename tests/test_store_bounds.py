"""Store containment — a store id never names a file outside its own store.

`_safe_store_id` closes every *syntactic* escape (`..`, absolute paths, NUL).
These tests close the *filesystem* one: a symlink planted inside a store is
lexically clean, so the join lands wherever it points. See the item spec at
`docs/work/active/2026-07-30-resolve-taxonomy-refs-against-symlinks-not-just-lexically/`.

Every fixture is a real `git init` repository: a repository precondition runs
inside `_write_node`, so a write into a non-repository fails there rather than
at the containment guard, which would make these tests pass for the wrong
reason.
"""

import subprocess

import pytest

from tcw.store.fs import (FsCapabilitiesStore, FsTaxonomyStore, FsWorkStore,
                          write_sentinel)


def _repo(tmp_path, name="repo"):
    """A git repository with all three component trees scaffolded.

    `write_sentinel` is what makes it a *node*: without `tcw-config.yaml` the
    project registry refuses it, and every test here would fail on the fixture
    rather than on the behavior under test.
    """
    root = tmp_path / name
    for component in ("taxonomy", "capabilities", "work"):
        (root / "docs" / component).mkdir(parents=True)
    for status in ("inbox", "backlog", "active", "review", "completed", "discarded"):
        (root / "docs" / "work" / status).mkdir()
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "t"], check=True)
    write_sentinel(root, name)
    return root


# ── the helper itself ────────────────────────────────────────────────────────

@pytest.mark.parametrize("store_cls", [FsTaxonomyStore, FsCapabilitiesStore, FsWorkStore])
def test_within_store_exists_on_every_store_class(tmp_path, store_cls):
    """`FsWorkStore.__init__` does not chain to `FsTreeStore.__init__`, so a
    `_resolved_root` assigned in the base initializer would be missing there.
    One case per class is what proves the `cached_property` resolves for all."""
    root = _repo(tmp_path)
    store = store_cls.open(root)
    assert store._within_store(store.root / "ordinary-child") is True


def test_within_store_rejects_a_sibling_reached_through_a_symlink(tmp_path):
    root = _repo(tmp_path)
    (root / "docs" / "capabilities" / "secret").mkdir()
    (root / "docs" / "taxonomy" / "link").symlink_to("../capabilities/secret")
    store = FsTaxonomyStore.open(root)
    assert store._within_store(store.root / "link" / "victim") is False


def test_within_store_allows_a_path_that_does_not_exist_yet(tmp_path):
    """Non-strict `resolve()` resolves the existing prefix and appends the rest,
    so the helper is usable on a write target as well as a read."""
    root = _repo(tmp_path)
    store = FsTaxonomyStore.open(root)
    assert store._within_store(store.root / "not" / "created" / "yet") is True


def test_within_store_never_raises_on_a_symlink_loop(tmp_path):
    """The requirement is "does not raise", not a particular verdict.

    A loop raises `RuntimeError` on Python < 3.13 — not an `OSError` — and
    since 3.13 raises nothing at all, returning the path unresolved. Pinning
    the verdict would pin a Python-version detail; every read through a loop
    fails with ELOOP regardless, and every caller stats before reading.
    """
    root = _repo(tmp_path)
    (root / "docs" / "taxonomy" / "loop-a").symlink_to("loop-b")
    (root / "docs" / "taxonomy" / "loop-b").symlink_to("loop-a")
    store = FsTaxonomyStore.open(root)
    assert store._within_store(store.root / "loop-a" / "child") in (True, False)


def test_within_store_rejects_a_sibling_root_sharing_a_name_prefix(tmp_path):
    """`/a/store-other` must not read as inside `/a/store`."""
    root = _repo(tmp_path)
    (root / "docs" / "taxonomy-other").mkdir()
    store = FsTaxonomyStore.open(root)
    assert store._within_store(root / "docs" / "taxonomy-other" / "x") is False


def test_within_store_accepts_a_store_opened_through_a_symlinked_spelling(tmp_path):
    """A checkout reached through a symlinked ancestor must keep working.

    Asserted with an explicit fixture rather than inferred from the suite
    passing under `tmp_path`: pytest hands over an already-physical path, so a
    green suite proves nothing about symlinked roots.
    """
    _repo(tmp_path, "real")
    link = tmp_path / "link"
    link.symlink_to("real")
    store = FsTaxonomyStore.open(link)
    assert store._within_store(store.root / "alpha") is True


# ── resource containment: the files *inside* an in-store folder ──────────────
#
# A folder can be legitimately inside the store while a file inside it is a
# symlink pointing out. Every directory-level guard passes, and the external
# file is read in full. The work store already gets this treatment for a
# symlinked `state.yaml`; these are the symmetric cases for the other two.

def _outside(root, name, text):
    """A file outside every store, for a planted symlink to point at."""
    d = root.parent / "outside"
    d.mkdir(exist_ok=True)
    (d / name).write_text(text)
    return d / name


def test_taxonomy_node_with_a_symlinked_meta_does_not_resolve(tmp_path):
    root = _repo(tmp_path)
    target = _outside(root, "meta.yaml", "kind: Vocabulary\nname: Stolen\n")
    d = root / "docs" / "taxonomy" / "victim"
    d.mkdir()
    (d / "meta.yaml").symlink_to(target)
    (d / "description.md").write_text("body")
    assert FsTaxonomyStore.open(root).get_local("victim") is None


def test_capability_node_with_a_symlinked_meta_does_not_resolve(tmp_path):
    root = _repo(tmp_path)
    target = _outside(root, "meta.yaml", "id: cap-stolen\nname: Stolen\nStatus: Supported\n")
    d = root / "docs" / "capabilities" / "victim"
    d.mkdir()
    (d / "meta.yaml").symlink_to(target)
    (d / "description.md").write_text("body")
    assert FsCapabilitiesStore.open(root).get_local("victim") is None


def test_a_symlinked_description_reads_empty_not_external(tmp_path):
    """The node still resolves — its meta is real — but the external body must
    not appear in it."""
    root = _repo(tmp_path)
    target = _outside(root, "description.md", "SECRET BODY")
    d = root / "docs" / "capabilities" / "partly"
    d.mkdir()
    (d / "meta.yaml").write_text("id: cap-partly\nname: Partly\nStatus: Supported\n")
    (d / "description.md").symlink_to(target)
    cap = FsCapabilitiesStore.open(root).get_local("partly")
    assert cap is not None
    assert "SECRET BODY" not in (cap.body or "")


def test_an_in_store_node_still_reads_normally(tmp_path):
    """The control. Without it, a broken fixture is indistinguishable from a
    working guard — every assertion above is about something *not* happening."""
    root = _repo(tmp_path)
    d = root / "docs" / "capabilities" / "ordinary"
    d.mkdir()
    (d / "meta.yaml").write_text("id: cap-ord\nname: Ordinary\nStatus: Supported\n")
    (d / "description.md").write_text("REAL BODY")
    cap = FsCapabilitiesStore.open(root).get_local("ordinary")
    assert cap is not None and cap.name == "Ordinary"
    assert "REAL BODY" in cap.body
