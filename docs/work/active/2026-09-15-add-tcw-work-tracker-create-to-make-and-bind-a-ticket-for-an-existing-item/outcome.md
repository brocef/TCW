# Outcome

Both landings shipped. `tcw work tracker create` makes a ticket for an item that
has none and binds it, and `work.tracker.create.on-new` makes filing an item
create its ticket.

## What shipped, task by task

### Landing A — the command

| Task | What | Commit |
| ---- | ---- | ------ |
| 1 | `statuses.backlog` accepted by `tcw validate` | `b3b543fa` |
| 2 | the `work.tracker.create` block, failing closed | `823eca0e` |
| 3 | `tcw/tracker/create.py` — `create_and_place` and `JiraClient.create_issue` | `3fa2a30a` |
| 4 | the `tcw work tracker create` subcommand, binding through `link` | `d86b51d8` |
| 5 | re-running creates one ticket | `d86b51d8` |
| 6 | an interrupted run binds the recorded key | `52bb0c09` |
| 7 | `--dry-run` and `--all` | `d86b51d8`, `52bb0c09` |
| 8 | Landing A gate | superseded — see "The gates" |

### Landing B — creation on filing

| Task | What | Commit |
| ---- | ---- | ------ |
| 9 | `create.on-new`, off by default | `823eca0e`, `69601c56` |
| 10 | `tcw work new` and `inbox accept` of a raw entry create the ticket | `69601c56` |
| 11 | an unreachable tracker owes a ticket, visible on the board | `69601c56` |
| 12 | `strict` with `on-new` is a configuration error | `69601c56` |
| 13 | command, configuration and skill documents | `40f11d28` |
| 14 | release notes and changelog | `40f11d28` |
| 15 | final gate | see below |

Two commits are neither plan tasks nor documentation. `59afd4d8` and `17517fc8`
act on review findings during implementation; `103a303d` addresses the rest of
the multi review.

## What the plan and spec got wrong

**The plan's correction to task 1 was itself wrong, and it shipped a silent
regression.** I wrote that `statuses.backlog` could not affect `sync`, reasoning
that `_RUNG_ORDER` has no backlog rung. That much is true and beside the point:
`deliver` calls `target_status(config.statuses, item.status, ...)` directly
(`tcw/tracker/sync.py:316`), so the moment `backlog` became a legal key, `sync`
began pulling a bound backlog item's ticket *backwards* — with no error. Found by
reproducing it, fixed by never computing a target for a backlog item whatever
`statuses` says, and pinned by
`test_a_bound_backlog_items_ticket_is_never_moved`. This is the worst thing in
the item: a correction made from reading one function and not its callers.

**Spec criterion 3 named the wrong key.** It said the refusal names
`work.tracker.statuses.<status>`, implying it depends on the item's own status.
It does not: every created ticket is placed at the backlog status whatever the
item's status is, so `backlog` is the only entry creation can be missing.
Corrected in the spec and in plan task 4.

**"Walks the workflow's transitions as `sync` already does" overstated both.**
Spec Rule 3 and plan task 3 read as a multi-hop search. Neither `_place` nor
`assess_move` does that: both take one hop chosen by its destination, treat a
ticket already in the target as nothing to do, and refuse rather than guess when
a workflow offers two ways in. `_place` is also not `assess_move` — that function
asks questions meaningless a second after creation, such as whether the ticket is
assigned to you.

**The spec's non-goal about closed items was not enforceable as written.** It
listed backfilling `completed` and `discarded` items as out of scope but nothing
refused one, so the command would have created a ticket in the backlog status for
finished work and then had to walk it forward and resolve it. Now refused by
name.

**Task 11's owed state could not literally reuse the sync record.**
`classify_binding` only parses `sync` for a *bound* item, and an item owing a
ticket has no binding. It is a sibling key in the same sidecar, read by the same
code path — one mechanism with one more key, not the second pending-work system
the plan warned against. `WorkItem.tracker` gained a fourth shape for it.

## What review found that the plan did not anticipate

- **Workflows with no triage column.** Most Jira projects create issues straight
  into their backlog status, and Jira offers no self-transition, so `_place`
  demanded a hop that does not exist and refused *after* making the ticket. Every
  fixture used this project's shape. Found by Codex.
- **Accepted is not applied.** `apply_transition` reports only that Jira accepted
  the request; a validator can decline it silently. The status is now read back.
- **Everything locally refusable is refused before the ticket exists.** `--part`
  validation and the ownership check ran inside `_tracker_link`, after creation.
  Found by Codex.
- **A test that guarded nothing.** The only test covering the `verb` refactor
  never entered `_tracker_link` — it returned at an earlier refusal, and passed
  with the whole refactor reverted.
- **A disk failure while recording the created key escaped as a traceback**, and
  a create response naming no key was carried into placement. Both found while
  building task 6.

## The gates

Landing A's own gate (task 8) did not produce a usable result. The run was still
in progress when Landing B's edits began landing in the same tree, so what it was
measuring stopped being any commit; it was killed rather than reported. Landing A
is still independently shippable — the commits are ordered so it can be — but the
evidence for it is the final gate below, not a separate one.

