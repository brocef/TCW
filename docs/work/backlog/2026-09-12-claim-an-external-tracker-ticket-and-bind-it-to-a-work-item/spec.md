# Spec — Claim an external tracker ticket and bind it to a work item

Child C2 of `2026-08-04-supplement-filesystem-tcw-work-with-an-external-tracker-bridge`.
The epic's spec fixes this item's boundary, its identity rules and five of its
acceptance criteria; this document decides the rest. Every `file:line` below was
read at `29d832e7`.

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
   assigned to the signed-in account, no item is created.
2. A ticket may be claimed when it is unassigned or already assigned to the
   signed-in account. Claiming an unassigned ticket assigns it. A ticket assigned
   to anyone else is refused, and the refusal names the assignee and the status.
3. The binding is a machine-readable `tracker.yaml` sidecar, written by a command
   and never offered for editing in the web app.
4. Importing the same ticket and part twice produces one item. A different part
   deliberately produces another.
5. A claim that succeeded in the tracker but did not finish locally completes when
   the same command is run again.
6. `tcw work tracker link <slug> <ticket>` binds an existing unresolved item by the
   same claim rules. `tcw work tracker unlink <slug> --reason <text>` removes a
   binding and keeps a record of it and the reason.
7. The ticket's product text lands in the item's intake with its origin; the
   `request` stage still has to run.
8. A project with no tracker configured behaves exactly as it does today.

**On a workflow that can exclude a second claimant**, goal 1 with the read-back of
goal 2 gives exactly one winner between two accounts: the loser's transition is
refused, so it never assigns, so its read-back shows the ticket is not its own.
**On a workflow that cannot exclude**, two accounts racing may both succeed. The
user decided at the `request` stage that import should not check or warn about
this ("We don't care if multiple claimants is possible or not"), so it does
neither, and no criterion here promises a single winner there.

## Non-goals

- **Judging whether the workflow excludes a second claimant.** No check, no
  warning, no refusal. The user's decision; see Goals. C1's `assess` still reports
  it under `tracker show`.
- **Two runs by the same account at the same moment.** Both are "you", so the
  read-back cannot tell them apart, and on one machine both may create an item.
  Epic criterion 2's loser "names the current assignee", which presumes two
  accounts; that is the case covered. A duplicate made this way is visible on the
  board and removable with `drop`.
- **Setting `owner`.** Epic identity rule 1: importing is not starting.
- **Import options beyond `--part` and `--title`.** Priority, tags, blockers,
  initiative and parent are set afterwards with `tcw work edit`, as they are for
  any item. The epic request says import accepts creation metadata "where needed";
  nothing here needs it.
- **Any change to the tracker from `unlink`.** It is a local repair. The ticket
  stays where it is and assigned to whoever holds it, and the command says so.
- **A server-side refusal of writes to generated sidecars.** `PUT
  /api/work/<slug>/sidecars/<name>` accepts any registered name
  (`tcw/serve/__init__.py:1281-1305`); `generated` is only reported to the client
  (`tcw/serve/__init__.py:646`). That gap also affects `rollup.md`, and the epic
  says to file it separately. See Notes.
- Outbound sync and `tracker sync` (C3); strict mode, `drop` refusal for bound
  items, workflow-definition reads (C4); showing the binding in `list`, `show`,
  `--json` or the web app beyond the raw sidecar the app already lists (C5);
  inheriting `work.tracker` from parent nodes
  (`2026-09-14-inherit-work-tracker-from-parent-nodes-key-by-key`).
- **No new configuration key.** Everything this item needs is derived from the
  existing `transitions.claim` and from the ticket.

## Design

### 1. The claim

A new module `tcw/tracker/intake.py` holds the decision logic, pure over values
the client returns, the way `tcw/tracker/claim.py` holds `assess`. The client
gains the writes.

**Client additions** (`tcw/tracker/jira.py`), both through the existing `_request`
seam and therefore under its timeout:

- `apply_transition(key, transition_id)` — `POST /rest/api/3/issue/{key}/transitions`.
- `assign(key, account_id)` — `PUT /rest/api/3/issue/{key}/assignee`.
- `issue(key)` requests `reporter` as well (`tcw/tracker/jira.py:214`), for the
  intake's attribution. `status.statusCategory` already arrives inside `status`
  (visible in `tests/fixtures/tracker/conforming-ready-issue.json`).

The module docstring's "read-only" description changes with them.

**Identity** is `myself()["accountId"]` (`tcw/tracker/jira.py:184`), compared
against `fields.assignee.accountId`. Never display names, which are not unique.

