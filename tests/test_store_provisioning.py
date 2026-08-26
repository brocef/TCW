"""Declaring a component store's home repository, and provisioning it.

The subject is `work.repository`: the portable half of the store location, which
says where a store *comes from* rather than where it happens to sit on one disk.

**No test here reaches the network.** Where a remote is needed, it is a real bare
repository in `tmp_path` — Git does not care that the URL is a local path, and
the code under test never learns the difference.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import yaml

from tcw.store.base import (
    RepositoryDeclaration, StoreNotProvisioned, parse_repository_declaration,
)
from tcw.store.fs import FsWorkStore, init


WHERE = "work.repository"


def _repo(path: Path) -> Path:
    """A git repository with an identity, so commits do not depend on the
    developer's global config."""
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", "-b", "main", str(path)], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.email", "test@example.com"],
                   check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.name", "Test"], check=True)
    subprocess.run(["git", "-C", str(path), "config", "commit.gpgsign", "false"], check=True)
    return path


def _write_config(node_root: Path, **work: object) -> None:
    path = node_root / "tcw-config.yaml"
    config = yaml.safe_load(path.read_text()) or {}
    config.setdefault("work", {}).update(work)
    path.write_text(yaml.safe_dump(config, sort_keys=False))


# ── the declaration parser ───────────────────────────────────────────────────

def test_a_full_declaration_parses_to_its_fields():
    declaration, problems = parse_repository_declaration(
        {"url": "https://example.invalid/orchestrator.git",
         "ref": "main",
         "path": "docs/work/corelib",
         "checkout": "~/src/orchestrator"},
        WHERE,
    )
    assert problems == []
    assert declaration == RepositoryDeclaration(
        url="https://example.invalid/orchestrator.git",
        ref="main",
        path="docs/work/corelib",
        checkout="~/src/orchestrator",
    )


def test_only_a_url_is_required_and_the_rest_default():
    declaration, problems = parse_repository_declaration({"url": "git@host:o/r.git"}, WHERE)
    assert problems == []
    assert declaration == RepositoryDeclaration(url="git@host:o/r.git", ref=None,
                                                path="", checkout=None)


def test_an_absent_declaration_is_not_a_problem():
    assert parse_repository_declaration(None, WHERE) == (None, [])


@pytest.mark.parametrize("raw, expected", [
    ({}, "work.repository.url"),
    ({"url": "   "}, "work.repository.url"),
    ({"url": 7}, "work.repository.url"),
    ({"url": "u", "ref": ""}, "work.repository.ref"),
    ({"url": "u", "checkout": 3}, "work.repository.checkout"),
    ({"url": "u", "path": "/etc/passwd"}, "work.repository.path"),
    ({"url": "u", "path": "../../elsewhere"}, "work.repository.path"),
    ({"url": "u", "path": "docs/../../out"}, "work.repository.path"),
    ({"url": "u", "surprise": 1}, "work.repository"),
])
def test_a_bad_declaration_is_reported_and_yields_nothing(raw, expected):
    declaration, problems = parse_repository_declaration(raw, WHERE)
    assert declaration is None, "a declaration with a problem must fail closed"
    assert any(p.startswith(expected) for p in problems), problems


def test_a_non_mapping_declaration_names_the_type_it_got():
    declaration, problems = parse_repository_declaration("git@host:o/r.git", WHERE)
    assert declaration is None
    assert problems == ["work.repository: expected a mapping, got str"]


def test_a_relative_path_is_normalized_not_merely_accepted():
    declaration, problems = parse_repository_declaration(
        {"url": "u", "path": "./docs/work/corelib/"}, WHERE)
    assert problems == []
    assert declaration is not None and declaration.path == "docs/work/corelib"


# ── the declaration on a node ────────────────────────────────────────────────

def test_a_node_reads_back_its_declaration(tmp_path):
    code = _repo(tmp_path / "code")
    init(["work"], code, "corelib")
    _write_config(code, repository={"url": "git@host:me/orchestrator.git",
                                    "path": "docs/work/corelib"})
    store = FsWorkStore.open(code)
    declaration = store.repository_declaration()
    assert declaration is not None
    assert declaration.url == "git@host:me/orchestrator.git"
    assert store.repository_problems() == []


def test_a_malformed_declaration_is_reported_by_check_not_by_opening(tmp_path):
    code = _repo(tmp_path / "code")
    init(["work"], code, "corelib")
    _write_config(code, repository={"path": "docs/work/corelib"})   # no url

    store = FsWorkStore.open(code)          # must not raise: reading is not validating
    assert store.repository_declaration() is None

    problems = store.repository_problems()
    assert len(problems) == 1
    assert "work.repository.url" in problems[0]
    assert "tcw-config.yaml" in problems[0]
    assert problems[0] in store.check()


def test_store_not_provisioned_is_a_value_error():
    """Existing `except ValueError` callers around `open()` must keep working —
    this is what lets the new state be introduced without a flag day."""
    assert issubclass(StoreNotProvisioned, ValueError)
