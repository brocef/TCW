"""A project `demo` inheriting its taxonomy and capabilities from a project
`core`, for the TCW-110 tests of how inherited entries are named."""

from __future__ import annotations

import subprocess
from pathlib import Path

import yaml

from tcw.store.fs import FsCapabilitiesStore, FsTaxonomyStore, write_sentinel
from tests.projectfiles import write_config, write_manifest


def _repo(tmp_path: Path, name: str) -> Path:
    root = tmp_path / name
    (root / "docs" / "taxonomy").mkdir(parents=True)
    (root / "docs" / "capabilities").mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    write_sentinel(root, name)
    return root


def entry(root: Path, tree: str, path: str, **meta) -> None:
    """One taxonomy entry or capability, written as its files."""
    folder = root / "docs" / tree / path
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "meta.yaml").write_text(yaml.safe_dump(
        {"name": path.rsplit("/", 1)[-1].title(), **meta}))
    (folder / "description.md").write_text("")


def demo_inheriting_core(tmp_path: Path) -> Path:
    """`demo` holds the term `term` and the capability `cli/x`; `core` holds
    the term `shared` and the capability `cli/y`. Returns `demo`'s root."""
    core, demo = _repo(tmp_path, "core"), _repo(tmp_path, "demo")
    entry(core, "taxonomy", "shared")
    entry(core, "capabilities", "cli/y", id="cap-y", Status="Supported")
    entry(demo, "taxonomy", "term")
    entry(demo, "capabilities", "cli/x", id="cap-x", Status="Missing")
    write_config(core, "id: core\nchildren:\n- demo\n")
    write_manifest(core, {"demo": "../demo"})
    write_config(demo, "id: demo\nparents:\n- core\n")
    write_manifest(demo, {"core": "../core"})
    FsTaxonomyStore.open(demo).extends_add("core")
    FsCapabilitiesStore.open(demo).extends_add("core")
    return demo
