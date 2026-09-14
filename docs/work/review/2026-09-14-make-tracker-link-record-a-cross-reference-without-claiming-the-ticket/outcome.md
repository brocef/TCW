# Outcome — Make `tracker link` record a cross-reference without claiming the ticket

Every acceptance criterion is met. Seven commits, one per plan task except that
tasks 5–7 collapsed for the reasons below, plus a capability commit the plan had
no task for.

## What shipped

| Commit    | Task | What                                                                                                 |
| --------- | ---- | ---------------------------------------------------------------------------------------------------- |
| `79236a2` | 1    | `claimed-by` out of the binding document; `_binding_for` retyped to three ticket values              |
| `2a3cd97` | 2    | `link` stops claiming                                                                                |
| `dd9b790` | 3    | `link` and `unlink` accept resolved items; `_unresolved_item` → `_item_or_reason`                    |
| `4d745cd` | 4    | `description=` / `epilog=` / positional `help=` on the five `tracker` parsers, and their tests       |
| `9a9a610` | 5    | `help=` on every positional CLI-wide, and the walking test                                           |
| `4fea5cb` | 8    | README, release notes, changelog, `skills/tcw-work/references/commands.md`                           |
| `a7719c9` | —    | The capability body and the item's `capabilities.yaml`                                               |

Task 6 (full-suite green) is not a commit; it is the gate each of the others
passed. Task 7 was already done — see below.

**Tests:** `pytest` green — 3112 passed, 1 skipped, on the branch rebased onto
`origin/main` at `e4d96f7`. `tcw validate` OK,
`tcw capabilities check` OK. `grep -rn "claimed-by" tcw/` is empty; the only
occurrences left in `tests/` are absence assertions and the deliberate `LEGACY`
fixture. `test_a_ticket_assigned_to_someone_else_is_refused_naming_them` and
`test_a_ready_unassigned_ticket_is_transitioned_then_assigned` both still pass
**unedited**, which is what shows `claim` itself was not reached into.

**Help read by hand**, as the plan's Verification asks: all five `--help` outputs
were rendered and read. That pass found a real defect the tests could not — see
"hand-wrapping" below.

## What the plan and spec got wrong

- **Task 7 was already complete.** The plan says the sibling item
  `2026-09-12-synchronize-the-work-lifecycle-outward-to-the-tracker` "has no
  artifacts at all today" and tells this item to write its `initial-request.md`
  and add the blocker. Both were already in the tree, landed by `f4debdb`
  ("Merge tracker-link cross-reference planning") after the plan was written.
  Its request carries the section "this item now owns claiming a linked ticket",
  and `state.yaml` lists this item as a blocker. Verified, not redone.

- **`RawDescriptionHelpFormatter` does not wrap, and the plan did not say so.**
  Task 4 says to give each parser that formatter and a `description=`. Written
  as ordinary prose, the description then prints as one unwrapped line however
  narrow the terminal — which the structural tests of criteria 14–15 cannot see,
  because a long line satisfies "a description exists". The descriptions are
  hand-wrapped to 70 columns to match the epilogs. This is exactly the case the
  plan flagged when it said the prose quality needs a human read.

- **Task 5's "watch it fail with 46" was not observable in that order.** Task 5's
  `tcw/taxonomy/cli.py` and `tcw/capabilities/cli.py` half was delegated and
  landed before the walking test was written, so the test first went red with 26.
  The 46 was confirmed instead by stashing the delegated change and running the
  same walk: 46 total, 31 under `tcw work` (5 of them `tracker`), 7 taxonomy,
  8 capabilities — the spec's number and its breakdown exactly. The walk is right.

- **The spec required a capability edit that no plan task carried.** The spec's
  § Capability changes says two sentences of
  `work/manage-external-tracker-intake` stop being true and that the delta is
  recorded at implementation. Task 8 lists only the four documentation entries,
  so the capability body and the item's `capabilities.yaml` would have been
  missed by working the plan alone. Both are in `a7719c9`.

- **Criterion 3 was stronger than the plan's edit for it.** The plan says to
  replace one assertion in the renamed body test. The criterion says a
  byte-for-byte snapshot of *every* other file is equal and the item's status and
  owner are unchanged; the test compared two named files and nothing else. It now
  diffs the whole folder minus `tracker.yaml` and checks status and owner, behind
  `_assert_only_the_binding_changed`.

## Notes

- **Two tests were added beyond the plan**, turning a hand check into coverage.
  The plan's Verification says to confirm by hand that a binding written before
  this change still reads and that `unlink` does not crash on its stale key.
  `test_a_binding_written_before_claiming_was_dropped_still_reads_as_bound` and
  `test_unlinking_an_old_binding_leaves_its_stale_claim_behind` assert both, so
  the no-migration decision is pinned rather than remembered. They cover
  `unlink_document` directly rather than through the CLI; the CLI path adds only
  a sidecar read.

- **Every new test that passed on its first run was mutation-checked**, and the
  failure message read rather than just observed:
  `test_unlinking_an_old_binding_leaves_its_stale_claim_behind` (put `claimed-by`
  back in `_BINDING_KEYS` → the key moves into the history entry),
  `test_link_refuses_an_unknown_ticket` (make the fake resolve any key → the link
  succeeds, proving it is the ticket read that refuses), and
  `test_link_refuses_a_slug_that_does_not_exist` (change the message → red on the
  message, not on the exit code). `LEGACY` was checked against `BINDING` to prove
  it is not a fixture that differs in nothing.

- **The two resolved-item tests assert the refusal they replace is absent**, not
  only that the command now exits 0, so deleting the message would not leave them
  green for the wrong reason.

- **Two dead imports** (`A`, `BASE_URL` in `tests/test_tracker_link.py`) were
  dropped in passing. `A` died with this change; `BASE_URL` was already unused.

- **`docs/release-notes/v2.1.2.md` still says `link` "takes a ticket for an item
  you already have"** and is deliberately left alone: a shipped release note is a
  historical record, and it was true of 2.1.2.

- **The `find_binding` limit is documented in four places now** — the docstring,
  the README's limits list, the skill reference, and the capability — because it
  became reachable by one more path and nothing refuses it.

- **Rebased onto `origin/main` at `e4d96f7`** after implementation. The two
  `upcoming.md` files conflicted, both purely additively — main added the skill
  ledger entries, this item added the tracker-link ones — and were resolved by
  keeping both. `tcw capabilities check` and `tcw validate` still pass against
  main's reworked ledger, which deleted nine capabilities but not this item's.

- **`tcw work start` was run before the first code edit**, while the tree was
  clean, since this repository's guide warns against driving the lifecycle with
  the `tcw` CLI once `tcw/` is being changed. The rest of the CLI use here was
  read-only (`validate`, `capabilities check`, `--help`) or against code this
  change does not touch.
