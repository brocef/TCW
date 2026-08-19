"""Resolving lifecycle bindings to text.

A library, not a command: C4's `tcw work stage` and C5's `tcw work scaffold` both
call it, and the existing transition-check path shares its condition filter. One
implementation so the three cannot disagree about when a binding applies.

**Nothing here writes.** It reads files, runs generators, and returns text.
Everything that writes belongs to C5.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from importlib.resources import files
from pathlib import Path
from typing import Mapping, Sequence

from tcw.store.base import (
    DEFAULT_OUTPUT_CAP, STAGE_IDS, Binding, DocEntry, LifecyclePolicy, WorkItem,
)
from tcw.work.generate import GenerateError, run_generate
from tcw.work.projection import work_item_json
from tcw.work.templates import ARTIFACT_TEMPLATES


class ResolveError(Exception):
    """A binding could not be resolved. The message names which and why."""


@dataclass(frozen=True)
class Builtins:
    """TCW's own shipped text, by role.

    **Two maps, not one.** Stage ids and artifact names overlap — `spec` and
    `plan` are both — so a single registry cannot hold `spec`'s prompt and
    `spec`'s template at the same time. C6 fills `stage_prompts`; C5 fills
    `artifact_templates`; C3 ships both empty, and an empty one resolving to
    nothing is a legal state rather than a failure.
    """
    stage_prompts: Mapping[str, str] = field(default_factory=dict)
    artifact_templates: Mapping[str, str] = field(default_factory=dict)


@lru_cache(maxsize=1)
def load_builtins() -> Builtins:
    """TCW's shipped text, loaded once per process.

    **One loader, both halves.** Two functions returning two different
    `Builtins` is how `spec`'s prompt and `spec`'s template end up resolved from
    different places, so every caller asks here and every new kind of built-in
    is added to this return value — C6 populates `stage_prompts` from
    `tcw/work/prompts/*.md` right here, beside the artifact templates.

    The stage set is the derivation `set(STAGE_IDS) - {"inbox"}`, never a
    literal list, so adding a stage without its prompt file fails here rather
    than shipping a stage that silently says nothing. `importlib.resources`
    rather than a path off `__file__`: the latter assumes an unpacked directory
    and breaks under a zipimport-style install.
    """
    root = files("tcw.work")
    prompts = {}
    for sid in sorted(set(STAGE_IDS) - {"inbox"}):
        rel = f"prompts/{sid}.md"
        try:
            text = (root / rel).read_text(encoding="utf-8")
        except (FileNotFoundError, OSError) as e:
            raise ResolveError(
                f"built-in prompt for stage '{sid}' is missing from the "
                f"installed package (tcw/work/{rel}): {e}")
        if not text.strip():
            raise ResolveError(
                f"built-in prompt for stage '{sid}' is empty "
                f"(tcw/work/{rel})")
        prompts[sid] = text
    return Builtins(stage_prompts=prompts, artifact_templates=ARTIFACT_TEMPLATES)


@dataclass(frozen=True)
class PlanEntry:
    """One binding as it was considered: what it is, whether it applied, and for
    a `generate`, the exact command line."""
    kind: str
    ref: str
    matched: bool
    executed: bool = False


@dataclass
class Resolution:
    text: str = ""
    plan: list[PlanEntry] = field(default_factory=list)


def select(bindings: Sequence[Binding], item: WorkItem | None) -> list[Binding]:
    """The bindings whose condition matches. Shared by all three roles.

    C4 needs this for stage checks and the existing transition path needs the
    same rule; one function is what stops "when does a `when:` apply" from having
    two answers.
    """
    return [b for b in bindings if b.when is None or b.when.matches(item)]


def _confined(node_root: Path, rel: str) -> Path:
    """Resolve a node-relative path and refuse one that leaves the node.

    Both sides are resolved with symlinks followed, because a symlink *inside*
    the node pointing out of it passes any lexical `..` check while reading
    exactly the file the check exists to prevent. This is a footgun guard, not a
    sandbox: the config is trusted, but a typo that quietly pulls an unrelated
    file into a prompt is worth refusing.
    """
    root = node_root.resolve()
    target = (root / rel).resolve()
    if target != root and root not in target.parents:
        raise ResolveError(
            f"file '{rel}' resolves outside the node root ({target})")
    return target


def _read_file(node_root: Path, rel: str) -> str:
    target = _confined(node_root, rel)
    try:
        return target.read_text(encoding="utf-8")
    except FileNotFoundError:
        # Validation catches a path that never existed; this is one that stopped
        # existing since, which is a runtime failure with a name rather than a
        # traceback.
        raise ResolveError(f"file '{rel}' no longer exists ({target})")
    except PermissionError:
        raise ResolveError(f"file '{rel}' cannot be read ({target})")
    except OSError as e:
        raise ResolveError(f"file '{rel}' could not be read: {e}")


# The bound on the item `body` a hook receives, in UTF-8 bytes. Deliberately
# **not** `work.lifecycle.output-cap`: that one bounds what a generator writes
# back, and a node tightening it to keep prompts short would silently start
# truncating the request its hooks read. Two limits, two reasons, one default.
BODY_CAP = DEFAULT_OUTPUT_CAP


def hook_payload(item: WorkItem | None, artifacts: Sequence, role: str, kind: str,
                 hook_id: str, phase: str, body_cap: int = BODY_CAP
                 ) -> tuple[str, bool]:
    """The JSON a `generate` hook receives on stdin, and whether the body was cut.

    `body_truncated` goes in the **hook** envelope, never beside `body` in the
    item: `WORK_ITEM_SCHEMA` is closed, so a sibling key there would make the
    document fail the schema TCW published for it. The item stays a valid DTO
    and only its `body` is shorter.

    The cap is **bytes of UTF-8, cut at a character boundary**. Slicing that many
    *characters* caps nothing on multi-byte text, and slicing bytes blindly
    yields invalid UTF-8 that breaks the JSON the hook is about to parse.
    """
    doc = work_item_json(item, artifacts) if item is not None else None
    truncated = False
    if doc is not None:
        raw = doc["body"].encode("utf-8")
        if len(raw) > body_cap:
            doc["body"] = raw[:body_cap].decode("utf-8", errors="ignore")
            truncated = True
    payload = {
        "item": doc,
        "hook": {"role": role, "kind": kind, "id": hook_id, "phase": phase,
                 "body_truncated": truncated},
    }
    return json.dumps(payload), truncated


def _hook_env(base_env: dict, role: str, kind: str, hook_id: str,
              phase: str) -> dict:
    """The four `TCW_*` variables a caller already set, plus the hook's own — so
    a one-line script needs no JSON parser."""
    return {**base_env, "TCW_HOOK_ROLE": role, "TCW_HOOK_KIND": kind,
            "TCW_HOOK_ID": hook_id, "TCW_HOOK_PHASE": phase}


def _resolve_one(b: Binding, *, role: str, hook_id: str, phase: str,
                 item: WorkItem | None, artifacts: Sequence, node_root: Path,
                 builtins: Mapping[str, str], policy: LifecyclePolicy,
                 env: dict, execute: bool) -> tuple[str, bool]:
    """One binding's text, and whether anything was executed."""
    if b.kind == "blob":
        return b.value, False
    if b.kind == "skill":
        return f"Invoke the {b.value} skill.", False
    if b.kind == "builtin":
        return builtins.get(hook_id, ""), False
    if b.kind == "file":
        if not execute:
            # Plan mode reads nothing either: "what would happen" must not make
            # any of it happen, and a file read is observable.
            return "", False
        return _read_file(node_root, b.value), False
    if b.kind == "generate":
        if not execute:
            return "", False
        stdin_text, _ = hook_payload(item, artifacts, role, b.kind, hook_id,
                                     phase)
        try:
            result = run_generate(b.value, node_root,
                                  _hook_env(env, role, b.kind, hook_id, phase),
                                  stdin_text, policy.timeout, policy.output_cap)
        except GenerateError as e:
            raise ResolveError(str(e))
        return result.text, True
    raise ResolveError(f"cannot resolve a '{b.kind}' binding in a {role} position")


