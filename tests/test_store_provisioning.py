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
    RepositoryDeclaration, StoreDeclarationError, StoreNotProvisioned,
    parse_repository_declaration,
)
from tcw.cli import main
from tcw.store import fs
from tcw.store.fs import (
    STORE_CLASSES, FsCapabilitiesStore, FsStoreProvisioner, FsTaxonomyStore,
    FsWorkStore, init,
)
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


def _remote_with_tree(tmp_path: Path, inner: str = "trees/taxonomy") -> Path:
    """A repository holding a *tree* store — which is just a directory.

    That is the whole point of these cases: `init` scaffolds a taxonomy or
    capabilities store as a bare folder with no required entries and no marker
    file, so there is nothing here to make it recognizable, and nothing the
    provisioner could check beyond its existence."""
    remote = _repo(tmp_path / "orchestrator-trees")
    (remote / inner).mkdir(parents=True)
    (remote / inner / ".gitkeep").write_text("")
    subprocess.run(["git", "-C", str(remote), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(remote), "commit", "-qm", "seed tree"], check=True)
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

    # The declared path names nothing in the clone, so *nothing* is missing from
    # a store — there is no store. The message used to enumerate all six status
    # folders as missing, which read as "an incomplete store" for a case that is
    # a wrong path. The enumeration belongs to the present-but-incomplete case,
    # which `test_the_work_layout_check_is_not_relaxed_by_the_tree_one` holds.
    assert "no work store" in str(caught.value)
    assert "no such directory" in str(caught.value)


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


def _declared_but_malformed(tmp_path: Path) -> Path:
    """The same node, with an ordinary config typo: a `repository` block whose
    `url` was never filled in. The store is just as absent, and the user is just
    as much in need of being told which line to fix."""
    code = _declared_but_absent(tmp_path)
    _write_config(code, repository={"ref": "main", "path": "stores/corelib"})
    return code


@pytest.mark.parametrize("argv", [
    ["work", "list"], ["work", "show", "anything"], ["work", "path"],
    ["work", "nodes"], ["work", "reconcile", "anything"],
    ["work", "escalate", "anything"],
])
def test_a_malformed_declaration_never_misdirects_to_tcw_init(tmp_path, monkeypatch,
                                                              capsys, argv):
    """Stated as the property, not an enumeration: a node that declares a home
    repository must never be answered with "run `tcw init`", however broken the
    declaration is. `tcw init` there would scaffold a second, empty store beside
    the real one — the worst advice available, and the reason this feature exists.

    `tcw validate` already reported the bad line; every work command flattened it
    to "no tcw work node here" because the message travelled as a plain
    `ValueError` that `find_node` discards."""
    monkeypatch.chdir(_declared_but_malformed(tmp_path))

    assert main(argv) == 1

    err = capsys.readouterr().err
    assert "no tcw work node here" not in err
    assert "tcw init" not in err
    assert "work.repository.url" in err, err


def test_a_malformed_declaration_is_a_declaration_error_not_a_bare_value_error(tmp_path):
    """The seam itself. `find_node` must be able to tell "this config is wrong"
    apart from "this is not a node", and only a distinct type carries that."""
    code = _declared_but_malformed(tmp_path)

    with pytest.raises(StoreDeclarationError):
        FsWorkStore.open(code)

    with pytest.raises(StoreDeclarationError):
        fs.find_node("work", code)


def test_a_misconfigured_sibling_node_does_not_break_a_topology_listing(tmp_path):
    """`_has_work_store` asks about *other* nodes, so it must keep answering
    False rather than raising — one broken child must not fail a parent's
    listing. The new type stays a `ValueError` subclass to preserve that."""
    assert fs._has_work_store(_declared_but_malformed(tmp_path)) is False


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


