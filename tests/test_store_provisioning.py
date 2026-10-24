"""Declaring a component store's home repository, and provisioning it.

The subject is `work.repository`: the portable half of the store location, which
says where a store *comes from* rather than where it happens to sit on one disk.

**No test here reaches the network.** Where a remote is needed, it is a real bare
repository in `tmp_path` — Git does not care that the URL is a local path, and
the code under test never learns the difference.
"""

from __future__ import annotations

import os
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
from tcw.store import checkouts, fs
from tcw.store.fs import (STORE_CLASSES, FsCapabilitiesStore, FsStoreProvisioner, FsTaxonomyStore, WorkLocation, init)
from tcw.store.project import FsProjectRegistry
from tcw.validate import validate


WHERE = "work.repository"


from nodeconfig import set_component_key
from tests.projectfiles import config_file, write_config, write_config_file, write_manifest


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


def _write_config(project_root: Path, **work: object) -> None:
    path = config_file(project_root)
    config = yaml.safe_load(path.read_text()) or {}
    config.setdefault("work", {}).update(work)
    write_config_file(path, yaml.safe_dump(config, sort_keys=False))


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


def _provisioner(tmp_path, project_root: Path, remote: Path, **overrides):
    """A provisioner whose cache lands inside `tmp_path`, never the real
    `~/.cache`."""
    declaration = RepositoryDeclaration(
        url=str(remote), path=overrides.pop("path", "docs/work/corelib"), **overrides)
    return FsStoreProvisioner(project_root, "work", declaration)


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


def test_an_available_store_is_never_fetched_into(tmp_path, monkeypatch):
    """TCW-73 Design 8.4: keeping an available store fresh is the project's
    own business; `ensure_available` on one runs no git at all."""
    code = _repo(tmp_path / "code")
    init(["work"], code, "corelib")
    remote = _remote_with_store(tmp_path)
    provisioner = _provisioner(tmp_path, code, remote, ref="main")
    provisioner.ensure_available()

    def no_git(*args, **kwargs):
        raise AssertionError(f"ran {args}")
    monkeypatch.setattr(fs, "_git", no_git)
    assert provisioner.ensure_available().action == "available"


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


# ── repository identity, kept apart from cache naming ────────────────────────

def test_the_cache_key_is_unchanged():
    """`_cache_key` names directories that already exist on users' machines.

    Pinned to literal strings rather than to a property, because the failure
    this guards is a *silent* rename: every provisioned store becomes
    unreachable and a fresh clone appears beside it, with nothing raised. The
    four cases differ only in URL spelling and ref, and their readable halves
    are identical — so only the digest tells them apart, and the digest is
    exactly what a shared normalizer would change.
    """
    expected = {
        ("https://github.com/Example-Org/workspace.git", "main"):
            "github.com-example-org-workspace-ec7917e6e4c3",
        ("https://github.com/Example-Org/workspace", "main"):
            "github.com-example-org-workspace-f86dcb6399fe",
        ("git@github.com:Example-Org/workspace.git", "main"):
            "github.com-example-org-workspace-1a37f0559bb2",
        ("https://github.com/Example-Org/workspace.git", "dev"):
            "github.com-example-org-workspace-c6c86f756591",
    }
    for (url, ref), key in expected.items():
        assert checkouts._cache_key(RepositoryDeclaration(url=url, ref=ref)) == key


@pytest.mark.parametrize("spelling", [
    "https://github.com/Example-Org/workspace",
    "https://github.com/Example-Org/workspace.git",
    "https://github.com/Example-Org/workspace/",
    "  https://github.com/Example-Org/workspace.git  ",
    "git@github.com:Example-Org/workspace.git",
])
def test_two_spellings_of_one_repository_normalize_alike(spelling):
    """The question `_cache_key` deliberately answers the other way.

    A declaration and a connected project routinely spell one repository
    differently — one config was written for HTTPS, the other for SSH — and the
    new resolution rung has to see through that.
    """
    canonical = checkouts.normalized_url(
        "https://github.com/Example-Org/workspace")
    assert checkouts.normalized_url(spelling) == canonical


@pytest.mark.parametrize("other", [
    "https://github.com/Example-Org/core",
    "https://github.com/Someone-Else/workspace",
    "https://gitlab.invalid/Example-Org/workspace",
])
def test_two_different_repositories_do_not_normalize_alike(other):
    assert checkouts.normalized_url(other) != checkouts.normalized_url(
        "https://github.com/Example-Org/workspace")


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
    _write_config(code, path=os.path.relpath(here, code),
                  repository={"url": str(_remote_with_store(tmp_path)),
                              "path": "docs/work/corelib"})

    assert WorkLocation.open(code).root == here.resolve()
    assert not (tmp_path / "cache" / "tcw").exists(), \
        "resolution must not provision, and must not even look in the cache"