**Step 1 — read.** `issue(key)`, `transitions(key)`, `myself()`. Then decide, in
this order:

| Ticket as read | Outcome |
| -------------- | ------- |
| `status.statusCategory.key` is `done` | Refuse: the ticket is resolved. |
| Assigned to another account | Refuse, naming the assignee's display name and the status. |
| `assess(...)` verdict `AMBIGUOUS` (`tcw/tracker/claim.py:99-108`) | Refuse with `assess`'s own detail. |
| Claim transition offered | Go to step 2. |
| Claim not offered, assigned to this account | **Already yours.** Bind without a transition, and say so: "not claimed by this run: <KEY> is already in '<status>' and assigned to you". |
| Claim not offered, unassigned | Refuse. List what the ticket offers, and say that a claim which stopped before assigning leaves exactly this state, in which case assign it to yourself in the tracker and run the command again. |

The "already yours" row is what makes goal 5 work on a workflow that excludes.
After a claim, that ticket no longer offers the claim, and nothing it returns says
where the claim led: C1 recorded that asymmetry (`tcw/tracker/claim.py:79-92`),
and a live read on 2026-09-14 confirmed that
`GET …/transitions?includeUnavailableTransitions=true` on the claimed `TCWCLAIM-1`
returns only `Finish`, the same as without it. So the ticket cannot prove it was
claimed; assignment to this account is the evidence used. Its cost is in Risks.

**Step 2 — claim.** `apply_transition` with the id `assess` matched. Then, only if
the ticket was unassigned at step 1, `assign` it to this account. **Transition
first, assign second**, and the order matters: on a workflow that excludes, a
loser's transition is refused, so a loser never reaches `assign` and cannot
overwrite the winner's assignment. Assigning first would let two accounts
overwrite each other before either transition ran.

A `TrackerRequestInvalid` or `TrackerUnavailable` from either write does not end
the command: it goes to step 3, because neither says what state the ticket is in
(a timeout may have applied). `TrackerAuthError`, `TrackerPermissionError` and
`TrackerRateLimited` from `apply_transition` end it with C1's message, since the
transition did not apply.

**Step 3 — read back.** `issue(key)` again, and decide from it alone:

| Read back | Outcome |
| --------- | ------- |
| Assigned to this account | Claimed. Go to binding. |
| Assigned to another account | Refuse: "claimed by <name>; now in '<status>'". |
| Unassigned, and the transition was refused | Refuse: the claim did not apply; the ticket is in '<status>'. Carry the transport's message as detail, never as the explanation. |
| Unassigned, transition applied, assign failed | Refuse: "<KEY> moved to '<status>' but could not be assigned to you: <error>". |

If the read-back itself fails, say that the claim's result is unknown and that
running the command again will find out. No item is created.

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
project: tcw                  # the node's project id
part: default
ticket:
    id: "10052"               # the tracker's stable issue id
    key: TCWCLAIM-6
    url: https://example.atlassian.net/browse/TCWCLAIM-6
claimed-by:
    account-id: "712020:…"
    name: Probe