def test_every_component_is_exposed_now_that_its_adapter_exists(
    tmp_path, monkeypatch, capsys,
):
    """The successor to child A's deliberate narrowing.

    That CLI accepted only `work`, because advertising a value whose layout and
    resolution were not built meant cloning a taxonomy declaration and then
    refusing it for missing work statuses. The adapters exist now, so the tuple
    widens — and the assertion that matters is not that the value is *accepted*
    but that accepting it does the right thing, which is what the narrowing was
    protecting."""
    remote = _remote_with_tree(tmp_path, inner="trees/taxonomy")
    code = _repo(tmp_path / "code")
    init(["work"], code, "corelib")
    config_path = code / "tcw-config.yaml"
    config = yaml.safe_load(config_path.read_text())
    config["taxonomy"] = {
        "repository": {"url": str(remote), "path": "trees/taxonomy",
                       "checkout": str(tmp_path / "co")}
    }
    config_path.write_text(yaml.safe_dump(config, sort_keys=False))
    monkeypatch.chdir(code)

    assert main(["provision", "--component", "taxonomy"]) == 0

    assert (tmp_path / "co" / "trees" / "taxonomy").is_dir()
    assert "taxonomy: obtained" in capsys.readouterr().out
    # The refusal that made the narrowing necessary is gone: a tree declaration
    # is no longer measured against the work store's status folders.
    assert main(["taxonomy", "path"]) == 0


def test_an_unknown_component_is_still_refused(tmp_path, monkeypatch):
    """Widening the tuple is not opening it."""
    monkeypatch.chdir(_repo(tmp_path / "code"))
    with pytest.raises(SystemExit):
        main(["provision", "--component", "nonsense"])


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


# ── what "usable" means, per component ───────────────────────────────────────
#
# A work store names six folders and the provisioner reads them. A tree store
# names nothing, so the strongest honest check is that the directory is there.
# These cases pin the difference in both directions, because the risk is not
# that the tree check is weak — that is deliberate — but that it silently
# becomes the *work* check's answer, or that widening the tree case weakens the
# work one.

def test_a_tree_store_is_any_directory_that_is_there(tmp_path):
    """The accepted consequence, asserted rather than left implicit: a declared
    taxonomy store carrying no marker of any kind is usable."""
    remote = _remote_with_tree(tmp_path)
    node = _repo(tmp_path / "code")
    provisioner = FsStoreProvisioner(
        node, "taxonomy",
        RepositoryDeclaration(url=str(remote), path="trees/taxonomy",
                              checkout=str(tmp_path / "co")))

    provisioner.ensure_available()

    assert provisioner.is_available()
    assert (tmp_path / "co" / "trees" / "taxonomy").is_dir()


def test_a_tree_declaration_pointing_at_nothing_is_refused_and_leaves_nothing(tmp_path):
    """The one guarantee that survives the weaker predicate: `repository.path`
    must resolve inside the clone before the staging checkout is published."""
    remote = _remote_with_tree(tmp_path)
    node = _repo(tmp_path / "code")
    checkout = tmp_path / "co"
    provisioner = FsStoreProvisioner(
        node, "capabilities",
        RepositoryDeclaration(url=str(remote), path="trees/not-here",
                              checkout=str(checkout)))

    with pytest.raises(ValueError) as caught:
        provisioner.ensure_available()

    assert "capabilities" in str(caught.value)
    assert "work store" not in str(caught.value)
    assert not checkout.exists()


def test_the_work_layout_check_is_not_relaxed_by_the_tree_one(tmp_path):
    """The direction that would actually be a regression. A work declaration
    whose clone holds a bare directory must still be refused for its missing
    status folders."""
    remote = _remote_with_tree(tmp_path, inner="trees/pretend-work")
    node = _repo(tmp_path / "code")
    checkout = tmp_path / "co"
    provisioner = FsStoreProvisioner(
        node, "work",
        RepositoryDeclaration(url=str(remote), path="trees/pretend-work",
                              checkout=str(checkout)))

    with pytest.raises(ValueError) as caught:
        provisioner.ensure_available()

    assert "missing" in str(caught.value)
    assert "inbox" in str(caught.value)
    assert not checkout.exists()


# ── the tree stores on the ladder ───────────────────────────────────────────

def _tree_node(tmp_path: Path, component: str = "taxonomy", **section) -> Path:
    """A node with `component` configured however the case needs."""
    code = _repo(tmp_path / "code")
    init([component], code, "corelib")
    path = code / "tcw-config.yaml"
    config = yaml.safe_load(path.read_text()) or {}
    config.setdefault(component, {}).update(section)
    path.write_text(yaml.safe_dump(config, sort_keys=False))
    return code


