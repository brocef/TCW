# Spec — Jira work backend: Jira as the single owner of status and the request

## Capability changes

Planned ledger changes. No records are written at this stage; implement writes them
in the same change as the code, and `<item>/capabilities.yaml` declares them
(TCW-69 Design 4.4 and 7).

**Removed, by TCW-70 or here.** The six records under the `external-work-tracker`
Feature describe the 2.x tracker integration:

- `work/hold-a-tracker-ticket` (`tracker claim` / `tracker release`);
- `work/require-tracker-backed-work` (strict mode);
- `work/synchronize-external-tracker-work` (sync after each lifecycle move);
- `work/manage-external-tracker-intake` (`tracker import`);
- `work/inspect-external-tracker-work` (`tracker list` / `tracker show`, and the
  `work.tracker` block);
- `work/inherit-tracker-settings-from-parent-nodes`. **[Decision]** `work.jira` is
  not inherited from parent projects. Each project states its own block. Key-by-key
  inheritance across projects cost about 180 lines of merging and attribution
  (`tcw/store/base.py:1885-2010`, `tcw/store/fs.py:7382-7440`). It also needed a
  special rule so that a token is never sent to a site named in a different file.
  3.0's only layering is TCW-72's personal layers.

TCW-70 decides each of the 46 `docs/capabilities/work/` records, because it removes
the 2.x store (epic decision 12), and its spec removes all six, together with the
`external-work-tracker` Feature: the code they describe cannot outlive the 2.x work
store that TCW-70 deletes (Design 14). This slice owns them only if TCW-70 leaves
any of them, and then declares them as removed. Either way, criterion 21 checks that
they are gone. Later wording changes to the command surface in the new records are
TCW-73's (decision 12).

The `Tracker` and `Planning doc` *fields* of capability records (`CAP_FIELDS`,
`tcw/store/base.py:844-847`) are not this slice's: TCW-73 removes them from the
capabilities commands and TCW-76 from the records (decision 9).

**New.**

- `work/keep-work-items-in-jira`: a project sets `work.backend: jira`. Jira then
  owns status, the request, assignee, priority, estimates, labels, parent and
  blocking links, and the repository owns the technical record. It covers the
  stage-to-status mapping, `advance` as one workflow transition, QA on the ticket,
  and `item.yaml` holding only the ticket link.
- `work/adopt-a-jira-ticket`: `tcw work tickets list` and `tcw work tickets adopt
  <KEY>`.
- `work/check-a-jira-project-against-the-stage-mapping`: `tcw validate --remote`.

**Changed.**

- The delegation record. TCW-70's draft replaces
  `work/delegate-a-request-to-a-child-node` with a new
  `work/delegate-a-work-item-to-another-project` for `tcw work new --project`, which
  covers filesystem-mode targets only. This slice adds Jira-mode targets to that
  record (Design 8).

**Taxonomy.**

- Removed (by TCW-70's draft, or here if it does not): `external-work-tracker`. Its
  description ("the coordination boundary … an external tracker that owns ticket
  existence, assignment and claim state",
  `docs/taxonomy/external-work-tracker/description.md`) describes claims and
  coordination, which 3.0 does not have.
- New: Feature `jira-work-backend`. The new capabilities above link to it.
- Changed: `configure-skill`. Its `relatesTo` names `external-work-tracker`
  (`docs/taxonomy/configure-skill/meta.yaml:6`), and must name `jira-work-backend`
  instead, unless TCW-70 has already dropped the reference.

`work-inbox` is not changed here. TCW-70 redefines the filesystem inbox, and the
Jira inbox is described by `work/adopt-a-jira-ticket`.

## Problem

1. **Status lives in two places, and the code that copies it is most of the
   integration.** In 2.x an item's status is its folder, and the ticket is moved
   afterwards. `tcw/tracker/sync.py:3` says it plainly: "A local transition has
   already happened, and been committed, when anything here runs." Whatever did not
   reach Jira is recorded on the item and retried later
   (`tcw/tracker/intake.py:312` `record_owed`, `tcw/tracker/progress.py:79`
   `retry`). Around that sit several more pieces:
   - claims (`tcw/tracker/claim.py`, `tcw/tracker/ownership.py`);
   - bindings (`tracker.yaml`, classified at `tcw/store/base.py:469`);
   - strict mode, and recording tickets owed to new items (`tcw/work/cli.py:428-738`, `779`);
   - nine `tcw work tracker` commands (`tcw/work/cli.py:4664-4934`, with handlers
     at `tcw/work/cli.py:2760-4087`).

   Together that is 3,301 lines in `tcw/tracker/`, about 1,330 lines of command
   handlers, the configuration parser (`tcw/store/base.py:1255-2011`), and 14,761
   lines across 28 `tests/test_tracker_*.py` files. All of it exists to keep two
   copies of one fact in step.
2. **3.0 has no Jira backend.** TCW-69 defines the backend interface (eleven
   operations, `external_stages`, `inbox_items`; epic decision 1) and tests it against an in-memory
   backend only. Nothing implements it against Jira.
3. **A Jira workflow is found to be wrong only when a real item moves.** 2.x checks
   the `work.tracker` block's shape only, and deliberately never calls Jira from
   `tcw validate` (`tcw/validate.py:376-384`). GitHub #44 reports the result: two
   transitions into one status, and statuses that cannot be reached, found "by
   running a throwaway item through the whole lifecycle". This is recorded as
   `docs/work/backlog/2026-09-15-check-the-tracker-s-workflow-against-the-statuses-mapping-in-tcw-validate/`.
4. **The 2.x client reads too little for a backend.**
   - `search` fetches one page and three fields (`tcw/tracker/jira.py:221-232`).
   - There is no operation that edits fields or creates links.
   - `transitions` puts the key into the path without quoting it
     (`jira.py:252`), unlike `issue` (`jira.py:240`).

   Its transport, though, is sound: the one replaceable request function
   (`jira.py:129-185`), a timeout on every call, and one error class per HTTP
   cause, never interpreted from the message (`jira.py:410-439`).

## Goals

1. **A Jira Cloud implementation of TCW-69's backend interface.** It provides all
   eleven operations, declares `external_stages = {request, qa}` and
   `inbox_items = false`, and never stores on disk a fact Jira owns.
2. **Ticket-first identity.** Folders are named `<KEY>-<title words>`, `item.yaml`
   holds only `ticket: <url>`, and the TCW Project and TCW Item fields are always
   set on tickets TCW creates or adopts.
3. **A stage change is one workflow transition** that carries the move's note as a
   comment. TCW confirms the move by reading the status back. When several
   transitions lead to the target status it prefers the one whose screen asks for
   nothing but a comment, and refuses when that leaves none or more than one (epic
   decision 5).
4. **The Jira inbox:** `tcw work tickets list` and `tcw work tickets adopt <KEY>`.
5. **Delegation into Jira-mode projects** through `tcw work new --project <id>`.
6. **The `work.jira` configuration block**, parsed and checked offline.
7. **`tcw validate --remote`** checks the workflow, the fields, and the agreement
   between each item and its ticket. Plain `tcw validate` stays offline.
8. **The 2.x tracker integration is gone:** code, commands, configuration, tests and
   capability records.
9. **Tested without the real Jira in continuous integration (CI)**, and checked once
   against a real Jira project before the slice is accepted.

## Non-goals

- **Anything TCW-69 defines:** the stage table, properties, layout, `advance`,
  gates, `work.*` parsing and the backend protocol. This slice implements the
  protocol; where it needs the protocol changed, Notes says so.
- **The filesystem backend and the CLI switch-over** (TCW-70). That includes
  `new --project` for filesystem targets and the shared "can the target's folder be
  created" check.
- **Personal configuration and identity resolution** (TCW-72). This slice provides
  the Jira half of identity (Design 10) and nothing else.
- **Command names, the surface of every command, the output format rules and the
  exit-code table** (TCW-73; epic decisions 2 and 10). TCW-73 lands after this slice,
  so this slice adds `tickets list`, `tickets adopt` and `validate --remote` already
  following TCW-73's spec (one identifier per stdout line, details through `--json`,
  `validate` printing findings only), and TCW-73 then owns their final surface.
- **The `setup` skill's workflow walkthrough, every prompt, and every other skill
  and agent** (TCW-74; decision 3). This slice supplies the `validate --remote`
  findings that the walkthrough reads.
- **Guides, including `docs/guide/jira.md`, and everything under
  `skills/configure/`, including `skills/configure/references/tracker.md`** (TCW-75;
  decision 3).
- **Migrating TCW's own board, configuration and Jira project** (TCW-76). That
  includes adding statuses and fields to the TCW Jira project.
- **Jira Server and Data Center**, other trackers, and any "relates to" link.
- **Filling transition screen fields** (Design 13).
- **Automatic changes to a Jira workflow.** `validate --remote` reports; a person
  changes the workflow.

## Design

New code lives in a package `tcw/work/jira/`:

