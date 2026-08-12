# Stop a claim loser from stealing the winner's published item

Found by CI on the first push of
`2026-06-22-concurrency-safe-work-claims-for-multi-agent-repos-configurable-work-path-atomic-owner-stamp`,
and by the stress test that item added. That item was accepted and completed;
`completed` is terminal, so its residue is tracked here rather than by reopening
it. Its acceptance was premature — see "Correction" below.

## Product changes

Three ways concurrent use still misbehaves, in descending severity.

1. **Two agents can both successfully claim the same item.** The single-winner
   invariant — acceptance criterion 1 of the completed item — is violated in
   roughly 1 round in 20 with four contenders. Both callers return success, both
   reporting the *same* owner, and each believes it holds the item.
2. **A board read can crash with `MultipleMatch`** while any item is being
   claimed, reporting "slug resolves to 2 items" for an item that is perfectly
   healthy.
3. **A board read can crash with `FileNotFoundError`** when a claim moves a
   folder while the scan is walking it.

## Technical changes

### 1. The steal (`tcw/store/fs.py`, `start()`)

`src = self._find(slug)` searches *every* status folder. Between `start()`'s
opening status read and this claim lookup, the winner can publish to `active/` —
and `os.replace(src, private)` then renames the winner's **already-published**
item into the loser's private claiming area. It succeeds, because nothing in the
protocol says a claim may only take an item out of `backlog`.

With more than two contenders each one steals from the last and republishes, so
every caller ends up re-reading the same final state through `_require()`. That
is why all of them return a `WorkItem` with an identical owner and `started` —
the tell that first made this look impossible.

Fix: a claim moves an item out of `backlog` and nowhere else. `_find` returning
anything outside `backlog` means the race was lost, and routes to the existing
recovery.

### 2. `MultipleMatch` on a transition in flight (`_find`)

`_item_dirs` walks the status folders in order, so an item moving from an
earlier-scanned folder to a later one — `backlog` → `active`, i.e. every claim —
is counted in the folder it left *and* the folder it entered. One item at two
instants, reported as two items.

Fix: re-walk before concluding. A genuine duplicate survives a re-walk; a
transition does not.

### 3. `FileNotFoundError` from the walk (`_item_dirs`)

`rglob` reaches each directory through `scandir`, which raises rather than
skipping when the directory has gone — so one item leaving `backlog` mid-scan
takes down a read of the whole board. This is upstream of every per-item guard
the completed item added, which is why those guards did not cover it.

Fix: retry the walk, bounded.

## Correction to the completed item

`2026-06-22-…-atomic-owner-stamp` records in its `outcome.md` an enumeration of
the `_find` windows that classified `query()` → `_item_from_dir` as "same window,
same fix". That was wrong: the *scan* has two failure modes the per-item read
never sees, and the claim lookup had a third that is not a read at all. The
enumeration was of reads, and it stopped at the reads.

Its `refined-outcome.md` also states that the deterministic tests were the real
evidence and the stress test only mattered on constrained CI schedulers. The
first half held; the second was too generous to the deterministic set. The
stress test found the severe defect, and found it locally once contention went
from two contenders to four.

## Notes

The completed item's acceptance stands for what it delivered — the read windows
it closed are closed. What it did not deliver is the invariant its criterion 1
claims, and that is this item's job.