def test_rule_four_is_untouched_for_a_node_that_configures_nothing(tmp_path):
    """The back-compatibility contract, and the one most easily broken by
    accident. With neither key set, `open` returns `docs/<component>` exactly as
    the single line it replaces did — no existence check, no new refusal."""
    code = _repo(tmp_path / "code")
    init(["taxonomy", "capabilities"], code, "corelib")

    assert FsTaxonomyStore.open(code).root == code / "docs" / "taxonomy"
    assert FsCapabilitiesStore.open(code).root == code / "docs" / "capabilities"


def test_rule_four_holds_even_when_the_component_folder_is_absent(tmp_path):
    """The case that would catch a `is_dir()` leaking into the undeclared path.
    A node with no `docs/taxonomy/` at all still opens, because that is what it
    does today."""
    code = _repo(tmp_path / "code")
    init(["work"], code, "corelib")           # taxonomy deliberately not scaffolded
    assert not (code / "docs" / "taxonomy").exists()

    assert FsTaxonomyStore.open(code).root == code / "docs" / "taxonomy"


def test_a_configured_tree_path_is_followed(tmp_path):
    """Criterion 6's other half: the new local locator actually works."""
    elsewhere = tmp_path / "trees" / "taxonomy"
    elsewhere.mkdir(parents=True)
    code = _tree_node(tmp_path, "taxonomy", path=str(elsewhere))

    assert FsTaxonomyStore.open(code).root == elsewhere.resolve()


def test_a_declared_tree_store_that_is_absent_says_so(tmp_path):
    """Criterion 1 at the store layer: not "no component here", but "declared,
    not provisioned, run this"."""
    code = _tree_node(tmp_path, "taxonomy",
                      path="../orchestrator/trees/taxonomy",
                      repository={"url": "https://example.invalid/orchestrator.git",
                                  "path": "trees/taxonomy"})

    with pytest.raises(StoreNotProvisioned) as caught:
        FsTaxonomyStore.open(code)

    assert "taxonomy store is declared" in str(caught.value)
    assert "tcw provision" in str(caught.value)


def test_a_provisioned_tree_store_resolves(tmp_path):
    """Criterion 2: after provisioning, reads come from the provisioned copy."""
    remote = _remote_with_tree(tmp_path)
    checkout = tmp_path / "co"
    code = _tree_node(tmp_path, "capabilities",
                      path="../orchestrator/trees/capabilities",
                      repository={"url": str(remote), "path": "trees/taxonomy",
                                  "checkout": str(checkout)})

    FsStoreProvisioner(code, "capabilities",
                       RepositoryDeclaration(url=str(remote), path="trees/taxonomy",
                                             checkout=str(checkout))).ensure_available()

    assert FsCapabilitiesStore.open(code).root == (checkout / "trees" / "taxonomy").resolve()


def test_a_local_tree_store_wins_over_a_declaration(tmp_path):
    """Criterion 4 per component. A declaration is a fallback, never an override."""
    here = tmp_path / "trees" / "taxonomy"
    here.mkdir(parents=True)
    code = _tree_node(tmp_path, "taxonomy", path=str(here),
                      repository={"url": "https://example.invalid/orchestrator.git",
                                  "path": "trees/taxonomy"})

    assert FsTaxonomyStore.open(code).root == here.resolve()


def test_a_malformed_tree_declaration_names_the_line(tmp_path):
    """Criterion 9 per component."""
    code = _tree_node(tmp_path, "capabilities",
                      path="../nowhere/capabilities",
                      repository={"ref": "main", "path": "trees/capabilities"})

    with pytest.raises(StoreDeclarationError) as caught:
        FsCapabilitiesStore.open(code)

    assert "capabilities.repository.url" in str(caught.value)


# ── the tree stores' error surfaces ─────────────────────────────────────────
#
# Criteria 1 and 9 are properties over a command surface, so they are asserted
# across that surface rather than at one call site. Child A shipped criterion 1
# holding for `tcw work list` while a malformed declaration still sent every
# work command to `tcw init`; the parametrization is what makes that shape of
# defect impossible to repeat here.

