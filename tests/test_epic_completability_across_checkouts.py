"""An epic whose children are all resolved reads as ready to close in every
checkout (spec: 2026-09-09-make-epic-completability-read-the-same-in-every-checkout)."""

import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

from tcw.store.fs import FsWorkStore, init


def node(path: Path, pid: str, *, board: bool = True, parent: str | None = None,
         children: dict | None = None, git: bool = True) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    if git and parent is None:
        for cmd in (["init", "-q"], ["config", "user.email", "t@t"],
                    ["config", "user.name", "t"]):
            subprocess.run(["git", "-C", str(path), *cmd], check=True)
    if board:
        init(["work"], path, pid)
    else:
        (path / "tcw-config.yaml").write_text(f"id: {pid}\n")
    cfg = yaml.safe_load((path / "tcw-config.yaml").read_text()) or {}
    links = {}
    if parent:
        links["parent"] = {parent: ".."}
    if children:
        links["children"] = children
    if links:
        cfg["connected-projects"] = links
    (path / "tcw-config.yaml").write_text(yaml.safe_dump(cfg, sort_keys=False))
    return path


def new(st: FsWorkStore, title: str, **fields) -> str:
    slug = st.create(title, created="2026-01-01").slug
    for key, value in fields.items():
        st.set_field(slug, key, value)
    return slug


def finish(st: FsWorkStore, slug: str, resolution: str = "done") -> None:
    if resolution == "done":
        st.start(slug, force=True)
    st.complete(slug, resolution, st.dod_checklist(), force=True)


def elsewhere(st: FsWorkStore, slug: str) -> None:
    """What every clone but the resolving one sees: the folder is gone."""
    shutil.rmtree(st.path(slug))
    assert st.get(slug) is None and st.tombstone(slug) is not None


@pytest.fixture
def solo(tmp_path) -> FsWorkStore:
    return FsWorkStore.open(node(tmp_path / "solo", "solo"))


def epic(st: FsWorkStore) -> str:
    return new(st, "Epic", type="epic")


# ── criterion 1 ──────────────────────────────────────────────────────────────

def test_an_epic_whose_child_is_gone_can_close_from_backlog(solo):
    e = epic(solo)
    child = new(solo, "Child", initiative=e)
    finish(solo, child)
    elsewhere(solo, child)
    assert solo.epic_completable(solo.get(e))
    assert solo.complete(e, "done", solo.dod_checklist()).status == "completed"


def test_the_tombstone_records_the_epic(solo):
    e = epic(solo)
    child = new(solo, "Child", initiative=e)
    finish(solo, child, "wontfix")
    assert solo.tombstone(child).initiative == e


# ── criterion 2: in a descendant node, and behind a routing node ─────────────

def test_a_child_in_a_node_below_a_routing_node(tmp_path):
    root = node(tmp_path / "root", "root", children={"mid": "mid"})
    node(root / "mid", "mid", board=False, parent="root", children={"pc": "pc"})
    node(root / "mid" / "pc", "pc", parent="mid")
    top, low = FsWorkStore.open(root), FsWorkStore.open(root / "mid" / "pc")
    e = epic(top)
    child = new(low, "Child", initiative=e)
    finish(low, child)
    elsewhere(low, child)
    assert top.epic_completable(top.get(e))


# ── criterion 3: what must stay not completable ─────────────────────────────

def test_a_childless_epic_is_still_not_completable(solo):
    assert not solo.epic_completable(solo.get(epic(solo)))


def test_an_open_live_child_still_holds_the_epic(solo):
    e = epic(solo)
    gone = new(solo, "Gone", initiative=e)
    finish(solo, gone)
    elsewhere(solo, gone)
    new(solo, "Open", initiative=e)
    assert not solo.epic_completable(solo.get(e))


def test_a_child_repointed_before_it_resolved_counts_only_for_its_new_epic(solo):
    first, second = epic(solo), epic(solo)
    child = new(solo, "Child", initiative=first)
    solo.set_field(child, "initiative", second)
    finish(solo, child)
    elsewhere(solo, child)
    assert not solo.epic_completable(solo.get(first))
    assert solo.epic_completable(solo.get(second))


