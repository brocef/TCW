# Spec — The claiming lookup globs with an unescaped slug

## Capability changes

None. No command gains, loses, or changes documented behaviour. `tcw work start`
stops destroying an item when handed a slug containing a glob metacharacter,
which is a defect being removed rather than a capability being altered.

## Problem

The request reports two things and calls them "a correctness and hardening item,
not a live exposure", on the grounds that `tcw serve` is localhost and
single-user so no untrusted caller reaches the store API.

**That assessment is wrong, and the request's proposed fix does not work.**
Everything below was reproduced at `f2ba258b`.

### 1. It destroys the item — through the store API

> **Corrected after verification.** This section first claimed the destructive
> case is reachable from the command line by an operator typing an unquoted `*`,
> and the item's priority was raised from 20 to 55 on that basis. **It is not.**
> `_start` in `tcw/work/cli.py:782` evaluates `st.get(bare)` as an argument to
> `run_pre`, before `st.start` is ever called; that read consults the same claim
> directories and raises `has an interrupted claim`, so `start` is never entered
> and the victim survives. Verified by driving the CLI against the pre-change
> source in a detached worktree.
>
> The original reproduction below is through the **store API**, which is what it
> always was. My "end to end through the CLI" check was run against the *fixed*
> code, where it correctly refuses, and I read that as confirming reachability
> when it confirmed nothing about it. The requester's own assessment — "no
> untrusted caller reaches the store API today" — was closer to right than my
> correction of it.

With one interrupted claim for `2026-01-01-axxxb-thing`, called directly on the
store:

```
start("2026-01-01-axxxb-th*g", owner="attacker@example.com", take_over=True)
```

`_claiming_dirs` (`tcw/store/fs.py:3665`) globs with the caller's slug unescaped,
so the wildcard matches the **victim's** claim directory. `len(interrupted) != 1`
passes. `start` then rewrites `owner` and `started` in the victim's `state.yaml`
(`:3565-3567`) and `os.replace`s it to `active/<the wildcard slug>` (`:3569`).
Only afterwards does `git_stage` fail on the pathspec, and the exception escapes
**after** the move. Observed end state:

| Before | After |
| --- | --- |
| `.claiming/2026-01-01-axxxb-thing-<uuid>` | `.claiming/` empty |
| `backlog/` empty (claim in flight) | `backlog/` empty |
| — | `active/2026-01-01-axxxb-th*g`, owner `attacker@example.com` |

The real item is gone, under a name nobody can address, and the command that did
it reported a `git` error rather than success.

`tcw serve` cannot reach this branch either: its start action
(`tcw/serve/__init__.py:870`) never passes `take_over`, and it resolves the slug
before calling the store at all.

### 2. The same glob breaks the ordinary path — and this half *is* CLI-reachable

Without `--take-over`, a wildcard slug cross-matches another item's claim, so
`start` treats a non-existent slug as a lost race. Measured: it stalls 0.63 s and
raises `2026-01-01-axxxb-th*g has an interrupted claim; use --take-over --owner
<identity>` instead of "no such work item". That is exactly the failure the
`_claiming_dirs` docstring already warns about for a loose glob — the warning is
about `-*` spanning `-`, and the same hole is open through metacharacters.

### 3. `_safe_store_id` is not the fix

The request says "the existing mechanism for exactly this question is already in
the codebase and simply not used here", naming `_safe_store_id` (`:1275`), and
proposes routing the slug through it. Run against the inputs that cause the
defect:

| Input | `_safe_store_id` |
| --- | --- |
| `a*b` | passes unchanged |
| `a?b` | passes unchanged |
| `a[0-9]b` | passes unchanged |
| `../x` | refused |

It rejects traversal, not pattern syntax. Routing the slug through it would
leave every case above exactly as it is. It also permits `/`, so it would let a
slug glob into a subdirectory.

## Goals

1. A slug containing a glob metacharacter matches only a claim directory whose
   name contains that character literally.
2. `tcw work start` with such a slug never moves, renames, or rewrites an item it
   was not given.
3. An item whose slug genuinely contains a metacharacter still finds its own
   claim, so recovery is not narrowed.

## Non-goals

- **Routing the slug through `_safe_store_id`.** It does not address the defect
  (see Problem 3). Adding it anyway would be cargo, and would newly refuse slugs
  the store can hold.
- **Replacing the glob with a directory scan.** `Path.glob` returns nothing for a
  missing directory; `Path.iterdir` raises `FileNotFoundError`. Commit `9cd69e83`
  — the item immediately before this one — documents `.claiming` being absent or
  empty as one state *because* glob is blind to the difference. A scan would have
  to re-add that guard, so it trades a free property for a line of code.
- **Symlink containment.** Explicitly out of scope in the request, and still is.
- **Reworking the take-over branch's path composition.** Deriving the slug back
  from `interrupted[0].name` is sensible and is done, but as defence in depth; it
  is redundant once the glob is escaped, and the escape is what closes the hole.

