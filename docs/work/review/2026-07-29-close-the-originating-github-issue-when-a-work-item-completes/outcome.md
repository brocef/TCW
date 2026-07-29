# Outcome: Close the originating GitHub issue when a work item completes

All seven plan tasks shipped. `python -m pytest` → **1095 passed** (156s);
`tcw validate` → OK; `tcw capabilities check` → OK.

**No code was written.** The request's central question was whether this change
finally justified a `source`/`external-ref` field on the work model, and whether
the trigger had to live in the CLI. Both answers turned out to be no, and the
diff under `tcw/` is empty (criterion 8, checked with `git diff --stat -- tcw/`,
not assumed).

## What shipped

### Task 1 — `docs/work/dod.yaml` — `065727e`

The five `DEFAULT_DOD` entries plus `originating GitHub issue answered and
closed, if the item came from one`.

The prompt cost nothing because the mechanism already existed:
`FsWorkStore.dod_checklist` (`tcw/store/fs.py:2012`) has always read this file
and fallen back to `DEFAULT_DOD`. It also satisfies harness parity for free —
`dod_checklist()` is declared on the abstract store (`tcw/store/base.py:983`), so
any adapter serves it, and `tcw work complete` prints the same checklist to
whoever runs it.

Generated from `DEFAULT_DOD` programmatically rather than retyped: the file
replaces the defaults rather than extending them, so a dropped entry deletes a
check from every completion here with no error and no failing test.

### Task 2 — `tcw-triage-issues` §8 — `32e0201`

Locate the issue (`tcw work path <slug>` → `## Origin`), then map resolution to
reply. Restates the exact-text approval rule rather than cross-referencing §6,
since a reader arriving at closeout months later has not read §6.

### Task 3 — `transitions.md` pointers — `32e0201`

In `complete` and in `discard`, deliberately **not** symmetric — see below.

### Task 4 — the ledger — `2d3c587`

New `work/customize-the-definition-of-done` (`cap-73460f`); corrected
`work/complete-a-work-item`; extended `plugin/triage-github-issues`.

### Tasks 5-7 — documentation — `f1ab7d9`

All four Documentation Sync entries fired.

## What the plan and spec got right, and where the evidence came from

Unlike the sibling item, nothing here disproved the spec. What the implementation
added was **evidence for claims the spec had only read off the source**:

- **The override is live and the fallback intact.** This repo prints six
  checklist items; a throwaway `tcw init` repo prints five.
- **A discard prints no checklist at all** — only the permanence warning. This
  was read out of `cli.py:810` at spec time and is now observed. It is the reason
  the two `transitions.md` pointers differ: three of the four resolutions get no
  prompt from the DoD, so the `discard` pointer is the only prompt they have.
- **`self.root / "dod.yaml"` resolves to `docs/work/dod.yaml`.** This was the
  spec's single open assumption, and running `complete` settled it.

## The undocumented feature

The spec found that `dod.yaml` appeared in **no** README, skill, doc, or
capability — a supported behavior discoverable only by reading `fs.py`. Worse,
`work/complete-a-work-item` positively asserted the opposite: "the same fixed
checklist on every item".

Documenting it was in scope rather than creep, because this item's entire design
rests on it. Depending on an undocumented feature while leaving it undocumented
is how the next person deletes it as dead configuration.

## What is **not** delivered

- **This is a prompt, not a guarantee.** The DoD is `[prompted]`, never
  `[gated]` (`transitions.md:70`). An agent can acknowledge the line without
  doing anything and nothing detects it. Enforcement would need `tcw` to make a
  network call at completion, which the spec ruled out — `tcw work complete` must
  not become able to fail because GitHub was unreachable. Recorded here so the
  release notes do not overclaim.
- **Three of four resolutions have no automatic prompt.** Covered only by
  `transitions.md`'s `discard` section and §8.
- **No back-fill.** Items completed before this change were not revisited.
- **Issues #9 and #8 remain open** (criterion 10, verified) — their work has not
  shipped, so this change correctly did not touch them. They are the first real
  test of §8, and it will not happen until those items complete.

## Notes

The first real exercise of this change is **this item's own completion**: it
came from a chat request rather than a GitHub issue, so §8's first branch — no
`## Origin` issue, nothing to do — is what should fire.