- `client.py`: HTTP, moved from `tcw/tracker/jira.py` (Design 14);
- `config.py`: `work.jira` parsing;
- `mapping.py`: properties to and from ticket fields, and the Atlassian Document
  Format (ADF, the JSON document format Jira's version 3 API uses for rich text);
- `jql.py`: every Jira Query Language (JQL) string TCW sends;
- `backend.py`: `JiraBackend`, the eleven operations;
- `tickets.py`: `tickets list`, `tickets adopt`, and delegation into a Jira project;
- `remote.py`: the `validate --remote` checks.

Only `client.py` touches the network, and only its `_request` function.

### 1. Configuration (`config.py`)

TCW-69's `parse_work_config` passes `work.jira` through unparsed, and errors when
`backend` is not `jira` (TCW-69 Design 8). `parse_jira_config(mapping) ->
(JiraConfig, problems)` accepts exactly these keys:

| key | required | value |
| --- | --- | --- |
| `site` | yes | `https://<host>`, no path, no trailing `/` |
| `project` | yes | a Jira project key, `^[A-Z][A-Z0-9_]+$` |
| `credentials` | yes | `{email-env, token-env}`, each an environment variable *name* matching `^[A-Z_][A-Z0-9_]*$` |
| `fields` | yes | `{project, item, effort?, complexity?}`: Jira field *display names* |
| `priorities` | no | a mapping from some or all of the five model priorities to Jira priority names; the default is `Highest`, `High`, `Medium`, `Low`, `Lowest` |
| `issue-type` | no | the issue type of a new top-level ticket; default `Task` |
| `inbox-query` | no | a JQL string that widens the inbox (Design 7) |
| `timeout` | no | seconds per request, a positive number; default 15 |

- **[Decision] `issue-type` and `timeout` are added to the ticket's sketch.** Jira
  refuses to create an issue without a type. The 15-second default is 2.x's
  (`tcw/store/base.py:1315`), and the transport needs some timeout, because a request
  without one waits forever (`jira.py:132-136`).
- Unknown keys are errors, at every level.
- Values are never secrets. Config names environment variables, and the client reads
  their values only inside `_request`, as today (`jira.py:138-146`).
- **A malformed credential variable name** is reported by naming its key (for
  example `work.jira.credentials.token-env`) and the rule it breaks, and **never
  prints the value**. The value may come from a personal file (TCW-72) and may be a
  token pasted there by mistake. The same holds for the connected-project `jira`
  block (Design 8).
- Statuses are not here. Each enabled stage's `work.stages.<stage>.status` is
  TCW-69's, which already requires a distinct status for every enabled non-side stage,
  inbox included (TCW-69 Design 8, check 6).
- Which keys a person may override is TCW-72's allowlist. It already names the
  credential variable names; every other key here is shared.
- Field names are resolved to Jira field IDs at run time (Design 12), not in config.

### 2. Identity, folders and `lookup`

1. **Folder name:** `<KEY>-<title words>`, matching
   `^(?P<key>[A-Z][A-Z0-9_]*-[1-9][0-9]*)-[a-z0-9]+(-[a-z0-9]+)*$`, within TCW-69's
   128-character limit. Title words come from TCW-69's `title_words`. A Jira key is
   at most 19 characters with its trailing `-`, inside TCW-69's 20-character prefix
   allowance. A name that already exists is refused (exit 3).
2. **`item.yaml`** is exactly `ticket: <site>/browse/<KEY>`. It is a convenience
   link; the key in the folder name is authoritative. Offline `tcw validate` reports
   an error when:
   - the file has any other key;
   - the URL's site differs from `work.jira.site`;
   - the URL's key differs from the folder's key.
3. **[Decision] The TCW Item field holds the full slug** (`tcw/TCW-67-…`, TCW-69
   Design 1). A ticket read from another project, or a ticket found as someone's
   parent or blocker, then names its item without TCW knowing which project it came
   from. TCW Project holds the owning project's `tcw-config.id`.
4. **`lookup(name)`** reads no network.
   - It upper-cases `name`. If the result is not a whole key
     (`^[A-Z][A-Z0-9_]*-[1-9][0-9]*$`), the answer is `None`.
   - Otherwise it returns the folder in the work path whose name starts with
     `name + "-"` and matches the pattern above. That is an exact match on the key,
     so `TCW-6` never finds `TCW-67-x` (TCW-69 Design 5.3).
   - Two such folders is `BackendError` (exit 1) naming both. Offline `validate`
     also reports duplicate keys.
5. **`rename(folder, title_words)` changes only the part after the key** (Design 4.4).

### 3. Reading: `read` and the property mapping (`mapping.py`)

`read(folder)`:

- A folder that does not exist here, or whose name does not match the pattern, is
  `NotFound` (exit 4).
- Otherwise TCW sends one `GET /rest/api/3/issue/{key}` asking for these fields:
  `summary`, `status`, `created`, `priority`, `labels`, `assignee`, `parent`,
  `issuelinks`, `issuetype`, and the configured custom fields.
- A 404 is `NotFound`, and the message says the folder's ticket does not exist.
- If Jira answers with a different key (the ticket was moved to another Jira project,
  and Jira follows the old key), the item is still returned. A warning on stderr names
  both keys, and `validate --remote` reports it as an error (Design 9.2).

| Property | Jira | Read | Write |
| --- | --- | --- | --- |
| title | Summary | as is | as is |
| stage | Status | the enabled stage whose `status` equals the status name exactly; otherwise `None` (TCW-69: no stage) | only through `set_stage` |
| created | `created` | the date part of the timestamp as Jira returns it | never |
| priority | Priority | the model name whose mapped Jira name matches; otherwise `None` | the mapped name |
| effort, complexity | the configured custom fields (single-choice lists) | the option whose value, lower-cased with spaces turned into `-`, is a scale name; otherwise `None` | that option |
| tags | Labels | the labels that are in the project's tag registry, in Jira's order | added and removed one by one, so other labels are untouched |
| assignee | Assignee | the account ID, or `None` (Design 10) | an account (Design 4.2) |
| parent | Parent | a slug (Design 3.1); a parent ticket with no item leaves `parent` as `None` and puts its key in `untracked` | the parent's key |
| blocked-by | links of type `Blocks` where this ticket is the blocked one | slugs (Design 3.1); blocker tickets with no item go to `untracked` as keys | links created and deleted |

**[Decision] Labels outside the tag registry are ignored, not reported.** People
outside engineering label tickets freely. TCW neither shows nor removes those labels,
and `validate` does not warn about them.

**[Decision] Priority, effort and complexity can read as `None`.** A team-managed
project may have no Priority field at all. An estimate field may be unset, or set to
an option outside the scale. TCW-69's `Item` allows `None` for `priority` (TCW-69
Design 2.1; epic decision 16).

#### 3.1 Turning ticket keys into slugs

A parent or blocker arrives as a ticket key. Each key resolves as follows:

1. If `lookup(key)` finds a folder here, the slug is `<this project>/<folder>`.
2. The remaining keys are read in **one** `key in (…)` search, asking for TCW
   Project and TCW Item. A TCW Item value that parses as a slug is that slug.
3. A key left over is an **untracked reference**: a ticket with no item. It goes
   into `Item.untracked`, a tuple of ticket keys (TCW-69 Design 2.1; epic decision
   16), parent first, then blockers in Jira's order, with no key twice. `show`
   prints them as bare keys (ticket: "`show` displays links to tickets that have no
   item as bare keys"). The filesystem backend always leaves `untracked` empty.

**`untracked` does not say which relation a key came from.** TCW-69's field holds
keys only. A person who needs to know reads the ticket in Jira, and `edit` never
takes an untracked key, because `--parent` and `--blocked-by` name items.

#### 3.2 `read_request` and `read_comments`

TCW-69 Design 5.4 defines both (epic decision 1). In Jira mode:

- **`read_request(folder)`** sends one `GET /rest/api/3/issue/{key}?fields=description`
  and turns the description into text with `_document_text` (Design 14). An empty
  or missing description is `None`. Folder and 404 handling are as in `read`.
- **`read_comments(folder, limit)`** reads
  `GET /rest/api/3/issue/{key}/comment?orderBy=-created`, newest first, page by page
  (`startAt`, `maxResults`) until it has `limit` comments or Jira has no more. Each
  becomes TCW-69's `Comment`:
  - `at`: the comment's `created` timestamp, in UTC;
  - `author`: the author's account ID, or `None` when Jira gives none (a deleted
    account);
  - `text`: the body through `_document_text`.

  2.x's `recent_comments` (`tcw/tracker/jira.py:333-342`) read one page of 100 and
  returned account IDs; it changes to this.

**[Decision] A comment's author is an account ID**, the same form as `assignee` and
`current_user()` (Design 10), so every person in Jira mode is named one way. Display
names are for output only, through `user_name` (Design 7.3).

### 4. Writing: `create`, `update`, `comment`, `rename` (`backend.py`)

Each operation below is a fixed sequence of requests. Where a sequence can stop part
way, it is ordered so that every stopping point is a state the model allows, and the
error names what was done.

#### 4.1 `create(title, props, *, stage, request)`

`stage` must be the first flow stage whose artifact is not `none` (request). Any
other stage is a `UsageError`. Inbox is already refused by TCW-69, because
`inbox_items` is false.

1. **Resolve, reading only:**
   - The parent's key (Design 3.1, in reverse) and the issue type the child needs
     (Design 11).
   - The assignee's account (Design 4.2).
   - Each blocker's key. A blocker or parent that is not a Jira ticket on this site
     is refused (exit 3). For example, an item in a filesystem-mode project, whose
     folder name does not match the key pattern.
2. **Create the ticket** (`POST /rest/api/3/issue`) in one request, with:
   - `project`, `issuetype` and `summary`;
   - `description`: the request as ADF paragraphs, one per blank-line-separated
     block (Design 14), or no description when `request` is `None`;
   - `priority`, `labels`, `assignee` and `parent`;
   - the effort and complexity fields;
   - TCW Project set to this project's id.

   Priority is sent only when the project's create metadata has a Priority field
   (Design 11). An explicit priority in a project without one is refused before
   anything is created (exit 3).
3. **Check the route to the request status.**
   - If the new ticket is already in the request stage's status, there is nothing to
     move.
   - Otherwise TCW reads the ticket's transitions and applies the choice rule of
     Design 5 step 2. If it picks one, that transition is used in step 6.
   - If it picks none, TCW stops: `Refused` (exit 3), carrying the key (TCW-69
     Design 5.5; epic decision 16). The ticket stays with no item, which is a legal
     state (an inbox entry if it sits at the inbox status). The command prints the
     key on stdout, as TCW-73 already does when delegation stops at an inbox.
4. **Set TCW Item** to the new slug (`PUT /rest/api/3/issue/{key}`).
5. **Write the folder and `item.yaml`.**
6. **Apply the transition** from step 3, if one is needed. Then read the status back.
   If it is not the request status, the result is `BackendError` (exit 1). The item
   exists, the message names its stage, and `tcw work advance <slug>` moves it on.
7. **Create the `Blocks` links.**

**[Decision] Checking the route (step 3) before setting TCW Item** means a workflow
that cannot reach request leaves a plain ticket, not an item stuck at the inbox
status. The same check comes first in `adopt` and in delegation.

#### 4.2 `update(folder, changes)`

