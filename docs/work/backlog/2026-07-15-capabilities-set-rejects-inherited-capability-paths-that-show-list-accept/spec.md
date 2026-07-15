# Spec — `capabilities set` rejects inherited capability paths

Source: https://github.com/brocef/TCW/issues/3 (v0.11.3).

## Capability changes

Product delta, recorded as a **changed** capability (see `capabilities.yaml`):

- `capabilities/override-inherited` (`cap-9e644f`, currently `Supported`) — an
  override remains the only way a child node alters an inherited capability, but
  it becomes reachable through `tcw capabilities set` (and the web editor)
  instead of only by hand-authoring `meta.yaml`. Status stays `Supported`; the
  scope of *how* the user does it widens. Body is currently empty; give it one
  sentence naming the command-driven route.

No new capability is required for the fix itself. Two ledger observations
surfaced for the user rather than silently actioned:

- There is **no** declared capability for `tcw capabilities set` at all (add,
  read, search, browse, federate, override, validate are declared; setting
  status/fields is not). That is a pre-existing ledger gap this item exposes but
  did not create — candidate follow-up item, not scope creep here.
- `capabilities/override-inherited` reads `Supported` today while the documented
  command route hard-fails. After this fix the entry becomes honest as written.

Contradiction check: `tcw capabilities check` is clean; no `Supported` entry
contradicts the proposed behavior (the fix makes an existing `Supported` entry
true rather than asserting anything new).

## Problem

In a node that federates another via `tcw capabilities extends <alias> <ref>`,
an inherited capability resolves for reads but not for writes.

Reproduced against v0.11.3 (fixture: `master` declares
`moderation/report-content`, `child` extends it as `shared`):

```
$ tcw capabilities list
[Supported]	shared/moderation/report-content	Report content

$ tcw capabilities show shared/moderation/report-content     # ok
$ tcw capabilities show moderation/report-content            # ok (bare-wins-local, falls through to inherited)

$ tcw capabilities set shared/moderation/report-content --status Missing
tcw capabilities set: no such capability: shared/moderation/report-content     # exit 1
$ tcw capabilities set moderation/report-content --status Missing
tcw capabilities set: no such capability: moderation/report-content            # exit 1
```

Both addressing forms fail; the reporter's transcript matches exactly.

### Root cause

`tcw/store/fs.py` — the read and write paths resolve through different methods:

- `FsCapabilitiesStore.get()` (fs.py:998) resolves the **federated** view: alias
  prefix → `get_inherited()`, else bare-wins-local, else a unique inherited
  match, with `_apply_override()` merged on top. `show`/`list`/`search` use it.
- `FsCapabilitiesStore.set()` (fs.py:1070) opens with
  `cap = self.get_local(identifier)`, and `get_local()` (fs.py:970) returns a
  capability **only** for a local, non-override `meta.yaml` folder. Every
  inherited path returns `None` → `no such capability`.

The error message is also misleading: the capability exists and is printable; it
is only unwritable.

A sweep of every `get_local()` call site confirms the blast radius is exactly two
write paths (fs.py:1071 `set`, fs.py:1282 `update_capability`). The other call
sites (fs.py:575/579/588 taxonomy, 1002/1006/1017 capability resolution) are
resolution internals where local-only lookup is the intended semantics.
`remove()` (fs.py:1042) already resolves through `get()` and refuses inherited
entries deliberately — it is correct as written and out of scope.

### The same bug has a second caller

`FsCapabilitiesStore.update_capability()` (fs.py:1276) — the `tcw serve` web
editor's `PATCH /api/capabilities/<ref>` handler (`tcw/serve/__init__.py:997`) —
opens with the identical `self.get_local(identifier)` line, while its read
sibling `get_capability_detail()` (fs.py:1265) uses `get()`. So the web app
displays an inherited capability and refuses to save it, for the same reason.
Fixing only `set` would leave the web route broken, so the fix belongs in shared
resolution both methods route through.

## Goals

1. `tcw capabilities set <path>` accepts any path `show` accepts — bare or
   alias-qualified — and materializes/updates the local override file itself.
2. The web editor's capability PATCH accepts inherited paths on the same terms.
3. The override file shape is documented as the *storage* detail it is, with the
   command as the front door.

