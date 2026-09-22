# Outcome

Strict tracker mode now requires `work.tracker.exclusive-claim-transition`. A
strict block without the key is a configuration problem: `tcw validate` names the
key, says why strict mode needs it and what to set, and every strict move refuses
through the existing broken-configuration refusal, which points at `tcw validate`.
A project that is not strict is unaffected.

## What shipped, task by task

| Task | What | Commit |
| ---- | ---- | ------ |
| 1 | Every strict test fixture sets the key while it is still optional; `strict_node` takes it as a required `claim_transition` argument; the stale `test_strict_is_reported_as_unknown_because_c4_owns_it` is removed | `5135d67b` |
| 2 | `parse_tracker_config` reports `STRICT_NEEDS_EXCLUSIVE_CLAIM` for a strict block with no such key; comments in `tcw/store/base.py` and the `tcw/tracker/ownership.py` docstring updated; one test per criterion 1–7 | `a0804846` |
| 3 | Capability statement for `work/require-tracker-backed-work` names the key | `857323d6` |
| 3 | Documentation Sync: `skills/configure/references/tracker.md`, `docs/guide/jira.md`, `docs/release-notes/upcoming.md` (its first and only entry), `docs/changelogs/upcoming.md` | `60b3e92d` |

## Test result

Full suite, bare `pytest` from the worktree in the private virtual environment
(`tcw.__file__` confirmed to resolve to the worktree): **4312 passed, 3 skipped,
0 failed** (4315 collected). `main` at `25aacd33` collects 4304; this item removes
one test and adds twelve (criterion 3 and 4 tests are parametrized in two cases
each, criterion 7 in four), so 4304 − 1 + 12 = 4315.

`tcw validate` from the worktree: `validate OK`.

## Mutations

Each break was applied to the committed code, the named tests run, the failure
message read, and the file restored (`git diff` empty afterwards).

| Mutation | Went red | Why it went red |
| --- | --- | --- |
| Delete the new check | criteria 1, 5, 6, 7(b) | 1: `config` was a `TrackerConfig`, not `None`. 5: `validate()` returned `[]`. 6: `tracker_config()` was not `None`. 7(b): the child's problems were `[]`. |
| Fire whether or not the key is set (`if True:` inside `if strict:`) | criteria 2, 4 (both cases), 6, 7(a), 7(c) | 2, 7(a), 7(c): the unexpected `required when strict is true` problem. 4: two problems naming the key. 6: its setup (`tracker link`) was refused because the configuration was broken. |
| Move the check out of `if strict:` | criteria 3 (both cases), 7(d) | The `required when strict is true` problem appeared for a block that is not strict. |
| Test presence with `raw.get(...) is None` instead of `not in raw` | criterion 4, `null` case only | Two problems named the key (the `blank` case stays green, as expected: `""` is not `None`). |
| Delete `timeout-seconds: -1` in `test_a_broken_strict_block_names_validate` | red | The refusal for `new` from a valid strict block does not mention `tcw validate`. |
| Delete `timeout-seconds: -1` in `test_a_broken_strict_block_refuses_inbox_accept_even_with_ticket` | red | Exit code 0: a valid strict block accepts `inbox accept --ticket`. |

Before the check existed (the constant added, the check not yet written), the new
tests failed in exactly the first row's pattern, so each was red before the code
that makes it pass.

**Sweep check.** With the `problems.append(...)` replaced by
`raise AssertionError("strict block without exclusive-claim-transition")`, the
whole suite gave 4 failed, 4308 passed, 3 skipped. The four failures are exactly
the tests that build a strict block without the key on purpose (criteria 1, 5, 6
and 7(b)), and each failed on that `AssertionError`. No strict fixture was
missed. The `raise` was reverted.

## What an upgrading strict user sees

A throwaway node with `strict: true`, the three statuses, no
`exclusive-claim-transition`, and one backlog item:

```
$ tcw validate
tcw-config.yaml: work.tracker.exclusive-claim-transition: required when strict is true. Strict mode promises that only one person can take a ticket, and a claim keeps that promise by applying this transition, which your workflow will not apply to a ticket that has already been taken. Name the transition that takes a ticket into work.
1 problem(s).
(exit 1)
$ tcw work start 2026-09-22-some-work
tcw work start: refused under strict tracker mode; 2026-09-22-some-work was not started. The tracker configuration has problems, and strict mode refuses until it is fixed. Run `tcw validate`.
(exit 1)
$ tcw work tracker list
tcw work tracker list: the tracker configuration has problems:
  - tcw-config.yaml: work.tracker.exclusive-claim-transition: required when strict is true. Strict mode promises that only one person can take a ticket, and a claim keeps that promise by applying this transition, which your workflow will not apply to a ticket that has already been taken. Name the transition that takes a ticket into work.
(exit 1)
```

The first and third name the key; the second names `tcw validate`, as planned.

**The texts read together.** The validate message, the `tracker.md` and `jira.md`
passages, and the release-note entry were read side by side. None says that
`tcw work start` uses the key; each says only that a claim applies it and that
`tcw work tracker claim` does so, which is true in a release that has this item
and not C4.

## What the plan or spec got wrong

- **The inheritance test is one parametrized test, not four assertions in one
  test.** The plan listed 7(a)–(d) as cases of one test; written as four
  parametrized cases, each mutation's result shows exactly which cases went red,
  which one test with four assertions would hide after its first failure.
- **The plan's mutation lists were incomplete, not wrong.** "Fire whether or not
  the key is set" also turns criterion 4 (both cases) and criterion 6 red, not
  only 2, 7(a) and 7(c): criterion 4 gets a second problem naming the key, and
  criterion 6's setup links items while the key is set, which the mutation breaks.
  Neither weakens a test; they are recorded above.
- **Under that same mutation, 7(a)'s problem is attributed to the parent's file,
  not the child's**, because the parent wrote the key and attribution follows the
  file that wrote a key. It does not affect the shipped behaviour (the problem only
  fires when nobody wrote the key, so it is always the child's), but it shows that
  Design 2's attribution claim holds only because the check fires on an absent key.
- **`STRICT_NEEDS_EXCLUSIVE_CLAIM` is written as one string split across source
  lines** by implicit concatenation rather than a single source line; the text is
  exactly the plan's.
- **`:411` in `tests/test_tracker_strict.py` needed nothing, as the plan said**; a
  first pass of the sweep added the key there too and it was taken back out.

Otherwise the plan held: its fixture list (including the eight sites it added over
the spec's) was complete, as the sweep check confirmed.

## Notes

- **Open question for verify (from the spec):** should the next version cut wait
  for C4 (`2026-09-16-compose-the-lifecycle-moves-from-claim-and-sync`)? Until C4
  lands, strict projects must set a key that a strict `start` does not yet use;
  only `tcw work tracker claim` applies it. The texts are written to be true either
  way.
- C4's release-note entry must follow this item's (now the first in
  `docs/release-notes/upcoming.md`) and not repeat it.
