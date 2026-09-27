"""An item's tags are read in canonical form, and the tag registry refuses a
write that would drop an entry that is not a tag
(spec: 2026-09-26-read-item-tags-normalized-and-keep-non-tag-work-tags-entries-visible)."""

from pathlib import Path

import pytest
import yaml

from tcw.cli import main
from tcw.store.base import _parse_condition
from tcw.store.fs import FsWorkStore

from test_lifecycle_config_tags import node


def hand_tagged(root: Path, tags) -> str:
    """An item whose `state.yaml` a person edited to hold `tags` as written."""
    slug = FsWorkStore.open(root).create("Hand tagged", created="2026-01-01").slug
    state = next(root.rglob(f"{slug}/state.yaml"))
    data = yaml.safe_load(state.read_text())
    data["tags"] = tags
    state.write_text(yaml.safe_dump(data, sort_keys=False))
    return slug


def run(root: Path, monkeypatch, capsys, *argv: str) -> tuple[int, str, str]:
    monkeypatch.chdir(root)
    capsys.readouterr()
    code = main(list(argv))
    out, err = capsys.readouterr()
    return code, out, err


# ── criteria 1-3: a hand-written spelling reads as the tag ──────────────────

def test_hand_written_tags_read_normalized_deduplicated_in_order(tmp_path):
    root = node(tmp_path, {"tags": ["cli", "docs-only"]})
    slug = hand_tagged(root, ["CLI", "cli", "Docs Only"])
    st = FsWorkStore.open(root)
    assert st.get(slug).tags == ["cli", "docs-only"]
    assert [i.tags for i in st.query() if i.slug == slug] == [["cli", "docs-only"]]


def test_a_condition_matches_and_check_is_quiet(tmp_path):
    root = node(tmp_path, {"tags": ["cli", "docs-only"]})
    slug = hand_tagged(root, ["CLI", "Docs Only"])
    st = FsWorkStore.open(root)
    cond = _parse_condition({"tags": ["CLI"]}, "w", [])
    assert cond.matches(st.get(slug))
    assert [p for p in st.check() if "tag" in p] == []


def test_list_filter_and_untag_reach_a_hand_written_tag(tmp_path, monkeypatch, capsys):
    root = node(tmp_path, {"tags": ["cli", "docs-only"]})
    slug = hand_tagged(root, ["CLI", "Docs Only"])
    code, out, err = run(root, monkeypatch, capsys, "work", "list", "--tag", "cli")
    assert code == 0 and slug in out, err
    code, _out, err = run(root, monkeypatch, capsys, "work", "edit", slug, "--untag", "cli")
    assert code == 0, err
    assert FsWorkStore.open(root).get(slug).tags == ["docs-only"]
    state = next(root.rglob(f"{slug}/state.yaml"))
    assert yaml.safe_load(state.read_text())["tags"] == ["docs-only"]


# ── criteria 4-5: what cannot be a tag is still read, as its text ───────────

def test_an_entry_that_cannot_be_a_tag_is_read_as_text_and_reported(tmp_path, monkeypatch,
                                                                    capsys):
    root = node(tmp_path, {"tags": ["cli"]})
    slug = hand_tagged(root, [7, "cli,docs", "!!!"])
    st = FsWorkStore.open(root)
    assert st.get(slug).tags == ["7", "cli,docs", "!!!"]
    code, _out, err = run(root, monkeypatch, capsys, "work", "show", slug)
    assert code == 0, err
    problems = st.check()
    for tag in ("7", "cli,docs", "!!!"):
        assert f"{slug}: unregistered tag '{tag}'" in problems, problems


def test_a_single_tag_written_without_a_list_is_one_tag(tmp_path):
    root = node(tmp_path, {"tags": ["cli"]})
    slug = hand_tagged(root, "CLI")
    assert FsWorkStore.open(root).get(slug).tags == ["cli"]


# ── criteria 6, 9, 10: the registry refuses to drop what is not a tag ───────

@pytest.mark.parametrize("entry, named", [
    (7, "7"),
    ({"a": 1}, "{'a': 1}"),
    ("cli,docs", "'cli,docs'"),
])
@pytest.mark.parametrize("verb", ["add", "rm"])
def test_tags_add_and_rm_refuse_while_the_registry_holds_a_non_tag(
        tmp_path, monkeypatch, capsys, entry, named, verb):
    root = node(tmp_path, {"tags": ["cli", entry]})
    config = root / "tcw-config.yaml"
    before = config.read_bytes()
    code, _out, err = run(root, monkeypatch, capsys, "work", "tags", verb,
                          "docs" if verb == "add" else "cli")
    assert code == 1, err
    assert named in err and "not a tag" in err, err
    assert config.read_bytes() == before


def test_check_reports_a_registry_entry_holding_a_comma(tmp_path):
    root = node(tmp_path, {"tags": ["cli", "cli,docs"]})
    st = FsWorkStore.open(root)
    assert "tcw-config.yaml: work.tags entry 'cli,docs' is not a tag" in st.check()
    assert st.registered_tags() == ["cli"]


# ── criterion 7: a clean registry still changes ─────────────────────────────

def test_a_clean_registry_still_adds_and_removes(tmp_path, monkeypatch, capsys):
    root = node(tmp_path, {"tags": ["cli"]})
    code, out, err = run(root, monkeypatch, capsys, "work", "tags", "add", "docs")
    assert code == 0 and out.split() == ["cli", "docs"], err
    code, out, err = run(root, monkeypatch, capsys, "work", "tags", "rm", "docs")
    assert code == 0 and out.split() == ["cli"], err
