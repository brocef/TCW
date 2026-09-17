# Outcome: commands-pause-work

Second pass, following `rework.md`. No file under `tcw/` changed —
`git diff --stat origin/main...HEAD -- tcw/` is empty, which was the request's
hard constraint and is checked by nothing else.

## What the rework changed

| | Before | After |
| --- | --- | --- |
| Handoff contents | A five-item list the spec fixed in advance | The pausing agent's judgment: "whatever context an agent would need to resume the work you were doing at the time of the pause" |
| File name | `<stage-id>.handoff.md` | `handoff-<UTC timestamp>.md` |
| Skill length | 136 lines | **79** |

Two rules **disappeared** rather than being restated, which is the point of the
rename. The `inbox` carve-out existed because that stage has no item folder to
name a file after; with no stage in the name there is nothing to carve out. The
"remove any handoff already present" rule existed because a second pause in the
same stage would overwrite the first; a timestamp collides with nothing. Several
handoffs may now coexist, and the resume rule absorbs it: read what you find,
newest last, delete what you read.

Two requirements survived the cut, because they are facts about the system rather
than advice about note-taking: **name the branch** (nothing else records it for a
non-worktree item) and **no `tcw://` links** (`tcw validate` scans every `*.md`
under the work root and gates `complete` here, so a dangling one refuses the
completion).

Commits: `684f1b7` spec, `0e0b24c` plan, `2d0c305` the skill and its cascade.

## Cascade

Renaming reached five files beyond the skill, all updated in `2d0c305`:
`skills/work/SKILL.md`'s resume line, `skills/commands-verify-work/SKILL.md`,
the capability's `description.md`, and both `upcoming.md` docs. A repo-wide grep
for `<stage-id>.handoff` and `implement.handoff` outside `docs/work/` returns
nothing.

## First pass, retained

Everything below shipped in the first pass and was not reopened by the rework.

| Task | Commit | What |
| --- | --- | --- |
| 1 | `a12092a` | Taxonomy Feature `commands-pause-work-skill` |
| 2 | `0d26ed3` | Capability `skills/commands-pause-work`, seeded `Missing`, with `Feature`, `Subject` and `Planning doc`; the item's `capabilities.yaml` |
| 3 | `2c319d0` | The skill, plus the verdict row, Codex manifest and eval exclusion that must land with it |
| 4 | `5d64a1f` | The resume-side read: `skills/work/SKILL.md` and a pointer from `commands-drive-work-to-completion` |
| 5 | `5527bcb` | The two prose enumerations |
| 7 | `ed81615` | Release note and changelog entries, and two counts this change makes stale |
| — | `b7cf520`, `7da86f5` | Fixes from implementation and from verification |

The procedure itself is unchanged: coherent resting point → ask whether to commit
and push, no answer is a yes → commit and push → write the handoff → commit and
push it as a second push → report → fall silent. No transition runs.

## Test result

`python -m pytest` — **3609 passed, 2 skipped** (529s), re-run after the rework.
`tcw validate` exits 0.

Evidence from the first pass that the rework does not invalidate:

- The three registration tests were **mutation-checked**: reverting each of
  `skills/README.md`, `.codex-plugin/plugin.json` and `evals/coverage.py` in turn
  made the expected test fail. An independent verifier re-did the
  `skills/README.md` one and confirmed it, noting that **two** tests fail on that
  revert rather than one, and that this document's earlier quotation of the
  failure message was a paraphrase presented as command output. Corrected here.
- **Handoff survival was proven, not asserted**: a scratch item carried an
  unregistered handoff through `backlog → active → discarded` with content intact,
  and `tcw validate` / `work show` / `work list` reported it no differently. The
  file name changed in the rework; nothing about that result depends on the name.

## What verification found, and what it cost

An independent verifier returned 15 of 16 criteria met and four defects. All were
fixed in `7da86f5` before the requester's rework arrived:

1. **Criterion 7's resume-and-delete statement was missing from the skill body.**
   The behaviour existed in `skills/work/SKILL.md`, but the pause skill never told
   its reader the file would be deleted — so a pausing agent could not say what
   would happen to the document it had just written.
2. **`when_to_use` named `tcw work drop` for abandoning**, and `drop` refuses any
   item not in `backlog` (`tcw/store/base.py:3556`). A pause during `implement` is
   an `active` item, so the reader most likely to follow that clause would hit an
   error. **This was the third instance of one shape**: the commit that fixed
   `discard`→`drop` introduced it, and this document had already recorded
   discovering that `drop` cannot reach an active item without revisiting the line
   it had just written. The root fix was to delete the command name from the
   negative clause — naming a command in a "not for this" aside carries no value
   and is what kept biting.
3. **`commands-verify-work` never routed through "Finding your place"**, so a
   `verify`-stage pause resumed with the skill named for that stage would leave the
   handoff unread — while the release note promised it would be read and deleted.
4. **This document described the probe residue inaccurately**, and
   `commands-drive-work-to-completion` overstated the router's ordering.

## What the plan and spec got wrong

Five things, all found by running the work rather than reading it.

1. **The plan named a command that does not exist.** Task 6 said
   `tcw work discard`; the CLI verb is `drop`, and `discard` is only the transition
   id. See defect 2 above for where that error went next.
2. **The plan was wrong that no test constrains `skills/work/SKILL.md`'s length.**
   `test_the_router_stays_within_its_line_budget` caps the body at 60 and it was at
   59. This was a correction of a correction: an earlier draft cited
   `ROUTER_LINE_CEILING`, which really does apply only to `stage-<id>.md`, and I
   replaced a right-for-the-wrong-reason claim with a wrong one. The budget's rule
   is "extract, never grow", so the resume sentence was folded into an existing
   line; the body is still 59 after the rework reworded it.
3. **`tcw work drop` cannot reach an active item** — only `backlog`. Task 6's
   cleanup assumed otherwise, so the probe had to be completed with
   `--resolution wontfix`, which is what gave the survival claim a second
   transition to survive.
4. **A JSON round-trip reformats more than it edits.** Rewriting
   `.codex-plugin/plugin.json` through `json.dumps` expanded an unrelated inline
   array; reverted, so the committed diff is one line.
5. **The spec over-specified the deliverable, and no gate could catch that.**
   Every acceptance criterion passed while the skill was twice the size it needed
   to be, because the criteria asked whether things were *stated*, never whether
   stating them was worth the reader's time. A criterion that counts contents
   cannot notice that the contents should be the agent's to choose.

## Residue

The scratch probe folder sits in `docs/work/discarded/`, which `.gitignore:29`
makes **untracked** — it is local to this machine and does not travel with the
branch. The only thing that ships is one line in `docs/work/graveyard.yaml`
recording the slug as `wontfix`.

## Notes

- The follow-up named in the spec — registering `handoff` in `WORK_SIDECARS` so
  `tcw` can see, validate and display it — is still unfiled, on the reasoning that
  it is better judged after the convention has been used. It is now slightly more
  attractive than before: a glob (`handoff-*.md`) is a weaker thing for the store
  to be unaware of than a fixed name was.
