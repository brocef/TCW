# Spec — Synchronize the work lifecycle outward to the tracker

## Capability changes

Planned deltas only; nothing is written to the ledger here.

| Capability | Delta | Why |
| ---------- | ----- | --- |
| `work/synchronize-external-tracker-work` | changed: `Missing` → `Supported`, with its first text | Seeded by the epic for this item. |
| `work/manage-external-tracker-intake` | changed | It says nothing claims a linked ticket; `start` now does. It also gains the refusal of a binding from another Jira site. |
| `work/start-a-work-item` | changed | `start` claims a bound item's ticket. |
| `work/read-a-work-item` | changed | `show` and `--json` gain the synchronization record. |
| `work/view-the-board` | changed | A bound row's ticket segment gains the record's state. |

The capabilities for `submit`, `rework`, `complete` and discarding are not
changed: what those commands do locally is unchanged, and what they now also do to
a ticket is the synchronize capability's text, which names them. No taxonomy
change: the `external-work-tracker` Feature covers all of it.

## Problem

A work item can be bound to a Jira ticket (`tracker.yaml`, written by
`tcw work tracker import` and `link` in `tcw/work/cli.py`), and after that the two
drift apart silently:

1. **Starting a linked item leaves its ticket where it was.** Since
   `2026-09-14-make-tracker-link-record-a-cross-reference-without-claiming-the-ticket`,
   `link` records a cross-reference and claims nothing, and `import` is the only
   command that claims (`_tracker_import`). `_start` contains no tracker code. The
   capability text says claiming a linked ticket is something "nothing does yet"
   (`tcw capabilities show work/manage-external-tracker-intake`).
2. **No other local transition reaches the ticket.** `_submit`, `_rework` and
   `_complete` contain no tracker code either. An item can be completed locally
   while its ticket stays In Progress.
3. **The configuration has nowhere to say where a ticket should go.**
   `TRACKER_TRANSITION_KEYS` in `tcw/store/base.py` is `{"claim"}`, and its comment
   names this item as the one that adds the rest.
4. **Nobody can see that a ticket is behind.** `tcw work show` and `tcw work list`
   print a binding's identity (the sibling
   `2026-09-12-surface-an-item-s-tracker-binding-in-the-board-the-projection-and-the-web-app`,
   "C5") and nothing about whether the ticket followed the item.

## Goals

1. `tcw work start` on a bound item claims its ticket, by the rules `import` uses.
2. `submit`, `rework`, `complete` and discarding move a bound item's ticket to the
   tracker status the project configured for the item's new local status.
3. A tracker that is down, refuses, or disagrees never undoes or blocks a local
   transition. The command says the item moved, says what the tracker did not do,
   and exits non-zero (epic criterion 5).
4. What did not reach the tracker is recorded, shown on the board and in `show`,
   and retried by `tcw work tracker sync [<slug> | --all]` without a second local
   transition.
5. TCW never follows the tracker, and never pulls a ticket back from where somebody
   else moved it.
6. No tracker configured, or an item with no binding, behaves exactly as today.

## Non-goals

- **Refusing local work.** Refusing `new`, `start` or any mutation because of what
  the tracker says is strict mode, in
  `2026-09-12-refuse-local-work-that-no-claimed-tracker-ticket-authorizes` (C4).
  This item never refuses a local transition for a tracker reason.
