# Spec — Tombstone resolved work items so references to them stay resolvable

## Capability changes

Planned ledger deltas. No records are written at this stage.

| Capability | id | Delta |
| --- | --- | --- |
| `cli/validate-a-node` | cap-2bd014 | **Amend.** A `tcw://W/` reference to an item this store once held and has since resolved is no longer a validation problem. Add the reproducibility promise: the verdict depends only on tracked content. Status stays **Supported**. |
| `cli/reference-a-tcw-object` | cap-65e549 | **Amend.** A reference to a resolved item resolves, rather than failing as if the slug never existed. `tcw serve` renders it as resolved-and-archived, not broken. Status stays **Supported**. |
| `work/complete-a-work-item` | cap-24543d | **Amend.** Completing records a tombstone, so references to the item keep resolving after its documents leave the tracked tree. Status stays **Supported**. |
| `work/discard-a-work-item` | — | **Amend.** Same sentence as completion. Status stays **Supported**. |

No new capability and no status flips: every one of these already promises the
behaviour a user expects, and this item makes the code match.

## Problem

A `tcw://W/<slug>` reference to a completed or discarded item is reported
identically to a reference to a slug that never existed —
`no such work item: <slug>` (`tcw/store/fs.py:347`, reached from
`tcw/refs.py:132-134`, where a W ref fails when `store.get(bare) is None`).

But the sharper defect is that **the answer is not reproducible across
checkouts.** `completed/` and `discarded/` are gitignored by default
(`.gitignore:28-32`), and completion *moves the item's folder there on disk*
rather than removing it. On the machine that ran `tcw work complete` the folder
is still present, so `get()` resolves it and the reference is fine. In any other
clone the folder never arrived, so the same reference, at the same commit,
fails.

Demonstrated on a scratch node — one item, completed, one file referencing it,
one commit:

```
=== validate HERE (folder still on disk) ===
validate OK
=== validate in a FRESH CLONE of the same repo ===
docs/work/inbox/ref.md: tcw:// tcw://W/2026-09-02-a-thing → no such work item: …
2 problem(s).
```

Because this repository wires `tcw validate` as the `complete` transition's
`pre` hook (`tcw-config.yaml`, `work.lifecycle.transitions.complete.pre`), that
irreproducibility is currently fatal: four such references exist, `tcw validate`
exits 1 in any fresh checkout, and **no item can be completed here at all**. It
also explains why completion succeeded on 2026-09-01 and fails now — the
difference is which machine ran it, not what changed.

There is a second, quieter consequence — a hazard rather than a present fault.
`_unique_slug` (`tcw/store/fs.py:3552`) loops
`while self._find(slug) is not None`, which sees **live items only**. In a clone
without the ignored folders, nothing stops a new item whose date and title match
a resolved one from being handed **that same slug**; every existing reference to
the resolved item would then silently resolve to a *different* item.

**Working assumption, set by the requester: slugs have been unique to date.** No
collision is presumed to have happened, so nothing here needs repairing — the
graveyard is what guarantees it stays true going forward, since it is the only
record of a resolved slug that survives into another clone. Stated as an
assumption because it is not verified: doing so would mean reconstructing every
resolved slug from git history, which is both the trick the prime directive
forbids and unnecessary if the assumption holds.

### Sweep

Repo-wide, for the same "an ignored folder makes the answer depend on local
residue" pattern. Two negative results, recorded so a later reader does not
redo them:

- **`unresolved_blockers` is not affected** (`tcw/store/base.py:2118-2142`). It
  already documents the opposite decision — *"A slug that no longer resolves
  counts as resolved (silently)"* — and fails open. Safe, but imprecise for the
  same reason references are: it cannot tell a resolved blocker from a typo, so
  a misspelled blocker slug silently stops blocking. The tombstone lookup makes
  that precise, which is a genuine improvement but a **separate** behaviour
  change; see Non-goals.
- **`tcw work list` is not affected.** Resolved statuses are excluded by
  default, so it prints the same thing either side of the ignore rule
  (verified in both the scratch node and its clone).

## Goals

1. A reference to a slug the store once held and has since resolved is
   distinguishable from a reference to a slug that never existed, in every
   checkout, from tracked content alone.
