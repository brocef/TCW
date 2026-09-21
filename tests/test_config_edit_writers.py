"""The commands that write `tcw-config.yaml` change only their own key's lines,
or refuse and leave everything alone (spec:
2026-09-21-keep-comments-and-formatting-when-tcw-writes-a-key-into-tcw-config-yaml).

Every comparison reads raw bytes, because a text read would translate `\\r\\n`
and hide exactly the loss a test here exists to catch. The text-level rules are
`tests/test_config_edit.py`.
"""

import subprocess
from pathlib import Path

import pytest
import yaml

from tcw.cli import main
from tcw.store.fs import FsTaxonomyStore, init, write_sentinel

PARENT = ("id: child\nconnected-projects:\n    parent:\n        base: ../base\n"
          "    children:\n        other: ../other\n")


def git(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(root), *args], check=True,
                          capture_output=True, text=True)


def repository(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    git(root, "init", "-q")
    git(root, "config", "user.email", "t@t")
    git(root, "config", "user.name", "t")
    return root


def commit_all(root: Path) -> None:
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "fixture", "--allow-empty")


def federated(tmp_path: Path, child_config: bytes) -> Path:
    """Registered `base` and `other` projects and a `child` whose config is
    exactly `child_config`, all with taxonomy and capabilities trees, committed
    so the index starts clean."""
    base = repository(tmp_path / "base")
    other = repository(tmp_path / "other")
    child = repository(tmp_path / "child")
    for root in (base, other, child):
        for tree in ("taxonomy", "capabilities"):
            (root / "docs" / tree).mkdir(parents=True)
            (root / "docs" / tree / ".gitkeep").touch()
    (base / "tcw-config.yaml").write_text(
        "id: base\nconnected-projects:\n  children:\n    child: ../child\n")
    (other / "tcw-config.yaml").write_text(
        "id: other\nconnected-projects:\n  parent:\n    child: ../child\n")
    (child / "tcw-config.yaml").write_bytes(child_config)
    commit_all(other)
    commit_all(base)
    commit_all(child)
    return child


def work_node(tmp_path: Path, config: bytes) -> Path:
    root = repository(tmp_path / "node")
    init(["work"], root, "node")
    (root / "tcw-config.yaml").write_bytes(config)
    commit_all(root)
    return root


def run(root: Path, monkeypatch, *argv: str) -> int:
    monkeypatch.chdir(root)
    return main(list(argv))


def config(root: Path) -> bytes:
    return (root / "tcw-config.yaml").read_bytes()


def assert_only_added(before: bytes, after: bytes, *added: bytes) -> None:
    """`after` is `before` with exactly the lines `added` inserted."""
    remaining = after.splitlines(keepends=True)
    for line in added:
        assert line in remaining, f"{line!r} not added:\n{after.decode()}"
        remaining.remove(line)
    assert remaining == before.splitlines(keepends=True), after.decode()


def assert_only_removed(before: bytes, after: bytes, *removed: bytes) -> None:
    assert_only_added(after, before, *removed)


def assert_refused_leaving_everything(root: Path, before: bytes, code: int, capsys,
                                      *expected: str) -> str:
    """The one assertion every refusal goes through: non-zero exit, the file's
    bytes untouched, nothing staged, and the refusal — not some other error —
    is what was printed."""
    err = capsys.readouterr().err
    assert code != 0, err
    assert config(root) == before
    assert subprocess.run(["git", "-C", str(root), "diff", "--cached", "--quiet"]).returncode == 0
    assert "would lose its comments and formatting" in err, err
    for text in expected:
        assert text in err, err
    return err


# ── extends ──────────────────────────────────────────────────────────────────

ANNOTATED = (PARENT + """\
# Our own taxonomy lives beside the code.
taxonomy:
    path: docs/taxonomy   # moved here in 2.3
work:
    lifecycle:
        # the spec stage runs our checklist first
        spec: [checklist]
    tracker:
        candidate-query: "project = WEB AND status in ('To Do', 'In Progress') AND labels = tcw ORDER BY rank"
# end of file
""").encode()


def test_taxonomy_extends_add_changes_only_its_own_lines(tmp_path, monkeypatch):
    child = federated(tmp_path, ANNOTATED)
    assert run(child, monkeypatch, "taxonomy", "extends", "add", "base") == 0
    assert_only_added(ANNOTATED, config(child), b"    extends:\n", b"        - base\n")