- **Progress links and comments** (the epic's goal 4 names "concise progress
  links"). Split into their own child of the epic; see Design § 8.
- **Following the tracker.** A ticket reassigned, reopened or closed in Jira is
  reported, never copied into the item.
- **Finding a path through the workflow.** A ticket that does not offer exactly one
  transition to the configured status is reported, never moved by chaining.
- **Setting Jira's resolution field.** Only the status moves.
- **Delivering transitions made through `tcw serve`.** The web app runs no hooks and
  no tracker code (`tcw/work/hooks.py` module docstring).
- **`tcw work drop` of a bound item.** `drop` deletes the item and its binding; a
  claimed ticket stays where it is. Refusing that is C4's (epic § Design C4).
- **The workflow-definition exclusivity check and the `strict` key** — C4.
- **Entries of `docs/work/inbox/2026-09-14-follow-ups-the-tracker-link-review-left.md`.**
  Entry 2 (a binding write on an item waiting for deletion makes `delete` refuse)
  is the reason § 5 writes no record on such an item; the entry itself stays open.
  Entries 1, 3 and 4 concern resolved-item bindings and dead claim fields this item
  does not touch.

## Design

### 1. Configuration: the status each local status maps to

A new optional block, `work.tracker.statuses`:

```yaml
work:
    tracker:
        transitions:
            claim: Start Progress
        statuses:
            active: In Progress
            review: In Review
            completed: Done
            discarded: Won't Do          # or, per resolution:
            # discarded:
            #     wontfix: Won't Do
            #     duplicate: Duplicate
```

- Keys are local statuses: `active`, `review`, `completed`, `discarded`. Values are
  tracker **status** names, matched trimmed and case-folded like `transitions.claim`
  (`_normalize`, `tcw/tracker/claim.py`). `discarded` may instead map discard
  resolutions (`wontfix`, `duplicate`, `superseded`) to status names; a resolution
  it leaves out sends nothing.
- Every key is optional; a local status with no mapping sends nothing. **`active`
  is required once any other key is set**, because every later move checks where
  the ticket is expected to be (§ 4), and the chain of expectations starts at
  `active`.
- An unknown key, a non-string value, an unknown resolution, and a block without
  `active` are problems `tcw validate` reports, and a block with problems fails
  closed as the rest of `work.tracker` does (`parse_tracker_config`). Parent-node
  inheritance merges the block key by key with no new code (`merge_tracker_blocks`).

**Why statuses and not transition names — a departure from the epic, stated.** The
epic's spec keys the mapping on the move with a transition name, and derives
delivery "from the observed remote state plus deterministic event ids". A
transition name cannot say where a ticket should *be*: Jira reports a transition's
destination only while the ticket offers it (`JiraClient.transitions`,
`tcw/tracker/jira.py`), so once a ticket is where the move leads or has moved on,
"already delivered" (epic criterion 6) cannot be told from "never delivered". A
status can be compared with the ticket directly, and delivery applies whichever
offered transition leads there — which also works on Jira's default simplified
workflow, where every transition is offered from every status
(`jira-claim-experiment.md` § 1). The moves still key on `TRANSITION_IDS` in the
record below; only the target is a status.

### 2. When delivery happens

After a local transition of an item whose `WorkItem.tracker` is a binding, in a node
with a tracker configured:

| Local command | Move | Delivered |
| ------------- | ---- | --------- |
| `start` (including `--take-over`) | `start` | the claim (§ 3) |
| `submit` | `submit` | the ticket to `statuses.review` |
| `rework` | `rework` | the ticket to `statuses.active` |
| `complete --resolution done` | `complete` | the ticket to `statuses.completed` |
| `complete --resolution <other>` | `discard` | the ticket to `statuses.discarded` for that resolution |

- **After the store move, and after `post` hooks.** The local move never depends on
  the tracker. A move that raised `TransitionCommitError` or `PublicationError` did
  happen, so delivery runs for it too before the command exits 1. For `start
  --worktree`, delivery runs before the worktree is set up, so a worktree failure
  does not skip it. For `complete`, delivery runs before the automatic removal of an
  item the project does not retain (§ 5).
- **No tracker configured** (`tracker_config()` is `None` and `tracker_problems()`
  is empty): nothing happens and nothing is printed. **A tracker block with
  problems**, on a bound item, is **pending** with the problems as the reason.
- **An unbound or unreadable binding:** nothing is delivered. An unreadable binding
  already reports itself wherever the item is read.
- **`tcw.tracker` is imported only for a bound item with a tracker configured.** The
  decision reads `WorkItem.tracker` and the store's configuration, neither of which
  imports it, so `tests/test_tracker_absent.py` keeps holding.
- **Parts.** When another **open** item in this node is bound to the same ticket
  (another `--part`), a status move is **held**: nothing is sent, nothing recorded,
  and the command prints one note naming the other items. The last open part to
  move delivers. The claim at `start` is not held. Items in other nodes or clones
  are invisible, which the capability says.

### 3. The claim at `start`

`claim()` from `tcw/tracker/intake.py`, unchanged, against the ticket the binding
names by its stored id. Outcome:

- **Claimed** (rows `1e`, `3a`): when `statuses.active` is mapped and the ticket is
  not in it, **conflicting** ("claimed, but in 'X', not 'In Progress'"); otherwise
  **current**. Row `1e` accepts a ticket already assigned to the caller in any
  status, so this check is what stops a mistyped claim name, or a take-over of an
  item whose ticket sits in `In Review`, from reading as current.
- **Refused by the tracker's answer** (`1a`, `1b`, `1c`, `1f`, `3b`, `3c`, `3d`,
  `3e`): **conflicting**.
