"""The work item JSON projection.

One document, consumed by `tcw work show --json`, by `serve`, and by `generate`
hooks. Pure: it takes a `WorkItem` and the artifact list a caller already
resolved through abstract store methods, and returns a dict. No store, no path,
no I/O — every field is a `WorkItem` field and `artifacts()` is an existing
abstract primitive, so nothing here presumes a filesystem.

The projection this replaces was `asdict()` finished with
`json.dumps(..., default=str)`. `default=` is not a decision: it fires silently,
anywhere in the tree, and the caller never learns it happened. It also does not
work for floats — `json.dumps(float("nan"))` emits bare `NaN`, which is not valid
JSON — so the old path could ship an unparseable document. Everything here is
made JSON-native before an encoder sees it.
"""

from __future__ import annotations

import base64
import math
from collections.abc import Mapping, Sequence
from dataclasses import fields
from typing import Any

from tcw.store.base import WORK_ARTIFACTS, Artifact, WorkItem

SCHEMA_VERSION = 1

CIRCULAR = "<circular reference>"


def _json_safe(value: Any, _seen: frozenset[int] = frozenset()) -> Any:
    """Coerce an arbitrary YAML-loaded value into JSON-native data.

    Every branch below exists for a shape `yaml.safe_load` actually produces;
    they were reproduced against the loader rather than imagined.
    """
    if value is None or isinstance(value, (bool, int, str)):
        # bool before int is not needed — bool *is* an int and both pass through
        # unchanged — but int must come before the float branch, since a bool is
        # not a float and an int is not one either.
        return value
    if isinstance(value, float):
        # `default=` is never consulted for floats, so this is the only place a
        # non-finite value can be caught before it becomes bare `NaN`/`Infinity`.
        return value if math.isfinite(value) else str(value)
    if isinstance(value, bytes):
        # `!!binary`. `str(b"hi")` is `"b'hi'"` — a Python repr posing as data.
        return base64.b64encode(value).decode("ascii")

    marker = id(value)
    if marker in _seen:
        # A YAML anchor can make a container hold itself: `a: &x\n  b: *x`. A
        # naive walk raises RecursionError and json.dumps raises "Circular
        # reference detected". Rendering a marker is visible in the output and
        # cannot hang.
        return CIRCULAR

    if isinstance(value, Mapping):
        nested = _seen | {marker}
        out: dict[str, Any] = {}
        origin: dict[str, Any] = {}
        for key, sub in value.items():
            k = str(key)
            if k in out:
                # YAML produces `{1: "a", "1": "b"}`; both keys stringify to
                # "1". Keeping one and dropping the other loses data silently,
                # which is the failure mode this whole module exists to remove.
                raise ValueError(
                    f"cannot project to JSON: mapping keys {origin[k]!r} and "
                    f"{key!r} both render as {k!r}, so one value would be lost")
            out[k] = _json_safe(sub, nested)
            origin[k] = key
        return out
    if isinstance(value, (set, frozenset)):
        # `!!set`. JSON has no set; an unordered dump would make the projection
        # non-deterministic for identical input. `key=str` never compares the
        # elements to each other, so a mixed-type set sorts fine.
        nested = _seen | {marker}
        return [_json_safe(v, nested) for v in sorted(value, key=str)]
    if isinstance(value, (list, tuple)):
        nested = _seen | {marker}
        return [_json_safe(v, nested) for v in value]

    # datetime.date and datetime.datetime land here (a bare `2026-01-01` in YAML
    # is a date, not a string) and render ISO-8601.
    return str(value)


_BLOCKER = {
    "type": "object",
    "properties": {"slug": {"type": "string"},
                   "external": {"type": "string"}},
    "additionalProperties": False,
    "minProperties": 1,
}

_STR = {"type": "string"}

