# Plan — Make and bind a ticket for a work item, on demand and on filing

Fifteen tasks in **two landings**, matching the spec's first risk. Landing A
(tasks 1–8) is the command; Landing B (tasks 9–12) is creation on filing and
cannot be built first. The suite is green at every commit boundary and at the
boundary between landings, so Landing A can ship alone if B is deferred.

Ordering principle: the **creation operation** exists before either caller
(task 3), the **refusal that makes the inbox-query trap unreachable** lands with
the status mapping it depends on (tasks 2–3), and the two **idempotency** paths —
re-run and interrupted-run — get tasks of their own (tasks 5, 6) because a
double-create in a shared tracker is not undoable from TCW.

---

## Landing A — `tcw work tracker create`

### Task 1 — Let `statuses` name `backlog`

**Files:** `tcw/store/base.py`, `tests/test_tracker_validate.py`

Add `"backlog"` to `TRACKER_STATUS_KEYS` (`tcw/store/base.py:1141`). The parse
loop at `tcw/store/base.py:1360-1363` then accepts it and still refuses anything
else.

State in the comment above `statuses` (`tcw/store/base.py:1093-1095`) that
`backlog` is read by creation **and** by `sync`, so a project that sets it is
asking for backlog tickets to be held there, not only started there. Absent —
the default — nothing changes for anyone.

**Proves it:** a test that `{"statuses": {"backlog": "To Do"}}` parses with no
problems, and that `{"statuses": {"nonsense": "X"}}` still yields
`work.tracker.statuses.nonsense: unknown key`. The first fails today with
`work.tracker.statuses.backlog: unknown key` — verified by running
`parse_tracker_config` against that input before the change (spec criterion 4).

### Task 2 — The `work.tracker.create` configuration block

**Files:** `tcw/store/base.py`, `tests/test_tracker_validate.py`,
`tests/test_tracker_inheritance.py`

Add `create` to `TRACKER_KEYS` (`tcw/store/base.py:1114`) and a parsed shape on
`TrackerConfig` (`tcw/store/base.py:1061`) holding, at minimum: the issue type
rules, the parent rule, and any fixed fields (components) a created ticket
carries. Follow the existing keys' conventions — hyphenated in YAML, snake on
the dataclass, problems reported as `work.tracker.create.<key>: …`.

**Issue type is configured, never literal.** The reporter's Epic/Bug/Task rule
is expressed as configuration with those as the documented default, so a project
whose tracker has different types is not broken by a constant in the source
(spec Rule 2).

Inheritance comes for free — `create` sits inside the block that
`tcw work tracker` already inherits from parent nodes — but assert it, because
"comes for free" is the claim that is wrong most often.

**Proves it:** parse tests for each key and each malformed shape; an inheritance
test that a child node with no `create` block uses its parent's.

### Task 3 — The create-and-bind operation

**Files:** `tcw/tracker/create.py` (new), `tcw/tracker/jira.py`,
`tests/test_tracker_create.py` (new)

One operation, in the tracker layer beside `import` and `link`, which for one
item: builds the ticket content (summary from title, description from
`initial-request.md` or `intake.md`), creates it, moves it to the status mapped
for the item's status, and writes the binding.

It reuses `tcw/tracker/intake.py`'s `binding_document` and `find_binding` rather
than writing a second binding format, and the status walk reuses whatever `sync`
already uses to reach a status — **not** a single hard-coded transition. The
2026-09-20 backfill needed `Accept` to reach `To Do`, and the transition's name
is not the target's name.

`tcw/tracker/jira.py` gains issue creation and transition-listing if it does not
already expose them.

**Refuses when no status is mapped** for the item's status, creating nothing —
spec Rule 3, and the reason the inbox-query trap is unreachable rather than
unlikely.

**Derives claim from the item, not from a flag.** A backlog item's ticket is
left unassigned; an `active` item's is claimed and assigned, as
`tcw work tracker link --sync-status` does. The backfill had to remember this
per item; the operation must not (spec Notes).

**Proves it:** tests against a stubbed tracker client for content, status
movement, the refusal, and the claim asymmetry. Spec criteria 1 and 3.

**Spec criterion 2 is not unit-testable and is discharged at `verify`.** It asks
that the created ticket be absent from what `work.tracker.inbox-query` selects,
and that query is JQL the tracker evaluates — a stub asserting it would be
asserting its own arithmetic. What the tests here *can* pin is the step that
makes it true: the ticket ends in the mapped status. The end-to-end check is
Verification item 1, and it is the reason that item exists.

