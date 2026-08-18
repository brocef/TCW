# Refined outcome — Repoint the work skill and docs at the CLI

**Accepted** by the requester on 2026-08-18, with no rework.

## What was checked, and by whom

The coordinating session ran every check itself rather than accepting a report —
which mattered here more than usual, because C7 was implemented across three
sessions and two of the three implementing agents died on session limits
mid-task. Each handover recovered from the tree, not from a handoff document.

- **1580 tests pass.** No existing test was edited except the two parity
  assertions the plan named.
- **`skills/tcw-work/references/stage-inbox.md` is byte-identical** —
  `git diff b2f65de~1..HEAD` over that path is empty. Criterion 1's exemption
  clause.
- **No line outside `README.md:605-735` moved** — every hunk header in
  `git diff -U0` falls between `:636` and `:719`.
- **`hooks.md` is 92 lines** (159 before, ceiling 95) with all four judgment
  anchors and all three role-table rows present.
- **`SKILL.md`'s body is exactly 60 of 60**, `tcw work lifecycle --stage` absent,
  `tcw work stage` present, `Runs in` gone.
- `tcw capabilities check` → `capabilities OK`; `drift` → `no capability drift`;
  `tcw validate` → `validate OK`.

## Criteria

All 14 met. Two numeric tensions the plan flagged resolved as it predicted: the
self-review block fit in 8 lines rather than needing the spec's looser 10, so
`spec.md` landed at exactly its 48-line cap and **the escalation never fired** —
no existing prompt content was compressed to make room. And five of six routers
landed at 22–30 lines, well under the ceiling, which is why the requester had
already amended constraint 1's 40–50 range to a ceiling with no floor.

## Decisions taken at this stage

None. The two decisions this item needed — the router ceiling and the ledger
linkage fixes being C7's rather than C8's — were both taken at the `spec` stage
and are recorded there (`fb9e629`).

## What was accepted without a test behind it

Stated plainly, because these are the item's real risks and no criterion covers
either:

- **A faithful paraphrase inside 40 lines.** Criterion 2 catches a sentence
  copied from a prompt into its router; nothing catches a router that restates
  its prompt in different words, and the epic's own Verification section already
  conceded that a test "cannot assert the router's summary is faithful". C7 wrote
  both sides of the seam in one sitting, which makes this *more* likely, not
  less. The 40-line ceiling is the backstop — a router paraphrasing its whole
  prompt would not fit — but one paraphrased paragraph inside budget would
  survive. Accepted on that basis.
- **Whether the rewritten `README.md:605-735` states each of its four facts
  exactly once** (criterion 10). "In exactly one paragraph" is a reading, not a
  grep.

## Carried forward to C8

- **`hooks.md`'s "configured-but-missing skill" note.** Harness-neutral operating
  advice a Codex user never sees, which would be better said by
  `tcw work lifecycle` beside a reported `skill:` binding — but that is a CLI
  behaviour change with a capability delta, and C7 was explicitly not touching
  `tcw/` outside the prompts.
- **`README.md`'s heading at `:605` has no closing boundary.** Everything from
  `:737` to `:1017` — transition commits, the Definition of Done, the whole
  command listing, the board, the JSON projection, descendants — renders inside
  "Binding your own skills and commands to the lifecycle", because the next
  `###` is at `:1102`. Predates the epic.
- **`read_artifact`'s `p.is_file()`** (`tcw/store/fs.py:3478`) still disagrees
  with the canonical presence rule (`fs.py:2217-2221`), per C5's refined outcome.

## Note on the `## Exit` removal

It is one-directional. Arguing "how does this stage end well" back into a router
now means arguing against a test. That is intended, and it is recorded in the
outcome and here so the argument is available rather than rediscovered.
