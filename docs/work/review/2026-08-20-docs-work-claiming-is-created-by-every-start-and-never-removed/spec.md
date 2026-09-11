# Spec — The leftover claiming directory

## Capability changes

**None declared, and that is a judgment rather than an omission.** The
user-visible effect this fixes belongs to `cli/point-tcw-at-a-project-i-already-have`
and `work/configure-the-work-store-location`, but neither description promises
anything this changes: they say a default store is replaced when it is pristine,
and after this change a store that *is* pristine is correctly recognized as such.
The capability was always true; the code did not implement it. No ledger delta.

## Problem

The intake reports that `FsWorkStore.start` creates `docs/work/.claiming/`
(`tcw/store/fs.py:3613-3614`) and nothing removes it, so a node accumulates an
empty directory the first time anyone starts an item. It calls this "harmless in
itself" and grounds the item in a test annoyance.

**The intake is wrong about both the symptom and the harm.**

**The symptom.** It says the leftover directory "invalidates the obvious
assertion — `assert not (root / "docs/work/.claiming").exists()` — which passes
for the wrong reason on any node that has ever started an item." On such a node
that assertion *fails*; it passes vacuously on a node that never started one.
The muddle matters because it is the whole stated justification.

**The harm is real, but it is somewhere else.** `init` decides whether a default
store may be replaced by comparing the work root's entries against an exact set
(`tcw/store/fs.py:917-926`):

```python
expected = {"inbox", *WORK_STATUSES}
actual = {entry.name for entry in default_root.iterdir()}
pristine = ... and actual == expected and all(...)
```

A leftover `.claiming` puts an extra name in `actual`, so `actual == expected` is
false and `tcw init --work-path <elsewhere>` refuses:

```
tcw init: refusing to replace non-pristine …/docs/work; move existing work
manually, update work.path, then re-run init
```

Reproduced at `60c8b857` on two nodes identical in every other respect. On a
fresh node the relocation succeeds. Creating `.claiming` — the only change, no
work items at all — makes it refuse; removing that one directory makes it
succeed again. So a user who started a single item at any point in the past, then
later moves their work store to another repository, is told to "move existing
work manually" when there is no work to move and nothing they can see.

## Goals

1. `tcw init --work-path <elsewhere>` relocates a default store whose only
   non-standard entry is `.claiming`.
2. The invariant that `.claiming` actually carries is written down, so the next
   reader does not re-derive it or assert the wrong thing.

## Non-goals

- **Removing the directory after a successful claim.** This is the obvious fix
  and it is wrong; see **Design**.
- **Restructuring the claim to avoid a shared parent.** Also considered and
  rejected; see **Design**.
- **Anything about `_claiming_dirs` and unvalidated slugs.** That is
  `2026-09-09-validate-a-slug-before-the-claiming-lookup-globs-with-it`, the next
  item in this run. The two touch the same area and their combined difference is
  reviewed together, but they are separate mechanisms.

## Design

**One line: drop `.claiming` from the pristine comparison.**

```python
actual = {entry.name for entry in default_root.iterdir()} - {".claiming"}
```

`.claiming` is an adapter-private staging area. Its presence says nothing about
whether a store holds work, which is what the pristine check is asking.

### Why the directory is not removed

The obvious fix — `rmdir` after a successful claim, suppressing the error when
another claim is in flight — was proposed, analysed, and rejected on three
independent grounds. Both advisors reached the same conclusion separately.

1. **It introduces a race whose failure mode is a lie.** `os.replace` into a
   missing destination parent raises `FileNotFoundError` — verified directly,
   and POSIX `rename` returns `ENOENT` for a missing destination parent. Process
   A finishing its claim and removing the now-empty directory, between process
   B's `mkdir(exist_ok=True)` (`:3614`) and B's `os.replace` (`:3629`), makes B
   take the `except FileNotFoundError` branch into `_lost_the_claim`. That loops
   fifty times at 10 ms waiting for the item to appear in `active`; it never
   does, because nobody claimed it. B stalls half a second and reports
   `has an interrupted claim; use --take-over --owner <identity>` about an item
   sitting untouched in `backlog`.