TREE_COMMANDS = [
    ["taxonomy", "list"], ["taxonomy", "path"], ["taxonomy", "show", "anything"],
    ["taxonomy", "check"],
    ["capabilities", "list"], ["capabilities", "path"],
    ["capabilities", "show", "anything"], ["capabilities", "check"],
]


def _tree_component(argv) -> str:
    return argv[0]


@pytest.mark.parametrize("argv", TREE_COMMANDS)
def test_a_declared_tree_store_is_never_reported_as_an_absent_component(
        tmp_path, monkeypatch, capsys, argv):
    """Criterion 1. The node is right in front of the command and says where its
    store comes from; answering "no tcw <component> node here — run `tcw init`"
    would point the user at the one action that makes things worse."""
    component = _tree_component(argv)
    code = _tree_node(tmp_path, component,
                      path=f"../orchestrator/trees/{component}",
                      repository={"url": "https://example.invalid/orchestrator.git",
                                  "path": f"trees/{component}"})
    monkeypatch.chdir(code)

    assert main(argv) == 1

    err = capsys.readouterr().err
    assert "no tcw" not in err, err
    assert "tcw init" not in err, err
    assert "https://example.invalid/orchestrator.git" in err, err
    assert "tcw provision" in err, err


@pytest.mark.parametrize("argv", TREE_COMMANDS)
def test_a_malformed_tree_declaration_names_the_line_from_every_command(
        tmp_path, monkeypatch, capsys, argv):
    """Criterion 9, as a property over the same surface."""
    component = _tree_component(argv)
    code = _tree_node(tmp_path, component,
                      path=f"../orchestrator/trees/{component}",
                      repository={"ref": "main", "path": f"trees/{component}"})
    monkeypatch.chdir(code)

    assert main(argv) == 1

    err = capsys.readouterr().err
    assert "no tcw" not in err, err
    assert "tcw init" not in err, err
    assert f"{component}.repository.url" in err, err


def test_a_node_without_the_component_still_says_so(tmp_path, monkeypatch, capsys):
    """Criterion 6's edge. Nothing declared and no `docs/taxonomy` — the answer
    is still "no tcw taxonomy node here", exactly as before this work."""
    code = _repo(tmp_path / "code")
    init(["work"], code, "corelib")
    monkeypatch.chdir(code)

    assert main(["taxonomy", "list"]) == 1

    assert "no tcw taxonomy node here" in capsys.readouterr().err


@pytest.mark.parametrize("argv", TREE_COMMANDS)
def test_a_declared_tree_store_is_found_even_with_no_local_component_folder(
        tmp_path, monkeypatch, capsys, argv):
    """The requester's actual shape, and the one the other cases cannot reach.

    A checkout that cloned only the code repository has no `docs/taxonomy/`,
    because the taxonomy lives in the other repository — that is the whole
    premise. `find_node` decided "does this node have this component?" by looking
    for that folder, so it answered None before the resolution ladder ever ran,
    and the declaration went unread."""
    component = _tree_component(argv)
    code = _repo(tmp_path / "code")
    init(["work"], code, "corelib")            # the component is deliberately absent
    path = code / "tcw-config.yaml"
    config = yaml.safe_load(path.read_text()) or {}
    config[component] = {"repository": {"url": "https://example.invalid/orchestrator.git",
                                        "path": f"trees/{component}"}}
    path.write_text(yaml.safe_dump(config, sort_keys=False))
    monkeypatch.chdir(code)

    assert main(argv) == 1

    err = capsys.readouterr().err
    assert "no tcw" not in err, err
    assert "tcw init" not in err, err
    assert "https://example.invalid/orchestrator.git" in err, err
    assert "tcw provision" in err, err