# `WorkItem.tracker`: exactly the four shapes `binding_value` produces, each
# closed, so a script can rely on `.tracker.ticket.key` meaning what it says.
_TRACKER = {"oneOf": [
    {"type": "null"},
    # A ticket that filing was configured to create and could not. There is no
    # binding here and no `ticket` key to read — the item is unbound, and this
    # says only that somebody expected it not to be.
    {"type": "object",
     "additionalProperties": False,
     "properties": {"owed": {"type": "object",
                             "additionalProperties": False,
                             "properties": {"since": _STR, "reason": _STR},
                             "required": ["since", "reason"]}},
     "required": ["owed"]},
    {"type": "object",
     "additionalProperties": False,
     "properties": {
         "provider": {"type": "string"},
         "project": {"type": "string"},
         "part": {"type": "string"},
         "ticket": {"type": "object",
                    "additionalProperties": False,
                    "properties": {name: {"type": "string"}
                                   for name in ("id", "key", "url")},
                    "required": ["id", "key", "url"]},
         "bound": {"type": "string"},
         # What did not reach the tracker, while it has not.
         "sync": {"oneOf": [
             {"type": "null"},
             {"type": "object",
              "additionalProperties": False,
              "properties": {
                  "state": {"enum": ["pending", "conflicting"]},
                  "move": {"type": "string"},
                  "since": {"type": "string"},
                  "reason": {"type": "string"},
                  "at": {"type": "string"},
              },
              "required": ["state", "move", "since", "reason", "at"]},
             {"type": "object",
              "additionalProperties": False,
              "properties": {"problem": {"type": "string"}},
              "required": ["problem"]},
         ]},
         # A progress comment that did not post, while it has not.
         "comment": {"oneOf": [
             {"type": "null"},
             {"type": "object",
              "additionalProperties": False,
              "properties": {
                  "move": {"type": "string"},
                  "event": {"type": "string"},
                  "state": {"enum": ["pending", "conflicting"]},
                  "reason": {"type": "string"},
                  "at": {"type": "string"},
              },
              "required": ["move", "event", "state", "reason", "at"]},
             {"type": "object",
              "additionalProperties": False,
              "properties": {"problem": {"type": "string"}},
              "required": ["problem"]},
         ]},
     },
     "required": ["provider", "project", "part", "ticket", "bound", "sync",
                  "comment"]},
    {"type": "object",
     "additionalProperties": False,
     "properties": {"problem": {"type": "string"}},
     "required": ["problem"]},
]}
_STR_OR_NULL = {"type": ["string", "null"]}
_INT_OR_NULL = {"type": ["integer", "null"]}

WORK_ITEM_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "tcw work item",
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "schema": {"const": SCHEMA_VERSION},
        "slug": _STR,
        "title": _STR,
        "status": _STR,
        "created": _STR,
        "modified": _STR,
        "resolution": _STR_OR_NULL,
        "priority": _INT_OR_NULL,
        "effort": _STR,
        "complexity": _STR,
        "tags": {"type": "array", "items": _STR},
        "body": _STR,
        "blocked_by": {"type": "array", "items": _BLOCKER},
        # Opaque by design (`WorkItem.capabilities` is typed `object`), so the
        # schema declares no shape — only that whatever it holds is JSON.
        "capabilities": True,
        "initiative": _STR,
        "type": _STR,
        "worktree": _STR,
        "branch": _STR,
        "parent": _STR,
        "owner": _STR,
        "started": _STR,
        "tracker": _TRACKER,
        "artifacts": {
            "type": "object",
            "additionalProperties": False,
            "properties": {name: {"type": "boolean"} for name in WORK_ARTIFACTS},
            "required": list(WORK_ARTIFACTS),
        },
    },
}
WORK_ITEM_SCHEMA["required"] = sorted(WORK_ITEM_SCHEMA["properties"])


def work_item_json(item: WorkItem, artifacts: Sequence[Artifact]) -> dict:
    """Project one work item as the versioned JSON document.

    `artifacts` is a `Sequence`, not an `Iterable`: a caller handing over a spent
    generator would get an all-absent map and no error, which is not a failure
    mode worth having.
    """
    present = {a.name for a in artifacts if a.present}
    doc: dict[str, Any] = {"schema": SCHEMA_VERSION}
    for f in fields(item):
        doc[f.name] = _json_safe(getattr(item, f.name))
    doc["artifacts"] = {name: name in present for name in WORK_ARTIFACTS}
    return doc
