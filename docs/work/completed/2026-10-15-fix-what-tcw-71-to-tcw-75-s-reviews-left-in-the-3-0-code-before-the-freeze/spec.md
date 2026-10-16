# Spec — Fix what TCW-71 to TCW-75's reviews left in the 3.0 code, before the freeze

A child of the TCW 3.0 epic (TCW-68). Every file, line and function named here
was read on `epic/tcw-3.0` at `e301bef5`.

## Capability changes

No capability is added or removed. `docs/work/dod.yaml` requires the ledger to
be reconciled, and several behavior changes make an existing record
incomplete, so the item declares them as changed:

```yaml
changed:
  - capabilities/reset-an-override       # C1: refuses a capability nested under the override
  - taxonomy/add-a-term                  # C2: --slug must be a slug
  - web/editing                          # V1: a save without a revision is refused; V2: a file path that leads outside the item folder is refused
  - cli/provision-declared-stores        # C4: never asks for a password or a host-key confirmation
  - cli/validate-a-project               # T5, T7: offline Jira-mode validation
```

Each record's `description.md` is edited on the work branch to say the new
behavior (plan, Task 8), except `cli/validate-a-project`: TCW-76's Task A10
owns that file, so this item hands its T5 and T7 wording to TCW-76 rather than
editing it. The other records were read and need no change: J1, T4 and C9
change messages and refusals no record describes, and P1 to P5 do not change
what `tcw config show` is described as doing.

## Problem

The verify reviews of TCW-71, 72, 73, 74, 77 and 75 left 32 findings sorted as
"needs a separate change". Most are in `tcw/`, which TCW-76's code freeze (its
Task B3) closes until the epic merges. The owner decided on 2026-10-15 that
every one goes in before the freeze, including those that change behavior.
Eleven change what a command or the viewer does (J1, P4, C1, C2, C4, C9, V1,
V2, T4, T5, T7); one (C7) is rejected; the rest change messages, comments,
documents or tests.

## Triage

Numbering: **J** = TCW-71's Jira backend entry, **P** = TCW-72's personal
configuration entry, **C** = TCW-73's CLI entry, **V** = TCW-74's and TCW-77's
entry, **T** = TCW-75's code-text entry, each in the order of
`initial-request.md`.

