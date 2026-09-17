# Outcome — Stop offering a version cut after every completed work item

All eight plan tasks are done in commit `4cfdcaab`, except one deliberately
deferred step named below. The version-cut machinery is intact; only the
volunteering is gone.

## What changed

**The offer, deleted.** `tcw/work/prompts/verify.md` step 9; item 5 of
`skills/work/references/lifecycle/stage-verify.md` (the option menu); the
`After complete` row of `skills/documentation-sync/SKILL.md`, whose lifecycle
count drops from three points to two.

**The Definition of Done, shortened.** `DEFAULT_DOD` in `tcw/store/base.py` is
four items. The same five strings were copied into
`web/client/src/ui/content-views.tsx` (the completion dialog's fallback),
`tests/test_serve_write.py`, `docs/guide/work.md` twice,
`skills/work/references/transitions.md`,
`skills/configure/references/work.md`, and this repo's `docs/work/dod.yaml`;
all now read four. The comment beneath `DEFAULT_DOD` about tuple order shifting
`tcw work list` was checked before editing and belongs to `WORK_ARTIFACTS`
below it, so no display changed.

**The procedure, rewritten not deleted.**
`tcw/work/procedures/documentation-sync.md`'s `## When to offer version and
changelog options` is now `## When the user asks to cut a version`. Gone: the
four-option menu and every instruction to present it. Kept: the
`unpushed-version.sh` gate with unchanged exit codes, the judgment against
folding work too large for the version it would join, the absolute bar on
rewriting a published tag, and the deferral to the project's own version-cut
process ahead of the manual ritual. It now states explicitly that changelog
upkeep belongs to the end-of-`implement` documentation gate and never waited on
a version cut — which is what the deleted "keep the current version and update
the changelogs" option had been standing in for.

**`tcw work docs` kept, its rationale rewritten.** Both `tcw/work/cli.py` and
`skills/work/references/commands.md` justified the verb *solely* by the third,
non-stage invocation point this item removes. Trimming that to "two points,
both stages" would have left the next reader with a verb that reads as
unnecessary, so the justification was rewritten around what actually uses it:
the `documentation-sync` skill asks it before any stage prompt resolves, and
the web app reads the same answer.

**Ledger reconciled.** Four `changed:` records, recorded in the item's
`capabilities.yaml` and edited: `work/customize-the-definition-of-done`,
`work/read-the-documentation-gate-for-a-change`, `skills/documentation-sync`,
`skills/extras-autonomous-work`. `tcw capabilities check` → `capabilities OK`.

**Documentation.** `docs/release-notes/upcoming.md` and
`docs/changelogs/upcoming.md` both carry entries. Per the requester's explicit
decision, the release note does **not** mention that projects whose own
`dod.yaml` restates the five defaults keep the old behavior.

## Judgment calls made during implementation

1. **`unattended-work.md`'s "Version choice" row was kept, not deleted.** The
   plan said to delete it but to preserve the `upcoming.md` accumulation
   instruction if it appeared nowhere else, moving it into a neighbouring
   documentation row. Checked: `upcoming.md` appears **only** in that row, and
   the table has no documentation row to move it into. An unattended run also
   still needs telling not to cut a version, since there is no user present to
   ask. The row was therefore reworded to `Version cut` — "not yours to make,
   nobody is present to ask" — rather than removed.

## Verification

| Check | Result |
| --- | --- |
| Acceptance criterion 1 (offer-pattern grep) | **Clean.** No matches. |
| Acceptance criterion 2 ("version cut" grep) | **Passes in substance.** The five matches are all in `skills/documentation-sync/` (the kept how-to) and the rewritten procedure body. None in `prompts/`, `lifecycle/` or the guide, which is what the criterion required. See the wording note below. |
| Acceptance criterion 3 (`version offered` grep) | **Clean.** No matches. |
| Criterion 4 — `DEFAULT_DOD` is four items | **Passes.** Prints `('tests pass', 'docs synced', 'capabilities reconciled', 'reviewed')`. |
| Criterion 6 — verify prompt ends at step 8 | **Passes in substance.** Step 8 (the post-mortem offer) is last. The criterion's literal "contains no occurrence of 'version'" cannot hold here: the two remaining matches are this item's own slug echoed into the gate header and footer. |
| Criterion 7 — the cut still works when asked | **Passes.** `cut-version.md`, `scripts/cut_version.py` and `unpushed-version.sh` all present; `unpushed-version.sh` still exits 1 with `STATUS: NOT-FOLDABLE` against the published `v2.3.0`. |
| Criterion 8 — the suite | **Blocked by the environment, not by this change.** See below. |
| Criterion 9 — the web dialog | Read, not run. The fallback list is four entries. `pnpm prettify:check` not run. |

### Two criteria whose wording is imprecise, not two failures

Criterion 2 says the surviving matches are "the renamed procedure heading"; the
heading is "When the user asks to cut a version" and does not contain the string
"version cut" — the surviving matches are in that **section's body**. Criterion
6 asks for no occurrence of "version" in the prompt, which no item whose slug
contains "version" could ever satisfy. Both substantive checks pass; the spec's
phrasing was written before the replacement text existed.

### The environment blocks the suite, and one step of Task 1

**The editable install points at a worktree, not this checkout:**
`.worktrees/2026-09-16-make-claim-and-release-assert-ownership-without-moving-a-ticket`.
That worktree's item is still active, and the requester chose to leave the
install alone rather than re-point it mid-flight.

Consequence: the `tcw` console script runs the worktree's code, while
`python -m tcw.cli` from this checkout runs the edited code. Any test that
shells out to `tcw` therefore tests the wrong tree.

- **Suite result:** `1190 passed, 1 failed`.
- **The one failure** is `tests/test_procedure_verb.py::test_an_unconfigured_node_prints_every_default`.
  It shells out to `tcw` (worktree, stale procedure text) and compares against
  `REPO/tcw/work/procedures/<id>.md` (this checkout, edited text), so the two
  disagree on exactly the lines this item edited.
- **Proven, not assumed:** re-running that test's own assertion with the
  checkout's code serving the procedures gives **all 10 procedures matching**.
  The failure is the install pin, and would not occur in CI, which installs the
  checkout.

**Deferred: the prompt-fixture re-baseline.**
`tests/fixtures/prompt_fallback/unconfigured.json` embeds the `verify` prompt
verbatim and is **unchanged** in this commit. It must be re-captured so only the
`verify` entry moves, and both `capture.py` and `test_prompt_fallback.py` shell
out to `tcw` — so a capture taken now would record the worktree's text and
silently re-baseline the fixture to the wrong thing. A control run confirmed
`capture.py` currently reproduces the existing baseline byte-for-byte, i.e. it
is reading the worktree.

**This item cannot pass verification until that is done.** It needs
`pip install -e /Users/brian/Projects/TCW --no-deps`, then: re-capture, assert
only the `verify` entry differs, add a paragraph to `capture.py`'s docstring
naming this re-capture and its reason as the three previous ones did, and run
bare `pytest` from the repo root.

## Notes

The lifecycle was driven by hand from the point Task 1 began editing `tcw/`,
per this repo's agent guide. `tcw work start` was the last CLI transition; this
file, `capabilities.yaml`, and any subsequent status move are hand-maintained.

**Follow-up, not done here.** The backlog item
`2026-08-18-serve-version-cut-instructions-from-tcw-config-yaml-instead-of-the-agent-guide`
contains prose referring to "the completion options" that no longer exist. Its
premise is strengthened by this change, not invalidated — it serves *how* a
project cuts a version, which matters more now that cuts are only ever
user-initiated. Its wording needs a touch; it was deliberately not edited here.
