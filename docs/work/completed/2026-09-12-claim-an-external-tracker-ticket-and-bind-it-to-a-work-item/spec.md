# Spec — Claim an external tracker ticket and bind it to a work item

Child C2 of `2026-08-04-supplement-filesystem-tcw-work-with-an-external-tracker-bridge`.
The epic's spec fixes this item's boundary, its identity rules and five of its
acceptance criteria; this document decides the rest. Every `file:line` below was
read at `29d832e7` and re-checked at `7eccfcff`.

**Revised 2026-09-14 after an adversarial review**, before planning. What was
accepted, narrowed and rejected is in `## Notes`.

## Capability changes

Planned deltas only; nothing is written to the ledger here.

| Capability | Delta | Now |
| ---------- | ----- | --- |
| `work/manage-external-tracker-intake` (`cap-bd57b7`) | `Missing` → `Supported` at completion, with a `description.md` describing what shipped | Seeded by the epic's plan task 6: `Status: Missing`, `Feature: external-work-tracker`, `Planning doc` this item. `tcw capabilities check` exits 0. |

No other capability changes. `work/inspect-external-tracker-work` (C1's) still
describes `list` and `show` truthfully; this item changes neither command.
`work/manage-the-work-inbox` is deliberately untouched, per the epic.
`work/open-a-work-item` is not changed: `tcw work new` behaves as before, and
import is a separate way in that belongs to this item's own capability.

The epic's `capabilities.yaml` already lists this path under `new:`, so the
epic's completion gate covers it. C1 kept no `capabilities.yaml` of its own, and
this item follows it.

`tcw capabilities search` for `intake`, `tracker`, `import` and `claim` found
nothing this contradicts.

## Problem

C1 lets a developer read tickets (`tcw work tracker list`, `show`) and nothing
more: the `tracker` group's help text says "read the configured external tracker
(read-only)" (`tcw/work/cli.py:1981`), and `JiraClient` has four read operations
and no write (`tcw/tracker/jira.py:184-234`). Three gaps follow.

1. **Taking a ticket is a manual, two-system operation.** The developer moves the
   ticket in Jira, runs `tcw work new`, and pastes the ticket's text. Nothing
   stops the local item being created when the Jira move failed, or the Jira move
   happening without an item.
2. **Nothing records that an item answers a ticket.** The sidecar registry holds
   `capabilities.yaml` and `rollup.md` only (`tcw/store/base.py:1928-1943`), and a
   ticket key in a title is prose no command can read.
3. **Nothing prevents two items for one ticket.** `create_work` derives a unique
   slug from the date and title (`tcw/store/fs.py:6045`), so running the same
   manual steps twice silently produces a second item.

The epic's experiment settled how a claim must be detected
(`jira-claim-experiment.md`): a transition's response carries no reliable reason
for failing — three different `HTTP 400` bodies for one condition, one blaming
permissions for a lost race — so whether a claim worked is decided by reading the
ticket back.

## Goals

1. `tcw work tracker import <ticket>` claims the ticket in the tracker and then
   creates a backlog item bound to it. If the claim does not end with the ticket
   in the status the claim leads to and assigned to the signed-in account, no
   item is created.
2. A ticket may be claimed when it is unassigned or already assigned to the
   signed-in account. Claiming an unassigned ticket assigns it. A ticket assigned
   to anyone else is refused, and the refusal names the assignee and the status.
3. The binding is a machine-readable `tracker.yaml` sidecar, written by a command
   and never offered for editing in the web app.
4. Within one working copy, importing the same ticket and part twice produces one
   item, and a different part deliberately produces another. (Other working
   copies see a binding only once it is committed and pushed; see Non-goals.)
5. A claim that succeeded in the tracker but did not finish locally completes when
   the same command is run again.
6. `tcw work tracker link <slug> <ticket>` binds an existing unresolved item by the
   same claim rules. `tcw work tracker unlink <slug> --reason <text>` removes a
   binding and keeps a record of it and the reason.
7. The ticket's product text lands in the item's intake with its origin; the
   `request` stage still has to run.
8. A project with no tracker configured behaves exactly as it does today on every
   command. The one visible difference is in the web server's API, not the app:
   `GET /api/work/<slug>/sidecars` lists every registered sidecar name, present or
   not (`tcw/serve/__init__.py:635-647`), so it gains a `tracker.yaml` entry with
   `present: false`. The web client shows only present sidecars
   (`web/client/src/ui/content-views.tsx:548-554`).

**On a workflow that can exclude a second claimant**, two accounts racing get
exactly one winner: the loser's transition is refused, a refused transition is
never followed by an assign, so the loser's read-back never shows the ticket as
its own. **On a workflow that cannot exclude**, two accounts may both succeed. The
user decided at the `request` stage that import should not check or warn about
this ("We don't care if multiple claimants is possible or not"), so it does
neither, and no criterion here promises a single winner there.

## Non-goals

- **Judging whether the workflow excludes a second claimant.** No check, no
  warning, no refusal. The user's decision; see Goals. C1's `assess` still reports
  it under `tracker show`.
- **Two imports by the same account at the same moment.** Both are "you", so the
  read-back cannot tell them apart, and both may create an item — two agents
  sharing one set of credentials included. **The user decided this on 2026-09-14,
  after review:** accept it and document it, add no lock. A duplicate made this way
  is visible on the board and removable with `tcw work drop`.
- **Idempotency across working copies.** Import stages its files and commits
  nothing, like `tcw work new`, and resolved items are not tracked by Git at all
  (`.gitignore:29-32`). So the same account importing the same ticket in a second
  clone or worktree before the first binding is pushed gets a second item. This
  is the same boundary every uncommitted local change has.
- **Resolved items in the lookup.** A completed or discarded item's binding is not
  consulted, so a ticket whose item was discarded can be imported again. `link` and
  `unlink` refuse resolved items.
- **Setting `owner`.** Epic identity rule 1: importing is not starting.
- **Import options beyond `--part` and `--title`.** Priority, tags, blockers,
  initiative and parent are set afterwards with `tcw work edit`, as they are for
  any item.
- **Qualified slugs.** `link` and `unlink` take a bare slug of this node, not the
  `<project-id>/<slug>` form `_resolve` accepts for other commands
  (`tcw/work/cli.py:127`). A tracker configuration and project id belong to one
  node, and choosing which one for a qualified slug is not worth deciding for a
  repair command.
- **Any change to the tracker from `unlink`.** It is a local repair; the command
  says the ticket is unchanged.
- **A `tcw validate` check for bindings.** Import and link already refuse a
  malformed or duplicated binding when they meet one. A validate check would also
  run as this repository's `pre` hook on `complete` (`tcw-config.yaml:62-65`), so
  one bad binding would block completing every unrelated item.
- **Converting Jira's rich-text description format.** Jira's v2 issue endpoint
  returns the description as a plain wiki-markup string (verified live; see
  Notes), which is adequate raw input.
- **A server-side refusal of writes to generated sidecars.** `PUT
  /api/work/<slug>/sidecars/<name>` accepts any registered name
  (`tcw/serve/__init__.py:1281-1305`); `generated` is only reported to the client
  (`tcw/serve/__init__.py:646`). That gap also affects `rollup.md`, and the epic
  says to file it separately.
- Outbound sync and `tracker sync` (C3); strict mode, `drop` refusal for bound
  items, workflow-definition reads (C4); showing the binding in `list`, `show`,
  `--json` or the web app beyond the raw sidecar the app already lists (C5);
  inheriting `work.tracker` from parent nodes
  (`2026-09-14-inherit-work-tracker-from-parent-nodes-key-by-key`).
- **No new configuration key.** Everything needed is derived from the existing
  `transitions.claim` and from the ticket.

## Design

### 1. The claim

A new module `tcw/tracker/intake.py` holds the claim sequence and the binding
rules, taking a `JiraClient` and plain values. The client gains the writes.

**Client changes** (`tcw/tracker/jira.py`), all through the existing `_request`
seam and therefore under its timeout:

- `apply_transition(issue_id, transition_id)` —
  `POST /rest/api/3/issue/{id}/transitions`.
- `assign(issue_id, account_id)` — `PUT /rest/api/3/issue/{id}/assignee`.
- `description(issue_id)` — `GET /rest/api/2/issue/{id}?fields=description`,
  returning the string or `""`.
- `issue(key)` URL-quotes the key it inserts into the path (today it is inserted
  as typed, `tcw/tracker/jira.py:214`). Every later request uses the issue's
  numeric `id` from that first read.
- The module docstring's "read-only" description changes.

`status.statusCategory` already arrives inside `status`
(`tests/fixtures/tracker/conforming-ready-issue.json`).

**Identity** is `myself()["accountId"]` (`tcw/tracker/jira.py:184`), compared
against `fields.assignee.accountId`. Never display names, which are not unique.

**Step 1 — read.** `issue(key)`, `transitions(id)`, `myself()`. Then, in order:

| # | Ticket as read | Outcome |
| - | -------------- | ------- |
| 1a | `status.statusCategory.key` is `done` | Refuse: resolved. |
| 1b | Assigned to another account | Refuse, naming the assignee and status. |
| 1c | `assess(...)` verdict `AMBIGUOUS` (`tcw/tracker/claim.py:99-108`) | Refuse with `assess`'s detail. |
| 1d | Claim transition offered | Step 2. The **landing status** is that transition's destination (`tcw/tracker/claim.py:111`). |
| 1e | Claim not offered, assigned to this account | **Already yours.** Bind without a transition, and say "not claimed by this run: <KEY> is already in '<status>' and assigned to you". |
| 1f | Claim not offered, unassigned | Refuse: "<KEY> is in '<status>', unassigned, and does not offer '<claim>'. It offers: …". **No advice to assign it** — the account reading this may not be the one that moved it. |

Row 1e is what makes goal 5 work on a workflow that excludes. After a claim, that
ticket no longer offers the claim, and nothing the ticket returns says where the
claim led: C1 recorded that asymmetry (`tcw/tracker/claim.py:79-92`), and on
2026-09-14 `GET …/transitions?includeUnavailableTransitions=true` on the claimed
`TCWCLAIM-1` returned only `Finish`, the same as without it. So assignment to this
account is the evidence used. Its cost is Risk 1.

**Step 2 — claim.**

1. `apply_transition` with the id `assess` matched. The result is one of:
   - **applied** — a success response;
   - **refused** — `TrackerRequestInvalid`;
   - **unknown** — `TrackerUnavailable`, or any other `TrackerError` not listed
     next (a timeout may have applied);
   - **stop** — `TrackerAuthError`, `TrackerPermissionError`, `TrackerRateLimited`
     or `TrackerNotFound`: end the command with C1's message for that cause. The
     transition did not apply, and no read-back is done.
2. **Only if the transition was applied**, and the ticket was unassigned at step 1,
   `assign` it to this account. Any `TrackerError` from `assign` is recorded as
   **assign failed** and does not end the command.

Transition first, assign second, and assign only after an applied transition:
that rule is what keeps a loser on an excluding workflow from ever overwriting the
winner's assignment. Assigning first would let two accounts overwrite each other
before either transition ran.

**Step 3 — read back.** `issue(id)` again. If the read itself fails: refuse,
saying the claim's result is unknown and that running the command again will find
out. Otherwise, with *landed* meaning the status equals the landing status (C1's
normalized comparison) and its category is not `done`:

| # | Read back | Outcome |
| - | --------- | ------- |
| 3a | Assigned to this account, landed | **Claimed.** Bind. |
| 3b | Assigned to another account | Refuse: "not claimed: <KEY> is assigned to <name> in '<status>'". If the transition was applied, add "this run's transition applied; the assignment is theirs". |
| 3c | Assigned to this account, not landed | Refuse: "the claim did not take effect: <KEY> is assigned to you but is in '<status>', not '<landing>'". |
| 3d | Unassigned, transition refused | Refuse: "the claim did not apply: <KEY> is in '<status>', unassigned". |
| 3e | Unassigned, transition applied | Refuse: "<KEY> moved to '<status>' but is not assigned to you", plus the assign error when there was one, plus "assign it to yourself in the tracker, then run this command again". Safe to say here: this run's transition is the one that moved it. The re-run reaches row 1e. |
| 3f | Unassigned, transition unknown | Refuse: "could not tell whether this run's claim applied: <KEY> is in '<status>', unassigned. Check the ticket's history in the tracker before assigning it." |

Every pair of transition result and read-back maps to one row: a read-back
assigned to this account is 3a or 3c; to another, 3b; unassigned, 3d, 3e or 3f by
transition result. A refusal's first line is fixed text as above; a transport
message, when carried, is on a following line starting `detail:` and is never the
explanation.

### 2. The binding

`tracker.yaml` joins `WORK_SIDECARS` (`tcw/store/base.py:1928`):

```python
"tracker.yaml": {
    "media_type": "application/yaml",
    "validation": "yaml_mapping",
    "generated": "yes",
},
```

`generated` is the epic's Risk 1: the web client renders an edit button for every
sidecar not marked generated, and `rollup.md` is the precedent
(`tcw/store/base.py:1936-1942`).

The document:

```yaml
schema: 1
provider: jira-cloud
project: <the node's project id>
part: default
ticket:
    id: "<tracker issue id>"
    key: <canonical key>
    url: <base-url>/browse/<canonical key>
claimed-by:
    account-id: <accountId>
    name: <displayName>
bound: "<ISO date>"
unlinked: []
```

- **`project`** comes from the abstract `ProjectRegistry.current`
  (`tcw/store/base.py:186-189`), passed into `intake.py` as a string;
  `tcw/tracker/intake.py` does not import the filesystem registry.
- **The ticket is identified by `id`, not `key`.** Jira changes an issue's key when
  it moves between projects; its id does not. The key is taken from the tracker's
  response, not from what the user typed (a lowercase `tcwclaim-1` resolves live).
- **No credential and no e-mail address.** Epic identity rule 2: `claimed-by` is a
  separate field from `owner` and never overwrites it.

**Reading a binding.** For one item:

- no `tracker.yaml` → **unbound**;
- the file does not parse to a mapping → **malformed**;
- no `ticket` key → **unbound** (the state `unlink` leaves);
- `ticket` present, and it is a mapping with non-empty string `id` and `key`, and
  `provider`, `project` and `part` are non-empty strings → **bound**;
- `ticket` present in any other shape → **malformed**.

**The idempotency key** is `(project, provider, ticket.id, part)`. `part` must
match `[a-z0-9][a-z0-9-]*` and defaults to `default`.

**The lookup** reads every item `query()` returns (`tcw/store/base.py:2341`) whose
status is not in `RESOLVED_STATUSES` (`tcw/store/base.py:644`). In the filesystem
adapter that is every item folder at every depth (`tcw/store/fs.py:3594-3610`,
`tcw/store/fs.py:4962-4965`). A **malformed** binding on any of them makes import
and link refuse, naming the item — a lookup that skips an unreadable binding
cannot say there is no existing one. Two items holding one key also refuse, naming
both. It is composed over `query` and `read_sidecar`; the store interface gains
nothing.

### 3. `tcw work tracker import <ticket> [--part <id>] [--title <title>]`

1. Refuse with C1's messages if no tracker is configured
   (`_tracker_client`, `tcw/work/cli.py:1607-1631`). Refuse an invalid `--part` or
   an empty `--title`. Both before any tracker call.
2. Read the ticket (for its id), then run the lookup.
   - **Already bound, ticket assigned to this account:** print the bound slug on
     stdout, "already bound" on stderr, exit 0. No write request.
   - **Already bound, ticket not assigned to this account:** print the slug, and on
     stderr "bound here, but the tracker says <KEY> is assigned to <name|nobody>
     in '<status>'"; exit 1. The binding is never taken as proof of a claim (epic
     criterion 11).
