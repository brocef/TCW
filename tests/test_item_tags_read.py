"""An item's tags are read in canonical form, and the tag registry refuses a
write that would drop an entry that is not a tag
(spec: 2026-09-26-read-item-tags-normalized-and-keep-non-tag-work-tags-entries-visible)."""

from pathlib import Path

import pytest

from tcw.cli import main

from test_lifecycle_config_tags import node


def run(root: Path, monkeypatch, capsys, *argv: str) -> tuple[int, str, str]:
    monkeypatch.chdir(root)
    capsys.readouterr()
    code = main(list(argv))
    out, err = capsys.readouterr()
    return code, out, err


# ── criteria 1-3: a hand-written spelling reads as the tag ──────────────────


# ── criteria 4-5: what cannot be a tag is still read, as its text ───────────


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


# ── criterion 7: a clean registry still changes ─────────────────────────────

def test_a_clean_registry_still_adds_and_removes(tmp_path, monkeypatch, capsys):
    root = node(tmp_path, {"tags": ["cli"]})
    code, out, err = run(root, monkeypatch, capsys, "work", "tags", "add", "docs")
    assert code == 0 and out.split() == ["cli", "docs"], err
    code, out, err = run(root, monkeypatch, capsys, "work", "tags", "rm", "docs")
    assert code == 0 and out.split() == ["cli"], err


# ── review fold-ins ──────────────────────────────────────────────────────────