1. Resolve, reading only, as in 4.1 step 1. For the assignee:
   - **[Decision]** a value is first tried as an account ID (`GET /rest/api/3/user`);
   - otherwise it is searched among the project's assignable users;
   - exactly one match is used;
   - no match is `NotFound` (exit 4);
   - several matches are `Refused` (exit 3), listing up to ten of them.
2. **One edit request** (`PUT /rest/api/3/issue/{key}`) carries every field change.
   Labels go in its `update` section as individual `add` and `remove` operations.
   Assignee and parent go in `fields`.
3. **Then links:** one `POST /rest/api/3/issueLink` per blocker added, and one
   `DELETE /rest/api/3/issueLink/{id}` per blocker removed.
4. The answer is the item read again.

**Partial failure.** If the edit succeeds and a link request fails, the result is
`BackendError` (exit 1). The message says the fields were saved, and names the links
that were and were not changed. Re-running the same `edit` is safe:
- adding a link that exists is skipped after reading the current links;
- removing one that is gone is skipped.

**Changing the parent** checks the hierarchy before any request (Design 11). Jira
cannot change an issue's type through this API, so a ticket whose type cannot sit
under the new parent is refused (exit 3) with both issue types named.

#### 4.3 `comment(folder, text)`

One `POST /rest/api/3/issue/{key}/comment` with the text as ADF paragraphs.

#### 4.4 `rename(folder, title_words)`

1. Build `<KEY>-<title words>`. Words that are not valid are a `UsageError`. A name
   that already exists is `Refused` (exit 3). A name equal to the current one is
   `Refused` as a no-op.
2. Set TCW Item to the new slug. If this fails, nothing has changed.
3. Rename the folder on disk. If that fails, TCW sets TCW Item back (a best effort),
   and the result is exit 1, naming both values.
4. Nothing else is rewritten. Parent and blocker references live in Jira as keys,
   which a rename does not change. As in TCW-70, TCW lists other mentions of the old
   slug in this project's files on stderr, and edits none of them.

### 5. Moving: `set_stage(folder, stage, note)`

TCW-69 Design 5.2 defines the contract: move, record the note as part of the move
where possible, return the reported stage, and raise `Refused` or
`MovedWithoutNote`. `advance` has already run every check and gate. The Jira
implementation:

1. **Read the transitions** the ticket offers now, with their screen fields
   (`GET /rest/api/3/issue/{key}/transitions?expand=transitions.fields`).
2. **Choose one** (epic decision 5). This is the *choice rule*; `create`, `adopt`,
   delegation and `validate --remote` use the same one.
   - Keep the transitions whose destination status name equals the target stage's
     `status`. These are the candidates.
   - Exactly one candidate: use it.
   - Several: keep those whose screen asks for nothing but a comment, meaning the
     transition has no screen, or its expanded `fields` names no field other than
     `comment`. If exactly one is left, use it.
   - Otherwise `Refused` (exit 3), having changed nothing. With several candidates
     left, the message lists them, each as `name → destination` with the fields its
     screen shows. With none, it lists every transition offered. It never walks
     through intermediate statuses.

   **[Decision]** The first case uses a lone candidate even when its screen has a
   required field: the request then fails, and Design 13 reports it. Refusing it
   here instead would hide Jira's own message about which field is missing.
3. **Apply it, with the note in the same request:** `POST …/transitions` with
   `{"transition": {"id": …}}`, plus, when `note` is given,
   `{"update": {"comment": [{"add": {"body": <ADF of note>}}]}}`.
4. **Read the status back** (`GET` the issue, status only), and return the stage it
   maps to, or `None`. `advance` compares that with the target (TCW-69 Design 6.7).

**When Jira refuses the request (HTTP 400).** Jira gives the same status for different
causes, and 2.x recorded three different message bodies for one of them
(`jira.py:17-24`). So TCW never reads the message to decide. It reads the status:

- **Status already at the target:** the move happened. Return it.
- **Status unchanged, and a note was sent:** retry the transition once without the
  comment.
  - If that succeeds, post the note with `comment`. If posting fails, raise
    `MovedWithoutNote`.
  - If the retry is refused too, raise `Refused`, carrying Jira's message text
    verbatim as detail (Design 13).
- **Status unchanged, and no note was sent:** `Refused`, with Jira's text.

**[Decision] The retry without a comment** exists because Jira may reject a comment on
a transition whose screen does not show the comment field. That is not certain; the
live check settles it (Design 15.4). The retry costs one request, and without it the
first such workflow would refuse every forced move. When the comment is accepted,
which is the common case, the note and the move are one request, as the owner decided
for TCW-69.

**When the connection fails mid-request** (`Unreachable`), the request may have
landed. TCW reads the status once more:

- **Status at the target:** the move happened. TCW looks for the note among the
  ticket's newest comments, by exact text. If it is not there, raise
  `MovedWithoutNote`.
- **Status unchanged:** raise `Unreachable` (exit 5).
- **The status cannot be read either:** raise `Unreachable`, with a message saying
  the move may have happened and to check with `tcw work show`.

A ticket moved by hand in Jira is, by the ticket's definition, a forced move without
a recorded reason. TCW cannot see that it happened. `validate --remote` reports any
item whose stage is ahead of its artifacts (TCW-69 Design 9).

### 6. Listing: `list(query)` and `jql.py`

One JQL query, read page by page through `POST /rest/api/3/search/jql` with
`nextPageToken` until Jira says the page is the last. 2.x read one page only
(`jira.py:216-219`); a list that stops early hides items.

```
project = "<project>" AND cf[<TCW Project id>] ~ "<id>" AND cf[<TCW Item id>] IS NOT EMPTY
  [AND status IN (...)]            # Query.stages: their configured statuses
  [AND status NOT IN (...)]        # default: the completion and discard stages' statuses
  [AND parent = "<KEY>"]           # Query.parent
  [AND assignee = "<accountId>"]   # Query.assignee, resolved as in 4.2
ORDER BY created ASC
```

- `Query(all=True)` drops the status clause. The default (TCW-69 Design 5.1) excludes
  only the two terminal statuses, so a ticket in an unmapped status, which has no
  stage, is listed.
- `Query.stages` containing a stage with no status (a disabled stage) is a
  `UsageError`.
- **[Decision] Exact match on TCW Project happens after the search.** JQL's `~` on a
  text field is a word search, not equality: `tcw` also matches `tcw-web`. The query
  narrows, and TCW keeps only tickets whose TCW Project equals the id exactly. That
  still lets several TCW projects share one Jira project.
- A parent filter whose slug is not a ticket gives an empty list without a request.
- Each ticket returned becomes an `Item`. It must name, in TCW Item, a slug of this
  project whose folder exists here. If the folder is not here (for example the item
  was created on another branch), the ticket is left out and stderr names it.
- Parents and blockers of every returned item are resolved together, with at most one
  extra `key in (…)` search (Design 3.1). So a `list` costs one query, plus at most one
  more, however many items there are. **[Decision]** The ticket's "one batched JQL
  query" is read as "never one request per item".
- Every string placed in JQL goes through one quoting function: wrap it in `"`, and
  escape `\` and `"`. Custom fields are addressed by ID (`cf[10042]`), never by name.

### 7. The Jira inbox: `tickets list` and `tickets adopt` (`tickets.py`)

These are Jira-only commands outside the backend interface (TCW-69 Design 5.7). In
filesystem mode both are usage errors (exit 2), per TCW-73.

#### 7.1 `tcw work tickets list [--json]`

The inbox is every ticket where all of these hold:

- it is in the configured Jira project;
- it is at the inbox stage's status;
- TCW Item is empty;
- TCW Project is empty or equals this project's id.

The query is:

```
project = "<project>" AND status = "<inbox status>" AND cf[<item>] IS EMPTY
  AND (cf[<project field>] IS EMPTY OR cf[<project field>] ~ "<id>")
```

- With `inbox-query` set, the JQL is `(<default>) OR (<inbox-query>)`. **[Decision]**
  "Widens" means the union.
- Either way, TCW keeps only tickets whose TCW Item is empty and whose TCW Project is
  empty or exactly this id. A ticket that already has an item, or belongs to another
  project, is never an inbox entry, whatever the query says.
- Every page is read. The order is by creation date, oldest first.
- **stdout** has one ticket key per line (epic decision 10). `--json` gives an array
  of `{key, summary, status, created, reporter, url, description}`. stderr gives the
  count and the JQL that ran.
- **[Decision] `--json` includes each ticket's description**, as plain text through
  `_document_text`, or `null` when there is none. TCW-74's inbox prompt can then
  triage a ticket without adopting it. The search asks for the `description` field
  as well, so this costs no extra request.

#### 7.2 `tcw work tickets adopt <KEY>`

1. **Read the ticket**, which is all that happens before the checks. A 404 is exit 4.
2. **Refuse (exit 3), changing nothing,** when:
   - the ticket is in another Jira project than `work.jira.project`;
   - TCW Project names another project;
   - TCW Item is set (but see resuming, below);
   - a folder named for this key already exists here;
   - the ticket's status is neither the inbox status nor the request status.
     **[Decision]** Adopting a ticket that is already further along would skip
     stages with no trace;
   - the ticket is at the inbox status and the choice rule (Design 5 step 2) picks
     no transition to the request status (as in 4.1 step 3).
3. **Set TCW Project and TCW Item** in one edit. The folder is `<KEY>-<words>`, with
   the words taken from the summary.
4. **Write the folder and `item.yaml`.**
5. **Move to request** if the ticket was at the inbox status, and read the status back.
6. **stdout** has the slug (TCW-73).

**Resuming.** If TCW Item already names a slug of *this* project, that slug's key is
`<KEY>`, and its folder does not exist here, `adopt` creates that exact folder and
continues from step 5. It says so on stderr. This is how a run that stopped between
steps 3 and 5 is finished, without a check that would otherwise refuse it forever.
**[Decision]** The ticket says to refuse whenever TCW Item is set; this exception
applies only to TCW Item naming the very item `adopt` would create.

