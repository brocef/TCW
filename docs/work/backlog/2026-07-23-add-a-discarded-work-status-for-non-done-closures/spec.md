# Specification

## Capability changes

**New**

- `work/discard-a-work-item` — abandoning an item without pretending it shipped,
  including directly from `backlog`. Seeded `Missing`, flipped at completion.

**Changed**

- `work/complete-a-work-item` — the resolution now selects the destination
  status, and the Definition-of-Done / capability gates apply only to a `done`
  closure.
- `work/drop-a-work-item` — **wording only, but required.** It currently reads
  "delete a backlog item that won't be done", which is now exactly what a
  discard is. Contradiction-detection surfaced this; left alone, the two
  capabilities describe the same user intent with different commands. It is
  rewritten to name its actual niche: erasing a mis-created item (a typo, an
  accidental duplicate) that should leave no record. Behavior is unchanged.
- `work/view-the-board` — `list` hides `discarded` alongside `completed`;
  `--all` and `--status discarded` reveal it.
- `web/editing` — the board's status filter gains a fourth toggle and the
  complete modal branches on resolution.

**Taxonomy:** no new entry. `discarded` is a value of the existing
`work-item/transition` state machine, not a new domain noun. The registered
vocabulary already covers `work-item`, `work-item/transition`, and
`work-item/definition-of-done`.

## Problem

`completed/` currently answers two different questions with one folder: "what
did we ship?" and "what did we decide about?". Three items closed during the
2026-07-23 backlog audit — two `superseded`, one `wontfix` — sit in `completed/`
next to genuinely shipped work, and telling them apart requires opening each
`state.yaml`.

Two consequences:

1. **The board lies at a glance.** `completed/` is the natural answer to "what
   shipped", and it is wrong.
2. **Abandoning a backlog item is the hardest closure.** `complete()` only
   accepts `active`, so all three audit closures took a throwaway
   `backlog → active → completed` round-trip. The item most likely to be
   abandoned is the one that requires a fake `start` to abandon.

There is also a latent correctness bug that the current conflation hides:
`tcw capabilities drift` reports "shipped-missing" for any `Missing` capability
whose planning doc is a `completed` item (`tcw/capabilities/cli.py:210`). A
`wontfix` item that declared capabilities is therefore reported today as
shipped-but-unreconciled. Routing non-`done` closures elsewhere fixes that
without a special case.

## Goals

- `completed/` means exactly "we shipped this".
- `backlog → discarded` is a first-class transition; no throwaway `start`.
- Status and resolution cannot disagree.
- A discarded item counts as **resolved** everywhere resolution matters —
  blockers, epic rollup, epic completion.
- Existing history migrates so one rule holds across the whole repo.

## Non-goals

- A reopen transition. `discarded` is terminal; re-raising an abandoned idea is
  a fresh item with fresh context.
- Removing or narrowing `tcw work drop`. Hard delete for genuine mis-creations
  stays; `discarded` is for decisions worth a record.
- Per-item judgment about the destination. The resolution decides, always.
- A `discarded` resolution value. The four resolutions are unchanged.

## Current state

### The status model

`tcw/store/base.py:434`

```python
WORK_STATUSES = ("backlog", "active", "completed")
LEGAL_TRANSITIONS = {("backlog", "active"), ("active", "completed")}
WORK_RESOLUTIONS = {"done", "wontfix", "duplicate", "superseded"}
```

`complete()` (`base.py:962`) hard-codes `"completed"` as the destination and
carries one scoped exception: a completable epic may close straight from
`backlog` (`from_backlog_epic`, `base.py:971`), bypassing the
`LEGAL_TRANSITIONS` check via `_effect_transition`.

Most of the filesystem adapter is already derived from `WORK_STATUSES` and needs
no edit: `_item_dirs` (`fs.py:1554`), `_status_of` (`fs.py:1563`), status-path
locators (`fs.py:211`), and `init` scaffolding (`fs.py:354`) all iterate the
tuple.

