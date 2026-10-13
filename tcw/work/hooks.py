"""Running configured `pre` and `post` command bindings.

**Trust model.** `tcw-config.yaml` lives in the user's own repository and is
trusted exactly as much as any other file there — a `Makefile`, a git hook, a
`conftest.py`. Commands run through the shell so pipelines and `&&` work. This is
stated plainly so nobody mistakes it for a sandbox.

`tcw serve` does not call any of this: running configured shell from an HTTP
handler on a button click is a meaningfully worse posture than a CLI the user
invoked deliberately.
"""
import subprocess
import sys
from pathlib import Path

from tcw.work.config import Binding


def run_bindings(bindings: list[Binding], project_root: Path, env: dict[str, str],
                 timeout: int, label: str) -> str | None:
    """Run each command binding in declared order; return the first failure.

    Returns None when everything passed (or there was nothing to run). Stops at
    the first failure — a caller running `pre` hooks needs the remainder skipped,
    and a caller running `post` hooks gains nothing from continuing past one.

    **Skill bindings are reported, never executed.** The CLI cannot invoke a
    skill; only the agent can. They are surfaced so the agent knows to act, and
    that reporting is `[judgment]` — nothing here can make invocation certain,
    and on a harness that cannot enumerate skills nothing can even confirm the
    skill exists. Do not build anything that depends on such a check firing.
    """
    for binding in bindings:
        if binding.kind == "skill":
            print(f"tcw work: {label} binding — invoke the {binding.ref} skill "
                  f"(TCW cannot run it for you)", file=sys.stderr)
            continue
        try:
            r = subprocess.run(
                binding.ref, shell=True, cwd=str(project_root), env=env,
                capture_output=True, text=True, timeout=timeout,
                # A hook reads only the stdin it was given, which is none: an
                # inherited descriptor would let it consume the caller's piped
                # intake, or stall to the full timeout and abort the transition.
                stdin=subprocess.DEVNULL)
        except subprocess.TimeoutExpired:
            return (f"{label} hook `{binding.ref}` exceeded the {timeout}s "
                    f"timeout")
        if r.stdout:
            sys.stderr.write(r.stdout)
        if r.stderr:
            sys.stderr.write(r.stderr)
        if r.returncode != 0:
            return (f"{label} hook `{binding.ref}` failed "
                    f"(exit {r.returncode})")
    return None


