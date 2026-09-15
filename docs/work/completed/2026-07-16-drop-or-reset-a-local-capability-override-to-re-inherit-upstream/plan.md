# Plan: drop/reset a local capability override

Derived from `spec.md`. Small, single-threaded, TDD (failing test per behavior first).

## Phase 1 — store (`base.py` + `fs.py`)

1. `tcw/store/base.py` — `CapabilitiesStore`: add abstract
   `reset(self, identifier: str) -> None` (docstring: drop the local override,
   re-inherit upstream; `ValueError` when none; never mutate an extended store).
   Only `FsCapabilitiesStore` implements the ABC, so no other adapter breaks.
2. `tcw/store/fs.py` — `FsCapabilitiesStore.reset` (beside `remove`, ~`fs.py:1058`):
   - `get_local(identifier)` non-None → refuse ("local capability, use `remove`").
   - else `get(identifier)` (may raise `AmbiguousRef`); None → "no such capability".
   - look up the override via `_override_index()` by `cap.id` then
     `f"{cap.origin}/{cap.id}"`; None → refuse ("no local override … inherits verbatim").
   - `self._rm(ov[0])` — remove only the local override folder.

**Verify:** `pytest tests/ -k "capabilit and (reset or override)"`; `python -c "import tcw.store.fs"`.

## Phase 2 — CLI (`tcw/capabilities/cli.py`)

1. `_reset(args)` mirroring `_set`: `_store()`, `st.reset(args.id)` in a
   `try/except (ValueError, RefError, AmbiguousRef)` → stderr + return 1; on success
   `print(f"reset {args.id}")`.
2. Add `"reset"` to `SUBCOMMANDS`; add a `reset` subparser (`id` positional,
   `metavar="path"`) with `set_defaults(func=_reset)`.
3. Import `AmbiguousRef` is already imported.

**Verify:** `pytest tests/ -k "cli and capabilit"`; manual: federate → `set` an
override → `reset` → `show` shows upstream.

## Phase 3 — new capability (ledger)

`tcw capabilities add capabilities/reset-an-override "Reset an override" --status Missing`
then `set … --field "Planning doc=2026-07-16-drop-or-reset-a-local-capability-override-to-re-inherit-upstream"`
and `--field "Subject=capability"`; relate to `capabilities/override-inherited`
(body prose `tcw://C/capabilities/override-inherited`). Record `new:` in this
item's `capabilities.yaml`. Flip to `Supported` at completion.

## Phase 4 — docs (documentation-sync)

- `README.md` — `tcw capabilities reset <path>` in the capabilities section.
- `docs/release-notes/upcoming.md` — "revert a federated override to upstream".
- `docs/changelogs/upcoming.md` — Added: `reset` (interface + FS + CLI).
- `skills/tcw-capabilities/SKILL.md` — override lifecycle drop step + quick-ref row.

## Tests (`tests/test_capabilities_federation.py` or a new `test_capabilities_reset.py`)

Two-node federated `tmp_path` fixture (mirror existing federation tests):
- reset removes an override, re-inherits upstream (criterion 1), incl. the
  alias-qualified folder-placement variant;
- reset refuses a standalone local (2), an un-overridden inherited path (3),
  unknown/ambiguous (4);
- upstream tree hash unchanged across reset (5).

## Verification (full)

- `pytest` green; `tcw validate` clean; `tcw capabilities check` clean.
- `verify`/manual: federate two nodes, override, reset, confirm re-inheritance and
  that the upstream node is untouched.