| # | Finding | Verdict | Evidence or reason |
| --- | --- | --- | --- |
| J1 | A dropped connection while posting a note invites a duplicate | **fix** (Design 1) | `_post_note`, `tcw/work/jira/backend.py:946`, turns every `TrackerError` into `MovedWithoutNote`, including a drop after Jira received the comment; `advance.py:285-289` then says "add it with `tcw work comment`" |
| J2 | Three shapes of Jira's answers were never recorded live | **fix** (Design 18) | `tests/work/jira/test_recorded_shapes.py:74-76` lists them as read but never seen: a second page of search results (`nextPageToken`, read by `search`, `tcw/work/jira/client.py:225-244`), a transition restricted to some statuses (`links.*.fromStatusReference`, read by `_definition`, `tcw/work/jira/remote.py:352`), and a transition screen that lists fields (`transitions.*.fields`, read by `transitions`, `client.py:260-269`). Owner's answer 1: record all three before the freeze |
| J3 | Recorded user objects keep `timeZone` and `locale` | **fix** | `tests/work/jira/capture.py` replaces only `accountId`, `displayName`, `emailAddress` (`_PEOPLE`, line 33); six recorded files hold `"timeZone"` (`get-issue-key-200.json`, `get-issue-key-comment-200.json`, `get-myself-200.json`, `get-user-200.json`, `post-issue-key-comment-201.json`, `post-search-jql-200.json`), and `get-myself-200.json` and `get-user-200.json` hold `"locale"` |
| P1 | A YAML key that is itself a list crashes every command | **fix** | `_no_dup_keys`, `tcw/store/yaml_source.py:34-41`: `key in mapping` raises `TypeError` for an unhashable key |
| P2 | Two layers writing the same empty mapping blame the lower one | **fix** | `_merge`, `tcw/config.py:469-473`: with `value == {}` and `lower == {}` the origin is never restamped |
| P3 | Only the first bad Jira credential key is reported | **fix** | `_credentials`, `tcw/work/jira/config.py:146-155`, returns at the first bad name (the entry calls it `parse_jira_credentials`; that name does not exist) |
| P4 | `work new --stage inbox` in a Jira project reads piped input before its usage error | **fix** (Design 2) | `_new`, `tcw/work/cli.py:205` reads stdin; `creation_stage`, which refuses, runs at line 211 |
| P5 | `config show` writes a `!!binary` or `!!set` value wrongly | **fix** | `_scalar`, `tcw/config_cli.py:42-43`: `yaml.safe_dump` of `bytes` or `set` is several lines, and `_one_line` keeps only the tag line, so the value is lost |
| C1 | `capabilities reset` deletes local capabilities nested in the override folder | **fix** (Design 3) | `reset`, `tcw/store/fs.py:2475-2490`, calls `_rm(ov[0])` with no nested check; `remove` (line 2422-2428) has one |
| C2 | `--slug` is not checked | **fix** (Design 4) | `FsTaxonomyStore.add`, `tcw/store/fs.py:1742`, passes `--slug` through `_safe_store_id`, which allows spaces and capitals |
| C3 | The scan for git commands that change state is incomplete | **fix** | `tests/work/test_git_write_scan.py`: `WRITERS` lacks the eight verbs; `_verb` skips `-c` but reads its value as the verb; `ALLOWED` is keyed on the class; no check of `--no-optional-locks` |
| C4 | `tcw provision` can still ask for a password | **fix** (Design 5) | `FsStoreProvisioner._run`, `tcw/store/fs.py:3421`, closes stdin only; git and ssh prompt on the terminal |
| C5 | The implement-stage instructions name code that no longer exists | **already fixed** | TCW-75 Task 4 (`36da5873`) rewrote `docs/lifecycle/implementation.md`: it no longer names `descendant_nodes` or `--include-descendants`, and the two names it keeps exist (`find_project_root`, `tcw/store/fs.py:259`; `descendant_projects`, line 488) |
| C6 | `tests/test_upstream_projects.py` runs whatever `tcw` is first on the search path | **fix**, widened | The same `["tcw", …]` call is in eight more test files and `tests/fixtures/prompt_fallback/capture.py`; fixed once in `tests/conftest.py` (Design 6) |
| C7 | `list` and `rm` disagree about a sub-folder with no `meta.yaml` | **rejected** (Design 7) | The premise is false: TCW itself makes such folders. `FsTaxonomyStore.add(..., slug='billing/bulk')` creates `billing/` with no `meta.yaml`, the viewer does the same (`tests/serve/test_records.py:87`), and TCW-73 deliberately treats such a folder as a term (`tests/test_taxonomy_rm_gaps.py:178-210`, its Design 8.2). The listing stays as it is |
| C8 | The retired-key message names a bare `tcw-config.yaml` | **fix** | `refuse_retired_config`, `tcw/store/fs.py:291`, prints `SENTINEL` alone |
| C9 | `tcw work list` does not notice a child project's retired key | **fix**, narrowed (Design 8) | `open_backend`, `tcw/work/open.py:63`, opens the registry without `require_valid()`, which `taxonomy`, `projects`, `provision` and `validate` all call |
| V1 | Taxonomy and capability edits skip the stale check when no revision is sent | **fix** (Design 9) | `update_term` and the capability update, `tcw/serve/records.py:112` and `:188`, read `revision` with `required=False` |
| V2 | A symbolic link inside the work path lets a file save write outside the project | **fix** (Design 10) | `file_path`, `tcw/serve/files.py:101-118`, builds the path and never resolves it; `write_checked` makes the parent and writes there |
| V3 | `_ANCHOR_CACHE` lives for the whole server process; its comment says one command | **fix** (comment) | `tcw/store/project.py:58-61`. Scoping the cache would change behavior for no observed gain; the comment is corrected to say what is true |
| V4 | The stage-name scan misreads some TypeScript | **fix** | `tests/serve/test_no_stage_names.py`: template `${…}` bodies, unquoted object keys, member access, and a regex after a keyword |
| V5 | `Conflict` nests a `<div>` inside a `<p>` | **fix** | `web/client/src/ui/content-views.tsx:399-417`: `Callout.Text` is a `<p>` and holds `Text as="p"` and a `Flex` |
| V6 | Commands wrapped across a line inside backticks are never checked | **fix** (Design 11) | `BACKTICKED`, `tests/test_documented_cli_surface.py:84`, forbids a newline in a span |
| V7 | `tcw work advance` leaves spec and plan with no document written | **fix: documentation only** (Design 12) | No built-in gate is added. Settled by owner's answer 2 |
| V8 | Unattended runs have no rule for an item at request | **fix** (Design 13) | `tcw/work/procedures/unattended-work.md`'s table has no request row. Settled by owner's answer 3 |
| T1 | Error messages name removed keys | **fix** | `tcw/work/generate.py:180` and `:184` say `work.lifecycle.output-cap` and `work.lifecycle.timeout`; the keys are `work.hooks.*` (`tcw/work/config.py:44`) |
| T2 | A doubled quote in a refusal | **fix** | `uncommitted_changes`, `tcw/work/open.py:107-110`, prints `'child''s work store` |
| T3 | Four out-of-date texts: `hooks.py` on `tcw serve`; `run_provision` "the only command that reaches the network"; `store/base.py` "remote adapters … unbuilt"; `skills/README.md:85` "TCW-75 rewrites this skill" | **fix** (all four) | Each read at the cited line; the viewer runs request `post` hooks on adopt (`tcw/serve/work.py:529-537`); the Jira backend reaches the network |
| T4 | A missing Jira site is reported as "the tracker has no such resource" | **fix** (Design 14) | `_for_status`, `tcw/work/jira/client.py:487-488`, maps every 404 to `TrackerNotFound`, which `_jira()` turns into "not found" (exit 4). An unreachable host is already "Jira could not be reached" (exit 5, `client.py:170-177`), so only the 404 case is fixed |
| T5 | Offline `tcw validate` in Jira mode skips the item-folder checks | **fix** (Design 15) | `_work_findings`, `tcw/validate.py:556-560`, returns before any item folder's `capabilities.yaml` is read |
| T6 | The shared vocabulary scan reads one line at a time | **fix** (Design 16) | `scan`, `tests/doc_vocabulary.py:61-68` |
| T7 | Offline Jira validation reports `qa/` rounds it says are ignored | **fix** (Design 17) | `round_findings`, `tcw/validate.py:597-624`, reads every enabled verdict stage, including those in `layout.external` |

**Counts: 30 fix, 1 already fixed (C5), 1 rejected (C7).** J2 is the only one that needs the
owner's hands first (the "Owner's TCWTEST checklist" below), so it is done
last and the freeze waits for it.

The two items the CLI entry lists as "already assigned elsewhere" are done:
`tcw serve` prints only the URL, flushed (`tcw/serve/server.py:400`), and the
`review` and `qa` built-in prompts exist (`tcw/work/prompts/`).

## Design

Each behavior change below passes the abstraction litmus test
(`docs/lifecycle/abstraction.md`): _could a non-filesystem store implement
this operation, even if less elegantly?_ The answer is given with each.

### 1. A note that may have been posted (J1)

When posting a note separately after a move (`_post_note`) fails with
`TrackerUnavailable` (the connection failed, so Jira may have received it),
TCW reads the ticket's newest `NOTE_WINDOW` comments, as `_after_drop` already
does for a move:

- the note is among them: success, nothing is reported;
- it is not: `MovedWithoutNote` as today ("posting the note failed");
- they cannot be read: `MovedWithoutNote` saying the note **may** have been
  posted, and to read the comments with `tcw work show <slug>` before adding
  it.

Every other `TrackerError` (a refusal) keeps today's message. In
`advance.py`, the suffix becomes "if it is missing, add it with
`tcw work comment`", which is right for all three. Litmus: Jira-adapter
private; the operation "move with a note" is unchanged.

### 2. Usage errors before piped input (P4)

`_new` opens the backend and calls `creation_stage` before
`read_piped_stdin`, so `--stage inbox` in a Jira project is refused at once.
`open_backend` reads only local configuration (the `JiraBackend` constructor
makes no request), so nothing else moves earlier. Litmus: no operation changes.

