---
verdict: rejected
judges: 1
---

# Review round 1 — TCW-109

Reviewed by a separate read-only agent (the `tcw:reviewer` agent) on
2026-10-24 in a frozen worktree at `ff12abd3`, the head of branch
`impl-109`, over `0287fc4e..ff12abd3`. The dispatching session checked the
blocking finding against the repository before writing this round. The item
is reviewed on its branch because TCW-111 lands in `v4` first; the branch is
rebased onto it before the item moves on.

## Checks run

- The full suite as CI runs it, run by the implementer at `ff3aba68` in two
  halves by folder: `1915 passed, 2 skipped` and `4190 passed, 111 skipped`.
  The dispatching session runs it again on the final tree.
- By the reviewer: the eight top-level test files of this item,
  `455 passed, 3 skipped`; `tests/config`, `244 passed`;
  `tests/serve/test_work_read.py`, `35 passed`.
- By hand, with every `TCW_*` variable unset: AC 13, 17 and 18 (`tags list`
  exit 7 with the spec's message; `tags add z` writes `[inherit: true, z]`;
  `rm a` exit 3 naming `core`; `--origin` showing the whole path and the
  variable; `validate` exit 0 with the suffix; `config show` exit 7), and
  the AC 23 binding with `{command: gate}`.
- `documentation-sync`: both `upcoming/` entries present; the guides,
  `docs/use-cases.md` and the skills deferred to TCW-117 as the spec's
  non-goals allow.

## Acceptance criteria

AC 1 to 29, 32 and 33 are met, each by a named test. AC 30: the records
match the capability changes; the released `tcw validate` over this
repository is run by the dispatching session at completion. AC 31 is the
suite run.

The implementer's decisions agree with the spec or settle what it leaves
open. The four amended tests are each required by the spec (Design 3.5 and
3.6, 1.6, 2.4; the helper rename obeys `test_no_node`). `cdd6be20` reaches
only the warnings in `validate.config_findings`, whose tests ran. No
override prints a secret value; no git call was added; no private name is in
the change.

## Findings

1. `tcw/config.py:927`: in Jira mode with a gap, the undecided keys always
   include `("work", "jira")`, and the prefix filter then drops every parse
   problem under `work.jira`, including keys this project decides itself.
   Spec 3.2 says the decided keys under an undecided `work.jira` are still
   checked, apart from "required". With `app: [core]`, `core` missing, and
   `app`'s own `work.jira: {project: APP, timeout: soon, credentials:
   {email-env: "bad name"}}`, `tcw validate` exits 0 with no error; with no
   parent it reports both. An ancestor's decided Jira keys are hidden the
   same way. No acceptance criterion's fixture has a bad key of its own.
2. A binding problem in a variable's value is reported as `error:
   environment: work.stages.spec.prompt[0]: …`, without the variable's name,
   though spec 7.2 asks that each Design 4 problem start with it.
3. The changelog entry says a bad variable "stops commands in that project";
   every command checks every variable, so it is "in any project".

## Needs a separate change

- The `tag-a-work-item` record leaves `rm` out of the commands that stop with
  exit 7; a wording point for TCW-117.

## What implement must do

- (a) Check the decided keys under an undecided `work.jira` (Design 3.2),
  this project's and its ancestors', apart from "required", with a test
  using the scenario above.
- (b) Name the variable in each problem from a variable's value (Design 7.2),
  with a test.
- (c) Correct the changelog wording.
- (d) `implement/round-2.md`.
