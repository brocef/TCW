# Reconcile the doc-sync item's status — it sits in `active` with nothing implemented

Housekeeping, not a feature. Recorded because it cannot be fixed without the CLI
and should not be fixed by hand.

## State

`2026-08-18-serve-documentation-sync-entries-from-tcw-config-yaml-instead-of-scraping-the-agent-guide`
is in `docs/work/active/`. Its `initial-request.md`, `spec.md`, and `plan.md` are
written, reviewed, and committed. **Not one line of its nine implementation tasks
was written.** The item was started, task 1 failed on the first command, and the
session stopped using the CLI.

So the board currently claims work is in progress that has not begun.

## What should happen

Either `tcw work rework`-style return to `backlog`, or simply resume
implementation from task 1. Both are one CLI call away and neither is urgent —
what matters is that the status is a claim, and right now the claim is false.

**Do not fix this by moving the directory by hand.** `AGENTS.md` is explicit that
the store is not hand-edited when a command exists, and the whole point of the
status being a folder is that the CLI owns the move. A `git mv` here would be the
exact filesystem-trick shortcut the prime directive exists to refuse.

## Where implementation stopped

Task 1 of `plan.md` — capturing `tcw work stage` output on an unconfigured node,
so the back-compat criterion has evidence recorded *before* the prompts change.
The capture script was written and deleted rather than committed: it never ran
successfully, and an untested fixture generator is worse than none. `plan.md`
task 1 describes what it has to do; rewriting it is maybe thirty minutes.

That ordering constraint still stands and is the single most important thing
about this item. If the prompts are edited before the baseline is recorded, the
recording captures the new behavior and the back-compat criterion becomes
unfalsifiable.

## Context worth keeping

The spec was reviewed by `codex` and six defects were found and folded in, all
verified against the tree. Two of them changed the design materially — the
substitution site moved from `_resolve_one` to `resolve_prompts`, and the
`LifecyclePolicy`-carries-the-entries assumption was replaced with real plumbing
through the `WorkStore` interface. That review is worth not repeating from
scratch; it is summarised in `spec.md` under `## Notes`.