## Non-goals

- Editing the upstream node from the child. An override is still a local delta;
  inherited entries stay structurally read-only (`remove` keeps refusing).
- `capabilities add --overrides`. `add` scaffolds a fresh local declaration;
  overriding is `set`'s job now. No new flag.
- Reworking override *placement* for hand-authored overrides that already exist
  (e.g. an `ov/login` folder). They keep working and are updated in place.
- Backfilling the reporter's 8 unflipped capabilities, or the DoD-gate
  enforcement tracked separately in
  `2026-07-15-capability-drift-enforce-the-dod-gate-at-complete-and-distinguish-unreviewed-from-decided-missing`.

## Constraints

- **Abstraction litmus test:** "could a non-filesystem store implement this?" —
  yes. The operation is *record a local field delta against an inherited item,
  keyed by the upstream stable id*. A Jira/graph adapter stores that delta its
  own way. The `set` contract in `CapabilitiesStore` (base.py:256) needs no new
  method and no signature change; only the FS adapter learns to realize the delta
  as an override folder. Folder placement stays a private FS detail.
- The locked field vocabulary (`CAP_FIELDS`) and `CAP_STATUSES` validation apply
  unchanged to override writes.
- Override semantics already defined by `_apply_override()` (fs.py:936) must be
  honored, not re-invented: fields partial-merge, YAML `null` clears an inherited
  field, `overrides:` targets a bare `<id>` or `<alias>/<id>`.

## Affected surfaces

| Surface | File | Change |
|---|---|---|
| store (write path) | `tcw/store/fs.py` | `set()`, `update_capability()`, new private override-resolution helper |
| CLI | `tcw/capabilities/cli.py` | `_set` must catch `AmbiguousRef` (see risk below) |
| web | `tcw/serve/__init__.py` | none expected — inherited PATCH starts working via the store |
| skill | `skills/tcw-capabilities/SKILL.md` | ledger-flip + federation sections |
| docs | `README.md`, changelog, release notes | override route |

## Proposed behavior

`set(identifier, fields)`:

1. `get_local(identifier)` → if a local capability, today's behavior, unchanged.
2. Otherwise `get(identifier)` (federated resolution; propagates `AmbiguousRef`).
   `None` → `no such capability: <id>` as before.
3. For an inherited hit, resolve the override folder:
   - an existing override for that upstream id — `_override_index()` keyed by
     `<id>` or `<alias>/<id>` — is **updated in place** (so hand-authored
     overrides anywhere in the tree keep their location);
   - otherwise materialize a new one at the **upstream path mirrored locally**
     (`docs/capabilities/<upstream-path>/meta.yaml`), seeded
     `overrides: <alias>/<id>` (alias-qualified — unambiguous by construction).
     The mirrored path is taken from the resolved `Capability.path`, which is
     already the alias-free upstream path (`Capability.qualified` is the form
     that carries the `<alias>/` prefix). So both `set shared/moderation/report-content`
     and the bare `set moderation/report-content` mirror to the same
     `moderation/report-content` folder — no prefix stripping by hand.
     A mirrored folder is invisible to `list`/`check`'s local enumeration because
     `_local_paths()` already excludes `overrides:`-bearing meta dirs.
4. Merge the validated fields into the override meta and write. In an override,
   a `None` value is written as explicit YAML `null` (= *clear the inherited
   field*, per `_apply_override`) rather than popped — popping would silently
   mean "re-inherit", a different intent. CLI `--field K=` yields `""`, never
   `None`, so this only reaches the web path.
5. Return the composed federated capability (`get(identifier)`), so the caller
   sees the effective post-merge entry, not the bare delta.

`update_capability()` routes through the same helper, and additionally writes a
child `description.md` into the override folder when `body` is supplied — which
is exactly the documented body-composition rule, no new concept.

CLI output stays `Set <path>`.

### Revision for an inherited capability (web only)

`get_capability_detail()` currently hashes `_revision_multi(upstream meta.yaml,
upstream description.md)`. For an inherited capability it must also cover the
local override's files, or two successive PATCHes to the same override compute an
identical revision and stale-write rejection silently never fires:

