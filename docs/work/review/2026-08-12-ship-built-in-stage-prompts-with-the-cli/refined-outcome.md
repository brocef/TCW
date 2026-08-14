# Refined outcome — Ship built-in stage prompts with the CLI

**Accepted** by the requester on 2026-08-14, with one change made at this stage.

## What was checked, and by whom

The coordinating session re-ran everything rather than accepting the
implementation's report:

- **1561 tests passed.** This item adds 51 and edits none of C5's or C3's.
- **The eleven lifecycle baselines are byte-unmodified** across both children —
  `git diff` over `tests/fixtures/` is empty. Task 5 was the one task that could
  have moved one, and it did not.
- `tcw capabilities check` → `capabilities OK`; `tcw capabilities drift` → `no
  capability drift`; `tcw validate` → `validate OK`.
- **The headline feature was exercised by hand** on this repo, whose
  `tcw-config.yaml` has no `work.lifecycle` key at all:
  `tcw work stage implement 2026-08-12-ship-built-in-stage-prompts-with-the-cli`
  and `tcw work stage spec 2026-08-11-accept-comma-separated-tags-on-tcw-work-new`
  each exit 0 and print the shipped instructions. Before this item the same
  command exited 0 and printed nothing. That is the epic's **checkpoint 4**.
- The Codex-user contract was spot-checked in the output: the `implement` prompt
  says "the project's agent guide (`AGENTS.md` or `CLAUDE.md`)" and "check any
  capability change against the standing ledger" — obligations stated without
  naming a plugin skill, which is the whole point of the item.

## Criteria

All 13 met, including criterion 13 — the epic's one deliberate back-compat
break. `prompt: []` is refused in both spellings, `pre: []` is asserted
unaffected so the check cannot be generalized later, and resolution still
returns the built-in because the parser's problem list is advisory. The break is
pinned to `tests/fixtures/lifecycle_baseline/stage_empty.config.yaml`, a config
that demonstrably predates it.

## Decision taken at this stage

**The stage-prompt line ceiling was raised from 40 to 50** (`ab86012`).

Four of the six prompts landed at exactly 40, so the ceiling had no margin. C7
has to move clauses across the CLI/skill seam and could not have accepted one
without first removing another — which would have let the ceiling decide the
seam instead of the design. The guard is the point rather than the number: at 50
it still refuses a prompt that grows back into the stage document it was
condensed from. `tests/test_shipped_prompts.py` and the changelog entry both
carry the new figure; the spec's §6 and criterion 8 say 40 and are **superseded
by this decision**, not by a silent edit.

## What was accepted without a test behind it

- **The six prompts are asserted to exist, to be bounded, and to contain no
  dangling skill reference — not to be good instructions.** No test can assert
  that. Accepted on a reading of the rendered output.
- **sdist parity remains untested**, per the spec's Risks. `package-data` reaches
  sdists too and the `tcw.serve` precedent has shipped that way for several
  releases; the wheel check is the one that earns its runtime.

## Carried forward

- **`work/configure-the-work-lifecycle` now contains a contradiction.** Its line
  6 reads "Everything I configured before this still works and still prints the
  same thing. A stage id with a plain list under it means what it always meant."
  After task 5 a bare `stages.<id>: []` is a `tcw validate` problem. The sentence
  survives on a narrow reading — resolution genuinely is unchanged, so such a
  node still *runs* identically and only `validate` complains — and the
  implementation surfaced it rather than overwriting it, which is the correct
  behaviour for a semantic contradiction. **It belongs to C7's documentation
  consolidation or to C8's audit.**
- **The 40→50 raise gives C7 headroom it should spend deliberately.** The reason
  for the raise was to stop the ceiling from deciding the CLI/skill seam; it is
  not an invitation to move the stage documents wholesale into the CLI.
