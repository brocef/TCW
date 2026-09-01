# Refined outcome: Re-anchor a relative work.path at the node's counterpart inside the main worktree

**Accepted.** The user approved closeout in advance — "post a correction then
finish this work, cut a patch and push after everything is done" — after being
shown the mid-implementation finding that main's generalized store ladder had
introduced a second copy of the defect and that the fix would widen to cover it.

## Evidence

Every acceptance criterion in `spec.md` is met; the mapping to the test that
checks each one is the table in `outcome.md`, and all of them were watched fail
before the code that makes them pass.

Commands run at verification, not recalled:

- `pytest -q -p no:randomly` — **2175 passed, 5 failed**, the five confirmed
  pre-existing on the rebase base with this branch stashed (three assert a
  `PermissionError` that cannot raise under root, one reads an unbuilt wheel,
  one is `test_invalid_utf8_is_replaced_rather_than_fatal`).
- `pytest tests/test_environment_hardness.py -q -p no:randomly` — **81 passed**,
  including `monorepo_worktree`, the layout a naive "always re-anchor" fix
  breaks.
- `tcw capabilities check` — `capabilities OK`.
- `tcw capabilities drift` — `no capability drift`, exit 0.
- The reporter's own shape, end to end: same store path from the primary
  checkout and the linked worktree, a `tcw work new` from inside the worktree
  landing in the external store and visible from the primary checkout, and his
  verbatim error reproduced when `anchor_configured_path` is reverted.

## Capability reconciliation

Two entries amended, both still **Supported**, neither newly introduced:

- `cli/run-from-a-git-worktree` (cap-b47597) — the escape rule and the
  "the node I operate on is the worktree" promise now cover a configured
  `work.path` / `taxonomy.path` / `capabilities.path`, not only
  `connected-projects` locators. This entry is what made the change's scope
  correct: it documented the behaviour the code did not have.
- `work/configure-the-work-store-location` (cap-46e036) — "a path relative to
  the owning project's primary checkout" qualified, since that holds only for a
  path that leaves the checkout.

No status flips, no new capability, and no Planning doc repointed — the
originating items keep the credit, because this item corrected the code to match
promises they had already made.

## Deferred follow-ups

None blocking. Two things noted and deliberately not done here:

1. **The four standing `tcw validate` problems** — dangling `tcw://W/`
   references to items that no longer exist under those slugs. Present
   identically on the base, untouched, and a live instance of what issue #25
   reports; the item tracking that is
   `2026-09-01-make-tcw-validate-usable-as-a-gate-suppressible-references-and-graded-exit-codes`.
2. **The counterpart expression still appears three times** —
   `tcw/store/project.py:123`, `:334`, and `tcw/work/cli.py:1199` each spell
   `main / <node>.relative_to(top)` inline. The store hooks are now one
   function; these three are correct and were left alone rather than refactoring
   working code that two other features depend on.

## Closeout choices

- **Route:** the branch `claude/tcw-triage-issues-skill-hp67lr`, rebased onto
  `main`. No pull request was requested.
- **Documentation:** README, `docs/changelogs/upcoming.md` and
  `docs/release-notes/upcoming.md` updated in `08358fb`; the
  `Skill-Driven-Component` trigger evaluated and recorded as not firing.
- **Version:** a patch cut, at the user's instruction.
- **Post-mortem:** not offered as a blocking step. The spec's sweep was wrong
  about the second `_local_root`, but the cause was the tree moving under the
  branch rather than a stage that skipped its job — the sweep was run, and
  correctly, against the tree that existed at the time. Worth revisiting only if
  a rebase invalidating a spec happens again.
