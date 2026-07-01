# Spec — optional effort & complexity fields for work items

Small, additive change. This spec is compressed but complete enough to resume from.

## Capability changes

One new `Missing` capability in `docs/capabilities/work/capabilities.md`, worded
parallel to the existing "Prioritize a work item":

> **Estimate a work item's effort and complexity** — Supported (once shipped)
> **Subject:** work-item
>
> As a user, I record coarse estimates with `tcw work new "<title>" --effort <level>
> --complexity <level>` or `tcw work edit <slug> --effort <level> --complexity
> <level>`, where `<level>` is one of `low | medium | high | very-high`. Both fields
> are optional and default to unset. `tcw work show` displays them when set. They
> are estimation signals only and do not affect board ordering.

No taxonomy Vocabulary/Feature change: "effort" and "complexity" are ordinary
attributes of the existing `work-item` term, not new domain nouns.

## Problem

Work items carry `priority` but no estimate of *how much work* or *how hard*. Users
triaging a backlog want a coarse effort/complexity signal per item.

## Goals

- Two optional fields, `effort` and `complexity`, on every work item.
- Settable at creation (`new`) and later (`edit`); visible in `show`.
- Constrained to `low | medium | high | very-high`; invalid values rejected.

## Non-goals

- No board re-ordering, filtering, or sorting by these fields.
- No numeric/story-point scale; no clear-to-empty flag.
- No change to `tcw work list` output.

## Constraints

- **Abstraction litmus (AGENTS.md):** these are named fields on an item — a Jira/
  wiki store has direct analogs. They belong in the model spine, realized by the FS
  adapter through the existing generic `state.yaml` + `set_field` path. No
  filesystem-only trick is introduced.
- Match the existing `priority` field's shape and the `--resolution` validation idiom.

## Current-state findings

- `tcw/store/base.py:197` — `WorkItem` dataclass; `priority` (`:206`) is the model
  for an optional scalar field. Value-set constants (`WORK_RESOLUTIONS`,
  `CAP_STATUSES`) already live here as the portable vocabulary.
- `tcw/store/fs.py:907` `_item_from_dir` — reads each field from `state.yaml`
  (`priority=state.get("priority")` at `:924`). `set_field` (`:997`) is fully
  generic — writes any key; **no store change needed to persist new keys**.
- `tcw/work/cli.py`:
  - `_print_item` (`:47`) prints `priority` at `:58` — display insertion point.
  - `_new` (`:145`) sets `--epic`/`--initiative` via `set_field` after `create`
    (`:162-165`) — the pattern to follow for the new flags (no `create` signature
    change).
  - `_edit` (`:282`) sets `--priority`/`--initiative` via `set_field` (`:301-304`).
  - `new`/`edit` parsers (`:398`, `:427`); `complete --resolution` uses
    `choices=sorted(WORK_RESOLUTIONS)` (`:438`) — the validation idiom to reuse.

## Proposed behavior

**Spine (`base.py`):**
- Add `WORK_LEVELS = ("low", "medium", "high", "very-high")`.
- Add `effort: str = ""` and `complexity: str = ""` to `WorkItem` (after `priority`).

**FS adapter (`fs.py`):**
- In `_item_from_dir`, read `effort=state.get("effort", "")` and
  `complexity=state.get("complexity", "")`. Nothing else — `set_field` already
  persists them.

**CLI (`work/cli.py`):**
- `new` + `edit` parsers gain `--effort` / `--complexity`, both
  `choices=WORK_LEVELS`. When provided, apply via `set_field` (mirroring
  `--initiative`). No clear-to-empty.
- `_print_item` prints `effort:` / `complexity:` after `priority` when non-empty.
- `list` output unchanged.

## Acceptance criteria

1. `tcw work new "T" --effort high --complexity low` creates an item; `state.yaml`
   has `effort: high`, `complexity: low`.
2. `tcw work edit <slug> --effort medium` updates only effort.
3. `tcw work show <slug>` prints `effort:`/`complexity:` lines when set, omits them
   when unset.
4. `--effort bogus` is rejected by argparse (non-zero exit, usage error) — no write.
5. `tcw work list` output is byte-identical to before for items with/without the
   fields.
6. Items created before this change (no keys in `state.yaml`) read back with empty
   effort/complexity and display/serialize cleanly.

## Risks & dependencies

- Low risk; purely additive, no migration (absent keys read as `""`).
- Docs-sync triggers that will fire (tasks for `plan.md`): README `work new/edit`
  flag list; `skills/tcw-work/SKILL.md` quick-reference; `docs/changelogs/upcoming.md`;
  `docs/release-notes/upcoming.md`; `docs/capabilities/work/capabilities.md` (new
  capability above). `tests/test_plugin_manifests.py` / version files: **not** touched
  (no release cut here — version bump is a closeout decision).
- No related/blocking work items.
