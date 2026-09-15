# Outcome — Refuse local work that no claimed tracker ticket authorizes

## What shipped, task by task

| Plan task | Commit | What |
| --------- | ------ | ---- |
| 1 — `strict` in the configuration | `0d170f29` | `TrackerConfig.strict`, `WorkStore.tracker_strict()`, the statuses strict requires; a broken block does not switch strict off. |
| 2 — `authorize` and the exclusivity check | `615f3d37` | `authorize` and `claim_refusal` in `tcw/tracker/sync.py`. |
| 3 — command gates | `9f3855a9` | `new`, `inbox accept`, `start`, `submit`, `rework`, `complete`, `drop`, `tracker import`; strict `deliver` runs `claim_refusal` after an owed claim. Also the shared-ticket fix in § What the plan or spec got wrong. |
| 4 — `tcw serve` | `d3eb90f9` | `_strict_refuses`: 409 for create, start, complete as `done`, drop of an ever-bound item, PUT of `tracker.yaml`. `ever_bound()` shared with `drop`. |
| 5 — capabilities | `d7b9d3a3` | `work/require-tracker-backed-work` → Supported with its first text; five others amended. |
| Documentation Sync | `4302e841` | README, release notes, changelog, `tcw-work` command reference, `tcw-configure` tracker reference. |
| Review round 1 fixes | `5fe9c061` | See § Review. |
| Binding-surface review leftovers | `0086d8ae` | Findings the sibling item's review raised after it completed, relayed by the team lead; see § Review. |
| Review round 2 fixes | `5abfca99` | See § Review. |
| Follow-ups | `dd5e94e6` | `docs/work/inbox/2026-09-15-a-tracker-hold-leaves-no-evidence-outside-this-checkout.md`. |

## Test results

- Full suite, `pytest` in the worktree with the editable install pointed at it, after
  the documentation commit and before review: **3285 passed** in 692 s. After both
  review rounds and the follow-up commits (`dd5e94e6`): **3297 passed** in 692 s. Bare `pytest` on merged `main` is run at verify.
- `tests/test_tracker_strict.py` and `tests/test_tracker_sync.py`: 125 passed after round 2. All `tracker`, `doc` and
  `skill` tests: 1020 passed.
- `tests/test_tracker_sync.py` is unedited by this change (criterion 19):
  `git diff 1aa715a0 -- tests/test_tracker_sync.py` is empty.