**Two people adopting at once** is a known limit, as the ticket says. Both may set
TCW Item. The later write wins in Jira, and each person has a folder. If both folders
have the same name, git merges them as one. If not, `validate --remote` reports the
folder whose slug the ticket does not name.

#### 7.3 Jira-only helpers for display (`tickets.py`)

Three functions sit beside `tickets list`, outside the backend interface, for the
CLI's output (TCW-73) and the web viewer (TCW-77). None changes anything.

- **[Decision] `ticket_link(folder) -> (label, url)`** gives `("Jira",
  "<site>/browse/<KEY>")`. It reads no network and no file: the key is
  authoritative in the folder name (Design 2), and the site is `work.jira.site`. A
  folder name that does not match the pattern is `NotFound` (exit 4). Callers use it
  rather than building the URL themselves or reading `item.yaml`.
- **[Decision] `user_name(account_id) -> str | None`** gives a person's display
  name. It answers from the names already present in the responses this command
  has read (every `assignee` and comment `author` object carries `displayName`), so
  showing an item costs no extra request. Otherwise it sends one
  `GET /rest/api/3/user?accountId=…`. `None` means Jira gives no name (a deleted
  account); output then shows the account ID.
- **[Decision] `assignable_users(query, limit=20) -> list[(account_id,
  display_name)]`** gives the project's assignable users matching `query`, over the
  client's `assignable_users` (Design 14), which Design 4.2's assignee search uses
  too. It exists for the viewer's assignee chooser.

In filesystem mode none of the three exists; a caller that asks is a usage error
(exit 2), as for the other Jira-only commands.

### 8. Delegation into a Jira-mode project (`tickets.py`)

`tcw work new "title" --project <id>` is TCW-70's command. TCW-70's draft opens
the target through `open_delegation_target` and leaves a Jira branch in it that
refuses with exit 1 until this slice. This slice fills that branch with
`delegate_to_jira(target, title, request, priority)`, which returns either a slug
or a ticket key. In the same way, it fills TCW-70's `open_backend` and
`open_project` branches for `backend: jira`. Through `open_project`, a Jira-mode
project that is declared but not on this machine is `Unreachable` (exit 5), as for
any project (epic decision 4): its items are folders in its checkout.

1. **Target settings.**
   - If the target's `tcw-config.yaml` can be read, TCW uses its tracked configuration
     only (TCW-72: personal layers apply only to the project a command acts on):
     `work.jira`, the inbox and request statuses, and the credential variable
     *names*.
   - Otherwise the target is declared but not on this machine. TCW uses the
     delegator's connected-project entry for the target, which gains an optional
     `jira` block: `{site, project, inbox-status, credentials: {email-env,
     token-env}, fields: {project}}`.
   - With neither, the result is `Refused` (exit 3), saying the target is not on
     this machine and its Jira settings are unknown. This is epic decision 4's
     "delegation into a project not on this machine is exit 3".
   - **[Decision]** With a `jira` block, delegation into a target that is not on
     this machine still creates the ticket in the target's inbox, prints the key and
     exits 0, as in step 4. The ticket's own text names the connected-project entry
     as a source of the target's settings, which only matters when the target's
     config cannot be read; the inbox ticket is the whole delegation there, and it is
     a legal state for the target. Decision 4's exit 3 applies when TCW can create
     nothing at all.
   - **[Decision]** The site and the credential names always come from the same file,
     so a token is never sent to a site that a different file named. This is 2.x's
     rule, `work/inherit-tracker-settings-from-parent-nodes`.
2. **Create the ticket** in the target's Jira project, with summary, description,
   priority, and TCW Project set to the target's id.
3. **Place it at the target's inbox status.** If it is not there already, TCW applies
   the transition the choice rule (Design 5 step 2) picks. If it picks none, the
   result is `Refused` (exit 3) carrying the key, with the key on stdout: the ticket
   exists but is outside the target's inbox.
4. **Try to create the item.** It is created only if all of these hold:
   - the target's path is resolved;
   - its work store exists;
   - there are no uncommitted changes in it (TCW-70's shared check, which reads git
     and changes nothing);
   - the choice rule picks a transition from the inbox status to the request
     status.

   If so, TCW sets TCW Item, writes the folder in the target, moves the ticket to
   request, prints the slug, and names the files on stderr, left uncommitted.
   Otherwise the ticket stays in the target's inbox: TCW prints the key and exits 0
   (TCW-73), and stderr says which condition failed. A target not on this machine
   fails the first condition.
5. **No gates run**, since creation is not a move (TCW-69 Design 6).

**[Decision] Delegation sets only title, request and priority.** Tags must be in the
*target's* tag registry, and assignees are people on the target's site. Other
property flags given with `--project` against a Jira target are usage errors (exit 2).
TCW-70 decides the same question for filesystem targets.

### 9. Validation

#### 9.1 Offline `tcw validate` in Jira mode

This needs no network and no credentials. It checks:

- the `work.jira` shape (Design 1);
- each folder in the work path against the name pattern, and its `item.yaml`
  (Design 2.2);
- that no two folders share a key;
- that no item has a `request/` or `qa/` folder. Each is a warning, saying Jira owns
  those stages' records and the folder is ignored.

It does not report stage, references or anything else Jira owns.

#### 9.2 `tcw validate --remote`

This runs every offline check, then the checks below for each Jira-mode project that
`validate` visits. Every request is a read. Problems are **errors** unless marked
*warning*.

1. **Access.**
   - `GET /rest/api/3/myself` must succeed. Rejected credentials are an error, and
     the rest of that project's remote checks are skipped.
   - The project must be readable (`GET /rest/api/3/project/{key}`).
2. **Fields.** Through the project's create metadata for the configured issue type
   (Design 12):
   - TCW Project and TCW Item exist as text fields;
   - effort and complexity, when configured, are single-choice lists whose options
     cover the four scale names;
   - every mapped priority name exists;
   - the `Blocks` link type exists (`GET /rest/api/3/issueLinkType`).
3. **Statuses.** Each enabled stage's status exists in the project, for each checked
   issue type (`GET /rest/api/3/project/{key}/statuses`). That two stages do not share
   one is already checked offline (TCW-69).
4. **Moves.** For each checked issue type, the choice rule (Design 5 step 2) must
   pick a transition for every move TCW needs:
   - inbox to the request stage (adoption and delegation);
   - each enabled flow stage to the next enabled flow stage, and the last one to the
     completion stage;
   - each verdict stage to its `on_reject` stage;
   - each enabled non-terminal flow stage after inbox to the discard stage.

   Backward moves, forced skips and reopening are not needed, so they are not checked;
   when a workflow lacks them, `advance` refuses and lists what is offered.
5. **How the moves are found.**
   - First TCW reads the workflow definition (`POST /rest/api/3/workflows` for the
     project and issue type). It counts a transition that can start from any status
     as offered from every status.
   - If that is refused for lack of permission, TCW samples: for each source status it
     searches for one ticket of that type in that status, and reads its transitions,
     with their screen fields (`expand=transitions.fields`).
   - A move whose source status has no sample ticket is reported as *unchecked*, a
     warning, and never as passing.
   - **[Decision]** When the definition shows several candidates for one move, the
     choice rule needs their screen fields, which TCW reads only from a sample
     ticket. TCW then samples that source status as above. With no sample ticket the
     move is *unchecked*; with one, the rule decides.
   - A needed transition whose screen has a required field is an error (Design 13).
     Required fields are visible only through a sample ticket. When the definition was
     read, a finding says screen fields were not checked.
6. **Checked issue types** are the configured `issue-type` plus every issue type that
   an existing item's ticket has. **[Decision]** Checking every type in the project
   would report errors for types TCW never touches; checking only one would miss
   adopted Bugs.
7. **Items and tickets.** One `key in (…)` search over every folder's key, plus the
   default inbox search, checks:
   - each folder's ticket exists;
   - its key is unchanged;
   - its TCW Project is this id;
   - its TCW Item is this folder's slug;
   - an item at the inbox status is a *warning*: it can be moved on with `advance`;
   - a ticket whose TCW Item names this project's slug, with no folder here, is a
     *warning*: the item may be on another branch.
8. **TCW-69's model checks:** stage ahead of artifacts, and references. These are
   warnings, and in Jira mode they run here, because both need Jira (TCW-69
   Design 9).

**Output** follows TCW-73's rules (epic decision 10). stdout carries findings
only, one per line, as `<severity>: <where>: <message>`, where `<where>` is the
folder's slug, the ticket key, or `work.jira` for project-wide checks. An unchecked
move is a finding: a `warning` whose message starts `unchecked:` and names the
source status, the target status and the issue type. Checks that passed are
narrated on stderr, never stdout. A clean run prints nothing on stdout. The `setup`
skill (TCW-74) works through the findings with the user. **It never changes Jira.**

**Exit codes** follow TCW-73:

- 0 with warnings only;
- 1 with any error;
- 5 when Jira cannot be reached. The findings from checks completed before the
  connection failed are still printed.

### 10. Errors, network and identity

**The client's error classes** stay as they are (Design 14). The backend turns each
into one of the exception classes in `tcw/errors.py` (TCW-69 Design 5.5; epic
decision 8) in one place:

| client error | HTTP | `tcw/errors.py` class | exit |
| --- | --- | --- | --- |
| `Unavailable` | 5xx, refused or dropped connection, timeout | `Unreachable` | 5 |
| `RateLimited` | 429 | `Unreachable`, naming `Retry-After` when given | 5 |
| `AuthError` | 401, or a credential variable unset | `BackendError`, naming the variables | 1 |
| `PermissionError` | 403 | `BackendError` | 1 |
| `NotFound` | 404 | `NotFound` | 4 |
| `RequestInvalid` | other 4xx | `BackendError`, with Jira's text; inside `set_stage`, as Design 5 | 1 or 3 |
| shape error | an unexpected answer | `BackendError` | 1 |

- **[Decision] No automatic retry**, even on 429. A command that sleeps and tries
  again is not predictable. Exit 5 tells the caller to try again later.
- **The network is needed** by every operation except `lookup`, by `tickets`, and by
  `validate --remote`. Plain `validate` and every model check of what git owns
  (records gate, completion gate, `path`, rounds) need none. That is why the
  completion gate checks only review in Jira mode (TCW-69 Design 7).