# ── the registry rung: a store inside a project already on this disk ─────────
#
# The flat-workspace case from issue #31. The config is written for a nested
# layout and is correct there; this machine cloned the same repositories side by
# side, and says so with `TCW_PROJECT_*`.


def _flat_workspace(tmp_path, monkeypatch, *, component="work",
                    inner="docs/work/corelib", url=None, ref="main",
                    configured_path="../orchestrator/stores/corelib"):
    """A child whose parent is a checkout of the repository its store is
    declared in, laid out flat rather than nested.

    Nothing is defaulted that the resolution path branches on: the configured
    path, the declared url, and the parent's real location are all arguments,
    because a fixture that fixed any of them would make a cell of this ladder
    unreachable by construction.
    """
    orchestration = _repo(tmp_path / "orchestration")
    store = orchestration / inner
    for name in (("inbox", *("backlog", "active", "review", "completed", "discarded"))
                 if component == "work" else ()):
        (store / name).mkdir(parents=True, exist_ok=True)
        (store / name / ".gitkeep").write_text("")
    if component != "work":
        store.mkdir(parents=True, exist_ok=True)
        (store / ".gitkeep").write_text("")
    subprocess.run(["git", "-C", str(orchestration), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(orchestration), "commit", "-qm", "seed"], check=True)

    code = _repo(tmp_path / "core")
    init([component], code, "core")
    url = url if url is not None else "https://github.invalid/acme/orchestration.git"

    write_config(orchestration, "id: orchestration\nchildren:\n- core\n")
    write_manifest(orchestration, {"core": os.path.relpath(code, orchestration)})
    config = yaml.safe_load((code / ".tcw/tcw-config.yaml").read_text()) or {}
    config.setdefault(component, {}).update({
        "path": configured_path,
        "repository": {"url": url, "ref": ref, "path": inner},
    })
    config["parents"] = ["orchestration"]
    write_config(code, yaml.safe_dump(config, sort_keys=False))
    write_manifest(code, {"orchestration": {
        "path": "../orchestrator",              # right for the nested layout, wrong here
        "repository": f"{url}#{ref}",
    }})

    monkeypatch.setenv("TCW_PROJECT_ORCHESTRATION", str(orchestration))
    return code, orchestration, store


def test_a_store_in_a_project_the_registry_located_is_used(tmp_path, monkeypatch):
    code, _orchestration, store = _flat_workspace(tmp_path, monkeypatch)

    assert WorkLocation.open(code).root == store.resolve()


def test_a_ref_mismatch_does_not_stop_the_registry_rung(tmp_path, monkeypatch, capsys):
    """A checkout the user is standing in wins whatever branch it is on, which
    is what rung 1 already does with a configured path."""
    code, orchestration, store = _flat_workspace(tmp_path, monkeypatch, ref="main")
    subprocess.run(["git", "-C", str(orchestration), "checkout", "-q", "-b", "other"],
                   check=True)

    assert WorkLocation.open(code).root == store.resolve()
    assert "ref" not in capsys.readouterr().err


APP_URL = "https://github.invalid/acme/app.git"


def _project(root: Path, project_id: str, *, parent=(), upstream=(), children=()) -> Path:
    """`project_id` at `root`, naming `parent` as parents that pass every axis,
    `upstream` as parents that pass none, and `children`, all by ID only."""
    data: dict = {"id": project_id}
    parents = [*parent, *({"id": i, "inherit": "none"} for i in upstream)]
    if parents:
        data["parents"] = parents
    if children:
        data["children"] = list(children)
    write_config(root, yaml.safe_dump(data, sort_keys=False))
    return root.resolve()


def _store_in_app(tmp_path: Path) -> tuple[Path, Path]:
    """`core`, whose work store lives in the repository `APP_URL`, and a
    checkout of that repository at `app-repo` holding the project `server` at
    `apps/server` and the store at `docs/work/core`."""
    checkout = tmp_path / "app-repo"
    server = _project(checkout / "apps" / "server", "server")
    store = _local_store(checkout / "docs" / "work" / "core")
    core = _repo(tmp_path / "core")
    init(["work"], core, "core")
    _write_config(core, path="../absent",
                  repository={"url": APP_URL, "path": "docs/work/core"})
    config = yaml.safe_load(config_file(core).read_text())
    config["parents"] = [{"id": "server", "inherit": "none"}]
    write_config(core, yaml.safe_dump(config, sort_keys=False))
    write_manifest(core, {"server": {"path": "../app-repo/apps/server",
                                     "repository": f"{APP_URL}#main",
                                     "subfolder": "apps/server"}})
    return core, store