- **A tracker error, `3-read` or `3f`:** **pending**.

**A claim that did not succeed is owed** (`claim: owed` in the record, § 5). Every
later delivery and every `sync` for the item retries the claim **first**, and does
nothing else until it succeeds. So a failed claim followed by `submit` does not
silently become a status move on a ticket nobody took. Starting locally rather than
refusing follows the epic's identity rule 4 — a developer who starts a linked item
"gets the local claim and no tracker claim", refused only in strict mode.

### 4. A status move — the rules

*target* is the mapped status for the item's new local status (per resolution for a
discard). *expected* is where the ticket should be before the move:

- with a record (§ 5): the record's `since`, **or** the target of the record's
  `move` — so a user who moved the ticket by hand to where TCW meant to put it is
  not punished;
- otherwise: the mapped status of the item's previous local status, falling back
  through earlier mapped statuses in the order `review` → `active`. A previous
  status of `backlog` has none.

Then:

1. No *target* → nothing to deliver, silently.
2. The binding's site (§ 6) differs from the configured one → **conflicting**, with
   no request sent.
3. Read the ticket, its offered transitions, and the authenticated account
   (`read_ticket`). Error → classified by § 7.
4. Ticket already in *target* → **current**, with nothing written to the tracker
   (epic criterion 6).
5. Ticket not assigned to the authenticated account — someone else, or nobody →
   **conflicting**. Nothing here assigns.
6. *expected* known and the ticket in neither of its statuses → **conflicting**:
   somebody moved it, and TCW does not pull it back. *expected* unknown (a discard
   of an item never started): a ticket whose status category is done →
   **conflicting**; any other passes.
7. Offered transitions leading to *target*: none → **conflicting**, naming what the
   ticket offers; more than one → **conflicting**, naming the ids; one → apply it.
8. Re-read, and decide from the re-read as `claim` does. In *target* and assigned to
   the caller → **current**. Otherwise, the transition's error (if any) classified
   by § 7; no error → **conflicting**, naming where the ticket is.

These rules are one function over a ticket read and the item, with no side effects
until step 7, so C4 can call steps 2–6 before a mutation to refuse it.

### 5. The record: only what did not reach the tracker

`tracker.yaml` gains an optional `sync` mapping, written with `write_sidecar` (so
staged, like every binding write), only when a delivery ends **pending** or
**conflicting**:

```yaml
sync:
    state: pending            # or conflicting
    move: submit              # a TRANSITION_IDS value
    since: In Progress        # empty when unknown
    claim: done               # or owed
    reason: the tracker at https://site.atlassian.net could not be reached (…)
    at: '2026-09-14T10:00:00Z'
```

- A delivery that ends **current** removes an existing `sync` and otherwise writes
  nothing, so a ticket that followed first time costs no file change and no commit.
  There is no event log and no event id: the item's committed local status says
  where the ticket should be, and the record only says it is not there yet — which
  is how this design meets the epic's "no second cleanup commit" without event ids.
- A later transition while a record exists keeps the record's `since` and `claim`,
  and replaces `move`, `state`, `reason` and `at`.
