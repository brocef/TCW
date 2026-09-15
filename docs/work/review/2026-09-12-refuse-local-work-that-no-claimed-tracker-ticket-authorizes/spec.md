# Spec — Refuse local work that no claimed tracker ticket authorizes

## Capability changes

Planned deltas only.

| Capability | Delta | Why |
| ---------- | ----- | --- |
| `work/require-tracker-backed-work` | changed: `Missing` → `Supported`, with its first text | Seeded by the epic for this item. |
| `work/open-a-work-item` | changed | `tcw work new` refuses under strict mode. |
| `work/start-a-work-item` | changed | Under strict mode, `start` claims before the move and refuses when the claim does not succeed. |
| `work/drop-a-work-item` | changed | `drop` refuses an item that has ever been bound. |
| `work/manage-external-tracker-intake` | changed | `import` refuses to create an item when the claimed ticket shows a workflow that cannot exclude a second claimant. |
| `work/synchronize-external-tracker-work` | changed | Its text says nothing refuses local work; under strict mode some things do. |

**Not changed, on purpose:** `work/manage-the-work-inbox`. The epic's request says
the inbox capability is not to be changed, because a permissive filesystem inbox and
an authoritative tracker are different intake sources. `tcw work inbox accept` does
refuse under strict mode (§ 3), and that refusal is described in
`work/require-tracker-backed-work`, which is where a reader of strict mode looks.
`work/submit-a-work-item-for-review`, `work/rework-a-reviewed-work-item`,
`work/complete-a-work-item` and `work/discard-a-work-item` are likewise described
there rather than each gaining a strict-mode paragraph. `web` is not changed: the
web app refusing under strict mode is in the same text.

## Problem

`work.tracker` lets a project take tickets and keep them in step with items
(C1–C3), but nothing stops local work that no ticket authorizes. `tcw work new`,
`start` and every transition behave the same whether or not a ticket exists, is
claimed, or is held by someone else — C3 deliberately never refuses
(`tcw/tracker/sync.py` module docstring). `parse_tracker_config` reports `strict` as
an unknown key (`TRACKER_KEYS`, `tcw/store/base.py`;
`tests/test_tracker_validate.py::test_strict_is_reported_as_unknown`), so a project
cannot even ask.

Two further gaps the epic assigned here:

- **Nothing checks that a workflow can exclude a second claimant.** C1 reports it
  per ticket only when the ticket is already in the claim's destination
  (`tcw/tracker/claim.py`), and the epic's criterion 9 wants a refusal.
- **`drop` erases a bound item and its binding** with no record (`_drop`,
  `tcw/work/cli.py`).

## Goals

1. A project can set `work.tracker.strict: true`, and from then on local work
   happens only for items whose ticket is claimed by, and assigned to, the account
   the local credentials authenticate as — checked against the tracker at the moment
   of the change.
2. A refusal changes nothing locally, names what the tracker said, and names the fix.
3. The claim that authorizes work is one the workflow can make exclusive; when the
   ticket shows it cannot be, strict mode refuses rather than promising.
4. There is no bypass flag. Turning strict mode off is a reviewable edit to
   `tcw-config.yaml`.
5. With strict mode off or absent, everything behaves as C3 left it.

## Non-goals

- **Reading a project's workflow definition** (`POST /rest/api/3/workflows`). The
  epic said to settle whether a non-admin token can read it before designing around
  it, and this run has no Jira access to settle that. Filed as its own backlog item,
  not a child of the epic (§ 7).
- **Gating `tcw work edit`, artifact writes and `tcw work scaffold`.** They change an
  item's documents and fields, not whether work happens; every one of those files is
  also editable in a text editor, so a CLI refusal there would gate nothing.
- **Gating `tracker link` and `tracker unlink`.** `link` is how existing items come
  under strict mode; `unlink` is an audited repair that keeps its history.
- **Following the tracker** — unchanged from C3.
- **Records of refusals.** A refused change moved nothing, so C3's `sync` record —
  which says the ticket is not where the item's *committed* status says — does not
  apply, and writing one would rewrite a file criterion 7 says must not change. A
  refusal is reported, not recorded. The epic's C4 text says "recorded"; this spec
  changes it (§ 8).

## Design

### 1. Configuration

`work.tracker.strict`: a YAML boolean; absent means `false`. A non-boolean value is a
problem `tcw validate` reports.

