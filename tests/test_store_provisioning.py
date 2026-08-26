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
from tcw.store import fs
from tcw.store.fs import FsStoreProvisioner, FsWorkStore, init


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


# ── the provisioner ──────────────────────────────────────────────────────────

def _remote_with_store(tmp_path: Path, inner: str = "docs/work/corelib") -> Path:
    """A repository that actually holds a work store, used as the remote.

    Git does not care that the URL is a local path, and the code under test
    never learns the difference — which is how this suite honors "no network,
    ever" while exercising real clones.
    """
    remote = _repo(tmp_path / "orchestrator")
    store = remote / inner
    for name in ("inbox", "backlog", "active", "review", "completed", "discarded"):
        (store / name).mkdir(parents=True)
        (store / name / ".gitkeep").write_text("")
    subprocess.run(["git", "-C", str(remote), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(remote), "commit", "-qm", "seed store"], check=True)
    return remote


def _provisioner(tmp_path, node_root: Path, remote: Path, **overrides):
    """A provisioner whose cache lands inside `tmp_path`, never the real
    `~/.cache`."""
    declaration = RepositoryDeclaration(
        url=str(remote), path=overrides.pop("path", "docs/work/corelib"), **overrides)
    return FsStoreProvisioner(node_root, "work", declaration)


@pytest.fixture(autouse=True)
def _cache_in_tmp(tmp_path, monkeypatch):
    """No test may write to the developer's real cache directory."""
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))


def _count_git(monkeypatch):
    """Count git invocations made by the provisioner, letting them run."""
    calls: list[list[str]] = []
    real = fs._git

    def counting(argv, *args, **kwargs):
        calls.append(list(argv))
        return real(argv, *args, **kwargs)

    monkeypatch.setattr(fs, "_git", counting)
    return calls


def test_obtaining_a_declared_store_puts_it_where_resolution_expects(tmp_path):
    code = _repo(tmp_path / "code")
    init(["work"], code, "corelib")
    remote = _remote_with_store(tmp_path)
    provisioner = _provisioner(tmp_path, code, remote)

    assert provisioner.is_available() is False
    result = provisioner.ensure_available()

    assert result.action == "obtained"
    assert result.available is True
    expected = fs.provisioned_store_root(code, provisioner.declaration)
    assert Path(result.location) == expected
    assert (expected / "backlog").is_dir()
    assert provisioner.is_available() is True


def test_a_second_call_contacts_nothing(tmp_path, monkeypatch):
    """Idempotence is the property that lets a caller run this unconditionally,
    and it is only worth anything if the second run makes no git call at all."""
    code = _repo(tmp_path / "code")
    init(["work"], code, "corelib")
    provisioner = _provisioner(tmp_path, code, _remote_with_store(tmp_path))
    provisioner.ensure_available()

    calls = _count_git(monkeypatch)
    result = provisioner.ensure_available()

    assert result.action == "available"
    assert result.available is True
    assert calls == [], f"an already-available store must contact nothing, ran {calls}"


def test_a_dry_run_contacts_nothing_and_reports_the_plan(tmp_path, monkeypatch):
    code = _repo(tmp_path / "code")
    init(["work"], code, "corelib")
    provisioner = _provisioner(tmp_path, code, _remote_with_store(tmp_path))

    calls = _count_git(monkeypatch)
    result = provisioner.ensure_available(dry_run=True)

    assert result.action == "planned"
    assert result.available is False
    assert calls == []
    assert not fs.checkout_root(code, provisioner.declaration).exists()


def test_refresh_brings_an_existing_checkout_to_the_declared_ref(tmp_path):
    code = _repo(tmp_path / "code")
    init(["work"], code, "corelib")
    remote = _remote_with_store(tmp_path)
    provisioner = _provisioner(tmp_path, code, remote, ref="main")
    provisioner.ensure_available()
    target = fs.provisioned_store_root(code, provisioner.declaration)

    (remote / "docs" / "work" / "corelib" / "backlog" / "later.md").write_text("later\n")
    subprocess.run(["git", "-C", str(remote), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(remote), "commit", "-qm", "add an item"], check=True)

    result = provisioner.ensure_available(refresh=True)

    assert result.action == "refreshed"
    assert (target / "backlog" / "later.md").is_file()


