# Plan — An auto-delete step with hooks

Depends on [Retain resolved work items in history](tcw://W/2026-09-03-retain-resolved-work-items-in-history-and-make-auto-delete-configurable),
recorded as a blocker on the item: tasks 3 and 4 attach to a deletion that item
creates.

## Tasks

### 1. Add `auto-delete` to the lifecycle vocabulary

**Modifies** `tcw/store/base.py`.

Add `auto-delete` to `TRANSITION_IDS` (`:609`) and a `LifecycleStep` to
`LIFECYCLE_STEPS` (`:908-931`) with `kind="transition"`,
`moves="completed | discarded → (removed)"`, and an objective saying it is
reached as part of a resolving transition under `retain: false` — not as a verb
of its own — mirroring how `discard`'s entry says the same about itself
(`:926-930`).

Add no `LEGAL_TRANSITIONS` pair (`:493-502`): no status changes. Put a comment
there saying so, next to the set, because its absence otherwise looks like an
oversight.

**Proves it:** `tests/test_lifecycle_baseline.py` and
`tests/test_lifecycle_validation.py` — `tcw work lifecycle` lists the step with
its `moves` string; a config binding `pre`/`post` under `auto-delete` validates;
an unknown id still fails naming the offender; the `LEGAL_TRANSITIONS` set is
unchanged.

### 2. Export the item's location and resolution to hooks

**Modifies** `tcw/work/hooks.py`, and the callers of `hook_env`.

`hook_env` (`:28-39`) gains `TCW_ITEM_PATH` and `TCW_RESOLUTION`. The path is the
store's own answer for the item — the same value `tcw work path <slug>` prints —
passed in by the caller, never composed from `TCW_NODE_ROOT`, because the store
may be in a different repository (`skills/tcw-work/references/commands.md`
§ Claims and external work stores states this rule).

Both are optional: a transition with no item path or no resolution — `start`,
`submit`, `rework` — omits them rather than exporting an empty string, so a hook
can test for presence.

**Proves it:** `tests/test_lifecycle_hooks.py` — a `pre` binding on `complete`
observes both variables and `TCW_ITEM_PATH` names a directory that exists at hook
time; a binding on `start` sees neither; with an external `work.path`, the
exported path is inside the store's repository and not under the node root.

### 3. Run the bindings between the two commits

**Modifies** `tcw/store/fs.py`, `tcw/work/cli.py`.

The blocking item's deletion path gains its hook points, run from the CLI layer
where every other binding runs — `hooks.py`'s docstring gives the reason a store
method must not shell out, and it applies here unchanged.

Order: first commit lands (item in its resolved folder, graveyard recorded) →
`run_pre` for `auto-delete` → deletion → second commit → `run_post`.

A `pre` failure returns before the deletion, leaving the item present, recorded
and committed. The command exits non-zero and its message names the failing
binding and says the item was kept, so the state reads as finishable rather than
broken.

The deletion treats an absent path as already done — the folder-move scenario —
and the second commit still records the removal.

**Proves it:** `tests/test_lifecycle_hooks.py` — a passing `pre` yields two
commits and no folder; a failing `pre` yields one commit, the folder present, the
graveyard recorded, and a non-zero exit naming the binding; a `pre` that moves
the folder away yields two commits and no error; `post` runs after the second
commit and its failure does not undo it; `retain: true` runs no `auto-delete`
bindings at all.

### 4. `tcw work delete <slug>`

**Modifies** `tcw/work/cli.py`.

The manual entry point for the state a failed archive leaves: an item resolved,
recorded, still present. It runs the *same* code path as task 3 — one
implementation, two callers, which is the spec's requirement — so the bindings
run again in the same order.

Refuse on an item that is not resolved (that is `tcw work drop`'s territory), and
on a node whose retention keeps the status. Add it to
`skills/tcw-work/references/commands.md` in task 6, beside `drop`, with the
distinction spelled out: `drop` deletes a backlog item and keeps no record;
`delete` finishes the removal of an item already resolved and recorded.

**Proves it:** `tests/cli` — after a failed archive, `tcw work delete <slug>`
with a passing binding completes the deletion; on a live item it refuses; under
`retain: true` it refuses naming the config key.

### 5. `tcw serve` stops short of the deletion

**Modifies** `tcw/serve/__init__.py`.

`serve` runs no hooks by design (`tcw/work/hooks.py:14-17`). Under `retain:
false` that would mean a web-driven resolution deletes the item with no archive —
the one destructive outcome available in this item. So `serve` performs the
resolving transition and stops: the item stays in its resolved folder for a CLI
`tcw work delete` to finish.

Surface it in the UI response rather than silently: the resolution succeeded and
the removal is pending.

**Proves it:** `tests/test_serve.py` — resolving through the HTTP surface under
`retain: false` leaves the item present and recorded, runs no bindings, and the
response says the removal is pending; under `retain: true` the behavior is
unchanged.

### 6. Documentation Sync

One pass over the finished diff.

- **`README.md`** — [Public-API]. Fires. The lifecycle section gains
  `auto-delete`, the two new environment variables, and the two supported
  archival shapes. State the two non-promises the capability states: TCW cannot
  tell whether the archive really happened, and a `skill:` binding is reported
  rather than run, so a guarantee belongs in a `command:`.
- **`docs/release-notes/upcoming.md`** — [Public-API]. Fires. Plain language: if
  you let TCW delete finished work, you can have it hand the item to your own
  archive first, and it keeps the item if your archive fails.
- **`docs/changelogs/upcoming.md`** — [Any-Code-Change]. Fires. Added: the
  `auto-delete` step, `TCW_ITEM_PATH`, `TCW_RESOLUTION`, `tcw work delete`.
  Changed: `hook_env`, the deletion path, `serve`'s resolution behavior.
- **`skills/<component>/SKILL.md`** — [Skill-Driven-Component]. Fires for
  `tcw-work`: `references/hooks.md` documents the hook environment and must gain
  both variables; `references/transitions.md` gains the step; `commands.md` gains
  `tcw work delete` beside `drop`, and its "Web editing" note gains the pending
  removal.
- **`docs/capabilities/work/archive-a-resolved-item-before-it-is-deleted/`** —
  seeded `Missing` at planning (`cap-240fde`); flip to `Supported` at completion.
- **`docs/capabilities/work/configure-the-work-lifecycle/`** — recorded as
  changed in `capabilities.yaml`. Its body enumerates the four hook variables
  verbatim and lists the transitions; both are now wrong. Drive it with the
  `tcw-capabilities` skill.

## Verification

What the suite cannot check:

- **The two named scenarios, end to end.** Write both and run them against a
  throwaway item in this repository: a `command:` that tars `$TCW_ITEM_PATH` and
  writes it somewhere (an S3 upload stands in as a local `aws --endpoint` or a
  plain `cp` of the tar — the point is the tar, not the vendor), and a `command:`
  that `mv`s `$TCW_ITEM_PATH` elsewhere. Paste the configs and the resulting
  `git log` into `outcome.md`. These are the two shapes the requester named, and
  a fixture binding that echoes a variable does not prove either works.
- **That the kept state reads as finishable.** After a deliberately failing
  archive, read the actual terminal output and confirm a user would know the item
  is safe and what to run. Criterion 4 asserts the state; only a person can
  judge whether the message earns trust.
- **The serve stop-short.** Drive a resolution through the web UI under
  `retain: false` and confirm the pending removal is visible rather than
  something the user discovers later from `tcw work list`.

## Notes

Task 1 lands before the blocking item's deletion path exists and is inert until
task 3, which keeps this item's first commits independent of that one's
sequencing.

Task 5 is the only place where "the web UI does not drive the lifecycle" becomes
code rather than a convention. Worth flagging at review: it is a deliberate
narrowing of what `serve` completes, and someone will eventually read it as a
missing feature rather than a decision.
