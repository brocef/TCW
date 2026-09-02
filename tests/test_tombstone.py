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

import subprocess
from pathlib import Path

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