- `reason` is TCW's sentence, cut to 300 characters, plus nothing a credential could
  be in (the error types in `jira.py` carry no credential; epic criterion 8).
- `unlink` removes `sync` with the binding — a change to `unlink_document`, whose
  `_BINDING_KEYS` does not include it today. `link` never writes one.
- **A record that cannot be read does not unbind the item.** `classify_binding`
  keeps the binding bound and gives the record as `{"problem": reason}`; delivery and
  `sync` treat it as no record and overwrite it. So a hand-broken record cannot make
  `link`, `unlink`, `import` or `find_binding` refuse.
- **No record on an item waiting for removal.** A resolved item the project does not
  retain is removed only when git holds all of it (`_require_retrievable`,
  `tcw/store/fs.py`), so a staged record would make the removal, and `tcw work
  delete`, refuse. When such an item's delivery is not current, no record is
  written, the automatic removal is skipped, and the message says to move the
  ticket in the tracker by hand (or run `tcw work tracker sync <slug>`, which checks
  but cannot move without a record) and then run `tcw work delete <slug>`.
- `WorkItem.tracker`'s bound value gains `sync`: `null`, the record, or
  `{"problem"}` — each closed in `WORK_ITEM_SCHEMA`. C5 is unreleased, so its shape
  changes without a version bump.

### 6. A binding from another Jira site

Before any tracker call made for a binding, its `ticket.url` must parse to the
configured `base-url`'s scheme and host (case-insensitive) with a path under
`base-url`'s path followed by `/browse/`. An empty or unparseable URL fails. The
check is one helper in `tcw/tracker/intake.py`.

`find_binding` uses it too: a binding with the same ticket id whose URL is on a
different site makes it raise `BindingProblem` naming that item and both sites,
instead of treating an unrelated ticket as already bound — the direction
`docs/work/inbox/2026-09-14-a-tracker-binding-does-not-record-its-site.md` suggests,
including not adding the site to the key. That makes the inbox note resolved by
this item.

### 7. Classifying tracker errors

- **Pending** (the tracker was not reached, or cannot yet be asked):
  `TrackerUnavailable`, `TrackerRateLimited`, `TrackerAuthError` (including absent
  credentials), and a tracker block with problems.
- **Conflicting** (the tracker answered, and the answer stops the move):
  `TrackerRequestInvalid` (400), `TrackerPermissionError` (403), `TrackerNotFound`
  (404), and any other `TrackerError`.

A pending record is expected to clear by itself on a later `sync`; a conflicting one
needs a person, and the reason says what the tracker said.

### 8. `tcw work tracker sync [<slug> | --all]`

- `<slug>`: one bound item in this node, any status. `--all`: every item in this
  node, resolved items the store still holds included, whose binding has a record.
  Exactly one of the two.
- **Only the item's owner acts.** Records are committed with the item and reach
  other clones, and `sync` acts as whoever runs it, so an item whose `owner` is set
  and is not the local identity (resolved as `start` resolves it: `TCW_WORK_OWNER`,
  then git `user.email`, then `user.name`) is reported
  `<slug>: skipped — started by <owner>` and left untouched. That comparison stays
  inside the local-owner namespace, so identity rule 3 (never compare a Git identity
  with a Jira account) holds. Items with no owner (never started) are acted on.
- For each item acted on: an owed claim is retried first (§ 3); then the status-move
  rules run for the item's current local status (§ 4). The record is updated as § 5
  says.
- **An item with no record** (reachable only with `<slug>`) is checked and never
  moved: without a record, "not where the item says" is indistinguishable from a
  ticket somebody moved, or a transition made in `tcw serve`. It prints `current`
  when the ticket is at its target, else `conflicting — …`, and writes nothing.
- One line per item: `<slug>: current`, `<slug>: pending — <reason>`,
  `<slug>: conflicting — <reason>`, or the skipped line. Exit 0 when every item it
  acted on is current, 1 otherwise; the existing messages and exit 1 when no tracker
  is configured or the slug is not a bound item here.

