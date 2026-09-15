# Refined outcome: accepted

The user accepted on 2026-07-30, after reviewing the assessment below.

## Evidence

All eight of the spec's acceptance criteria were checked against the finished
tree, not recalled:

| # | Criterion | Evidence |
|---|---|---|
| 1 | Both folders gitignored | `git check-ignore -q` exits 0 for each |
| 2 | Out of the index | `git ls-files docs/work/completed docs/work/discarded` → 0 lines |
| 3 | Still on disk and listable | 74 completed + 7 discarded folders present; `tcw work list --all` → 94 lines, identical before and after |
| 4 | New test for an ignored destination | `test_a_transition_into_an_ignored_destination_untracks_instead_of_moving` passes; it failed before `063ba02` with the item's `initial-request.md`, `state.yaml`, and `.gitkeep` still tracked |
| 5 | Existing transition tests unchanged | all five `test_every_transition_commits_its_own_move` cases pass; their repos ignore nothing, so they cover the untouched path |
| 6 | Suite and validate | `pytest -q` → 1097 passed; `tcw validate` → `validate OK`, exit 0; `tcw capabilities check` → `capabilities OK` |
| 7 | Private name gone from tracked files | `git ls-files -z \| xargs -0 grep -il` → 0 files |
| 8 | Capability flipped | `work/keep-resolved-work-out-of-git` reads `Supported` |

## The decision

Accepted as delivered. Nothing was sent back, and no criterion was waived.

Two corrections `implement` made to its own plan were reviewed and stand, both
recorded in `outcome.md`: the plan's test sketch missed that `init`'s `.gitkeep`
stays tracked across a new `.gitignore` entry, and the scrub falsified a
"quoted text is the report as filed" note in each of the two backlog items it
touched.

The `git_mv` change was reviewed against the prime directive: it is git plumbing
inside an FS-adapter private helper, no store-interface method changed, and no
model concept moved. It passes the litmus test.

## Closeout choices

- **No post-mortem.** Nothing unforeseen or serious surfaced. The one real
  discovery — that `git mv` ignores `.gitignore` for its destination — was found
  during `spec`, before any code was written, and is recorded there.
- **Version cut: offered after `complete`**, per `stage-verify.md` step 9. The
  change is user-visible, so a patch bump is defensible; the call is the user's
  and is made after this item closes.

## Deferred follow-ups

- **The private name still appears on disk** in roughly eight files under
  `docs/work/completed/`. Out of scope by the requester's explicit choice: those
  files left the repository via this item's own change, so rewriting them would
  be churn with no effect on what ships. Not tracked as a work item.
- **Past commits still carry the resolved-work folders.** The requester chose
  untracking over a history rewrite: purging them would change every SHA, need a
  force-push, and break existing clones and the release tags. If that decision
  is ever revisited it is a fresh item, not a follow-up to this one.

## Notes

This item's own completion is the end-to-end proof — the first `complete` into
the newly ignored folder in this repo. What to expect: the transition commit
records *deletions* under `docs/work/review/<slug>` rather than a rename into
`completed/`, `git status --short` is clean afterwards, and the item is readable
on disk at `docs/work/completed/<slug>`. Confirmed below the fold, in the
session that ran it.