def test_capabilities_extends_appends_a_missing_section(tmp_path, monkeypatch):
    child = federated(tmp_path, ANNOTATED)
    assert run(child, monkeypatch, "capabilities", "extends", "base") == 0
    assert config(child) == ANNOTATED + b"capabilities:\n    extends:\n        - base\n"


def test_capabilities_extends_goes_before_a_document_end_marker(tmp_path, monkeypatch):
    before = (PARENT + "...\n").encode()
    child = federated(tmp_path, before)
    assert run(child, monkeypatch, "capabilities", "extends", "base") == 0
    assert config(child) == (PARENT + "capabilities:\n    extends:\n"
                             "        - base\n...\n").encode()


def test_taxonomy_extends_rm_removes_only_that_line_then_the_key(tmp_path, monkeypatch):
    before = (PARENT + "taxonomy:\n    path: docs/taxonomy\n    # inherited\n"
              "    extends:\n        - base\n        - other  # kept\n").encode()
    child = federated(tmp_path, before)
    assert run(child, monkeypatch, "taxonomy", "extends", "rm", "base") == 0
    after_one = config(child)
    assert_only_removed(before, after_one, b"        - base\n")
    assert run(child, monkeypatch, "taxonomy", "extends", "rm", "other") == 0
    assert config(child) == (PARENT + "taxonomy:\n    path: docs/taxonomy\n"
                             "    # inherited\n").encode()


def test_extends_add_on_a_stub_section_keeps_its_comments(tmp_path, monkeypatch):
    before = (PARENT + "taxonomy:\n    # extends:\n    #     - old-name\n").encode()
    child = federated(tmp_path, before)
    assert run(child, monkeypatch, "taxonomy", "extends", "add", "base") == 0
    assert config(child) == (PARENT + "taxonomy:\n    extends:\n        - base\n"
                             "    # extends:\n    #     - old-name\n").encode()


def test_extends_add_on_an_empty_key_keeps_its_comment(tmp_path, monkeypatch):
    before = (PARENT + "taxonomy:\n    extends: # filled in by tcw\n"
              "    path: docs/taxonomy\n").encode()
    child = federated(tmp_path, before)
    assert run(child, monkeypatch, "taxonomy", "extends", "add", "base") == 0
    assert config(child) == (PARENT + "taxonomy:\n    extends: # filled in by tcw\n"
                             "        - base\n    path: docs/taxonomy\n").encode()


def test_extends_add_into_a_brace_section_is_refused(tmp_path, monkeypatch, capsys):
    before = (PARENT + "taxonomy: {path: docs/taxonomy}\n").encode()
    child = federated(tmp_path, before)
    code = run(child, monkeypatch, "taxonomy", "extends", "add", "base")
    assert_refused_leaving_everything(child, before, code, capsys,
                                      "inside the braces", ", extends: [base]")


def test_extends_rm_over_an_aliased_anchor_is_refused(tmp_path, monkeypatch, capsys):
    before = (PARENT + "taxonomy:\n    extends: &ids [base]\n"
              "capabilities:\n    extends: *ids\n").encode()
    child = federated(tmp_path, before)
    code = run(child, monkeypatch, "taxonomy", "extends", "rm", "base")
    assert_refused_leaving_everything(child, before, code, capsys, "taxonomy.extends")


def test_a_refused_extends_add_leaves_the_store_object_unchanged(tmp_path):
    before = (PARENT + "taxonomy: {path: docs/taxonomy}\n").encode()
    child = federated(tmp_path, before)
    store = FsTaxonomyStore.open(child)
    with pytest.raises(ValueError, match="would lose its comments"):
        store.extends_add("base")
    assert "extends" not in store.config
    (child / "tcw-config.yaml").write_bytes(
        (PARENT + "taxonomy:\n    path: docs/taxonomy\n").encode())
    store.extends_add("base")
    assert store.config["extends"] == ["base"]
    assert yaml.safe_load(config(child))["taxonomy"]["extends"] == ["base"]


# ── tags ─────────────────────────────────────────────────────────────────────

