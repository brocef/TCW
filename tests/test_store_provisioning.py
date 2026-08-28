"""Declaring a component store's home repository, and provisioning it.

The subject is `work.repository`: the portable half of the store location, which
says where a store *comes from* rather than where it happens to sit on one disk.

**No test here reaches the network.** Where a remote is needed, it is a real bare
repository in `tmp_path` — Git does not care that the URL is a local path, and
the code under test never learns the difference.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

from tcw.store.base import (
    RepositoryDeclaration, StoreNotProvisioned, parse_repository_declaration,
)
from tcw.cli import main
from tcw.store import fs
from tcw.store.fs import FsStoreProvisioner, FsWorkStore, init
from tcw.validate import validate


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


# ── resolution precedence ────────────────────────────────────────────────────

def _local_store(root: Path) -> Path:
    for name in ("inbox", "backlog", "active", "review", "completed", "discarded"):
        (root / name).mkdir(parents=True, exist_ok=True)
        (root / name / ".gitkeep").write_text("")
    return root


def test_a_store_already_here_wins_over_the_declaration(tmp_path):
    """The requester's laptop: the orchestrator folder is present, so nothing
    about that machine changes and the declaration is never consulted."""
    code = _repo(tmp_path / "code")
    init(["work"], code, "corelib")
    here = _local_store(_repo(tmp_path / "orchestrator-local") / "stores" / "corelib")
    _write_config(code, path=str(here),
                  repository={"url": str(_remote_with_store(tmp_path)),
                              "path": "docs/work/corelib"})

    assert FsWorkStore.open(code).root == here.resolve()
    assert not (tmp_path / "cache" / "tcw").exists(), \
        "resolution must not provision, and must not even look in the cache"


def test_provision_reports_a_local_store_without_contacting_the_remote(
    tmp_path, monkeypatch, capsys,
):
    """Criterion 5 applies to the command as well as resolution: a usable local
    ``work.path`` wins, so plain provisioning has nothing to obtain."""
    code = _repo(tmp_path / "code")
    init(["work"], code, "corelib")
    here = _local_store(_repo(tmp_path / "orchestrator-local") / "stores" / "corelib")
    remote = _remote_with_store(tmp_path)
    _write_config(
        code,
        path=str(here),
        repository={"url": str(remote), "path": "docs/work/corelib"},
    )
    monkeypatch.chdir(code)

    calls = _count_git(monkeypatch)
    assert main(["provision"]) == 0

    assert "already available" in capsys.readouterr().out
    assert not any("clone" in argv or "fetch" in argv for argv in calls), calls
    assert not (tmp_path / "cache" / "tcw").exists()


def test_an_absent_local_store_falls_through_to_the_provisioned_one(tmp_path):
    """The cloud session: the same config, on a machine that has only the code."""
    code = _repo(tmp_path / "code")
    init(["work"], code, "corelib")
    declaration = RepositoryDeclaration(url=str(_remote_with_store(tmp_path)),
                                        path="docs/work/corelib")
    _write_config(code, path="../orchestrator-that-is-not-here/stores/corelib",
                  repository={"url": declaration.url, "path": declaration.path})

    with pytest.raises(StoreNotProvisioned):
        FsWorkStore.open(code)

    FsStoreProvisioner(code, "work", declaration).ensure_available()

    assert FsWorkStore.open(code).root == fs.provisioned_store_root(
        code, declaration).resolve()


def test_not_provisioned_names_the_remote_and_the_command(tmp_path):
    code = _repo(tmp_path / "code")
    init(["work"], code, "corelib")
    _write_config(code, path="../nowhere/stores/corelib",
                  repository={"url": "https://example.invalid/orchestrator.git"})

    with pytest.raises(StoreNotProvisioned) as caught:
        FsWorkStore.open(code)

    message = str(caught.value)
    assert "https://example.invalid/orchestrator.git" in message
    assert "tcw provision" in message
    assert "not a directory" not in message, \
        "a declared store that simply is not here yet is not a misconfiguration"


def test_without_a_declaration_a_broken_path_still_says_what_it_always_said(tmp_path):
    """The compatibility guarantee: with nothing declared, not one byte moves."""
    code = _repo(tmp_path / "code")
    init(["work"], code, "corelib")
    _write_config(code, path="../nowhere/stores/corelib")

    with pytest.raises(ValueError) as caught:
        FsWorkStore.open(code)

    assert not isinstance(caught.value, StoreNotProvisioned)
    assert "work.path is not a directory" in str(caught.value)


def test_a_declared_node_whose_default_store_exists_uses_it(tmp_path):
    """`work.path` unset, `docs/work` present, a declaration alongside: the real
    store on this machine still wins."""
    code = _repo(tmp_path / "code")
    init(["work"], code, "corelib")
    _write_config(code, repository={"url": str(_remote_with_store(tmp_path)),
                                    "path": "docs/work/corelib"})

    assert FsWorkStore.open(code).root == (code / "docs" / "work").resolve()


def test_a_provisioned_store_commits_in_its_own_repository(tmp_path):
    """The store's repository owns its commits, not the code repository — the
    same split a local `work.path` in another repository already gets."""
    code = _repo(tmp_path / "code")
    init(["work"], code, "corelib")
    declaration = RepositoryDeclaration(url=str(_remote_with_store(tmp_path)),
                                        path="docs/work/corelib")
    _write_config(code, repository={"url": declaration.url, "path": declaration.path})
    (code / "docs" / "work").rename(code / "docs" / "work-moved-aside")
    FsStoreProvisioner(code, "work", declaration).ensure_available()

    store = FsWorkStore.open(code)

    assert store.store_git_root == fs.checkout_root(code, declaration).resolve()
    assert store.node_root == code.resolve()


# ── what the user is told ────────────────────────────────────────────────────

def _declared_but_absent(tmp_path: Path) -> Path:
    """A node exactly like the requester's cloud session: the config names a
    store in another repository, and this machine has only the code."""
    code = _repo(tmp_path / "code")
    init(["work"], code, "corelib")
    subprocess.run(["git", "-C", str(code), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(code), "commit", "-qm", "init"], check=True)
    (code / "docs" / "work").rename(code / "docs" / "work-elsewhere")
    _write_config(code, path="../orchestrator/stores/corelib",
                  repository={"url": "https://example.invalid/orchestrator.git",
                              "path": "stores/corelib"})
    return code


def test_the_board_no_longer_misdirects_to_tcw_init(tmp_path, monkeypatch, capsys):
    """The reported symptom. `tcw work list` used to answer a declared-but-absent
    store with "run `tcw init`" — advice that would scaffold a second, empty
    store beside the real one."""
    monkeypatch.chdir(_declared_but_absent(tmp_path))

    assert main(["work", "list"]) == 1

    err = capsys.readouterr().err
    assert "no tcw work node here" not in err
    assert "tcw init" not in err
    assert "https://example.invalid/orchestrator.git" in err
    assert "tcw provision" in err


@pytest.mark.parametrize("argv", [
    ["work", "list"], ["work", "show", "anything"], ["work", "path"],
    ["work", "nodes"], ["work", "reconcile", "anything"],
    ["work", "escalate", "anything"],
])
def test_every_work_command_says_the_same_actionable_thing(tmp_path, monkeypatch,
                                                           capsys, argv):
    """One message, six call sites — the duplication is what kept it unimprovable."""
    monkeypatch.chdir(_declared_but_absent(tmp_path))

    assert main(argv) == 1
    assert "tcw provision" in capsys.readouterr().err


def test_an_absent_node_still_gets_the_tcw_init_advice(tmp_path, monkeypatch, capsys):
    """The other answer must not be lost: somewhere that is not a node at all is
    exactly what `tcw init` fixes."""
    plain = tmp_path / "not-a-node"
    plain.mkdir()
    monkeypatch.chdir(plain)

    assert main(["work", "list"]) == 1
    assert "no tcw work node here" in capsys.readouterr().err


def test_validate_reports_the_declared_store_rather_than_a_dead_path(tmp_path, capsys):
    code = _declared_but_absent(tmp_path)

    problems = validate(code)

    assert any("tcw provision" in p for p in problems), problems
    assert not any("is not a directory" in p for p in problems), problems


def test_a_parent_still_lists_its_topology_when_a_child_is_unprovisioned(tmp_path,
                                                                        monkeypatch,
                                                                        capsys):
    """`_has_work_store` answers False rather than raising, so one unprovisioned
    child cannot turn a parent's listing into a hard failure."""
    parent = _repo(tmp_path / "parent")
    init(["work"], parent, "parent-project")
    child = _repo(tmp_path / "child")
    init(["work"], child, "child-project")
    (child / "docs" / "work").rename(child / "docs" / "work-elsewhere")
    _write_config(child, repository={"url": "https://example.invalid/o.git"})

    for root, key, other in ((parent, "children", "child-project"),
                             (child, "parent", "parent-project")):
        path = root / "tcw-config.yaml"
        config = yaml.safe_load(path.read_text())
        config["connected-projects"] = {key: {other: f"../{other.split('-')[0]}"}}
        path.write_text(yaml.safe_dump(config, sort_keys=False))

    monkeypatch.chdir(parent)
    assert main(["work", "nodes"]) == 0

    out = capsys.readouterr().out
    assert "parent-project" in out
    assert "children: (none — leaf)" in out, \
        "an unprovisioned child has no usable store here, and says so by absence"


