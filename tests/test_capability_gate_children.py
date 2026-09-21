"""The capability completion gate, for paths that name a child node's ledger.

A repository-root node can keep a work board but no capabilities ledger while
its child nodes each keep one. An item on that board declares the capabilities
it changes in a child's ledger by starting each `capabilities.yaml` path with the
child's project id (`kid/auth/login`), and `tcw work complete` checks the rest of
the path against that child's own ledger.

Every criterion test ends in `_refused` or `_passed`, so a test that skips the
full check is visible in the diff.
"""
import subprocess
from contextlib import chdir
from pathlib import Path

import yaml

from nodeconfig import set_component_key
from tcw.store.fs import FsCapabilitiesStore, FsWorkStore, init
from tcw.work.recursion import capability_gate


def _git(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", "--initial-branch=main", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "t"], check=True)
    return root


def _work_node(root: Path, project_id: str) -> Path:
    """A node with a work board and nothing else."""
    init(["work"], root, project_id)
    return root


def _register(parent: Path, child: Path) -> None:
    """Declare `child` under `parent`'s children, and the parent back."""
    parent_cfg = yaml.safe_load((parent / "tcw-config.yaml").read_text()) or {}
    child_cfg = yaml.safe_load((child / "tcw-config.yaml").read_text()) or {}
    parent_cfg.setdefault("connected-projects", {}).setdefault("children", {})[
        child_cfg["id"]] = str(child.resolve())
    child_cfg.setdefault("connected-projects", {})["parent"] = {
        parent_cfg["id"]: str(parent.resolve())}
    (parent / "tcw-config.yaml").write_text(yaml.safe_dump(parent_cfg, sort_keys=False))
    (child / "tcw-config.yaml").write_text(yaml.safe_dump(child_cfg, sort_keys=False))


def _give_ledger(node: Path, where: str) -> None:
    """`where` is "default" (docs/capabilities) or "path" (`capabilities.path:
    ledger`, so no docs/capabilities exists)."""
    if where == "default":
        init(["capabilities"], node)
    elif where == "path":
        (node / "ledger").mkdir()
        set_component_key(node, "capabilities", "path", "ledger")
    else:
        raise AssertionError(where)


def _graph(tmp_path: Path, *, parent_ledger: bool, kid_ledger: str | None,
           kid_repo: str) -> tuple[Path, Path]:
    """`root` (a work board, and a ledger only when `parent_ledger`) with one
    declared child `kid`. `kid_repo` is "same" (a folder inside root's
    repository) or "separate" (its own repository). No argument has a default:
    each is an axis the gate branches on."""
    root = _work_node(_git(tmp_path / "root"), "root")
    if kid_repo == "same":
        kid = root / "packages" / "kid"
        kid.mkdir(parents=True)
    elif kid_repo == "separate":
        kid = _git(tmp_path / "kid")
    else:
        raise AssertionError(kid_repo)
    _work_node(kid, "kid")
    _register(root, kid)
    if parent_ledger:
        _give_ledger(root, "default")
    if kid_ledger is not None:
        _give_ledger(kid, kid_ledger)
    return root, kid


def _item(root: Path, sidecar: str | None) -> str:
    """Create and start an item; `None` writes no capabilities.yaml, "" an
    empty one."""
    from tcw.cli import main
    ws = FsWorkStore.open(root)
    slug = ws.create("Task", created="2026-01-01").slug
    with chdir(root):
        assert main(["work", "start", slug]) == 0
    if sidecar is not None:
        (FsWorkStore.open(root).path(slug) / "capabilities.yaml").write_text(sidecar)
    return slug


def _complete(root: Path, slug: str, monkeypatch, resolution: str = "done") -> int:
    from tcw.cli import main
    monkeypatch.chdir(root)
    return main(["work", "complete", slug, "--resolution", resolution, "--confirm"])


def _refused(root, slug, monkeypatch, capsys, *needles, absent=()) -> str:
    """Completion as `done` exits 1, names every needle, names none of
    `absent`, and leaves the item where it was."""
    capsys.readouterr()
    assert _complete(root, slug, monkeypatch) == 1
    err = capsys.readouterr().err
    for n in needles:
        assert n in err, (n, err)
    for a in absent:
        assert a not in err, (a, err)
    assert FsWorkStore.open(root).get(slug).status == "active"
    return err


def _passed(root, slug, monkeypatch, capsys, resolution: str = "done") -> str:
    capsys.readouterr()
    rc = _complete(root, slug, monkeypatch, resolution)
    err = capsys.readouterr().err
    assert rc == 0, err
    expected = "completed" if resolution == "done" else "discarded"
    assert FsWorkStore.open(root).get(slug).status == expected
    return err


def _cap(node: Path, path: str, status: str) -> None:
    FsCapabilitiesStore.open(node).add(path, name=path.rsplit("/", 1)[-1], status=status)


# ── Task 1: the sidecar is read first, the ledger is found where it is ──────

def test_a_ledger_at_a_configured_path_is_gated(tmp_path, monkeypatch, capsys):
    """C13, second half; part 1 of the configured-ledger item. The gate used to
    look only for docs/capabilities and pass everything else."""
    root = _work_node(_git(tmp_path / "solo"), "solo")
    _give_ledger(root, "path")
    _cap(root, "auth/login", "Missing")
    slug = _item(root, "new:\n- auth/login\n")
    _refused(root, slug, monkeypatch, capsys, "auth/login: still Missing")


def test_a_work_only_node_passes_with_no_or_an_empty_sidecar(tmp_path, monkeypatch, capsys):
    """C11: a genuine work-only node, not `_wc_node`, which has a ledger."""
    root = _work_node(_git(tmp_path / "solo"), "solo")
    for sidecar in (None, ""):
        slug = _item(root, sidecar)
        _passed(root, slug, monkeypatch, capsys)


def test_a_broken_capabilities_declaration_passes_when_nothing_is_declared(
        tmp_path, monkeypatch, capsys):
    """C11: the sidecar is read before any store is opened."""
    root = _work_node(_git(tmp_path / "solo"), "solo")
    set_component_key(root, "capabilities", "path", "nowhere")
    for sidecar in (None, ""):
        slug = _item(root, sidecar)
        _passed(root, slug, monkeypatch, capsys)


def test_a_broken_capabilities_declaration_refuses_a_declared_path(
        tmp_path, monkeypatch, capsys):
    """The store's own complaint reaches the user as a problem line, where the
    old gate passed silently because docs/capabilities was absent."""
    root = _work_node(_git(tmp_path / "solo"), "solo")
    set_component_key(root, "capabilities", "path", "nowhere")
    slug = _item(root, "new:\n- auth/login\n")
    _refused(root, slug, monkeypatch, capsys,
             "auth/login: ", "capabilities.path is not a directory")


def test_a_discard_completes_when_the_store_cannot_be_opened(tmp_path, monkeypatch, capsys):
    """C12, store-failure half: a store failure is a problem, never an
    exception, so a discard still goes through with a warning."""
    root = _work_node(_git(tmp_path / "solo"), "solo")
    set_component_key(root, "capabilities", "path", "nowhere")
    slug = _item(root, "new:\n- auth/login\n")
    err = _passed(root, slug, monkeypatch, capsys, resolution="wontfix")
    assert "warning: unreconciled capability: auth/login: " in err


def test_invalid_connected_projects_is_not_read_when_nothing_is_declared(tmp_path):
    """C11: a node whose connected-projects fails validation. The CLI refuses
    to run at all on such a node, so the gate is called directly."""
    root, kid = _graph(tmp_path, parent_ledger=True, kid_ledger="default",
                       kid_repo="separate")
    ws = FsWorkStore.open(root)
    slug = ws.create("Task", created="2026-01-01").slug
    kid_cfg = yaml.safe_load((kid / "tcw-config.yaml").read_text())
    del kid_cfg["connected-projects"]                     # parent no longer declared back
    (kid / "tcw-config.yaml").write_text(yaml.safe_dump(kid_cfg))
    assert capability_gate(ws, ws.get(slug)) == []
    (ws.path(slug) / "capabilities.yaml").write_text("")
    assert capability_gate(ws, ws.get(slug)) == []
    (ws.path(slug) / "capabilities.yaml").write_text("new:\n- auth/login\n")
    problems = capability_gate(ws, ws.get(slug))
    assert problems and all("nonreciprocal connection" in p for p in problems), problems


# ── Task 2: child-qualified paths ───────────────────────────────────────────

def _sibling(tmp_path: Path, root: Path, name: str) -> Path:
    """A second child of `root`, in its own repository, with a ledger — the
    project `kid` (or `root`) extends in the inheritance cases."""
    lib = _work_node(_git(tmp_path / name), name)
    _register(root, lib)
    _give_ledger(lib, "default")
    return lib


def test_a_child_qualified_new_path_is_checked_in_the_childs_ledger(
        tmp_path, monkeypatch, capsys):
    """C1 (the remedy line is Task 5's)."""
    root, kid = _graph(tmp_path, parent_ledger=False, kid_ledger="default", kid_repo="same")
    _cap(kid, "auth/login", "Missing")
    slug = _item(root, "new:\n- kid/auth/login\n")
    _refused(root, slug, monkeypatch, capsys,
             "kid/auth/login: still Missing in project 'kid'",
             absent=["keeps no capabilities ledger"])
    FsCapabilitiesStore.open(kid).set("auth/login", {"Status": "Supported"})
    _passed(root, slug, monkeypatch, capsys)


def test_a_child_qualified_new_path_that_does_not_exist_is_refused(
        tmp_path, monkeypatch, capsys):
    """C3."""
    root, kid = _graph(tmp_path, parent_ledger=False, kid_ledger="default", kid_repo="same")
    slug = _item(root, "new:\n- kid/auth/ghost\n")
    _refused(root, slug, monkeypatch, capsys,
             "kid/auth/ghost: declared (new) but does not resolve in project 'kid'")


def test_a_child_qualified_changed_path_only_has_to_resolve(tmp_path, monkeypatch, capsys):
    """C4."""
    root, kid = _graph(tmp_path, parent_ledger=False, kid_ledger="default", kid_repo="same")
    _cap(kid, "auth/login", "Missing")
    slug = _item(root, "changed:\n- kid/auth/login\n")
    _passed(root, slug, monkeypatch, capsys)
    slug = _item(root, "changed:\n- kid/auth/ghost\n")
    _refused(root, slug, monkeypatch, capsys,
             "kid/auth/ghost: declared (changed) but does not resolve in project 'kid'")


def test_a_child_qualified_removed_path_must_be_gone(tmp_path, monkeypatch, capsys):
    """C5."""
    root, kid = _graph(tmp_path, parent_ledger=False, kid_ledger="default", kid_repo="same")
    _cap(kid, "auth/login", "Supported")
    slug = _item(root, "removed:\n- kid/auth/login\n")
    _refused(root, slug, monkeypatch, capsys,
             "kid/auth/login: declared (removed) but still resolves in project 'kid'")
    FsCapabilitiesStore.open(kid).remove("auth/login")
    _passed(root, slug, monkeypatch, capsys)


def test_the_rest_of_the_path_is_read_the_way_the_child_reads_it(
        tmp_path, monkeypatch, capsys):
    """C6: `kid` inherits `auth/login` from a sibling; its own override is
    what decides the status."""
    root, kid = _graph(tmp_path, parent_ledger=False, kid_ledger="default", kid_repo="same")
    lib = _sibling(tmp_path, root, "lib")
    _cap(lib, "auth/login", "Missing")
    FsCapabilitiesStore.open(kid).extends_add("lib")
    slug = _item(root, "new:\n- kid/auth/login\n")
    _refused(root, slug, monkeypatch, capsys, "kid/auth/login: still Missing in project 'kid'")
    FsCapabilitiesStore.open(kid).set("auth/login", {"Status": "Supported"})
    _passed(root, slug, monkeypatch, capsys)


def test_a_child_that_is_not_here_is_refused(tmp_path, monkeypatch, capsys):
    """C9, first half."""
    import shutil
    root, kid = _graph(tmp_path, parent_ledger=False, kid_ledger="default",
                       kid_repo="separate")
    slug = _item(root, "new:\n- kid/auth/login\n")
    shutil.rmtree(kid)
    _refused(root, slug, monkeypatch, capsys,
             "kid/auth/login: project 'kid' is declared in",
             "not reachable in this checkout")


def test_a_child_with_no_ledger_is_refused(tmp_path, monkeypatch, capsys):
    """C9, second half."""
    root, kid = _graph(tmp_path, parent_ledger=False, kid_ledger=None, kid_repo="same")
    slug = _item(root, "new:\n- kid/auth/login\n")
    _refused(root, slug, monkeypatch, capsys,
             "kid/auth/login: project 'kid' keeps no capabilities ledger")


def test_an_unqualified_path_on_a_node_with_no_ledger_is_refused(
        tmp_path, monkeypatch, capsys):
    """C10: nothing can check it, so it is refused, naming the qualifiers."""
    root, kid = _graph(tmp_path, parent_ledger=False, kid_ledger="default", kid_repo="same")
    _cap(kid, "auth/login", "Supported")
    slug = _item(root, "new:\n- auth/login\n")
    _refused(root, slug, monkeypatch, capsys,
             "auth/login: this node ('root') keeps no capabilities ledger; "
             "qualify the path with a child project id (kid)")


def test_a_childs_ledger_at_a_configured_path_is_found(tmp_path, monkeypatch, capsys):
    """C13, first half: C1 and C3 with the child's ledger at capabilities.path."""
    root, kid = _graph(tmp_path, parent_ledger=False, kid_ledger="path", kid_repo="same")
    assert not (kid / "docs" / "capabilities").exists()
    _cap(kid, "auth/login", "Missing")
    slug = _item(root, "new:\n- kid/auth/login\n- kid/auth/ghost\n")
    _refused(root, slug, monkeypatch, capsys,
             "kid/auth/login: still Missing in project 'kid'",
             "kid/auth/ghost: declared (new) but does not resolve in project 'kid'",
             absent=["keeps no capabilities ledger"])


def test_local_inherited_and_child_paths_mix_on_a_node_with_a_ledger(
        tmp_path, monkeypatch, capsys):
    """C15."""
    root, kid = _graph(tmp_path, parent_ledger=True, kid_ledger="default", kid_repo="same")
    lib = _sibling(tmp_path, root, "lib")
    FsCapabilitiesStore.open(root).extends_add("lib")
    _cap(root, "auth/local", "Missing")
    _cap(kid, "auth/login", "Supported")
    _cap(lib, "auth/x", "Missing")
    slug = _item(root, "new:\n- auth/local\n- kid/auth/login\n- lib/auth/x\n")
    err = _refused(root, slug, monkeypatch, capsys,
                   "auth/local: still Missing (declared new",
                   "lib/auth/x: still Missing (declared new")
    assert "kid/auth/login" not in err
    FsCapabilitiesStore.open(root).set("auth/local", {"Status": "Supported"})
    FsCapabilitiesStore.open(root).set("lib/auth/x", {"Status": "Supported"})
    _passed(root, slug, monkeypatch, capsys)


def test_an_extended_project_wins_over_a_child_of_the_same_id(tmp_path, monkeypatch, capsys):
    """C16: `kid` is both a child and a project root's ledger extends; the
    inheritance reading — root's own override — decides."""
    root, kid = _graph(tmp_path, parent_ledger=True, kid_ledger="default", kid_repo="same")
    _cap(kid, "auth/login", "Missing")
    FsCapabilitiesStore.open(root).extends_add("kid")
    FsCapabilitiesStore.open(root).set("kid/auth/login", {"Status": "Supported"})
    slug = _item(root, "new:\n- kid/auth/login\n")
    _passed(root, slug, monkeypatch, capsys)


def test_an_unprovisioned_own_ledger_refuses_even_child_paths(tmp_path, monkeypatch, capsys):
    """C18: without root's own ledger the gate cannot tell which reading a
    path has."""
    root, kid = _graph(tmp_path, parent_ledger=False, kid_ledger="default", kid_repo="same")
    set_component_key(root, "capabilities", "path", "../nowhere/capabilities")
    set_component_key(root, "capabilities", "repository",
                      {"url": "https://example.invalid/orchestrator.git",
                       "path": "trees/capabilities"})
    _cap(kid, "auth/login", "Supported")
    slug = _item(root, "new:\n- kid/auth/login\n")
    _refused(root, slug, monkeypatch, capsys, "kid/auth/login: ", "tcw provision")


def test_a_discard_only_warns_about_child_paths(tmp_path, monkeypatch, capsys):
    """C12, child half: C1's unreconciled state, C9's absent child and C10's
    unqualified path each warn on a discard instead of refusing it."""
    root, kid = _graph(tmp_path, parent_ledger=False, kid_ledger="default", kid_repo="same")
    _cap(kid, "auth/login", "Missing")
    slug = _item(root, "new:\n- kid/auth/login\n- auth/login\n- ghost/auth/login\n")
    err = _passed(root, slug, monkeypatch, capsys, resolution="wontfix")
    assert "warning: unreconciled capability: kid/auth/login: still Missing" in err
    assert "warning: unreconciled capability: auth/login: this node ('root')" in err


# ── Task 3: a child id that is also a namespace the parent already shows ────

def test_a_child_id_that_is_a_local_namespace_is_ambiguous(tmp_path, monkeypatch, capsys):
    """C17 (a): root has its own `kid/x`."""
    root, kid = _graph(tmp_path, parent_ledger=True, kid_ledger="default", kid_repo="same")
    _cap(root, "kid/x", "Supported")
    _cap(kid, "auth/login", "Supported")
    slug = _item(root, "new:\n- kid/auth/login\n")
    _refused(root, slug, monkeypatch, capsys,
             "kid/auth/login: ambiguous", "kid/x",
             absent=["in project 'kid'"])


def test_declaring_a_child_does_not_silently_redirect_an_inherited_path(
        tmp_path, monkeypatch, capsys):
    """C17 (b), the redirection case: `kid/x` reaches root through inheritance
    from `lib` (bare fall-through), and passes. Declaring a child `kid` must
    refuse it as ambiguous, not quietly send it to the child's ledger."""
    root = _work_node(_git(tmp_path / "root"), "root")
    _give_ledger(root, "default")
    lib = _sibling(tmp_path, root, "lib")
    FsCapabilitiesStore.open(root).extends_add("lib")
    _cap(lib, "kid/x", "Supported")
    slug = _item(root, "new:\n- kid/x\n")
    assert capability_gate(FsWorkStore.open(root), FsWorkStore.open(root).get(slug)) == []
    kid = root / "packages" / "kid"
    kid.mkdir(parents=True)
    _work_node(kid, "kid")
    _register(root, kid)
    _give_ledger(kid, "default")
    _refused(root, slug, monkeypatch, capsys, "kid/x: ambiguous", "kid/x",
             absent=["in project 'kid'"])


# ── Task 4: removed: stays local-only ───────────────────────────────────────

def test_removing_a_capability_the_child_inherits_is_refused(tmp_path, monkeypatch, capsys):
    """C8, child half: `rm` deletes only local capabilities, so a `removed:`
    path naming one `kid` inherits can never be satisfied honestly."""
    root, kid = _graph(tmp_path, parent_ledger=False, kid_ledger="default", kid_repo="same")
    lib = _sibling(tmp_path, root, "lib")
    _cap(lib, "auth/login", "Supported")
    FsCapabilitiesStore.open(kid).extends_add("lib")
    slug = _item(root, "removed:\n- kid/lib/auth/login\n")
    _refused(root, slug, monkeypatch, capsys,
             "kid/lib/auth/login: `tcw capabilities rm` deletes only local capabilities; "
             "project 'kid' cannot remove a capability it inherits from 'lib'")


def test_removing_a_capability_the_node_inherits_is_refused(tmp_path, monkeypatch, capsys):
    """C8, own-ledger half: the same defect in the gate before this change,
    where the path passed because nothing local sat at that literal path."""
    root = _work_node(_git(tmp_path / "root"), "root")
    _give_ledger(root, "default")
    lib = _sibling(tmp_path, root, "lib")
    _cap(lib, "auth/login", "Supported")
    FsCapabilitiesStore.open(root).extends_add("lib")
    slug = _item(root, "removed:\n- lib/auth/login\n")
    _refused(root, slug, monkeypatch, capsys,
             "lib/auth/login: `tcw capabilities rm` deletes only local capabilities; "
             "this node cannot remove a capability it inherits from 'lib'")


def test_removing_a_local_capability_that_shadowed_an_inherited_one_passes(
        tmp_path, monkeypatch, capsys):
    """C7: after `rm`, the bare path falls through to `lib`'s capability,
    which `rm` would refuse — so only a local hit counts."""
    root, kid = _graph(tmp_path, parent_ledger=False, kid_ledger="default", kid_repo="same")
    lib = _sibling(tmp_path, root, "lib")
    _cap(lib, "auth/login", "Supported")
    FsCapabilitiesStore.open(kid).extends_add("lib")
    _cap(kid, "auth/login", "Supported")
    slug = _item(root, "removed:\n- kid/auth/login\n")
    _refused(root, slug, monkeypatch, capsys, "still resolves in project 'kid'")
    FsCapabilitiesStore.open(kid).remove("auth/login")
    assert FsCapabilitiesStore.open(kid).get("auth/login") is not None     # lib's
    _passed(root, slug, monkeypatch, capsys)
