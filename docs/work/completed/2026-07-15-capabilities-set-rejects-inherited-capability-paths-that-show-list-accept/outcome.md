# Outcome

Work completed successfully. The reporter's exact transcript now succeeds; the
plan's six phases all landed, with two additions discovered during
implementation (both recorded below).

## What changed

**The fix (`tcw/store/fs.py`).** `set()` and `update_capability()` both opened
with `get_local()`, which matches only local, non-override folders, while
`show`/`list` resolve the federated view via `get()`. Both write paths now route
through a shared pair:

- `_write_target(identifier) -> (folder, meta, is_override)` — local capability →
  its own folder; inherited → its existing override (wherever authored, found by
  upstream id) or a fresh delta mirroring the upstream path, seeded
  `overrides: <alias>/<id>`. Refuses to clobber a local capability already
  occupying the mirrored path.
- `_merge_meta(meta, norm, is_override)` — on an override a `None` writes an
  explicit YAML `null` (`_apply_override` reads that as *clear the inherited
  field*); on a local node it pops, as before. Sharing this is what keeps the CLI
  and web paths from diverging on clearing.

`set()` validates fields before touching disk and returns `self.get(identifier)`
(the composed entry) rather than the bare delta.

**Revision (`get_capability_detail`).** For an inherited capability the revision
covered only the upstream `meta.yaml`/`description.md`, so two successive edits
to the same override hashed identically and `StaleRevision` never fired — on
exactly the path this item was opening up. It now folds in the override's files
(upstream args first, order fixed). Local capabilities keep their two-argument
revision, so no token churn.

**Docs.** `skills/tcw-capabilities/SKILL.md` (the ledger-flip instruction that
hard-failed, plus the federation section that told authors to hand-write the
file — contradicting the skill's own "never hand-edit capability metadata when
`set` applies" rule), `README.md`, changelog, release notes.

## Deviations from plan.md

Two, both discovered by verification rather than planned:

1. **`AmbiguousRef` gained a message** (`tcw/store/base.py`). Plan Phase 4
   predicted "likely no code change" — the CLI already catches `AmbiguousRef`
   via its `RefError` base. It does catch it, but the exception was raised with
   the bare ref as its only argument, so `str(e)` printed
   `tcw capabilities set: x/thing` — an unexplained path, failing the spec's
   acceptance criterion that ambiguity be *reported*. Fixed in the exception
   rather than at the call site, so `show`, `set`, and the web app's 422 body all
   benefit (the taxonomy CLI hand-rolls its own message per call site and is
   unaffected). This is the risk the spec flagged as "verify the message reads
   sensibly rather than assuming" — it did not.
2. **`update_capability` skips the empty `description.md`.** `_write_node` always
   writes both files; for an override with no body supplied that would leave an
   empty `description.md`. Harmless to composition (an empty child body falls
   through to upstream) but it makes the delta untidy, so the override stays a
   pure `meta.yaml` unless a body is given or one already exists.

## Verification performed

Full suite: **569 passed** (`python -m pytest tests/ -q`), up from 567 —
26 new tests, 0 regressions. `tcw validate` and `tcw capabilities check` clean on
this node.

New coverage: `tests/test_capabilities_federation.py` (materialization at the
mirrored path, in-place reuse of a hand-authored override, idempotence, twice-set,
local-unchanged, validation, collision guard, ambiguity, null-clear vs local-pop,
`remove` still refusing); `tests/test_store_editor.py` (inherited fields, body,
web-vs-CLI merge parity, stale revision, revision tracks override body);
`tests/test_capabilities.py` (the reporter's transcript end-to-end, ambiguity
message).

End-to-end against two real scratch git repos — the reporter's exact command:

```
$ tcw capabilities set shared/moderation/report-content --status Supported
Set moderation/report-content                                     # exit 0

$ cat docs/capabilities/moderation/report-content/meta.yaml
overrides: shared/cap-afd9d2
Status: Missing

$ tcw capabilities check && tcw validate                          # both clean
```

Upstream node verified untouched (`Status: Supported` at the master). Ambiguity
now reads `ambiguous ref 'x/thing' — qualify it with an alias prefix` on both
`set` and `show`.

Pre-fix baseline captured before any edit: both the alias-qualified and bare
forms failed with `no such capability`, confirming the report against v0.11.3.

## Follow-up notes (not yet TCW items — a closeout decision)

1. **No way to drop an override.** `set` can now create one, but reverting to the
   upstream value means deleting the local folder by hand — the same hand-editing
   complaint this item fixes, one level down. `remove` refuses anything inherited
   (correctly; it must not imply deleting the upstream entry). Wants a
   `tcw capabilities reset <path>` or `remove --override`. Surfaced by the plan
   review.
2. **Redundant override on a no-op flip.** Setting an inherited capability to the
   status it already inherits writes an override asserting the same value.

   Harmless and arguably an intentional local assertion, so left alone.
3. **Related open item:**
   `2026-07-15-capability-drift-enforce-the-dod-gate-at-complete-and-distinguish-unreviewed-from-decided-missing`
   — that item enforces the flip at the DoD gate; this one made the flip possible.
   The reporter hit both as one symptom (8 capabilities shipped in code but still
   reading `Missing`).

## Pending at closeout

- Ledger flip (plan Phase 6, deliberately not yet run): `capabilities/set-a-capabilitys-status`
  `Partial` → `Supported` + drop the now-false `Gaps`; give
  `capabilities/override-inherited` its empty `description.md` a body.
- Version bump choice, completion route, and whether follow-up 1 becomes an item.
