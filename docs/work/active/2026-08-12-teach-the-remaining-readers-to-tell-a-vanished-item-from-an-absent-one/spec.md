# Teach the remaining readers to tell a vanished item from an absent one — Specification

## Capability changes

No capability-ledger change is required. This restores concurrency safety promised by the existing work lifecycle.

## Problem

An atomic claim temporarily moves an item from `backlog/` into adapter-private `.claiming/` before publishing it in `active/` (`tcw/store/fs.py:2036-2089`). During that interval, ordinary `get()` returns `None`. Storage-neutral base operations interpret `None` as permanent absence: `_entry_for` stores an existing blocker as external, while `unresolved_blockers` silently treats a temporarily missing blocker as resolved (`tcw/store/base.py:1192-1196`, `tcw/store/base.py:1278-1293`).

`get_detail` has an additional find-then-read window: after locating a directory it reads `state.yaml` without retry, so a concurrent claim can surface `FileNotFoundError` through the web API (`tcw/store/fs.py:2897-2921`).

The filesystem claim directory cannot leak into `WorkStore`. The abstract meaning of `get` remains “return the current item or None if absent”; an adapter may stabilize a transient move before answering.

## Goals

- Make filesystem reads wait briefly only when there is evidence that the requested slug is in an in-flight claim.
- Ensure base blocker operations receive the settled item rather than false absence.
- Make detail reads return a settled detail, `None` for genuine absence, or a domain error for an interrupted claim—never a raw filesystem traceback.
- Preserve the policy that a genuinely deleted blocker no longer blocks.
- Avoid recursive 500 ms waits in lost-claim detection.

## Non-goals

- Exposing `.claiming/` through `WorkStore` or adding filesystem-specific interface methods.
- Adding locks or transactions to the abstract store.
- Changing claim publication, takeover, owner, or transition semantics.
- Treating genuinely deleted blockers as unresolved.
- Hiding arbitrary filesystem corruption or permission failures.

## Design

### Stabilize `FsWorkStore.get`

Keep `WorkStore.get` unchanged. Split the filesystem adapter's current item lookup into a private immediate probe and a public stable read:

- `_get_now(slug)` performs the existing `_find` plus state decoding once and never waits.
- `get(slug)` calls `_get_now`. If it finds an item, return it. If not and an exact `_claiming_dirs(slug)` entry exists, poll `_get_now` for up to the existing 500 ms publication window. Return the published item, or raise a domain-level interrupted-claim error when the claim remains private. If neither item nor claim evidence exists, return `None` immediately.

A non-filesystem adapter can continue implementing `get` transactionally; the model gains no claim concept. `_lost_the_claim` must poll `_get_now`, not `get`, preventing each of its 50 iterations from nesting another wait.

Use one domain error/message for an abandoned private claim so CLI and HTTP layers can translate it consistently. `AlreadyClaimed` remains specific to a competing `start`, not an ordinary read.

### Claim-recovery paths must keep the immediate probe

A stable `get` is correct for callers asking *"what is this item?"* and wrong for
the callers whose whole job is to handle the unstable state. Two of them exist,
and both read through `get` today:

- **`start(..., take_over=True)`** recovers an abandoned claim by observing
  `get(slug) is None` and then looking in `.claiming/` (`tcw/store/fs.py:1993-2000`).
  A `get` that raises on exactly that state makes the recovery branch
  unreachable — `--take-over`, the documented remedy for an interrupted claim,
  would stop working the moment there is something to recover.
- **`unresolved_blockers`** calls `get` per blocker (`tcw/store/base.py:1284`).
  A blocker mid-claim must settle and then block; a blocker whose claim was
  *abandoned* must still report as a blocker, not convert `start(B)` into a
  raised error about some other item.

So: `_get_now` is the read for `start`'s take-over probe, for `_lost_the_claim`,
and for the blocker loop's error handling — the stable `get` supplies the
settled-value case, and the caller decides what an unsettled claim means to it.
That distinction is storage-neutral: a transactional adapter draws the same line
between "read the committed value" and "inspect an in-flight transaction".

### Consequence for the abandoned-claim error

Because the recovery callers no longer route through it, the domain error raised
by `get` is reachable only from plain reads (`show`, `get_detail`, the web API).
That is the intent — it names a state the reader cannot resolve and points at
`--take-over` — but it means the error's blast radius must be enumerated in the
implementation, not assumed: every `self.get(` in `base.py` and `fs.py` is a
caller whose behavior changes from "returns None" to "raises" for one input.

### Harden composite detail reads

`get_detail` should build a snapshot in a bounded retry loop. Each attempt obtains a stable item, finds its directory, and reads state/body/artifacts/sidecars. If the directory or one of those files vanishes because the item moved, restart from stable lookup. A genuine absence returns `None`; exhausted evidence of an interrupted claim raises the domain error. Permission errors, malformed YAML, and other corruption still surface.

The returned `WorkDetail.item` and revisions must come from the same successful directory snapshot. Do not return the first item paired with files from a later status.

### Base behavior

No changes are needed in `_entry_for` or `unresolved_blockers` once adapter `get` fulfills stable-read semantics. Keeping those methods storage-neutral preserves the abstraction and ensures every current and future base caller benefits.

## Acceptance criteria

- While blocker A is privately held in `.claiming/`, `start(B)` does not start B without `--force`; after A publishes active, B reports A as unresolved.
- `create_work(..., blockers=[A])` during A's claim records `{"slug": A}`, not `{"external": A}`.
- A blocker genuinely absent before and after the read retains current semantics: new input becomes external and a previously stored missing slug no longer blocks.
- `FsWorkStore.get("missing")` returns `None` without a 500 ms delay when no exact claim exists.
- Prefix-related claim directories do not delay or affect another slug.
- An abandoned exact claim raises the documented domain error after the bounded wait.
- `tcw work start <slug> --take-over --owner <id>` still recovers an abandoned exact claim, with no `--force`, and does not raise the interrupted-claim error before reaching the recovery branch.
- With an abandoned claim on blocker A, `start(B)` reports A as a blocker rather than raising A's interrupted-claim error.
- `_lost_the_claim` completes in roughly one bounded window rather than multiplying nested waits.
- A `get_detail` race with `start` returns a consistent detail or a translated not-found/conflict response, never `FileNotFoundError` or a traceback.
- Existing high-contention single-winner and takeover tests remain green.

## Risks

- Adding waiting to a hot read can hurt latency. The wait is conditional on exact claim evidence; ordinary hits and misses remain immediate.
- Over-broad claim matching could block unrelated slugs. Existing exact UUID-suffix matching remains mandatory.
- Retrying a composite read can combine revisions if implemented piecemeal. Each failed attempt must discard all collected values.
- Swallowing all `FileNotFoundError` would hide corruption. Retry only disappearance of paths within the located item during a detected move window.