### 9. What the commands print

- **Current:** what the command prints today. `start` adds
  `→ claimed EX-1: now in 'In Progress' and assigned to you.` on stderr, since taking
  a ticket is news. A held move adds `→ EX-1 not moved: also bound to <slug>.`
- **Pending or conflicting:** the usual success lines, then on stderr
  `tcw work <verb>: <slug> moved to <status> and was committed; EX-1 was not updated
  in the tracker (<state>): <reason>. Run \`tcw work tracker sync <slug>\` once that
  is resolved.` — exit 1, the convention `_post_result` already uses for "moved, but
  something after the move failed".
- **`show`:** after the `tracker:` line, `tracker sync: <state> after <move> (<at>):
  <reason>`, adding `; the claim is still owed` when it is; or
  `tracker sync: record cannot be read (<reason>)`.
- **`list`:** ` | ticket: EX-1 (pending)`, ` | ticket: EX-1 (part api, conflicting)`.
- **Web app:** the Ticket field appends ` · pending: <reason>` or
  ` · conflicting: <reason>`.

### 10. Progress links are split off

Both advisors and the spec review agreed that moving status without links is fine
only if the split is explicit in the epic. Links need something stable to link to —
TCW neither pushes branches nor requires `work.repository.url` — and a comment needs
its own de-duplication against the ticket's comments. Neither is needed for the
status to be right.

Taken: a new child of the epic, created with `--initiative`, holds progress links and
comments, and the epic's goal 4 names it. Being a child, it keeps the epic open until
it is built or deliberately discarded; that is the reversible choice, since a
completed epic cannot be reopened while a discarded child costs nothing. It is not
built in the run that builds this item.

### Abstraction litmus test

| Operation | Verdict | Why |
| --------- | ------- | --- |
| `work.tracker.statuses` | **store interface** (config) | A config-derived fact, parsed purely like the rest of `work.tracker`. |
| The `sync` record and `WorkItem.tracker.sync` | **model** | Portable data through the abstract sidecar surface. |
| Deciding current / pending / conflicting, parts, the site check | **neither — `tcw/tracker/`** | Operations on the tracker composed with store reads, beside `claim`. Nothing enters `WorkStore`. |
| Delivery after a transition, `sync` | **CLI coordinator** | Composes the store's transition with the tracker module, as `import` does. |
| Transition discovery, HTTP | **adapter private detail** | Unchanged, in `jira.py`. |

## Acceptance criteria

Tests use `tests/tracker_fake.py`, which this item extends: statuses `In Review`,
`Won't Do` and `Duplicate` with their categories; a `SYNC` workflow with
`To Do → In Progress (Start Progress)`, `In Progress → In Review`,
`In Review → In Progress`, `In Review → Done`, `In Progress → Done`, and discards
to `Won't Do` and `Duplicate` from `To Do`, `In Progress` and `In Review`; a `down`
switch that makes every request raise `TrackerUnavailable`; and a way to install two
fakes chosen by `client.config.base_url`. "Configured" means the `statuses` block of
§ 1 unless a criterion says otherwise. "No write" means the fake recorded no `POST`
or `PUT`.

1. `start` on a bound item whose ticket is unassigned in `To Do`: exit 0, item
   active, ticket `In Progress` assigned to the caller, stderr has the claimed line,
   no record.
2. `start` on a bound item whose ticket is assigned to another account: exit 1, item
   active and committed, no write, record `conflicting` with `move: start` and
   `claim: owed`, stderr names the assignee and says the item moved.
3. After criterion 2, the other account unassigns the ticket and the caller runs
   `submit`: the claim is retried first and succeeds, then the ticket moves to
   `In Review`; exit 0 and no record.
4. **Epic criterion 5.** `submit` on an active item whose ticket is claimed, with the
   fake `down`: exit 1, item in `review`, record `pending`, stderr says the local move
   happened. With the fake up, `sync <slug>` exits 0, moves the ticket to
   `In Review`, removes the record, and the item's status and the number of commits
   touching its folder are unchanged by the `sync`.
