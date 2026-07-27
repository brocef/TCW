# Commit every work transition; trunk-branch and DoD cleanup

Epic: [Redefine the TCW work lifecycle](tcw://W/2026-07-27-redefine-the-tcw-work-lifecycle-explicit-stages-transitions-and-hooks)

**The behavior half of the original child 2**, split out because it shares no
code with the configuration half. Depends on child 1, which shipped the `review`
status and the `submit`/`rework` edges.

Owns what a transition *does*. Adds no statuses, no transitions, and no
configuration schema beyond two flat keys.

## Scope

- **`work.auto-commit-transitions`, default `true`** — every transition commits
  its own move, implemented in `FsWorkStore._effect_transition`. That is the
  single choke point both the CLI and `tcw serve` pass through, and committing
  has no abstract analog, so it belongs in the adapter.
- Commits are **scoped to the item's source and destination paths**, not to
  `docs/work` — `git commit -- <paths>` takes working-tree state, so a broad
  pathspec would sweep in every other item's uncommitted edits.
- **Three distinct outcomes on a failed commit**, never conflated: not a repo →
  skip silently; nothing to commit → skip silently; anything else
  (`index.lock`, permissions, a failing pre-commit hook) → report and exit
  non-zero. The move is never rolled back.
- **`work.trunk-branch`** — compare `HEAD`, warn once on mismatch, commit where
  you are. Never checks out, never commits elsewhere, never refuses. Suppressed
  when the item's own `branch` field matches `HEAD`.
- **`start --worktree` stops double-committing.** The store now guarantees the
  move is committed before `add_worktree` runs, which is the ordering the
  worktree branch depends on. `_start` keeps a narrower commit for `.gitignore`
  and the `worktree`/`branch` fields. The setting does **not** apply to
  `--worktree`, which must commit regardless.
- **Stop persisting `dod:`** — a fixed constant on every completed item that
  records nothing. The checklist keeps being printed before `--confirm`; the real
  gates are untouched. `dod_ack` stays in the signature. Items completed before
  this change keep their stored value unread, exactly as child 1 handled `phase`.
- **`tcw work complete --already-integrated`** — for a `--worktree` item whose
  branch was merged outside TCW. Skips the auto-merge and nothing else; every
  other gate runs; tolerates an already-removed worktree or branch.

## Done when

- Every transition leaves a commit containing exactly the moved item, and an
  unrelated modified file elsewhere under `docs/work/` is not swept in.
- `auto-commit-transitions: false` reproduces today's staged-but-uncommitted
  behavior.
- A real git failure is reported and exits non-zero rather than being swallowed
  alongside the two benign cases.
- A transition performed through `tcw serve`'s API is committed too.
- `start --worktree` produces the status move on the branch with no duplicate
  commit, and still works with auto-commit disabled.
- A newly completed item has no `dod:`; one completed earlier keeps it and loads.
- `--already-integrated` skips the merge, keeps every other gate, and tolerates
  prior cleanup.

## Notes

`auto-commit-transitions` defaulting to `true` is **the largest behavior change
in the epic** — plain `tcw work start` commits nothing today, and this also
changes what the web app does to the repository. It needs a prominent release
note, not just a changelog line.

Concurrency is explicitly **not** solved here. Two processes transitioning the
same item can race, and auto-commit widens the window because a commit takes
longer than a rename. That problem has an owner:
[Concurrency-safe work claims for multi-agent repos](tcw://W/2026-06-22-concurrency-safe-work-claims-for-multi-agent-repos-configurable-work-path-atomic-owner-stamp).
What this child owes is a legible failure, not a fix.

`--already-integrated` is completion mechanics rather than commit behavior, so it
sits here only because it has to sit somewhere and it is small. It is the natural
consumer of the `pr` field child 1 added — but no coupling should be invented. If
the two never connect, `pr` was premature and that is worth saying at epic close.