### 3. `reset` refuses a nested capability (C1)

`reset` refuses, as `remove` does, when any folder below the override folder
holds a `meta.yaml`, exit 3. A folder nested under an override may itself be
an override of a nested inherited capability, which `rm` refuses and only
`reset` drops, so the message names both ways out: `cannot reset '<id>':
nested under its override: <paths> (delete a local capability with
`tcw capabilities rm` and drop an override with `tcw capabilities reset`
first)`. The search for nested folders is factored into one helper both use;
`remove` keeps its own message. Litmus: "an entry with children cannot be
deleted as a leaf" holds for any tree store.

### 4. `--slug` must be a slug (C2)

A slug given to `taxonomy add` (`--slug`, and `slug` in the viewer's create
request, which reaches the same `add`) must be lowercase letters and digits
in words joined by single hyphens, the form `slugify` produces: it must equal
`slugify(slug)`. Otherwise a usage error, exit 2. A `/` is refused too;
nesting is `--parent`'s job. The predicate lives beside `slugify` in
`tcw/store/base.py`; the check is in `FsTaxonomyStore.add`, so the viewer
answers 400. Existing terms are untouched. Litmus: a naming rule any store
can enforce.

The store's message names no command-line flag, because the viewer returns it
in its 400 answer: `'A B' is not a slug: use lowercase letters, digits and
single hyphens`. The CLI's `taxonomy add` prefixes `--slug ` when it reports
it. The new check runs after `_safe_store_id`, so a slug that tries to leave
the store (`../evil`) still gets `invalid slug`, as
`tests/test_store_editor.py:730` expects. Two existing tests change:
`tests/serve/test_records.py:87` adds a nested term with `slug="admin/adapter"`
and becomes the `parent=` form.

### 5. `tcw provision` never prompts (C4)

`FsStoreProvisioner._run` passes git an environment built as
`{**os.environ, ...}` with `GIT_TERMINAL_PROMPT=0`, which stops git's own
prompt for HTTPS credentials (a credential helper still answers), and
`GCM_INTERACTIVE=never`, which stops Git Credential Manager opening its own
prompt or window. It removes `GIT_ASKPASS` and `SSH_ASKPASS` from that
environment, since either names a program that asks the user. For ssh it also
sets
`GIT_SSH_COMMAND="ssh -o BatchMode=yes"`, but only when the environment holds
neither `GIT_SSH_COMMAND` nor `GIT_SSH` and `git config --get core.sshCommand`
prints nothing, so a user's own ssh setting is never replaced. With
`BatchMode`, ssh fails instead of asking for a passphrase or a host-key
confirmation; the existing message (`git clone failed: <git's reason>`) then
names it. Litmus: provisioning is filesystem-adapter private.

### 6. Tests run this interpreter's `tcw` (C6)

`tests/conftest.py` puts the folder holding `sys.executable` first on `PATH`
when that folder has a `tcw` script, so every `subprocess.run(["tcw", …])` in
the suite runs the `tcw` of the interpreter under test. One change instead of
nine files.

### 7. A folder with no `meta.yaml` stays a term (C7, rejected)

Rejected, by the orchestrator's decision after the plan review, which
offered this as its smaller option. The finding assumed only a hand-made
folder can lack `meta.yaml`, but TCW makes them itself: `taxonomy add` with a
nested `slug` creates each missing parent folder with no `meta.yaml`, the
viewer's create route does the same (`tests/serve/test_records.py:87`), and
TCW-73 deliberately lists such a folder as a term
(`tests/test_taxonomy_rm_gaps.py:178-210`, its Design 8.2). Counting only
folders with a `meta.yaml` would hide terms TCW made. `_local_slugs` and
`get_local` keep their current behavior and nothing changes.

### 8. Work commands that open the backend check the project graph (C9)

`open_backend` calls `require_valid()` on the registry it already opens, for
the project the command acts on (`personal=True`), so a child's retired key
refuses `work list`, and every other work command that calls `open_backend`,
exactly as it refuses `taxonomy list`. Not every work command does:
`work new --project` hands the item to another project through `delegate`
and is not covered. Another project's backend (`personal=False`) is not checked,
so one project's broken child does not stop reading it from elsewhere.
Litmus: registry validation is store-agnostic.

### 9. Record edits in the viewer need a revision (V1)

`PATCH /api/taxonomy/<ref>` and `PATCH /api/capabilities/<ref>` require
`revision` (a string, the `coreRevision` last read); without it, 400
`revision is required`. The client always sends it (`app.tsx:736`). Litmus:
optimistic concurrency is store-agnostic.

### 10. Viewer file paths stay in the item folder (V2)

`file_path` resolves the path it builds and refuses, with the same 404
("is not one of this item's files"), one that resolves outside the item
folder's resolved path. It covers reads and writes. The declaration routes,
`get_declaration` and `put_declaration` in `tcw/serve/files.py`, do not go
through `file_path`: they call `layout.capabilities_file` directly, and a GET
follows a `capabilities.yaml` that is a link. They get the same check, through
one shared helper, and the same 404. A work path that is itself a link is
unaffected, because both sides resolve.
Editing outside the viewer is the user's own business and is not changed.
Litmus: the viewer's file routes exist only where the layout keeps files.

### 11. Wrapped commands in backticks (V6)

The scan finds code spans over a block of joined lines instead of one line:
a span may cross a single line break, each line break inside it reads as a
space, and spans are paired left to right as Markdown pairs them. A block is a
run of lines joined together, and it ends at a blank line, a fenced code
block's fence, and before any line that starts a table row (`|`), a list item
(`-`, `*`, `+` or a number followed by `.` or `)`) or a heading (`#`). So an
unpaired backtick in one table row, list item or heading can never pair with
one in the next. The original reason for the one-line rule (an unpaired
backtick reuniting `tcw` and a verb from different sentences) cannot recur
across those boundaries. Commands it newly finds must be valid or reworded.

### 12. Leaving a stage without its document (V7)

No built-in gate is added. `spec` and `plan` are optional stages, a project
already adds such a check as a `pre` hook (TCW's own does, with
`scripts/require_artifact.py`), and a built-in one would add a refusal every
project must override when it decides the document is not needed. The work
guide's "Built-in gates" says that no gate checks a stage's document and how
to add one. Settled: the owner chose documentation only (answer 2).

