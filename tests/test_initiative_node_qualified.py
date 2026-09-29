"""An epic's slices are matched by the epic's node as well as its slug (spec:
2026-09-27-match-an-epic-s-children-by-the-epic-s-node-as-well-as-its-slug)."""

import pytest
import yaml

from tcw.store.fs import FsWorkStore
from tcw.work.recursion import delegate
from test_routing_nodes import node, slice_of

EPIC = "2026-01-01-epic"


@pytest.fixture
def graph(tmp_path):
    root = node(tmp_path / "root", "root", board=True, children={"kid": "kid"})
    node(root / "kid", "kid", board=True, parent="root")
    return root


def epic_in(where) -> str:
    st = FsWorkStore.open(where)
    slug = st.create("Epic", created="2026-01-01").slug
    st.set_field(slug, "type", "epic")
    assert slug == EPIC
    return slug


def slugs(items):
    return sorted(i.slug for i in items)


def test_a_child_node_s_own_same_slug_epic_keeps_its_slices(graph):
    epic_in(graph)
    epic_in(graph / "kid")
    done = slice_of(graph, EPIC, title="Root slice")
    FsWorkStore.open(graph).complete(done, "wontfix", [])
    theirs = slice_of(graph / "kid", EPIC, title="Kid slice")   # bare, legacy
    root = FsWorkStore.open(graph)
    assert theirs not in slugs(root.initiative_children(EPIC))
    assert theirs in slugs(FsWorkStore.open(graph / "kid").initiative_children(EPIC))
    root.complete(EPIC, "done", [])
    assert root.get(EPIC).status == "completed"


def test_a_child_node_s_graveyard_record_counts_for_its_own_epic(graph):
    epic_in(graph)
    epic_in(graph / "kid")
    FsWorkStore.open(graph / "kid")._write_tombstone(
        "2026-01-01-gone", "done", initiative=EPIC)
    assert FsWorkStore.open(graph).resolved_initiative_children(EPIC) == []
    assert FsWorkStore.open(graph / "kid").resolved_initiative_children(EPIC) == [
        (".", "2026-01-01-gone")]


def test_delegate_records_the_epic_s_node(graph):
    epic_in(graph)
    epic_in(graph / "kid")
    doc = delegate(graph, "kid", "Slice", initiative=EPIC)
    assert f"initiative: root/{EPIC}" in doc.read_text()
    kid = FsWorkStore.open(graph / "kid")
    entry, = kid.inbox_list()
    item = kid.inbox_accept(entry.ref)
    assert item.initiative == f"root/{EPIC}"
    assert item.slug in slugs(FsWorkStore.open(graph).initiative_children(EPIC))
    assert item.slug not in slugs(kid.initiative_children(EPIC))
    FsWorkStore.open(graph).transition(EPIC, "active")    # tell the two apart
    epic = kid.initiative_epic(kid.get(item.slug))
    assert epic is not None and epic.slug == EPIC and epic.status == "active"


def test_delegate_refuses_an_epic_it_cannot_find(graph):
    with pytest.raises(ValueError, match="<project-id>/<slug>"):
        delegate(graph, "kid", "Slice", initiative="2026-01-01-nowhere")


def test_an_old_bare_slice_below_still_counts(graph):
    epic_in(graph)
    theirs = slice_of(graph / "kid", EPIC, title="Kid slice")
    assert theirs in slugs(FsWorkStore.open(graph).initiative_children(EPIC))


def test_new_records_the_node_only_when_the_epic_is_elsewhere(graph):
    epic_in(graph)
    kid = FsWorkStore.open(graph / "kid").create_work("Kid slice", initiative=EPIC).item
    assert kid.initiative == f"root/{EPIC}"
    here = FsWorkStore.open(graph).create_work("Root slice", initiative=EPIC).item
    assert here.initiative == EPIC
    assert slugs(FsWorkStore.open(graph).initiative_children(EPIC)) == sorted(
        [kid.slug, here.slug])


def test_list_nests_a_qualified_slice_under_the_epic(graph, monkeypatch, capsys):
    from tcw.cli import main
    epic_in(graph)
    epic_in(graph / "kid")
    FsWorkStore.open(graph / "kid").create_work("Kid slice", initiative=f"root/{EPIC}")
    monkeypatch.chdir(graph)
    capsys.readouterr()
    main(["work", "list", "--all", "-i"])
    lines = capsys.readouterr().out.splitlines()
    row = next(i for i, line in enumerate(lines) if "kid-slice" in line)
    assert lines[row].startswith("  kid/"), lines
    assert lines[row - 1].startswith(EPIC), lines          # under root's epic
    assert lines.index("# kid") > row, lines                # not in kid's section


@pytest.fixture
def siblings(tmp_path):
    root = node(tmp_path / "root", "root", board=False, children={"a": "a", "b": "b"})
    node(root / "a", "a", board=True, parent="root")
    node(root / "b", "b", board=True, parent="root")
    return root


def test_an_initiative_naming_a_sibling_is_refused(siblings):
    epic_in(siblings / "a")
    b = FsWorkStore.open(siblings / "b")
    with pytest.raises(ValueError, match="neither this one nor above it"):
        b.create_work("B slice", initiative=f"a/{EPIC}")
    item = b.create("B slice", created="2026-01-01")
    b.set_field(item.slug, "initiative", f"a/{EPIC}")     # written by hand
    assert b.initiative_epic(b.get(item.slug)) is None   # so start refuses
    with pytest.raises(ValueError, match="names no epic in 'b'"):
        delegate(siblings, "b", "Slice", initiative=f"a/{EPIC}")


def test_a_resolved_local_epic_keeps_its_bare_slices_on_another_clone(graph):
    """`completed/` is not in every clone: the graveyard record is what says
    the kid's own epic existed."""
    import shutil
    epic_in(graph)
    epic_in(graph / "kid")
    kid = FsWorkStore.open(graph / "kid")
    slice_slug = kid.create_work("Kid slice", initiative=EPIC).item.slug
    kid.complete(slice_slug, "wontfix", [])
    kid.complete(EPIC, "done", [], force=True)
    for d in (graph / "kid" / "docs" / "work").glob("*/2026-0*"):
        if d.parent.name in ("completed", "discarded"):
            shutil.rmtree(d)
    root = FsWorkStore.open(graph)
    assert root.resolved_initiative_children(EPIC) == []
    assert not root.epic_completable(root.get(EPIC))
