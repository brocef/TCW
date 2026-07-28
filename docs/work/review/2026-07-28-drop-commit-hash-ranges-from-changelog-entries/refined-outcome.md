# Refined outcome: Drop commit hash ranges from changelog entries

**Accepted.** The user verified the work across two passes and approved closeout
on 2026-07-28.

## The decision

Verification ran twice. The first pass was accepted on its acceptance criteria
but rejected two of the spec's Non-goals; `rework.md` records that override and
the second pass delivered it. The second review found nothing outstanding, and
the user approved completion.

Nothing was deferred into a follow-up item. The work is closed as `done`.

## Evidence

| Check | Result |
| --- | --- |
| Acceptance criteria | All 9 met — see `outcome.md` for the per-criterion table and the two criteria that were themselves defective. |
| Test suite | `python -m pytest -q` → **1062 passed**, run at the end of both passes. |
| Node validation | `tcw validate` → `validate OK`. |
| Released history | `git diff --stat` over the item's full range lists no `docs/changelogs/v*.md`. The one boundary that held through the scope change. |
| Local LLM review | Two rounds of `bllm-review-many` (`qwen25`, `gemma4`), one per pass. No finding survived triage; the dismissals and their reasons are in `outcome.md`. |
| Capability reconciliation | `tcw capabilities list` has no entry covering changelog authoring, the `documentation-sync` skill, or release documentation. The spec's no-delta finding is confirmed against the ledger at closeout, not just at spec time. **No capability changed status and none was added.** |

## What shipped, in one paragraph

No shipped instruction asks an agent to record, compute, or extend a commit hash
range for a changelog entry. The `## Changelog Entry Format` section is gone from
`documentation-sync`; the version-fold procedure lost the step that repaired
ranges it had itself invalidated, and its Common Mistakes row; the two sentences
that used the requirement as half the documentation gate's rationale now argue
from shape drift alone, with the gate's position and force intact;
`scripts/cut_version.py` and TCW's own `AGENTS.md` no longer promise ranges; the
pending changelog carries no hash attributions at all; and
`docs/migration-guide-0.15.X-to-0.16.0.md` tells adopting projects that nothing
is required of them.

## Closeout choices

| Question | Decision |
| --- | --- |
| **Version** | **No bump.** The changes stay in `docs/{changelogs,release-notes}/upcoming.md` and ship with whatever version is cut next. |
| **Route** | **Direct to `main`.** No pull request, no branch, no worktree — the item's 17 commits are already on `main`. |
| **Follow-up items** | **None filed.** |

### One consequence to be aware of

`docs/migration-guide-0.15.X-to-0.16.0.md` is named for a version that has not
been cut. With no bump at closeout, that filename is a **prediction** that the
next release will be a minor one — which is consistent with how
`upcoming.md` already works (it accumulates content for a version whose number is
not yet known), and with the user's stated choice of a minor bump when one
happens.

If the next cut turns out to be a patch, the guide must be renamed as part of
that cut. `scripts/cut_version.py` rotates `upcoming.md` files but knows nothing
about migration guides, so it will not catch this.

## Considered and deliberately not done

- **A guard test asserting `docs/changelogs/upcoming.md` carries no commit-hash
  attribution.** Raised by both review rounds. Rejected on the item's own
  finding: the requirement was instruction-only, and no code emitted, validated,
  or read these hashes. Adding a validator would reintroduce as machinery the
  coupling this item removed as prose. Recorded here rather than filed, so a
  future reader sees it was weighed.
- **Rewriting released `docs/changelogs/v*.md`.** Out of scope throughout, and
  the one Non-goal the verification gate left standing. Those files describe
  versions that already shipped; their hashes were accurate when written.
- **A migration step for downstream `<changes>` wrappers.** The wrappers are
  inert Markdown that no command has ever read. The guide says so and offers
  optional cleanup instead of a required procedure.

## Notes

- The most transferable output of this item is not the change but the defect it
  exposed in its own acceptance criteria: **a criterion that greps for a
  keyword cannot be run over the document that announces the keyword's removal.**
  AC1 and AC3 both matched their own descriptions of the work satisfying them.
  Both were rewritten — AC1 scoped to instruction surfaces, AC3 to shape rather
  than vocabulary. `outcome.md` carries the full sequence.
- No post-mortem was offered. Verification surfaced no serious unforeseen
  problem: the criteria defects were found and corrected inside the lifecycle,
  and the scope change was a user decision at the gate rather than a failure.