def test_ac22_the_subfolder_is_removed_from_the_found_folder(tmp_path):
    core, store = _store_in_app(tmp_path)
    assert FsProjectRegistry.open(core).checkout_of(APP_URL) == (tmp_path / "app-repo").resolve()
    assert WorkLocation.open(core).root == store.resolve()


def test_ac22_a_found_folder_not_ending_in_the_subfolder_gives_no_answer(
        tmp_path, monkeypatch):
    core, _store = _store_in_app(tmp_path)
    elsewhere = _project(tmp_path / "elsewhere" / "srv", "server")
    monkeypatch.setenv("TCW_PROJECT_SERVER", str(elsewhere))
    registry = FsProjectRegistry.open(core)
    assert registry.found("server") == {"by": "variable", "name": "TCW_PROJECT_SERVER"}
    assert registry.checkout_of(APP_URL) is None
    # The store then resolves as it would with no match: with neither the
    # checkout nor the cache holding it, it is not provisioned here.
    with pytest.raises(StoreNotProvisioned) as found_elsewhere:
        WorkLocation.open(core)
    monkeypatch.delenv("TCW_PROJECT_SERVER")
    write_manifest(core, {"server": "../app-repo/apps/server"})
    assert FsProjectRegistry.open(core).checkout_of(APP_URL) is None
    with pytest.raises(StoreNotProvisioned) as no_match:
        WorkLocation.open(core)
    assert str(found_elsewhere.value) == str(no_match.value)


def test_ac22_the_rung_reads_manifests_in_the_lookups_order(tmp_path):
    """Design 6.4: the active project's manifests, then its ancestors', then
    its descendants'; the first matching entry for a found project answers."""
    top = _project(tmp_path / "top", "top", children=["mid"])
    mid = _project(tmp_path / "top" / "mid", "mid", parent=["top"], children=["kid"],
                   upstream=["x", "y"])
    kid = _project(tmp_path / "top" / "mid" / "kid", "kid", parent=["mid"])
    x = _project(tmp_path / "x", "x")
    y = _project(tmp_path / "y", "y")
    write_manifest(top, {"mid": "mid", "x": {"path": "../x",
                                             "repository": f"{APP_URL}#main"}})
    write_manifest(mid, {"kid": "kid", "top": ".."})
    write_manifest(kid, {"mid": "..",
                         "y": {"path": "../../../y", "repository": f"{APP_URL}#main"}})
    assert FsProjectRegistry.open(mid).checkout_of(APP_URL) == x
    write_manifest(mid, {"y": {"path": "../../y", "repository": f"{APP_URL}#main"}})
    assert FsProjectRegistry.open(mid).checkout_of(APP_URL) == y
    assert FsProjectRegistry.open(kid).checkout_of(APP_URL) == y


def test_ac22_an_entry_for_a_project_not_found_is_passed_over(tmp_path):
    """An entry matching the URL whose project is not on this machine gives
    no answer; the next matching entry does."""
    app = _project(tmp_path / "app", "app", upstream=["gone", "lib"])
    lib = _project(tmp_path / "lib", "lib")
    write_manifest(app, {"gone": {"path": "../gone", "repository": f"{APP_URL}#main"},
                         "lib": {"path": "../lib", "repository": f"{APP_URL}#main"}})
    assert FsProjectRegistry.open(app).checkout_of(APP_URL) == lib


def test_provision_reports_a_registry_resolved_store_as_available(
    tmp_path, monkeypatch, capsys,
):
    """No production change backs this: `run_provision` already asks the ladder
    before provisioning, so the new rung reaches the command for free."""
    code, _orchestration, _store = _flat_workspace(tmp_path, monkeypatch)
    monkeypatch.chdir(code)
    calls = _count_git(monkeypatch)

    assert main(["provision"]) == 0

    assert "already available" in capsys.readouterr().err
    assert not any("clone" in argv or "fetch" in argv for argv in calls), calls


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
        path=os.path.relpath(here, code),
        repository={"url": str(remote), "path": "docs/work/corelib"},
    )
    monkeypatch.chdir(code)

    calls = _count_git(monkeypatch)
    assert main(["provision"]) == 0

    assert "already available" in capsys.readouterr().err
    assert not any("clone" in argv or "fetch" in argv for argv in calls), calls
    assert not (tmp_path / "cache" / "tcw").exists()