### `status != "completed"` is an unnamed "resolved" predicate

This is the finding that shapes the work. Five call sites use the literal
`"completed"` where they mean **resolved**:

| Site | Meaning | Effect of a `discarded` item today |
| --- | --- | --- |
| `base.py:939` `unresolved_blockers` | resolved | a discarded blocker blocks forever |
| `base.py:920` `epic_completable` | resolved | a discarded child never lets its epic close |
| `base.py:977` `complete()` open-children | resolved | same, on the direct-complete path |
| `recursion.py:106,109` reconcile rollup | resolved | rollup reports the epic permanently incomplete |
| `capabilities/cli.py:210` shipped-missing | **shipped** | correct as-is — must stay `completed` only |

Four become `resolved`; one stays `completed`. Getting that split wrong is the
main correctness risk in this item, and it is the difference between a folder
rename and a working status.

### Other touch points

- `tcw/work/cli.py:276` — `list` hides `completed`.
- `tcw/work/cli.py:582-609` — DoD checklist print, `--confirm` gate, capability
  gate, worktree merge-back.
- `tcw/serve/__init__.py:808` — the web `complete` action.
- `web/client/src/ui/app.tsx:51`, `content-views.tsx:47` — duplicated
  `WORK_STATUSES` literal; `model/tree.ts:9` — status sort order.
- `tcw/store/project.py:16` — `RESERVED_PROJECT_IDS` is derived from
  `WORK_STATUSES`, so `discarded` becomes reserved automatically.

### Migration scope

Three items carry a non-`done` resolution in `completed/`:

- `2026-06-19-additional-capability-sidecars` (`wontfix`)
- `2026-07-03-live-browser-test-pass-for-the-interactive-web-editor` (`superseded`)
- `2026-07-03-per-object-capability-revision-token-fix-file-scoped-409s` (`superseded`)

No in-repo `tcw://` reference or status-path locator addresses any of the three
by a `completed/<slug>` path (verified by grep; the only `completed/` mentions
outside `docs/work/` are prose in the frozen `docs/plan/` build-phase documents).
Migration is therefore three `git mv`s with no reference fixups.

## Proposed behavior

### 1. Resolution derives status

```python
WORK_STATUSES = ("backlog", "active", "completed", "discarded")
RESOLVED_STATUSES = ("completed", "discarded")

def resolution_status(resolution: str) -> str:
    """The terminal status a resolution closes into. Raises on an unknown
    resolution — never guesses a destination."""
    if resolution not in WORK_RESOLUTIONS:
        raise ValueError(f"invalid resolution '{resolution}'")
    return "completed" if resolution == "done" else "discarded"
```

It **must not** default unknown input to `discarded`. `complete()` validates the
resolution before calling, so the raise is unreachable there — but `check()`
calls it on arbitrary persisted YAML, and a silent `else: "discarded"` would
make a corrupt-resolution item in `discarded/` read as *consistent*, defeating
the detector below.

`complete()` calls `resolution_status()` for its destination instead of
hard-coding `"completed"`. Because `complete()` is the **only** writer of a
terminal status — the CLI exposes no raw transition command, and `transition()`
is reachable only through `start()` and `complete()` — the pair is unforgeable
by construction. This settles the redundancy question from the request: derive,
do not reconcile two sources.

`WorkStore.check()` is the **corruption detector**, not a second source of
truth: it catches a hand-moved folder or a bad merge, which the filesystem
adapter makes physically possible even though no code path produces it. For each
item it reports:

- a terminal status (`completed`/`discarded`) with a missing or invalid
  `resolution`;
- a valid resolution whose `resolution_status()` disagrees with the item's
  status;
- a non-terminal status (`backlog`/`active`) carrying a `resolution` at all.

### 2. Transitions

