# Outcome

All seven planned tasks shipped. **873 Python tests** (from 851 at the start of
this child, 733 before the epic) and 44 web tests pass; `tcw validate` OK.

| Commit | Tasks |
|---|---|
| `36193dd` | Model, adapter, and `tcw validate` rejections (1–3) |
| `ae8e2d3` | `tcw work lifecycle`, `--directive`, hook executor (4–6) |
| *this* | Documentation sync (7) |

## What shipped

A node can bind agent skills or shell commands to any lifecycle stage or
transition. `tcw validate` rejects nineteen distinct malformed shapes, each with
a message naming the offending key. `tcw work lifecycle` reports the contract and
what is bound, in three output modes. Command bindings execute around
transitions; skill bindings are named and left to the agent.

## Three decisions worth their reasoning

**`discard` binds on the move, not the verb.** It is the one transition with no
CLI verb — it is `complete --resolution <not-done>`. Keying bindings on the verb
would make one binding fire for both "we shipped it" and "we gave up on it",
collapsing exactly the distinction `discard` exists to preserve. Two tests pin
which one fires for each resolution.

**The parser is pure and returns `(policy, problems)`.** `tcw validate` reports
the problems; the adapter discards them. Reading a policy must not take
`tcw work list` down over a mistyped key — but one shared implementation means
the two can never disagree about what is legal, which is the drift this whole
initiative exists to remove. Parsing is also *partial*: one bad binding does not
silently empty its stage, and every problem is reported rather than just the
first.

**`pre` hooks run before the store is touched at all.** This is the whole reason
hook execution lives in the CLI rather than in `WorkStore`. `complete()` writes
the resolution with `set_field` *before* it moves the item, so a hook evaluated
inside the store would abort having already stamped a resolution onto an item
still sitting in `active` — closed by its data, open by its folder. No
transaction concept or interface change was needed; the ordering is entirely
within the CLI's control. `test_a_failing_pre_hook_writes_no_field` asserts the
*field* as well as the status, because asserting "did not move" alone would pass
the broken implementation.

## `LIFECYCLE_STEPS` is the contract, in one place

The objective, inputs, produced artifact, status move, and gates for every stage
and transition are now a machine-readable table in the model rather than prose.
Child 4's stage documents must agree with it, and one source is what makes that
agreement checkable instead of two documents happening to match. Child 4 should
read this table before writing a single stage document.

## A child-1 bug this child's tests caught

`work/cli.py`'s `SUBCOMMANDS` never gained `submit` or `rework`. Latent — work's
`DEFAULT_SUBCOMMAND` is `None`, so nothing dispatches through it today — but
wrong data that would misdispatch the moment that changed. Found by a test
written to pin the transition-id/CLI-verb relationship, not to audit child 1.
`lifecycle` was added at the same time.

## Verification beyond the suite

A real repository with a configured `pre` hook, driven by hand:

1. `tcw validate` → OK on the valid policy.
2. `tcw work start` with the gate condition unmet → hook stderr surfaced, exit 1,
   item still `backlog`.
3. Gate satisfied → started, exit 0.
4. `--directive` bound → one complete sentence. Unbound → empty stdout, exit 0.
5. The binding rewritten as a bare string → `tcw validate` exit 1, message naming
   `work.lifecycle.stages.spec[0]` and what was expected.

## Notes

**The web complete modal now states that hooks do not run there** — which closes
child 2a's deferred item as well, since it is the same surface. It also says that
a refused auto-commit still moves the item and reports to `tcw serve`'s terminal.
Both are honest disclosure of a real asymmetry rather than a fix for it: running
configured shell from an HTTP handler on a button click is a meaningfully worse
posture than a CLI the user invoked, and that trade stands.

**Skill bindings remain `[judgment]` on every harness and unenforceable on some.**
Codex cannot enumerate skills, so "configured but missing" cannot fail closed
there. The skill instructs the agent to report and stop. Nothing in TCW depends
on that check firing, and nothing should be built that does — this is the
assumption most likely to be quietly reintroduced by a later child.

**`pr` is still unconsumed**, now through two children that were each predicted to
use it. Child 4's stage documents are its last plausible consumer. If it is still
unread at epic close it should be deleted, following the `phase`/`dod` pattern
this epic has now applied twice.

**One thing child 3 must not re-derive:** `tcw work lifecycle --directive` already
resolves a stage's bindings and emits an instruction. `tcw work methodology
<stage>` overlaps it heavily, and the epic spec's framing — "methodology is
*how*, the stage doc is *what*" — is the only thing distinguishing them. Child 3
should either justify the second command clearly or fold itself into this one.
