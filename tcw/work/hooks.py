"""Execution of configured lifecycle bindings.

**Deliberately not in the store.** A `WorkStore` method that shells out is one no
remote adapter could honor, so running a command is a CLI concern. There is a
second, sharper reason: `complete()` writes the resolution *before* it moves the
item, so a `pre` hook evaluated inside the store would leave a resolution on an
unmoved item when it aborts — an item reading as closed while sitting in
`active`. Running hooks from the CLI, before the store is touched at all, is what
makes that impossible. No transaction concept and no interface change required.

**Trust model.** `tcw-config.yaml` lives in the user's own repository and is
trusted exactly as much as any other file there — a `Makefile`, a git hook, a
`conftest.py`. Commands run through the shell so pipelines and `&&` work. This is
stated plainly so nobody mistakes it for a sandbox.

`tcw serve` does not call any of this: running configured shell from an HTTP
handler on a button click is a meaningfully worse posture than a CLI the user
invoked deliberately.
"""
import os
import subprocess
import sys
from pathlib import Path

from tcw.store.base import Binding, LifecyclePolicy
from tcw.work.resolve import select


def hook_env(node_root: Path, slug: str, status: str, transition: str,
             item_path: "Path | str | None" = None,
             resolution: str = "") -> dict[str, str]:
    """The caller's environment plus the `TCW_*` variables, so a hook can act
    without re-deriving context it cannot see.

    `TCW_ITEM_PATH` and `TCW_RESOLUTION` are **omitted** rather than exported
    empty when the transition has no item folder or no resolution — `start` and
    `submit` have neither — so a script can test for presence instead of for
    emptiness.

    The path is passed in by the caller, always the store's own answer for the
    item, and is never composed here from `TCW_NODE_ROOT`: the work store may
    live in a different repository entirely, which is the standing rule for
    store paths everywhere in this codebase.
    """
    env = {
        **os.environ,
        "TCW_SLUG": slug,
        "TCW_STATUS": status,
        "TCW_TRANSITION": transition,
        "TCW_NODE_ROOT": str(node_root),
    }
    if item_path is not None:
        env["TCW_ITEM_PATH"] = str(item_path)
    if resolution:
        env["TCW_RESOLUTION"] = resolution
    return env


def run_bindings(bindings: list[Binding], node_root: Path, env: dict[str, str],
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
                binding.ref, shell=True, cwd=str(node_root), env=env,
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


def run_pre(policy: LifecyclePolicy, transition: str, node_root: Path, slug: str,
            status: str, item=None, item_path=None, resolution: str = "") -> str | None:
    """`pre` hooks for a transition. A failure means **do not touch the store**.

    Callers must invoke this before any `set_field`, not merely before the move:
    that is the whole reason execution lives outside the store.

    `item` is what a binding's `when:` is matched against. It is optional so the
    existing callers keep working, and a conditional binding without one simply
    does not match — a check that cannot be evaluated must not silently run.
    """
    return run_bindings(select(policy.transition(transition).pre, item), node_root,
                        hook_env(node_root, slug, status, transition, item_path,
                                 resolution),
                        policy.timeout, f"{transition} pre")


def run_post(policy: LifecyclePolicy, transition: str, node_root: Path, slug: str,
             status: str, item=None, item_path=None, resolution: str = "") -> str | None:
    """`post` hooks for a transition. A failure **never rolls back**.

    The move and its commit have already happened, and unwinding a committed
    transition is worse than the failure. The caller reports it and exits
    non-zero so nothing downstream mistakes it for success — but the item stays
    where it moved to.
    """
    return run_bindings(select(policy.transition(transition).post, item), node_root,
                        hook_env(node_root, slug, status, transition, item_path,
                                 resolution),
                        policy.timeout, f"{transition} post")
