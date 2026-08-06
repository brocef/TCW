# Spec: gitignore resolved work folders at init by default

## Capability changes

```yaml
changed:
    - cli/scaffold-the-doc-trees
    - work/keep-resolved-work-out-of-git
```

No new capability. `work/keep-resolved-work-out-of-git` (`cap-7e064f`) already
describes the behavior — its body just says the user sets it up by hand, and now
`init` sets it up for them. `cli/scaffold-the-doc-trees` (`cap-2c5c9e`) gains a
sentence about what scaffolding the `work` component writes to `.gitignore`.

## Problem

`tcw work complete` and `tcw work discard` move an item into
`docs/work/{completed,discarded}/`, and by default those folders are tracked, so
a project's resolved work accumulates in its tree forever. This repo hit that at
83 folders and fixed it by hand (work item
`2026-07-30-untrack-completed-and-discarded-work-and-scrub-private-repository-references`):
gitignore both folders, and make `git_mv` untrack-rather-than-move when the
destination is ignored.

The mechanic landed; the default did not. Every new node still starts tracking
its resolved work and only finds out when the folders are large.

## Goals

1. `tcw init` / `tcw work init` writes the ignore rules for
   `docs/work/completed/` and `docs/work/discarded/` into the node's
   `.gitignore`, exempting each folder's `.gitkeep` so the empty folder itself
   stays in the tracked tree.
2. Re-running init on an existing node adds any missing rules and changes
   nothing else — that is the upgrade path for nodes scaffolded earlier.
3. This repo's own `.gitignore` moves to the same rules, restoring the two
   `.gitkeep` files to the index.

## Non-goals

- **No opt-out flag.** The `.gitignore` is the knob: delete the four lines. A
  `--no-ignore-resolved` flag would be a second way to express the same fact,
  and the fact already lives in a file the user edits freely.
- **No config setting** naming which statuses are ignored — same reasoning as
  the earlier item, which rejected `work.ignored-statuses`.
- **No history rewrite** and no retroactive `git rm --cached` on an existing
  node. Init writes rules; what git already tracks stays tracked until the user
  untracks it (the capability body already explains this).
- **No change to the transition mechanic.** `git_mv` already does the right
  thing; this item only makes nodes reach that path by default.

## Design

### Where it goes

`init()` in `tcw/store/fs.py` — the filesystem adapter's scaffold function,
already the thing that creates `docs/work/<status>/` and drops `.gitkeep` in it.

**Litmus test.** "Could a non-filesystem store implement this?" — no; `.gitignore`
has no analog in Jira. Which is exactly why it belongs where it lands: a private
detail of the FS adapter's own scaffolding, invisible to `WorkStore`. No
interface method changes. Passes.

### The rules

Written to `<node-root>/.gitignore` (paths in a `.gitignore` are relative to its
own directory, so a child node's rules stay correct without knowing the repo
root):

```gitignore
# Resolved work items: kept on disk and in history, out of the tracked tree.
docs/work/completed/*
!docs/work/completed/.gitkeep
docs/work/discarded/*
!docs/work/discarded/.gitkeep
```

The `dir/*` form is required: git cannot re-include a file whose *parent
directory* is excluded, so the existing `docs/work/completed/` (trailing slash)
form makes the `!…/.gitkeep` negation inert. The status names come from
`RESOLVED_STATUSES`, not a second hard-coded list.

### Mechanics

Extract the append-if-missing half of `ensure_worktree_ignored` into a shared
helper returning whether it wrote anything; `ensure_worktree_ignored` keeps its
`git_stage` call, and `init` does not stage — init stages nothing today (not the
sentinel, not the `.gitkeep`s), and many tests call `init()` on a `tmp_path` that
is not a repository at all.

Only the `work` component triggers it. Line-wise idempotence means a re-run is a
no-op, and a user who deleted the rules on purpose gets them back only if they
re-run init — accepted, same as `.worktrees/`.

## Acceptance criteria

1. In a fresh `tmp_path` git repo, `tcw init --id x work` leaves a `.gitignore`
   containing the four rules; `git check-ignore -q docs/work/completed/anything`
   exits 0 and `git check-ignore -q docs/work/completed/.gitkeep` exits non-zero.
2. Running init twice does not duplicate the rules.
3. `init(["taxonomy"], …)` writes no `.gitignore`.
4. An existing `.gitignore` keeps its content; the rules are appended.
5. A completion in such a node still untracks rather than moves (existing
   coverage in the earlier item's test) — unchanged.
6. This repo: `git ls-files docs/work/completed/.gitkeep docs/work/discarded/.gitkeep`
   lists both, and `git ls-files docs/work/completed | wc -l` is otherwise 0.
7. `pytest` green, `tcw validate` exits 0.
8. Both changed capabilities read `Supported` with bodies matching the new
   behavior.

## Risks

- **A node that deliberately tracks its resolved work.** Re-running init would
  re-add the ignore rules and silently start dropping items from the tree on the
  next completion. Mitigated only by the rules being visible in `.gitignore` and
  by init printing that it touched the file.
- **The `.gitkeep` exemption fooling someone into thinking the folder is
  tracked.** Accepted; it is what keeps the folder in a fresh clone.
