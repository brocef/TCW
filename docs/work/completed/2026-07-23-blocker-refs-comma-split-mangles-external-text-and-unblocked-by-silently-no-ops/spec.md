# Spec — Blocker refs: comma-split mangles external text and `--unblocked-by` silently no-ops

No product delta on the capabilities axis: this is a CLI-surface bug fix on an
existing capability (recording and clearing blockers), not a new user-facing
ability. No `## Capability changes` section.

## Problem

Three compounding defects make external blockers effectively unremovable while
the CLI reports success. See `initial-request.md` for the reproduction.

## Current-state findings

- `WorkStore.remove_blocker` (`tcw/store/base.py:872`) filters `blocked_by` and
  writes only when the length changed. A no-match returns `None` silently.
- `_edit` (`tcw/work/cli.py:501`) calls it in a loop and then unconditionally
  prints `edited <slug>`. Compare `--blocks` (`tcw/work/cli.py:491-495`), which
  validates each ref up front and fails closed with `no such work item: <ref>`.
- `unresolved_blockers` (`tcw/store/base.py:912`) and `_print_item`
  (`tcw/work/cli.py:112`) both render an external blocker as `external: <text>`,
  but `remove_blocker` compares against the bare `<text>`, and `_entry_for`
  (`tcw/store/base.py:835`) stores the bare `<text>`. So the string the board
  prints never matches on input.
- `_split` (`tcw/work/cli.py:81`) comma-splits `--blocked-by`, `--unblocked-by`,
  and `--blocks`. Slugs cannot contain a comma (`slugify` → `[a-z0-9-]`), so only
  the two external-bearing flags are affected.
- `README.md:492` already documents `--blocked-by "other-slug,external:JIRA-123"`
  — the `external:` prefix on *input* is the documented intent, so the display
  side is correct and the input side is the bug.
- Blockers also arrive through the web app: `tcw/serve/__init__.py:736` forwards a
  `blockers` list into `update_work`, which builds entries via `_entry_for`
  (`tcw/store/fs.py:2217,2324`). Any normalization must therefore live in
  `_entry_for`, not in the CLI, or the web path stays broken.

## Goals

1. `--unblocked-by` fails closed when the ref matches no blocker on the item.
2. The ref accepted on input round-trips with what `list` / `show` print: a
   leading `external:` prefix is stripped on input, and the display keeps the
   prefix (user decision, 2026-07-23).
3. An external blocker's text survives a comma.

## Non-goals

- Changing `--blocks` parsing. Its values are slugs, which cannot contain a
  comma; leaving it comma-split avoids churn for no defect.
- Any store-interface or filesystem-adapter change. The litmus test is not in
  play — this is core semantics plus flag parsing.
- Deduplicating or otherwise reworking external blocker identity beyond exact
  text match.

## Proposed behavior

### Ref normalization (shared, in the store core)

A new `WorkStore._normalize_ref(ref)` strips one leading `external:` prefix
(with optional following whitespace) and surrounding whitespace. It is applied in
`_entry_for` **before** the `self.get(ref)` slug probe and in `remove_blocker`
before matching. A slug can never begin with `external:`, so the probe is
unaffected. Placing it in the two shared helpers means CLI, web, `create_work`,
and `update_work` all inherit the fix — one guard where every caller routes
through.

Consequence: `--blocked-by "external: JIRA-123"` and `--blocked-by "JIRA-123"`
are the same blocker, and either string removes it.

### `remove_blocker` fails closed

`remove_blocker` raises `ValueError(f"no such blocker on {slug}: {ref}")` when the
normalized ref matches no entry. `_edit` already wraps its store calls in
`_ERRORS`, so the CLI prints the message and exits non-zero without further
change. This is a deliberate asymmetry with `add_blocker`, which stays idempotent
— adding what is already there is harmless; removing what is not there is the
silent failure being fixed.

### Repeatable blocker flags

`--blocked-by` and `--unblocked-by` on both `tcw work new` and `tcw work edit`
become `action="append"` (the existing `--tag` idiom) and stop routing through
`_split`. One flag occurrence = one blocker, comma or not.

This is a breaking change to the comma form:
`--blocked-by "a,b"` previously recorded two blockers and now records one
external blocker literally named `a,b`. Called out in the release notes.

## Acceptance criteria

1. `tcw work edit <slug> --blocked-by "waiting on vendor A, then legal signoff"`
   records exactly one external blocker whose text contains the comma.
2. `tcw work edit <slug> --unblocked-by "external: waiting on vendor A, then legal
   signoff"` — the exact string `show` prints — removes it and exits 0.
3. `tcw work edit <slug> --unblocked-by "not-a-blocker"` exits non-zero, prints
   `no such blocker on <slug>: not-a-blocker` to stderr, and leaves `state.yaml`
   unchanged.
4. `--blocked-by` / `--unblocked-by` given twice record/remove two blockers.
5. `--blocked-by "external: JIRA-123"` and `--blocked-by "JIRA-123"` produce the
   same stored entry, and adding both is idempotent.
6. A blocker added through the web app's `blockers` field is normalized the same
   way.

## Risks

- Existing items may already hold mangled multi-entry blockers from the old
  comma-split. Not migrated; they remain individually removable by their stored
  text, which is exactly what the fix enables.
- Users scripting the comma form get a silent behavior change (one blocker
  instead of N) rather than an error. Accepted: the alternative is rejecting
  commas outright, which defeats goal 3.

## Documentation sync

- `README.md:492,519,521` — repeatable flag form.
- `docs/release-notes/upcoming.md` — the fix plus the comma-form breaking change.
- `docs/changelogs/upcoming.md` — Fixed / Changed entries.
- `skills/tcw-work/SKILL.md` — no blocker-flag row exists today; add one only if
  the quick reference gains one, otherwise no change.

## Related work

None blocking. Independent of
`2026-07-23-cross-node-epic-slices-cannot-link-their-parent-epic-tcw-resolves-downward-only`.