def test_an_unknown_ref_fails_and_leaves_nothing_behind(tmp_path):
    code = _repo(tmp_path / "code")
    init(["work"], code, "corelib")
    provisioner = _provisioner(tmp_path, code, _remote_with_store(tmp_path),
                               ref="no-such-ref")

    with pytest.raises(ValueError) as caught:
        provisioner.ensure_available()

    assert "git" in str(caught.value)
    assert not fs.checkout_root(code, provisioner.declaration).exists()
    assert list((tmp_path / "cache" / "tcw" / "stores").glob("*")) == [], \
        "a failed clone must leave no staging directory behind either"


def test_an_unreachable_remote_fails_and_leaves_nothing_behind(tmp_path):
    code = _repo(tmp_path / "code")
    init(["work"], code, "corelib")
    provisioner = FsStoreProvisioner(code, "work", RepositoryDeclaration(
        url=str(tmp_path / "there-is-no-repository-here"), path="docs/work/corelib"))

    with pytest.raises(ValueError) as caught:
        provisioner.ensure_available()

    assert "git clone failed" in str(caught.value)
    assert not fs.checkout_root(code, provisioner.declaration).exists()


def test_a_repository_without_a_store_at_the_declared_path_is_refused(tmp_path):
    code = _repo(tmp_path / "code")
    init(["work"], code, "corelib")
    remote = _remote_with_store(tmp_path)
    provisioner = _provisioner(tmp_path, code, remote, path="docs/work/somewhere-else")

    with pytest.raises(ValueError) as caught:
        provisioner.ensure_available()

    assert "no work store" in str(caught.value)
    assert "missing:" in str(caught.value)


def test_a_declared_checkout_location_is_used_instead_of_the_cache(tmp_path):
    code = _repo(tmp_path / "code")
    init(["work"], code, "corelib")
    provisioner = _provisioner(tmp_path, code, _remote_with_store(tmp_path),
                               checkout=str(tmp_path / "elsewhere" / "orchestrator"))

    result = provisioner.ensure_available()

    assert Path(result.location).is_relative_to(tmp_path / "elsewhere")
    assert not (tmp_path / "cache" / "tcw").exists()


def test_the_cache_key_separates_refs_and_shares_a_repository(tmp_path):
    code = _repo(tmp_path / "code")
    one = FsStoreProvisioner(code, "work", RepositoryDeclaration(url="u", ref="main"))
    two = FsStoreProvisioner(code, "work", RepositoryDeclaration(url="u", ref="next"))
    same = FsStoreProvisioner(code, "work", RepositoryDeclaration(url="u", ref="main"))

    roots = {p: fs.checkout_root(code, p.declaration) for p in (one, two, same)}
    assert roots[one] != roots[two], "two refs must not fight over one checkout"
    assert roots[one] == roots[same], "one (url, ref) pair is one working copy"


def test_an_undeclared_component_is_a_no_op(tmp_path):
    code = _repo(tmp_path / "code")
    result = FsStoreProvisioner(code, "work", None).ensure_available()
    assert result.action == "undeclared"
    assert result.available is False


def test_the_git_counter_actually_sees_calls(tmp_path, monkeypatch):
    """Guards the two "contacts nothing" tests above.

    `assert calls == []` passes just as well when the monkeypatch missed its
    target as when the code genuinely made no call, so those assertions are only
    worth something if the same counter is shown to observe a real one.
    """
    code = _repo(tmp_path / "code")
    init(["work"], code, "corelib")
    provisioner = _provisioner(tmp_path, code, _remote_with_store(tmp_path))

    calls = _count_git(monkeypatch)
    provisioner.ensure_available()

    assert any(argv[:2] == ["git", "clone"] for argv in calls), calls