5. **Epic criterion 6.** `submit` when the ticket is already `In Review` and assigned
   to the caller: exit 0, no write.
6. A delivery that succeeds first time leaves `tracker.yaml` byte-identical.
7. `complete --resolution done` from `review` moves the ticket to `Done`. With
   `review` unmapped, `complete --resolution done` from `review` checks against
   `In Progress` and moves it. `complete --resolution duplicate` with
   `discarded: {duplicate: Duplicate}` moves it to `Duplicate`; `--resolution
   wontfix` with that mapping sends no write and exits 0.
8. `rework` after a delivered `submit` moves the ticket from `In Review` to
   `In Progress`.
9. A ticket moved in the tracker to a status that is neither expected nor the target
   is not moved by `submit` — exit 1, `conflicting`, no write — on the `SYNC`
   workflow and on `GLOBAL`, where the transition to the target is offered.
10. With a pending `submit` record and the ticket moved by hand to `In Review`,
    `complete --resolution done` moves it to `Done`.
11. A ticket assigned to another account, or to nobody, is not moved by `submit`,
    `rework`, `complete` or a discard; each records `conflicting`.
12. A ticket offering no transition to the target, or two, records `conflicting`
    with the offered names or ids in the reason.
13. A transition answered with 400 records `conflicting`; one answered with 503, or
    a missing credential variable, records `pending`.
14. Two items bound to one ticket (parts `api` and `web`), both active and claimed:
    completing `api` sends no write, exits 0, and names `web`; completing `web` then
    moves the ticket to `Done`.
15. A binding whose `ticket.url` is on another site makes `start`, `submit` and
    `sync` send no request to either fake and record `conflicting`. With colliding
    ticket ids on two fakes, `tracker import` of the new site's ticket refuses naming
    the old item, where before this change it reported "already bound".
16. `sync --all` visits exactly the items with a record, including a retained
    completed item, skips an item whose `owner` is another identity without a
    request or a write, and exits 1 while any it acted on stays pending or
    conflicting. `sync <slug>` on an item with no record whose ticket is not at its
    target sends no write, writes nothing, and exits 1.
17. A `sync` record made unreadable by hand (`sync: 5`) leaves `link`-time checks,
    `unlink` and `import` of another ticket working, `show` reports
    `tracker sync: record cannot be read`, and the next delivery overwrites it.
18. `show` prints the `tracker sync:` line for an item with a record and none
    without; `list` ends `| ticket: EX-1 (pending)`; `show --json` validates against
    `WORK_ITEM_SCHEMA` with `tracker.sync` null, a record, and a problem; the web
    app's Ticket field shows the state (`vitest`).
19. On a node with `work.retain` not keeping `completed`, a `complete` whose delivery
    is pending writes no record, keeps the item, exits 1, and names both the manual
    fix and `tcw work delete`; `tcw work delete <slug>` then succeeds.
20. **Epic criterion 1.** With no `work.tracker` block and an item that has a
    `tracker.yaml`: `start`, `submit`, `rework` and `complete` exit 0, no output line
    mentions the tracker, and in a fresh interpreter no `tcw.tracker` module is
    imported. `tests/test_tracker_absent.py` passes unedited.
21. **Epic criterion 9, C3's part.** `tcw validate` exits non-zero and names the key
    for an unknown key under `statuses`, a non-string status, an unknown discard
    resolution, and `review` set without `active`; `tcw work list` and `show` still
    run.
22. **Epic criterion 8.** With a sentinel token in the credential variable, no
    delivery or `sync` outcome — current, pending, conflicting — puts it in any file
    in the work store, in stdout or in stderr.
23. **Epic criterion 11.** A hand-written `tracker.yaml` for a ticket assigned to
    another account does not let `submit` move it.
24. `unlink` removes a `sync` record with the binding.
25. `tcw validate` and `tcw capabilities check` exit 0, and the capabilities in the
    table read their final status and text.

## Risks

