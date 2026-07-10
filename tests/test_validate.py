"""`tcw validate` — aggregate YAML + tcw:// link + component-check pass."""

import subprocess
from pathlib import Path

from tcw.cli import main
from tcw.store.fs import FsCapabilitiesStore, FsTaxonomyStore, init
from tcw.validate import validate


def node(tmp_path: Path, name: str = "repo") -> Path:
    root = tmp_path / name
    root.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "t"], check=True)
    init(["taxonomy", "capabilities", "work"], root)
    return root


def _body(root: Path, path: str, text: str) -> None:
    """Write a capability description body (a scanned *.md file)."""
    FsCapabilitiesStore.open(root).add(path, name=path.rsplit("/", 1)[-1].title())
    (root / "docs" / "capabilities" / path / "description.md").write_text(text)


# ── clean node ────────────────────────────────────────────────────────────────

def test_clean_node_ok(tmp_path):
    root = node(tmp_path)
    FsTaxonomyStore.open(root).add("Login", slug="auth")
    assert validate(root) == []


def test_valid_tcw_link_ok(tmp_path):
    root = node(tmp_path)
    FsTaxonomyStore.open(root).add("Login", slug="auth")
    _body(root, "signin", "See [the term](tcw://T/auth).")
    assert validate(root) == []


# ── (a) YAML ─────────────────────────────────────────────────────────────────

def test_bad_yaml_syntax_does_not_crash_and_skips_checks(tmp_path):
    root = node(tmp_path)
    (root / "docs" / "capabilities" / "meta.yaml").write_text("a: [unterminated\n")
    problems = validate(root)
    assert any("meta.yaml" in p for p in problems)
    assert any("component checks skipped" in p for p in problems)
    # No taxonomy/capabilities check ran.
    assert not any(p.startswith(("taxonomy check", "capabilities check")) for p in problems)


# ── (b) tcw:// links ─────────────────────────────────────────────────────────

def test_dangling_link_is_a_problem(tmp_path):
    root = node(tmp_path)
    _body(root, "signin", "Broken [x](tcw://C/does-not-exist).")
    problems = validate(root)
    assert any("tcw://C/does-not-exist" in p for p in problems)


def test_malformed_link_is_a_problem(tmp_path):
    root = node(tmp_path)
    _body(root, "signin", "Bad [x](tcw://no-axis-here).")
    problems = validate(root)
    assert any("tcw://no-axis-here" in p for p in problems)


def test_link_in_fenced_code_block_is_ignored(tmp_path):
    root = node(tmp_path)
    _body(root, "signin", "Example:\n\n```\n[x](tcw://C/nope)\n```\n")
    assert validate(root) == []


def test_link_in_inline_code_is_ignored(tmp_path):
    root = node(tmp_path)
    _body(root, "signin", "Write `[x](tcw://C/nope)` in prose.")
    assert validate(root) == []


def test_adjacent_backtick_runs_do_not_leak(tmp_path):
    # A doc teaching the scheme with adjacent backtick runs (```` ``` ````) must
    # still ignore an inline `](tcw://…)` example — no false positive.
    root = node(tmp_path)
    _body(root, "signin", "strip fenced ```` ``` ```` then match `](tcw://…)` targets")
    assert validate(root) == []


# ── (c) component checks ─────────────────────────────────────────────────────

def test_component_check_failure_surfaces(tmp_path):
    root = node(tmp_path)
    # A Feature with no vocabulary ref -> taxonomy check() flags it.
    FsTaxonomyStore.open(root).add("Search", slug="search", kind="Feature")
    problems = validate(root)
    assert any(p.startswith("taxonomy check:") for p in problems)


def test_path_narrows_scan_and_runs_that_check(tmp_path):
    root = node(tmp_path)
    # Break taxonomy, but scan only docs/capabilities -> taxonomy check not run.
    FsTaxonomyStore.open(root).add("Search", slug="search", kind="Feature")
    problems = validate(root, root / "docs" / "capabilities")
    assert not any(p.startswith("taxonomy check:") for p in problems)


# ── CLI exit codes ───────────────────────────────────────────────────────────

def test_cli_clean_exits_0(tmp_path, monkeypatch, capsys):
    root = node(tmp_path)
    monkeypatch.chdir(root)
    assert main(["validate"]) == 0
    assert "validate OK" in capsys.readouterr().out


def test_cli_problem_exits_1(tmp_path, monkeypatch, capsys):
    root = node(tmp_path)
    _body(root, "signin", "Broken [x](tcw://C/nope).")
    monkeypatch.chdir(root)
    assert main(["validate"]) == 1
