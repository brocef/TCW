# Refined outcome — Publish provisioned-store writes to their remote

**Accepted**, after an independent adversarial review that found three real
defects the suite and my own verification pass had both missed.

## The decision

The initiative's third and last child. A cloud session could already reach a
declared store; now it can keep what it does with it. All eleven criteria hold,
walked from a bare shell against a real two-repository fixture.

## Evidence

| # | Criterion | How it was checked |
| - | --------- | ------------------ |
| 1 | a transition is visible to a fresh provisioning | 3 transitions parametrized; by hand, a fresh `git clone` showed the item in `active/` |
| 2 | nothing moves until the store is up to date | the refresh observes whether the item has already moved |
| 3 | a refused refresh leaves the item untouched, and says why | same status, same folder, same HEAD; `git fetch failed: fatal: … does not appear to be a git repository` |
| 4 | a failed publish reports what landed, exits non-zero, rolls nothing back | read cold against a read-only remote |
| 5 | divergence is refused, never merged | asserts no merge commit exists, and that the message names the way out |
| 6 | only a publishing store touches the network | 3 rules × 3 transitions, adapter Git calls asserted **empty** |
| 7 | a non-publishing store is unchanged | no test outside the new module rewritten |
| 8 | a push contacts only the declared remote | by hand: "nothing was contacted", both URLs named |
| 9 | the off switch works, non-boolean reads as default | ✓ |
| 10 | git invoked with stdin closed | `tests/test_subprocess_stdin.py`, unchanged |
| 11 | reproducible from a bare shell | every row above |

**Suite: 2163 passed**, no failures, no skips. `tests/test_store_publication.py`
holds 35 cases — 31 before the review, 4 added by it.

**The abstraction seam holds.** `publishes`, `refresh()` and `publish()` name no
remote, ref, branch, clone directory, or ladder rule. The one thing the
filesystem contributes — which ladder rule resolved the store — is a private
attribute the adapter reads, which is where the litmus test puts it.

## What the review changed

Details in `outcome.md`. In short: `TransitionCommitError` had its meaning
widened without auditing its handlers, so `tcw serve` showed a green success
while a cloud session's work sat unpublished; a tag-pinned declaration failed at
step 4 instead of step 1, moving and committing the item before refusing, every
time; and a rejected push wedged the store permanently behind a message from git
rather than from TCW.

Two of Codex's five claims were wrong or benign and were rejected with reasons
rather than actioned.

## Known limit, recorded rather than fixed

**Publication happens at transition boundaries.** Ordinary writes stage without
committing — TCW's existing rule, not a new one — so artifacts written into an
item's folder are carried by the next transition's commit and pushed with it. A
session that writes and never transitions leaves that work committed nowhere and
pushed nowhere.

This is in scope as specified: the request asked for "pull before and push after
transitions", and that is what shipped. It is recorded here and in the capability
body because the initiative's *goal* is broader than its mechanism, and a reader
who knows only the goal would assume otherwise.

## Closeout choices

- **Route.** Direct to `main`; sixteen commits from `a33af26`.
- **Documentation.** README, changelog, release notes, and the `tcw-work` skill,
  into `upcoming.md`. The release note leads with the upgrade behaviour change
  rather than mentioning it, because anyone already on a provisioned store gets
  pushes they did not ask for.
- **Capabilities.** One new, now `Supported`; two `changed:` bodies genuinely
  edited, verified by reading their git history rather than trusting the
  declaration.
- **Version.** `v1.2.0`, cut at epic closeout — a minor, because children B and C
  each add user-facing surface without breaking an API. Not cut during
  implementation; this item's sibling recorded two premature cuts.

## Notes

- The review was requested rather than assumed, and its stopping rule was one
  pass. It found three real defects, which is a strong argument for running one
  on the riskiest item of an initiative — and the stopping rule is what kept
  "review-gated acceptance" from becoming "never accepted".