2. `tcw validate` stops reporting the first kind, so it is usable as the
   `complete` gate again and this repository's four failing references clear.
3. Slug assignment never reuses the slug of a resolved item, from this change
   forward.
4. The mechanism sits in the abstract model, not in a filesystem trick, and a
   store that keeps resolved items forever needs no graveyard to satisfy it.

## Non-goals

- **Changing how `complete` and `discard` interact with git.** The withdrawn
  two-commit sketch stays withdrawn; their commit behaviour is untouched beyond
  the tombstone path itself (see Design).
- **Any opinion on how long resolved documents are kept.** That stays the repo
  manager's call via `.gitignore`, exactly as today.
- **Recording where an item's documents went.** No repository, no commit, no
  locator. A recorded commit is a promise of retrievability that does not
  survive a squash-merge, a rebase, or a shallow clone, and a pointer that
  silently stops working is worse than none.
- **Making `unresolved_blockers` precise.** The tombstone makes it *possible* to
  tell a resolved blocker from a typo; acting on that changes when transitions
  refuse, which deserves its own item rather than riding in on this one.
- **Detecting or repairing a historical slug collision.** Out of scope on the
  assumption above. If one is ever found, it is its own item — this one only
  closes the path forward.
- **Reconciling `2026-09-01-make-tcw-validate-usable-as-a-gate-…`.** This item
  removes most of that one's motivation; re-scoping it is that item's business.

## Design

### The model operation

The question the resolver needs is not *"is this slug live?"* but **"does this
store know this slug at all?"** — which is answerable by any store.

Add one abstract method to `WorkStore` (`tcw/store/base.py`, beside `get` at
:1696):

```python
@abstractmethod
def tombstone(self, slug: str) -> Tombstone | None:
    """The record of an item this store once held and has since resolved,
    or None if it never held one by that id. An adapter whose resolved items
    remain retrievable by `get` may answer from those directly."""
```

`Tombstone` is a frozen dataclass of `slug`, `resolution`, and `resolved` (ISO
date). **No locator field** — omitted by decision, not oversight.

Litmus test: *could a non-filesystem store implement this?* Yes, and more
cheaply — a Jira-backed store's completed issues never stop existing, so its
`get()` already answers and `tombstone()` can read status or return `None`. The
graveyard is the **filesystem adapter's private mechanism** for answering an
abstract question, which is the shape the prime directive asks for. Nothing in
the interface mentions files, commits, or history.

### The filesystem realization

**One file for the whole store: `<store>/graveyard.yaml`** — a mapping of slug
to its `resolution` and `resolved` date. Requester's decision, taken after the
per-slug alternative below was put to them.

It is tracked, unconditionally. It must be, or the whole defect reproduces one
level up: an ignorable graveyard is invisible in exactly the clones that need it.

Two consequences follow from one shared file rather than one file per tombstone.
Neither blocks the design; both are recorded so `implement` handles them
deliberately rather than discovering them.

- **Commit scoping widens by one path.** `complete` commits scoped to the item's
  own folders so unrelated working-tree edits are never swept in
  (`work/complete-a-work-item`). The pathspec becomes `{item folder,
  graveyard.yaml}`, and that second path is shared with every other item — so a
  concurrent agent's *uncommitted* edit to `graveyard.yaml` would ride along in
  this item's transition commit. Narrow, but it is the promise's one hole.
- **Concurrent completions can conflict.** This store is explicitly multi-agent
  (`docs/work/.claiming/`). Two agents resolving different items write the same
  file; the write must be read-modify-write rather than a blind append, and a
  merge conflict on it is a plain YAML conflict a human can settle.

A single file also buys something real: it is one greppable artifact, it makes
the count of resolved items obvious, and it does not scatter thousands of
near-empty files through the store over a project's life.

### Writing and reading

- `complete` and `discard` write the tombstone as part of the transition.
- `tcw work tombstone add <slug> [--resolution r] [--resolved date]` records one
  after the fact. Required, not a convenience: this repository's four failing
  references name items resolved before any graveyard existed, so Goal 2 is
  unreachable without it. It is also the migration path for every existing
  adopter. A CLI command rather than deriving entries from git history, which
  would be exactly the "reconstruct state from history" trick the prime
  directive forbids.
