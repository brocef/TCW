"""Which agent harness directly ran this process: Claude Code, or another one.

Only `tcw work stage validate` asks. Dynamic context injection (the
`` !`command` `` lines a skill runs as it loads) exists in Claude Code alone, so
under any other harness the command prepends a notice that those lines must be
run by hand. Nothing here gates anything: a wrong answer costs one misleading
paragraph.

**The process tree decides first**, because it is the only signal that survives
nesting. When Claude Code runs `codex exec`, every command Codex runs inherits
Claude's environment variables, yet the nearest harness ancestor is `codex`.

**Environment variables decide when the tree cannot** (no `ps`, a sandbox that
refuses it, Windows, or no ancestor with a known name). A Codex variable
outranks a Claude one for the same nesting reason, which is why the Claude
variables (`CLAUDECODE`, `CLAUDE_CODE_SESSION_ID`) need no check of their own:
their presence and "nothing detected" both answer Claude.

`CODEX_SESSION_ID` is checked though Codex 0.154.0 does not set it; it costs
nothing and was the variable first proposed. `CODEX_THREAD_ID` and
`CODEX_SANDBOX` are the ones found in that release.
"""
from __future__ import annotations

import os
import subprocess
from collections.abc import Mapping
from pathlib import Path

CLAUDE = "claude"
OTHER = "other"

_CODEX_VARIABLES = ("CODEX_THREAD_ID", "CODEX_SANDBOX", "CODEX_SESSION_ID")
_PROGRAMS = {"claude": CLAUDE, "codex": OTHER}
_PROC = Path("/proc")
_MAX_HOPS = 64


def _parent_via_ps(pid: int) -> tuple[int, str] | None:
    try:
        out = subprocess.run(["ps", "-o", "ppid=,comm=", "-p", str(pid)],
                             stdin=subprocess.DEVNULL, capture_output=True,
                             text=True, timeout=2).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    parts = out.strip().split(None, 1)
    if len(parts) != 2 or not parts[0].isdigit():
        return None
    return int(parts[0]), parts[1]


def _parent_via_proc(pid: int) -> tuple[int, str] | None:
    try:
        stat = (_PROC / str(pid) / "stat").read_text()
        comm = (_PROC / str(pid) / "comm").read_text().strip()
    except OSError:
        return None
    # The program name in `stat` is parenthesised and may itself contain spaces
    # or parentheses, so the fields after it are split from the *last* `)`.
    fields = stat[stat.rfind(")") + 1:].split()
    if len(fields) < 2 or not fields[1].isdigit() or not comm:
        return None
    return int(fields[1]), comm


def _lookup(pid: int) -> tuple[int, str] | None:
    """`(parent pid, program name)` of `pid`, or None when unreadable."""
    return _parent_via_ps(pid) or _parent_via_proc(pid)


def ancestor_programs(pid: int | None = None) -> list[str] | None:
    """Program names of `pid`'s ancestors, nearest first; None if unreadable.

    Starts at the parent of `pid` (this process by default). A failure after at
    least one name was read ends the walk with what it has. Never raises.
    """
    try:
        found = _lookup(os.getpid() if pid is None else pid)
        if found is None:
            return None
        names: list[str] = []
        seen: set[int] = set()
        current = found[0]
        while current > 1 and current not in seen and len(names) < _MAX_HOPS:
            seen.add(current)
            found = _lookup(current)
            if found is None:
                break
            names.append(found[1])
            current = found[0]
        return names
    except Exception:  # ponytail: advisory signal only; any surprise reads as "unreadable"
        return None


def detect(ancestors: list[str] | None, environ: Mapping[str, str]) -> str:
    """`CLAUDE` or `OTHER` for the harness that directly ran this process."""
    for name in ancestors or ():
        program = os.path.basename(name.strip()).lstrip("-").lower()
        if program in _PROGRAMS:
            return _PROGRAMS[program]
    if any(environ.get(v) for v in _CODEX_VARIABLES):
        return OTHER
    return CLAUDE
