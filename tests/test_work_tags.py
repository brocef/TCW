"""Tags on work items: per-node registry + apply/filter/validate (spec:
2026-07-17-add-tags-to-work-items-for-filtering)."""

import subprocess
from pathlib import Path

import pytest

from tcw.cli import main
from tcw.store.base import normalize_tag
from tcw.store.fs import FsWorkStore, init
from tcw.validate import validate


def node(tmp_path: Path, name: str = "repo") -> Path:
    root = tmp_path / name
    root.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "t"], check=True)
    init(["work"], root)
    return root


# ── normalize ────────────────────────────────────────────────────────────────

def test_normalize_tag_slugifies():
    assert normalize_tag("Bug") == "bug"
    assert normalize_tag("  Tech Debt ") == "tech-debt"


def test_normalize_tag_rejects_empty():
    with pytest.raises(ValueError):
        normalize_tag("  ")


# ── registry round-trip ──────────────────────────────────────────────────────

def test_registered_tags_empty_by_default(tmp_path):
    st = FsWorkStore.open(node(tmp_path))
    assert st.registered_tags() == []


def test_register_normalizes_dedups_sorts_and_persists(tmp_path):
    root = node(tmp_path)
    st = FsWorkStore.open(root)
    assert st.register_tags(["Bug", "tech-debt", "bug"]) == ["bug", "tech-debt"]
    # persisted: a fresh store sees them
    assert FsWorkStore.open(root).registered_tags() == ["bug", "tech-debt"]
    # idempotent
    assert st.register_tags(["bug"]) == ["bug", "tech-debt"]


def test_registered_tags_tolerates_non_dict_work_config(tmp_path):
    root = node(tmp_path)
    (root / "tcw-config.yaml").write_text("work: enabled\n")   # hand-edited to a scalar
    assert FsWorkStore.open(root).registered_tags() == []      # no crash


def test_malformed_config_raises_clear_error(tmp_path):
    root = node(tmp_path)
    (root / "tcw-config.yaml").write_text("- just\n- a\n- list\n")  # valid YAML, wrong shape
    with pytest.raises(ValueError, match="malformed"):
        FsWorkStore.open(root).registered_tags()


def test_unregister(tmp_path):
    st = FsWorkStore.open(node(tmp_path))
    st.register_tags(["bug", "tech-debt"])
    assert st.unregister_tags(["bug"]) == ["tech-debt"]
    assert st.registered_tags() == ["tech-debt"]


# ── apply on create / update ─────────────────────────────────────────────────

def test_create_with_registered_tag(tmp_path):
    st = FsWorkStore.open(node(tmp_path))
    st.register_tags(["bug"])
    detail = st.create_work("X", created="2026-01-01", tags=["Bug"])
    assert detail.item.tags == ["bug"]
    assert st.get(detail.item.slug).tags == ["bug"]


def test_create_with_unregistered_tag_rejected_and_creates_nothing(tmp_path):
    st = FsWorkStore.open(node(tmp_path))
    with pytest.raises(ValueError):
        st.create_work("Y", created="2026-01-01", tags=["nope"])
    assert st.query() == []


def test_update_add_and_remove_tags(tmp_path):
    st = FsWorkStore.open(node(tmp_path))
    st.register_tags(["bug", "urgent"])
    slug = st.create_work("Z", created="2026-01-01", tags=["bug"]).item.slug
    st.update_work(slug, tags=["urgent"])
    assert st.get(slug).tags == ["urgent"]


def test_update_unregistered_tag_rejected(tmp_path):
    st = FsWorkStore.open(node(tmp_path))
    slug = st.create_work("Z", created="2026-01-01").item.slug
    with pytest.raises(ValueError):
        st.update_work(slug, tags=["nope"])


def test_tagless_item_omits_tags_key(tmp_path):
    root = node(tmp_path)
    st = FsWorkStore.open(root)
    slug = st.create_work("plain", created="2026-01-01").item.slug
    state = (st.path(slug) / "state.yaml").read_text()
    assert "tags" not in state
    assert st.get(slug).tags == []


# ── validation ───────────────────────────────────────────────────────────────

def test_check_flags_stale_tag(tmp_path):
    root = node(tmp_path)
    st = FsWorkStore.open(root)
    st.register_tags(["bug"])
    slug = st.create_work("stale", created="2026-01-01", tags=["bug"]).item.slug
    st.unregister_tags(["bug"])            # tag now stale on the item
    problems = st.check()
    assert any(slug in p and "bug" in p for p in problems)
    # surfaced through the aggregate validate() pass too
    assert any("work check" in p and slug in p for p in validate(root))


def test_validate_reports_malformed_config_without_crashing(tmp_path):
    root = node(tmp_path)
    (root / "tcw-config.yaml").write_text("- not\n- a\n- mapping\n")
    problems = validate(root)                          # must not raise
    assert any("project graph" in p and "config must be a mapping" in p for p in problems)


# ── CLI end-to-end ───────────────────────────────────────────────────────────

def test_cli_register_apply_list_filter(tmp_path, monkeypatch, capsys):
    root = node(tmp_path)
    monkeypatch.chdir(root)
    assert main(["work", "tags", "add", "bug"]) == 0
    capsys.readouterr()
    assert main(["work", "new", "Boom", "--tag", "bug"]) == 0
    slug = capsys.readouterr().out.strip().splitlines()[0]
    state = (FsWorkStore.open(root).path(slug) / "state.yaml").read_text()
    assert "tags:" in state and "bug" in state

    assert main(["work", "list", "--tag", "bug"]) == 0
    assert slug in capsys.readouterr().out
    assert main(["work", "list", "--tag", "other"]) == 0
    assert slug not in capsys.readouterr().out


def test_cli_new_unregistered_tag_fails(tmp_path, monkeypatch, capsys):
    root = node(tmp_path)
    monkeypatch.chdir(root)
    assert main(["work", "new", "Nope", "--tag", "ghost"]) == 1
    assert "unregistered tag" in capsys.readouterr().err
    assert FsWorkStore.open(root).query() == []


def test_cli_edit_tag_and_untag(tmp_path, monkeypatch, capsys):
    root = node(tmp_path)
    st = FsWorkStore.open(root)
    st.register_tags(["bug", "urgent"])
    slug = st.create_work("E", created="2026-01-01", tags=["bug"]).item.slug
    monkeypatch.chdir(root)
    assert main(["work", "edit", slug, "--tag", "urgent", "--untag", "bug"]) == 0
    assert FsWorkStore.open(root).get(slug).tags == ["urgent"]
    capsys.readouterr()
    assert main(["work", "show", slug]) == 0
    assert "tags: urgent" in capsys.readouterr().out


def test_cli_tags_rm_warns_about_stale_items(tmp_path, monkeypatch, capsys):
    root = node(tmp_path)
    st = FsWorkStore.open(root)
    st.register_tags(["bug"])
    slug = st.create_work("S", created="2026-01-01", tags=["bug"]).item.slug
    monkeypatch.chdir(root)
    assert main(["work", "tags", "rm", "bug"]) == 0
    assert slug in capsys.readouterr().err