- **Identity** is the account the credentials belong to. `current_user()` is one
  of TCW-69's eleven operations (TCW-69 Design 5.4; epic decisions 1 and 17,
  replacing TCW-72's proposed `me()`). The Jira backend sends
  `GET /rest/api/3/myself` once per command and returns the `accountId`.
  - **[Decision] One form for a person in Jira mode: the account ID.** TCW-69
    Design 5.4 requires `current_user()` to return the same form the backend uses
    for `Item.assignee`, so the two compare directly. Display names are not unique
    and can change, while every Jira write and query that takes a person needs the
    account. So `current_user()`, `Item.assignee` and `Comment.author` are all
    account IDs. Input stays friendly: an assignee given to `update`, `create` or
    `Query` may be an account ID or a name to search for (Design 4.2). The display
    name appears only on output, through the Jira-only `user_name` (Design 7.3).
  - It never returns `None`. Unset credential variables are `BackendError` (exit 1)
    naming them, as in the table above, because no other Jira operation could run
    either.

### 11. Hierarchy: creating children, and parents in other projects

The model sets no depth limit (TCW-69 Design 2.6). Jira's issue hierarchy does, so the
backend narrows it.

1. The backend reads the project's issue types once per command
   (`GET /rest/api/3/project/{key}`). Each type carries a hierarchy level: 1 for epics,
   0 for standard types, −1 for sub-tasks, and higher levels on premium plans.
2. **A new child's type** depends on the parent ticket's level `L`:
   - `L - 1 == 0`: the configured `issue-type`;
   - `L - 1 == -1`: the project's sub-task type, found by its `subtask` flag rather
     than its name, because team-managed projects call it `Subtask` and
     company-managed ones `Sub-task`;
   - `L - 1 >= 1`: the one type at that level;
   - otherwise, or with no single type to choose: `Refused` (exit 3), naming the
     parent's type. For example, "TCW-12 is a Sub-task; Jira gives sub-tasks no
     children."
3. **Changing an existing item's parent** is refused (exit 3) when the item's own type
   is not exactly one level below the parent's, because this API cannot change an
   issue's type.
4. **[Decision on the open question] A parent or blocker in another Jira project** on
   the same site is allowed. TCW sends it, and if Jira refuses, the result is exit 1
   with Jira's text, plus a hint that the project type may not allow cross-project
   parents. Team-managed projects are reported not to allow them; the live check
   records what this site does (Design 15.4). Blocking links across projects are
   ordinary Jira links. A parent or blocker in a filesystem-mode project, or on
   another site, is refused before any request (exit 3).

### 12. Team-managed projects

**[Decision on the open question]** TCW supports company-managed and team-managed
projects with one code path. It never branches on the project's kind, and relies only
on reads that both answer.

- **Custom fields** in team-managed projects belong to the project. Another project
  may have a field with the same name. So field names are resolved through the
  project's own create metadata
  (`GET /rest/api/3/issue/createmeta/{project}/issuetypes/{typeId}`), never the
  site-wide field list. The same metadata says whether Priority exists.
- **Statuses** are matched by name, which works in both kinds. Status IDs differ
  between team-managed projects.
- **The sub-task type** is found by its flag (Design 11).
- **Transitions** offered by a ticket read the same in both kinds (2.x established
  this, `jira.py:244-251`). Whether the workflow definition can be read in a
  team-managed project is not known. Design 9.2 falls back to sample tickets either
  way.
- **Priority** may be missing from a team-managed project. Then `--priority` is
  refused (exit 3), `new` sends no priority, and read gives `None`.

### 13. Transition screens with required fields

**[Decision on the open question]** TCW never fills in transition screen fields other
than the comment. A transition `advance` needs that requires another field (for
example a resolution on the done status) makes every such move refuse (exit 3), with
Jira's message and the advice to set the value in a workflow post function instead.
`validate --remote` reports it ahead of time when a sample ticket shows it (Design
9.2). Filling fields would need per-transition field configuration and values TCW
cannot know, and Jira's standard way to set a resolution is a post function, which
needs no screen.

A required *comment* on a rejection screen is satisfied whenever `advance` gives a
reason. TCW-69 requires a reason to leave qa, so the comment travels with the
transition (Design 5).

### 14. What is kept from 2.x, and what is removed

**Kept, moved to `tcw/work/jira/client.py`:**

- `_request`, the only function that touches the network (`jira.py:129-185`), with
  its per-call timeout and credential reading;
- the error classes and `_for_status` (`jira.py:45-80`, `410-439`);
- the response-shape guards (`jira.py:363-407`);
- `myself`, `issue` (`jira.py:204`, `234`);
- `transitions`, now quoting the key and always expanding screen fields, which the
  choice rule needs (`jira.py:244-263`);
- `add_comment` and `_document_text` (`jira.py:327-331`, `345-360`).

**Changed:**

- `search` returns every page and takes a field list (`jira.py:208-232`);
- `create_issue` takes any fields (`jira.py:266-288`);
- `apply_transition` takes an optional comment (`jira.py:290-298`);
- `recent_comments` becomes `comments(key, limit)`: every page up to `limit`, with
  each comment's author account ID, author display name and `created`
  (`jira.py:333-342`; Design 3.2).

**Added:**

- `edit_issue`;
- `add_link` and `delete_link`;
- `user` and `assignable_users`;
- `project`, `project_statuses` and `create_metadata`;
- `link_types`;
- `workflows`.

**Dropped:**

- `assign`, since assignee goes through `edit_issue`;
- `description` (`jira.py:315-325`). **[Decision]** `read_request` reads the request
  through the version 3 API and turns ADF into text with the kept `_document_text`
  (Design 3.2), so one API version is used throughout.

The ADF paragraph builder in `tcw/tracker/create.py:47-66` moves to `mapping.py`,
without its "Tracked in TCW as" footer. The ticket body is the request, which Jira
owns; the TCW Item field already says which item it belongs to.