bound: "2026-09-14"
unlinked: []                  # earlier bindings, see part 5
```

- **`project`** is `FsProjectRegistry.open(node_root).current.id`
  (`tcw/store/project.py:170`) — `id: tcw` in this repository
  (`tcw-config.yaml:1`).
- **The ticket is identified by `id`, not `key`.** Jira changes an issue's key when
  it moves between projects; its id does not. The key and URL are kept for
  reading. The key is taken from the tracker's response, not from what the user
  typed, so `tcwclaim-6` and `TCWCLAIM-6` are one ticket.
- **No credential, no e-mail address.** `claimed-by` is the account id and display
  name only. Epic identity rule 2: this is a separate field from `owner` and never
  overwrites it.
- **An item is bound** when its `tracker.yaml` has a `ticket` mapping.

**The idempotency key** is `(project, provider, ticket.id, part)`. `part` must
match `[a-z0-9][a-z0-9-]*` and defaults to `default`.

**Finding an existing binding** reads `tracker.yaml` from every item `query()`
returns (`tcw/store/base.py:2341`), which in the filesystem adapter is every item
folder at every depth and status (`tcw/store/fs.py:3594-3610`,
`tcw/store/fs.py:4962-4965`). A binding that is not a mapping, or lacks a field
the key needs, makes import and link **refuse**, naming the item: a lookup that
skips an unreadable binding cannot say there is no existing one. Two items holding
one key also refuse, naming both.

The lookup lives in `tcw/tracker/intake.py`, composed over the store's existing
`query` and `read_sidecar`. The store interface gains nothing.

### 3. `tcw work tracker import <ticket> [--part <id>] [--title <title>]`

1. Refuse with C1's messages if no tracker is configured
   (`_tracker_client`, `tcw/work/cli.py:1607-1631`).
2. Read the ticket (for its id), then look up the key.
   - **Already bound, and the ticket is assigned to this account:** print the
     bound slug on stdout, "already bound" on stderr, exit 0. No claim is
     attempted.
   - **Already bound, and it is not:** print the slug and "bound here, but the
     tracker says <KEY> is assigned to <name|nobody> in '<status>'", exit 1. The
     binding is never taken as proof of a claim (epic criterion 11).
3. Run the claim (part 1).
4. `create_work(title, intake=…)` (`tcw/store/base.py:2503`). Title defaults to
   `<KEY> — <summary>`, so the key appears in the slug and in any `work/<slug>`
   branch; `--title` replaces it.
5. `write_sidecar(slug, "tracker.yaml", …, revision="")`. `revision=""` refuses if
   a binding somehow already exists (`tcw/store/fs.py:6381-6385`).
6. If step 5 raises, `drop(slug)` the item just created (`tcw/store/base.py:2972`,
   legal because it is in `backlog`) and report that the ticket is claimed and a
   re-run will finish. If the drop fails too, name the unbound item.
7. Print the slug on stdout, like `tcw work new` (`tcw/work/cli.py:324`), and on
   stderr the ticket, its status, and whether this run claimed it or found it
   already assigned.

Nothing is committed. `tcw work new` commits nothing either; `create_work` and
`write_sidecar` stage their files (`tcw/store/fs.py:6094`, `tcw/store/fs.py:6387`).

**The intake** is Markdown:

```markdown
# TCWCLAIM-6 — A ready ticket for the claimable demo