3. Run the claim (part 1).
4. `create_work(title, intake=…)` (`tcw/store/base.py:2503`). Title defaults to
   `<KEY> — <summary>`, so the key appears in the slug and any `work/<slug>` branch;
   `--title` replaces it. If it raises: exit 1 with "claimed <KEY>, but the item
   could not be created: <error>. Fix that and run this command again" — the re-run
   reaches row 1e.
5. `write_sidecar(slug, "tracker.yaml", …, revision="")`. With `revision=""` the
   write refuses if the file already exists (`tcw/store/fs.py:6374-6380`).
6. If step 5 raises, `drop(slug)` the item just created (`tcw/store/base.py:2972`;
   it is in `backlog`, and `git rm -rfq` removes staged-but-uncommitted files,
   `tcw/store/fs.py:566-568`), then exit 1 with "claimed <KEY>, but the binding
   could not be written: <error>. Run this command again." **If the drop raises
   too** — likely, since a held Git index lock is the usual reason step 5 fails —
   the message instead names the unbound item and says to run
   `tcw work drop <slug> --confirm` before importing again, or a second item will
   be created.
7. Print the slug on stdout, like `tcw work new` (`tcw/work/cli.py:324`), and on
   stderr the ticket, its status, and whether this run claimed it or found it
   already assigned.