**Removed** (the ticket's "sync, retry queue, link/unlink, claims, strict mode"):

| What | Where today |
| --- | --- |
| Sync after lifecycle moves, owed records, progress comments | `tcw/tracker/sync.py`, `tcw/tracker/progress.py`, `_deliver_after` (`tcw/work/cli.py:1462`) |
| Bindings, import, claims, release | `tcw/tracker/intake.py`, `tcw/tracker/claim.py`, `tcw/tracker/ownership.py`, `tcw/tracker/create.py` |
| Strict mode, tickets owed to new items | `tcw/work/cli.py:428-738`, `779`, and the checks at `cli.py:808`, `1005`, `1639`, `2696` and `4575`; `tcw/serve/__init__.py:216-288` |
| `tcw work tracker list/show/import/create/link/claim/release/unlink/sync` | `tcw/work/cli.py:4664-4934`, with handlers at `2760-4087` |
| `work.tracker` parsing and inheritance | `tcw/store/base.py:1255-2011`; `tcw/store/fs.py:7365-7440` |
| `tracker.yaml` reading on the board | `tcw/store/base.py:469`; `tcw/store/fs.py:5340-5390` |
| The validate hook | `tcw/validate.py:372-384` |
| Suggestions naming `tracker` | `tcw/cli_suggest.py:4-12`, `41` |
| Tests | the 28 `tests/test_tracker_*.py` files, except the transport tests in `test_tracker_client.py`, which move with the client |
| Package | `tcw/tracker/` disappears; its `__init__.py` note that `jira.py` is the single home of Jira HTTP work (`tcw/tracker/__init__.py:9-11`) carries over to `tcw/work/jira/client.py` |

**Order with TCW-70.** TCW-70 removes the 2.x work store (`tcw/store/base.py`
`WorkStore`, `tcw/store/fs.py` `FsWorkStore`), and the tracker modules import from it
(`tcw/tracker/intake.py:27-28`). So they cannot outlive it. TCW-70's spec
therefore deletes the whole `tcw/tracker/` package except its HTTP client, the
`tracker` commands and their tests. It moves `jira.py` unchanged to
`tcw/work/jira/client.py`, `tests/tracker_fake.py` to `tests/work/jira/fake.py`,
and the transport tests to `tests/work/jira/test_client.py`.

**[Decision]**

- The removal list above is whichever of the two slices lands it. TCW-70 removes
  every command built on the 2.x store, `tracker` included (epic decision 2), so in
  practice it lands there. Whatever TCW-70 has deleted counts as done, and
  criterion 21 checks that none of it remains.
- The client is kept by content, not by path. `jira.py` imports nothing from
  TCW (`jira.py:27-37`), so it can outlive the store, and TCW-70's spec moves it
  as this slice asked. This slice starts from the moved files and makes the
  changes listed above. If they are missing when this slice starts, it restores
  them from git history at the commit before the deletion, so that
  `git log --follow` still shows where they came from.

### 15. Testing without the real Jira

#### 15.1 A stateful fake Jira (`tests/work/jira/fake.py`)

This extends the approach of `tests/tracker_fake.py`, which holds tickets and a
workflow and is installed in place of `_request` (`tests/tracker_fake.py:149-156`), so
no socket is opened. It answers every endpoint the client calls:

- create, edit, read, comments, links, transitions;
- project, statuses, create metadata, link types, users;
- workflow definitions, with a switch that makes them answer 403;
- searches, paginated.

It can be told to:

- refuse a transition that carries a comment;
- require a screen field on a transition;
- drop a connection after applying a write.

**Searches.** The fake evaluates JQL through a small parser for **exactly** the clause
shapes `jql.py` emits: `=`, `~`, `IN`, `NOT IN`, `IS EMPTY`, `IS NOT EMPTY`, `AND`,
`OR`, parentheses and `ORDER BY created`. A test builds every query `jql.py` can
produce and asserts the fake parses each one, so the two cannot drift apart silently.
A user's `inbox-query` is not parsed: the fake's tests use `inbox-query` values made
only of those shapes.

#### 15.2 Recorded responses (`tests/work/jira/recorded/`)

- JSON bodies are captured once from a real Jira Cloud site, for each endpoint the
  client calls, plus the error bodies.
- Account IDs, email addresses, display names and the site are replaced with fixed
  values. A test fails if any recorded file contains `@`, or the real site's host.
- A *shape test* asserts that, for each endpoint, the fake's answer has every key, at
  the same nesting, that the backend reads from the recorded answer. The fake can
  therefore not invent a shape Jira does not send.

#### 15.3 Transport tests

The transport tests in `tests/test_tracker_client.py` move with the client. That
includes the test that a server which never answers times out
(`test_tracker_client.py:454`) and the test that every operation passes a timeout
(`:285`).

#### 15.3a The shared backend contract tests

TCW-70's draft runs one set of backend contract tests over its in-memory and
filesystem backends, and leaves room for a third. `JiraBackend` over the fake is that
third. Every rule the contract states for all backends then holds for Jira too, and
the tests above cover only what is Jira's own.

#### 15.4 One scenario, two targets, and the live check

One scripted scenario, `tests/work/jira/scenario.py`, drives the backend through:

1. `new` with a request, a priority and a tag;
2. `advance` through every enabled stage to qa;
3. a qa rejection back to implement, with a reason;
4. a qa acceptance;
5. reopening, and a discard;
6. `edit` of each property, including a blocker link added and removed;
7. `rename`;
8. a child under an epic, and a refused child under a sub-task;
9. `tickets adopt` of a ticket written without TCW fields;
10. `validate --remote`.

At each step it asserts what the ticket shows. The scenario runs:

- in CI, against the fake;
- by hand, against a real scratch Jira project, when `TCW_JIRA_LIVE=1` and its
  credentials are set. Otherwise that run is skipped.

**[Decision] The live run is part of acceptance** (criterion 23). It runs once during
implement, with its output kept in the implement round, and again at review. It
settles what only a real site can, and the recorded responses are captured during
that run:

- the direction of `Blocks` links;
- whether a comment is accepted on a transition with no screen;
- whether a cross-project parent is accepted;
- whether a non-administrator can read the workflow definition;
- what `expand=transitions.fields` shows for a transition with no screen, and for
  one whose screen holds only a comment, which the choice rule (Design 5 step 2)
  depends on.

**It must not run against the TCW Jira project:** TCW's own workflow is not migrated
to 3.0 statuses until TCW-76, and throwaway tickets would clutter its board.

### 16. Git

No module in `tcw/work/jira/` imports `subprocess`, or calls `os.system` or
`os.popen`. Delegation's "no uncommitted changes" check is TCW-70's read-only helper.
TCW writes only:

- item folders and `item.yaml`;
- in `rename`, one folder move on disk.

It names every file it writes on stderr.

### 17. Release notes and the documented-command allowance

- **Entry files.** This slice adds `docs/changelogs/upcoming/<folder>.md` and
  `docs/release-notes/upcoming/<folder>.md`, named by this item's folder name, as
  `CLAUDE.md` requires. Each starts with its first `##` heading, with no text
  before it: only TCW-75's entry carries the 3.0.0 introduction (epic decision 15).
- **The allowance.** TCW-70 gives `tests/test_documented_cli_surface.py` a
  temporary list of removed commands and configuration keys that documents may
  still name, with a guard test that each entry is really gone (epic decision 6).
  Whatever this slice removes that TCW-70 did not (Design 14's removal list, if any
  of it is left) is added to that list in the same change, and the guard test then
  covers it. This slice never shortens the list: TCW-74 and TCW-75 do, as they
  rewrite the text, and TCW-76 requires it empty before 3.0.0 is cut.
- The new commands (`tickets list`, `tickets adopt`) and `validate --remote` are
  not documented here; guides are TCW-75's, and TCW-73's surface test covers the
  commands.

## Abstraction litmus test

| Operation | Verdict |
| --- | --- |
| create, read, list, update, set stage, comment, rename, lookup, read_request, read_comments, current_user | **Backend interface**, eleven operations (TCW-69 Design 5; epic decision 1). Jira implements each, as Design 3 to 6 and 10 describe. `lookup` is answered from folder names without the network, because the key in the name is authoritative. |
| `external_stages = {request, qa}`, `inbox_items = false` | **Backend facts,** declared. |
| `tickets list`, `tickets adopt` | **Jira-only commands**, outside the interface (TCW-69 Design 5.7). A filesystem project's inbox is items at the inbox stage, so it has nothing to adopt. |
| Delegation | **Per target backend.** TCW-70's `new --project` chooses by the target's backend; this slice supplies the Jira target. |
| `validate --remote` | **Jira-only checks.** The model's own checks (stage ahead of artifacts, references) are shared and only scheduled here. A filesystem project has no remote to check. |
| `Item.untracked` | **Model field** (TCW-69 Design 2.1; epic decision 16). Any store whose links can point outside TCW has such references; the filesystem backend leaves it empty. |

Nothing here relies on a filesystem trick. The one directory scan, `lookup`'s scan of
folder names, is a private detail of this backend, and the model never sees it.

## Harness compatibility

Everything this slice guarantees is in the `tcw` CLI: the backend, both `tickets`
commands, delegation, and `validate --remote`. It behaves the same under Claude and
Codex. Credentials come from environment variables, which both harnesses pass
through. Nothing depends on a hook, on injected context, or on a skill: the `setup`
skill's walkthrough (TCW-74) reads `validate --remote`'s report, and a Codex agent
running the same command gets the same report.

## Acceptance criteria

All criteria except 23 are pytest tests in `tests/work/jira/`, against the fake
(Design 15.1), unless they name another target. "Nothing written" means the fake
records no write request and the work path is unchanged.

1. **Config.**
   - A block with only `site`, `project`, `credentials` and `fields.{project,item}`
     parses, with issue type `Task`, timeout 15 and the default priority names.
   - Each of these is an error naming the key:
     - an unknown key at any level;
     - a missing required key;
     - a `site` with a path;
     - a lowercase `project`;
     - `timeout: 0`;
     - a credential name with a `-`.
   - No parse result contains the value of a credential variable, and the problem
     for a malformed credential name (for example `abc def/123`) names the key and
     does not contain the value.
2. **Folder names and `item.yaml`.**
   - Offline `validate` reports an error for each of: `item.yaml` with a second key, a
     URL on another site, a URL whose key differs from the folder's, two folders with
     the key `TCW-5`, and a folder `tcw-5-x`.
   - It warns about a `request/` folder in an item.
   - It makes no network request; a test asserts that `_request` is never called.
3. **`lookup`.**
   - `lookup("tcw-67")` finds `TCW-67-x`.
   - `lookup("TCW-6")` with only `TCW-67-x` present is `None`.
   - `lookup("2026-10-01-x")` is `None`.
   - Two `TCW-5-…` folders give exit 1.
   - None of these makes a request.
4. **`read`.** For a fake ticket with every property set:
   - the `Item` has the mapped values;
   - a status mapped to no enabled stage reads as stage `None`;
   - a label outside the registry is absent from `tags`;
   - a priority name outside the mapping reads as `None`;
   - a blocker ticket with no TCW Item appears as its key in `untracked`, and
     not in `blocked_by`;
   - a parent ticket in another project with TCW Item `web/WEB-3-x` reads as that
     slug.

   A 404 is exit 4. A ticket answered under a different key is returned, with a
   warning naming both keys.
5. **`create`.**
   - A new item's ticket has TCW Project = id and TCW Item = `id/KEY-words`. Its folder
     contains only `item.yaml`, and its status is the request status.
   - When the workflow offers no transition to the request status, the result is
     exit 3 carrying the key. TCW Item is empty and no folder exists.
   - With a project whose create metadata has no Priority, `--priority high` is
     refused before any write, and a `new` without it sends no priority.
6. **Children.**
   - A child of an Epic is created with the configured issue type.
   - A child of a Task is created with the type flagged `subtask`, whatever its name.
   - A child of a Sub-task is refused (exit 3) with nothing written.
   - Changing a Task's parent to another Task is refused (exit 3).
7. **`update`.**
   - One edit request carries title, priority, effort and tags. A pre-existing label
     outside the registry survives.
   - Adding a blocker creates one `Blocks` link with this ticket as the blocked one,
     and removing it deletes that link.
   - When the link request fails after the edit, the result is exit 1 naming the
     unchanged link. Re-running adds it once.
8. **Assignee.**
   - A value matching one assignable user sets that account.
   - No match is exit 4; two matches are exit 3, listing both.
   - An account ID is used directly.
9. **`set_stage`.**
   - With one transition to the target's status, the fake records exactly one
     transition request, which carries the note as a comment. The returned stage is
     the one read back.
   - With two transitions to that status, one with no screen and one whose screen
     shows a resolution field, the one with no screen is used.
   - With two transitions to that status that both ask for nothing but a comment,
     the result is `Refused`, the message lists both, and nothing is written. With
     none, the message lists every offered transition, and nothing is written.
   - With the fake refusing comments on transitions: the transition is retried
     without the comment, the comment is then posted, and the result is the target
     stage.
   - With the fake requiring a screen field: the result is `Refused`, carrying the
     fake's message, with the status unchanged.
   - With the connection dropped after the write landed, and the note not among the
     comments: `MovedWithoutNote`.
   - With the connection dropped before the write: `Unreachable` (exit 5).
10. **Through `advance` (TCW-69), Jira mode.**
    - A bare `advance` from qa is refused (exit 3).
    - `advance --to implement --reason r` from qa moves the ticket, and its newest
      comment contains `r`.
    - `advance --to completed --reason r` from qa moves it.
    - `advance --to inbox` is refused.
    - `discard --reason r` from a ticket in an unmapped status moves it, without
      force.
    - With review enabled and accepted, a move into completed checks only review's
      verdict.
    - `path <slug> request` and `path <slug> qa` are refused (exit 3), naming the
      backend, with and without `--handoff` (epic decision 18).
11. **`list`.**
    - The default excludes completed and discarded tickets, and includes a ticket in an
      unmapped status.
    - A ticket whose TCW Project is `tcw-web` is absent from project `tcw`'s list.
    - A ticket naming a folder that is not here is absent, and stderr names it.
    - With 250 matching tickets and pages of 100, all 250 are listed.
    - Listing 50 items whose parents and blockers are spread over 20 other tickets
      makes at most two search requests per page of results, and no per-item request.
12. **JQL.**
    - A status name containing `"` is escaped.
    - Every query `jql.py` can produce is parsed by the fake's evaluator.
    - Custom fields appear only as `cf[<id>]`.
13. **`tickets list`.**
    - It lists a Triage ticket with neither TCW field set, and one with TCW Project =
      this id.
    - It omits one with TCW Item set and one with TCW Project = another id, even when
      `inbox-query` selects them.
    - With `inbox-query` selecting a `To Do` ticket that has no TCW fields, that
      ticket is listed as well.
    - stdout has one ticket key per line and nothing else; `--json` gives the
      fields named in Design 7.1, with `description` as the ticket body's text and
      `null` for a ticket with none, from the same single search.
14. **`tickets adopt`.**
    - From the inbox status: TCW Project and TCW Item are set, the folder is created,
      the ticket moves to request, and stdout is the slug.
    - Each refusal in Design 7.2 step 2 gives exit 3 with nothing written.
    - A ticket whose TCW Item names this project's slug with no folder here is resumed:
      the folder is created with that exact name.
    - In filesystem mode, `tickets list` and `tickets adopt` exit 2.
15. **`rename`.**
    - It changes the words after the key and sets TCW Item to the new slug.
    - Asking to change the key is a usage error.
    - When the TCW Item edit fails, the folder keeps its old name.
16. **`comment`** posts one comment whose text reads back unchanged through
    `_document_text`, for text containing `[`, `]`, `*` and a blank line.
17. **Delegation.**
    - With the target's folder creatable: the ticket is in the target's Jira project
      with TCW Project = target id. TCW Item is set, the folder is in the target, the
      status is the target's request status, and stdout is the slug.
    - With uncommitted changes in the target's work store: the ticket stays at the
      target's inbox status with TCW Item empty, stdout is the key, and the exit code
      is 0.
    - With the target not on this machine and a connected-project `jira` block: the
      ticket is created from that block at the target's inbox status, TCW Item is
      empty, stdout is the key, and the exit code is 0.
    - With neither: exit 3, nothing written.
    - `--tag` with `--project` against a Jira target: exit 2.
18. **`validate --remote`**, against fakes set up for each case:
    - an error for a missing TCW Item field;
    - an error for a stage status missing from the project;
    - with the definition readable, a needed move with no candidate transition is
      an error; one with two candidates is decided by a sample ticket (an error when
      both ask for nothing but a comment, a pass when only one does), and is
      *unchecked* when there is no sample ticket;
    - with the definition refused (403), a needed move from a status with no sample
      ticket is *unchecked*, not passed, and a needed transition whose screen
      requires a field is an error;
    - an error for an item whose ticket's TCW Item names another slug;
    - an error for a ticket answered under a different key;
    - a warning for a ticket naming a missing folder;
    - exit 0 when only warnings remain;
    - exit 5 when the fake is unreachable;
    - every stdout line has the form `<severity>: <where>: <message>`, an unchecked
      move is a `warning` line starting `unchecked:`, and a clean project prints
      nothing on stdout;
    - no write request in any case.
19. **Offline stays offline.** Plain `tcw validate` in a Jira-mode project, with the
    credential variables unset, makes no request and exits 0 on a clean tree.
20. **Errors.** Each row of Design 10's table gives its exit code, through one
    operation each. A 429 makes exactly one request and no retry.
21. **2.x is gone.**
    - `tcw/tracker/` does not exist.
    - No file under `tcw/` contains `work.tracker`, `tracker_strict`, `tracker.yaml`,
      `tcw.tracker` or `TrackerConfig`.
    - `tcw work tracker --help` exits 2.
    - A config containing `work.tracker` is an error naming the migration guide
      (TCW-69 criterion 16 covers the message).
    - The six removed capability records and the `external-work-tracker` term are
      absent, and the three new records and `jira-work-backend` are present.
      `<item>/capabilities.yaml` declares them, and TCW-69's records gate passes for
      this item.
22. **No git.** A test asserts that no module in `tcw/work/jira/` imports
    `subprocess` or calls `os.system` or `os.popen`. A second test runs `create`,
    `rename` and `adopt` inside a temporary git repository, and asserts that
    `git rev-parse HEAD`, `git status --porcelain` and `git for-each-ref` show only the
    expected untracked files.
23. **Live check.** The scenario (Design 15.4) passes against a real scratch Jira
    Cloud project configured with one status per enabled stage. Its output is saved in
    the implement round, and the recorded responses in `tests/work/jira/recorded/` come
    from that run. It records an answer to each of these five questions:
    - the direction of `Blocks` links;
    - whether a comment is accepted on a transition with no screen;
    - whether a cross-project parent is accepted;
    - whether a non-administrator can read the workflow definition;
    - what `expand=transitions.fields` shows for a transition with no screen and
      for one whose screen holds only a comment.

    If a team-managed scratch project is available, the scenario passes there too
    (Notes, owner questions).
24. **Shape agreement.** For every endpoint, the shape test (Design 15.2) passes, and
    no recorded file contains `@` or the real site's host.
25. **The rest of the suite passes,** with the removed tests deleted rather than
    skipped. TCW-70's backend contract tests run against `JiraBackend` over the fake
    (Design 15.3a) and pass.
26. **The three reads.**
    - `read_request` gives the description's text, and `None` for a ticket with no
      description.
    - `read_comments(folder, 3)` over five comments gives the newest three, newest
      first, each with its author's account ID and a UTC `at`; with 150 comments
      and `limit=None`, all 150, across pages.
    - `current_user()` gives the fake's `myself` account ID.
      `list(Query(assignee=current_user()))` selects exactly the tickets assigned
      to that account, and `update` with that value as assignee sets it (the paths
      TCW-72's `--mine` and `--assign-me` take). A ticket assigned to that account
      reads with `Item.assignee == current_user()`. With the credential variables
      unset it is exit 1 naming them, and makes no request.
    - `ticket_link` of `TCW-5-x` gives `("Jira", "<site>/browse/TCW-5")` with no
      request; `user_name` of an account seen in that command's `read` makes no
      request; `assignable_users("ali")` returns the fake's matching users.
27. **Release notes and allowance.**
    - Both entry files exist and start with a `##` heading.
    - Every command or key this slice removes is either absent from all documents
      or listed in TCW-70's allowance, and the allowance's guard test passes.

### Coverage

| Design rule | Criteria |
| --- | --- |
| 1 Config | 1 |
| 2 Identity, folders, lookup | 2, 3, 15 |
| 3 Read, mapping, untracked references, the request and comments | 4, 11, 26 |
| 4 Create, update, comment, rename | 5, 6, 7, 8, 15, 16 |
| 5 Set stage | 9, 10 |
| 6 List, JQL | 11, 12 |
| 7 Tickets, display helpers | 13, 14, 26 |
| 8 Delegation | 17 |
| 9 Validation | 2, 18, 19 |
| 10 Errors, network, identity | 19, 20, 26 |
| 11 Hierarchy | 6, 23 |
| 12 Team-managed | 5 (no Priority), 6 (sub-task by flag), 23 |
| 13 Required screen fields | 9, 18 |
| 14 Kept and removed | 16, 21, 25 |
| 15 Testing | 12, 23, 24, 25 |
| 16 Git | 22 |
| 17 Release notes, allowance | 27 |

## Risks

- **The fake can be wrong about Jira.** Every test above would then pass against a
  Jira that behaves otherwise. Mitigations:
  - recorded real responses, with a test holding the fake to their shapes;
  - one scenario run against both the fake and a real project;
  - the five behaviors that only a real site can settle, named and recorded
    (criterion 23).
- **`Blocks` link direction is easy to invert.** Jira's issue-link JSON names the two
  sides in a way that is often misread, and an inverted link would silently swap
  blocker and blocked. The live scenario asserts the direction as Jira's own UI shows
  it.
- **The workflow definition may need administrator permission.** If so, most users get
  the sample-ticket check. On a new project with no tickets, that check leaves most
  moves *unchecked*. Each is reported as an `unchecked:` finding rather than passing,
  and the `setup` walkthrough (TCW-74) can create one sample ticket per status with
  the user's agreement.
- **A status renamed in Jira breaks the mapping silently** until the next
  `validate --remote`: items read as having no stage, and moves refuse. TCW matches
  statuses by name for portability across team-managed projects; the cost is this
  rename risk.
- **Multi-request operations can stop part way** (create, adopt, update, delegation).
  Each sequence is ordered so that every stopping point is a legal state, and each
  error names what was done. `adopt` can be resumed.
- **Concurrent adoption** is a known limit (Design 7.2). Two `new` runs on two branches
  cannot collide, because each ticket's key is unique.
- **Every read needs the network.** In Jira mode, `list`, `show` and `advance` fail
  with exit 5 when Jira is down. This is the ticket's deliberate trade: one owner per
  fact, and no copy to drift. TCW-77 handles the viewer's offline display.
- **Hand moves in Jira bypass gates.** This is by design. `validate --remote` reports
  stage ahead of artifacts after the fact.
- **Exact matching on text fields** relies on filtering after the search, so a very
  common project id makes `list` fetch extra tickets that it then drops. It is
  correct, and only slower.
- **Order with TCW-70.** TCW-70 deletes the tracker integration with the 2.x store
  and moves the client and fake (Design 14). If the move does not happen, this
  slice restores them from history, which is extra work but not a blocker.
  Criterion 21 holds whichever slice does the removal.
- **Size.** This is a large slice: about seven new modules, a fake Jira, a live
  check, and, unless TCW-70 has done it, the removal of roughly 20,000 lines
  including tests. The plan should order it as:
  1. client and config;
  2. backend;
  3. tickets and delegation;
  4. `validate --remote`;
  5. removal.

  Each step leaves the suite green. Splitting it into child items is the owner's call
  (Notes).

## Notes

- Reconciled with the epic's cross-slice decisions on 2026-10-01.
- **Decisions made in this spec, for the owner to confirm.** Each is marked
  **[Decision]** above:
  1. `work.jira` is not inherited from parent projects; that capability record is
     removed.
  2. `work.jira` gains `issue-type` (default `Task`) and `timeout` (default 15
     seconds).
  3. TCW Item holds the full slug, `project/folder`, the same value as `TCW_SLUG`
     (epic decision 11).
  4. Labels outside the tag registry are ignored, neither shown nor removed.
  5. Priority, effort and complexity can read as `None`.
  6. `create` and delegation check the route to the request status before setting
     TCW Item.
  7. An assignee value is tried as an account ID, then searched; no match is exit 4,
     several matches are exit 3.
  8. `set_stage` retries once without the comment when Jira refuses a transition
     carrying one.
  9. A lone candidate transition is used even when its screen has a required field,
     so that Jira's own message names the field (Design 5 step 2).
  10. The exact match on TCW Project happens after the search; `list` may make one
      extra batched request to turn keys into slugs.
  11. `inbox-query` widens the inbox by union, and the TCW-field filter still
      applies.
  12. `adopt` accepts only tickets at the inbox or request status, and resumes a
      half-finished adoption of the same item.
  13. Delegation's site and credential names always come from one file, and
      delegation sets only title, request and priority.
  14. Delegation into a target that is not on this machine, but has a `jira` block
      in the delegator's connected-project entry, creates the inbox ticket and
      exits 0 with the key; without such a block it is exit 3 (epic decision 4).
  15. `validate --remote` checks the configured issue type plus the types of
      existing items' tickets.
  16. When the workflow definition shows several candidates for one move,
      `validate --remote` samples a ticket to apply the choice rule, and reports the
      move as unchecked without one.
  17. No automatic retry on rate limiting.
  18. Cross-project parents are sent, and Jira's refusal is reported.
  19. Team-managed projects take the same code path as company-managed ones.
  20. Transition screen fields other than the comment are never filled.
  21. The version 2 `description` read is dropped in favour of version 3 plus
      `_document_text`.
  22. In Jira mode a person is always an account ID: `current_user()`,
      `Item.assignee` and `Comment.author`. Display names appear only on output,
      through `user_name`. `current_user()` never returns `None`.
  23. Three Jira-only display helpers beside `tickets list`: `ticket_link(folder)`
      (no network), `user_name(account_id)` and `assignable_users(query)`
      (Design 7.3), as TCW-77 asked.
  24. `tickets list --json` includes each ticket's description as text, as TCW-74
      asked.
  25. The 2.x removal list belongs to whichever of TCW-70 and TCW-71 lands it.
      The Jira client and fake are kept by content: moved by TCW-70, or restored
      from history here.
  26. The live check is part of acceptance and runs against a scratch project, not
      TCW's.
- **Settled by the epic's cross-slice decisions** (2026-10-01):
  - The three reads and the untracked references TCW-69's interface lacked: the
    interface has eleven operations, with `read_request`, `read_comments` and
    `current_user` (decision 1), and `Item.untracked` holds ticket keys (decision 16).
    Design 3.1, 3.2 and 10 implement them.
  - `Item.priority` may be `None`, and `Refused` may carry a ticket key (decision 16).
  - TCW-72's `me()` is replaced by `current_user()` (decision 17).
  - Several transitions into one status: the choice rule of Design 5 step 2
    (decision 5).
  - `tickets list` prints one key per line, with details through `--json`, and
    `validate --remote` prints findings only, with unchecked moves as findings
    (decision 10). This replaces the earlier `KEY<TAB>status<TAB>summary` output
    and the passed/failed/unchecked report.
  - The exception classes live in `tcw/errors.py` (decision 8).
  - Who removes the six tracker capability records: TCW-70 (decision 12); this
    slice only if TCW-70 leaves any.
  - `capabilities.yaml` lives at `<item>/capabilities.yaml`, including in TCW-76
    (decision 19).
  - A project declared but not on this machine reads as exit 5, and delegation into
    it is exit 3 (decision 4); see the reading in Design 8 step 1.
  - The documented-command allowance (decision 6) and the release-notes rule
    (decision 15): Design 17.
  - `skills/configure/` is TCW-75's, every other skill TCW-74's (decision 3).
- **Cross-slice findings the decisions do not settle.** Nothing has been posted to
  any ticket.
  - **TCW-70.**
    - Moving the client, its transport tests and the fake rather than deleting
      them is now in TCW-70's spec (its removal list); nothing more is needed.
    - **Delegation conditions.** In its spec, a delegated item lands at the
      target's inbox stage. In Jira mode it lands at request, because an inbox entry
      is a ticket with no item (ticket, and TCW-69's `inbox_items`). That difference
      is intended. Its "no uncommitted changes" check should be callable from
      Design 8.
    - **Open conflict.** Its `open_delegation_target` refuses (exit 3) a declared
      project not present on this machine before looking at any backend, citing
      decision 4. This slice's Design 8 step 1 creates an inbox ticket in that case
      when the delegator's connected-project entry has a `jira` block, because the
      ticket names that entry as a source of the target's settings. Either
      `open_delegation_target` reaches the Jira branch first when such a block
      exists, or the fallback is dropped from this slice. Listed under owner
      questions.
  - **TCW-72.** Its spec lists `issue-type` and `timeout` as shared and treats the
    whole connected-project `jira` block as shared, which agrees with Design 1 and
    8. Its request that a malformed credential name be reported by key without its
    value is met (Design 1, criterion 1). Its text that `Item.assignee` is a display
    name in Jira mode is now out of date: under TCW-69 Design 5.4 both are account
    IDs (Design 10). Nothing breaks, since it never compares them itself.
  - **TCW-73.** Keep the connected-project `jira` block through the
    `connected-projects` rename. Its request that this slice add the Jira-key branch
    to `resolve_item` is moot under decision 2's order (TCW-73 lands after this
    slice and builds `resolve_item`); this slice supplies `lookup`.
  - **TCW-74.** The `setup` walkthrough should cover *unchecked* moves and offer
    sample tickets. Its request that `tickets list --json` carry each ticket's
    description is met (Design 7.1).
  - **TCW-76.** Its spec now creates tickets for migrated items with REST writes,
    not `tcw work new`, because TCW creates tickets at the inbox status and moves
    them one transition at a time (its Design 4.1). Nothing more is needed.
  - **TCW-77.**
    - Its "stubbed Jira API" for viewer tests can be this slice's fake.
    - Its requested `ticket_link(folder)` and `assignable_users(query)` are provided
      (Design 7.3), with `user_name` for display. Its reason for not offering "me"
      in Jira mode (account ID against display names) no longer holds:
      `current_user()` and `Item.assignee` are both account IDs, so it may offer
      "me" there too.
    - It lists "update properties (filesystem mode)" and makes Jira properties
      read-only after creation, while the CLI's `edit` writes them in Jira mode. That
      is a viewer choice, not a contradiction, but its spec should say so.
- **Superseded 2.x backlog items.** For the owner to discard, or merge into this item:
  - `2026-09-15-check-the-tracker-s-workflow-against-the-statuses-mapping-in-tcw-validate`
    is absorbed into Design 9.2;
  - `2026-09-15-write-work-item-properties-to-mapped-tracker-fields` is absorbed into
    Design 3 and 4;
  - `2026-09-15-decide-claim-exclusivity-from-a-jira-project-s-workflow-definition`
    is moot, since there are no claims;
  - `2026-09-21-two-tracker-create-runs-at-once-can-make-two-tickets-for-one-item`,
    `2026-09-22-let-a-leftover-start-record-stop-refusing-a-legitimate-rework`,
    `2026-09-22-refuse-an-unconfigured-start-before-the-ticket-leaves-triage` and
    `2026-09-24-give-a-strict-tracker-claim-past-the-active-status-a-way-forward-instead-of-a-transition-list`
    are moot with sync, claims and strict mode gone.
- **Open questions only the owner can answer.**
  1. **Which Jira project the live check uses, and who prepares it.** `TCWTEST`
     ("TCW Bridge Test", created 2026-09-12 for the claim experiment) exists on
     proposit.atlassian.net. It needs one status per enabled stage, the transitions in
     Design 9.2, and the TCW Project and TCW Item fields: a Jira-administrator task.
     A team-managed scratch project as well? Recommended: reuse `TCWTEST`, and add a
     team-managed one only if creating it is cheap.
  2. **Delegation into a Jira-mode project that is not on this machine.** The
     ticket lets the target's Jira settings come from the delegator's
     connected-project entry, and decision 4 says delegation into a project not on
     this machine is exit 3; TCW-70's `open_delegation_target` applies decision 4
     before any backend is consulted. Recommended: keep the fallback (Design 8 step
     1), since without it the connected-project `jira` block has no use, and have
     TCW-70 dispatch a Jira-mode declaration with such a block to this slice's
     branch; decision 4's exit 3 then covers every case where TCW can create nothing.
  3. **Should this slice be split into child items** along the plan order in Risks?
     Recommended: one item, with the plan's five steps each leaving the suite green;
     split only if review rounds become too large to read.
- **Removed from the open questions.** Whether `current_user`, `read_request` and
  `read_comments` join the interface is settled (decision 1). Whether the TCW Jira
  project is company-managed or team-managed no longer matters to this slice, which
  takes one code path for both (Design 12); it is TCW-76's question.
- **Assumptions not grounded in this repository**, all to be confirmed by the live
  check:
  - the Jira Cloud endpoints and parameters named above (`search/jql` with
    `nextPageToken`, project create metadata, `POST /rest/api/3/workflows`,
    `expand=transitions.fields`, comment paging with `startAt`);
  - team-managed projects disallowing cross-project parents;
  - the 19-character bound on a key prefix, which assumes Jira's 10-character limit on
    project keys.
- **This item's `capabilities.yaml`** is written at implement, at
  `<item>/capabilities.yaml` (decision 19), from Capability changes, not at this
  stage.
- **Driving this item.** Implementation edits `tcw/`. For the whole epic the
  repository's 2.x board is edited by hand, per `CLAUDE.md`, and this slice's Jira
  ticket (TCW-71) is moved by hand when its item moves: In Progress, In Review,
  Done (epic decision 7). Read-only views of the board may use a released 2.8 `tcw`
  installed outside the checkout.
