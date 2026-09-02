# Refined outcome — accepted

## The decision

Accepted by the requester on 2026-09-02, in their words: *"I think it's good
enough, approved."*

The acceptance followed an adversarial multi review of the branch and two rounds
of rework answering it. It was not conditional on a further clean round.

## What changed after `outcome.md` was written

`outcome.md` describes the feature as first implemented. Everything below landed
after it, in response to the review, and is the accurate description of what
shipped.

### Defects the review found in the shipped feature

| # | Defect | Where |
| --- | --- | --- |
| 1 | `tombstone add` refused the backfill case it exists for — `get()` answers for `completed/` and `discarded/`, so on the machine an adopter backfills from it rejected the documented migration path with "it is a live work item … resolve the item instead" of an item already resolved | `record_tombstone` |
| 2 | A second `tombstone add` for the same slug silently replaced its record with an empty resolution and today's date, and reported success. No `tombstone rm` exists, so the only repair was the forbidden hand-edit | `_write_tombstone` |
| 3 | Resolving transitions were not serialized: check, write and commit are three steps with nothing holding them together, so two agents in one working tree could lose a graveyard entry — leaving an item resolved with no tombstone, which is the collision the feature exists to prevent, arriving by another route | `_effect_transition` |
| 4 | `tcw://W/completed/<slug>` returned before the tombstone was consulted, keeping the exact per-machine behaviour the bare spelling was fixed for | `resolve_qualified_work_ref` |
| 5 | `tombstone add` committed without publishing, so on a provisioned store the record never reached the clones it exists for | `record_tombstone` |
| 6 | No slug validation: an empty or path-shaped key could be written and committed permanently | `record_tombstone` |
| 7 | `--resolved` was validated but not normalized, so `20260601` was stored in a shape nothing else reads | `record_tombstone` |
| 8 | `tombstone()` promised tolerance for "every degraded shape"; an unreadable or non-UTF-8 graveyard raised out of `_unique_slug` and turned `tcw work new` into a traceback | `tombstone` |
| 9 | The viewer called a tombstone with no recorded resolution "completed work", wrong for a discarded item | `serve` |

All nine are fixed. Three false claims in prose were corrected alongside them:
the capability entry and release note said validation "reads only what is
committed" (it walks the working tree); `_commit_transition` said the guard
closed a concurrency hole it only narrows; and `_write_tombstone` presented
read-modify-write as the answer to concurrent completions, which it is not.

### The concurrency fix, since it is the largest

A `flock` keyed to the store path spans check, write and commit, and
`record_tombstone` takes the same lock. The lock file sits in the system temp
directory rather than the store: the graveyard is replaced atomically so a lock
held on it protects nothing once the replacement lands, and a lock file inside a
tracked store root would sit in `git status` forever. `flock` rather than a lock
directory because the kernel releases it on process death — a stale directory
lock would wedge every future resolution in the store, a worse failure than the
race it prevents. It degrades to no locking where `fcntl` is absent, which is
the behaviour every caller had before it existed.

Cross-machine concurrency is deliberately not covered. That case ends in a git
merge conflict on the graveyard, which is a plain YAML conflict a human settles —
as the spec intended.

The refusal message beside it was also rewritten. It described another agent's
in-flight record as a stray edit to "commit or discard", and a user following
that advice destroys that item's record while its folder has already moved. That
was the only path to data loss a person actually walks.

## Evidence

- Full suite green: **2230 passed**, run against the final tree.
- `tcw validate` exits 0 in this repository — spec criterion 9, and the reason
  the `complete` transition works here again.
- Every new test was confirmed to fail without its fix, by stashing the source
  and reading the failure text.

## Where the record must not overstate itself

One test does not prove what its first draft claimed.
`test_two_resolutions_racing_keep_both_records` goes red *with the lock removed*
on a git index collision, not on the lost graveyard entry — that needs a
narrower interleaving than two real transitions reliably produce. Its docstring
now says so. Read it as "unserialized concurrent resolution is broken and the
lock fixes it", not as a demonstration of the entry loss. The entry loss is
established by tracing, and independently by a second reviewer, not by a test.

## The multi review

Three reviewers, all of which produced real answers — checked, because an empty
run is indistinguishable from a clean one by exit code alone.

| Reviewer | Answered | Findings |
| --- | --- | --- |
| `adversarial-code-reviewer` | yes | 4 blocking, 3 significant, 2 reuse, 7 notes |
| `codex exec review` | yes — verdict line, 4 numbered findings, ~200s | 4 |
| `bllm review diff` | yes — 5.2 KB, explicit verdict | 0 |

Codex independently confirmed three of the agent's findings at the same lines
and contributed one the agent missed, which on checking was real in its
observation but not in its stated consequence (`load_yaml` coerces a falsey
document to `{}` before the guard sees it, so no data loss is reachable) and was
taken as a note.

`bllm` found nothing and affirmatively endorsed two things that turned out to be
defects, restating the code's own comments back as verification. **It should not
be counted as an independent clean review.**

Codex ran in a detached git worktree rather than the checkout, and left it
unmoved — recorded because a read-only Codex review has written commits to this
repository before.

## Deferred, with reasons

- **`tcw capabilities drift` has the identical defect.** `_shipped_but_missing`
  decides "did this ship?" from `get()`, so it reports drift for whoever
  completed the work and nothing in every other clone, failing silently. Filed
  as `docs/work/inbox/2026-09-02-capabilities-drift-goes-silent-in-a-clone-without-the-resolved-folders.md`.
  Not folded in: it changes what a different command reports, which is the same
  reason this item's spec non-goaled making `unresolved_blockers` precise.
- **The spec's Sweep is recorded as repo-wide and was not.** It found two
  negative results and missed the positive one above. Corrected in the changelog;
  `spec.md` is left as the historical record of what was believed at the time.
- **The originating GitHub issue, if any, stays open until the release carrying
  this is cut and pushed.** An issue closed before the fix ships tells the
  reporter it is fixed when they still cannot install it. This is a deliberate
  deferral of the `dod.yaml` entry asking for it at completion, not an oversight.

## Notes

The review paid for itself twice over, and the two highest-value findings were
ones no test could have caught: a command that refused the exact situation its
own release notes tell users to run it in, and a concurrency window reachable
only by tracing three steps that no single test exercises together. A green
suite was not a substitute for it.
