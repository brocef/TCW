"""`tcw taxonomy rm` refuses a term a capability names, and a term with a child
the listing counts but git does not track
(spec: 2026-09-24-close-the-remaining-gaps-in-tcw-taxonomy-rm)."""

import subprocess
from pathlib import Path

import pytest
import yaml

from tcw.cli import main
from tcw.store.fs import FsTaxonomyStore, init
from nodeconfig import set_component_key


def git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)


def node(tmp_path: Path) -> Path:
    root = tmp_path / "node"
    root.mkdir()
    git(root, "init", "-q")
    git(root, "config", "user.email", "t@t")
    git(root, "config", "user.name", "t")
    init(["taxonomy", "capabilities"], root, "node")
    return root


def term(root: Path, slug: str, *, stage: bool = True) -> None:
    d = root / "docs" / "taxonomy" / slug
    d.mkdir(parents=True)
    (d / "meta.yaml").write_text(yaml.safe_dump({"name": slug.rsplit("/", 1)[-1]}))
    (d / "description.md").write_text("")
    if stage:
        git(root, "add", str(d))


def cap(root: Path, path: str, **fields) -> None:
    d = root / "docs" / "capabilities" / path
    d.mkdir(parents=True)
    (d / "meta.yaml").write_text(yaml.safe_dump(
        {"id": f"cap-{path}", "name": path, "Status": "Supported", **fields}))
    (d / "description.md").write_text("")
    git(root, "add", str(d))


def rm(root: Path, monkeypatch, capsys, slug: str) -> tuple[int, str]:
    monkeypatch.chdir(root)
    code = main(["taxonomy", "rm", slug])
    return code, capsys.readouterr().err


def lists(root: Path, slug: str) -> bool:
    return FsTaxonomyStore.open(root).get(slug) is not None


# ── a capability names the term ──────────────────────────────────────────────

@pytest.mark.parametrize("field, value", [("Subject", ["zed"]), ("Feature", "zed")])
def test_a_capability_naming_the_term_refuses_the_removal(tmp_path, monkeypatch, capsys,
                                                          field, value):
    root = node(tmp_path)
    term(root, "zed")
    cap(root, "login", **{field: value})
    code, err = rm(root, monkeypatch, capsys, "zed")
    assert code == 1 and "login" in err and field in err, err
    assert lists(root, "zed")


def test_a_capability_naming_another_term_does_not_block(tmp_path, monkeypatch, capsys):
    root = node(tmp_path)
    term(root, "zed")
    term(root, "other")
    cap(root, "login", Subject=["other"])
    code, err = rm(root, monkeypatch, capsys, "zed")
    assert code == 0, err
    assert not lists(root, "zed")


def test_an_unopenable_capabilities_store_refuses_the_removal(tmp_path, monkeypatch, capsys):
    root = node(tmp_path)
    term(root, "zed")
    set_component_key(root, "capabilities", "path", "nowhere")
    code, err = rm(root, monkeypatch, capsys, "zed")
    assert code == 1 and "nowhere" in err, err
    assert lists(root, "zed")


def test_a_node_without_capabilities_removes_as_before(tmp_path, monkeypatch, capsys):
    root = tmp_path / "node"
    root.mkdir()
    git(root, "init", "-q")
    init(["taxonomy"], root, "node")
    term(root, "zed")
    code, err = rm(root, monkeypatch, capsys, "zed")
    assert code == 0, err
    assert not lists(root, "zed")


# ── a child the listing counts but git does not track ────────────────────────

def test_an_unstaged_child_term_refuses_the_removal(tmp_path, monkeypatch, capsys):
    root = node(tmp_path)
    term(root, "zed")
    term(root, "zed/kid", stage=False)
    code, err = rm(root, monkeypatch, capsys, "zed")
    assert code == 1 and "zed/kid" in err and "git add" in err, err
    assert "Removed" not in err and lists(root, "zed") and lists(root, "zed/kid")