@pytest.mark.parametrize("component", ["taxonomy", "capabilities"])
def test_validate_reports_a_declared_tree_store_rather_than_aborting(
        tmp_path, monkeypatch, capsys, component):
    """`tcw validate`'s job is to list configuration faults, so a store it cannot
    open is a problem to report, not a reason to stop. Only the work branch was
    guarded; the tree branches let the exception escape to the top-level
    handler, which prints one line and abandons every other check."""
    code = _tree_node(tmp_path, component,
                      path=f"../orchestrator/trees/{component}",
                      repository={"url": "https://example.invalid/orchestrator.git",
                                  "path": f"trees/{component}"})
    monkeypatch.chdir(code)

    assert main(["validate"]) == 1

    err = capsys.readouterr().err
    assert f"{component} check:" in err, err
    assert "has not been provisioned here" in err, err
    assert "tcw provision" in err, err


# ── the provisioning verb, across components ────────────────────────────────

@pytest.mark.parametrize("component", ["taxonomy", "capabilities"])
def test_provision_obtains_a_declared_tree_store(tmp_path, monkeypatch, capsys,
                                                 component):
    """Criteria 2 and 5 through the command, not the adapter."""
    remote = _remote_with_tree(tmp_path, inner=f"trees/{component}")
    checkout = tmp_path / "co"
    code = _tree_node(tmp_path, component,
                      path=f"../orchestrator/trees/{component}",
                      repository={"url": str(remote), "path": f"trees/{component}",
                                  "checkout": str(checkout)})
    monkeypatch.chdir(code)

    assert main(["provision", "--component", component]) == 0

    assert (checkout / "trees" / component).is_dir()
    assert main([component, "path"]) == 0
    assert capsys.readouterr().out.strip().endswith(f"trees/{component}")


@pytest.mark.parametrize("component", ["taxonomy", "capabilities", "work"])
def test_a_local_store_wins_at_the_command_for_every_component(
        tmp_path, monkeypatch, capsys, component):
    """Criterion 4, per component.

    This is the defect child A's fourth review pass found, in the shape that
    makes it invisible: `run_provision` loops over components and asked
    `FsWorkStore.open` inside the loop. Correct while the tuple held one value,
    and wrong for every value added to it — so a taxonomy declaration would be
    cloned because the *work* store did not resolve."""
    remote = _remote_with_tree(tmp_path, inner="trees/thing")
    if component == "work":
        here = _remote_with_store(tmp_path, inner="local/work") / "local" / "work"
    else:
        here = tmp_path / "local" / component
        here.mkdir(parents=True)
    code = _tree_node(tmp_path, component, path=str(here),
                      repository={"url": str(remote), "path": "trees/thing",
                                  "checkout": str(tmp_path / "co")})
    monkeypatch.chdir(code)

    calls: list[list[str]] = []
    monkeypatch.setattr(fs.FsStoreProvisioner, "_run",
                        lambda self, argv, **kw: calls.append(list(argv)))

    assert main(["provision", "--component", component]) == 0

    assert calls == [], calls
    assert "already available" in capsys.readouterr().out
    assert not (tmp_path / "co").exists()


def test_each_declared_component_is_provisioned_independently(tmp_path, monkeypatch,
                                                              capsys):
    """Criterion 5. Two declarations, one good and one naming nothing: the good
    one lands, the bad one is reported, and neither result is the other's."""
    good = _remote_with_tree(tmp_path, inner="trees/taxonomy")
    code = _tree_node(tmp_path, "taxonomy",
                      path="../nowhere/taxonomy",
                      repository={"url": str(good), "path": "trees/taxonomy",
                                  "checkout": str(tmp_path / "co-good")})
    path = code / "tcw-config.yaml"
    config = yaml.safe_load(path.read_text())
    config["capabilities"] = {
        "path": "../nowhere/capabilities",
        "repository": {"url": str(good), "path": "trees/not-here",
                       "checkout": str(tmp_path / "co-bad")}}
    path.write_text(yaml.safe_dump(config, sort_keys=False))
    monkeypatch.chdir(code)

    assert main(["provision"]) == 1

    captured = capsys.readouterr()
    assert (tmp_path / "co-good" / "trees" / "taxonomy").is_dir()
    assert "taxonomy: obtained" in captured.out
    assert "capabilities" in captured.err
    assert not (tmp_path / "co-bad").exists()


