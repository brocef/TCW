# Spec — Replace private project names in TCW's tracked files with generic ones

_Written after the work was done, from what was done. The item went straight
from its request to implementation, delegated to an agent in a worktree while
other items were in review. This spec records the decisions so review has
something to check against._

## Capability changes

None. The one capability description touched
(`work/declare-capability-changes-in-a-child-projects-ledger`) changes only
its example paths.

## Problem

`git grep -i "proposit\|PRPI"` at the head of `main` found private project
IDs, a GitHub organisation, a Jira project key and ticket keys, folder
layouts and capability paths in 11 tracked files outside `docs/work`, and in
some work items. The repository is public.

## Goals

1. No tracked file names a private project, except the Jira site address of
   TCW's own tracker, which the user decided to keep.
2. Every changed test checks the same behavior as before.

## Non-goals

Rewriting git history or published tags; renaming work-item folders other
than TCW-101's (done in TCW-101).

## Design

Generic names, consistently: `core`, `app`/`app-repo`, `workspace` (project
`product`), GitHub organisation `Example-Org` (mixed case, so the cache-key
test still checks lowercasing), Jira project `APP`. Values derived from a
name (cache keys) are recomputed by calling the code, not guessed.

## Abstraction litmus test

No operation changes.

## Use cases

None: names only. UC-7's rule (a public repository must not carry a private
reader's names) is what this enforces for TCW itself.

## Acceptance criteria

1. `git grep -n -i "proposit\|PRPI" -- . ':!pnpm-lock.yaml'` shows only
   `proposit.atlassian.net`.
2. Each changed test goes red when the behavior it names is broken.
3. Bare `pytest` passes, apart from failures shown to be unrelated.

## Risks

A recomputed expected value that merely restates the code would weaken a
test; recomputing with the same call reproduced the old pinned value for the
old URL, which checks the method.