Nothing is committed. `create_work` and `write_sidecar` stage their files
(`tcw/store/fs.py:6094`, `tcw/store/fs.py:6387`), as for `tcw work new`.

**The intake** is Markdown:

```markdown
# <KEY> — <summary>

Imported on <ISO date> from [<KEY>](<url>) (jira-cloud).

<description string, or "The ticket has no description.">
```

The description is included as Jira returns it from the v2 endpoint: wiki markup,
unconverted.

### 4. `tcw work tracker link <slug> <ticket> [--part <id>]`

1. Refuse if the item does not exist in this node, is resolved, or is bound —
   naming the ticket it is bound to and pointing at `unlink`. Refuse a malformed
   binding on the item.
2. Read the ticket and run the lookup; refuse if another item holds the key.
3. Run the claim (part 1).
4. Write the binding with `write_sidecar(..., revision=<the revision read in step
   1>)`, or `""` when the item had no `tracker.yaml`. An item that was unlinked
   still has the file, and its `unlinked` list is carried into the new document.

The item's intake and request are not touched.

### 5. `tcw work tracker unlink <slug> --reason <text>`

- Refuses an item that does not exist in this node, is resolved, is not bound, or
  has a malformed binding; and an empty `--reason`.
- Appends the current binding's `provider`, `project`, `part`, `ticket`,
  `claimed-by` and `bound` to `unlinked`, with `unlinked-on` (today) and `reason`,
  and removes those keys from the top level. The file stays, written with its read
  revision.
