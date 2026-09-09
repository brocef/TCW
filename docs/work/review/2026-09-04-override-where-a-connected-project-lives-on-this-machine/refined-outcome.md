# Refined outcome — Override where a connected project lives on this machine

**Accepted on 2026-09-09**, on the second pass, after one rework round.

## The decision

Accepted with one acceptance condition deferred, named below, and with
publication deliberately withheld. The user's closeout choices were: complete the
item, cut a patch version, and **hold the push** — nothing leaves this machine
until the deferred check has been run.

The first pass met all eleven acceptance criteria as written but left `tcw
provision` fetching when an override was present and wrong. `outcome.md` flagged
that rather than absorbing it, and verification assigned it to this item instead
of a follow-up. `rework.md` records the rejection; `e05c6e7` and `da130aa` are
the response.

## Evidence

**The suite, run whole after the rework:**

```
2403 passed in 1067.98s (0:17:47)
```

Zero failures. The pre-work baseline was `1 failed, 2379 passed`, and that one
failure is the wheel test task R2 addresses — so this is the first fully green
run, and 24 tests were added across the two passes.

**The reproduction from the intake**, built by hand in a scratch workspace with a
local git remote, because criterion 3 names a workspace the suite cannot reach.
Configs describing a nested layout, repositories checked out flat. Without the
override, `tcw provision` fetched a second copy and `tcw validate` reported the
two problems the intake quoted, verbatim. With `TCW_PROJECT_PROPOSIT_CORE` set
and the cache cleared: no cache entry, `validate OK` from both nodes, exit 0.
Two problems to zero, nothing fetched.

**The four provisioning outcomes**, also by hand:

| Override                  | `tcw provision`                        | Cache |
| ------------------------- | -------------------------------------- | ----- |
| names the right node      | `already available`, exit 0            | empty |
| names a node with another id | refuses naming both ids, exit 1     | empty |
| names a directory, not a node | refuses naming the variable, exit 1 | empty |
| names a path not here     | falls through and fetches, exit 0      | one   |

**Mutation testing rather than green tests alone.** Ten mutations were applied
and every one turned the intended assertion red: demoting rule 0 below rule 1,
making an absent path an error, letting a present-and-wrong override fall
through, removing the memoisation, removing the empty-value guard, moving the
`tcw validate` reporting below the block that returns, deleting that reporting,
removing the provisioning gate, neutering the reconcile pass, and removing the
gate's filter so it refuses everything. That last one matters most: it is what
proves the gate does not pass by over-refusing.

Two assertions were found passing for the wrong reason and rewritten — the
empty-variable case, which resolved to a nonexistent directory either way, and
the whole first round of `tcw validate` checks, which a stale `__pycache__` entry
had been answering from mutated bytecode.

**The capability ledger** reconciles: `tcw capabilities check` reports
`capabilities OK` and `tcw capabilities drift` reports no drift.
`cli/point-tcw-at-a-project-i-already-have` (`cap-75c7e9`) is `Supported`, and no
existing capability's status changed.

## Deferred acceptance condition

**A real Claude Code cloud session has not been run, and it is the only test of
the assumption the feature rests on** — that attached repositories are cloned as
flat siblings under one base directory. The spec flags this as unestablished,
inferred from one observed session and from `add_repo`'s description, never
documented as a guarantee.

The local reproduction covers the *layout*; it cannot cover whether the layout is
the one a cloud session actually produces. To run it, set these in the
environment's own configuration — **node ids, not repository names**, and in this
workspace the two are crossed:

```sh
TCW_PROJECT_PROPOSIT_CORE=/home/user/proposit-core
TCW_PROJECT_PROPOSIT_APP=/home/user/proposit-orchestration
TCW_PROJECT_PROPOSIT_APP_REPO=/home/user/proposit-app
```

Then, from a session with every repository attached, `tcw provision` should fetch
nothing and `tcw validate` should print three override lines and `validate OK`.
From a session with only one attached, the other two variables should name absent
paths, fall through, and provision normally.

If the assumption is wrong the failure is benign — the paths are simply absent,
the overrides fall through, and provisioning resumes — but the feature would not
be delivering what it was asked for, and that is a new item rather than a defect
in this one. **This is the reason the push is being held.**

## Closeout

- **Version:** patch, 1.3.1. A new user-facing capability, but the user's call was
  that it reads as a fix to multi-repo resolution rather than a feature.
- **Publication:** withheld. The commits and the tag stay local until the
  deferred check above is run.
- **Originating GitHub issue:** none. The item came from conversation on
  2026-09-04, so that Definition of Done criterion does not apply. Nothing to
  answer or close.
- **The spec branch:** `claude/tcw-project-path-overrides` had never been merged
  and had no pull request. Its two spec commits were fast-forwarded onto `main`
  at the start of this session; the branch is now fully contained in `main` and
  can be deleted whenever convenient.

## Follow-ups

None filed. The two candidates were both absorbed into this item by the user's
decision at verify: the provisioning gap became task R1, and the wheel-test
failure became task R2. The spec's non-goals stand untouched and remain available
as separate items if wanted — a per-machine config file below the environment
rung, and the matching gap in `resolve_store` for component stores, which is the
first place to look if this pattern proves out.