DOC_OPEN = "{{tcw:documentation}}"
DOC_CLOSE = "{{/tcw:documentation}}"


def render_documentation(entries: Sequence[DocEntry]) -> str:
    """A project's documentation entries as a Markdown list.

    **A list, not a table.** A table row is delimited by `|`, and a description
    containing one would break it silently. A list has no load-bearing
    delimiter, so no escaping rule is needed. `path` and `trigger` are validated
    to hold no newline; a `description` written as a YAML block scalar has its
    internal newlines collapsed here, so it cannot break out of its bullet.
    """
    lines = ["The project's own documentation entries — evaluate every one "
             "whose trigger fires:", ""]
    for entry in entries:
        description = " ".join(entry.description.split())
        lines.append(f"- `{entry.path}` — **[{entry.trigger}]**")
        lines.append(f"  {description}")
    return "\n".join(lines)


def substitute_documentation(text: str, entries: Sequence[DocEntry]) -> str:
    """Replace each `{{tcw:documentation}}…{{/tcw:documentation}}` span.

    **The span carries its own fallback, and that is the design.** With entries
    configured the whole span becomes `render_documentation`; with none it
    becomes its own inner text, unchanged. So a project that configures nothing
    gets byte-identical bytes *by construction* rather than by a Python constant
    that has to be kept in agreement with the prompt.

    That matters because the two built-in prompts word the instruction
    differently — `plan` says "and name a task for each trigger that will fire",
    `implement` says "once, against the whole finished diff" — so a single
    hardcoded fallback could not reproduce both. Keeping prompt prose in the
    prompt file is also simply where it belongs.

    Continuation lines are indented to match whatever precedes the token on its
    line, so a span inside a numbered list item renders as part of that item.

    An unterminated open token is left **verbatim**: a malformed prompt should
    look wrong, not silently swallow the rest of the text.
    """
    out: list[str] = []
    rest = text
    while True:
        start = rest.find(DOC_OPEN)
        if start < 0:
            out.append(rest)
            break
        end = rest.find(DOC_CLOSE, start)
        if end < 0:
            out.append(rest)                      # unterminated: leave it alone
            break
        out.append(rest[:start])
        fallback = rest[start + len(DOC_OPEN):end]
        if entries:
            indent = " " * (start - (rest.rfind("\n", 0, start) + 1))
            rendered = render_documentation(entries).replace("\n", "\n" + indent)
            out.append(rendered + "\n" + indent)
        else:
            out.append(fallback)
        rest = rest[end + len(DOC_CLOSE):]
    return "".join(out)