def test_a_declared_node_whose_default_store_exists_uses_it(tmp_path):
    """`work.path` unset, `docs/work` present, a declaration alongside: the real
    store on this machine still wins."""
    code = _repo(tmp_path / "code")
    init(["work"], code, "corelib")
    _write_config(code, repository={"url": str(_remote_with_store(tmp_path)),
                                    "path": "docs/work/corelib"})

    assert WorkLocation.open(code).root == (code / "docs" / "work").resolve()


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
    ["work", "reconcile", "anything"],
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
    `ValueError` that `find_component_project` discards."""
    monkeypatch.chdir(_declared_but_malformed(tmp_path))

    assert main(argv) == 1

    err = capsys.readouterr().err
    assert "no tcw work node here" not in err
    assert "tcw init" not in err
    assert "work.repository.url" in err, err


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
    ["work", "reconcile", "anything"],
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

    problems = [str(f) for f in validate(code)]

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
                             (child, "parents", "parent-project")):
        path = config_file(root)
        config = yaml.safe_load(path.read_text())
        config[key] = [other]
        write_config_file(path, yaml.safe_dump(config, sort_keys=False))
        write_manifest(root, {other: f"../{other.split('-')[0]}"})

    monkeypatch.chdir(parent)
    assert main(["projects", "list"]) == 0

    # A registered child is listed even when its store is not usable here:
    # omitting it made a project with children read as having none.
    assert capsys.readouterr().out.split() == ["parent-project", "child-project"]


# ── the `tcw provision` verb ─────────────────────────────────────────────────

def test_provision_refresh_is_a_usage_error(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit) as stop:
        main(["provision", "--refresh"])
    assert stop.value.code == 2


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

    out = capsys.readouterr().err
    assert str(remote) in out
    assert out.index(str(remote)) < out.index("obtained")


def test_a_second_provision_reports_available_and_contacts_nothing(tmp_path,
                                                                   monkeypatch, capsys):
    monkeypatch.chdir(_declared_against(tmp_path, _remote_with_store(tmp_path)))
    assert main(["provision"]) == 0
    capsys.readouterr()

    calls = _count_git(monkeypatch)
    assert main(["provision"]) == 0

    assert "already available" in capsys.readouterr().err
    assert calls == []


def test_a_dry_run_from_the_cli_contacts_nothing(tmp_path, monkeypatch, capsys):
    code = _declared_against(tmp_path, _remote_with_store(tmp_path))
    monkeypatch.chdir(code)

    calls = _count_git(monkeypatch)
    assert main(["provision", "--dry-run"]) == 0

    assert "would obtain" in capsys.readouterr().err
    assert calls == []
    assert not (tmp_path / "cache" / "tcw").exists()


def test_a_node_declaring_nothing_says_so_and_succeeds(tmp_path, monkeypatch, capsys):
    code = _repo(tmp_path / "code")
    init(["work"], code, "corelib")
    monkeypatch.chdir(code)

    assert main(["provision"]) == 0
    assert "Nothing to provision" in capsys.readouterr().err


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


@pytest.mark.parametrize("broken, words", [
    ("id: corelib\n? [a]\n: 1\n", "a mapping key must be a single value"),
    ("id: corelib\nx: [\n", "while parsing a flow node"),
    ("id: corelib\nid: other\n", "duplicate key: 'id'"),
])
def test_a_config_that_cannot_be_parsed_is_an_error_not_nothing(tmp_path, monkeypatch,
                                                                capsys, broken, words):
    """It read as declaring nothing, so the command said "Nothing to
    provision" and succeeded."""
    code = _repo(tmp_path / "code")
    init(["work"], code, "corelib")
    write_config(code, broken)
    monkeypatch.chdir(code)

    assert main(["provision"]) == 1
    err = capsys.readouterr().err
    assert err.startswith("tcw provision: malformed "), err
    assert f"{code.name}/.tcw/tcw-config.yaml: " in err, err
    assert words in err and "Traceback" not in err, err
    assert "Nothing to provision" not in err, err


@pytest.mark.parametrize("command", [["provision"], ["init"]])
def test_a_config_that_is_not_utf_8_is_named(tmp_path, monkeypatch, capsys, command):
    """Pre-freeze clean-up, final fixes: the codec's own words named no
    file. The shared reader names it, and the file is left as it was."""
    code = _repo(tmp_path / "code")
    init(["work"], code, "corelib")
    broken = b"id: corelib\n# caf\xe9\n"
    write_config(code, broken)
    monkeypatch.chdir(code)

    assert main(command) == 1
    err = capsys.readouterr().err
    assert err == (f"tcw {command[0]}: {code / '.tcw/tcw-config.yaml'}: is not valid "
                   f"UTF-8 text (byte 0xe9 at position 17)\n"), err
    assert (code / ".tcw/tcw-config.yaml").read_bytes() == broken


