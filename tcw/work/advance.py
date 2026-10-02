"""`advance`: the one operation that moves a work item between stages.

It decides the target, checks the rules about direction and reasons, runs the
target stage's gates, moves the item together with a note saying why, and runs
the target's `post` hooks. The steps below are numbered as in TCW-69's spec,
Design 6.1 to 6.9.

Usage errors and an unknown item are raised. Every other result, refusals
included, is returned as an `Outcome` whose `code` is the exit code.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from tcw import exit as codes
from tcw.errors import MovedWithoutNote, NotFound, Refused, UsageError
from tcw.work.backend import WorkBackend
from tcw.work.config import Binding, WorkConfig
from tcw.work.gates import RecordsReader, completion_gate, records_gate
from tcw.work.hooks import run_bindings
from tcw.work.layout import ACCEPTED, REJECTED, Layout
from tcw.work.model import (
    COMPLETION_GATE, FLOW, RECORDS_GATE, SIDE, TERMINAL, Item, Slug,
    discard_stage, gates_for, inbox_stage, is_skip, next_stage, position,
    stage as table_stage,
)

NO_STAGE = "no stage"


@dataclass(frozen=True)
class Outcome:
    code: int
    stage: str | None  # the stage the backend reports afterwards
    messages: tuple[str, ...] = ()
    overridden: tuple[str, ...] = ()  # gate failures a forced move went past


def _blank(text: str | None) -> bool:
    return text is None or not text.strip()


def _refuse(item: Item, *messages: str) -> Outcome:
    return Outcome(codes.REFUSED, item.stage, tuple(messages))


# -- 6.1 usage --------------------------------------------------------------

def _check_usage(config: WorkConfig, to: str | None, force: bool,
                 reason: str | None) -> None:
    if force and _blank(reason):
        raise UsageError("--force needs a --reason saying why")
    if to is None:
        return
    target = table_stage(to)
    if to not in config.enabled:
        raise UsageError(f"{to} is disabled in this project")
    if target.kind == SIDE:
        raise UsageError(f"{to} is worked on alongside the item, never moved "
                         f"into; write its document instead")
    if target.discard and _blank(reason):
        raise UsageError(f"moving to {to} needs a --reason saying why")


# -- 6.3 the target ------------------------------------------------------------

def _round_hint(layout: Layout, slug: Slug, name: str) -> str:
    return (f"write {layout.next_round(slug, name)} with a `verdict:` of "
            f"{ACCEPTED} or {REJECTED} and `judges:` set to the latest "
            f"implementation round")


def _choose_target(item: Item, to: str | None, backend: WorkBackend,
                   config: WorkConfig, layout: Layout) -> str | Outcome:
    current = item.stage
    if to is not None:
        target = to
    elif current is None:
        return _refuse(item, f"{item.slug} has no stage the model knows; name "
                             f"the target with --to (and --force, with a reason)")
    else:
        row = table_stage(current)
        if row.kind != FLOW:
            return _refuse(item, f"{item.slug} is at {current}, which has no next "
                                 f"stage; name the target with --to")
        if row.verdict and current in backend.external_stages:
            return _refuse(item, f"the verdict on {current} is kept in the backend, "
                                 f"which TCW cannot read; name the target with "
                                 f"--to and give a --reason")
        if row.verdict:
            state = layout.current_verdict(item.slug, current)
            if state == REJECTED:
                target = row.on_reject
            elif state == ACCEPTED:
                target = next_stage(current, config.enabled)
            else:
                return _refuse(item, f"{current} has no usable verdict (it is "
                                     f"{state}); {_round_hint(layout, item.slug, current)}")
        else:
            target = next_stage(current, config.enabled)

    if target == current:
        return _refuse(item, f"{item.slug} is already at {current}")
    if target == inbox_stage() and not backend.inbox_items:
        return _refuse(item, f"this backend keeps no items at {target}")
    return target


# -- 6.4 direction and reasons -----------------------------------------------------

def _check_direction(item: Item, target: str, force: bool, reason: str | None,
                     backend: WorkBackend, config: WorkConfig,
                     layout: Layout) -> Outcome | None:
    current = item.stage
    discarding = table_stage(target).discard
    if current is None:
        if not discarding and not force:
            return _refuse(item, f"{item.slug} has no stage to move from; moving "
                                 f"it needs --force and a --reason")
        return None
    row = table_stage(current)
    if row.kind == TERMINAL:
        if _blank(reason):
            return _refuse(item, f"{item.slug} is finished ({current}); reopening "
                                 f"it needs a --reason")
        return None
    if is_skip(current, target, config.enabled) and not force:
        return _refuse(item, f"moving from {current} to {target} skips a stage; "
                             f"that needs --force and a --reason")
    forward = position(target) > position(current) and not discarding
    external = current in backend.external_stages
    if row.verdict and forward and not force and not external:
        state = layout.current_verdict(item.slug, current)
        if state != ACCEPTED:
            return _refuse(item, f"{current} is {state}, not {ACCEPTED}; going "
                                 f"forward needs --force and a --reason, or "
                                 f"{_round_hint(layout, item.slug, current)}")
    if row.verdict and external and _blank(reason):
        return _refuse(item, f"leaving {current} records its verdict, which needs "
                             f"a --reason")
    return None


# -- 6.5 gates -------------------------------------------------------------------

def _applies(binding: Binding, item: Item) -> bool:
    """No `when`, or the item carries one of `when.tags` (any, when none are
    listed) and none of `when.not_tags`."""
    when = binding.when
    if when is None:
        return True
    tags = set(item.tags)
    if when.tags and not tags.intersection(when.tags):
        return False
    return not tags.intersection(when.not_tags)


def _hook_env(item: Item, target: str, layout: Layout, project_root: Path,
              force: bool, reason: str | None) -> dict[str, str]:
    env = dict(os.environ)
    env.update({
        "TCW_SLUG": str(item.slug),
        "TCW_STAGE": target,
        "TCW_FROM_STAGE": item.stage or "",
        "TCW_ITEM_PATH": str(layout.item_dir(item.slug)),
        "TCW_PROJECT_ROOT": str(project_root),
    })
    for name in ("TCW_FORCED", "TCW_REASON"):
        env.pop(name, None)
    if force:
        env["TCW_FORCED"] = "1"
        env["TCW_REASON"] = reason or ""
    return env


def _bindings(bindings: tuple[Binding, ...] | None, item: Item) -> list[Binding]:
    return [b for b in bindings or () if _applies(b, item)]


def _run_gates(item: Item, target: str, force: bool, config: WorkConfig,
               layout: Layout, reader: RecordsReader, project_root: Path,
               env: dict[str, str]) -> Outcome | list[str]:
    """Built-in gates first, then the target's matching `pre` hooks. Without
    `force` the first failure refuses the move; with it every gate runs and
    the failures are returned for the note."""
    failures: list[str] = []
    for gate in gates_for(target, config.enabled):
        if gate == RECORDS_GATE:
            problems = records_gate(layout, item.slug, reader)
        elif gate == COMPLETION_GATE:
            problems = completion_gate(layout, item.slug)
        else:  # pragma: no cover - the table names only these two
            raise ValueError(f"unknown built-in gate {gate!r}")
        if problems:
            failure = f"{gate} gate: " + "; ".join(problems)
            if not force:
                return _refuse(item, failure)
            failures.append(failure)
    for binding in _bindings(config.stage(target).pre, item):
        failure = run_bindings([binding], project_root, env,
                               config.hooks.timeout, f"{target} pre")
        if failure:
            if not force:
                return _refuse(item, failure)
            failures.append(failure)
    return failures


# -- 6.7 the trace -------------------------------------------------------------

def _note(item: Item, target: str, force: bool, reason: str,
          overridden: list[str]) -> str:
    lines = [f"Moved from {item.stage or NO_STAGE} to {target}"
             f"{' (forced)' if force else ''}.", f"Reason: {reason.strip()}"]
    if overridden:
        lines.append("Gate failures overridden:")
        lines += [f"- {failure}" for failure in overridden]
    return "\n".join(lines)


# -- the operation ---------------------------------------------------------------

def advance(backend: WorkBackend, config: WorkConfig, layout: Layout,
            reader: RecordsReader, project_root: Path, slug: Slug, *,
            to: str | None = None, force: bool = False, reason: str | None = None,
            dry_run: bool = False) -> Outcome:
    if layout.enabled != config.enabled \
            or layout.external != backend.external_stages:
        # The layout answers for verdicts and the completion gate, the config
        # and backend for everything else; built apart, they would disagree.
        raise ValueError("the layout must be built from config.enabled and "
                         "backend.external_stages")
    _check_usage(config, to, force, reason)                         # 6.1
    if slug.project != backend.project:                             # 6.2
        raise NotFound(f"{slug} is not an item of project {backend.project}")
    item = backend.read(slug.folder)

    target = _choose_target(item, to, backend, config, layout)      # 6.3
    if isinstance(target, Outcome):
        return target
    refusal = _check_direction(item, target, force, reason, backend,  # 6.4
                               config, layout)
    if refusal:
        return refusal

    env = _hook_env(item, target, layout, project_root, force, reason)
    gated = _run_gates(item, target, force, config, layout, reader,  # 6.5
                       project_root, env)
    if isinstance(gated, Outcome):
        return gated
    overridden = tuple(gated)

    if dry_run:                                                      # 6.6
        return Outcome(codes.OK, target, (f"would move {item.slug} from "
                                          f"{item.stage or NO_STAGE} to {target}",),
                       overridden)

    note = None if _blank(reason) else _note(item, target, force, reason,
                                             list(overridden))
    messages: list[str] = []
    code = codes.OK
    try:                                                             # 6.7
        reported = backend.set_stage(slug.folder, target, note)
    except Refused as error:
        return Outcome(codes.REFUSED, item.stage, (str(error),), overridden)
    except MovedWithoutNote as error:
        reported = target
        code = codes.MOVED_WITH_PROBLEM
        messages.append(f"moved to {target}, but the trace was not recorded "
                        f"({error}); add it with `tcw work comment`")
    if reported != target:
        return Outcome(codes.ERROR, reported,
                       (f"asked the backend to move {item.slug} to {target}, but "
                        f"it reports {reported}",), overridden)

    failure = run_bindings(_bindings(config.stage(target).post, item),  # 6.8
                           project_root, env, config.hooks.timeout,
                           f"{target} post")
    if failure:
        code = codes.MOVED_WITH_PROBLEM
        messages.append(f"moved to {target}, but {failure}")

    return Outcome(code, reported, tuple(messages), overridden)     # 6.9


def discard(backend: WorkBackend, config: WorkConfig, layout: Layout,
            reader: RecordsReader, project_root: Path, slug: Slug,
            reason: str) -> Outcome:
    return advance(backend, config, layout, reader, project_root, slug,
                   to=discard_stage(), reason=reason)