# ── the `tcw provision` verb ─────────────────────────────────────────────────

def _declared_against(tmp_path: Path, remote: Path, **repository) -> Path:
    """A node declaring `remote` as its work store's home, with no local store."""
    code = _repo(tmp_path / "code")
    init(["work"], code, "corelib")
    shutil.rmtree(code / "docs" / "work")
    _write_config(code, repository={"url": str(remote), "path": "docs/work/corelib",
                                    **repository})
    return code


def test_provision_then_the_board_works(tmp_path, monkeypatch, capsys):
    """The whole feature, end to end, in the shape the requester hits it."""
    remote = _remote_with_store(tmp_path)
    (remote / "docs" / "work" / "corelib" / "backlog" / "an-item").mkdir()
    (remote / "docs" / "work" / "corelib" / "backlog" / "an-item" / "state.yaml").write_text(
        "slug: an-item\ntitle: An item from the orchestrator\nstatus: backlog\n"
        "created: 2026-01-01\n")
    subprocess.run(["git", "-C", str(remote), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(remote), "commit", "-qm", "add an item"], check=True)
    monkeypatch.chdir(_declared_against(tmp_path, remote))

    assert main(["work", "list"]) == 1                      # before
    assert main(["provision"]) == 0
    capsys.readouterr()
    assert main(["work", "list"]) == 0                      # after

    assert "An item from the orchestrator" in capsys.readouterr().out