def _join(parts: Sequence[str]) -> str:
    """Exactly how prompt text composes.

    "Concatenate" is not a byte-level contract and this slice has a byte-level
    criterion. Each part loses its trailing whitespace and the parts are joined
    by one blank line; empty parts drop out so an unfilled `builtin` does not
    leave a gap.
    """
    kept = [p.rstrip() for p in parts if p and p.strip()]
    return "\n\n".join(kept)


def resolve_prompts(policy: LifecyclePolicy, stage_id: str,
                    item: WorkItem | None, node_root: Path, builtins: Builtins,
                    artifacts: Sequence = (), env: dict | None = None, *,
                    execute: bool = True,
                    documentation: Sequence[DocEntry] = ()) -> Resolution:
    """A stage's prompt text: **every** matching binding, in declaration order.

    A stage with **no prompt bindings** resolves as if it bound
    `[{builtin: true}]` — the floor, so a node that configures nothing still
    gets TCW's own instructions. The condition is on the binding *list*, not on
    the resolved text: a stage whose only binding carries a `when:` that did not
    match resolves to nothing, because the node configured that stage and a
    stage the node configures wins outright.
    """
    res = Resolution()
    parts: list[str] = []
    bindings = policy.stage(stage_id) or [Binding(kind="builtin")]
    for b in bindings:
        matched = b.when is None or b.when.matches(item)
        if not matched:
            res.plan.append(PlanEntry(b.kind, b.ref, False))
            continue
        text, ran = _resolve_one(
            b, role="prompt", hook_id=stage_id, phase="prompt", item=item,
            artifacts=artifacts, node_root=node_root,
            builtins=builtins.stage_prompts, policy=policy, env=env or {},
            execute=execute)
        res.plan.append(PlanEntry(b.kind, b.ref, True, ran))
        parts.append(text)
    # Substituted here, over the joined text, and deliberately **not** in
    # `_resolve_one`: that is shared with `resolve_artifact`, so substituting
    # there would rewrite artifact templates too — and inconsistently, because
    # `tcw work scaffold`'s implicit built-in fallback bypasses `_resolve_one`
    # entirely. Doing it here also means a project's own `file:` or `blob:`
    # prompt can use the token, which is what makes this prompt generation
    # rather than a built-in-only special case.
    res.text = substitute_documentation(_join(parts), documentation)
    return res


def resolve_artifact(policy: LifecyclePolicy, artifact: str,
                     item: WorkItem | None, node_root: Path, builtins: Builtins,
                     artifacts: Sequence = (), env: dict | None = None, *,
                     execute: bool = True) -> Resolution:
    """An artifact's template: the **first** matching binding wins.

    Nothing after the winner is resolved — so a `generate` entry below a match
    does not run, which is the difference between "first match wins" and "first
    match is returned".
    """
    res = Resolution()
    won = False
    for b in policy.artifact(artifact):
        if won:
            res.plan.append(PlanEntry(b.kind, b.ref, False))
            continue
        if b.when is not None and not b.when.matches(item):
            res.plan.append(PlanEntry(b.kind, b.ref, False))
            continue
        text, ran = _resolve_one(
            b, role="artifact", hook_id=artifact, phase="artifact", item=item,
            artifacts=artifacts, node_root=node_root,
            builtins=builtins.artifact_templates, policy=policy, env=env or {},
            execute=execute)
        res.plan.append(PlanEntry(b.kind, b.ref, True, ran))
        res.text = text
        won = True
    return res