- **Makes no tracker call and needs no tracker configuration.** It prints that the
  ticket is unchanged in the tracker.

### 6. What does not change

`tcw work new`, `show`, `list`, `start`, `drop`, every transition, and
`tcw validate`. `tracker list` and `tracker show` behave as before; the `tracker`
group's help text drops "read-only".

### Harness compatibility

Everything is CLI behavior, so Claude and Codex get the same thing. The skill
reference (`skills/tcw-work/references/commands.md:83`) documents the commands; no
skill mechanism carries a requirement.

## Abstraction litmus test

| Operation | Verdict | Why |
| --------- | ------- | --- |
| Read and write `tracker.yaml` | **model** | `read_sidecar` / `write_sidecar` are abstract (`tcw/store/base.py:2611`, `2620`). The registry gains an entry; the interface gains nothing. |
| The binding's content — provider, project, part, ticket id/key/url, claiming account, unlink history | **model** | Portable data. A tracker-backed store would hold the same facts in its own fields. |
| Find the unresolved item bound to a key | **model, composed** | A query over items and one named sidecar each. Any store can answer it, less efficiently without an index. `intake.py` calls `query`; it walks no folder. |
| The project id | **model** | Read from the abstract `ProjectRegistry.current`, passed as a value. |
| Claim: read, transition, assign, read back | **neither — tracker module** | An operation on the tracker, outside `WorkStore`, per the epic's table. |
| Undo a local create when binding fails | **model** | `drop` is concrete on `WorkStore` over the abstract `_delete` (`tcw/store/base.py:2417`, `2972`). |
| REST paths, the v2 description endpoint, `statusCategory.key == "done"`, `accountId` | **adapter private detail** | Jira-shaped; confined to `tcw/tracker/jira.py` and the values `intake.py` is handed. |

