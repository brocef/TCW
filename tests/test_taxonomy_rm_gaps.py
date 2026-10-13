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
from tcw.errors import TcwError


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
    assert code == 3 and "login" in err and field in err, err
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
    assert code == 3 and "nowhere" in err, err
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

def test_a_child_term_refuses_the_removal_whatever_git_knows(tmp_path, monkeypatch, capsys):
    """A nested term is a folder holding a `meta.yaml`, decided from the disk
    (TCW-73 Design 8.2): one never added to git refuses like any other."""
    root = node(tmp_path)
    term(root, "zed")
    term(root, "zed/kid", stage=False)
    code, err = rm(root, monkeypatch, capsys, "zed")
    assert code == 3 and "nested under it: zed/kid" in err, err
    assert lists(root, "zed") and lists(root, "zed/kid")


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
def test_any_other_file_goes_with_the_term(tmp_path, monkeypatch, capsys, where):
    root = node(tmp_path)
    term(root, "zed")
    stray = root / "docs" / "taxonomy" / "zed" / where
    stray.parent.mkdir(parents=True, exist_ok=True)
    stray.write_text("mine")
    code, err = rm(root, monkeypatch, capsys, "zed")
    assert code == 0, err
    assert not lists(root, "zed") and not stray.exists()


def test_a_term_never_added_to_git_is_removed(tmp_path, monkeypatch, capsys):
    root = node(tmp_path)
    term(root, "zed", stage=False)
    code, err = rm(root, monkeypatch, capsys, "zed")
    assert code == 0, err
    assert not lists(root, "zed")


# ── every caller: the guard is the store's, not the command's ────────────────

def test_the_store_refuses_for_any_caller(tmp_path):
    """The web app has no term-removal route today; anything that removes a term
    goes through `FsTaxonomyStore.remove`, which is where the guard lives."""
    root = node(tmp_path)
    term(root, "zed")
    cap(root, "login", Subject=["zed"])
    with pytest.raises(TcwError, match="capability login"):
        FsTaxonomyStore.open(root).remove("zed")
    assert lists(root, "zed")


# ── review fold-in: a malformed capability ───────────────────────────────────

def test_a_malformed_capability_names_the_capabilities_check(tmp_path, monkeypatch, capsys):
    root = node(tmp_path)
    term(root, "zed")
    bad = root / "docs" / "capabilities" / "broken"
    bad.mkdir()
    (bad / "meta.yaml").write_text("Subject: [unclosed\n")
    code, err = rm(root, monkeypatch, capsys, "zed")
    assert code == 3 and "capabilities that might name it cannot be read" in err, err
    assert lists(root, "zed")


# ── review fix S1: a sub-folder without a meta.yaml still lists as a term ────

def test_a_reference_to_a_folder_under_the_term_refuses_the_removal(
        tmp_path, monkeypatch, capsys):
    """`taxonomy list` counts a folder with no `meta.yaml` as a term, so a
    capability can name `zed/sub`. Removing `zed` would delete that folder and
    leave the capability pointing at nothing, so the removal is refused."""
    root = node(tmp_path)
    term(root, "zed")
    sub = root / "docs" / "taxonomy" / "zed" / "sub"
    sub.mkdir()
    (sub / "f").write_text("x")
    assert lists(root, "zed/sub")
    cap(root, "pay", Subject=["zed/sub"])
    code, err = rm(root, monkeypatch, capsys, "zed")
    assert code == 3 and "capability pay (Subject)" in err, err
    assert lists(root, "zed") and lists(root, "zed/sub")


def test_a_term_naming_a_folder_under_the_term_refuses_the_removal(
        tmp_path, monkeypatch, capsys):
    root = node(tmp_path)
    term(root, "zed")
    (root / "docs" / "taxonomy" / "zed" / "sub").mkdir()
    term(root, "other")
    meta = root / "docs" / "taxonomy" / "other" / "meta.yaml"
    meta.write_text(yaml.safe_dump({"name": "other", "relatesTo": ["zed/sub"]}))
    code, err = rm(root, monkeypatch, capsys, "zed")
    assert code == 3 and "other (relatesTo)" in err, err