def test_a_failure_exits_non_zero_and_names_the_cause(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(_declared_against(tmp_path, tmp_path / "no-such-repository"))

    assert main(["provision"]) == 1
    assert "git clone failed" in capsys.readouterr().err


def test_provision_outside_a_project_says_so(tmp_path, monkeypatch, capsys):
    plain = tmp_path / "not-a-node"
    plain.mkdir()
    monkeypatch.chdir(plain)

    assert main(["provision"]) == 1
    assert "tcw provision: no TCW project here" in capsys.readouterr().err


def test_limiting_to_undeclared_work_is_a_no_op(tmp_path, monkeypatch, capsys):
    code = _repo(tmp_path / "code")
    init(["work"], code, "corelib")
    monkeypatch.chdir(code)

    assert main(["provision", "--component", "work"]) == 0
    assert "Nothing to provision" in capsys.readouterr().err


# ── nothing else reaches the network ─────────────────────────────────────────

@pytest.mark.parametrize("argv", [
    ["work", "list"], ["work", "show", "an-item"], ["work", "path"],
    ["projects", "list"], ["work", "docs"], ["validate"],
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
    config_path = config_file(code)
    config = yaml.safe_load(config_path.read_text())
    config["taxonomy"] = {
        "repository": {"url": str(remote), "path": "trees/taxonomy",
                       "checkout": str(tmp_path / "co")}
    }
    write_config_file(config_path, yaml.safe_dump(config, sort_keys=False))
    monkeypatch.chdir(code)

    assert main(["provision", "--component", "taxonomy"]) == 0

    assert (tmp_path / "co" / "trees" / "taxonomy").is_dir()
    assert "taxonomy: obtained" in capsys.readouterr().err
    # The refusal that made the narrowing necessary is gone: a tree declaration
    # is no longer measured against the work store's status folders.
    assert main(["taxonomy", "path"]) == 0


def test_an_unknown_component_is_still_refused(tmp_path, monkeypatch):
    """Widening the tuple is not opening it."""
    monkeypatch.chdir(_repo(tmp_path / "code"))
    with pytest.raises(SystemExit):
        main(["provision", "--component", "nonsense"])


def test_validate_reports_a_malformed_declaration_when_the_store_is_absent(tmp_path):
    """Criterion 10 is about the declaration error, even when no local store can
    be opened to report it through ``store.check()``."""
    code = _repo(tmp_path / "code")
    init(["work"], code, "corelib")
    shutil.rmtree(code / "docs" / "work")
    _write_config(code, repository={"path": "docs/work/corelib"})

    problems = [str(f) for f in validate(code)]

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
    path = config_file(code)
    config = yaml.safe_load(path.read_text()) or {}
    config.setdefault(component, {}).update(section)
    write_config_file(path, yaml.safe_dump(config, sort_keys=False))
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
    code = _tree_node(tmp_path, "taxonomy",
                      path=os.path.relpath(elsewhere, tmp_path / "code"))

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
    code = _tree_node(tmp_path, "taxonomy", path=os.path.relpath(here, tmp_path / "code"),
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
    ["taxonomy", "search", "anything"],
    ["capabilities", "list"], ["capabilities", "path"],
    ["capabilities", "show", "anything"], ["capabilities", "search", "anything"],
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
    is still that there is no taxonomy store here."""
    code = _repo(tmp_path / "code")
    init(["work"], code, "corelib")
    monkeypatch.chdir(code)

    assert main(["taxonomy", "list"]) == 1

    assert "no taxonomy store here" in capsys.readouterr().err


@pytest.mark.parametrize("argv", TREE_COMMANDS)
def test_a_declared_tree_store_is_found_even_with_no_local_component_folder(
        tmp_path, monkeypatch, capsys, argv):
    """The requester's actual shape, and the one the other cases cannot reach.

    A checkout that cloned only the code repository has no `docs/taxonomy/`,
    because the taxonomy lives in the other repository — that is the whole
    premise. `find_component_project` decided "does this node have this component?" by looking
    for that folder, so it answered None before the resolution ladder ever ran,
    and the declaration went unread."""
    component = _tree_component(argv)
    code = _repo(tmp_path / "code")
    init(["work"], code, "corelib")            # the component is deliberately absent
    path = config_file(code)
    config = yaml.safe_load(path.read_text()) or {}
    config[component] = {"repository": {"url": "https://example.invalid/orchestrator.git",
                                        "path": f"trees/{component}"}}
    write_config_file(path, yaml.safe_dump(config, sort_keys=False))
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

    out = capsys.readouterr().out
    assert f"error: .tcw/tcw-config.yaml: {component}: " in out, out
    assert "has not been provisioned here" in out, out
    assert "tcw provision" in out, out


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
    code = _tree_node(tmp_path, component, path=os.path.relpath(here, tmp_path / "code"),
                      repository={"url": str(remote), "path": "trees/thing",
                                  "checkout": str(tmp_path / "co")})
    monkeypatch.chdir(code)

    calls: list[list[str]] = []
    monkeypatch.setattr(fs.FsStoreProvisioner, "_run",
                        lambda self, argv, **kw: calls.append(list(argv)))

    assert main(["provision", "--component", component]) == 0

    assert calls == [], calls
    assert "already available" in capsys.readouterr().err
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
    path = config_file(code)
    config = yaml.safe_load(path.read_text())
    config["capabilities"] = {
        "path": "../nowhere/capabilities",
        "repository": {"url": str(good), "path": "trees/not-here",
                       "checkout": str(tmp_path / "co-bad")}}
    write_config_file(path, yaml.safe_dump(config, sort_keys=False))
    monkeypatch.chdir(code)

    assert main(["provision"]) == 1

    captured = capsys.readouterr()
    assert (tmp_path / "co-good" / "trees" / "taxonomy").is_dir()
    assert "taxonomy: obtained" in captured.err
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

    assert main(["init", "--id", "corelib", f"--{component}-path",
                 f"../trees/{component}", component]) == 0

    assert elsewhere.is_dir()
    assert yaml.safe_load((code / ".tcw/tcw-config.yaml").read_text())[component]["path"] \
        == f"../trees/{component}"
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
    config_path = config_file(code)
    config = yaml.safe_load(config_path.read_text()) or {}
    config[component] = section
    write_config_file(config_path, yaml.safe_dump(config, sort_keys=False))
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
    config_path = config_file(code)
    config = yaml.safe_load(config_path.read_text()) or {}
    config[component] = {"repository": {"ref": "main"}}
    write_config_file(config_path, yaml.safe_dump(config, sort_keys=False))
    monkeypatch.chdir(code)

    assert main([component, "list"]) == 0


# ── what falls through the ladder, and what must not ─────────────────────────

def test_a_federation_error_is_not_reported_as_unprovisioned(tmp_path):
    """Rules 1 and 2 swallowed every `ValueError`, so a store that was present
    and failed to open was answered with `tcw provision` — which then succeeded
    and left the store exactly as unopenable."""
    node = _repo(tmp_path / "node")
    init(["capabilities"], node, "node-project")
    _write_config(node, retain={"completed": True})     # unrelated; keeps shape
    config_path = config_file(node)
    config = yaml.safe_load(config_path.read_text())
    config["capabilities"] = {
        "repository": {"url": "https://example.invalid/ledger.git"},
    }
    write_config_file(config_path, yaml.safe_dump(config, sort_keys=False))
    # A store that is right here, and whose own config is wrong: it still
    # holds the key TCW 4.0 removed, written here on purpose.
    set_component_key(node, "capabilities", "extends", ["nope"])

    with pytest.raises(ValueError) as excinfo:
        FsCapabilitiesStore.open(node)
    message = str(excinfo.value)
    assert "'capabilities.extends' was removed in TCW 4.0" in message
    assert "tcw provision" not in message
    assert not isinstance(excinfo.value, StoreNotProvisioned)


# ── a leftover pre-2.5.0 config file in a provisioned tree ───────────────────

def test_a_leftover_in_a_provisioned_tree_is_reported_by_its_absolute_path(tmp_path):
    """The tree lives in another repository's clone, outside the node, and
    `validate` never runs its check (there is no `docs/taxonomy` here) — so the
    leftover is named by its absolute path, and exactly once."""
    remote = _remote_with_tree(tmp_path)
    (remote / "trees/taxonomy/config.yaml").write_text("extends: []\n")
    subprocess.run(["git", "-C", str(remote), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(remote), "commit", "-qm", "old config"], check=True)
    code = _repo(tmp_path / "code")
    init(["work"], code, "corelib")
    declaration = RepositoryDeclaration(url=str(remote), path="trees/taxonomy")
    set_component_key(code, "taxonomy", "repository",
                      {"url": declaration.url, "path": declaration.path})
    FsStoreProvisioner(code, "taxonomy", declaration).ensure_available()
    leftover = str(fs.provisioned_store_root(code, declaration).resolve() / "config.yaml")

    lines = [p for p in map(str, FsTaxonomyStore.open(code).check()) if "no longer read" in p]
    assert len(lines) == 1 and lines[0].startswith(f"error: {leftover}: "), lines
    lines = [p for p in map(str, validate(code)) if "no longer read" in p]
    assert len(lines) == 1 and lines[0].startswith(f"error: {leftover}: "), lines


def test_an_unprovisioned_declared_tree_now_fails_validate(tmp_path):
    """A taxonomy declared only through `taxonomy.repository`, not yet obtained
    on this machine, and no `docs/taxonomy`. `validate` never selected such a
    store for a check, so it used to say nothing; the work store has always
    been reported in this state. Now the tree is too — once, naming the
    command that fixes it."""
    code = _repo(tmp_path / "code")
    init(["work"], code, "corelib")
    set_component_key(code, "taxonomy", "repository",
                      {"url": "https://example.invalid/orchestrator.git",
                       "path": "trees/taxonomy"})

    problems = [p for p in map(str, validate(code))
                if p.startswith("error: .tcw/tcw-config.yaml: taxonomy: ")]
    assert len(problems) == 1, problems
    assert "tcw provision" in problems[0], problems


# ── A store that fails to open is not "no node here" ─────────────────────────
# spec: 2026-09-21-let-a-broken-extends-reach-the-user-instead-of-find-node-answering-no-node-here
# Since TCW 4.0 a project inherits from its parents, and the `extends` key is
# refused (TCW-112 Design 1); both failures below still reach the user.

def _node(tmp_path: Path, component: str, extra: str) -> Path:
    node = _repo(tmp_path / "node")
    init([component], node, "node")
    config = config_file(node)
    write_config_file(config, config.read_text() + extra)
    return node


def _assert_reports_not_no_node(err: str, component: str, *expected: str) -> None:
    assert f"no tcw {component} node here" not in err, err
    assert "tcw init" not in err, err
    for text in expected:
        assert text in err, err


@pytest.mark.parametrize("component", ["taxonomy", "capabilities"])
def test_a_parent_not_on_this_machine_reaches_the_user(tmp_path, monkeypatch, capsys,
                                                       component):
    node = _node(tmp_path, component, "parents:\n- ghost\n")
    monkeypatch.chdir(node)
    assert main([component, "list", "--scope", "up"]) == 7
    _assert_reports_not_no_node(capsys.readouterr().err, component, "ghost",
                                "not on this machine")


@pytest.mark.parametrize("component", ["taxonomy", "capabilities"])
def test_the_removed_extends_key_reaches_the_user(tmp_path, monkeypatch, capsys,
                                                  component):
    node = _node(tmp_path, component, f"{component}:\n  extends: [node]\n")
    monkeypatch.chdir(node)
    assert main([component, "list"]) == 1
    _assert_reports_not_no_node(capsys.readouterr().err, component,
                                f"'{component}.extends' was removed in TCW 4.0")


def test_a_node_without_a_work_store_still_says_so(tmp_path, monkeypatch, capsys):
    node = _repo(tmp_path / "node")
    init(["taxonomy"], node, "node")
    monkeypatch.chdir(node)
    assert main(["work", "list"]) == 1
    assert "no tcw work node here" in capsys.readouterr().err


def test_procedure_prompt_without_a_work_store_still_prints_the_builtin(tmp_path, monkeypatch, capsys):
    node = _repo(tmp_path / "node")
    init(["taxonomy"], node, "node")
    monkeypatch.chdir(node)
    assert main(["work", "procedure", "unattended-work"]) == 0
    assert "## The advisors" in capsys.readouterr().out


def test_procedure_prompt_reports_an_empty_work_path(tmp_path, monkeypatch, capsys):
    """The one exit code this changes: a broken `work.path` is an error, not a
    reason to fall back to the built-in text."""
    node = _repo(tmp_path / "node")
    init(["taxonomy"], node, "node")
    write_config(node, "id: node\nwork:\n  path: ''\n")
    monkeypatch.chdir(node)
    assert main(["work", "procedure", "unattended-work"]) == 1
    out = capsys.readouterr()
    assert "work.path" in out.err and "## The advisors" not in out.out


# ── provisioning never asks (pre-freeze clean-up, C4) ────────────────────────


def _git_envs(monkeypatch, ssh_command: str = "", scope: str = "global"):
    """Run `_run` with `_git` replaced, recording each call's argv and
    environment; the one `git config --show-scope --get-all core.sshCommand`
    read answers `ssh_command` as set in `scope` (`global`, `system`,
    `command`, or `local` and `worktree` for the repository the command runs
    in)."""
    calls = []

    def fake_git(argv, **kwargs):
        calls.append((list(argv), kwargs.get("env")))
        read = (argv[1] == "config" and "--show-scope" in argv
                and argv[-2:] == ["--get-all", "core.sshCommand"])
        out = f"{scope}\t{ssh_command}" if read and ssh_command else ""
        return subprocess.CompletedProcess(argv, 1 if read and not out else 0, out, "")
    monkeypatch.setattr(fs, "_git", fake_git)
    for name in ("GIT_SSH_COMMAND", "GIT_SSH"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("GIT_ASKPASS", "/usr/bin/some-askpass")
    monkeypatch.setenv("SSH_ASKPASS", "/usr/bin/ssh-askpass")
    monkeypatch.setenv("TCW_PROBE_KEPT", "yes")
    FsStoreProvisioner(Path("."), "work", None)._run(["git", "clone", "u", "d"])
    [(argv, env)] = [c for c in calls if c[0][1] == "clone"]
    return env


def test_git_is_told_never_to_prompt(monkeypatch):
    env = _git_envs(monkeypatch)
    assert env["GIT_TERMINAL_PROMPT"] == "0"
    assert env["GCM_INTERACTIVE"] == "never"
    assert env["GIT_ASKPASS"] == ""          # empty: git skips askpass, even `core.askPass`
    assert "SSH_ASKPASS" not in env
    assert env["TCW_PROBE_KEPT"] == "yes"              # the rest passes through
    assert env["GIT_SSH_COMMAND"] == "ssh -o BatchMode=yes"


def test_a_users_own_ssh_command_is_kept(monkeypatch):
    monkeypatch.setenv("GIT_SSH_COMMAND", "ssh -i ~/.ssh/mine")
    calls = []

    def fake_git(argv, **kwargs):
        calls.append((list(argv), kwargs.get("env")))
        return subprocess.CompletedProcess(argv, 0, "", "")
    monkeypatch.setattr(fs, "_git", fake_git)
    FsStoreProvisioner(Path("."), "work", None)._run(["git", "clone", "u", "d"])
    [(argv, env)] = calls                       # no `core.sshCommand` read either
    assert env["GIT_SSH_COMMAND"] == "ssh -i ~/.ssh/mine"


@pytest.mark.parametrize("scope", ["global", "system", "command"])
def test_a_configured_core_ssh_command_is_not_replaced(monkeypatch, scope):
    env = _git_envs(monkeypatch, ssh_command="ssh -i ~/.ssh/other\n", scope=scope)
    assert "GIT_SSH_COMMAND" not in env


@pytest.mark.parametrize("scope", ["local", "worktree"])
def test_the_current_repositorys_ssh_command_does_not_turn_batch_mode_off(monkeypatch, scope):
    """A clone into a new folder does not use the setting of the repository
    the command runs in, so that setting must not decide."""
    env = _git_envs(monkeypatch, ssh_command="ssh -i ~/.ssh/other\n", scope=scope)
    assert env["GIT_SSH_COMMAND"] == "ssh -o BatchMode=yes"


REPO = Path(__file__).resolve().parents[1]
#: Every document that says `tcw provision` does not ask (B2).
NOT_ASKING = [
    "docs/guide/multi-repo.md", "skills/setup/references/project.md",
    "docs/capabilities/cli/provision-declared-stores/description.md",
    "docs/release-notes/upcoming/2026-10-15-fix-what-tcw-71-to-tcw-75-s-reviews-"
    "left-in-the-3-0-code-before-the-freeze.md",
]


@pytest.mark.parametrize("name", NOT_ASKING)
def test_the_documents_name_the_ssh_command_exception(name):
    """A user's own ssh command is left alone, so ssh may still ask: no
    document may say provisioning never asks without saying so."""
    if "/upcoming/" in name and not (REPO / name).exists():
        pytest.skip("the entry files are combined into a version's file at a cut")
    text = " ".join((REPO / name).read_text(encoding="utf-8").lower().split())
    assert "never asks" not in text and "never prompts" not in text, name
    assert "ssh may still ask" in text, name
    # ...and which ssh command counts as the user's own: the one a clone into
    # a new folder uses, not the current repository's (`_no_prompt_env`).
    assert "global or system" in text, name
    assert "given on the git command line" in text \
        or "given on the command line" in text, name
    assert "not the current repository's own setting" in text, name


def test_with_real_git_a_local_ssh_command_is_not_read(monkeypatch, tmp_path):
    repo = tmp_path / "repo"
    subprocess.run(["git", "init", "-q", str(repo)], check=True, stdin=subprocess.DEVNULL)
    subprocess.run(["git", "-C", str(repo), "config", "core.sshCommand", "ssh -i mine"],
                   check=True, stdin=subprocess.DEVNULL)
    empty = tmp_path / "gitconfig"
    empty.write_text("")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(empty))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    for name in ("GIT_SSH_COMMAND", "GIT_SSH", "GIT_DIR"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.chdir(repo)
    assert fs._no_prompt_env()["GIT_SSH_COMMAND"] == "ssh -o BatchMode=yes"
    empty.write_text("[core]\n\tsshCommand = ssh -i global\n")
    assert "GIT_SSH_COMMAND" not in fs._no_prompt_env()


def test_with_real_git_a_command_line_ssh_command_is_kept(monkeypatch, tmp_path):
    """A `core.sshCommand` given on the command line, here through
    `GIT_CONFIG_COUNT`, is what the clone uses, so it is the user's own."""
    empty = tmp_path / "gitconfig"
    empty.write_text("")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(empty))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    for name in ("GIT_SSH_COMMAND", "GIT_SSH", "GIT_DIR", "GIT_CONFIG_PARAMETERS"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", "core.sshCommand")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", "ssh -i command-line")
    assert "GIT_SSH_COMMAND" not in fs._no_prompt_env()
