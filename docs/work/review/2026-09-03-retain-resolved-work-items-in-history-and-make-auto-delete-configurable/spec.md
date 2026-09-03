# Spec — Retain resolved work items in history, and make auto-delete configurable

## Capability changes

- **changed** — `work/keep-resolved-work-out-of-git`. Its body describes today's
  only behavior — gitignoring the resolved status folders — as "the default".
  After this item that is one of three retention modes, and the one that keeps a
  resolved item off every other machine. The capability is the contract and has
  to say which mode a user is in and what each costs them.
- **changed** — `work/complete-a-work-item` and `work/discard-a-work-item`, if
  their bodies describe what becomes of the item's folder. Under auto-delete a
  resolving transition writes two commits instead of one, which is user-visible
  in `git log`. Confirm at implementation and drop from `capabilities.yaml` if
  neither body makes the claim.

No new capabilities: this changes what an existing operation does, and the new
`auto-delete` step is the *next* item.

## Problem

**A resolved item is not deleted, and it does not travel.** `git_mv`
(`tcw/store/fs.py:487-521`) checks whether the destination is gitignored, and
when it is, untracks the source and moves it outside git:

    if git_ignored(node_root, dst):
        ...
        _git(["git", "-C", str(node_root), "rm", "-rqf", "--cached",
              "--ignore-unmatch", "--", str(src)], check=True)
        shutil.move(str(src), str(dst))
        return

`resolved_ignore_rules` (`:720-731`) is what makes that branch fire, and
`tcw work init` writes those rules by default (`:903`). The result is that the
folder accumulates on the resolving machine forever, untracked, and reaches no
other clone. Verified against a provisioned checkout of a real orchestration
repository in session: `docs/proposit-server/work/completed` holds nothing, and
`tcw validate` there reports `tcw://W/…` references to resolved items as
`no such work item`. The provisioner clones with a plain `git clone`
(`tcw/store/fs.py:2961`) with no depth limit, so history *would* be reachable —
there is simply nothing in it.

So the present behavior is the worst of both: the tree is clean, the disk is not,
and the record is on exactly one machine.

**The pieces the request depends on already exist.** The graveyard is tracked
unconditionally and documented as never gitignorable (`tcw/store/fs.py:3064-3069`):
"an ignorable graveyard is invisible in exactly the clones that need it, which is
the defect it exists to fix". `_unique_slug` consults it so a resolved slug can
never be reissued (`:3595-3605`). And `tcw capabilities drift` already answers
from the tombstone rather than the local tree (`tcw/capabilities/cli.py:223-236`),
so the one known reader of `completed/` does not regress when the folder is
emptied.

**Nothing expresses retention.** There is no configuration for it; the only lever
is whether the user's `.gitignore` happens to contain the rules, which is a git
fact rather than a project decision, and which no store but the filesystem one
could honor.

## Goals

- `tcw-config.yaml` declares retention per resolved status.
- The default retains everything, and an existing project's behavior is unchanged
  until it says otherwise.
- Under auto-delete, a resolving transition lands the item in its resolved status
  folder in one commit and removes it in a second, so the content is in history.
- The graveyard entry records the commit in which the item was last present.
- `tcw work show` on a resolved slug reports the tombstone and where the content
  can be retrieved, rather than reporting nothing.

## Non-goals

