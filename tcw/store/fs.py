"""Filesystem scaffolding for `tcw init`.

ponytail: this is the only store code Phase 1 needs. The abstract store
interface (`base.py`) and the per-component adapters land in Phase 2+, when a
real component operation exists to justify them — not before (see AGENTS.md:
don't pre-abstract).
"""
from __future__ import annotations

import subprocess
from pathlib import Path

# Component trees `tcw init` scaffolds. `work` gets a status-folder skeleton;
# `taxonomy` and `capabilities` are flat trees that fill in per their phases.
COMPONENTS = ("taxonomy", "capabilities", "work")
WORK_STATUSES = ("inbox", "backlog", "active", "blocked", "completed")


def git_root(start: Path | None = None) -> Path | None:
    """Top of the git work-tree containing `start` (cwd by default), or None.

    Shells out to git so worktrees/submodules resolve correctly — more correct
    on edge cases than walking up looking for a literal `.git` dir.
    """
    start = (start or Path.cwd()).resolve()
    try:
        out = subprocess.run(
            ["git", "-C", str(start), "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    return Path(out)


def init(components: list[str], root: Path) -> list[Path]:
    """Scaffold `docs/<component>/` skeletons under `root`. Returns leaf dirs made.

    A `.gitkeep` lands in each leaf so the empty skeleton survives a commit
    (git doesn't track empty directories).
    """
    created: list[Path] = []
    for c in components:
        base = root / "docs" / c
        leaves = [base / s for s in WORK_STATUSES] if c == "work" else [base]
        for leaf in leaves:
            leaf.mkdir(parents=True, exist_ok=True)
            (leaf / ".gitkeep").touch()
            created.append(leaf)
    return created
