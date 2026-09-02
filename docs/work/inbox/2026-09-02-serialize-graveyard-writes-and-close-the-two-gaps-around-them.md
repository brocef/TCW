# Serialize graveyard writes, and close the two gaps around them

## Desired outcome

Three things the tombstone item left open, grouped because the first is the
substantial one and the other two are small enough that opening separate items
for them would cost more than it saves.

1. Two agents resolving different items at the same time cannot lose a tombstone.
2. `tcw://W/completed/<slug>` resolves the same way `tcw://W/<slug>` does.
3. `tcw work tombstone add` gets the record to the other clones it exists for.

## Context

All three came out of the adversarial review of
`2026-09-02-tombstone-resolved-work-items-so-references-to-them-stay-resolvable`,
and were independently confirmed by a second reviewer in two of the three cases.
The prose that claimed otherwise has been corrected in that branch; the code has
not.

### 1. The graveyard write is not concurrency-safe

`_require_writable_graveyard` runs before the move (`tcw/store/fs.py`, in
`_effect_transition`), `_write_tombstone` runs after it, and `_commit_transition`
runs after that. The state checked at the first step is not held at the second
or third, and this store is explicitly multi-agent (`docs/work/.claiming/`).
Three outcomes, in decreasing order of severity and increasing order of window
size:

- **Lost update.** Both processes pass the check while the file is clean, both
  read the same mapping, and the second write drops the first one's entry. The
  item stays in `completed/`, committed, with no tombstone anywhere — after
  which `_unique_slug` can hand its slug to a new item and every existing
  `tcw://W/<slug>` reference silently retargets to different work. Window: one
  YAML parse plus one atomic write.
- **Spurious refusal with a destructive remedy.** The second process sees the
  first one's staged-but-uncommitted graveyard and refuses with a message
  telling the user the changes are "someone else's — commit or discard them".
  A user who follows that advice and runs `git checkout --` on the file destroys
  the first item's record while its folder has already moved. Window: several
  subprocess round-trips, so much wider than the lost update.
- **Absorption.** The second process's commit carries the first one's entry
  under its own message. Nothing is lost; the attribution is wrong.

The fix is a lock held across check, write and commit. `.claiming/` already
establishes the atomic-directory idiom in this store, so the mechanism exists and
does not need inventing.

### 2. The status-path spelling still depends on local residue

`resolve_qualified_work_ref` (`tcw/store/fs.py:315-323`) takes the status-path
branch for `tcw://W/completed/<slug>`, calls `store.get(bare)`, and returns
`None` when the folder is absent — returning before `tcw/refs.py` ever asks for a
tombstone. So that spelling still fails in a fresh clone and resolves on the
machine that completed the item, which is the exact defect the tombstone item
set out to remove. Its Goal 1 is written without qualifying the spelling.

No such reference exists in this repository today, so this is a coverage gap
rather than an active fault.

The wrinkle that makes it more than a mechanical fix: the status segment has to
be checked against something. A tombstone's `resolution` implies the status —
`done` means `completed`, and `wontfix`/`duplicate`/`superseded` mean
`discarded` — but `tcw work tombstone add` may record an empty resolution,
and then the segment cannot be verified at all. Decide what a
`tcw://W/completed/<slug>` reference should do against a tombstone with no
recorded resolution before writing the code.

### 3. `tombstone add` commits but never publishes

Every transition calls `_refresh_before_transition` first and
`_publish_after_transition` after. `record_tombstone` does neither. On a
provisioned store — the feature the two backfilled items added — `tcw work
tombstone add` prints `recorded …` and the record stays on that machine until
some later transition happens to push it. The plan said the command would commit
"the way TCW commits a transition"; publication is the half of that which
actually gets the record to the clones it exists for.

## Constraints

- Deliberately not fixed in the tombstone item itself. Item 1 needs a locking
  mechanism that is a change in its own right; item 2 needs a decision about
  unrecorded resolutions before any code; item 3 adds a network side effect to a
  command that currently has none, which is a behaviour change worth stating
  rather than slipping in.
- `_publish_after_transition`'s failure message is written for an item that
  moved ("`<slug>` moved to `<status>` and was committed …"). A backfill has no
  move, so reusing it verbatim would print something false — item 3 needs its
  own wording, not just the call.
- Item 1's fix must not make the single-agent path slower or more fragile; the
  overwhelmingly common case is one agent, no contention.
- Item 3 has a test to add with it: `tcw work tombstone add` is absent from
  `TRANSITIONS` in `tests/test_store_publication.py:189`, which is the list that
  would have caught the missing publish. It is deliberately not added yet,
  because the test would fail — the command does not publish. Add the entry in
  the same change that makes it publish, not before.
