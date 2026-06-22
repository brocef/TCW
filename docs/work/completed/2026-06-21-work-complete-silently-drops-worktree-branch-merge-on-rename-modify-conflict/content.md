# work complete silently drops worktree branch merge on rename/modify conflict

## Product changes

## Technical changes

`tcw work complete <slug>` on a `--worktree` item performed the active→completed
folder move and **deleted the work branch**, but the work branch was never
merged into the primary checkout. The implementation commit became unreachable
(dangling) instead of landing on the integration branch. No error was raised —
the command printed the DoD checklist and `completed ... (done)` as if it had
succeeded.

## Meta changes

# Bug: `work complete` deletes the worktree branch without merging it (silent data-loss-shaped failure)

## Severity

High. The completion path can throw away committed implementation work while
reporting success. The commit is recoverable from the object DB only until GC;
a user who trusts the "completed" output and moves on can lose it.

## Environment

- tcw plugin cache version: `tcw/0.3.2`
- Repo: a `--worktree` item in `proposit-shared` (separate child repo).
- Primary branch: `main`. Worktree branch: `work/<slug>`.

## What I did (repro)

1. `tcw work new "<slug>"` → backlog. Wrote `spec.md` + `plan.md` into the item
   folder while it was in backlog.
2. `tcw work start <slug> --worktree` → created worktree + branch `work/<slug>`;
   start commit `S` landed on `main` carrying the item docs (content/spec/plan/
   state) in `active/`.
3. In the worktree, made all code/test/doc edits, then ran the repo's
   formatter. **Prettier reformatted the tracked `active/.../spec.md`,
   `plan.md`, and `state.yaml`** (the same item-doc files the start commit had
   added). Committed everything as `I` on `work/<slug>` (parent = `S`).
4. `git status`/`check` in the worktree: clean, full pipeline green.
5. From the primary checkout: `tcw work complete <slug> --resolution done
   --confirm`.

## What happened

- The active→completed rename for the item docs was **staged** in `main`'s index
  (left for the user to commit — that part is by design).
- The worktree was removed and branch `work/<slug>` was **deleted**.
- **The merge of `work/<slug>` (commit `I`) into `main` did not happen.** `main`
  HEAD was still `S`. `git branch -a --contains I` → nothing; `I` was only
  reachable as a dangling object.
- Command output gave no warning — just the DoD checklist and
  `completed <slug> (done)`.

A comparison item completed in the same repo earlier (no formatter touch on the
tracked item docs) shows a clean `merge … Fast-forward` in the reflog right
before its complete commit — so the merge normally happens. The differentiator
here is the **rename/modify overlap**: the work branch modified the same tracked
`active/<slug>/*` files that `complete` renames to `completed/<slug>/*`. The
auto-merge presumably hit a rename/modify situation, failed or was skipped, and
the flow proceeded to branch deletion regardless.

## Expected

`work complete` on a worktree item should either:

- merge the work branch into the primary checkout first and **only delete the
  branch if the merge succeeds**; or
- on any merge failure/conflict, **abort with a clear error**, leave the branch
  intact, and do not move the folder — so the user can resolve and retry.

It must never delete the work branch while its commits are unmerged, and must
never report `completed` when the code did not integrate.

## Root-cause hypotheses (for the implementer)

- The completion sequence likely orders branch-delete / worktree-remove
  independently of (or before checking) the merge result.
- The merge step is probably not failing loudly: a rename/modify or
  non-fast-forward outcome should be a hard stop, not a no-op.
- Note the interaction with tracked item docs living under `docs/work/`: when a
  worktree run reformats/edits `active/<slug>/*`, those edits collide with the
  rename `complete` performs. Either (a) don't track formatting-volatile item
  docs in a way that collides, or (b) make the merge robust to a
  modify-on-renamed-path (merge first on the `active/` paths, then rename).

## Suggested fixes

1. Gate branch/worktree teardown on a successful merge; fail closed otherwise.
2. Make the merge explicit and check its exit status; surface conflicts.
3. Add a regression test: worktree item whose run modifies its own tracked
   `active/<slug>/*` docs, then `complete` — assert the implementation commit is
   reachable from the integration branch afterward and the branch is only
   removed post-merge.

## Workaround used

Recovered the dangling implementation commit `I` (still in the object DB),
`git merge --ff-only I` onto `main` (its parent was the start commit `S`, so it
fast-forwarded), re-ran `tcw work complete` to re-stage the folder move, then
committed it. End history: `start → feat(impl) → complete`.

## Secondary (minor) observations

- On the recovery re-run, `complete` printed
  `worktree remove failed … is not a working tree` (the worktree was already
  gone) but still proceeded — harmless here, but teardown of an
  already-absent worktree should be tolerated quietly rather than printed as a
  failure line.
- `complete` leaves the `state.yaml` it rewrites in a non-prettier format,
  which then fails the repo's `prettier --check` lint. Minor, but it forces a
  follow-up formatting commit on every completion in repos that lint
  `docs/work/`.