```
core_revision = _revision_multi(upstream meta.yaml, upstream description.md,
                                override meta.yaml or "", override description.md or "")
```

`_revision_multi` is already varargs (fs.py:396), so this is an argument change,
not a new mechanism. A local (non-inherited) capability's revision is unchanged —
the two extra arguments are absent, not empty, so existing revisions do not churn.
Ordering is fixed (upstream before override) to keep the token stable.

### Collision guard

If the mirrored path is already occupied by a *local, non-override* capability
folder, refuse with a clear error naming both. This is only reachable by
addressing `alias/x/y` explicitly while a local `x/y` also exists (a bare ref
would have won local at step 1). Rare, but it must not clobber a real local
declaration.

## Acceptance criteria

- `tcw capabilities set shared/moderation/report-content --status Missing`
  succeeds in the repro fixture, exits 0, and `show` then reports
  `Status: Missing` with `[shared]` origin retained.
- The bare form `set moderation/report-content --status Missing` behaves
  identically.
- The materialized file is `docs/capabilities/moderation/report-content/meta.yaml`
  containing `overrides: shared/cap-XXXXXX` + `Status: Missing`, and nothing else.
- A second `set` on the same path updates that file in place (no duplicate
  override folder, idempotent as the skill promises).
- An existing hand-authored override at an arbitrary path (`ov/login`) is updated
  in place, not duplicated.
- A local capability's `set` is byte-identical to today (no override machinery).
- Invalid status/field on an inherited path fails validation the same as local.
- `tcw capabilities check` is clean after every materialization.
- An ambiguous bare ref (two aliases exporting the same path) reports the
  ambiguity rather than a false `no such capability`, and the CLI prints that
  message (not a traceback) with a non-zero exit.
- The collision guard fires: with a local `x/y` **and** an inherited
  `alias/x/y`, `set alias/x/y --status Missing` refuses with an error naming both
  and leaves the local `x/y/meta.yaml` byte-unchanged.
- Field-clearing semantics on an override are distinguishable and tested:
  a web `fields: {Priority: null}` writes explicit `Priority: null` (effective
  field cleared), while CLI `--field Priority=` writes the empty string (field
  set to empty) — the two must not collapse into each other.
- Web `PATCH /api/capabilities/<inherited-ref>` updates status and body.
- A second web PATCH carrying the first PATCH's revision is rejected as stale
  (guards the revision fix above; fails today because the override files are not
  in the revision).
- `tcw capabilities remove <inherited>` still refuses.

## Risks

- **`AmbiguousRef` escaping the CLI.** `_set` (cli.py:116) catches
  `(ValueError, RefError)`; `AmbiguousRef` subclasses `RefError` (base.py:26), so
  it is already caught — but only once `set` starts calling `get()`, which is
  what raises it. Verify the message reads sensibly rather than assuming.
- **Stale-revision blind spot (web).** `get_capability_detail()` computes the
  revision from `owner.root / cap.path` — the **upstream** files — so for an
  inherited capability it ignores the local override's `meta.yaml`. Enabling
  override writes via PATCH makes concurrent-edit detection unreliable on exactly
  the new path: two edits to the same override produce the same upstream-derived
  revision. Fixing the revision to cover the override files is a small, contained
  addition and should ride along; flagged for the user as the one judgment call
  that widens the diff.
- **Mirrored-path placement** is a convention choice. Hand-authored overrides
  elsewhere stay supported, so this is not a migration — but it does mean two
  override layouts coexist in the wild. Documenting the mirrored path as what the
  tool produces (not as the only legal shape) keeps that honest.

## Dependencies and related work

- Related, not blocking:
  `2026-07-15-capability-drift-enforce-the-dod-gate-at-complete-and-distinguish-unreviewed-from-decided-missing`
  — that item enforces the flip at the gate; this one makes the flip possible for
  inherited entries. The reporter hit both as one symptom (8 capabilities shipped
  but still reading `Missing`).
- Doc-sync triggers expected to fire: `README.md` (Public-API), `docs/release-notes/upcoming.md`,
  `docs/changelogs/upcoming.md`, `skills/tcw-capabilities/SKILL.md` (Skill-Driven-Component).