- **The archive hook.** [An auto-delete step with hooks](tcw://W/2026-09-03-an-auto-delete-step-with-hooks-so-a-consumer-can-archive-an-item-before-it-is-removed)
  is a separate item that depends on this one.
- Changing what `tcw work drop` does. It deletes a backlog item with no record
  kept, which is a different operation with a different promise.
- Migrating any existing project. The migration path is documented; running it
  is the project's decision.
- Deleting anything a user already has on disk. Whatever is sitting in
  `completed/` today stays there.

## Design

**Three modes, and the interlock between two of them.**

| mode | tracked in the resolved folder | on disk after | recoverable from |
| --- | --- | --- | --- |
| gitignored | no | yes, untracked | the resolving machine only |
| `retain` | yes | yes | tree and history |
| `auto-delete` | one commit, then removed | no | history and the graveyard |

**`auto-delete` and the gitignore rules cannot coexist, and this is the sharpest
finding in the spec.** With the rules in place, `git_mv` untracks rather than
moves, so the first commit records a *deletion* and holds no content; the second
commit then removes the folder from disk. The graveyard would point at a commit
containing nothing, and the item would be gone from every machine — strictly
worse than today, where at least one copy survives. So a resolving transition
under `auto-delete` must refuse while the destination is gitignored, naming the
`.gitignore` lines to remove. Dropping those rules is a precondition of the
feature, not a companion change.

**Retention is expressed as retention.** The configuration names what happens to
the item, not what happens to git:

    work:
        retain:
            completed: true      # default
            discarded: true      # default

with `false` meaning auto-delete. This passes the litmus test: a tracker-backed
store honors "do not retain resolved items" by closing and dropping the ticket,
while `.gitignore` has no analog anywhere but a filesystem. The ignore rules
become one adapter's realization of the gitignored mode, and
`tcw work init` stops writing them when the project has declared retention.

**Two commits, and the order that makes them safe.** The resolving transition
already commits (`_commit_transition`); auto-delete adds a second commit after
it. The graveyard write must land in the *first* commit, before the content is
removed — a crash between the two must leave a recorded item sitting in its
resolved folder, which is a recoverable state, and never an unrecorded deletion.
The SHA of that first commit is what the graveyard entry records, so it names a
commit that demonstrably contains the item.

Recording the SHA needs one field on the tombstone. It is adapter-specific in
*content* — a tracker would record its own retrieval handle — so the abstract
shape is "where this item can be retrieved", carried as an opaque string the
adapter writes and the presentation layer prints without parsing, exactly as
`WorkStore.locate` is already handled (`tcw/store/base.py:732-735`).

**Publication.** On a provisioned store both commits must be pushed. The push
happens after the move today (`tcw/store/fs.py:4192`); with two commits it runs
after the second, so a push failure leaves both locally and the existing "your
work is saved here" message stays true.

**Harness.** Configuration and CLI only; identical under both.

## Acceptance criteria

1. A project declaring nothing behaves exactly as it does today, asserted by the
   existing resolution tests passing unchanged.
2. `work.retain.completed: true` on a node whose `.gitignore` still carries the
   rules keeps today's untracking, and `tcw validate` reports the combination as
   a conflict — the project says retain, git says otherwise.
3. `work.retain.completed: false` on a node whose `.gitignore` carries the
   resolved rules causes `tcw work complete` to refuse before moving anything,
   naming the lines to remove.
4. With the rules removed and `retain.completed: false`, completing an item
   produces exactly two commits: the first containing the item's files under
   `completed/`, the second removing them.
5. After that, the item's folder does not exist on disk, `tcw work list` does not
   show it, and `tcw work show <slug>` reports the tombstone including the first
   commit's SHA.
6. `git show <sha>:<path>` retrieves the item's `spec.md` for that SHA and path.
7. The slug cannot be reissued: `tcw work new` with the same date and title
   produces a suffixed slug.
8. `tcw capabilities drift` reports a capability whose planning doc was
   auto-deleted exactly as it does for one that was retained.
9. A crash simulated between the two commits leaves the item in `completed/`,
   recorded in the graveyard, and re-running the transition completes the
   deletion rather than erroring.
10. On a provisioned store, both commits reach the remote.
11. `tcw validate` accepts a malformed `work.retain` with a message naming the
    line, and does not fall back to a default silently.

## Risks

- **History becomes the only copy.** Under auto-delete, a squash of the store
  repository, or a shallow clone, loses the content and leaves only the slug and
  a SHA that resolves to nothing. The requester has accepted this explicitly. The
  SHA field limits the damage where history survives; nothing limits it where it
  does not, and the documentation must say so rather than implying the record is
  durable.
- **A project can configure away its own record.** `retain: false` plus a
  squash-merge workflow is a supported configuration that quietly keeps nothing.
  Refusing it is not possible — TCW cannot see the merge policy — so this is a
  documentation and default-value problem, which is why the default retains.
- **Two commits are two chances to fail.** The failure window between them is
  new. Criterion 9 exists because "recorded but not yet deleted" must be a state
  the system can finish from, not one a user has to repair by hand.
- **Existing projects have both the rules and years of untracked folders.**
  Nothing in this item touches them, which means a project that flips to
  `retain: true` starts tracking new resolutions while its old ones stay
  invisible. That asymmetry is permanent unless someone migrates deliberately.
- **Adopters with no graveyard at all.** Boards that predate the graveyard — the
  `proposit-*` stores among them — have no `graveyard.yaml`, so their historical
  slugs are reissuable. Auto-delete on such a store is safe for items resolved
  from now on and does nothing for the ones already gone. `tcw work tombstone add`
  is the backfill, and the migration note must say to run it first.

## Notes

The two-commit shape is the requester's, and the reason it works is that the
graveyard was already built to be the durable half: it is deliberately not
gitignorable, and `_unique_slug` already treats it as authoritative for slug
collisions in a clone that never held the item. This item makes the content half
as durable as the slug half, in the one place it can be.

The sequencing constraint worth carrying to the plan: task order must put the
refusal (criterion 3) before the two-commit path exists, so no intermediate
commit can produce a contentless deletion on a real user's store.