The final gate (task 15) ran against the tree at **`40f11d28`**, after the last
commit, with the commit read before and after the run:

```
3859 passed in 893.51s (0:14:53)
pytest_exit=0
tcw validate: OK
validate_exit=0
40f11d288d09f499e755277b091567a486da5b09
```

The exit code is captured on its own line rather than taken from a pipeline.
Earlier in this item a commit went through on a red suite because the run was
piped into `tail`, whose exit code is the one the shell reports.

## The review round of 2026-09-21, and what it found

The multi review at `17517fc8` covered about half of what shipped. Everything
from task 6 onward — `--all`, the resumption record, and the whole of Landing B
— went through a second round on 2026-09-21: two adversarial reviewers and
Codex, on `17517fc8..2fb6908a`. The local model (`bllm`) has been disabled for
maintenance for seven days and gave no answer; that is recorded in the `llama`
repository's work inbox.

Eighteen findings were verified against the tree. Five were serious enough to
stop a merge, and two of those were crashes reproduced end to end through the
real CLI against a real node:

- `_deliver_after` raised `KeyError: 'ticket'` on an item carrying an owed
  record — on `start`, `submit`, `rework` and `complete`, *after* the status
  move had been committed. This is the flagship path: file on a train, then
  start the work.
- `_siblings` raised `KeyError: 'project'`, and it scans every item in the
  store, so one owed item anywhere took tracker delivery down for every other
  properly bound item on the node.

Both had one cause. `binding_value` gained a fourth shape and has three readers;
each spelled its guard as "not a `problem`" rather than "has a `ticket`", and
only one of the three was updated. `outcome.md` already confessed to exactly
this failure for `statuses.backlog` — "a correction made from reading one
function and not its callers" — and it was repeated inside the same item. The
fix is one predicate, `bound_value`, that every reader asks.

The other three that blocked:

- `_sweep_order` decided "already bound" with `"ticket:" not in found.content`.
  An unlinked item keeps its former binding under `unlinked:`, which contains a
  nested `ticket:`, so `--all` silently walked past exactly the items somebody
  had unlinked in order to re-create — confirmed live. It also failed the
  abstraction litmus test outright: a store serialising the sidecar as JSON
  would read *every* bound item as unbound and duplicate a ticket for the whole
  board.
- The web client's `TrackerField` threw on the owed shape, and that app has no
  error boundary, so the page rendered blank rather than losing one field.
- `POST /api/work` ignored `create.on-new` entirely, so an item filed on the web
  board was indistinguishable from one filed in a project that never turned the
  setting on — the accumulation the owed record exists to prevent.

**The tests could not have caught the sweep defect.** `_board` took no status
and filed everything with `tcw work new`, so every item was `backlog`. The
status filter, the unbound filter and the held-by-someone-else skip could each
be deleted with all 58 tests in the file still green — proved by deleting them.
That is the shape `docs/lifecycle/implementation.md` forbids, and
`_created_node`, fifteen lines above it in the same file, carries a docstring
explicitly refusing to default `status` for that reason. Two other assertions
guarded nothing: `test_all_sweeps_up_owed_tickets` passed with the binding call
replaced by `return 0`, and `"owed" not in item.tracker` is true for every bound
item whatever is on disk, because `binding_value`'s `Bound` branch never emits
it.

Three claims in the spec were wrong and had been repeated into shipped text:

- Rule 6 promised `tcw work tracker sync` would settle an owed ticket. It never
  could: `sync` is about a binding, and an item owing a ticket has none.
- Rule 7 rejected `strict` with `create.on-new` as contradictory. `_new` exempts
  epics from strict mode's refusal and creation-on-filing covers them, so the
  pair is coherent — and rejecting it made `tracker_config` fail closed, taking
  `import`, `link`, `sync` and `claim` down with it.
- The reason given for including epics — that an epic with no ticket "breaks its
  children's parent links" — describes a capability TCW does not have. It sets
  no parent link and `create_issue` takes no parent. The conclusion survives;
  the reason had reached the command's help text and the user guide.

Every fix carries a test that was watched to fail first, or a mutation that was
run to prove the test guards what it claims.

## Notes

- **The four live Jira checks were run on 2026-09-20**, against
  `proposit.atlassian.net`, from a throwaway node, using throwaway items the
  user approved. All four passed, and the first of them proved the hazard is
  real rather than theoretical: Jira created TCW-55 in **Triage** — the exact
  status `inbox-query` selects — and creation moved it to `To Do`. The issue's
  own changelog records the hop, and `tcw work inbox list` afterwards returned
  none of the eight tickets made. The refusals fired before anything reached
  the tracker (a Jira search for the refused summary returned zero issues); the
  sweep made four tickets with distinct keys, epic first and Epic-typed; and the
  owed path ran end to end, recording the debt with a bad token and clearing it
  with a good one. The eight tickets were moved to `Won't Do` afterwards.
- The live node also reproduced both crashes found in review, and both were
  re-run against the fix.
- GitHub #43 is answered and closed after publication, not at completion, per
  this project's sequencing rule.
