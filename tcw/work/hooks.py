"""Running configured `pre` and `post` command bindings.

**Trust model.** `tcw-config.yaml` lives in the user's own repository and is
trusted exactly as much as any other file there — a `Makefile`, a git hook, a
`conftest.py`. Commands run through the shell so pipelines and `&&` work. This is
stated plainly so nobody mistakes it for a sandbox.

`tcw serve` runs no `pre` hooks and moves no item: running configured shell
from an HTTP handler on a button click is a meaningfully worse posture than a
CLI the user invoked deliberately. The one exception is adopting a Jira
ticket, which runs the request stage's `post` hooks, exactly as
`tcw work tickets adopt` does, because the item it makes would otherwise
differ from the one the CLI makes.
"""
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from tcw.output import shown
from tcw.work.config import Binding


@dataclass(frozen=True)
class HookFailure:
    """The binding that failed, and what to say about it. Its `str()` is the
    message, so a caller that only reports it reads it as text."""

    binding: Binding
    message: str

    def __str__(self) -> str:
        return self.message


def config_dir(binding: Binding, project_root: Path) -> Path:
    """The folder of the file that declared `binding` (TCW-72 Design 6): what
    its relative `file:` path is read from and what `TCW_CONFIG_DIR` names.
    The project root for a binding with no recorded file."""
    origin = binding.origin
    folder = getattr(origin, "folder", None)
    return folder if folder is not None else Path(project_root)


def run_bindings(bindings: list[Binding], project_root: Path, env: dict[str, str],
                 timeout: int, label: str, *,
                 name_origin: bool = False) -> HookFailure | None:
    """Run each command binding in declared order; return the first failure.

    Returns None when everything passed (or there was nothing to run). Stops at
    the first failure — a caller running `pre` hooks needs the remainder skipped,
    and a caller running `post` hooks gains nothing from continuing past one.

    Each command runs from the project root with `TCW_CONFIG_DIR` set to its
    declaring file's folder, so a personal hook can reach its own script.
    With `name_origin`, a failure names that file: a `post` hook may come from
    a personal file, and the person reading the failure needs to know which.

    **Skill bindings are reported, never executed.** The CLI cannot invoke a
    skill; only the agent can. They are surfaced so the agent knows to act, and
    that reporting is `[judgment]` — nothing here can make invocation certain,
    and on a harness that cannot enumerate skills nothing can even confirm the
    skill exists. Do not build anything that depends on such a check firing.
    """
    for binding in bindings:
        if binding.kind == "skill":
            print(f"{label} binding: invoke the {binding.ref} skill "
                  f"(TCW cannot run it for you)", file=sys.stderr)
            continue
        source = ""
        file = getattr(binding.origin, "file", None)
        variable = getattr(binding.origin, "variable", None)
        if name_origin and variable is not None:
            source = f" from {variable}"
        elif name_origin and file is not None:
            source = f" from {shown(file)}"
        try:
            r = subprocess.run(
                binding.ref, shell=True, cwd=str(project_root),
                env={**env, "TCW_CONFIG_DIR": str(config_dir(binding, project_root))},
                capture_output=True, text=True, timeout=timeout,
                # A hook reads only the stdin it was given, which is none: an
                # inherited descriptor would let it consume the caller's piped
                # intake, or stall to the full timeout and abort the transition.
                stdin=subprocess.DEVNULL)
        except subprocess.TimeoutExpired:
            return HookFailure(binding, f"{label} hook `{binding.ref}`{source} "
                                        f"exceeded the {timeout}s timeout")
        if r.stdout:
            sys.stderr.write(r.stdout)
        if r.stderr:
            sys.stderr.write(r.stderr)
        if r.returncode != 0:
            return HookFailure(binding, f"{label} hook `{binding.ref}`{source} "
                                        f"failed (exit {r.returncode})")
    return None


