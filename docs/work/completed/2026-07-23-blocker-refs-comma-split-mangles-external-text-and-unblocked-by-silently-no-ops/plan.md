# Plan — Blocker refs fix

Small, single-session change. Three phases; 1 and 2 touch different files and can
be done in either order, but 3 depends on both. No stage documents — the plan
fits in one read.

## Phase 1 — store core (`tcw/store/base.py`)

1. Add `WorkStore._normalize_ref(ref: str) -> str` (staticmethod, next to
   `_same_entry`): strip surrounding whitespace, then strip one leading
   `external:` prefix plus any whitespace after it, then strip again.
   Docstring states why: display prints `external: <text>`, so input must accept
   it back.
2. `_entry_for` — normalize **before** the `self.get(ref)` slug probe:
   `ref = self._normalize_ref(ref)`. A slug can never begin with `external:`
   (`slugify` → `[a-z0-9-]`), so the probe is unaffected.
3. `remove_blocker` — normalize the ref, match against it, and raise
   `ValueError(f"no such blocker on {slug}: {ref}")` (using the *original* ref in
   the message so the user sees what they typed) when nothing was removed.
   `add_blocker` stays idempotent — deliberate asymmetry, note it in the
   docstring.

Touch points: `tcw/store/base.py` ~L835 (`_entry_for`), ~L839 (`_same_entry`
neighbourhood, for the new helper), ~L872 (`remove_blocker`).

`tcw/store/fs.py:2217,2324` already call `_entry_for`, so `create_work` /
`update_work` / the web app's `blockers` field inherit normalization with no edit.

## Phase 2 — CLI flags (`tcw/work/cli.py`)

1. `tcw work new`: `--blocked-by` → `action="append"`, help text
   `"a slug or external text that blocks it (repeatable)"` (~L686).
2. `tcw work edit`: same for `--blocked-by` (~L721) and `--unblocked-by` (~L723),
   help `"a blocker to remove (repeatable; accepts the 'external: …' form shown by
   show/list)"`.
3. Replace the three `_split(args.blocked_by)` / `_split(args.unblocked_by)` uses
   with the bare list: `args.blocked_by or []` at L208 (`blockers=` kwarg, keep the
   `or None`), L496, L500.
4. Leave `--blocks` and `_split` itself alone — `--blocks` takes slugs, which
   cannot contain a comma.
5. No new error handling in `_edit`: it already wraps store calls in `_ERRORS`, so
   the `ValueError` from phase 1 prints and exits non-zero.

Verify point 5 by reading the `_edit` try/except extent before relying on it — if
the blocker loops sit outside the `try`, move them inside rather than adding a
second handler.

## Phase 3 — tests (`tests/test_work.py`)

Store-level, near the existing blocker tests (~L427-441):

1. Update `test_...` at L433 — `remove_blocker` on an absent ref now raises
   `ValueError`; assert the message names the slug and the ref.
   (Local-review pickup: assert at the store level, not only through the CLI.)
2. `external:`-prefixed ref and bare ref produce the same entry; either removes it;
   adding both is idempotent.
3. A comma-bearing external blocker round-trips as **one** entry.

CLI-level, in the CLI test area of the same file:

4. `--blocked-by` twice records two blockers; `--unblocked-by` twice removes two.
5. `--unblocked-by` with a non-matching ref exits non-zero and leaves the item's
   `blocked_by` unchanged.
6. The exact `blocked_by:` string printed by `tcw work show` is accepted by
   `--unblocked-by`.

## Phase 4 — documentation sync

- `README.md:492` — `--blocked-by "other-slug,external:JIRA-123"` becomes
  `--blocked-by other-slug --blocked-by "external: JIRA-123"`.
- `README.md:519,521` — note the flags are repeatable.
- `docs/changelogs/upcoming.md` — Fixed (`--unblocked-by` silent no-op; prefix
  round-trip) and Changed (repeatable flags; comma no longer splits).
- `docs/release-notes/upcoming.md` — plain-language version, including the
  breaking comma-form change.
- `skills/tcw-work/SKILL.md` — the quick reference has no blocker row today; add
  none. No change expected.

Run the `skill-cefailures:documentation-sync` skill before reporting complete.

## Verification

```
python -m pytest tests/test_work.py -q
python -m pytest -q
```

Plus the manual reproduction from `initial-request.md` in a throwaway node:
record a comma-bearing external blocker, copy the string `show` prints, remove it
with `--unblocked-by`, and confirm a bogus ref exits non-zero.

## Lifecycle

`tcw work start` before phase 1's first edit, committed on its own after this
plan is checkpointed.