@pytest.mark.parametrize("component", ["taxonomy", "capabilities"])
def test_init_scaffolds_a_tree_store_at_a_configured_location(tmp_path, monkeypatch,
                                                              component):
    """`--work-path` grows companions. The scaffolding difference stays: work
    gets its status folders, a tree component gets the directory."""
    code = _repo(tmp_path / "code")
    monkeypatch.chdir(code)
    elsewhere = tmp_path / "trees" / component

    assert main(["init", "--id", "corelib", f"--{component}-path", str(elsewhere),
                 component]) == 0

    assert elsewhere.is_dir()
    assert yaml.safe_load((code / "tcw-config.yaml").read_text())[component]["path"] \
        == str(elsewhere)
    assert STORE_CLASSES[component].open(code).root == elsewhere.resolve()


@pytest.mark.parametrize("argv", TREE_COMMANDS)
@pytest.mark.parametrize("with_path", [True, False], ids=["with-path", "no-path"])
def test_a_malformed_tree_declaration_is_named_with_or_without_a_configured_path(
        tmp_path, monkeypatch, capsys, argv, with_path):
    """Criterion 9, finally tested as the property it was written as.

    The earlier cases all set `<component>.path`, and passed. Without one the
    same config answered "no tcw taxonomy node here — run `tcw init`": a
    malformed declaration parses to `(None, problems)`, so the ladder saw no
    declaration, took rule 4, and a tree store's rule 4 validates nothing and
    cannot fail — so the problems were dropped on a path that never raised.

    Both shapes are the same user with the same typo, and the second is the more
    likely one: someone adding a `repository` block to a project whose tree has
    always been at the default location has no reason to add a `path` too."""
    component = _tree_component(argv)
    section = {"repository": {"ref": "main", "path": f"trees/{component}"}}
    if with_path:
        section["path"] = f"../orchestrator/trees/{component}"
    code = _repo(tmp_path / "code")
    init(["work"], code, "corelib")
    config_path = code / "tcw-config.yaml"
    config = yaml.safe_load(config_path.read_text()) or {}
    config[component] = section
    config_path.write_text(yaml.safe_dump(config, sort_keys=False))
    monkeypatch.chdir(code)

    assert main(argv) == 1

    err = capsys.readouterr().err
    assert "no tcw" not in err, err
    assert "tcw init" not in err, err
    assert f"{component}.repository.url" in err, err


@pytest.mark.parametrize("component", ["taxonomy", "capabilities"])
def test_a_usable_local_tree_still_masks_an_unused_malformed_declaration(
        tmp_path, monkeypatch, capsys, component):
    """The other side of the same rule, and the reason the fix is not "always
    raise". A tree that is really here keeps working even when a declaration
    nobody needs is malformed — the contract the work store already holds."""
    code = _repo(tmp_path / "code")
    init([component], code, "corelib")          # the default tree exists
    config_path = code / "tcw-config.yaml"
    config = yaml.safe_load(config_path.read_text()) or {}
    config[component] = {"repository": {"ref": "main"}}
    config_path.write_text(yaml.safe_dump(config, sort_keys=False))
    monkeypatch.chdir(code)

    assert main([component, "list"]) == 0


# ── provisioning a connected project ─────────────────────────────────────────


def _node_repo(path: Path, project_id: str, connected: dict | None = None) -> Path:
    """A committed git repository holding one tcw node."""
    _repo(path)
    init(["work"], path, project_id)
    if connected:
        config_path = path / "tcw-config.yaml"
        config = yaml.safe_load(config_path.read_text()) or {}
        config["connected-projects"] = connected
        config_path.write_text(yaml.safe_dump(config, sort_keys=False))
    subprocess.run(["git", "-C", str(path), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(path), "commit", "-qm", "node"], check=True)
    return path