### Task 4 — Wire `tcw work tracker create <slug>`

**Files:** `tcw/work/cli.py`, `tests/test_tracker_cli.py`

Register the subcommand beside `link` (`tcw/work/cli.py:3382`) and route it to
task 3. Flags: `--type`, `--parent`, `--dry-run`.

**Proves it:** `tcw work tracker create <slug>` binds the item and
`tcw work list` shows `ticket: <key>` (spec criterion 1); the refusal in
criterion 3 exits non-zero and names `work.tracker.statuses.<status>`.

### Task 5 — Re-running creates one ticket

**Files:** `tcw/tracker/create.py`, `tests/test_tracker_create.py`

An item that already has a binding is skipped and the command exits zero,
reporting the existing key. No second ticket is requested from the tracker —
asserted on the stub's call log, not only on the resulting binding, because a
create followed by a discard would leave the binding right and the tracker
wrong.

**Proves it:** spec criterion 5.

### Task 6 — An interrupted run resumes by linking

**Files:** `tcw/tracker/create.py`, `tests/test_tracker_create.py`

The created key is recorded **before** the binding is attempted, so a crash
between the two leaves a key that the next run binds rather than replaces. This
is the half-state the backfill script's key log existed to survive.

**Proves it:** a test that starts from a recorded key with no binding, runs
create, and asserts the tracker received **no** create call and the item is now
bound to the recorded key (spec criterion 6).

### Task 7 — `--dry-run` and `--all`

**Files:** `tcw/work/cli.py`, `tcw/tracker/create.py`,
`tests/test_tracker_cli.py`

`--dry-run` reports what would be created and makes no write, local or remote —
asserted against the stub's call log as well as the tree (spec criterion 7).
`--all` walks every unbound open item, skipping bound ones, and reports per item
(spec criterion 8). Epics before their children, so a child's parent link can
point at a ticket that exists.

### Task 8 — Landing A gate

**Files:** none

`pytest` and `tcw validate`, both clean. Landing A is shippable here: the
command works, nothing about filing has changed, and criterion 9's "default off"
is trivially true because the setting does not exist yet.

---

## Landing B — creation on filing

### Task 9 — The setting, off by default

**Files:** `tcw/store/base.py`, `tests/test_tracker_validate.py`

The key under `work.tracker.create` that turns filing-time creation on, default
**off**. Parse and inheritance tests as in task 2.

**Proves it:** with the key absent, `tcw work new` makes no tracker call at all —
asserted with no credentials in the environment, so a call would fail loudly
rather than silently succeed (spec criterion 9).

### Task 10 — `tcw work new` and `inbox accept` create the ticket