def test_provision_names_the_remote_before_contacting_it(tmp_path, monkeypatch, capsys):
    """A config can name a URL, so the person holding the checkout is told which
    one is about to be contacted."""
    remote = _remote_with_store(tmp_path)
    monkeypatch.chdir(_declared_against(tmp_path, remote))

    assert main(["provision"]) == 0

    out = capsys.readouterr().out
    assert str(remote) in out
    assert out.index(str(remote)) < out.index("obtained")


def test_a_second_provision_reports_available_and_contacts_nothing(tmp_path,
                                                                   monkeypatch, capsys):
    monkeypatch.chdir(_declared_against(tmp_path, _remote_with_store(tmp_path)))
    assert main(["provision"]) == 0
    capsys.readouterr()

    calls = _count_git(monkeypatch)
    assert main(["provision"]) == 0

    assert "already available" in capsys.readouterr().out
    assert calls == []


def test_a_dry_run_from_the_cli_contacts_nothing(tmp_path, monkeypatch, capsys):
    code = _declared_against(tmp_path, _remote_with_store(tmp_path))
    monkeypatch.chdir(code)

    calls = _count_git(monkeypatch)
    assert main(["provision", "--dry-run"]) == 0

    assert "would obtain" in capsys.readouterr().out
    assert calls == []
    assert not (tmp_path / "cache" / "tcw").exists()