def test_a_declared_connected_project_is_obtained(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    away = _node_repo(tmp_path / "away", "away-project",
                      {"parent": {"here-project": "../here"}})
    here = _node_repo(
        tmp_path / "here", "here-project",
        {"children": {"away-project": {"path": "../away-not-here",
                                       "repository": {"url": str(away), "ref": "main"}}}},
    )
    monkeypatch.chdir(here)

    assert main(["provision", "--dry-run"]) == 0
    planned = capsys.readouterr().out
    assert str(away) in planned and "would obtain" in planned

    assert main(["provision"]) == 0
    assert "obtained" in capsys.readouterr().out

    from tcw.store.project import FsProjectRegistry
    registry = FsProjectRegistry.open(here)
    registry.require_valid()
    assert [c.id for c in registry.children()] == ["away-project"]

    assert main(["provision"]) == 0
    assert "already available" in capsys.readouterr().out


def test_provisioning_follows_a_declaration_inside_an_obtained_node(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    c = _node_repo(tmp_path / "c", "c-project",
                   {"parent": {"b-project": "../b"}})
    b = _node_repo(
        tmp_path / "b", "b-project",
        {"parent": {"a-project": "../a"},
         "children": {"c-project": {"path": "../c-not-here",
                                    "repository": {"url": str(c), "ref": "main"}}}},
    )
    a = _node_repo(
        tmp_path / "a", "a-project",
        {"children": {"b-project": {"path": "../b-not-here",
                                    "repository": {"url": str(b), "ref": "main"}}}},
    )
    monkeypatch.chdir(a)

    assert main(["provision", "--dry-run"]) == 0
    planned = capsys.readouterr().out
    assert str(b) in planned
    assert "cannot be listed until it is obtained" in planned
    # `c` is two hops away, behind a node this run has not fetched.
    assert "c-project" not in planned

    assert main(["provision"]) == 0
    out = capsys.readouterr().out
    assert "b-project" in out and "c-project" in out


def test_two_entries_naming_one_repository_share_a_working_copy(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    away = _node_repo(tmp_path / "away", "away-project")
    declaration = {"url": str(away), "ref": "main"}
    here = _node_repo(
        tmp_path / "here", "here-project",
        {"parent": {"away-project": {"path": "../away-not-here",
                                     "repository": dict(declaration)}},
         "children": {"away-project": {"path": "../away-not-here",
                                       "repository": dict(declaration)}}},
    )
    monkeypatch.chdir(here)
    assert main(["provision"]) == 0
    cache = tmp_path / "cache" / "tcw" / "stores"
    assert len(list(cache.iterdir())) == 1


def test_a_repository_with_no_node_at_the_declared_path_is_refused(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    away = _repo(tmp_path / "away")
    (away / "README.md").write_text("no node here\n")
    subprocess.run(["git", "-C", str(away), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(away), "commit", "-qm", "init"], check=True)
    here = _node_repo(
        tmp_path / "here", "here-project",
        {"children": {"away-project": {"path": "../away-not-here",
                                       "repository": {"url": str(away), "ref": "main"}}}},
    )
    monkeypatch.chdir(here)
    assert main(["provision"]) == 1
    assert "has no tcw node at" in capsys.readouterr().err
    assert not (tmp_path / "cache" / "tcw" / "stores").exists() or not list(
        (tmp_path / "cache" / "tcw" / "stores").iterdir())


def test_an_occupied_checkout_is_refused_before_any_fetch(tmp_path, monkeypatch, capsys):
    away = _node_repo(tmp_path / "away", "away-project")
    squatter = _repo(tmp_path / "squatter")
    (squatter / "f").write_text("x")
    subprocess.run(["git", "-C", str(squatter), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(squatter), "commit", "-qm", "init"], check=True)
    here = _node_repo(
        tmp_path / "here", "here-project",
        {"children": {"away-project": {
            "path": "../away-not-here",
            "repository": {"url": str(away), "ref": "main",
                           "checkout": str(squatter)}}}},
    )
    monkeypatch.chdir(here)
    assert main(["provision"]) == 1
    assert (squatter / "f").read_text() == "x"


def test_a_malformed_connected_declaration_refuses_and_names_the_line(tmp_path, monkeypatch, capsys):
    here = _node_repo(
        tmp_path / "here", "here-project",
        {"children": {"away-project": {"repository": {"ref": "main"}}}},
    )
    monkeypatch.chdir(here)
    assert main(["provision"]) == 1
    assert "url: expected a non-empty string" in capsys.readouterr().err
