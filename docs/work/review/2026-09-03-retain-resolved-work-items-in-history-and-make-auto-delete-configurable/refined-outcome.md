# Refined outcome — Retain resolved work items in history

_Accepted._

## Decision

Accepted. The behavior is right, the default is genuinely inert, and the two
places this could have destroyed data — the interlock and the record — are both
tested rather than reasoned about.

## Evidence

- **Suite:** 2290 passed; the four environmental failures only.
- **Retrievability is demonstrated, not asserted.** A test resolves the recorded
  SHA with `git show <sha>:<path>` and reads the item's `state.yaml` back out.
  That is the whole promise of the feature and it is checked directly.
- **The interlock works, and it did not at first.** `git check-ignore` on the
  folder answers "not ignored" for a rule that matches its contents, so the
  refusal silently passed until a test caught it. It now probes a path inside the
  folder, and the test would fail again if that regressed.
- **The default is inert.** A node declaring nothing scaffolds the same rules,
  resolves the same way, leaves the item on disk, and produces one commit.
  `tcw validate` on this repository is clean.
- **Never silently a deletion.** Three malformed shapes are parametrized; each
  reports and each still reads `True`.
- **Both commits reach a remote** from a provisioned store.

## Deferred follow-ups

- **`tcw work delete <slug>`** — the CLI verb for finishing an interrupted
  deletion — is the blocked follow-up item. The store operation it wraps exists
  and is re-runnable.
- **No migration was performed on a real board.** The plan asked for the
  documented migration to be walked on a copy of a `proposit-*` store. It was
  not: those boards live in another repository, none of them has declared
  retention, and doing it would have changed a store this item has no mandate
  over. The README's migration order is therefore *documented and unexercised*,
  and that is the one place this item's verification is weaker than planned.
- **`Tombstone.location` on a tracker-backed adapter** is specified as opaque
  and unparsed but has only the filesystem implementation.

## Closeout choices

- **Merge route:** the session branch.
- **Documentation:** README's resolved-work section rewritten around three
  arrangements; release notes; changelog; the `tcw-work` transitions and commands
  references; three capability bodies.
- **Capabilities:** `work/keep-resolved-work-out-of-git` now owns all three
  arrangements rather than the one; `work/complete-a-work-item` and
  `work/discard-a-work-item` note the second commit. Recorded in
  `capabilities.yaml`. No new capability — the archival hook is the next item's.
- **Version:** deferred to the end of the run.
- **Originating GitHub issue:** none.

## Notes

The correction worth carrying forward is the `Tombstone` docstring: the spec
proposed a field the codebase had explicitly refused, and neither the spec nor
the plan noticed. The reversal is defensible — the premise it rested on changed —
but it was defended after the fact rather than before, and the docstring now
carries the argument so the next reader does not have to reconstruct it.
