# Outcome — Teach the remaining readers to tell a vanished item from an absent one

Implemented on `main`, second of the three queued items.

## What shipped

### Tasks 1-2: split immediate and stable reads (`d6aa7a5`, tests in the prior commit)

`FsWorkStore._get_now` is the one-shot probe; `get` stabilizes. `get` answers a
hit or an evidence-free miss immediately and waits only when `_claiming_dirs(slug)`
proves that exact slug is mid-flight, raising the documented interrupted-claim
error when the claim never publishes. `.claiming/` stays out of `WorkStore`.

**Three call sites deliberately keep `_get_now`**, each because its job *is* the
unstable state — `_lost_the_claim` (else each of its 50 iterations nests another
500 ms wait), `start`'s take-over probe (the branch exists for the state `get` now
raises on, so `--take-over` would have become unreachable), and
`_effect_transition`'s lost-race message (which wants the raw state to describe).

`WorkStore.unresolved_blockers` catches the adapter's refusal to settle and reports
that blocker *as a blocker*. Raising there would answer "why can't I start B?" with
an error about A.

Full classification of every `self.get(` caller, as Step 3 required:

| Caller | Read | Why |
| --- | --- | --- |
| `_lost_the_claim`, `start` take-over probe, `_effect_transition` error path | `_get_now` | handling the unstable state |
| `unresolved_blockers` | `get` + catch | needs settled, but an unsettleable blocker still blocks |
| `_entry_for`, `_require`, blocker-cycle walk, `initiative_epic`, `check`, `create`, `_effect_transition` pre-move read | `get` | wants the settled value |
| taxonomy/capabilities `self.get` (fs.py:987-1854) | untouched | different classes; no claim concept |

### Task 3: atomic detail snapshots (`af9d645`)

`get_detail` retries a whole snapshot (bounded at 5) via `_detail_snapshot`, which
raises the private `_Moved` — or lets a `FileNotFoundError` from a path inside the
item propagate — when the item relocates mid-read. All-or-nothing on purpose:
pairing the first item with files re-read from its new status would hand out
revisions that never coexisted, and a caller would then write against them.
Permission errors and malformed content still surface.

### Task 4: sibling sweep — no code change, no commit

Every `_find` call site in `tcw/store`, `tcw/serve`, `tcw/work` classified:

| Sites | Classification |
| --- | --- |
| `_effect_transition:2074`, `create_work:3133`, reparent:3273 | transition/write logic, conflict-aware by contract |
| `_require_dir`, `path`, `body_path`, `artifact_locator`, `_unique_slug` | single lookup, reads nothing composite |
| `artifacts()`, `_validation_resources()` | **already** carry explicit vanish guards (`except FileNotFoundError: return []`) — a pre-existing deliberate degradation, not a new hole |
| `_get_now`, `_detail_snapshot` | fixed above |

No sibling was vulnerable, so no empty commit — as the plan directed.

## What the spec and plan got wrong

**The spec's design missed a second, unrelated race, and my own test caught it.**

The spec frames the whole problem around `.claiming/`, so `get`'s stabilization
keys on claim evidence. But `get` has its *own* find-then-read window: `_find`
returns a folder, `_item_from_dir` reads it, and an ordinary `git mv` transition
(`submit`, `complete` — no `.claiming/` involved) can land in between. The stale
path then reads as **absent**, with no claim evidence for `get` to key on.

Found because `test_get_detail_survives_a_move_between_find_and_read` still failed
after Task 3 was implemented exactly as planned. The retry could not help: the
snapshot was returning a legitimate-looking `None` from `get`, not raising.

Fixed inside `_get_now` with one re-probe, which is the only level where the stale
path is known. The spec's design section is narrower than the defect it names.

**Two smaller plan corrections:**

1. Task 1's fixture as written passed against the unfixed code. Publishing the
   claim from a thread released immediately meant the item was already in `active/`
   before the blocker read happened, so the race never occurred. Rewritten to
   publish after a deliberate delay — an order of magnitude inside the 500 ms
   window, and the unfixed code fails instantly rather than on a timing edge.
2. Task 3 Step 1 called `test_get_detail_lost_at_find_returns_none` "obsolete",
   which understates it: its asserted contract is now *wrong*. `None` was the
   honest answer only while nothing looked again. Replaced with
   `test_get_detail_retries_a_transient_loss_at_find` plus
   `test_get_detail_gives_up_when_the_item_never_settles` to pin the bound.

## Verification

| Check | Result |
| --- | --- |
| `python -m pytest -q` | **1277 passed** (was 1267; +10) |
| Contention suites × 10 | 149 passed each, 22.99-24.03 s — no flakes, no hangs |
| `pnpm` tsc / lint / test / build / check:build | all clean; 50 frontend tests |
| `tcw taxonomy check` / `capabilities check` / `validate` | all OK |
| `git diff --check` / `git status --short` | clean |

### Verification beyond the suite

The plan asks to confirm ordinary misses never sleep and abandoned claims consume
one bounded window. Both are asserted directly rather than eyeballed:
`test_get_of_a_missing_slug_does_not_wait` and
`test_a_longer_slugs_claim_does_not_stall_a_shorter_one` both bound the read under
0.25 s against a 0.5 s window — generous CI margin while still far below the
window they would trip if the wait were unconditional. The prefix case matters
because `_unique_slug` mints `{base}-2`, so slugs are prefixes of each other by
construction.

## Notes

- No capability-ledger change, as `spec.md` said: this restores concurrency safety
  the existing lifecycle already promised.
- The `_Moved` exception is private to the filesystem adapter and never crosses
  `WorkStore` — "the folder moved" has no abstract analog.