Only a node with its own `work.tracker` block has a tracker at all (C1), so a node
without one is never strict, whatever its ancestors say. A gate for a qualified slug
(`<project-id>/<slug>`) reads the configuration of the node that slug resolves to.
A block that is not a mapping cannot say whether it is strict and is treated as not
strict; `tcw validate` reports it either way.

When `strict` is `true`, `tcw validate` also requires, offline:

- `statuses.active` and `statuses.completed`;
- `statuses.discarded` as one status name, or a mapping naming all three of
  `wontfix`, `duplicate` and `superseded`.

`transitions.claim` is already required. `statuses.review` stays optional.

**A broken block does not switch strict mode off.** `parse_tracker_config` fails
closed, returning no configuration on any problem, and every gate would then read
"no tracker". So the store answers `tracker_strict()` from the merged raw block:
`true` when the parsed configuration says so, and also when the configuration has
problems and the merged block's `strict` is present and not `false`. Every gate
consults `tracker_strict()` first; strict with no usable configuration refuses,
naming `tcw validate`.

`tracker_strict()` is a concrete `WorkStore` method returning `False` by default,
beside `tracker_config()` and `tracker_problems()` — a config-derived fact any store
can answer.

A child node inheriting the tracker block can set `strict: false`; that is still a
reviewable edit to a tracked file, and the capability says so.

### 2. The authorization check

One function in `tcw/tracker/sync.py`, `authorize(store, slug, client, config, *,
change)`, returning `None` when the change may go ahead, or a refusal reason. It
never writes. For a bound item:

1. A readable binding whose `ticket.url` is on the configured site (`same_site`).
2. No C3 `sync` value, a record or an unreadable one: either means an earlier change
   has not reached the tracker, and strict mode resolves that first — the reason
   names `tcw work tracker sync <slug>` and, for a record `sync` cannot clear,
   `tcw work tracker unlink`.
3. Read the ticket (`read_ticket`). Any tracker error refuses: an unreachable tracker
   means authorization is unknown.
4. **Assigned to the authenticated account.** Checked before anything else about the
   ticket, including "already where it should be" — C3's `assess_move` answers
   "current" before it checks assignment, so this check does not reuse that shortcut.