**Files:** `tcw/work/cli.py`, `tests/test_tracker_cli.py`,
`tests/test_stdin_cli.py` (where `tcw work new`'s piped-intake path is covered)

Call task 3's operation from `_new` (`tcw/work/cli.py:418`) and from
`_inbox_accept` (`tcw/work/cli.py:590`) for a **raw** entry. Accepting a ticket
key is already `import` and is untouched.

**Epics included**, departing from strict mode's `and not args.epic`
(`tcw/work/cli.py:422`) — an epic with no ticket breaks its children's parent
links (spec Rule 5).

**Proves it:** spec criteria 10, 12 and 13.

### Task 11 — An unreachable tracker owes a ticket

**Files:** `tcw/work/cli.py`, `tcw/tracker/create.py`, `tcw/tracker/sync.py`,
`tests/test_tracker_sync.py`

When creation is enabled and the tracker cannot be reached, the item is still
created, the command exits zero and says the ticket is owed, and the owed state
is recorded in the **existing** sync record (`tcw/tracker/intake.py`'s
`with_sync_record`) rather than a second pending-work mechanism.
`tcw work tracker sync` then creates and binds it.

**The owed state must be visible on the board**, not only in a sidecar —
spec Risks. Surface it in `tcw work list` the way `ticket:` already appears.

**Proves it:** spec criterion 11, including that a `sync` after a retried filing
does not double-create — the interaction of tasks 6 and 11.

### Task 12 — `strict` and creation-on-filing together are a config error

**Files:** `tcw/validate.py`, `tcw/store/base.py`, `tests/test_tracker_validate.py`

`tcw validate` reports the combination as a problem naming both keys. Either
alone validates (spec criterion 14).

**And assert the untouched path:** `strict: true` alone still refuses
`tcw work new` with today's wording pointing at `tcw work tracker import`.
Written as criterion 15 — the absence of a change — because every other
criterion here is about new paths, so nothing else would notice if this broke.

---

## Documentation Sync

Evaluated against `tcw work docs`. One pass over the finished diff, after task 12.

| Entry | Trigger | Fires? |
| --- | --- | --- |
| `README.md` | Public-API | **Yes** — task 13 |
| `docs/guide/jira.md` | Tracker-Change | **Yes** — task 13 |
| `docs/guide/<topic>.md` | Guide-Topic-Change | **Evaluate** — task 13 |
| `docs/release-notes/upcoming.md` | Public-API | **Yes** — task 14 |
| `docs/changelogs/upcoming.md` | Any-Code-Change | **Yes** — task 14 |
| `skills/<component>/SKILL.md` | Skill-Driven-Component | **Yes** — task 13 |
| `skills/configure/references/<document>.md` | Configuration-Key-Change | **Yes** — task 13 |

### Task 13 — Command, configuration and skill documents

**Files:** `README.md`, `docs/guide/jira.md`, `skills/work/SKILL.md`,
`skills/work/references/commands.md`, `skills/configure/references/tracker.md`

- `docs/guide/jira.md` — the largest change: a new command, a new config block,
  `statuses.backlog`, and the three-arrangement table from spec Rule 7.
- `skills/configure/references/tracker.md` — the `create` block and
  `statuses.backlog`; it already documents `strict` at
  `skills/configure/references/tracker.md:120`, and that paragraph now has to
  say what happens when both are set.
- `README.md` — the `tcw work tracker` row gains `create`.
- `skills/work/SKILL.md` and its `commands.md` — the new verb, and the fact that
  filing can now produce a ticket, which changes what an agent should expect
  from `tcw work new`.
- `docs/guide/<topic>.md` — evaluate `multi-repo.md`, which discusses per-node
  configuration; expected no change, but say so in `outcome.md` rather than
  leaving it unmentioned.

### Task 14 — Release notes and changelog

**Files:** `docs/release-notes/upcoming.md`, `docs/changelogs/upcoming.md`

Release notes must carry the migration-shaped warning from spec Risks: **a
project that already sets `statuses` will have its first `tracker create`
refused** until it adds `backlog`. That is correct behaviour and a surprise, so
it belongs in the notes rather than in a support conversation.

**Do not cut a version.** That is a human step.

### Task 15 — Final gate

**Files:** none

`pytest` and `tcw validate` clean, against the final tree, with the SHA recorded
in `outcome.md`. Re-run the whole suite **after** the last commit — an earlier
green run against an earlier commit is not evidence, which this repository
learned the hard way on the previous item.

## Verification

What the suite cannot check, for `verify`:

1. **A real ticket, created against real Jira.** Every test here uses a stubbed
   client. Run `tcw work tracker create` once against the live TCW project for a
   throwaway item, confirm the ticket lands in `To Do` and not `Triage`, then
   run the configured `inbox-query` and confirm the key is absent. This is the
   hazard the whole spec is built around and no stub can prove it.
2. **The refusal fires before anything is created.** With `statuses.backlog`
   unset, run creation and then query the tracker for issues created in that
   window: there must be none. A refusal after a create is the bad outcome and
   looks identical locally.
3. **`--all` on more than a handful.** Run it against this repository's own
   board on a scratch Jira project. 53 items is where an idempotency bug becomes
   53 duplicate tickets rather than one.
4. **The owed path end to end.** Break the network, file an item, confirm it
   exists and says the ticket is owed, restore the network, run
   `tcw work tracker sync`, confirm exactly one ticket.

## Notes

- **Landing A is independently shippable**, and the plan is ordered so it can be.
  If Landing B turns out to need its own spec once A exists, decompose then —
  folding the *request* was deliberate and does not oblige a single landing
  (spec Risks).
- **Task 11 is the riskiest and is scheduled after its infrastructure**, per the
  plan-stage rule: it depends on task 3's operation, task 6's resumption
  record and the existing sync machinery all being in place.
- **No blockers.** The four in-flight tracker items — the claim/status-movement
  epic and its children — all concern already-bound tickets and none touches
  creation. `2026-09-15-write-work-item-properties-to-mapped-tracker-fields`
  (GitHub #37) is `related`: it writes item properties onto a bound ticket and
  its own notes keep it separate.
- GitHub #43 is answered and closed after publication, not at completion, per
  this project's sequencing rule.
