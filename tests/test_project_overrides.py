"""`TCW_PROJECT_<ID>` — telling TCW where a connected project sits on this machine.

The registry-level behaviour is pinned in `test_project_registry.py`. What is
here is the half that only shows at the command boundary: whether an override is
*reported*, and whether the commands that resolve a graph all honour it.

Both matter more than they look. An override is invisible to every file the
checkout holds — set in an environment's configuration, it is in no config any
reader can grep — so a graph that resolves for a reason nobody can see is the
inverse of works-on-my-machine. Reporting is the whole mitigation.

**No test here reaches the network.** Where a remote is needed it is a real bare
repository in `tmp_path`; git does not care that the URL is a local path.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from tcw.cli import main


def _node(root: Path, body: str) -> Path:
    """A tcw node at `root` with `body` as its config, and nothing defaulted.

    Every key the resolution ladder branches on is written by the caller. A
    helper that supplied a locator or a repository of its own would fix an axis
    these tests exist to vary.
    """
    root.mkdir(parents=True, exist_ok=True)
    (root / "tcw-config.yaml").write_text(body, encoding="utf-8")
    return root


def _git_repo(root: Path) -> Path:
    subprocess.run(["git", "init", "-q", "-b", "main", str(root)], check=True)
    for key, value in (("user.email", "t@example.invalid"), ("user.name", "T"),
                       ("commit.gpgsign", "false")):
        subprocess.run(["git", "-C", str(root), "config", key, value], check=True)
    return root


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    """Three sibling nodes, laid out flat, with the configs written for a
    *nested* layout — the reproduction from the intake.

    `orchestrator` declares its child at `./core`, which is where it would sit
    on the machine whose author wrote the config. Here it is a sibling, so the
    declared locator names nothing and the graph is incomplete without help.
    """
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    orchestrator = _node(
        tmp_path / "orchestrator",
        "id: root-project\nconnected-projects:\n  children:\n"
        "    core-project: ./core\n",
    )
    core = _node(
        tmp_path / "core",
        "id: core-project\nconnected-projects:\n  parent:\n"
        "    root-project: ..\n",
    )
    monkeypatch.chdir(orchestrator)
    return tmp_path, orchestrator, core


def test_validate_says_which_overrides_are_in_effect(workspace, capsys, monkeypatch):
    """Criterion 9 — printed, exit 0, and not counted as a problem."""
    _tmp, _orchestrator, core = workspace
    monkeypatch.setenv("TCW_PROJECT_CORE_PROJECT", str(core))
    assert main(["validate"]) == 0
    err = capsys.readouterr().err
    assert err.count("TCW_PROJECT_CORE_PROJECT") == 1
    assert "'core-project' is overridden by TCW_PROJECT_CORE_PROJECT" in err
    assert str(core) in err
    # Never counted. The tally is what a reader scans for, and an override in
    # it would read as something to fix.
    assert "problem(s)" not in err


def test_validate_reports_the_override_beside_the_error_it_explains(
        workspace, capsys, monkeypatch):
    """An override that landed on the wrong node names a path in no config.

    `_cmd_validate` returns from inside its problem block, so an override line
    printed after it never appears on precisely the run where the reader most
    needs it. This asserts the ordering, not merely the presence.
    """
    tmp_path, _orchestrator, _core = workspace
    _node(tmp_path / "wrong", "id: other-project\n")
    monkeypatch.setenv("TCW_PROJECT_CORE_PROJECT", str(tmp_path / "wrong"))
    assert main(["validate"]) == 1
    err = capsys.readouterr().err
    assert "TCW_PROJECT_CORE_PROJECT" in err
    assert "other-project" in err
    assert err.index("TCW_PROJECT_CORE_PROJECT") < err.index("project graph problem")


def test_validate_with_no_override_says_nothing_about_one(workspace, capsys):
    """The rung is absent, not empty.

    Exit 0: the declared locator resolves nothing, which is a declaration this
    checkout cannot follow rather than a defect, and that was true before this
    feature existed. The assertion that matters is that no override vocabulary
    reaches a run that has none.
    """
    assert main(["validate"]) == 0
    err = capsys.readouterr().err
    assert "declared but not reachable" in err       # the pre-existing report
    assert "TCW_PROJECT" not in err
    assert "overridden" not in err


# --- provisioning, and the commands that resolve a graph ----------------------


def _node_remote(tmp_path: Path, name: str, body: str) -> Path:
    """A git repository whose working tree *is* a tcw node, used as a remote.

    Git does not care that the URL is a local path, which is how these stay
    inside the "no network, ever" rule while doing a real clone.
    """
    remote = _git_repo(tmp_path / name)
    (remote / "tcw-config.yaml").write_text(body, encoding="utf-8")
    subprocess.run(["git", "-C", str(remote), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(remote), "commit", "-qm", "seed node"], check=True)
    return remote


@pytest.fixture
def provisionable(tmp_path, monkeypatch):
    """An orchestrator whose child is declared at a path that is not here, with
    a repository saying where to get it — and a local sibling checkout of that
    same child that the declared locator does not name.

    The exact shape the intake reported: the configs describe a nested layout,
    the machine has a flat one, and without help TCW fetches a second copy of
    something already on disk.

    Returns `(orchestrator, local_core, cache_root)`.
    """
    cache = tmp_path / "cache"
    monkeypatch.setenv("XDG_CACHE_HOME", str(cache))
    remote = _node_remote(
        tmp_path, "remote-core",
        "id: core-project\nconnected-projects:\n  parent:\n    root-project: ..\n",
    )
    orchestrator = _node(
        tmp_path / "orchestrator",
        "id: root-project\nconnected-projects:\n  children:\n"
        "    core-project:\n      path: ./core\n      repository:\n"
        f"        url: {remote}\n        ref: main\n",
    )
    local_core = _node(
        tmp_path / "core",
        "id: core-project\nconnected-projects:\n  parent:\n"
        f"    root-project: {orchestrator}\n",
    )
    monkeypatch.chdir(orchestrator)
    return orchestrator, local_core, cache


def _cache_entries(cache: Path) -> list[str]:
    stores = cache / "tcw" / "stores"
    return sorted(p.name for p in stores.iterdir()) if stores.is_dir() else []


def test_without_an_override_the_declared_repository_is_fetched(
        provisionable, capsys):
    """The behaviour the override exists to prevent, asserted first.

    Without this, the next test cannot tell "the override stopped a fetch" from
    "nothing was ever going to fetch".
    """
    _orchestrator, _local_core, cache = provisionable
    assert main(["provision"]) == 0
    assert _cache_entries(cache), "expected a fetched copy with no override set"


def test_an_overridden_project_is_never_fetched(provisionable, capsys, monkeypatch):
    """Criterion 2 — resolved here, so nothing is obtained on its behalf.

    Provisioning is not told about overrides. It asks the registry where each
    project is, and the registry answers with the override, so this holds
    because rule 0 lives in graph loading rather than in one command.
    """
    _orchestrator, local_core, cache = provisionable
    monkeypatch.setenv("TCW_PROJECT_CORE_PROJECT", str(local_core))
    assert main(["provision"]) == 0
    out = capsys.readouterr().out
    assert "core-project: already available" in out
    assert _cache_entries(cache) == [], "an overridden project must not be fetched"


def test_one_variable_set_serves_both_session_shapes(tmp_path, monkeypatch, capsys):
    """Criterion 7 — the case that justifies absent-is-not-wrong.

    One set of variables is configured once for an environment. A session that
    attaches the repository resolves it locally and fetches nothing; a session
    that does not finds the same variable naming an absent path, falls through
    to the declaration, and provisions exactly as it would with no variable at
    all. Neither session is told which case it is in, and that is the point —
    if the absent path were an error, the second session would simply refuse.
    """
    remote = _node_remote(
        tmp_path, "remote-core",
        "id: core-project\nconnected-projects:\n  parent:\n    root-project: ..\n",
    )

    def session(name: str, *, attach_core: bool):
        base = tmp_path / name
        base.mkdir()
        cache = base / "cache"
        monkeypatch.setenv("XDG_CACHE_HOME", str(cache))
        orchestrator = _node(
            base / "orchestrator",
            "id: root-project\nconnected-projects:\n  children:\n"
            "    core-project:\n      path: ./core\n      repository:\n"
            f"        url: {remote}\n        ref: main\n",
        )
        if attach_core:
            _node(
                base / "core",
                "id: core-project\nconnected-projects:\n  parent:\n"
                f"    root-project: {orchestrator}\n",
            )
        # The same variable in both, naming the same place in the layout —
        # which exists in one session and not the other.
        monkeypatch.setenv("TCW_PROJECT_CORE_PROJECT", str(base / "core"))
        monkeypatch.chdir(orchestrator)
        return orchestrator, cache

    _orchestrator, cache = session("attached", attach_core=True)
    assert main(["provision"]) == 0
    assert _cache_entries(cache) == [], "an attached repository must not be fetched"

    _orchestrator, cache = session("detached", attach_core=False)
    assert main(["provision"]) == 0
    assert _cache_entries(cache), "an absent override must fall through and provision"
    assert main(["validate"]) == 0


def test_the_override_is_honoured_by_every_command(provisionable, monkeypatch, capsys):
    """Criterion 11 — applied in graph loading, not in one command.

    Each assertion is a separate command on purpose. A per-command
    implementation would satisfy any one of them and fail the others, and the
    claim being made is precisely that there is no per-command implementation.
    """
    from tcw.store.fs import init

    orchestrator, local_core, _cache = provisionable
    init(["work", "taxonomy", "capabilities"], orchestrator, "root-project")
    init(["work", "taxonomy", "capabilities"], local_core, "core-project")
    monkeypatch.setenv("TCW_PROJECT_CORE_PROJECT", str(local_core))

    assert main(["validate"]) == 0
    capsys.readouterr()

    assert main(["work", "list", "--include-descendants"]) == 0
    assert "core-project" in capsys.readouterr().out

    assert main(["work", "nodes"]) == 0
    assert "core-project" in capsys.readouterr().out

    assert main(["taxonomy", "list"]) == 0
    capsys.readouterr()


def test_with_no_variable_set_the_nested_layout_is_untouched(tmp_path, monkeypatch):
    """Criterion 8 — the rung is absent, not empty.

    Stated as a regression rather than a comparison against a released version,
    which the suite cannot run. The stronger evidence is the whole suite: the
    conftest fixture guarantees no `TCW_PROJECT_*` variable is set, so all 2379
    other tests exercise this path. This one names the criterion so a later
    change to `_target_path` that breaks the no-override case fails on a test
    that says what it broke.
    """
    cache = tmp_path / "cache"
    monkeypatch.setenv("XDG_CACHE_HOME", str(cache))
    orchestrator = _node(
        tmp_path / "orchestrator",
        "id: root-project\nconnected-projects:\n  children:\n"
        "    core-project: ./core\n",
    )
    _node(
        tmp_path / "orchestrator" / "core",
        "id: core-project\nconnected-projects:\n  parent:\n    root-project: ..\n",
    )
    from tcw.store.project import FsProjectRegistry

    registry = FsProjectRegistry.open(orchestrator)
    registry.require_valid()
    assert registry.check() == []
    assert registry.unreachable() == []
    assert registry.misdirected() == []
    assert registry.overrides() == []
    assert [c.id for c in registry.children()] == ["core-project"]
    assert not (cache / "tcw").exists(), "a resolved graph must fetch nothing"
