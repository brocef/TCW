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
    assert git(root, "status", "--porcelain").stdout == ""
    assert "work must be a mapping" in err and "tcw-config.yaml" in err


# ── init and write_sentinel ──────────────────────────────────────────────────

def test_init_writes_only_the_id_and_path_lines(tmp_path):
    root = repository(tmp_path / "node")
    before = b"# my node\nwork:\n    tags: [a]  # registered by hand\n"
    (root / "tcw-config.yaml").write_bytes(before)
    target = root / "planning" / "work"
    init(["work"], root, "node", work_path=target)
    assert_only_added(before, config(root), b"id: node\n", f"    path: {target}\n".encode())


def test_init_replacing_a_path_keeps_the_comment_after_it(tmp_path):
    root = repository(tmp_path / "node")
    before = b"id: node\ntaxonomy:\n    path: docs/old   # moved in 2.3\n"
    (root / "tcw-config.yaml").write_bytes(before)
    init(["taxonomy"], root, paths={"taxonomy": Path("docs/new")})
    assert config(root) == b"id: node\ntaxonomy:\n    path: docs/new   # moved in 2.3\n"


def test_a_refused_init_leaves_config_index_and_folders_alone(tmp_path, monkeypatch, capsys):
    root = repository(tmp_path / "node")
    init(["work"], root, "node")                      # a pristine default store
    before = b"# no id yet\nwork: {tags: [a]}\n"      # braces: `path` cannot be added
    (root / "tcw-config.yaml").write_bytes(before)
    commit_all(root)
    status = git(root, "status", "--porcelain").stdout
    target = root / "planning" / "work"
    code = run(root, monkeypatch, "init", "work", "--id", "node", "--work-path", str(target))
    err = assert_refused_leaving_everything(root, before, code, capsys, "inside the braces")
    assert git(root, "status", "--porcelain").stdout == status   # .gitignore too
    assert "work.path" in err
    assert (root / "docs" / "work" / "inbox").is_dir()
    assert not (root / "planning").exists()
    assert b"id:" not in config(root)


@pytest.mark.parametrize("existing", [None, b"", b"\n  \n"])
def test_a_fresh_init_writes_the_whole_file(tmp_path, monkeypatch, existing):
    root = repository(tmp_path / "node")
    if existing is not None:
        (root / "tcw-config.yaml").write_bytes(existing)
    assert run(root, monkeypatch, "init", "work", "--id", "fresh") == 0
    assert yaml.safe_load(config(root))["id"] == "fresh"


def test_write_sentinel_adds_id_below_the_leading_comments(tmp_path):
    before = b"# header\n# more\nwork:\n  tags: [a]  # keep\n"
    (tmp_path / "tcw-config.yaml").write_bytes(before)
    assert write_sentinel(tmp_path, "proj") is True
    assert config(tmp_path) == b"# header\n# more\nid: proj\nwork:\n  tags: [a]  # keep\n"
    assert write_sentinel(tmp_path, "proj") is False


def test_write_sentinel_fills_a_null_id(tmp_path):
    (tmp_path / "tcw-config.yaml").write_bytes(b"id: null\n# keep me\nwork: {}\n")
    assert write_sentinel(tmp_path, "proj") is True
    assert config(tmp_path) == b"id: proj\n# keep me\nwork: {}\n"
    assert yaml.safe_load(config(tmp_path))["id"] == "proj"


def test_init_over_a_block_scalar_path_is_refused(tmp_path):
    root = repository(tmp_path / "node")
    before = b"id: node\ntaxonomy:\n  path: |\n    docs/old\n"
    (root / "tcw-config.yaml").write_bytes(before)
    with pytest.raises(ValueError, match="spans more than one line"):
        init(["taxonomy"], root, paths={"taxonomy": Path("docs/new")})
    assert config(root) == before
    assert not (root / "docs" / "new").exists()


def test_init_with_a_scalar_work_section_is_refused(tmp_path, monkeypatch, capsys):
    root = repository(tmp_path / "node")
    before = b"id: node\nwork: docs/work\n"
    (root / "tcw-config.yaml").write_bytes(before)
    commit_all(root)
    code = run(root, monkeypatch, "init", "work", "--work-path", str(root / "w"))
    err = capsys.readouterr().err
    assert code != 0
    assert config(root) == before
    assert git(root, "status", "--porcelain").stdout == ""
    assert "work must be a mapping" in err and "tcw-config.yaml" in err
    assert not (root / "w").exists()


@pytest.mark.parametrize("argv", [("add", "gamma"), ("rm", "missing")])
def test_a_tags_change_that_changes_nothing_is_not_refused(tmp_path, monkeypatch, argv):
    before = b"id: node\nwork:\n  tags:\n  - gamma  # hand-ordered\n  - alpha\n"
    root = work_node(tmp_path, before)
    assert run(root, monkeypatch, "work", "tags", *argv) == 0
    assert config(root) == before
    assert git(root, "status", "--porcelain").stdout == ""


@pytest.mark.parametrize("text", [b"---\n", b"~\n", b"# placeholder\n---\n"])
def test_write_sentinel_on_a_null_document(tmp_path, text):
    (tmp_path / "tcw-config.yaml").write_bytes(text)
    assert write_sentinel(tmp_path, "proj") is True
    assert yaml.safe_load(config(tmp_path)) == {"id": "proj"}