2. **The race is not rare in this project's own usage.** A and B need not be
   claiming the same slug. Two agents starting *different* items is the ordinary
   case here, and it is exactly the case where both claims would otherwise
   succeed. The fix would convert a working concurrent start into a spurious
   corruption report.

3. **It would not even buy the invariant it pays for.** A claim leaves the
   private directory by three different renames — the ordinary publish
   (`:3639`), the take-over publish (`:3561`), and the rollback that puts the
   item back (`:3641`). A `rmdir` at one of them leaves the directory behind at
   the other two, so the "always cleaned up" property would still be false.

A single retry does not close the race either: another completing claimant can
remove the recreated directory before the retry's rename. Closing it properly
needs a contention policy over directory creation, rename and removal.

### Why the claim is not restructured

Staging as a dotted sibling of the work root — `root / f".claiming-{slug}-{uuid}"`
rather than `root / ".claiming" / f"{slug}-{uuid}"` — removes the shared parent
entirely, so the rename's destination parent is the work root, which
`FsWorkStore.open` has already validated. Nothing is created and nothing is
removed, so the directory has no lifetime to race against.

Rejected anyway. It rewrites the most safety-critical function in the store plus
roughly a dozen tests that construct `.claiming/` by hand, and an interrupted
claim written by an older version becomes unrecoverable by `--take-over`,
because `_claiming_dirs` would no longer look where that claim is. Real churn
and a migration hazard for a cosmetic gain.

### The invariant, written down

> `.claiming/` is a staging area whose **contents** are the state. Its own
> existence means nothing: it is created on demand and never removed, so a node
> that has ever started an item has it forever, empty.

Every consumer inside the store already behaves this way. `_claiming_dirs`
(`:3649-3658`) reaches the directory through `Path.glob`, which returns an empty
iterator for a missing directory rather than raising — verified. So "absent" and
"empty" are already indistinguishable to every reader that matters. This
documents the design; it does not excuse a defect.

The one place that treated existence as meaningful is the pristine check, and
that is the bug being fixed.

## Acceptance criteria

1. On a node whose `docs/work/` holds only the standard entries plus an empty
   `.claiming`, `tcw init --work-path <other repo>` succeeds and relocates the
   store. It refuses today.
2. On the same node without `.claiming`, it still succeeds — no regression.
3. A node whose `docs/work/backlog/` holds a real item is still refused as
   non-pristine, with the unchanged message. `.claiming` is the only name
   forgiven.
4. A node holding both a real item and `.claiming` is still refused.
5. `FsWorkStore.start` is unchanged. `git diff` touches no line of it.
6. `tests/test_non_git_writes.py:190` keeps its fresh-node fixture and its
   `assert not claiming.exists()`. That test checks a refused command creates
   **nothing**, so absence is the right assertion there and the fresh node is
   the right fixture — not a workaround to be removed. Its docstring is
   corrected only where it explains *why*.
7. The invariant above appears in a docstring on `_claiming_dirs`.
8. `pytest` passes with no fewer tests than the `2617` baseline.

## Risks

- **Forgiving a name in a safety check is a small hole.** The check exists to
  refuse deleting someone's work. `.claiming` can hold a real item mid-claim —
  that is what it is for — so forgiving the *name* while ignoring the contents
  could delete a claim in flight. Mitigated by criteria 3 and 4, and by the fact
  that a mid-claim item is by definition in a concurrent `start` on the same
  node, where `init --work-path` has no business running. Worth stating rather
  than assuming: this forgives a name, not a directory's contents.
- **The item's premise is corrected rather than accepted.** The intake says
  harmless-but-annoying; this spec says the annoyance is misdescribed and the
  real harm is a refused relocation. Anyone reviewing against the intake will
  find the scope unrecognizable, which is why the Problem section reproduces
  both.
- **This is one of two items touching claiming in the same run.** Their combined
  difference gets its own review pass, per this repository's rule that an
  interaction only reachable once both have landed is the kind of thing no
  single-item review finds.

## Notes

- Line citations are against `60c8b857`.
- The intake's own framing — "harmless in itself" — is why this sat at no
  priority for three weeks. The cost of a misdescribed symptom is that nobody
  can weigh the item.