def test_tags_add_to_a_flow_list_keeps_it_on_its_line(tmp_path, monkeypatch):
    before = b"id: node\n# registered tags\nwork:\n    tags: [alpha, gamma]  # sorted\n"
    root = work_node(tmp_path, before)
    assert run(root, monkeypatch, "work", "tags", "add", "beta") == 0
    assert config(root) == before.replace(b"[alpha, gamma]", b"[alpha, beta, gamma]")


def test_tags_add_and_rm_on_a_commented_block_list(tmp_path, monkeypatch):
    before = (b"id: node\nwork:\n    tags:\n        - alpha  # first\n"
              b"        # the rest are areas\n        - gamma  # last\n")
    root = work_node(tmp_path, before)
    assert run(root, monkeypatch, "work", "tags", "add", "beta") == 0
    assert_only_added(before, config(root), b"        - beta\n")
    added = config(root)
    assert run(root, monkeypatch, "work", "tags", "rm", "beta") == 0
    assert config(root) == before
    assert added != before


def test_tags_add_where_work_has_no_tags(tmp_path, monkeypatch):
    before = b"id: node\nwork:\n    auto-commit-transitions: false  # we commit by hand\n"
    root = work_node(tmp_path, before)
    assert run(root, monkeypatch, "work", "tags", "add", "bug") == 0
    assert_only_added(before, config(root), b"    tags:\n", b"        - bug\n")


def test_tags_add_of_a_registered_tag_writes_and_stages_nothing(tmp_path, monkeypatch):
    before = b"id: node\nwork:\n  tags: [bug]\n"
    root = work_node(tmp_path, before)
    mtime = (root / "tcw-config.yaml").stat().st_mtime_ns
    assert run(root, monkeypatch, "work", "tags", "add", "bug") == 0
    assert config(root) == before
    assert (root / "tcw-config.yaml").stat().st_mtime_ns == mtime
    assert subprocess.run(["git", "-C", str(root), "diff", "--cached", "--quiet"]).returncode == 0


def test_an_unsorted_tag_list_is_sorted_only_when_it_has_no_comments(tmp_path, monkeypatch, capsys):
    before = b"id: node\nwork:\n  tags:\n  - gamma\n  - alpha\n  path: docs/work\n"
    root = work_node(tmp_path, before)
    assert run(root, monkeypatch, "work", "tags", "add", "beta") == 0
    assert config(root) == (b"id: node\nwork:\n  tags:\n  - alpha\n  - beta\n  - gamma\n"
                            b"  path: docs/work\n")
    commented = b"id: node\nwork:\n  tags:\n  - gamma  # why\n  - alpha\n  path: docs/work\n"
    (root / "tcw-config.yaml").write_bytes(commented)
    commit_all(root)
    code = run(root, monkeypatch, "work", "tags", "add", "beta")
    assert_refused_leaving_everything(root, commented, code, capsys,
                                      "do not add a second one")


def test_windows_line_endings_and_a_byte_order_mark_survive(tmp_path, monkeypatch):
    before = "﻿id: node\r\n# tags\r\nwork:\r\n  tags:\r\n  - alpha\r\n".encode()
    root = work_node(tmp_path, before)
    assert run(root, monkeypatch, "work", "tags", "add", "beta") == 0
    assert config(root) == before + b"  - beta\r\n"


def test_a_file_without_a_final_line_break(tmp_path, monkeypatch):
    before = b"id: node\nwork:\n  tags: [a]"
    root = work_node(tmp_path, before)
    assert run(root, monkeypatch, "work", "tags", "add", "b") == 0
    assert config(root) == b"id: node\nwork:\n  tags: [a, b]"


def test_tags_add_on_an_alias_is_refused(tmp_path, monkeypatch, capsys):
    before = b"id: node\nshared: &t [a]\nwork:\n  tags: *t\n"
    root = work_node(tmp_path, before)
    code = run(root, monkeypatch, "work", "tags", "add", "b")
    assert_refused_leaving_everything(root, before, code, capsys, "is an alias")


def test_tags_add_with_a_scalar_work_section_is_refused(tmp_path, monkeypatch, capsys):
    before = b"id: node\nwork: docs/work\n"
    root = work_node(tmp_path, before)
    code = run(root, monkeypatch, "work", "tags", "add", "b")
    err = capsys.readouterr().err
    assert code != 0
    assert config(root) == before
    assert "work must be a mapping" in err and "tcw-config.yaml" in err
