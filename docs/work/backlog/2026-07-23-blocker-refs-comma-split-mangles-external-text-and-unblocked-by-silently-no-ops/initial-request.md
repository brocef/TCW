# Blocker refs: comma-split mangles external text and --unblocked-by silently no-ops

## Origin

Found during the 2026-07-23 backlog audit, while trying to clear a stale external
blocker off `2026-06-19-additional-capability-sidecars`. The removal reported
success and did nothing; `start --force` was used instead.

## Problem

Three defects compound into "external blockers are effectively unremovable, and
the CLI tells you they were removed."

### 1. `--unblocked-by` reports success when it matched nothing

`WorkStore.remove_blocker` (`tcw/store/base.py`) filters `blocked_by` and writes
only when the length changed — a no-match is a silent no-op. `_edit`
(`tcw/work/cli.py`) then prints `edited <slug>` unconditionally. Contrast
`--blocks` in the same function, which validates each ref and fails closed with
`no such work item: <ref>`.

### 2. The ref format the board prints is not the ref format the flag accepts

`unresolved_blockers` and the board render an external blocker as
`external: <text>`, but `remove_blocker` matches against the bare `<text>`
(`e.get("external") != ref`). Copy-pasting what the board shows therefore never
matches. This is what produced the audit's silent failure.

### 3. Comma-splitting mangles any external blocker containing a comma

`_split` (`tcw/work/cli.py:81`) comma-splits every blocker flag value, so an
external blocker with a comma in its prose is stored as several blockers — and
none of them are removable by the original string.

## Reproduction

Verified end-to-end in a throwaway node:

```
tcw work edit <slug> --blocked-by "waiting on vendor A, then legal signoff"
# → blocked_by: [{external: "waiting on vendor A"}, {external: "then legal signoff"}]

tcw work edit <slug> --unblocked-by "external: waiting on vendor A"
# → prints "edited <slug>"; state.yaml unchanged
```

## Desired outcome

- `--unblocked-by` fails closed on a ref that matches no blocker on the item,
  the way `--blocks` already does for unresolvable slugs.
- The ref accepted by `--blocked-by` / `--unblocked-by` round-trips with what
  `list` / `show` print. Either strip a leading `external:` prefix on input, or
  stop printing the prefix — pick one and make display and input agree.
- An external blocker's text survives a comma. Make the blocker flags repeatable
  (`--blocked-by` once per blocker, matching the existing `--tag` idiom) rather
  than comma-split, or otherwise stop splitting external prose.

## Notes

- Entirely core + CLI (`base.py` blocker helpers, `work/cli.py` flag parsing).
  No store-interface or filesystem-adapter change; the litmus test is not in
  play.
- Repeatable flags would be a small CLI-surface change — README, release notes,
  and the `tcw-work` skill's quick reference all need the new form.
- Regression tests: comma-bearing external blocker survives a round-trip;
  `--unblocked-by` with a non-matching ref exits non-zero; the string the board
  prints is accepted by `--unblocked-by`.