def test_a_node_declaring_nothing_says_so_and_succeeds(tmp_path, monkeypatch, capsys):
    code = _repo(tmp_path / "code")
    init(["work"], code, "corelib")
    monkeypatch.chdir(code)

    assert main(["provision"]) == 0
    assert "Nothing to provision" in capsys.readouterr().out


def test_a_malformed_declaration_refuses_rather_than_doing_nothing(tmp_path,
                                                                   monkeypatch, capsys):
    """Silently reporting success would be the worst outcome: the user asked for
    a store and would be told everything is fine."""
    code = _repo(tmp_path / "code")
    init(["work"], code, "corelib")
    _write_config(code, repository={"path": "docs/work/corelib"})     # no url
    monkeypatch.chdir(code)

    assert main(["provision"]) == 1
    assert "work.repository.url" in capsys.readouterr().err


def test_a_failure_exits_non_zero_and_names_the_cause(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(_declared_against(tmp_path, tmp_path / "no-such-repository"))

    assert main(["provision"]) == 1
    assert "git clone failed" in capsys.readouterr().err


def test_provision_outside_a_node_says_so(tmp_path, monkeypatch, capsys):
    plain = tmp_path / "not-a-node"
    plain.mkdir()
    monkeypatch.chdir(plain)

    assert main(["provision"]) == 1
    assert "no tcw node here" in capsys.readouterr().err


def test_limiting_to_undeclared_work_is_a_no_op(tmp_path, monkeypatch, capsys):
    code = _repo(tmp_path / "code")
    init(["work"], code, "corelib")
    monkeypatch.chdir(code)

    assert main(["provision", "--component", "work"]) == 0
    assert "Nothing to provision" in capsys.readouterr().out


# ── nothing else reaches the network ─────────────────────────────────────────

@pytest.mark.parametrize("argv", [
    ["work", "list"], ["work", "show", "an-item"], ["work", "path"],
    ["work", "nodes"], ["work", "docs"], ["validate"],
])
def test_no_read_command_provisions_implicitly(tmp_path, monkeypatch, capsys, argv):
    """A repository's config can name a URL. Nothing but the provisioning verb
    may act on it, so the commands a user runs first must work against a
    provisioned node with the fetch path made fatal.
    """
    remote = _remote_with_store(tmp_path)
    (remote / "docs" / "work" / "corelib" / "backlog" / "an-item").mkdir()
    (remote / "docs" / "work" / "corelib" / "backlog" / "an-item" / "state.yaml").write_text(
        "slug: an-item\ntitle: An item\nstatus: backlog\ncreated: 2026-01-01\n")
    subprocess.run(["git", "-C", str(remote), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(remote), "commit", "-qm", "item"], check=True)
    code = _declared_against(tmp_path, remote)
    monkeypatch.chdir(code)
    assert main(["provision"]) == 0
    capsys.readouterr()

    def explode(self, *args, **kwargs):
        raise AssertionError(f"{argv} provisioned implicitly")

    monkeypatch.setattr(FsStoreProvisioner, "ensure_available", explode)
    monkeypatch.setattr(FsStoreProvisioner, "_obtain", explode)
    monkeypatch.setattr(FsStoreProvisioner, "_refresh", explode)

    assert main(argv) == 0


# ── review findings (Codex, PR #23) ──────────────────────────────────────────

def test_a_repository_without_a_store_leaves_no_checkout_behind(tmp_path):
    """Review finding 1. The clone succeeds, so the staging directory is renamed
    into place, and only *then* is the layout checked — leaving a checkout at the
    target after a failure the command reports."""
    code = _repo(tmp_path / "code")
    init(["work"], code, "corelib")
    remote = _remote_with_store(tmp_path)
    provisioner = _provisioner(tmp_path, code, remote, path="docs/work/somewhere-else")

    with pytest.raises(ValueError):
        provisioner.ensure_available()

    assert not fs.checkout_root(code, provisioner.declaration).exists(), \
        "a provision that fails leaves nothing at the target"


def test_an_occupied_checkout_is_not_fetched_without_checking_its_origin(tmp_path,
                                                                        monkeypatch):
    """Review finding 2. `checkout.exists()` alone routes into refresh, which
    fetches *that* checkout's origin — so the command can print one remote and
    contact another."""
    code = _repo(tmp_path / "code")
    init(["work"], code, "corelib")
    declared = _remote_with_store(tmp_path)
    unrelated = _repo(tmp_path / "unrelated")
    (unrelated / "readme").write_text("not the declared repository\n")
    subprocess.run(["git", "-C", str(unrelated), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(unrelated), "commit", "-qm", "seed"], check=True)

    squatter = tmp_path / "squatter"
    subprocess.run(["git", "clone", "--quiet", str(unrelated), str(squatter)], check=True)
    provisioner = _provisioner(tmp_path, code, declared, checkout=str(squatter))

    calls = _count_git(monkeypatch)
    with pytest.raises(ValueError) as caught:
        provisioner.ensure_available()

    assert "origin" in str(caught.value) or "declared" in str(caught.value)
    assert not any(argv[:1] == ["git"] and "fetch" in argv for argv in calls), \
        f"refused only after contacting the wrong remote: {calls}"


def test_an_occupied_checkout_that_is_not_a_repository_is_refused(tmp_path, monkeypatch):
    """The other half of finding 2: a declared `checkout` is an arbitrary
    user-chosen directory, so it can hold something that is not a repository at
    all. `git fetch` there fails with a confusing error; this fails with a clear
    one, and without a network call."""
    code = _repo(tmp_path / "code")
    init(["work"], code, "corelib")
    occupied = tmp_path / "just-a-folder"
    occupied.mkdir()
    (occupied / "notes.txt").write_text("someone else's files\n")
    provisioner = _provisioner(tmp_path, code, _remote_with_store(tmp_path),
                               checkout=str(occupied))

    calls = _count_git(monkeypatch)
    with pytest.raises(ValueError) as caught:
        provisioner.ensure_available()

    assert "not a git repository" in str(caught.value)
    assert not any("fetch" in argv for argv in calls), calls
    assert (occupied / "notes.txt").is_file(), "someone else's directory is untouched"


# ── second review findings ─────────────────────────────────────────────────


def test_only_work_is_exposed_until_the_other_component_adapters_land(
    tmp_path, monkeypatch, capsys,
):
    """Child A provisions work. Taxonomy and capabilities are child B, so this
    CLI must not advertise values whose layouts and resolution are not built."""
    code = _repo(tmp_path / "code")
    init(["work"], code, "corelib")
    config_path = code / "tcw-config.yaml"
    config = yaml.safe_load(config_path.read_text())
    config["taxonomy"] = {
        "repository": {"url": str(tmp_path / "taxonomy-remote")}
    }
    config_path.write_text(yaml.safe_dump(config, sort_keys=False))
    monkeypatch.chdir(code)

    assert main(["provision"]) == 0
    assert "Nothing to provision" in capsys.readouterr().out
    assert not (tmp_path / "cache" / "tcw").exists()
    with pytest.raises(SystemExit):
        main(["provision", "--component", "taxonomy"])


def test_an_unusable_local_layout_falls_through_to_the_provisioned_store(tmp_path):
    """Status folders outside Git are not a usable external store and therefore
    must not block the declaration's valid provisioned fallback."""
    code = _repo(tmp_path / "code")
    init(["work"], code, "corelib")
    local = _local_store(tmp_path / "not-a-repository" / "work")
    declaration = RepositoryDeclaration(
        url=str(_remote_with_store(tmp_path)), path="docs/work/corelib")
    _write_config(
        code,
        path=str(local),
        repository={"url": declaration.url, "path": declaration.path},
    )
    FsStoreProvisioner(code, "work", declaration).ensure_available()

    assert FsWorkStore.open(code).root == fs.provisioned_store_root(
        code, declaration).resolve()


def test_validate_reports_a_malformed_declaration_when_the_store_is_absent(tmp_path):
    """Criterion 10 is about the declaration error, even when no local store can
    be opened to report it through ``store.check()``."""
    code = _repo(tmp_path / "code")
    init(["work"], code, "corelib")
    shutil.rmtree(code / "docs" / "work")
    _write_config(code, repository={"path": "docs/work/corelib"})

    problems = validate(code)

    assert any("work.repository.url" in problem for problem in problems), problems