5. **In a status the item's current local status accounts for**: the mapped status
   of that local status or of an earlier one (`review` falls back to `active`, as
   C3's `expected_statuses` does), or already the change's target. The fallback is
   what lets a part whose ticket C3 *held* in `In Progress` — because another part
   shares it — go on to complete. Otherwise the ticket was moved in the tracker, and
   the change is refused.

The check runs for a mapped **and** an unmapped target: C3 returns silently when no
status is mapped, and strict mode does not.

### 3. The gates

Under strict mode (`tracker_strict()`), with a tracker configured:

| Command | Unbound item | Bound item |
| ------- | ------------ | ---------- |
| `tcw work new` (with or without `--parent`), `tcw work inbox accept` | refused: create work from a ticket with `tcw work tracker import` | — |
| `tcw work tracker import` | — | claims as today; then the exclusivity check (§ 4) before the item is created |
| `start` (with `--force` or `--take-over` too) | refused | claim **before** the move; refused unless the ticket is claimed, in `statuses.active`, and exclusive (§ 4) |
| `submit`, `rework`, `complete --resolution done` | refused | `authorize` before the move |
| discard (`complete --resolution <other>`), from any status | allowed | allowed |
| `drop` | allowed if the item has no `tracker.yaml` at all | refused: discard instead |
| `tracker sync` | — | as C3; a retried claim also runs the exclusivity check |
| anything on an item of `type: epic` | not gated | not gated |

Why:

- **Discarding authorizes no work**, from any status. Refusing it would lock a
  project out of its own backlog (epic Risk 6) and trap an item whose ticket was
  cancelled, reassigned, or held for another part; the epic's request says local
  intent is reconciled "using the normal TCW lifecycle". C3 still tries to move the
  ticket afterwards and, when it cannot, records that and exits 1, as it does today —
  the discard itself is never refused.
- **`drop` refuses any item that has a `tracker.yaml`**, bound or unlinked. A bound
  item's `drop` would erase its binding and history; refusing only bound items would
  let `unlink` then `drop` do the same. Discarding keeps the item.
- **Epics are not gated.** An epic coordinates children and is not itself work a
  ticket authorizes; gating it would make `new --epic`, `tcw work reconcile
  --complete-when-ready` (which completes an epic through the store,
  `tcw/work/recursion.py`), and every child's "epic must be active" rule unreachable.
  Its children are gated like any other item.

**Ordering.** Every gate runs after the command's own argument checks and before the
store is touched. For `start`, `submit` and `rework` that is after the `pre` hook. For
`complete` it is **before** the worktree merge-back and therefore before the `pre`
hook, which `_complete` runs after the merge: a refusal must leave the item, its
branch and its worktree exactly as they were.

For `start` of a bound item, the cheap local checks run first — the item is in
`backlog` (or `active` with `--take-over`), it has no unresolved blockers unless
`--force`, and an owner identity is set — so a start the store is certain to refuse
does not claim a ticket. The claim then runs, then `st.start`. If the store still
refuses (an inactive epic), the message says the ticket is left claimed and that
running `start` again once that is fixed completes it: the claim accepts a ticket
already assigned to the caller (row `1e`), as `import`'s failure window already works
(epic criterion 4).

`--force` and `--take-over` override local blockers and local claims only; they
never skip the tracker.

**This departs from the epic's identity rule 4**, which says a second developer who
starts a linked item "gets the local claim and no tracker claim". Under strict mode
they get neither; outside it, rule 4 stands as C3 built it. The epic's spec is
amended (§ 8).

**`tcw serve`.** The web app's create, start, complete and drop routes call the store
directly and run no hooks and no tracker code (`tcw/serve/__init__.py`), and its
sidecar route can write `tracker.yaml`. Under strict mode one check answers 409, with
a message naming the `tcw work` command to use instead, for create, start, complete
with `done`, drop, and a PUT of `tracker.yaml`; a discard through `complete` stays
allowed, as on the command line. Otherwise strict mode would be
honoured only on the command line — the half-honoured flag the epic forbids.

### 4. Exclusivity at claim time

The epic's authoritative check read the workflow definition. What this item builds
instead uses what the tracker already shows: **immediately after a successful claim,
the ticket is in the claim's destination, and if it still offers the claim transition
from there, a second claimant would succeed too.** That is C1's `assess()` verdict
`NOT_EXCLUSIVE` (`tcw/tracker/claim.py`), asked at the one moment it is decisive.

**A claim outcome is not always a landing.** Row `1e` reports "claimed" for a ticket
already assigned to the caller *wherever it is* — `In Review` included — without
applying the claim. So strict `start` first requires the claim outcome's status to be
`statuses.active`, refusing otherwise, and passes that status as `landing_status` to
`assess`.

Under strict mode, `import`, `start` and a claim retried by `sync` read the ticket's
offered transitions after claiming, and refuse when `assess(...)` says
`NOT_EXCLUSIVE`: `import` creates no item; `start` does not move the item; `sync`
leaves its record. On a workflow that offers the claim everywhere, a later `sync`
applies the claim transition again before refusing again; that is harmless on such a
workflow and is stated rather than prevented. The ticket stays claimed — the refusal says so and says TCW will
not move it back, since releasing a claim is itself a tracker write that could race.

What this does not prove: a workflow that hides the claim transition from one
account can still offer it to another. The epic's claim experiment used one account
(`jira-claim-experiment.md`). Stated in the capability rather than promised.

### 5. Messages

Every refusal is on stderr, exits 1, and starts with what did not happen:

- `tcw work submit: refused under strict tracker mode; <slug> was not changed. EX-1
  is assigned to Bob, not to you.`
- For a claim that happened but whose check refused:
  `tcw work start: refused under strict tracker mode; <slug> was not started. EX-1
  was claimed, but its workflow still offers 'Start Progress' from 'In Progress', so
  a second person could claim it too. TCW leaves the ticket claimed.`
- An unbound item: names `tcw work tracker link <slug> <ticket>` and, for `new`,
  `tcw work tracker import <ticket>`.
- A ticket not assigned to the caller, or moved in the tracker — the common state of
  items that were open before strict mode was turned on: names the manual fix (assign
  the ticket to yourself and put it in the status the item is in, in the tracker,
  then run the command again) and that discarding is always allowed.
- An unreachable tracker: `… <slug> was not changed. The tracker could not be
  reached (…), so whether this change is authorized is unknown. Run it again once
  the tracker answers.`
- A strict block with problems: `… the tracker configuration has problems, and
  strict mode refuses until it is fixed. Run \`tcw validate\`.`

### 6. Abstraction litmus test

| Operation | Verdict | Why |
| --------- | ------- | --- |
| `work.tracker.strict`, `tracker_strict()` | **store interface** (config) | A config-derived fact any store can answer; concrete with a `False` default. |
| `authorize`, the exclusivity check | **`tcw/tracker/`** | Tracker reads composed with store reads, beside `deliver`. |
| The gates | **CLI and `serve` coordinators** | Policy applied before abstract transitions. |

### 7. The workflow-definition read, parked

A backlog item — not an `--initiative` child — records the route, the three problems
the epic named (a project identifier no key holds, possible site-administrator
permission, no severity tier in `tcw validate`), and the prerequisite: a non-admin
token test against real Jira. It is not a child because it cannot be settled without
live access, and a child nobody can settle would hold the epic open indefinitely.

### 8. Changes to the epic's spec

- Criterion 9's second sentence (validate fails on a non-excluding workflow) is
  replaced by § 4's runtime refusal, tested against the fake's `GLOBAL` workflow. A
  network call cannot live in `tcw validate`.
- Criterion 7's "the refusal names the conflict" stands; "recorded" in § Design C4
  becomes "reported".
- Identity rule 4 gains the strict-mode exception in § 3.
- § Design C4's workflow-shape verdict points at the parked item.

## Acceptance criteria

Against the fake tracker, in nodes built with an explicit `strict` argument.
"Strict" means `strict: true` with the `statuses` block `active: In Progress,
review: In Review, completed: Done, discarded: Won't Do` on the fake's `SYNC`
workflow.

1. `tcw validate` exits non-zero and names the key for: `strict: "yes"`; strict
   without `statuses.active`; without `statuses.completed`; with `discarded` mapping
   only `wontfix`. `tcw work list` and `show` still exit 0.
   `tests/test_tracker_validate.py::test_strict_is_reported_as_unknown` is replaced
   by a test that a boolean `strict` is accepted.
2. A strict block with an unrelated problem (a bad `timeout-seconds`) still refuses
   `tcw work new`, naming `tcw validate`.
3. Strict: `tcw work new "x"` and `tcw work inbox accept <entry>` exit 1, create
   nothing, and name `tcw work tracker import`.
4. Strict: `start`, `submit` and `complete --resolution done` of an unbound item exit
   1 and leave the item where it was; discarding it exits 0.
5. Strict: `start` of a bound item whose ticket is unassigned in `To Do` claims it
   and starts the item, exit 0.
6. Strict: `start` of a bound item whose ticket is assigned to another account exits
   1, sends no write, leaves the item in `backlog`, and names the assignee. Same with
   `--force` and with `--take-over`.
7. **Epic criterion 7.** Strict: an active bound item whose ticket is reassigned to
   another account — `submit` exits 1, the item stays `active`, the message names the
   assignee, and no file under the item's folder changes (byte comparison).
8. **Epic criterion 11.** Strict: a hand-written `tracker.yaml` for a ticket assigned
   to nobody — `submit` is refused.
9. Strict, `SYNC`: a ticket moved in the tracker back to `To Do` refuses `submit`.
10. Strict, tracker down: `submit` exits 1, the item is unchanged, and the message
    says the local item was not changed and the tracker could not be reached.
11. Strict: a bound item with a C3 `sync` record refuses `submit`, naming
    `tcw work tracker sync`.
12. Strict, `GLOBAL` workflow: `tcw work tracker import` of an unassigned ticket
    exits 1, creates no item, and says the ticket was claimed and the workflow cannot
    exclude a second claimant; `start` of a bound item refuses the same way and the
    item stays in `backlog`.
13. Strict: `drop` of a bound item and of an unlinked one exits 1 and deletes
    nothing; `drop` of an item with no `tracker.yaml` succeeds. Discarding a bound
    item in `backlog` whose ticket nobody claimed, and a bound `active` item whose
    ticket is assigned to another account, each leaves the item `discarded` with no
    strict-mode refusal in stderr (C3's delivery still exits 1 for them).
14. Strict: `complete --resolution done` of a worktree item whose ticket is
    reassigned exits 1 before the merge-back: the branch is not merged into the
    primary checkout and the worktree still exists.
15. Strict, `SYNC`: `start` of a bound item blocked by an unresolved item exits 1
    and sends no write. `start` of a bound item whose ticket is already assigned to
    the caller in `In Review` (claim row `1e`) exits 1, and the item stays in
    `backlog`.
16. Strict: two parts of one ticket, both started and submitted (C3 holds the ticket
    in `In Progress`) — `complete --resolution done` of the first is not refused, and
    of the second moves the ticket to `Done`.
17. Strict: an epic can be created with `tcw work new --epic`, started, and completed.
18. Strict: `tcw serve`'s create, start, complete and drop routes, and a PUT of
    `tracker.yaml`, answer 409 and change nothing.
19. With `strict` absent, every test in `tests/test_tracker_sync.py` passes unedited,
    and a copy of criteria 1–4 of C3's spec run with `strict: false` passes.
20. **Epic criterion 8.** No refusal message contains the sentinel token.
21. `tcw validate`, `tcw capabilities check` exit 0; the capabilities in the table
    read their final text, and `work/require-tracker-backed-work` reads `Supported`.

## Risks

1. **Strict mode makes a tracker outage block work.** That is what a gate is; the
   capability says so plainly, and `tcw validate` still makes no call.
2. **The exclusivity check sees one account's view of the workflow.** Stated in the
   capability; the authoritative check is parked.
3. **A refused claim leaves the ticket claimed.** Releasing it automatically would be
   another write that can race; the message tells the person what state it is in.
4. **Every lifecycle command under strict mode now costs tracker reads before the
   move and C3's reads after it.** Accepted; reads are cheap next to a refused
   change.
5. **`serve` refusing under strict mode removes the web app's lifecycle buttons for
   such projects.** Accepted over a half-honoured flag.
6. **Decomposition gets harder.** `new --parent` and `new --initiative` are refused,
   and `tcw work tracker import` takes neither option, so under strict mode a child is
   made by importing and then linking with `tracker link`; nesting a child under a
   parent is not available. Filed as a follow-up rather than widened here.
7. **One claimed ticket can authorize any number of items** through `link` and
   `import --part`. That is C2's design; the capability says so.

## Notes

- **Spec review** (adversarial spec reviewer) of the first draft: blocking findings
  all accepted — parts held by C3 stuck in review (§ 2 step 5 fallback); criterion 13
  contradicting C3's discard exit code (discards allowed from any status, criterion
  reworded); `reconcile --complete-when-ready` unguarded (epics not gated); claim row
  `1e` from the wrong status passing (§ 4). Significant, accepted: discards from
  `active`/`review` no longer gated; cheap local checks before claiming; epics and
  decomposition added to Risks; manual fix named in messages; the `complete` ordering
  sentence corrected; the fake's missing "everywhere" workflow dropped from criterion 9;
  `tracker_strict()` scope stated. Not taken: dropping the web app's indicator.
- **Advisors consulted** (autonomous run; no user available): Codex and an Opus
  subagent on one brief.
  - *Workflow-shape verdict* — both chose the runtime check after a claim (option C),
    parking the workflow-definition read and rewriting criterion 9's second
    sentence. Taken. Opus also applied the check to every later change while the
    ticket sits in the claim's destination; not taken — the guarantee is about
    claiming, and later changes are gated by assignment.
  - *Gates* — both agreed with the five proposed and added more. Taken from both:
    unbound `submit`/`rework`/`done` refused; `inbox accept` and `new --parent`
    gated; `serve` refusing under strict; no `sync` record on a refusal; identity
    rule 4 amended; `--force`/`--take-over` are not bypasses; the gate before
    `complete`'s merge-back (Codex); authorization before C3's "already current"
    shortcut (Codex); an unmapped status still checked (Opus). Split: gating `edit`
    and artifact writes (Codex yes, Opus no) — not gated, for the reason in
    Non-goals. Split: a bound backlog item nobody claimed — Opus let its discard
    through, Codex wanted a claimed state for every mutation — Opus's taken, and the
    spec review widened it to every discard, because otherwise an item can be trapped
    with no way out but turning strict mode off. Codex's point that
    `unlink` then `drop` would bypass the drop refusal is taken (§ 3).
  - *Configuration* — both: `active`, `completed`, full discard coverage, boolean
    `strict`, offline. Opus: a broken block must not switch strict off — taken (§ 1).
  - *Unreachable tracker* — both: refuse. Codex: say "the local item was not
    changed", since a claim may have landed — taken (§ 5).
