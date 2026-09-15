# Refined outcome — Make `tracker link` record a cross-reference without claiming the ticket

## Decision

**Accepted.** On 2026-09-14 the requester asked for a multi review of PR #38 with
the reviewing agent as the verifier, then asked for the review's fixes. After
that they said: "If it passes and everything looks good, you can merge to main
locally and cut a minor version." Both conditions held, so the fixes went in on
the branch (`3a36ade7`, `ea76b5b8`, `72029a6c`) and the branch was merged into
local `main` as `ea2f06d4`. `main` had first been checked against `origin/main`:
both were at `e4d96f7b`.

## Evidence

- **Full suite.** `python -m pytest` in the PR worktree after the fixes gave
  **3114 passed**. Bare `pytest`, as CI runs it, on merged `main` at `ea2f06d4`
  (tree identical to the branch tip): **3114 passed**. Before the fixes, CI on PR #38 was
  green on Python 3.11 and 3.14, and a local run gave 3113 passed.
- **Checks.** `tcw validate` printed `validate OK`; `tcw capabilities check`
  printed `capabilities OK`.
- **Help read by hand.** All five `tracker --help` outputs were rendered after
  the fixes; no line is over 79 columns.
- **Mutation checks on the new assertions.**
  - Disabling the new linked-but-not-claimed branch turned
    `test_import_after_link_says_the_ticket_is_linked_but_not_claimed` red, on
    its message assertion.
  - Making `link` write a stray file into a resolved item turned both cases of
    `test_link_binds_a_resolved_item` red, on the local-state comparison.

## Review

**Adversarial code reviewer: NOT DONE.** It found no defect in the core change.
What it raised, and what happened to each:

- *Accepted, narrowed from blocking:* a binding on a finished item lands in a
  gitignored folder, is never staged, and nothing warns. Everything else in a
  finished item's folder is equally local, so the defect was the documentation
  promising more. At the requester's direction the simplest behaviour stays;
  every document that mentions it now says so.
- *Accepted:* `import` after `link` said the tracker had the ticket "assigned to
  nobody". It now says the ticket is linked but not claimed.
- *Accepted:* a resolved item pending deletion under `work.retain: false` binds,
  and the docstring and changelog said it would refuse. Texts corrected; no
  refusal added.
- *Accepted:* the `import` epilog stated two refusals that do not happen; the
  epilogs left out others; `show` implied `claimable` looks at the assignee.
- *Accepted:* `outcome.md` named pre-rebase commit hashes; stale comments on
  `_binding_for`, `_LOCAL_WRITE_ERRORS` and one test.
- *Deferred:* the unused `ClaimOutcome.account_id` / `account_name` fields, and
  two finished items holding one ticket.
- *Noted, no change:* the spec's "nobody is on this version" was false (2.1.2
  shipped `claimed-by`), with no code consequence.

**Codex (read-only sandbox confirmed from its session header): merge after
fixes.** It found the same documentation gap about two resolved items and the
help-text omissions, and the resolved-item test not checking the rest of the
item; all were fixed. Its wish to list authentication, network and rate-limit
failures in every epilog was rejected, because generic tracker failures are not
a command's refusals.

**`bllm`: no answer.** All three slices returned "bllm is temporarily disabled
for maintenance". That outage is already filed in `/Users/brian/llama/docs/work/inbox`.

## Deferred follow-ups

`docs/work/inbox/2026-09-14-follow-ups-the-tracker-link-review-left.md`:

- revisit whether a binding on a finished item should warn or refuse when git
  will not record it;
- whether `link` should refuse an item pending deletion;
- two finished items can hold one ticket and part;
- the unused `ClaimOutcome` account fields.

Claiming a linked ticket remains with
`2026-09-12-synchronize-the-work-lifecycle-outward-to-the-tracker`, as the spec
planned.

## Closeout

- **Capability ledger.** `capabilities.yaml` lists one `changed:` path,
  `work/manage-external-tracker-intake`, still `Supported`; its body matches
  what shipped, including the review fixes.
- **No GitHub issue** is attached to this item.
- **Worktree.** Not started with `--worktree`. The review worktree
  `.worktrees/pr-38` was made by hand and removed after the merge; the branch
  `claude/charming-galileo-wyjmmj` is left in place.
- **Version:** at the requester's direction, a minor version is cut after this
  item completes. The merge and the cut are local; nothing is pushed.