```python
LEGAL_TRANSITIONS = {
    ("backlog", "active"),      # start
    ("active", "completed"),    # complete --resolution done
    ("active", "discarded"),    # complete --resolution wontfix|duplicate|superseded
    ("backlog", "discarded"),   # abandon without a throwaway start
}
```

The `from_backlog_epic` exception is **preserved and narrowed to `done`**. It
exists so a coordinator epic whose children all resolved can close as *shipped*
from `backlog`; the general `(backlog, discarded)` transition does not subsume
that, because it produces the wrong status. In code the legality test becomes:

```python
dest = resolution_status(resolution)
from_backlog_epic = (dest == "completed" and item.status == "backlog"
                     and self.epic_completable(item))
if (item.status, dest) not in self.LEGAL_TRANSITIONS and not from_backlog_epic:
    raise IllegalTransition(...)
```

`epic_completable()` also updates: an epic is completable when every initiative
child is **resolved** (`completed` or `discarded`), and it is itself in neither
terminal status.

### 3. The `resolved` split

Introduce `RESOLVED_STATUSES` and apply it to the four "resolved" sites in the
table above. Leave `capabilities/cli.py:210` reading `completed` — it genuinely
means shipped, and narrowing it is the bug fix noted in the problem statement.

### 4. Gates on a discard

A non-`done` closure is not a shipment, so the shipment gates do not apply:

| Gate | `done` | non-`done` |
| --- | --- | --- |
| Blocker check (unless `--force`) | yes | yes |
| DoD checklist printed | yes | **no** — `dod: []` is recorded |
| `--confirm` required | yes | **yes** |
| Capability gate (fails closed) | yes | **no** — warns instead |
| Worktree merge-back | yes | **no** — see below |

Requiring an operator to acknowledge "tests pass" in order to abandon an item is
nonsense, and blocking the abandonment on capability reconciliation puts
friction on precisely the path this item exists to smooth. Instead, discarding
an item that declared `new:` capabilities still reading `Missing` prints a
non-blocking warning naming them and suggesting
`tcw capabilities set <path> --status Omitted`. `--confirm` is retained: discard
is destructive-ish and terminal, and the confirmation is the deliberateness
signal that the DoD checklist otherwise provided.

### 5. Worktrees on discard

`active → discarded` for an item started with `--worktree` **does not merge** —
the whole point is that the work is not wanted. The worktree is removed and the
branch is **left intact**, with a warning naming it, because deleting an
unmerged branch destroys work that a discard decision does not authorize.
Recovering it is `git branch -D work/<slug>` by hand.

### 6. `list` and the web board

`list` hides `discarded` by default exactly as it hides `completed`; `--all`
includes both; `--status discarded` shows only discarded items. The web board
gains a fourth status filter toggle, defaulted off to match the CLI, and
`model/tree.ts` sorts `discarded` last (after `completed`). The two duplicated
`WORK_STATUSES` literals in `app.tsx` and `content-views.tsx` are extended in
place; deduplicating them is out of scope.

The web complete modal branches on the selected resolution: choosing a non-`done`
resolution replaces the DoD acknowledgment list and the capability-reconciliation
reminder with the discard warning, matching the CLI exactly.

### 7. Migration

**No migration code.** Two separate concerns, neither of which needs any:

**This repo** — three `git mv`s in **their own commit**, separate from the
feature commits:

```sh
git mv docs/work/completed/2026-06-19-additional-capability-sidecars \
       docs/work/discarded/
git mv docs/work/completed/2026-07-03-live-browser-test-pass-for-the-interactive-web-editor \
       docs/work/discarded/
git mv docs/work/completed/2026-07-03-per-object-capability-revision-token-fix-file-scoped-409s \
       docs/work/discarded/
```

`state.yaml` needs no edit — status is derived from the folder
(`_status_of`, `fs.py:1563`), so the move *is* the status change. `tcw validate`
and the new `check()` consistency rule verify the result.