1. **A crash between the local commit and delivery leaves no record**, and so does a
   transition made in `tcw serve`: the board reads current for a ticket that did not
   move, and `sync` can check it but never move it. Accepted and said in the
   capability: "current" means "no undelivered change is recorded". Recording intent
   before the move would need a write after every successful delivery.
2. **Never pulling a ticket back can strand one.** It stays conflicting until someone
   puts it where the item says or moves the item. The reason names both statuses.
3. **Two undelivered changes collapse into one target**, which a directed workflow
   may not offer in one step; reported as conflicting.
4. **A workflow with several transitions into one status** is always conflicting
   for that status. Not verified against a company-managed workflow; an optional
   transition-name choice per status is the fix if it proves common.
5. **Every lifecycle command of a bound item can now exit 1 on the network**, even
   without credentials, and a linked ticket held by someone else makes each of that
   item's commands exit 1 until it is unlinked or claimed. The item always moves and
   the message says so. This is epic criterion 5 applied as written; C4's strict mode
   is where refusing instead lives.
6. **Parts in other nodes or clones are invisible**, so a ticket shared across
   repositories can still be closed early.
7. **Departing from the epic's wording** (statuses, no event ids) is recorded in § 1
   and § 5 and in the epic's spec.

## Notes

- **Advisors consulted** (autonomous run; no user available): Codex and an Opus
  subagent on one brief; then an adversarial spec review of the first draft.
  - *Claim failure at `start`* — split. Codex: refuse the local start. Opus: start
    locally and record it. **Taken: Opus's**, for the stronger, repository-grounded
    argument — the epic's identity rule 4 says a developer who starts a linked item
    "gets the local claim and no tracker claim" and is refused only in strict mode;
    the epic's request says missing credentials must not affect filesystem mutations
    when strict mode is off; and "claim must succeed before the item is created or
    linked" is about `import` and `link`. Codex itself noted refusing would require
    changing rule 4. The spec review agreed.
  - *Other transitions* — agreed: never claim, move only a ticket assigned to the
    caller, unassigned counts as not assigned, decide from a re-read, a rule for
    shared parts.
  - *Mapping and record* — Codex preferred an event log with explicit target
    statuses; Opus, status targets with a record written only on failure and a drift
    check. **Taken: Opus's shape**, with each hole either advisor named closed:
    *expected* stops tickets being pulled back, `active` is required, per-resolution
    discard statuses, no multi-step paths, delivery before removal, `sync --all`
    covering resolved items. Codex's crash-visibility point is Risk 1.
  - *Progress links* — both advisors and the review: acceptable only if explicit in
    the epic; the review and Codex preferred a child. Taken: a child (§ 10).
  - *Site check* — both advisors: every write and `find_binding`, empty URL refused,
    two fakes by site. The review suggested leaving `find_binding` to the inbox note;
    not taken, because both advisors said include it and it is the same helper.
  - *The spec review's blocking findings, all accepted:* *expected* for an unmapped
    previous status (§ 4 fallback); a failed claim lost when a later move overwrote
    the record (`claim: owed`, § 3); a record on an item waiting for removal making
    `delete` refuse (§ 5); an unreadable record unbinding the item (§ 5); `sync --all`
    acting on a teammate's items (owner rule, § 8). *Significant, accepted:* check
    the ticket is in `statuses.active` after a claim (§ 3); 400/403/404 are
    conflicting (§ 7); accept a hand move to the record's target (§ 4); deliver after
    a move whose commit failed and before worktree setup (§ 2); make C3 blocked by C5.
    *Narrowed:* the least-advanced rule for parts became "hold while another open
    part exists", which the review proposed. *Not taken:* an optional transition-name
    choice per status (Risk 4), and leaving the web app's indicator out.
- **Inbox notes folded in:** `2026-09-14-a-tracker-binding-does-not-record-its-site.md`
  (§ 6) — resolved by this item.
- **The previous child's shapes change here:** `WorkItem.tracker` gains `sync`, and
  the board segment gains a state. Both were designed for this (C5's spec, Risk 3),
  and neither has been released.
