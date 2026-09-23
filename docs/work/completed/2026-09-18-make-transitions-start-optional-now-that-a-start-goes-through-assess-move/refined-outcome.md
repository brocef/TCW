# Refined outcome: make `transitions.start` optional now that a start goes through `assess_move`

## Decision

**Accepted** on 2026-09-22 by the coordinating session, after folding in two
corrections the assessment found. For this epic the requester approves at the
epic's own `verify` stage and lets each child complete on a clean assessment,
stopping only where a finding needs a decision. Neither finding here needed one:
both were sentences of shipped text that asserted something the code does not do,
and both were single-sentence corrections.

## Evidence

- Full suite, run from the worktree in a private virtual environment with
  `import tcw` confirmed to resolve into the worktree: **4404 passed, 3 skipped,
  0 failed**, both before and after the two corrections. `tcw validate` OK.
- `tcw:verifier`, working in its own scratch copy of the worktree with its own
  virtual environment: **all 17 acceptance criteria met**, every one of the 32
  named tests present and passing.
- **Eight mutations**, applied one at a time in a second scratch copy. Seven went
  red; the assessment read *why* each went red rather than only that it did. The
  eighth is discussed below.

## What the mutations established

Two of them are worth recording because they are the ones that prove the tests
reach the code rather than merely sitting beside it.

**One mutation reddened all three of criterion 9's tests at once.** Three separate
paths derive a transition from the target status: the ordinary lifecycle start,
the owed-start catch-up, and the hop inside `walk()`. Breaking the derivation
broke all three. Had any one stayed green, that path would have been untested, and
that is exactly the shape of hole this epic's earlier children kept producing.

**The removal-advice mutation went red on `start` and stayed green on the other
four moves** — which is what proves that test is genuinely parametrized across all
five rather than looking parametrized while only exercising one.

**One mutation stayed green, and it is not a defect.** Criterion 17's mutation,
worded exactly as the spec words it, broke nothing. The reason is that the spec
described the wrong break: longest-prefix matching in `attribute_tracker_problems`
is implemented by the `": "` anchor in the `startswith` test, not by the
`reverse=True` sort, so for that input only one recorded spelling can ever match
and the sort order is unreachable. The break the spec *meant* does redden both
tests. The outcome document had already flagged this; the assessment re-derived it
from the code rather than taking it on trust, which is the right way to clear a
green mutation.

## The two corrections folded in at this stage

Both were false statements in shipped text. Neither changes behavior.

**1. The comment on `REASON_LIMIT` claimed a ceiling that cannot exist.** It said
400 holds the longest refusal TCW composes, measured at 331 characters. There is
no longest refusal. The message quotes a configured transition name, tracker-
supplied status names, and every transition the workflow offers from the ticket's
status, and TCW caps none of them. The fixed skeleton is 251 characters and
everything else is variable. A six-transition workflow with unremarkable names
composes 507 characters, and the cut still takes the `pre-backlog` hint — which is
the same failure the raise from 300 was meant to fix. The coordinating session
reproduced 507 independently before accepting the finding.

What made this worth fixing rather than noting: the next person to read that
comment would believe the number was derived from the code, when it came from one
fixture. The comment now says the limit caps how much of a reason the binding
stores, and records that only the stored record is cut — the CLI prints the reason
in full, and nothing truncated is sent to the tracker.

**2. The skill reference said `tracker list` reports an unset `transitions.start`.**
It does not. `_tracker_list` prints one row per ticket — key, status, assignee,
summary — and consults no transition at all; only `tracker show` and `inbox show`
reach the code that reports the setting. The matching sentence in the Jira guide
was already correct because it names the commands individually rather than saying
"both".

This is the more important of the two. A skill reference is read by an agent as
instruction, and criterion 14's tests cover `show` only, so nothing in the suite
would ever have caught the false half.

## Known effects

- **Two message texts change for projects that still set `transitions.start`.**
  The `offers no transition named` refusal for `start` now ends with the same
  "or remove it" advice the other four moves already gave, and a recorded reason
  that was previously cut at 300 characters now keeps 400. No transition applied
  and no exit code changes. Both are held by tests and described in the release
  note.
- **The non-breaking guarantee is genuinely tested, not assumed.** The test that
  proves a configured name is still honoured runs on a two-route fixture where the
  derived answer differs from the named one. On the old single-route fixture the
  two coincide, so that test proved nothing until the fixture was changed.
- No path can present an empty transition name to a user: the named branch is
  behind a truthiness check, the parser rejects an empty or blank value, and the
  one message that would have printed `''` is now unreachable because the new
  verdict returns before it.

## Deferred, with the reason

- **A pre-backlog ticket leaves triage before the refusal fires.** With
  `work.tracker.pre-backlog` configured and `transitions.start` unset, `import`
  applies the triage-exit transition and only then refuses, so the ticket moves
  and no item is created. The assessment verified this by probe against the real
  code. It is a newly reachable state rather than a regression — the configuration
  could not exist before this change — the CLI does tell the user the ticket moved,
  and the fix is a guard in `claim()` ahead of `leave_pre_backlog`. Filed rather
  than folded in, because it is a behavior change with its own test to write.
- **Closing the originating GitHub issues waits for publication**, per this
  project's standing rule: an issue closed before the fix ships tells the reporter
  it is fixed when they still cannot install it. The epic's closeout covers this.
- **Not checked against a real Jira.** Every tracker assertion here is against the
  in-repo fake. That has been true of this epic throughout and is recorded so the
  epic's verify can weigh it once rather than per child.

## Operational note

Merging this branch hit a rename conflict rather than merging unattended: the item
folder moved from `active/` to `review/` on `main` while the branch still had
`outcome.md` under `active/`. Git placed the file correctly and the resolution was
to stage it, but the merge does stop. Any child submitted for review from a
worktree will hit the same thing.
