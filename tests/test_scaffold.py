"""`write_draft` and `tcw work scaffold` — drafts, and everything they are not.

A draft is a file to type into. It is never the artifact: no surface reports it,
and `scaffold` refuses rather than overwrite either the real artifact or a draft
someone has already started.
"""

import subprocess
from pathlib import Path

import pytest
import yaml

from tcw.store.base import WORK_ARTIFACTS
from tcw.store.fs import FsWorkStore, init


def _node(tmp_path: Path, name: str = "repo") -> Path:
    root = tmp_path / name
    root.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "t"], check=True)
    init(["work"], root, name.lower())
    return root


def _configure(root: Path, lifecycle: dict) -> None:
    cfg_path = root / "tcw-config.yaml"
    cfg = yaml.safe_load(cfg_path.read_text()) or {}
    cfg.setdefault("work", {})["lifecycle"] = lifecycle
    cfg_path.write_text(yaml.safe_dump(cfg, sort_keys=False))


@pytest.fixture
def item(tmp_path):
    """A node with one backlog item."""
    root = _node(tmp_path)
    st = FsWorkStore.open(root)
    return root, st, st.create("Thing", body="req\n").slug


# ── the store method ─────────────────────────────────────────────────────────


def test_write_draft_writes_the_file_and_returns_its_locator(item):
    _root, st, slug = item
    locator = st.write_draft(slug, "spec", "# Draft\n")
    assert Path(locator).read_text() == "# Draft\n"


def test_write_draft_refuses_a_present_draft_and_leaves_it_alone(item):
    _root, st, slug = item
    locator = st.write_draft(slug, "spec", "typed by hand\n")
    with pytest.raises(ValueError) as e:
        st.write_draft(slug, "spec", "clobbered\n")
    assert locator in str(e.value)
    assert Path(locator).read_text() == "typed by hand\n"


def test_force_overwrites_a_present_draft(item):
    _root, st, slug = item
    locator = st.write_draft(slug, "spec", "typed by hand\n")
    st.write_draft(slug, "spec", "regenerated\n", force=True)
    assert Path(locator).read_text() == "regenerated\n"


def test_an_empty_draft_is_not_present_and_needs_no_force(item):
    """The canonical presence rule, not `.exists()` — which is what makes
    `intake`, whose template is empty, work with no carve-out."""
    _root, st, slug = item
    locator = st.write_draft(slug, "intake", "")
    assert Path(locator).is_file()
    st.write_draft(slug, "intake", "now with content\n")
    assert Path(locator).read_text() == "now with content\n"


def test_an_unknown_artifact_name_raises_naming_the_legal_set(item):
    _root, st, slug = item
    with pytest.raises(ValueError) as e:
        st.write_draft(slug, "speck", "x")
    assert "speck" in str(e.value)
    assert all(name in str(e.value) for name in WORK_ARTIFACTS)


def test_a_draft_never_lands_on_the_artifact(item):
    _root, st, slug = item
    st.write_draft(slug, "spec", "# Draft\n")
    assert st.read_artifact(slug, "spec") is None
    assert {a.name for a in st.artifacts(slug) if a.present} == {"initial-request"}