Imported on 2026-09-14 from [TCWCLAIM-6](https://…/browse/TCWCLAIM-6)
(jira-cloud). Reported by <reporter name>.

<description as text, or "The ticket has no description.">
```

Jira Cloud's REST v3 returns `description` as an Atlassian Document Format tree,
not text (`null` when empty, as in the fixture above). A small converter in
`tcw/tracker/jira.py` — Jira-specific, so it stays there — walks the tree:
paragraphs and headings become lines, list items become `- ` lines, code blocks
are fenced, hard breaks are newlines, mentions and links keep their text, and any
node it does not recognize contributes its children's text. Nothing is dropped
silently: a tree that yields no text at all while having content gets the line
"The ticket's description could not be converted to text; read it at <url>."

### 4. `tcw work tracker link <slug> <ticket> [--part <id>]`

1. Refuse if the item is resolved (`completed` or `discarded`), or already bound —
   to any ticket, naming it and pointing at `unlink`.
2. Refuse if another item already holds the key, naming it.
3. Run the claim (part 1), then write the binding as import step 5. Existing
   `unlinked` history on the item is kept.

The item's intake and request are not touched.

### 5. `tcw work tracker unlink <slug> --reason <text>`

- Refuses an item that is not bound, and an empty `--reason`.
- Moves the current binding into `unlinked`, adding `unlinked-on` (today's date)
  and `reason`, and removes `ticket`, `claimed-by`, `part` and `bound` from the
  top level. The file stays, so the record survives.
- **Makes no tracker call and needs no tracker configuration**, so a binding can be
  removed after `work.tracker` has been deleted from the config. It prints that the
  ticket is unchanged in the tracker.

### 6. `tcw validate`

Beside `tracker_problems` (`tcw/validate.py:281`), offline: every malformed
`tracker.yaml`, and every key held by more than one item, is a problem naming the
items. The same function the import lookup uses. No network call and no credential
read, preserving C1's criterion 7.

### 7. What does not change

`tcw work new`, `show`, `list`, `start` and every transition. The `tracker` group's
help text changes from "read-only". `list` and `show` under `tracker` are
unchanged.

### Harness compatibility

Everything is CLI behavior, so Claude and Codex get the same thing. The skill
reference (`skills/tcw-work/references/commands.md:83`) documents the commands; no
skill mechanism carries a requirement.

## Abstraction litmus test

| Operation | Verdict | Why |
| --------- | ------- | --- |
| Read and write `tracker.yaml` | **model** | `read_sidecar` / `write_sidecar` are abstract (`tcw/store/base.py:2611`, `2620`). The registry gains an entry; the interface gains nothing. |
| The binding's content — provider, project, part, ticket id/key/url, claiming account, unlink history | **model** | Portable data. A tracker-backed store would hold the same facts in its own fields. |
| Find the item bound to a key | **model, composed** | A query over items and one named sidecar each. Any store can answer it, less efficiently without an index. No filesystem walk appears in `intake.py`; it calls `query`. |
| Claim: read, transition, assign, read back | **neither — tracker module** | An operation on the tracker, outside `WorkStore`, per the epic's table. |
| Undo a local create when binding fails | **model** | `drop` is abstract lifecycle over a `backlog` item. |
| ADF to text, REST paths, `statusCategory.key == "done"`, `accountId` | **adapter private detail** | Jira-shaped; confined to `tcw/tracker/jira.py` and the values `intake.py` is handed. |

## Acceptance criteria

Criteria marked **[live]** are checked by hand against the epic's two fixture
projects, `TCWCLAIM` (a workflow that excludes) and `TCWTEST` (one that does not).
All others are automated, with the transport replaced at `JiraClient._request`.

1. **No tracker configured.** `import` and `link` exit 1 with one line naming
   `work.tracker`, and create nothing. The existing suite passes with no existing
   assertion edited, and `tests/test_tracker_absent.py` still passes, including
   `test_the_jira_client_is_never_imported`.
2. **A ready, unassigned ticket.** `import` issues exactly one transition request
   and one assign request, in that order, creates one `backlog` item whose
   `intake.md` contains the key, the URL and the converted description, and whose
   `tracker.yaml` parses to the document in Design part 2. `owner` is unset.
   `initial-request.md` does not exist.
3. **Pre-assigned to this account.** `import` issues a transition and **no** assign
   request.
4. **Assigned to another account, or resolved.** `import` exits 1, sends no write
   request, creates no item, and the message names the assignee and status (or
   that the ticket is resolved).
5. **Two accounts, one ticket, a workflow that excludes** (epic criterion 2).
   Two concurrent `import` runs against a fake tracker that accepts the first
   transition and refuses the second with `HTTP 400`, each authenticated as a
   different account, produce exactly one item across both stores. The loser exits
   1, sends no assign request, and its message names the current assignee (or
   "unassigned") and status. **[live]** Repeated on `TCWCLAIM` with two accounts,
   if a second account is available; if not, recorded as not verified.
6. **Transition refused, ticket unmoved.** The read-back shows the ticket still
   unassigned in its ready status: exit 1, no item, and the message says the claim
   did not apply without quoting the 400 body as the reason.
7. **Idempotent** (epic criterion 3). `import` twice with the same `--part`: one
   item, the second run prints the same slug, exits 0, says "already bound", and
   sends no write request. With `--part api` then `--part web`: two items, each
   with its own binding.
8. **Claimed, then the local step failed** (epic criterion 4). With `write_sidecar`
   made to raise, `import` exits 1 and leaves no item. Re-running against the
   ticket as that first run left it — assigned to this account, claim no longer
   offered — produces one bound item, sends no write request, and reports "not
   claimed by this run". **[live]** On `TCWCLAIM`: claim a ticket by hand in Jira,
   assign it to yourself, then `import` it.
9. **The binding is not proof** (epic criterion 11). A hand-written `tracker.yaml`
   naming a ticket assigned to another account makes `import` of that ticket exit
   1 naming the bound slug and the real assignee, and sends no write request.
10. **Fail closed on bad bindings.** A `tracker.yaml` holding a YAML list, or two
    items holding one key, makes `import` and `link` exit 1 naming the item or
    items, and makes `tcw validate` exit non-zero with the same names.
    `tcw validate` still makes no network call (C1's
    `test_validate_makes_no_network_call` passes unedited).
11. **`link`.** On an unbound `backlog` item and a ready ticket: claims, binds, and
    leaves `intake.md` and `initial-request.md` byte-identical. On a bound item, a
    resolved item, or a key another item holds: exit 1, no write request, no file
    changed.
12. **`unlink`.** Without `--reason`, or on an unbound item: exit 1, nothing
    changed. On a bound item: exit 0, no network request (with no tracker
    configured, too), `tracker.yaml` has no `ticket` and one `unlinked` entry
    carrying the old ticket, `reason` and date. A later `link` to another ticket
    keeps that entry.
13. **No secret** (epic criterion 8). With the token variable set to a sentinel
    value, the sentinel appears in no stdout or stderr of `import`, `link` or
    `unlink` on any path above, and in no file under the work store.
14. **The web app offers no edit.** `GET /api/work/<slug>/sidecars` reports
    `tracker.yaml` with `generated: true`.
15. **Description conversion.** An ADF document with a heading, a paragraph with a
    link and a mention, a bullet list, a code block and an unknown node type
    converts to text containing every piece of visible text; a `null` description
    produces "The ticket has no description."
16. **[live]** On `TCWCLAIM`, `import` of a ready unassigned ticket leaves it in
    `In Progress` assigned to the signed-in account, with one bound item. On
    `TCWTEST`, the same command on a ready ticket behaves identically and prints
    nothing about exclusivity.
17. **Ledger.** `work/manage-external-tracker-intake` reads `Supported` with a
    non-empty description; `tcw capabilities check` and `tcw validate` exit 0.

### Coverage against the epic

| Epic criterion | Here |
| -------------- | ---- |
| 1 — no tracker, unchanged | 1 |
| 2 — concurrent imports, one item | 5, narrowed to two accounts on a workflow that excludes; see Goals and Non-goals |
| 3 — idempotent by part | 7 |
| 4 — remote claim, local failure, re-run | 8 |
| 8 — no secret | 13 |
| 11 — binding is not proof | 9 |
| 12 — ledger | 17 |

## Risks

1. **"Already yours" binds tickets nobody claimed through TCW.** A ticket assigned
   to you that does not offer the claim is bound without a transition — including
   one assigned to you while still before the claim point (for example in a
   `Triage` status). The ticket really is yours, so no one else is displaced, but
   it is bound without having moved. Accepted because the alternative is that a
   claim interrupted after its transition can never be completed on a workflow
   that excludes, which is epic criterion 4. The message names the status, so the
   user sees it. Resolved tickets are refused outright.
2. **A crash between `create_work` and `write_sidecar` leaves an unbound item**,
   and a re-run creates a second one. Part 3 step 6 covers every failure that
   raises; only a killed process escapes it. Accepted: the stray item is on the
   board. Making create and bind one operation would change the abstract
   `create_work` signature for one caller.
3. **The lookup reads every item's sidecar.** Linear in the number of items, on
   every import and link. This repository has a few hundred items; a filesystem
   read each is milliseconds. An index is a later change if it is ever measured
   slow.
4. **A second claimant on a workflow that does not exclude is not stopped.** The
   user's decision; recorded so C4, which owns refusal, does not assume C2 closed
   it.
5. **Jira's assign may be refused where the transition was allowed** (the "Assign
   issues" permission is separate from "Transition issues"). The ticket is left
   moved and unassigned; part 1's step 3 reports exactly that and the step 1 table
   tells the user how to finish.
6. **Configuration inheritance lands beside this.**
   `2026-09-14-inherit-work-tracker-from-parent-nodes-key-by-key` is being planned
   at the same time and changes where `TrackerConfig` comes from. This item adds no
   key and reads `TrackerConfig` only through `tracker_config()`, so it is
   unaffected either way. In an inheriting workspace, importing one ticket in two
   nodes gives two items, because `project` differs — which is the epic's stated
   intent ("one ticket may coordinate multiple TCW items across repositories").
7. **ADF conversion loses formatting.** Tables, panels and media are reduced to
   their text. The intake is raw input for the `request` stage, and it carries the
   ticket's URL.

## Notes

- **Live check, 2026-09-14.** `GET /rest/api/3/issue/TCWCLAIM-1/transitions` with
  and without `includeUnavailableTransitions=true` both return only
  `31 Finish → Done`; `TCWTEST-1` returns the same three global transitions either
  way. So that parameter does not reveal where a claim led, and Design part 1 does
  not rely on it.
- **The server-side gap for generated sidecars is still unfiled.** The epic says to
  file it separately; no inbox note or backlog item mentions it. The plan should
  file an inbox note rather than fix it here.
- **Criterion 5 is narrower than epic criterion 2's wording**, which does not say
  "two accounts" or "a workflow that excludes". Both narrowings follow from facts
  already in the epic (the loser names an assignee; goal 1 is conditional) and from
  the user's answer at the request stage. Recorded here so the epic's checkpoint 2
  reads it.
- **Sibling sweep.** This is new behavior, not a defect report. The one adjacent
  problem found — any registered sidecar is writable through `serve` regardless of
  `generated` — is repo-wide already and is the unfiled gap above.