## Acceptance criteria

**[live]** criteria are checked by hand against the epic's fixture projects,
`TCWCLAIM` (a workflow that excludes) and `TCWTEST` (one that does not). All others
are automated, with the transport replaced at `JiraClient._request`. "Write
request" means a `POST` or `PUT`.

1. **No tracker configured.** `import` and `link` exit 1 with one line naming
   `work.tracker`, and create nothing. The existing suite passes with no existing
   assertion edited, including `test_the_jira_client_is_never_imported`
   (`tests/test_tracker_absent.py:126`).
2. **A ready, unassigned ticket.** `import` sends exactly two write requests, the
   transition then the assign, and creates one `backlog` item with no `owner` and no
   `initial-request.md`. Its `intake.md` contains the canonical key, the URL and the
   fake's description string. Its `tracker.yaml` has `schema: 1`,
   `provider: jira-cloud`, `project` equal to the test node's id, `part: default`,
   `ticket.id` / `ticket.key` equal to the fake issue's, `claimed-by.account-id`
   equal to the fake `myself` account, and `unlinked: []`.
3. **Pre-assigned to this account, claim offered.** `import` sends the transition
   and no assign request, and binds.
4. **Pre-assigned to this account, claim offered, transition refused, read-back
   unmoved.** Exit 1 with the row 3c first line; no item.