- Hands-on, in a scratch node whose tracker `base-url` is
  `https://tcw-strict-check.invalid` (the name cannot resolve, so nothing reached any
  tracker; the credentials were made-up values): `tcw validate` exit 0; `tcw work new`
  refused naming `tcw work tracker import`; `new --epic` created the epic;
  `start --worktree` on it refused; `import` exited 1 unable to reach the tracker;
  `start` of a hand-bound item refused, "was not started … may or may not have been
  claimed"; `drop` refused naming the discard command; a `wontfix` discard went
  through (exit 1 only for C3's pending delivery). The token appeared in no file
  but the config's variable name.

**Mutation checks** — each went red for the reason named, then was restored:

| Broken | Test that went red |
| ------ | ------------------ |
| `authorize` skips the assignment check | `test_a_ticket_not_assigned_to_you_authorizes_nothing_even_at_the_target` |
| `claim_refusal` skips the landing-status check | `test_a_claim_row_1e_from_the_wrong_status_is_refused` |
| `claim_refusal` skips the exclusivity verdict | `test_a_claim_on_a_workflow_that_offers_it_everywhere_is_refused` |
| strict `start` claims before the blocker check | `test_start_claims_nothing_for_a_start_the_store_would_refuse` |
| `drop`, `submit`, `rework`, `new`, `import` ungated (one at a time) | the matching gate test |
| epics gated | `test_an_epic_is_not_gated` |
| `complete`'s gate moved after the merge-back | `test_complete_is_refused_before_the_worktree_merge` (the merged file existed) |
| each `serve` gate removed, and the epic exemption removed | `test_serve_refuses_what_it_cannot_check_and_changes_nothing` |
| `expected_statuses` ignores `shared` / always shared | the shared-part tests / `test_an_unshared_ticket_sent_back_from_review_is_not_carried_forward` |
| a same-part sibling counts as shared | `test_a_ticket_taken_again_after_a_discard_is_not_carried_forward` |
| `tracker_strict()` read from the merged block only | `test_strict_survives_problems_that_come_from_an_ancestor` |
| epic `--worktree` allowed; broken-block message; take-over skips the claim | the matching round-1 test |

## What the plan or spec got wrong

- **Spec § 2 step 5 said C3's `expected_statuses` falls back from `review` to
  `active`.** It returned only the nearest mapped status. So criterion 16 (two parts
  held in `In Progress` both complete) failed at C3's delivery, not at the gate: the
  last part, completing from `review`, found the ticket in `In Progress` and reported
  it conflicting. That is a C3 defect reachable with strict off too. Fixed in
  `9f3855a9` and narrowed in `5fe9c061`: when an item for **another part** of the same
  ticket is here, open or finished, every earlier mapped status is expected. A
  finished part that was not retained on disk, or lives in another clone, is not seen;
  that case still reports conflicting and is left as a documented limit.
- **Criterion 19** says `tests/test_tracker_sync.py` passes unedited. The first fix
  added two tests to it; they were moved to `tests/test_tracker_strict.py` so the file
  is unedited.
- The plan said `authorize` would reuse `expected_statuses`. The first version had
  its own loop, which accepted a ticket a reviewer sent back; round 1 made it reuse
  it.

## Review

Two rounds by the `adversarial-code-reviewer` agent, each finding checked against the
code before acting.

**Round 1 (NOT DONE)**

1. *`authorize` accepts a ticket a reviewer sent back from review* — **accepted.**
   It now uses `expected_statuses` plus the target. Test:
   `test_complete_is_refused_when_a_reviewer_sent_the_ticket_back`; the held-part test
   now has a real second part.
2. *"Shared" counted any item on disk, including a re-take after a discard; and it
   misses parts not retained* — **narrowed.** Shared means an item for another part.
   The retain/other-clone case is a documented limit (round 2, B).
3. *Epics bypass strict mode* — **narrowed.** Epics stay exempt (spec decision, so
   they can hold children and `reconcile` can close them), but `start --worktree` on
   an epic is refused, so no epic branch is merged back. Hand-editing `type: epic` is
   **rejected** as out of scope: a hand edit can set `strict: false` just as well.
4. *Ancestor-block problems switch strict off* — **accepted**: the nearest block that
   sets `strict` decides. A parent missing from the checkout still fails open; it is
   reported by `tcw validate`, and failing closed would make non-strict children
   refuse `new`.
5. *Take-over of an active item untested* — **accepted**, test added.
6. *Criterion 2: broken block's `new` does not name `tcw validate`* — **accepted.**
7. Duplicated binding checks — **accepted** (`binding_refusal`); two store scans —
   **accepted** (`_siblings`); weak tests — **accepted**, tightened; docs qualifiers —
   **accepted.**

**Round 2 (DONE, with notes)** — all round-1 fixes confirmed.

- A. *An unreadable `tracker.yaml` gives a traceback under strict* — **accepted**;
  `binding_refusal` catches read errors. Test:
  `test_an_unreadable_binding_is_refused_not_a_traceback`.
- B. *The refusal blames a tracker move for a hold made elsewhere* — **accepted**: the
  strict and non-strict messages name the possible hold and the fix; README and
  `commands.md` state the limit.
- Needs a separate change: recording evidence of a hold, and an epic worktree started
  before strict mode — filed (`dd5e94e6`).

**The binding-surface item's late review** (relayed by the team lead, verified here):
an impossible YAML value (`bound: 2026-02-30`) crashed every board read —
**accepted**, fixed with a test that goes red without it; a named pipe blocked the
read — **accepted** (not mutation-checked: without the fix the test hangs rather than
failing); the permission test failing as root — **accepted**; the anchor-chain test
too deep — **accepted**; a file removed mid-read — **already fixed** on `main`; the
tracker commands' separate read path — **filed**
(`docs/work/inbox/2026-09-15-tracker-commands-classify-an-unreadable-binding-differently-from-show.md`);
a size limit — **rejected**, as before.

## Autonomous decisions

- **The workflow-definition read is parked, not built** (spec). Codex and Opus both:
  it needs a non-admin token against real Jira, which this run may not use. The
  exclusivity check is made from the ticket right after the claim instead.
- **Refusals are reported, never recorded** (spec; both advisors).
- **Discards are always allowed; `drop` of an ever-bound item is refused; epics are
  exempt** (spec; Opus's position taken on discards, widened by the spec review).
- **`edit` and artifact writes are not gated** (spec; Codex wanted them gated, Opus
  not; Opus's reason taken — they move no work).
- **The shared-ticket fix in C3's `deliver`** (this stage; needed for criterion 16).
  Narrowed to "another part" after review.
- **No record of a hold** (this stage, round 2). Codex and Opus independently chose
  documenting the limit over writing a `held` record (breaks "only failures are
  recorded", adds a schema state and staged writes that strict mode would itself
  refuse) and over treating any non-default part as shared (a split ticket can keep
  a `default` part; it would carry forward a ticket sent back).
- **Epics cannot take a worktree under strict mode** (this stage, round 1), rather
  than gating epics.