## Design

**One line.** In `_claiming_dirs`:

```python
return sorted((self.root / ".claiming").glob(
    glob.escape(slug) + "-" + "[0-9a-f]" * 32))
```

`glob.escape` wraps only `*`, `?` and `[` in character classes. The `[0-9a-f]`
suffix is concatenated **after** escaping, so it stays a pattern of ours while
the caller's slug becomes a literal. Verified:

| Probe, against a claim for `2026-01-01-axxxb-thing` | Today | Escaped |
| --- | --- | --- |
| the real slug | 1 match | 1 match |
| `2026-01-01-axxxb-th*g` | **1 match** | 0 matches |
| a claim for the literal slug `item-a*b` | 1 match | 1 match |

**Second line, defence in depth.** In the take-over branch, derive the destination
from the claim directory that was actually found rather than from the caller's
string:

```python
slug = interrupted[0].name[:-33]        # strip "-" + 32 hex
```

Redundant once the glob is escaped — the escaped pattern can only match a
directory whose name begins with the literal slug — but it makes the invariant
local: the path published is the path found, not the path asked for.

### Why recovery cannot narrow

The request's stated constraint is that "a stricter lookup that matches nothing
is its own failure mode", and that the recovery semantics need deciding first.
They do not need deciding, because nothing narrows:

A claim directory is created in exactly one place, `:3627`, as
`claiming / f"{slug}-{uuid4().hex}"`, and only after `_find(slug)` returned a
folder whose name is exactly that slug. So every claim directory on disk is named
for a literal slug, and an escaped pattern built from that same literal matches
it. A slug containing `*` still finds its own claim — verified above. The only
matches lost are *other items'* claims, which is the defect.

## Acceptance criteria

Each is executable against a scratch store.

1. With one interrupted claim for `2026-01-01-axxxb-thing`,
   `start("2026-01-01-axxxb-th*g", owner=..., take_over=True)` raises
   `no recoverable interrupted claim`, and afterwards the claim directory is
   still in `.claiming`, `active/` holds nothing, and the victim's `state.yaml`
   still names its original owner. Today this empties `.claiming` and leaves
   `active/2026-01-01-axxxb-th*g`.
2. `start("2026-01-01-axxxb-th*g", owner=...)` without `--take-over` raises
   promptly and does **not** report an interrupted claim. Today it stalls about
   0.6 s and does.
3. A claim for an item whose slug literally contains `*` is still found by
   `_claiming_dirs` with that exact slug, and `--take-over` still recovers it.
4. `--take-over` on a genuine interrupted claim still works unchanged: the item
   lands in `active/<slug>` with the new owner.
5. `_claiming_dirs` on a store with no `.claiming` directory returns `[]` and
   raises nothing — the invariant `9cd69e83` documented.
6. `_claiming_dirs` still refuses to answer for a shorter slug when a longer one
   has a claim, which the existing test at
   `tests/test_external_work_store.py:377` covers.
7. `pytest` passes with no fewer than the `2617` baseline.

## Risks

- **The take-over branch's second line changes what `slug` names mid-function.**
  Reassigning the parameter is the smallest edit but the least readable; a
  separate name is clearer and is what the implementation should use.
- **`glob.escape` is platform-sensitive on drive letters.** On Windows it leaves
  a drive prefix unescaped. Irrelevant here — the value is a single path segment
  under `.claiming`, never a rooted path — but worth knowing before the same
  call is copied somewhere it does receive a full path.
- **This is the second of two items touching claiming in one run.** The first
  (`2026-08-20-docs-work-claiming-is-created-by-every-start-and-never-removed`)
  made `.claiming` absent-or-empty a documented invariant, and this item's
  rejected scan-based design would have broken it. That interaction is why the
  combined difference of the two gets its own review pass before either is
  called done.

## Notes

- Line citations are against `f2ba258b`.
- **The request's exposure assessment should be read as superseded, not wrong to
  have made.** It was the requester's answer at the `request` stage and is
  labelled as such. It rests on who can reach the store API; the reproduction
  above needed only the CLI and an unquoted wildcard.
- **Priority.** Raised from 20 to 55 at the spec stage on the belief that this
  was data loss reachable by a typo. That belief was wrong; see the correction
  above. What remains is data loss reachable only by a direct store-API caller,
  plus a CLI-reachable defect that misreports a missing item as an interrupted
  claim after a stall. **Lowered to 35** — above the original 20, because a
  destructive path in the store API is worth closing and the CLI half is a real
  if minor misreport, and well below 55, because nothing a user types can reach
  the destructive branch.
- **The severity claim was asserted before it was tested.** The lesson is narrow
  and worth stating: a reproduction through one entry point says nothing about
  another, and "I ran the CLI" means nothing if the run was against the fixed
  code.