5. **Assigned to another account, or resolved.** `import` exits 1, sends no write
   request, creates no item; the message names the assignee and status (1b) or says
   resolved (1a).
6. **Two accounts, one ticket, a workflow that excludes** (epic criterion 2). With
   a fake that accepts the first transition and refuses any later one, and nodes A
   and B authenticated as different accounts, each of these orders yields exactly
   one item across both nodes (A's), and B sends no assign request and exits 1:
   - (a) A finishes before B starts: B refused at row 1b, naming A's account and
     `In Progress`.
   - (b) Both read at step 1 first; A's transition applies; B's is refused; B reads
     back before A assigns: B refused at row 3d, `In Progress`, unassigned.
   - (c) As (b), but B reads back after A assigns: B refused at row 3b, naming A's
     account.
7. **Transition refused, ticket unmoved, unassigned.** Row 3d. The first stderr
   line is the fixed text; the 400 body appears only on a line starting `detail:`.
8. **Transition applied, assign refused with 403.** Row 3e; exit 1; no item. A
   re-run against the ticket then assigned to this account binds via row 1e.
9. **Transition timed out.** Read-back landed and assigned to this account (the
   ticket was pre-assigned): binds. Read-back unassigned: row 3f, no item.
10. **Idempotent** (epic criterion 3). `import` twice with the same `--part`: one
    item; the second run prints the same slug, exits 0, says "already bound", sends
    no write request. On an excluding workflow, `--part api` then `--part web`:
    two items, each with its own binding; the second run sends no write request
    (row 1e).
11. **Claimed, then the local step failed** (epic criterion 4). With
    `write_sidecar` made to raise, `import` exits 1 and leaves no item. With both
    `write_sidecar` and `drop` made to raise, the message names the slug and
    `tcw work drop`. With `create_work` made to raise, the message says the ticket
    is claimed. In each case, re-running against the ticket as left — assigned to
    this account, claim not offered — produces one bound item, sends no write
    request, and says "not claimed by this run". **[live]** On `TCWCLAIM`: move a
    ticket to `In Progress` and assign it to yourself by hand, then `import` it.
12. **The binding is not proof** (epic criterion 11). A hand-written `tracker.yaml`
    on a `backlog` item naming a ticket assigned to another account makes `import`
    of that ticket exit 1, naming the slug and the real assignee, with no write
    request.
13. **Malformed bindings fail closed.** A `tracker.yaml` holding a YAML list, or
    one whose `ticket` is the string `TCWCLAIM-6`, on an unresolved item makes
    `import` and `link` exit 1 naming that item. Two unresolved items holding one
    key make both exit 1 naming both. The same files on a `completed` item change
    nothing.
14. **`link`.** On an unbound `backlog` item and a ready ticket: claims, binds, and
    leaves `intake.md` and `initial-request.md` byte-identical. On a bound item, a
    resolved item, or a key another item holds: exit 1, no write request, no file
    changed.
15. **`unlink`.** Without `--reason`, or on an unbound or resolved item: exit 1,
    nothing changed. On a bound item, with no tracker configured: exit 0, no
    network request, `tracker.yaml` has no `ticket` and one `unlinked` entry with
    the old `ticket`, `reason` and `unlinked-on`. A following `link` of the same
    item to another ticket succeeds and keeps that entry.
16. **No secret** (epic criterion 8). With the token variable set to a sentinel,
    the sentinel appears in no stdout or stderr of `import`, `link` or `unlink` on
    any path in criteria 2–15, and in no file under the work store.
17. **The web app offers no edit.** `GET /api/work/<slug>/sidecars` reports
    `tracker.yaml` with `generated: true`.
18. **[live]** On `TCWCLAIM`, `import` of a ready unassigned ticket leaves it
    `In Progress` and assigned to the signed-in account, with one bound item whose
    intake holds the ticket's description text. On `TCWTEST`, the same command on a
    ready ticket behaves identically and prints nothing about exclusivity.
19. **Ledger.** `work/manage-external-tracker-intake` reads `Supported` with a
    non-empty description; `tcw capabilities check` and `tcw validate` exit 0.

### Coverage against the epic

| Epic criterion | Here |
| -------------- | ---- |
| 1 — no tracker, unchanged | 1 |
| 2 — concurrent imports, one item | 6: two accounts, a workflow that excludes, three named orders. Same-account races are a user-decided non-goal. |
| 3 — idempotent by part | 10 |
| 4 — remote claim, local failure, re-run | 8, 11 |
| 8 — no secret | 16 |
| 11 — binding is not proof | 12 |
| 12 — ledger | 19 |

## Risks

1. **Row 1e binds tickets nobody claimed through TCW.** A ticket assigned to you
   that does not offer the claim is bound without a transition — including one
   assigned to you before the claim point (a `Triage` status, as in the #36
   report's workflow). The ticket is yours, so nobody is displaced, but it is bound
   without having moved; the message names its status. This departs from the epic's
   C2 wording ("require it in the configured ready state"), because there is no
   configured ready state — C1 shipped `transitions.claim` only — and without the
   row an interrupted claim on an excluding workflow can never be completed (epic
   criterion 4). Resolved tickets are refused outright. Upgrade path: Notes,
   change history.
2. **A killed process between `create_work` and `write_sidecar` leaves an unbound
   item**, and a re-run creates a second. Every failure that raises is handled by
   part 3 step 6. A leftover untracked file in a dropped folder can also make the
   re-run's `create_work` raise `FileExistsError`, because slug uniqueness only
   sees folders holding `state.yaml` (`tcw/store/fs.py:6093`); the step 4 message
   then names the error. Both rare; both visible.
3. **The winner's assign overwrites any assignment made between its step 1 read
   and its `PUT`.** A person assigning the ticket in that one-round-trip window loses
   the assignment, and the read-back shows this account. Cannot be prevented with a
   blind assign; the window is small.
4. **The lookup reads every unresolved item's sidecar** on every import and link.
   Linear in items; milliseconds per item on a filesystem. An index is a later
   change if ever measured slow.
5. **A second claimant on a workflow that does not exclude is not stopped**, nor
   are two runs by one account. Both user decisions; recorded so C4, which owns
   refusal, does not assume C2 closed them.
6. **Configuration inheritance lands beside this.**
   `2026-09-14-inherit-work-tracker-from-parent-nodes-key-by-key` is being planned
   at the same time and changes where `TrackerConfig` comes from. This item adds no
   key and reads configuration only through `tracker_config()`, so the code does not
   collide. Both edit the tracker sections of `README.md`,
   `skills/tcw-work/references/commands.md` and `docs/changelogs/upcoming.md`;
   whichever lands second rebases those documentation tasks. In an inheriting
   workspace, importing one ticket in two nodes gives two items, because `project`
   differs — the epic's stated intent.
7. **Wiki markup in the intake reads oddly as Markdown** (`h2.`, `{{code}}`). It is
   raw input for the `request` stage, and it carries the ticket's URL.

## Notes

**Review, 2026-09-14.** One adversarial review (Claude `adversarial-spec-reviewer`)
of the first version, verdict NOT DONE. Every citation it raised was checked
against the tree.

- **Accepted:** the read-back ignored status, so a refused transition on a
  pre-assigned ticket would have bound (now 3a/3c, criterion 4); the error routing
  was incomplete (now step 2's four results and the six-row table); row 1f told
  whichever account read it to assign the ticket to itself, which in a race is how
  a loser takes the winner's claim (advice removed; kept only in 3e, where this run
  moved the ticket); `link` after `unlink` would always raise `StaleRevision`
  (`tcw/store/fs.py:6374-6380`) (now passes the read revision); the description
  converter dropped leaf nodes silently (removed: v2 description); the validate
  check would block `complete` on unrelated items (removed); malformed versus
  unbound was ambiguous (defined); idempotency across working copies and resolved
  items was unstated (Non-goals); `create_work` failing after a claim was
  unhandled, and a failed drop is the common case (part 3 steps 4 and 6); a
  citation pointed at the wrong branch of `write_sidecar`; criteria 2, 3, 5 and 6
  could be checked more than one way (pinned); the ticket key was put in the URL
  path unquoted; the project id should come from the abstract registry.
- **Narrowed:** "departures from the epic's ready-state rule are not recorded" —
  recorded in Risk 1 rather than changed, since no ready-state key exists.
  "`reporter` attribution is over-building" — removed.
- **Put to the user:** whether same-account concurrent imports may produce two
  items. Answered 2026-09-14: accept and document.
- **Rejected:** none outright.

**Two commitments in the epic plan's Verification section fall to this item** and
are carried to this item's plan rather than into criteria, because neither is
automatable: item 2, two developers on two machines against one Jira project
(criterion 6 proves the logic with a fake; the manual check needs a second Jira
account, which may not exist), and item 4, one ticket filed by someone without a
checkout and imported end to end. If either cannot be done, the outcome records it
as not verified, for the epic's checkpoint 2.

**Criterion 6 is narrower than epic criterion 2's wording**, which does not say
"two accounts" or "a workflow that excludes". Both narrowings follow from the epic
(the loser names an assignee; goal 1 is conditional) and from the user's two
answers. Recorded for checkpoint 2.

**Live checks, 2026-09-14,** read-only, against `proposit.atlassian.net`:

- `GET /rest/api/3/issue/TCWCLAIM-1/transitions`, with and without
  `includeUnavailableTransitions=true`, returns only `31 Finish → Done`. That
  parameter does not reveal where a claim led.
- `GET /rest/api/3/issue/TCWCLAIM-1/changelog` returns the status change
  `To Do → In Progress` with the author's `accountId`. **Upgrade path for Risk 1
  and row 3f:** the change history can tell whether this account made the last
  status change, which would let row 1e require proof. Not used now; it adds a
  paginated read for a case the user has said is acceptable.
- `GET /rest/api/3/issue/tcwclaim-1` succeeds, so a lowercase key resolves.
- On an issue in another project on the same site, `GET /rest/api/2/issue/{key}?fields=description`
  returns a wiki-markup string where v3 returns a document tree.

**The server-side gap for generated sidecars is still unfiled.** No inbox note or
backlog item mentions it. The plan files an inbox note.

**Sibling sweep.** This is new behavior, not a defect report. The one adjacent
problem found — any registered sidecar is writable through `serve` regardless of
`generated` — is repo-wide already and is the unfiled gap above.
