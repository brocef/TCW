# Plan — `capabilities set` resolves inherited paths

Implements `spec.md`. Scope confirmed by the user: fix **both** write paths
(`set` + web `update_capability`) through one shared helper, **and** extend the
revision to cover override files. The `capabilities/set-a-capabilitys-status`
declaration is part of this item (already seeded `Partial` at the planning gate).

Execution: **sequential**. The phases share one file (`tcw/store/fs.py`) and one
~40-line change; parallel subagents would collide for no wall-clock gain.

## Phase 1 — failing tests (TDD)

File: `tests/test_capabilities_federation.py` (extends the existing `write_cap`
fixture pattern; `master` + `child` stores already modeled there).

Store-level tests:

1. `set` on an alias-qualified inherited path (`shared/moderation/report-content`)
   → succeeds; `get()` reports the new Status with `origin == "shared"`.
2. `set` on the bare inherited path → identical result.
3. Materialized file lands at `<child>/docs/capabilities/moderation/report-content/meta.yaml`
   containing exactly `overrides: shared/<upstream-id>` + `Status: <new>`.
4. Second `set` updates that file in place — one override folder, no duplicate;
   idempotent for a repeated identical status.
5. An existing hand-authored override at an unrelated path (`ov/login`,
   `overrides: cap-aaa111`) is updated **in place** — not mirrored into a second
   folder.
6. Local capability `set` unchanged (no `overrides:` key appears in its meta).
7. Invalid Status / unknown field on an inherited path raises the same
   `ValueError` as local.
8. Collision guard: local `x/y` + inherited `alias/x/y`, `set alias/x/y` refuses;
   local `x/y/meta.yaml` byte-unchanged.
9. Ambiguous bare ref (two aliases exporting the same path) raises `AmbiguousRef`.
10. `tcw capabilities check` clean after materialization.
11. `remove` on an inherited path still refuses (regression guard).
12. Clear semantics: `fields={"Priority": None}` writes explicit `Priority: null`
    (effective field cleared via `_apply_override`); `--field Priority=` writes `""`.

Web/store tests — `update_capability`/revision behavior belongs in
`tests/test_store_editor.py` (the store-editor surface); the HTTP `PATCH` route
is covered in `tests/test_serve_write.py`. Follow each file's existing fixtures:

13. `update_capability` on an inherited path sets a field (`Status`) → override
    written, and the result matches what `set` produces for the same field (the
    two paths share `_merge_meta`; this test is what pins that).
14. `update_capability(body=...)` on an inherited path writes the override's
    `description.md`; composed body reflects it, upstream untouched.
15. Stale-revision: PATCH twice with the first revision → `StaleRevision`
    (fails before the Phase 3 fix — this is the test that proves the blind spot).

CLI test (`tests/test_capabilities.py` — the existing CLI-level coverage):

16. `tcw capabilities set <inherited>` exits 0 and prints `Set <path>`.
17. Ambiguous ref exits 1 with the ambiguity message, no traceback.

Run: `pytest tests/test_capabilities_federation.py -x` → expect 1–5, 8, 12–17 red.

## Phase 2 — store write-path fix

File: `tcw/store/fs.py`, `FsCapabilitiesStore`.

New private helper (FS-adapter detail, no interface change — litmus test in
`spec.md`):

```python
def _write_target(self, identifier: str) -> tuple[Path, dict, bool]:
    """(folder, meta, is_override) for a write to `identifier`.

    Local capability -> its own folder. Inherited -> the existing override for
    its upstream id, else a materialized one mirroring the upstream path.
    """
```

- local hit (`get_local`) → `(self.root / cap.path, load_yaml(...), False)`;
- else `get(identifier)` (raises `AmbiguousRef`); `None` → `ValueError("no such capability: ...")`;
- inherited → `_override_index()` lookup by `cap.id` / `f"{cap.origin}/{cap.id}"`;
  hit → that folder + meta;
- miss → mirror path `self.root / cap.path`; if it already holds a
  non-`overrides` `meta.yaml`, raise the collision error; else
  `{"overrides": f"{cap.origin}/{cap.id}"}` (folder created at write time).

The field merge is the second shared piece — `set()` and `update_capability()`
must merge identically, or the web path and the CLI path diverge on clearing:

```python
def _merge_meta(self, meta: dict, fields: dict, is_override: bool) -> dict:
    """Merge validated fields into a node's meta. On an override, a None value
    is written as explicit YAML null (= clear the inherited field); on a local
    node it pops the key."""
```

`_validate_fields` runs first and rejects any key outside `CAP_FIELDS`, so a
caller cannot reach `overrides`, `id`, or `name` through `--field` — the
structural keys (and a freshly seeded `overrides:`) survive the merge by
construction.

Rewrite `set()` (fs.py:1070) on top of both:

