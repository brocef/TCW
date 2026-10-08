"""Resolving prompt and procedure bindings to text (TCW-70 Design 7.2).

A library, not a command: `tcw work stage prompt` and `tcw work procedure
prompt` call it.

**Nothing here writes.** It reads files, runs generators, and returns text.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from functools import lru_cache
from importlib.resources import files
from pathlib import Path
from typing import Mapping, Sequence

from tcw.errors import BackendError
from tcw.store.base import DEFAULT_OUTPUT_CAP, PROCEDURE_IDS, DocEntry
from tcw.work.generate import GenerateError, run_generate


class ResolveError(Exception):
    """A binding could not be resolved. The message names which and why."""


@dataclass(frozen=True)
class Builtins:
    """TCW's own shipped text, by role: stage prompts and procedures. Two maps
    because a procedure id could one day equal a stage id."""
    stage_prompts: Mapping[str, str] = field(default_factory=dict)
    procedures: Mapping[str, str] = field(default_factory=dict)


@lru_cache(maxsize=1)
def load_builtins() -> Builtins:
    """TCW's shipped text, loaded once per process.

    The stages are those of TCW-69's table that ship a prompt file (`review`
    and `qa` arrive with TCW-74), never a literal list. `importlib.resources`
    rather than a path off `__file__`: the latter assumes an unpacked
    directory and breaks under a zipimport-style install.
    """
    from tcw.work.model import STAGES
    root = files("tcw.work")
    shipped = [s.name for s in STAGES
               if s.prompt and (root / "prompts" / f"{s.name}.md").is_file()]
    return Builtins(stage_prompts=_load_texts(root, "prompts", shipped,
                                              "prompt for stage"),
                    procedures=_load_texts(root, "procedures", PROCEDURE_IDS,
                                           "text for procedure"))


def _load_texts(root, folder: str, ids: Sequence[str], what: str) -> dict[str, str]:
    """`<folder>/<id>.md` for every id, refusing a missing or empty file by name.
    One loop for stage prompts and procedures, so the two refusals cannot drift."""
    texts = {}
    for sid in sorted(ids):
        rel = f"{folder}/{sid}.md"
        try:
            text = (root / rel).read_text(encoding="utf-8")
        except (FileNotFoundError, OSError) as e:
            raise ResolveError(
                f"built-in {what} '{sid}' is missing from the "
                f"installed package (tcw/work/{rel}): {e}")
        if not text.strip():
            raise ResolveError(
                f"built-in {what} '{sid}' is empty "
                f"(tcw/work/{rel})")
        texts[sid] = text
    return texts


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


def _hook_env(base_env: dict, role: str, kind: str, hook_id: str,
              phase: str) -> dict:
    """The four `TCW_*` variables a caller already set, plus the hook's own — so
    a one-line script needs no JSON parser."""
    return {**base_env, "TCW_HOOK_ROLE": role, "TCW_HOOK_KIND": kind,
            "TCW_HOOK_ID": hook_id, "TCW_HOOK_PHASE": phase}


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
        tail = rest[end + len(DOC_CLOSE):]
        if entries:
            indent = " " * (start - (rest.rfind("\n", 0, start) + 1))
            rendered = "\n".join(
                indent + line if line else ""      # never indent a blank line:
                for line in render_documentation(entries).splitlines())
            out.append(rendered.lstrip() + "\n" + indent)
            # The span ends mid-sentence, so whatever follows resumes on its own
            # line. Drop the single space that separated it from the close token,
            # or the continuation lands one column deeper than the list indent —
            # and at four spaces after a list, CommonMark reads it as a code
            # block rather than prose.
            if tail.startswith(" ") and not tail.startswith("  "):
                tail = tail[1:]
        else:
            out.append(fallback)
        rest = tail
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


# ---------------------------------------------------------------------------
# Composition on TCW-69's configuration and item model.

REQUEST_OPEN = "{{tcw:request}}"
REQUEST_CLOSE = "{{/tcw:request}}"
PACKAGED_KINDS = ("prompts", "procedures")


def packaged_text(kind: str, name: str) -> str:
    """TCW's own text for a stage (`prompts`) or a procedure (`procedures`),
    read from the installed package. A missing file is an error naming it."""
    if kind not in PACKAGED_KINDS:
        raise ValueError(f"unknown packaged text kind {kind!r}")
    rel = f"tcw/work/{kind}/{name}.md"
    try:
        return (files("tcw.work") / kind / f"{name}.md").read_text(encoding="utf-8")
    except (FileNotFoundError, OSError):
        raise BackendError(f"TCW's built-in text {rel} is missing from the "
                           f"installed package") from None


def substitute_request(text: str, request: str | None) -> str:
    """Replace each `{{tcw:request}}…{{/tcw:request}}` span with the item's
    request text, or with the span's own inner text when there is none.

    Inline, like the 2.x body span it replaces: no newline is added. An
    unterminated open token is left as written. `{{tcw:body}}` is not touched.
    """
    value = request.strip() if request and request.strip() else None
    out: list[str] = []
    rest = text
    while True:
        start = rest.find(REQUEST_OPEN)
        if start < 0:
            out.append(rest)
            break
        end = rest.find(REQUEST_CLOSE, start)
        if end < 0:
            out.append(rest)
            break
        out.append(rest[:start])
        fallback = rest[start + len(REQUEST_OPEN):end]
        out.append(value if value is not None else fallback)
        rest = rest[end + len(REQUEST_CLOSE):]
    return "".join(out)


def generate_payload(record: dict | None, request: str | None, role: str,
                     kind: str, hook_id: str, phase: str,
                     cap: int = BODY_CAP) -> tuple[str, bool]:
    """The one JSON object a `generate:` binding reads on stdin, and whether
    the request was cut. The cap is bytes of UTF-8, cut at a character
    boundary; the key `body_truncated` keeps its 2.x name."""
    truncated = False
    if request is not None:
        raw = request.encode("utf-8")
        if len(raw) > cap:
            request = raw[:cap].decode("utf-8", errors="ignore")
            truncated = True
    payload = {
        "schema": 1,
        "item": record,
        "request": request,
        "hook": {"role": role, "kind": kind, "id": hook_id, "phase": phase,
                 "body_truncated": truncated},
    }
    return json.dumps(payload), truncated


def _prompt_env(item, stage: str | None, layout, project_root: Path) -> dict:
    """TCW-69's hook variables for a composed prompt: `TCW_STAGE` is the stage
    being composed, and the move-only variables are absent."""
    from tcw.work.advance import hook_env
    if item is not None and stage is not None and layout is not None:
        env = hook_env(item, stage, layout, project_root)
        env.pop("TCW_FROM_STAGE", None)
        return env
    env = dict(os.environ)
    for name in ("TCW_SLUG", "TCW_STAGE", "TCW_FROM_STAGE", "TCW_ITEM_PATH",
                 "TCW_FORCED", "TCW_REASON"):
        env.pop(name, None)
    env["TCW_PROJECT_ROOT"] = str(project_root)
    if stage is not None:
        env["TCW_STAGE"] = stage
    if item is not None:
        env["TCW_SLUG"] = str(item.slug)
        if layout is not None:
            env["TCW_ITEM_PATH"] = str(layout.item_dir(item.slug))
    return env


def compose(bindings, *, role: str, hook_id: str, builtin_kind: str, item,
            record: dict | None, request: str | None, project_root: Path,
            config, documentation, env: dict, execute: bool = True) -> Resolution:
    """Every binding that applies to `item`, in order, joined, then the
    documentation and request spans substituted. With `execute` false, nothing
    is read or run: the plan says what would be."""
    from tcw.work.advance import binding_applies
    res = Resolution()
    parts: list[str] = []
    for b in bindings:
        if not binding_applies(b, item):
            res.plan.append(PlanEntry(b.kind, b.ref, False))
            continue
        ran = False
        if b.kind == "blob":
            text = b.value
        elif b.kind == "skill":
            text = f"Invoke the {b.value} skill."
        elif b.kind == "builtin":
            text = packaged_text(builtin_kind, hook_id)
        elif b.kind == "file":
            text = _read_file(project_root, b.value) if execute else ""
        elif b.kind == "generate":
            text = ""
            if execute:
                stdin_text, _ = generate_payload(record, request, role, b.kind,
                                                 hook_id, "prompt")
                try:
                    result = run_generate(
                        b.value, project_root,
                        _hook_env(env, role, b.kind, hook_id, "prompt"),
                        stdin_text, config.hooks.timeout, config.hooks.output_cap)
                except GenerateError as error:
                    raise ResolveError(str(error))
                text, ran = result.text, True
        else:
            raise ResolveError(f"cannot resolve a '{b.kind}' binding in a "
                               f"{role} position")
        res.plan.append(PlanEntry(b.kind, b.ref, True, ran))
        parts.append(text)
    res.text = substitute_request(
        substitute_documentation(_join(parts), documentation), request)
    return res


def stage_prompt(config, stage: str, *, item=None, record=None, request=None,
                 layout=None, project_root: Path, execute: bool = True
                 ) -> Resolution:
    """A stage's prompt: exactly `work.stages.<stage>.prompt`, which is TCW's
    own text when the key is not written, and nothing for an empty list."""
    bindings = config.stage(stage).prompt
    if bindings is None:
        from tcw.work.config import Binding as Binding3
        bindings = (Binding3("builtin", ""),)
    return compose(bindings, role="prompt", hook_id=stage, builtin_kind="prompts",
                   item=item, record=record, request=request,
                   project_root=project_root, config=config,
                   documentation=config.documentation,
                   env=_prompt_env(item, stage, layout, project_root),
                   execute=execute)


def procedure_prompt(config, procedure_id: str, *, item=None, record=None,
                     request=None, layout=None, project_root: Path,
                     execute: bool = True) -> Resolution:
    """A procedure's text, composed exactly as a stage's prompt is."""
    bindings = config.procedures.get(procedure_id)
    if bindings is None:
        from tcw.work.config import Binding as Binding3
        bindings = (Binding3("builtin", ""),)
    return compose(bindings, role="procedure", hook_id=procedure_id,
                   builtin_kind="procedures", item=item, record=record,
                   request=request, project_root=project_root, config=config,
                   documentation=config.documentation,
                   env=_prompt_env(item, None, layout, project_root),
                   execute=execute)


def stage_header(stage: str, target: str) -> str:
    """The line printed above a stage's prompt: reading instructions checks
    nothing, and `advance --dry-run` is what does."""
    return (f"> **This text ran no checks.** `tcw work stage prompt {stage}` "
            f"resolves instructions and gates nothing. Run "
            f"`tcw work advance {target} --dry-run` to see whether the item may "
            f"move on, and what would stop it.")