# ── criterion 4: counted once where both are present ────────────────────────

def test_the_resolving_checkout_counts_the_child_once(solo):
    e = epic(solo)
    child = new(solo, "Child", initiative=e)
    finish(solo, child)
    assert solo.get(child) is not None and solo.tombstone(child) is not None
    assert solo.resolved_initiative_children(e) == []    # the live item wins


# ── criterion 5: the record keeps the epic; a resolved child's epic is fixed ─

def test_deleting_a_resolved_folder_keeps_the_epic_in_its_record(tmp_path):
    root = node(tmp_path / "r", "r")
    cfg = yaml.safe_load((root / "tcw-config.yaml").read_text())
    cfg.setdefault("work", {})["retain"] = {"completed": False}
    (root / "tcw-config.yaml").write_text(yaml.safe_dump(cfg, sort_keys=False))
    ignore = root / ".gitignore"
    if ignore.exists():                                  # retention needs it tracked
        ignore.write_text("".join(line for line in ignore.read_text().splitlines(True)
                                  if "completed" not in line))
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(root), "commit", "-qm", "init"], check=True)
    st = FsWorkStore.open(root)
    e = epic(st)
    child = new(st, "Child", initiative=e)
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(root), "commit", "-qm", "items"], check=True)
    finish(st, child)
    st.delete_resolved(child)                            # what `complete` then does
    assert st.get(child) is None
    assert st.tombstone(child).initiative == e
    assert st.epic_completable(st.get(e))


def test_a_resolved_childs_epic_cannot_be_changed(solo):
    first, second = epic(solo), epic(solo)
    child = new(solo, "Child", initiative=first)
    finish(solo, child)
    with pytest.raises(ValueError, match="resolved"):
        solo.update_work(child, initiative=second)


# ── criterion 6: demoting ───────────────────────────────────────────────────

def test_an_epic_whose_only_child_is_gone_cannot_be_demoted(solo):
    e = epic(solo)
    child = new(solo, "Child", initiative=e)
    finish(solo, child)
    elsewhere(solo, child)
    with pytest.raises(ValueError, match=child):
        solo.update_work(e, type="")


# ── criterion 8: only a missing project below matters ───────────────────────

def _declare(root: Path, relation: str, pid: str, where: str) -> None:
    cfg = yaml.safe_load((root / "tcw-config.yaml").read_text())
    cfg.setdefault("connected-projects", {}).setdefault(relation, {})[pid] = where
    (root / "tcw-config.yaml").write_text(yaml.safe_dump(cfg, sort_keys=False))


def test_a_missing_parent_does_not_block_closing_or_demoting(tmp_path):
    root = node(tmp_path / "kid", "kid")
    _declare(root, "parent", "away", "../away")
    st = FsWorkStore.open(root)
    e = epic(st)
    child = new(st, "Child", initiative=e)
    finish(st, child)
    elsewhere(st, child)
    assert st.epic_completable(st.get(e))
    assert st.complete(e, "done", st.dod_checklist()).status == "completed"
    plain = epic(st)
    st.update_work(plain, type="")
    assert st.get(plain).type != "epic"


def test_a_missing_child_project_still_blocks_both(tmp_path):
    root = node(tmp_path / "top", "top")
    _declare(root, "children", "gone", "gone")
    st = FsWorkStore.open(root)
    e = epic(st)
    child = new(st, "Child", initiative=e)
    finish(st, child)
    assert not st.epic_completable(st.get(e))
    with pytest.raises(ValueError, match="gone"):
        st.update_work(epic(st), type="")


# ── criterion 9: an old record without the field ────────────────────────────

def test_an_old_tombstone_without_an_epic_changes_nothing(solo):
    e = epic(solo)
    child = new(solo, "Child", initiative=e)
    finish(solo, child)
    grave = solo.root / "graveyard.yaml"
    doc = yaml.safe_load(grave.read_text())
    doc[child].pop("initiative", None)
    grave.write_text(yaml.safe_dump(doc))
    elsewhere(solo, child)
    assert not solo.epic_completable(solo.get(e))