- `d, meta, is_override = self._write_target(identifier)`;
- `meta = self._merge_meta(meta, self._validate_fields(fields), is_override)`;
- `d.mkdir(parents=True, exist_ok=True)` then `_write_meta(d, meta)`
  (`_write_meta` does not mkdir; `_write_node` would also write an empty
  `description.md`, which we do **not** want for an override — an empty child
  description must fall through to the upstream body);
- return `self.get(identifier)` so the caller sees the composed entry.

Rewrite `update_capability()` (fs.py:1276) on the same two helpers — it takes
`fields` as well as `body`, so it routes through `_merge_meta` with the same
`is_override` flag rather than keeping its own copy of the merge. When `body` is
supplied, write `description.md` into the resolved folder (override or local).
Keep the `core_revision` stale check ahead of the write.

Verify: `pytest tests/test_capabilities_federation.py -x` → Phase 1 tests green
except the stale-revision one (15).

## Phase 3 — revision covers the override

File: `tcw/store/fs.py`, `get_capability_detail()` (fs.py:1265).

Append the local override's `meta.yaml` + `description.md` (empty string when
absent) to the existing `_revision_multi(...)` call, upstream args first, order
fixed. Local capabilities keep today's two-arg revision — no token churn.

Verify: test 15 green; `pytest tests/ -x` fully green.

## Phase 4 — CLI

File: `tcw/capabilities/cli.py`, `_set` (cli.py:99).

`AmbiguousRef` subclasses `RefError`, already caught at cli.py:117 — so likely
**no code change**. Confirm test 17's message reads sensibly; only touch the file
if it does not.

## Phase 5 — documentation sync

Triggers expected to fire (per `CLAUDE.md`):

- `README.md` [Public-API] — federation section (~line 383): the override is
  written by `tcw capabilities set <inherited-path>`; the `overrides:` file shape
  stays documented as the storage detail, no longer the front door.
- `skills/tcw-capabilities/SKILL.md` [Skill-Driven-Component] — the ledger-flip
  section (line 45–52) is the instruction that hard-failed; state that `set`
  addresses inherited paths too. Federation bullet (line 58): `set` writes the
  override; hand-authoring is no longer required. Quick-reference row for
  flipping an inherited entry.
- `docs/changelogs/upcoming.md` [Any-Code-Change] — Fixed: `set` /
  `update_capability` resolved only local declarations; Fixed: inherited
  capability revision ignored override files. With commit range.
- `docs/release-notes/upcoming.md` [Public-API] — plain language: flipping an
  inherited capability's status now works with the normal command.

Run `skill-cefailures:documentation-sync` before reporting complete.

## Phase 6 — ledger flip (at completion, not before)

- `tcw capabilities set capabilities/set-a-capabilitys-status --status Supported`
  and clear the now-false `Gaps` (`--field Gaps=` leaves `""` — remove the key
  instead; this is the local path, where `None` pops).
- `capabilities/override-inherited` (`cap-9e644f`): stays `Supported`; give its
  empty `description.md` a body naming the command route.
- `tcw capabilities check` + `tcw validate` clean.

## Touch points

| File | Phase |
|---|---|
| `tests/test_capabilities_federation.py`, `tests/test_store_editor.py`, `tests/test_serve_write.py`, `tests/test_capabilities.py` | 1 |
| `tcw/store/fs.py` (`_write_target`, `set`, `update_capability`, `get_capability_detail`) | 2, 3 |
| `tcw/capabilities/cli.py` | 4 (likely none) |
| `README.md`, `skills/tcw-capabilities/SKILL.md`, `docs/changelogs/upcoming.md`, `docs/release-notes/upcoming.md` | 5 |
| `docs/capabilities/capabilities/{set-a-capabilitys-status,override-inherited}/` | 6 |

## Verification commands

```sh
pytest tests/test_capabilities_federation.py -x     # phases 1-3
pytest tests/ -q                                    # full suite, incl. plugin manifests
tcw capabilities check && tcw validate              # this node's own ledger
```

Plus the end-to-end repro from `spec.md` (two scratch git repos, `extends`,
`set` an inherited path) — the reporter's exact transcript must succeed.

## Out of scope

Backfilling the reporter's 8 unflipped capabilities; DoD-gate enforcement
(tracked by `2026-07-15-capability-drift-enforce-the-dod-gate-at-complete-and-distinguish-unreviewed-from-decided-missing`);
migrating hand-authored overrides to mirrored paths (both layouts stay legal).

**Dropping an override (follow-up candidate).** Once `set` can *create* an
override, there is no command to *remove* one and revert to the upstream value —
`remove` refuses anything inherited (correctly: it must not imply deleting the
upstream entry). The workaround is deleting the local override folder by hand,
which is the same hand-editing complaint this item is fixing, one level down.
Surfaced by the plan review; not in this item's scope. Raise it at closeout as a
follow-up TCW item (`tcw capabilities reset <path>` / `remove --override`, naming
to be decided there).