- `tcw/refs.py`, at the `store.get(bare) is None` branch (:132-134), consults
  `tombstone()` before failing, and reports success with the resolved status.
- `tcw/validate.py` (:182-190) therefore stops reporting these, with no change
  of its own beyond what the resolver returns.
- `tcw serve`'s `/api/resolve` renders a tombstoned target as resolved and
  archived — not a live link, not an error — alongside the existing off-board
  treatment.
- `_unique_slug` (`tcw/store/fs.py:3552`) additionally rejects a slug with a
  tombstone, closing the silent-collision path.

Because the CLI carries all of it, a Codex user gets identical behaviour; no
part depends on a hook or on injected context.

## Acceptance criteria

Executable ones have been run against the tree as it stands today, and each
currently **fails** in the way the criterion describes (that is the point).

1. `tcw validate` in a fresh clone of a repository whose only reference problem
   is a reference to a resolved item exits **0** and prints `validate OK`. Today
   it exits 1 with `no such work item` — reproduced above.
2. `tcw validate` at the same commit gives the **same verdict** on the machine
   that completed the item and in a fresh clone. Today it gives `validate OK`
   and `2 problem(s)` respectively.
3. A `tcw://W/<slug>` reference to a slug that was never created is **still** a
   validation problem, with today's wording unchanged.
4. After `tcw work complete <slug> --resolution done --confirm`, a tracked file
   exists recording that `<slug>` resolved as `done`, and it is present in a
   fresh clone.
5. The same holds for `tcw work discard`, recording the discarding resolution.
6. `tcw work tombstone add <slug>` records an entry for an item that was
   resolved before the feature existed, after which criterion 1 holds for it.
7. Running it for a slug that is currently live is refused, and nothing is
   written.
8. In a clone with no `completed/` folder, creating an item whose date and title
   would generate a resolved item's slug yields a **different** slug. Today it
   yields the same one (`tcw/store/fs.py:3552`).
9. `tcw validate` in this repository exits 0, so
   `tcw work complete 2026-09-02-restore-the-ci-test-suite-to-green` — blocked
   today by its `pre` hook — succeeds.
10. No new abstract-store method mentions a file, a path, a commit, or git; a
    store implementing `tombstone()` by consulting its own resolved items
    satisfies the interface.
11. The full suite passes on both matrix legs in CI.

## Risks

- **Can a resolved item come back?** If any path returns a completed item to a
  live status, its tombstone must be removed or `_unique_slug` will refuse a
  slug that is legitimately live again. `plan` must establish whether such a
  path exists; if it does, tombstone removal is part of it.
- **The graveyard becomes the thing kept forever.** Deliberate and bounded: one
  file, two fields per resolved item, no documents. It is not what the requester
  asked not to keep. Still worth stating plainly in the release note, since it
  is a new permanent file in every adopting repo — and it grows monotonically,
  so a very long-lived store should expect a large-ish YAML mapping.
- **A tombstone can be wrong.** Nothing verifies the item really was resolved —
  `tombstone add` trusts its caller, which is what makes the backfill possible.
  The refusal in criterion 7 is the only guard.
- **Adopters with existing history see no improvement until they backfill.**
  The feature is inert for references written before it shipped. Worth a
  sentence in the release note pointing at `tombstone add`.
- **Naming.** "Graveyard" is the requester's word, "tombstone" the industry one
  for exactly this record. The spec uses `tombstone` for the model and
  `graveyard.yaml` for the file; if that split reads badly, settle it in `plan`
  before any code is written.

## Notes

- The problem statement's central claim — that the verdict depends on local
  residue — was reproduced on a scratch node rather than reasoned about, after
  an initial reading that assumed completion deleted the documents outright. It
  does not: it moves them into an ignored folder, and they survive on that one
  machine. Several conclusions changed once that was checked.
- `tcw/refs.py:9-13` states the module deliberately adds "no new store-interface
  method — litmus-clean" and dispatches through existing `get()`. This spec does
  add one. The justification is that the question being asked is genuinely new
  and genuinely abstract; if `plan` finds a way to answer it through existing
  methods, that is strictly better and should win.
