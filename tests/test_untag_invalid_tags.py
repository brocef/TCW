"""`--untag` removes a tag the item holds as written, even one that is not a
valid tag (spec: 2026-09-27-let-untag-remove-a-tag-an-item-holds-that-is-not-a-valid-tag)."""

from tcw.store.fs import FsWorkStore
from test_item_tags_read import hand_tagged, run
from test_lifecycle_config_tags import node


def tags(root, slug):
    return FsWorkStore.open(root).get(slug).tags


def test_untag_removes_held_tags_that_are_not_valid_tags(tmp_path, monkeypatch, capsys):
    root = node(tmp_path, {"tags": ["cli", "docs"]})
    slug = hand_tagged(root, ["cli,docs", "!!!", "cli"])
    code, _out, err = run(root, monkeypatch, capsys, "work", "edit", slug, "--untag", "cli,docs")
    assert code == 0, err
    assert tags(root, slug) == ["!!!", "cli"]
    code, _out, err = run(root, monkeypatch, capsys, "work", "edit", slug, "--untag", "!!!")
    assert code == 0, err
    assert tags(root, slug) == ["cli"]


def test_a_comma_list_still_removes_each_tag(tmp_path, monkeypatch, capsys):
    root = node(tmp_path, {"tags": ["cli", "docs"]})
    slug = hand_tagged(root, ["cli", "docs"])
    code, _out, err = run(root, monkeypatch, capsys, "work", "edit", slug, "--untag", "cli,docs")
    assert code == 0, err
    assert tags(root, slug) == []


def test_an_invalid_value_the_item_does_not_hold_is_refused(tmp_path, monkeypatch, capsys):
    root = node(tmp_path, {"tags": ["cli"]})
    slug = hand_tagged(root, ["cli"])
    code, _out, err = run(root, monkeypatch, capsys, "work", "edit", slug, "--untag", "!!!")
    assert code == 1 and "invalid tag" in err, err
    assert tags(root, slug) == ["cli"]


# ── an edit is refused for what it adds, never for what the item holds ──────

def test_tagging_an_item_that_holds_an_invalid_tag_keeps_it(tmp_path, monkeypatch, capsys):
    root = node(tmp_path, {"tags": ["cli", "docs"]})
    slug = hand_tagged(root, ["cli,docs"])
    code, _out, err = run(root, monkeypatch, capsys, "work", "edit", slug, "--tag", "docs")
    assert code == 0, err
    assert tags(root, slug) == ["cli,docs", "docs"]


def test_a_save_resending_the_held_tags_succeeds(tmp_path):
    root = node(tmp_path, {"tags": ["cli"]})
    slug = hand_tagged(root, ["!!!", "cli"])
    st = FsWorkStore.open(root)
    st.update_work(slug, tags=["!!!", "cli"], title="Renamed")
    assert (st.get(slug).title, st.get(slug).tags) == ("Renamed", ["!!!", "cli"])


def test_adding_an_invalid_tag_is_still_refused(tmp_path):
    import pytest
    root = node(tmp_path, {"tags": ["cli"]})
    slug = hand_tagged(root, ["cli"])
    with pytest.raises(ValueError, match="holds several tags"):
        FsWorkStore.open(root).update_work(slug, tags=["cli", "cli,docs"])


def test_a_held_tag_later_unregistered_is_kept_and_still_reported(tmp_path, monkeypatch, capsys):
    """"Refused for what it adds" covers an unregistered tag too: the edit
    succeeds, and `check` still names the tag."""
    root = node(tmp_path, {"tags": ["docs"]})
    slug = hand_tagged(root, ["cli"])
    code, _out, err = run(root, monkeypatch, capsys, "work", "edit", slug, "--tag", "docs")
    assert code == 0, err
    assert tags(root, slug) == ["cli", "docs"]
    assert any("unregistered tag 'cli'" in p for p in FsWorkStore.open(root).check())


def test_an_exact_held_match_is_removed_as_written_and_not_split(tmp_path, monkeypatch, capsys):
    root = node(tmp_path, {"tags": ["cli", "docs"]})
    slug = hand_tagged(root, ["cli,docs", "cli", "docs"])
    code, _out, err = run(root, monkeypatch, capsys, "work", "edit", slug, "--untag", "cli,docs")
    assert code == 0, err
    assert tags(root, slug) == ["cli", "docs"]