### 13. Unattended runs at request (V8)

A row in `unattended-work.md`'s table: at request, do not ask the advisors in
the requester's place, since what the requester wants is not theirs to know.
Write the request from the evidence available, marking each assumption, as
the request prompt says for "There is no user to ask"; where Jira keeps the
request, post the questions with `tcw work comment <slug>` instead and leave
the text alone; then continue. `skills/extras-autonomous-work/SKILL.md` gets
the same rule if it lists stages itself. Settled: the owner chose this rule
(answer 3).

### 14. A missing Jira site (T4)

A 404 from an endpoint every Jira Cloud site has (`/rest/api/3/search/jql`,
`/rest/api/3/myself`, `/rest/api/3/issueLinkType`) cannot mean a missing
ticket. The client raises a new `TrackerSiteMissing` for it, which `_jira()`
turns into a backend error, exit 1: `Jira at <site> has no <path>; check that
work.jira.site names your Jira site`. A 404 on any other path is unchanged.
Litmus: Jira-adapter private.

### 15. Offline Jira validation reads each item's declaration (T5)

Offline, in Jira mode, `tcw validate` parses each item folder's
`capabilities.yaml` and reports one that cannot be read or is malformed, as
an error naming the file, with `parse_declarations` (the same message as
filesystem mode). The records themselves are not checked offline: that check
skips finished items, and the stage that says an item is finished is kept in
Jira. References, the stage-ahead warnings and the records check stay under
`--remote`. `--remote` then skips a declaration that does not parse, so a
malformed file is reported once. Unlike filesystem mode, which reads no
declaration of a finished item, the parse check covers every folder; a
malformed file is wrong whatever the stage. Litmus: the declaration is part
of the item folder in both backends, read through the layout.

### 16. The vocabulary scan reads paragraphs (T6)