**Downstream adopters** — a migration guide, matching this repo's established
`docs/migration-guide-<from>-to-<to>.md` pattern (there are two already, and
`v0.13.0`'s release notes link theirs). It instructs an agent or human to move
every `completed/` item carrying a non-`done` resolution into `discarded/`, and
names the two other breaking edges: `discarded` joins the reserved project-ID
set (the 0.13 guide already documents work-status names as reserved), and any
`completed/<slug>` status-path locator pointing at a moved item must be
re-pointed.

A shipped `tcw work migrate` subcommand would be permanent CLI surface for a
one-time move that `git mv` already performs, and the guide is how this project
has handled every prior breaking change. `check()` tells an adopter exactly
which items are affected, so the guide does not need to enumerate them.

## Acceptance criteria

- `complete --resolution done` lands in `completed/`; each of `wontfix`,
  `duplicate`, `superseded` lands in `discarded/`.
- `complete` succeeds directly from `backlog` for a non-`done` resolution, with
  no intervening `active`.
- `complete --resolution done` from `backlog` is still refused for a
  non-completable item, and still permitted for a completable epic.
- An item blocked by a discarded item is startable and completable.
- An epic with one completed and one discarded child is completable, and
  `reconcile` reports it ready to close.
- `capabilities drift` does not report shipped-missing for a discarded item's
  declared capabilities.
- A discard prints no DoD checklist, records `dod: []`, still refuses without
  `--confirm`, and warns (without failing) about unreconciled declared
  capabilities.
- Discarding a `--worktree` item performs no merge, removes the worktree, leaves
  the branch, and warns with the branch name.
- `list` hides discarded by default; `--all` and `--status discarded` show it.
- `check()` reports an item whose status contradicts its resolution, one in a
  terminal status with a missing or invalid resolution, and one in `backlog` or
  `active` carrying a resolution.
- `resolution_status()` raises on an unknown resolution rather than defaulting
  to `discarded`.
- `discarded/<slug>` resolves as a status-path locator; `completed/<slug>` no
  longer resolves for a migrated item.
- The three historical items live in `discarded/`, `tcw validate` is clean, and
  `check()` reports no status/resolution disagreement across the whole node.
- A migration guide exists for the release and is linked from its release notes.
- Web board filters, status ordering, and the complete modal match CLI behavior.

## Risks and dependencies

- **The resolved/shipped split is the failure mode.** Treating a "shipped" check
  as "resolved" silently mis-reports capability drift; the reverse wedges epics
  and blockers. Each of the five sites gets a test asserting its side of the
  split.
- **`RESERVED_PROJECT_IDS` gains `discarded`.** A connected project already using
  that ID would now fail closed. No such project exists in this graph; the
  release note should mention it.
- **Status-path locators break for migrated items.** Verified as unused in-repo;
  external notes are outside TCW's control and the release note should say so.
- **`completed/` is no longer the single terminal folder.** Anything outside TCW
  that globs `docs/work/completed/` to answer "what closed?", or that treats the
  `serve` API's status field as a closed set of three, sees a behavior change.
  This is the intended semantic — `completed/` now means shipped — so the
  release note frames it as a deliberate narrowing, not a regression.
- **`--worktree` interaction is the least-covered path.** `merge_worktree` runs
  before the folder rename (`fs.py:309`); the discard route must skip it without
  disturbing that ordering for the `done` path.

## Related work items

- `2026-07-23-capability-first-lifecycle-…` — adds a capability/tests
  attestation to the completion gate. It must land **after** this item and apply
  only to the `done` route; the discard route has no DoD checklist to extend.
- `2026-07-22-planning-agnostic-tcw-lifecycle-orchestration` — its stated
  non-goal "no new work statuses" refers to its own scope, not a constraint on
  this item. Its `complete` checkpoint contract and `--already-integrated` flag
  must account for the derived destination once both land.
- `2026-07-23-emit-new-location-when-cli-commands-move-a-tcw-object` — its
  `plan.md:53` assumes `complete` moves to `completed/`; that assumption becomes
  resolution-dependent.
