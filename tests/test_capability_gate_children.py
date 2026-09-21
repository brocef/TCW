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