`scan` matches each block of lines joined with single spaces, then maps each
hit back to the line where it starts, with its start column in that line and
its end clamped to that line, so `Hit` and every caller
(`test_shipped_text.py`'s `_allowed_at`) keep working. A block ends where
Design 11's does: at a blank line, a fence, and before a line that starts a
table row, a list item or a heading.

### 17. External stages are not round-checked (T7)

`round_findings` skips any stage in `layout.external`, as `completion_gate`
already does. A `qa/round-1.md` in Jira mode then gets only "Jira keeps the
qa record, so this folder is ignored". The Jira guide already says offline
validation checks "the latest `review` round".

### 18. Recording the three unseen Jira shapes (J2)

The owner chose (answer 1) to record, from `TCWTEST` and before the freeze,
the three answers TCW reads but has never seen from a real site, then check
the fake against them and fix the code where they differ. Litmus: everything
here is Jira-adapter private; no operation changes unless a recording shows
the adapter misreads Jira, and then only inside the adapter.

**What `TCWTEST` is today** (read on 2026-10-15 with REST GET requests only):
project id 10003, "TCW Bridge Test", company-managed. Workflow scheme 10040,
used by `TCWTEST` alone, maps Task, Sub-task and Epic to the workflow
`TCWTEST: TCW lifecycle workflow (Task, Sub-task)`
(`19ccd58a-6ea1-49ff-b707-e0288d3495d7`); Story and Bug keep the simplified
workflow. That workflow has the nine statuses (`Won't Do` is status 10041,
`To Do` 10012) and ten transitions: `Create` (initial) and one global
transition into each status, ids 11 to 91, named after the status. Only the
one into `Planning` (41) has a screen, 10049 `TCWTEST: Planning transition
screen`, which lists no field. The project holds 85 tickets (Task 69, Epic 9,
Sub-task 7), none named like a probe. The scenario's account is a site
administrator and may create tickets, but does **not** hold the project
permission to delete them (`mypermissions`: `DELETE_ISSUES` false,
`ADMINISTER_PROJECTS` false).

**The restricted transition, and why it breaks nothing.** The owner adds one
new transition, `J2 probe: reopen`, from `Won't Do` only to `To Do`, with a
new screen listing the `Labels` field (not required in `TCWTEST`; the
recorded create metadata says `required: false`). No existing transition or
screen changes. This choice is safe for every recorded test:

- `validate --remote` checks only the moves TCW needs (`needed_moves`,
  `remote.py:307-322`): each stage to the next, the last to `completed`, a
  verdict stage back to where it rejects to, and each stage to `discarded`.
  None starts at `discarded` (`Won't Do`), so the new transition is never a
  candidate and no sample ticket is read for it.
- Every move into `To Do` still finds the global `To Do` transition (21).
  Where two are offered, `choose_transition` (`tcw/work/jira/backend.py:1028`)
  takes the one whose screen asks for nothing but a comment, which is 21.
- The live scenario (`tests/work/jira/scenario.py`) reads transitions only for
  tickets at `To Do`, `In Review` or `Planning` (probe question 2); on the
  ticket it discards it tries only the transition id `999999`, to record a
  refusal.
- Screen 10049 and the move into `Planning`, which the fake copies
  (`tests/work/jira/fake.py:100`), are untouched.

The transition and its screen stay in `TCWTEST` afterwards, as part of the
fixture, so a later capture can record the same shapes again.

**The paging tickets.** The owner approved creating just over 100 throwaway
tickets in `TCWTEST`. Exactly 101 are created, type `Task`, with the
summaries `J2 paging probe 001` through `J2 paging probe 101`, no description
and no other field set. `search` asks for pages of 100 (`PAGE`,
`client.py:39`), and Jira may answer fewer per page when fields are named, so
101 matching tickets always need at least two pages. No other text is written
to Jira: the only other write is moving `J2 paging probe 101` to `Won't Do`
through the global transition 91, with no comment.

**The live test.** A new `tests/work/jira/test_jira_live_shapes.py` holds one
test, gated as the live scenario is (`test_jira_scenario.py:51-55`: a
`skipif` on `TCW_JIRA_LIVE=1` and both credential variables) and in addition
on `TCW_JIRA_J2_PROBE=1` and `TCW_JIRA_CAPTURE` naming a folder. The extra
variable is needed because `TCW_JIRA_LIVE=1` alone runs the live scenario,
and a scenario run must never create 101 tickets. In every normal run,
including CI, the test is collected and skipped. It writes a scratch project
with the live scenario's `LIVE` configuration, opens its backend, installs
the `Recorder`, and then:

1. **Creates only what is missing.** It first reads `j2-keys.json` in the
   capture folder, where every key it creates is written as soon as Jira
   answers, and then searches for tickets whose summary is exactly
   `J2 paging probe NNN`. It creates only the numbers found in neither, so a
   re-run, even one soon enough that search has not yet caught up with the
   last run's tickets, never exceeds the 101 the owner approved.
2. **Records the pages as Jira sent them.** It waits (at most 120 seconds, as
   the scenario waits for search lag) until a search finds all 101. Then,
   separately from `JiraClient`, it walks the endpoint itself: a loop that
   posts to `/rest/api/3/search/jql` with the JQL
   `project = TCWTEST AND summary ~ "\"J2 paging probe\""` and the fields
   `tcw work list` reads (`read_fields`), records each request and answer, and
   follows `nextPageToken` until an answer has none. The first answer is
   recorded under the first-page name and the second request and its answer
   under the next-page name. The test asserts that the second request carried
   the `nextPageToken` the first answer gave, and that the pages together hold
   every one of the 101 keys exactly once. Recording the pages this way means
   that a mistake in `JiraClient.search`'s page walk cannot change what is
   recorded.
3. **Checks the client's page walk.** As its own step, it runs one real
   `JiraClient.search` with the same JQL and fields, and asserts it returns
   every one of the 101 keys exactly once. That assertion is the live check
   of the page walk.
4. **Records the workflow.** It calls `client.workflows` for `TCWTEST` and
   `Task`, and asserts the answer holds a transition whose
   `links.*.fromStatusReference`, mapped through the answer's own `statuses`
   list to a status id, is 10041 (`Won't Do`) and whose target, mapped the
   same way, is 10012 (`To Do`). A status reference is not a status id, so
   the comparison never reads one as the other.
5. **Records the screen.** It moves `J2 paging probe 101` to `Won't Do`
   through transition 91, unless it is there already (a re-run finds it
   there), reads its transitions with `expand=transitions.fields`, and asserts
   `J2 probe: reopen` is offered with `labels` among its fields.
6. **Cleans up, whatever happened before.** Steps 2 to 5 run inside a `try`
   whose `finally` block does the clean-up and prints the remaining keys, so a
   failed assertion still cleans up. It deletes only a ticket whose project is
   `TCWTEST` and whose summary exactly matches `J2 paging probe NNN` (three
   digits), checked on the ticket itself just before the delete
   (`DELETE /rest/api/3/issue/<key>`). At the first refusal for lack of
   permission it stops trying and prints every remaining key and the JQL
   `project = TCWTEST AND summary ~ "\"J2 paging probe\""`, for the owner to
   bulk-delete. Today the account cannot delete, so this is the expected path
   unless the owner does the optional checklist step 4. `j2-keys.json` is
   kept, so the owner's list and a re-run both have it.

**Where the recordings go.** `Recorder` keeps one file per endpoint and
status, the answer with the most key paths (`capture.py:118-128`). The probe
tickets are plain, so their search answers have fewer key paths than the
recorded read of a full ticket and would be thrown away. `Recorder` therefore
gains a way to record calls under a named file that never merges with the
endpoint's shared one, and the test names four:
`post-search-jql-200-first-page.json` (an answer with `nextPageToken` and
`isLast: false`), `post-search-jql-200-next-page.json` (a request carrying
`nextPageToken`, and its answer), `post-workflows-200-directed.json`, and
`get-issue-key-transitions-200-screen-fields.json`. The capture folder is a
scratch folder; only those four files are copied into
`tests/work/jira/recorded/`, so no existing recording changes. J3's
replacement of `timeZone` and `locale` (Task 1) is in `Recorder.record`, so it
applies to these files too, and they must pass
`test_no_person_or_real_site_is_recorded` like every other.

**Comparing with the fake.** `test_recorded_shapes.py` gets a `READS` entry
for each new file: `nextPageToken` and `isLast` for the first page;
`nextPageToken` in the request and `issues.*.key` for the next page;
`workflows.*.transitions.*.type` and
`workflows.*.transitions.*.links.*.fromStatusReference` for the workflow;
`transitions.*.hasScreen` and each screen field's `required` for the
transitions (the field map is keyed by field id, so `has` gains a wildcard for
a mapping's values). The shape test's `world` gains a ticket at `Won't Do`, a
transition like `J2 probe: reopen` and more than 100 tickets for the search;
these go in the test's fixture, not the fake's default project, so no other
test's transitions change. The comment at lines 74-76 that calls these shapes
"never seen" is removed. Beyond key paths, the comparison also reads by eye
what key paths cannot show: whether `isLast` is present on a page that is not
the last, whether the token is opaque text, whether the restricted transition's
`type` is something other than `GLOBAL`, and whether a global transition still
has `links: []`.

**Fixing what differs.** Where Jira's answer differs from what the code
reads, `tcw/work/jira/client.py` (`search`, `transitions`) or
`tcw/work/jira/remote.py` (`_definition`) is fixed to read Jira's shape, the
fake (`tests/work/jira/fake.py`) is changed to answer in that shape, and a
test against the fake reproduces the recorded shape and fails before the fix.
The one difference that matters most: `search` stops when `isLast` is
absent (`client.py:243`), so if Jira leaves `isLast` off a page that is not
the last, `tcw work list` silently loses tickets past the first page; step 3's
assertion would catch it.

## Owner's TCWTEST checklist

For J2 (Design 18). Do these in Jira's administration screens on
https://proposit.atlassian.net, in project `TCWTEST` ("TCW Bridge Test"),
then tell the agent the list is done. The agent then confirms steps 1 to 3
with REST GET requests before it creates any ticket. Nothing else in this
item waits on this list; only J2 does, and the freeze waits for J2.

Do not change any existing transition, status, screen or scheme, and in
particular leave the `Planning` transition's screen
(`TCWTEST: Planning transition screen`) as it is. The live tests rely on all
of them.

1. **Create the screen.** Settings (the gear, top right) → **Work items**
   (called **Issues** on older sites) → **Screens** → **Add screen**. Name:
   `TCWTEST: J2 probe transition screen`. Description:
   `TCW pre-freeze clean-up, J2: a transition screen that lists a field`.
   Add the field **Labels** to it, and nothing else. Do not add the screen to
   any screen scheme.
   *Confirm:* the Screens list shows the new screen, and opening it shows
   Labels as its only field. (The agent confirms this with
   `/rest/api/3/screens/{id}/tabs/{tab}/fields`.)
2. **Add the restricted transition.** Project settings for `TCWTEST` →
   **Workflows** → edit `TCWTEST: TCW lifecycle workflow (Task, Sub-task)`.
   Add a transition:
   - **From:** `Won't Do` only. Do not choose "any status" and do not mark it
     global.
   - **To:** `To Do`.
   - **Name:** `J2 probe: reopen`.
   - **Screen:** `TCWTEST: J2 probe transition screen`.
   - Leave conditions, validators and post functions empty.

   Save, and publish the workflow if the editor asks; if Jira asks how to
   move existing tickets between statuses, keep every ticket in the status it
   has.
   *Confirm:* the workflow now lists eleven transitions: `Create`, the nine
   global ones, and `J2 probe: reopen`, which starts only from `Won't Do`.
3. **Check it on a ticket.** Open any Task whose status is `Won't Do` and open
   its status menu.
   *Confirm:* `J2 probe: reopen` is offered, and choosing it shows a screen
   with a Labels field. Press **Cancel**; do not complete the move. A Task at
   `To Do` does not offer it.
4. **Optional: let the account delete the probe tickets.** Today the account
   behind `TCW_JIRA_EMAIL` cannot delete tickets in `TCWTEST`. If you want the
   101 probe tickets deleted automatically, grant it **Delete work items**
   (called **Delete issues** on older sites): Project settings for `TCWTEST` →
   **Permissions**; if the permission scheme shown there is used by other
   projects, skip this step rather than widen it for them. Skipping is fine:
   the agent will then give you the keys and the search
   `project = TCWTEST AND summary ~ "\"J2 paging probe\""` to bulk-delete
   them yourself.
   *Confirm:* say whether you did it; the agent re-reads the permission with
   a GET request.
5. **Tell the agent the list is done.**
6. **After the clean-up, if you did step 4:** remove the **Delete work items**
   permission you granted, so the account goes back to what it could do
   before.

The 101 tickets themselves are created by the agent's live test, not by hand
(Design 18). **Creating 101 tickets may send notification emails** to anyone
watching `TCWTEST` or subscribed to its notification scheme; if that matters,
check the project's notification scheme before telling the agent to go.

## Acceptance criteria

Each is checked by a test, named in the plan, unless a command is given.

1. **J1.** With the fake dropping the connection after it receives the
   separate note: the note found among the newest comments gives exit 0 and
   one comment; not found gives exit 6 and a message saying posting failed;
   comments unreadable gives exit 6 and a message containing "may have been
   posted" and `tcw work show`. No path posts the note twice.
2. **J3.** Every `timeZone` in `tests/work/jira/recorded/` is `Etc/UTC` and
   every `locale` is `en_US`; `Recorder.record` writes those values for a
   body holding others.
3. **P1.** A `tcw-config.yaml`, and separately a `tcw-config.local.yaml`,
   holding `? [a]\n: 1` makes a command exit 1 with a message naming that file
   and no traceback.
4. **P2.** Project and local files both writing `completed: {}` under one key:
   `config show --origin` names the local file.
5. **P3.** With both `email-env` and `token-env` invalid, `validate` reports
   two problems, one per key.
6. **P4.** In a Jira project, `work new T --stage inbox` exits 2 without
   reading standard input.
7. **P5.** `config show` writes an unknown key's `!!binary` and `!!set` values
   on one line each, and each line reads back to the same value.
8. **C1.** `capabilities reset auth/login` with `auth/login/nested` local
   exits 3, names `auth/login/nested` and both `rm` and `reset`, and leaves
   both folders.
9. **C2.** `taxonomy add X --slug 'A B'` and `--slug a/b` exit 2, name
   `--slug`, and create nothing; `--slug memo` still works; the viewer's create
   route answers 400 with a message that names no flag; `--slug ../evil` still
   says `invalid slug`.
10. **C3.** The scan reads `["git", "-c", "a=b", "switch", "x"]` as `switch`,
    reports each of the eight added verbs, accepts `clone` and `checkout` only
    inside `FsStoreProvisioner._obtain`, and fails on a `status` call without
    `--no-optional-locks`.
11. **C4.** `_run` passes the rest of the environment through, with
    `GIT_TERMINAL_PROMPT=0` and `GCM_INTERACTIVE=never` and without
    `GIT_ASKPASS` or `SSH_ASKPASS`; it sets `GIT_SSH_COMMAND` with
    `BatchMode=yes` when nothing is configured, and leaves a set
    `GIT_SSH_COMMAND` (or a `core.sshCommand`) as it was.
12. **C6.** Under pytest, `shutil.which("tcw")` is in the folder of
    `sys.executable` whenever that folder has a `tcw`.
13. **C7 (rejected).** Nothing changes: `tests/test_taxonomy_rm_gaps.py`,
    which lists a folder with no `meta.yaml` as a term, still passes.
14. **C8.** Run from `p/docs`, the retired-key refusal names
    `../tcw-config.yaml`.
15. **C9.** `work list` exits 1 naming the child's file when a child project's
    `tcw-config.yaml` holds the retired key; a declared child that is not on
    this machine still lets it exit 0.
16. **V1.** Both `PATCH` routes answer 400 without `revision`, and 409 with a
    stale one.
17. **V2.** With an item's `spec/` a link to a folder outside the project,
    `GET` and `PUT` of `spec/spec.md` answer 404 and nothing is written
    outside; with the item's `capabilities.yaml` a link to a file outside, the
    declaration's `GET` and `PUT` answer 404 and the outside file is
    unchanged.
18. **V3.** Read: the comment above `_ANCHOR_CACHE` describes a server
    process.
19. **V4.** The scanner tests find a stage name inside `${…}`, as an unquoted
    key and as a member name, and do not read a regex after `return` as a
    string; the client scan passes.
20. **V5.** A vitest test renders `Conflict` with no DOM-nesting warning;
    `pnpm check:build` passes on the committed bundle.
21. **V6.** The scan finds `` `tcw work\nlist --bogus` `` as one command and
    flags `--bogus`; it does not join spans across a blank line; every
    tracked Markdown file passes.
22. **V7.** Read: the work guide's "Built-in gates" says no gate checks a
    stage's document and names the `pre` hook way.
23. **V8.** Read: `unattended-work.md` has the request row of Design 13.
24. **T1.** The two `GenerateError` messages name `work.hooks.output-cap` and
    `work.hooks.timeout`, and `grep -rn "work\.lifecycle\.\(output-cap\|timeout\)" tcw`
    finds nothing.
25. **T2.** The refusal for project `child` reads "the work store of project
    'child' is not in a git repository".
26. **T3.** `grep` finds none of the four old phrases; each docstring states
    the current behavior (read).
27. **T4.** With the fake answering 404 to every request, `work list` exits 1
    with "check that work.jira.site"; a 404 for a ticket is still exit 4.
28. **T5.** Offline, in Jira mode, a malformed `capabilities.yaml` is one
    error naming the file; with `--remote` it is still one; a well-formed one
    produces no offline finding.
29. **T6.** `scan("TCW no\nlonger …")` reports the hit at line 1; every caller
    passes.
30. **T7.** Offline, in Jira mode, a `qa/round-1.md` with a bad verdict gets
    the "ignored" warning and no "latest qa round is invalid" warning;
    filesystem mode still gets the latter.
31. **Documentation.** The guides and references named in the plan's
    "Documentation sync" describe the new behavior, and the upcoming changelog
    and release-notes entries list every user-facing change.
32. **Collection.** `pytest --collect-only -q` is clean, and every new guard
    went red under its stated mutation.
33. **J2.**
    - The owner's TCWTEST checklist is done, and steps 1 to 3 were confirmed
      with GET requests before any ticket was created.
    - `tests/work/jira/recorded/` holds the four files of Design 18:
      `post-search-jql-200-first-page.json` with `nextPageToken` and
      `isLast: false` in its answer; `post-search-jql-200-next-page.json` with
      `nextPageToken` in its request; `post-workflows-200-directed.json` with
      a transition whose `links` hold a `fromStatusReference`; and
      `get-issue-key-transitions-200-screen-fields.json` with a transition
      whose `fields` hold `labels` with `required`. No other recorded file
      changed in the J2 commits.
    - The first page's answer as Jira sent it, recorded by the test's own
      loop over the endpoint, holds `nextPageToken`, and the next-page request
      carried that token.
    - In the live run, `JiraClient.search` returned all 101 probe keys, each
      once (the test's output, quoted in `outcome.md`).
    - `test_recorded_shapes.py` lists the Design 18 read paths for the four
      files, its "never seen" comment is gone, and it passes; criterion 2 (J3)
      and `test_no_person_or_real_site_is_recorded` hold for the new files.
    - Each difference found between a recording and the code or the fake is
      listed in `outcome.md` with its fix, and each fix has a test against the
      fake that went red before it; or `outcome.md` says none was found.
    - `test_jira_live_shapes.py` is skipped in a run without
      `TCW_JIRA_J2_PROBE=1`, even with `TCW_JIRA_LIVE=1` set.
    - No probe ticket remains in `TCWTEST`, or `outcome.md` lists every
      remaining key with the search that finds them, and the owner has been
      given that list.

## Risks

- **C9 refuses more.** Every work command that calls `open_backend` (and the
  viewer) now fails on any problem `require_valid` finds in the project
  graph, not only the retired key. That is what the other three axes already do; the test of a declared
  but absent child guards the case that must still work.
- **V6 and T6 widen two scans.** Text that passes today may fail. Both scan
  files TCW-76 Part A is editing (`docs/migration-guide-2.8-to-3.0.0.md`,
  `docs/procedures/create-work.md`), and `scan` is used by
  `tests/test_docs_describe_3_0.py`, which TCW-76 changes. Whichever of the
  two items lands on `epic/tcw-3.0` second re-runs both scans over the merged
  tree.
- **C4 can change how a clone fails.** With `BatchMode=yes` a first contact
  with an unknown ssh host fails instead of asking. That is the intent; the
  message names git's reason.
- **V5 rebuilds the committed bundle.** `tcw/serve/dist` must be rebuilt and
  committed with the source, or CI's `web-build` job fails.
- **J2 waits on the owner and blocks the freeze.** It cannot start until the
  owner's TCWTEST checklist is done, and the item cannot complete without it.
  Every other fix goes first, so only J2 is left waiting.
- **J2 writes to a real Jira project.** It creates 101 tickets with approved
  summaries and moves one; nothing else. Creating them may send notification
  emails (the owner's checklist warns of it). If the account still cannot delete,
  the tickets stay until the owner bulk-deletes them, and they show in
  `tcw work tickets list` for a `TCWTEST` project meanwhile, since they sit at
  `To Do`, the inbox status. The live scenario does not read that list.
- **J2 may change `tcw/` late.** A recording that disagrees with the code
  changes `client.py` or `remote.py` after every other fix; that change gets
  its own review round (plan, Task 11) before the item lands.

## Overlap with TCW-76 Part A

The 2.x-to-3.0 user-visible changes this item makes (C2, V1, C4, C9, T5) have
already been sent to TCW-76 for its migration guide, so this item does not
edit `docs/migration-guide-2.8-to-3.0.0.md`. TCW-76's Task A10 owns
`docs/capabilities/cli/validate-a-project/description.md`; this item hands it
the T5 wording instead of editing it.

No file is changed by both. Two are read by both: `tests/doc_vocabulary.py`
(changed here) is imported by `tests/test_docs_describe_3_0.py` (changed
there), and `tests/test_documented_cli_surface.py` (changed here) scans
Markdown that TCW-76 changes. The plan avoids `tests/test_cli_config.py` by
putting P5's test in a new file.

## Owner's answers (2026-10-15)

All three questions are settled.

1. **J2: yes, before the freeze, all three shapes.** Record a second page of
   search results, a transition restricted to some statuses, and a transition
   screen that lists fields from `TCWTEST`, check the fake against them, and
   fix the code if they differ. The owner makes the workflow change by hand
   (the "Owner's TCWTEST checklist") and approved creating just over 100
   throwaway tickets in `TCWTEST`. J2 is now a fix (Design 18).
2. **V7: documentation only.** No built-in gate; the work guide says no gate
   checks a stage's document and how to add one (Design 12, as written).
3. **V8: write the request from the evidence and mark the assumptions**, then
   continue (Design 13, as written).

## Amendments (fix round, 2026-10-16)

These record what the review rounds after implementation changed. The code
and its tests are on the work branch; this section is not committed with it.

- **Design 14 (T4).** The endpoint is spelled `/rest/api/3/issueLinkType`, as
  the code spells it (corrected above and in the plan). A 404 on
  `/rest/api/3/project/<key>` is ambiguous: the project may be missing, or the
  site may not be a Jira site. `_read_metadata` then asks `/rest/api/3/myself`;
  a 404 there is `TrackerSiteMissing` (exit 1, naming `work.jira.site`), and an
  answer means the project is missing, which stays exit 4.
- **Design 5 and criterion 11 (C4).** `GIT_ASKPASS` is set to the empty string,
  not removed. git asks the first of `GIT_ASKPASS`, `core.askPass` and
  `SSH_ASKPASS` that is set, so with the variable removed a configured
  `core.askPass` would still run; set and empty, git skips the step.
  `SSH_ASKPASS` is still removed. Only the global and system
  `core.sshCommand` are read (`git config --global --includes --get` and
  `--system`), not a plain `git config --get` in the current folder: a clone
  into a new folder does not use the current repository's own setting, so that
  setting must not turn `BatchMode` off. When the user has set their own ssh
  command, TCW leaves it alone and ssh may still ask; every document that says
  provisioning does not ask now says so.
- **Design 1 (J1).** Before a note is sent, the ids of the newest
  `NOTE_WINDOW` comments are read, and after a dropped connection only a
  matching comment whose id was not among them counts as the note. An older
  comment with the same words (the same forced move, made before) no longer
  hides a note that never arrived. When the comments cannot be read after the
  drop, the error says the note may have been posted, and `advance` says the
  trace "may not have been recorded" rather than "was not recorded".
- **Design 15 (T5).** The single-item check (`tcw validate` on one item, and
  every viewer save) in Jira mode with no item still parses that item's
  `capabilities.yaml`, offline, and reports a malformed one in the same words.
- **Design 10 (V2).** The item's detail in the viewer lists files and verdicts
  only from paths inside the item folder: a document or declaration reached
  through a link that leads outside is shown as not written, and a round or
  handoff reached that way is left out and decides no verdict.
- **The Jira token on a redirect.** The client adds `Authorization` as an
  unredirected header, so a redirect to another host does not carry the token.
- **`tcw provision` with an unparseable config (pre-existing; the owner chose
  to fix it here).** A `tcw-config.yaml` that cannot be parsed (a list as a
  key, an unclosed bracket, a duplicate key) read as declaring nothing, so the
  command printed "Nothing to provision" and exited 0. It now prints the parse
  error, which names the file, and exits 1, with no traceback.
- **`tcw work new --project <id> --stage <stage>` (pre-existing; the owner
  chose to fix it here).** `--stage` was never passed to the delegated
  project, so it was ignored without a word. It is now a usage error (exit 2)
  naming the flag, the way `--project` refuses every other flag it does not
  take ("only --priority can"). It is refused rather than passed through
  because a delegated item always starts in the other project's inbox, and the
  only value `--stage` accepts is `inbox`.
- **`tcw config show` (P5).** A list of (key, value) pairs, which is how YAML
  reads `!!omap` and `!!pairs`, is written with the `!!pairs` tag and reads
  back equal. The printed YAML is read back before it is printed, and a value
  that would come back as something else is refused with an error naming its
  key.

### Final fixes

- **Design 5 and criterion 11 (C4), replacing the read described above.**
  Reading only `--global` and `--system` missed a `core.sshCommand` given on
  the command line (`git -c`, `GIT_CONFIG_PARAMETERS`, `GIT_CONFIG_COUNT`),
  which the clone does use, so TCW set its own `GIT_SSH_COMMAND` and replaced
  the user's key. There is now one read,
  `git config --show-scope --includes --get-all core.sshCommand`, and any
  non-empty value whose scope is not `local` or `worktree` is the user's own
  and is left alone. The current repository's own setting still does not turn
  `BatchMode` off. The documents name the command line as a source.
- **Design 15 (T5), the item-given path.** In Jira mode, when the item is
  given and its stage is terminal, the records check does not run, but the
  item's `capabilities.yaml` is still parsed offline and a malformed one is
  reported in the same words, as the no-item path and a full `tcw validate`
  report it whatever the stage. Nothing is asked of Jira.
- **The Jira token on a redirect, the 401 that follows.** `Authorization` is
  never sent on a redirect, so a 401 from the address a redirect led to says
  nothing about the credentials. When the address that answered 401 differs
  from the one requested, the error says Jira redirected the request to that
  address, that credentials are not sent on a redirect, and that
  `work.jira.site` should be the address Jira answers at. A 401 from the site
  itself is still reported as rejected credentials.
- **A `tcw-config.yaml` that is not valid UTF-8 (pre-existing).** `tcw
  provision` and `tcw init` printed Python's codec error, which names no file.
  The shared YAML reader (`read_yaml_text`, used by `load_yaml` and by
  `tcw init`) raises `NotUtf8`, still a `UnicodeDecodeError` and so a
  `ValueError`, whose message names the file and the byte, as the other
  commands already word it.
- **`tcw work new --project <id> --stage <stage>`, the reason given.** The
  refusal said a delegated item always starts in the other project's inbox,
  which is not true of a Jira-mode project, where the ticket waits in Jira for
  `tcw work tickets adopt`. It now says the item starts where that project's
  intake puts it, which holds for both; the earlier amendment's "always starts
  in the other project's inbox" is superseded in the same way.