def test_os_metadata_is_removed_with_the_term(tmp_path, monkeypatch, capsys):
    """A file browser writes `.DS_Store` into any folder it opens. Refusing over
    it would make those terms unremovable, so it goes with the term — and the
    term, and a child folder holding only it, stop listing."""
    root = node(tmp_path)
    term(root, "zed")
    (root / "docs" / "taxonomy" / "zed" / ".DS_Store").write_text("x")
    junk = root / "docs" / "taxonomy" / "zed" / "kid"
    junk.mkdir()
    (junk / "Thumbs.db").write_text("x")
    code, err = rm(root, monkeypatch, capsys, "zed")
    assert code == 0, err
    assert not lists(root, "zed") and not lists(root, "zed/kid")


@pytest.mark.parametrize("where", ["notes.md", "kid/notes.md"])
def test_any_other_untracked_file_refuses_before_anything_is_removed(
        tmp_path, monkeypatch, capsys, where):
    root = node(tmp_path)
    term(root, "zed")
    stray = root / "docs" / "taxonomy" / "zed" / where
    stray.parent.mkdir(parents=True, exist_ok=True)
    stray.write_text("mine")
    code, err = rm(root, monkeypatch, capsys, "zed")
    assert code == 1 and f"zed/{where}" in err and "delete it" in err, err
    assert lists(root, "zed") and stray.exists()
    assert (root / "docs" / "taxonomy" / "zed" / "meta.yaml").exists()   # untouched


def test_a_term_never_staged_is_refused_in_tcw_words(tmp_path, monkeypatch, capsys):
    root = node(tmp_path)
    term(root, "zed", stage=False)
    code, err = rm(root, monkeypatch, capsys, "zed")
    assert code == 1 and "not tracked" in err, err
    assert "fatal:" not in err and lists(root, "zed")


# ── every caller: the guard is the store's, not the command's ────────────────

def test_the_store_refuses_for_any_caller(tmp_path):
    """The web app has no term-removal route today; anything that removes a term
    goes through `FsTaxonomyStore.remove`, which is where the guard lives."""
    root = node(tmp_path)
    term(root, "zed")
    cap(root, "login", Subject=["zed"])
    with pytest.raises(ValueError, match="capability login"):
        FsTaxonomyStore.open(root).remove("zed")
    assert lists(root, "zed")


# ── review fold-in: symlinks and a malformed capability ──────────────────────

def test_an_untracked_symlink_to_a_tracked_file_refuses_before_removing(tmp_path, monkeypatch, capsys):
    root = node(tmp_path)
    term(root, "zed")
    folder = root / "docs" / "taxonomy" / "zed"
    (folder / "alias.yaml").symlink_to("meta.yaml")
    code, err = rm(root, monkeypatch, capsys, "zed")
    assert code == 1 and "zed/alias.yaml" in err, err
    assert (folder / "meta.yaml").exists() and lists(root, "zed")


def test_a_tracked_symlink_does_not_vouch_for_its_untracked_target(tmp_path, monkeypatch, capsys):
    root = node(tmp_path)
    term(root, "zed")
    folder = root / "docs" / "taxonomy" / "zed"
    (folder / "mine.md").write_text("mine")
    (folder / "link.md").symlink_to("mine.md")
    git(root, "add", str(folder / "link.md"))
    code, err = rm(root, monkeypatch, capsys, "zed")
    assert code == 1 and "zed/mine.md" in err, err
    assert (folder / "meta.yaml").exists() and lists(root, "zed")


def test_a_malformed_capability_names_the_capabilities_check(tmp_path, monkeypatch, capsys):
    root = node(tmp_path)
    term(root, "zed")
    bad = root / "docs" / "capabilities" / "broken"
    bad.mkdir()
    (bad / "meta.yaml").write_text("Subject: [unclosed\n")
    code, err = rm(root, monkeypatch, capsys, "zed")
    assert code == 1 and "capabilities that might name it cannot be read" in err, err
    assert lists(root, "zed")
