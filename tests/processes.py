"""The processes a command may start (TCW-114 Design 4.6, 5.7; plan choice 11).

A move, a rename and `tcw -C` start no process other than read-only
`git rev-parse`: building a project registry probes, once per folder per
process, whether the folder is a linked git worktree, and that probe is the
one process TCW runs for them. `allowed_read_only_git` is that rule;
`recorded_processes` records every `subprocess.run` and `subprocess.Popen`
call a test makes, so the rule can be checked against them.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest


def git_command(argv) -> tuple[str | None, set[str]]:
    """The git command `argv` runs and the options given before it, each
    `-C <folder>` taken with its folder; `(None, set())` when `argv` does
    not run git."""
    words = [str(w) for w in argv]
    if not words or Path(words[0]).name != "git":
        return None, set()
    rest, options = words[1:], set()
    while rest and rest[0].startswith("-"):
        options.add(rest[0])
        rest = rest[2:] if rest[0] == "-C" else rest[1:]
    return (rest[0] if rest else None), options


def allowed_read_only_git(argv) -> bool:
    """`git rev-parse`, allowed a `-C <folder>` and other options before the
    command. Anything else, `git status`, `git add` and `git commit`
    included, is not."""
    command, _ = git_command(argv)
    return command == "rev-parse"


@pytest.fixture
def recorded_processes(monkeypatch):
    """Every argument list given to `subprocess.run` or `subprocess.Popen`
    while the test runs, in order. `run` is recorded as well as `Popen`,
    which it calls, so each `run` appears twice; a rule checked over the
    list is unaffected."""
    started: list[list[str]] = []
    real_popen, real_run = subprocess.Popen, subprocess.run

    def _words(args) -> list[str]:
        return [args] if isinstance(args, str) else [str(a) for a in args]

    class Recording(real_popen):
        def __init__(self, args, *rest, **kwargs):
            started.append(_words(args))
            super().__init__(args, *rest, **kwargs)

    def run(args, *rest, **kwargs):
        started.append(_words(args))
        return real_run(args, *rest, **kwargs)

    monkeypatch.setattr(subprocess, "Popen", Recording)
    monkeypatch.setattr(subprocess, "run", run)
    return started
