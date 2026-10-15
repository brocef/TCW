# Spec — Fix what TCW-71 to TCW-75's reviews left in the 3.0 code, before the freeze

A child of the TCW 3.0 epic (TCW-68). Every file, line and function named here
was read on `epic/tcw-3.0` at `e301bef5`.

## Capability changes

None. Each fix corrects an existing behavior, message or test; no capability
is added, changed or removed.

## Problem

The verify reviews of TCW-71, 72, 73, 74, 77 and 75 left 32 findings sorted as
"needs a separate change". Most are in `tcw/`, which TCW-76's code freeze (its
Task B3) closes until the epic merges. The owner decided on 2026-10-15 that
every one goes in before the freeze, including those that change behavior.
Twelve change what a command or the viewer does (J1, P4, C1, C2, C4, C7, C9,
V1, V2, T4, T5, T7); the rest change messages, comments, documents or tests.

## Triage

Numbering: **J** = TCW-71's Jira backend entry, **P** = TCW-72's personal
configuration entry, **C** = TCW-73's CLI entry, **V** = TCW-74's and TCW-77's
entry, **T** = TCW-75's code-text entry, each in the order of
`initial-request.md`.

| # | Finding | Verdict | Evidence or reason |
| --- | --- | --- | --- |
| J1 | A dropped connection while posting a note invites a duplicate | **fix** (Design 1) | `_post_note`, `tcw/work/jira/backend.py:946`, turns every `TrackerError` into `MovedWithoutNote`, including a drop after Jira received the comment; `advance.py:285-289` then says "add it with `tcw work comment`" |
| J2 | Two shapes of Jira's answers were never recorded live | **reject from this item** | Recording them needs a transition restricted to some statuses (a workflow change only the owner makes, epic rule) and more than 100 tickets created in `TCWTEST` (Jira writes needing approved text). It changes no code unless the recording disagrees with the fake, and the fake is in `tests/`, which the freeze does not cover. Returned to the inbox as its own entry (plan, Task 8). Owner question 1 |
| J3 | Recorded user objects keep `timeZone` and `locale` | **fix** | `tests/work/jira/capture.py` replaces only `accountId`, `displayName`, `emailAddress` (`_PEOPLE`, line 33); five recorded files hold `"timeZone": "America/New_York"` and `get-user-200.json` holds `"locale"` |
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
| C7 | `list` and `rm` disagree about a sub-folder with no `meta.yaml` | **fix** (Design 7) | `_local_slugs`, `tcw/store/fs.py:1672-1678`, lists any readable folder; `get_local` (line 1670) answers for one too |
| C8 | The retired-key message names a bare `tcw-config.yaml` | **fix** | `refuse_retired_config`, `tcw/store/fs.py:291`, prints `SENTINEL` alone |
| C9 | `tcw work list` does not notice a child project's retired key | **fix** (Design 8) | `open_backend`, `tcw/work/open.py:63`, opens the registry without `require_valid()`, which `taxonomy`, `projects`, `provision` and `validate` all call |
| V1 | Taxonomy and capability edits skip the stale check when no revision is sent | **fix** (Design 9) | `update_term` and the capability update, `tcw/serve/records.py:112` and `:188`, read `revision` with `required=False` |
| V2 | A symbolic link inside the work path lets a file save write outside the project | **fix** (Design 10) | `file_path`, `tcw/serve/files.py:101-118`, builds the path and never resolves it; `write_checked` makes the parent and writes there |
| V3 | `_ANCHOR_CACHE` lives for the whole server process; its comment says one command | **fix** (comment) | `tcw/store/project.py:58-61`. Scoping the cache would change behavior for no observed gain; the comment is corrected to say what is true |
| V4 | The stage-name scan misreads some TypeScript | **fix** | `tests/serve/test_no_stage_names.py`: template `${…}` bodies, unquoted object keys, member access, and a regex after a keyword |
| V5 | `Conflict` nests a `<div>` inside a `<p>` | **fix** | `web/client/src/ui/content-views.tsx:399-417`: `Callout.Text` is a `<p>` and holds `Text as="p"` and a `Flex` |
| V6 | Commands wrapped across a line inside backticks are never checked | **fix** (Design 11) | `BACKTICKED`, `tests/test_documented_cli_surface.py:84`, forbids a newline in a span |
| V7 | `tcw work advance` leaves spec and plan with no document written | **fix: documentation only** (Design 12) | No built-in gate is added. Owner question 2 |
| V8 | Unattended runs have no rule for an item at request | **fix** (Design 13) | `tcw/work/procedures/unattended-work.md`'s table has no request row |
| T1 | Error messages name removed keys | **fix** | `tcw/work/generate.py:180` and `:184` say `work.lifecycle.output-cap` and `work.lifecycle.timeout`; the keys are `work.hooks.*` (`tcw/work/config.py:44`) |
| T2 | A doubled quote in a refusal | **fix** | `uncommitted_changes`, `tcw/work/open.py:107-110`, prints `'child''s work store` |
| T3 | Four out-of-date texts: `hooks.py` on `tcw serve`; `run_provision` "the only command that reaches the network"; `store/base.py` "remote adapters … unbuilt"; `skills/README.md:85` "TCW-75 rewrites this skill" | **fix** (all four) | Each read at the cited line; the viewer runs request `post` hooks on adopt (`tcw/serve/work.py:529-537`); the Jira backend reaches the network |
| T4 | A missing Jira site is reported as "the tracker has no such resource" | **fix** (Design 14) | `_for_status`, `tcw/work/jira/client.py:487-488`, maps every 404 to `TrackerNotFound`, which `_jira()` turns into "not found" (exit 4). An unreachable host is already "Jira could not be reached" (exit 5, `client.py:170-177`), so only the 404 case is fixed |
| T5 | Offline `tcw validate` in Jira mode skips the item-folder checks | **fix** (Design 15) | `_work_findings`, `tcw/validate.py:556-560`, returns before any item folder's `capabilities.yaml` is read |
| T6 | The shared vocabulary scan reads one line at a time | **fix** (Design 16) | `scan`, `tests/doc_vocabulary.py:61-68` |
| T7 | Offline Jira validation reports `qa/` rounds it says are ignored | **fix** (Design 17) | `round_findings`, `tcw/validate.py:597-624`, reads every enabled verdict stage, including those in `layout.external` |

**Counts: 30 fix, 1 already fixed (C5), 1 rejected from this item (J2).**

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
holds a `meta.yaml`: `cannot reset '<id>': nested under its override: <paths>
(remove those first)`, exit 3. The check is factored into one helper both
use. Litmus: "an entry with children cannot be deleted as a leaf" holds for
any tree store.

### 4. `--slug` must be a slug (C2)

A slug given to `taxonomy add` (`--slug`, and `slug` in the viewer's create
request, which reaches the same `add`) must be lowercase letters and digits
in words joined by single hyphens, the form `slugify` produces: it must equal
`slugify(slug)`. Otherwise a usage error, exit 2: `--slug 'A B' is not a
slug: use lowercase letters, digits and single hyphens`. A `/` is refused too;
nesting is `--parent`'s job. The predicate lives beside `slugify` in
`tcw/store/base.py`; the check is in `FsTaxonomyStore.add`, so the viewer
answers 400. Existing terms are untouched. Litmus: a naming rule any store
can enforce.

### 5. `tcw provision` never prompts (C4)

`FsStoreProvisioner._run` passes git an environment with
`GIT_TERMINAL_PROMPT=0`, which stops git's own prompt for HTTPS credentials
(a credential helper still answers). For ssh it also sets
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

### 7. A term is a folder with a `meta.yaml` (C7)

`_local_slugs` and `get_local` count a folder as a term only when it holds a
`meta.yaml`, as TCW-73 Design 8.2 defines a nested term and as the
capabilities store already does (`_all_meta_dirs`). So `taxonomy list` no
longer shows `invoice/sub`, `show invoice/sub` is not found, and a reference
to it is reported dangling by `check`, which matches `rm invoice` deleting it
with its parent. `remove`'s comment that a sub-folder without a `meta.yaml`
"still lists as a term" is corrected. Litmus: "an entry is what has
metadata" holds for any store.

### 8. Every work command checks the project graph (C9)

`open_backend` calls `require_valid()` on the registry it already opens, for
the project the command acts on (`personal=True`), so a child's retired key
refuses `work list` and every other work command exactly as it refuses
`taxonomy list`. Another project's backend (`personal=False`) is not checked,
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
folder's resolved path. It covers reads and writes, and the declaration file.
A work path that is itself a link is unaffected, because both sides resolve.
Editing outside the viewer is the user's own business and is not changed.
Litmus: the viewer's file routes exist only where the layout keeps files.

### 11. Wrapped commands in backticks (V6)

The scan finds code spans over a whole paragraph instead of a line: a span
may cross a single line break but not a blank line, each line break inside it
reads as a space, and spans are paired left to right as Markdown pairs them.
The original reason for the one-line rule (an unpaired backtick reuniting
`tcw` and a verb from different sentences) cannot recur, since a span never
crosses a paragraph. Commands it newly finds must be valid or reworded.

### 12. Leaving a stage without its document (V7)

No built-in gate is added. `spec` and `plan` are optional stages, a project
already adds such a check as a `pre` hook (TCW's own does, with
`scripts/require_artifact.py`), and a built-in one would add a refusal every
project must override when it decides the document is not needed. The work
guide's "Built-in gates" says that no gate checks a stage's document and how
to add one. Owner question 2 asks whether the owner wants a built-in gate
instead.

### 13. Unattended runs at request (V8)

A row in `unattended-work.md`'s table: at request, do not ask the advisors in
the requester's place, since what the requester wants is not theirs to know.
Write the request from the evidence available, marking each assumption, as
the request prompt says for "There is no user to ask"; where Jira keeps the
request, post the questions with `tcw work comment <slug>` instead and leave
the text alone; then continue. `skills/extras-autonomous-work/SKILL.md` gets
the same rule if it lists stages itself.

### 14. A missing Jira site (T4)

A 404 from an endpoint every Jira Cloud site has (`/rest/api/3/search/jql`,
`/rest/api/3/myself`, `/rest/api/3/issuelinktype`) cannot mean a missing
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

`scan` matches each paragraph (consecutive non-blank lines) joined with
single spaces, then maps each hit back to the line where it starts, with its
start column in that line and its end clamped to that line, so `Hit` and
every caller (`test_shipped_text.py`'s `_allowed_at`) keep working.

### 17. External stages are not round-checked (T7)

`round_findings` skips any stage in `layout.external`, as `completion_gate`
already does. A `qa/round-1.md` in Jira mode then gets only "Jira keeps the
qa record, so this folder is ignored". The Jira guide already says offline
validation checks "the latest `review` round".

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
   exits 3, names `auth/login/nested`, and leaves both folders.
9. **C2.** `taxonomy add X --slug 'A B'` and `--slug a/b` exit 2 and create
   nothing; `--slug memo` still works.
10. **C3.** The scan reads `["git", "-c", "a=b", "switch", "x"]` as `switch`,
    reports each of the eight added verbs, accepts `clone` and `checkout` only
    inside `FsStoreProvisioner._obtain`, and fails on a `status` call without
    `--no-optional-locks`.
11. **C4.** `_run` passes `GIT_TERMINAL_PROMPT=0`; it sets `GIT_SSH_COMMAND`
    with `BatchMode=yes` when nothing is configured, and leaves a set
    `GIT_SSH_COMMAND` as it was.
12. **C6.** Under pytest, `shutil.which("tcw")` is in the folder of
    `sys.executable` whenever that folder has a `tcw`.
13. **C7.** With `invoice/sub/` holding no `meta.yaml`, `taxonomy list` does
    not show `invoice/sub` and `taxonomy show invoice/sub` exits 4.
14. **C8.** Run from `p/docs`, the retired-key refusal names
    `../tcw-config.yaml`.
15. **C9.** `work list` exits 1 naming the child's file when a child project's
    `tcw-config.yaml` holds the retired key; a declared child that is not on
    this machine still lets it exit 0.
16. **V1.** Both `PATCH` routes answer 400 without `revision`, and 409 with a
    stale one.
17. **V2.** With an item's `spec/` a link to a folder outside the project,
    `GET` and `PUT` of `spec/spec.md` answer 404 and nothing is written
    outside.
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

## Risks

- **C9 refuses more.** Every work command (and the viewer) now fails on any
  problem `require_valid` finds in the project graph, not only the retired
  key. That is what the other three axes already do; the test of a declared
  but absent child guards the case that must still work.
- **C7 hides folders that listed before.** A hand-made term folder with no
  `meta.yaml` disappears from `list` and references to it turn dangling.
  `taxonomy add` always writes `meta.yaml`, so only hand-made folders are hit,
  and `check` names each reference.
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

## Overlap with TCW-76 Part A

No file is changed by both. Two are read by both: `tests/doc_vocabulary.py`
(changed here) is imported by `tests/test_docs_describe_3_0.py` (changed
there), and `tests/test_documented_cli_surface.py` (changed here) scans
Markdown that TCW-76 changes. The plan avoids `tests/test_cli_config.py` by
putting P5's test in a new file.

## Questions only the owner can answer

1. **J2.** Recording the two unseen Jira shapes needs a status-restricted
   transition configured in `TCWTEST`'s workflow and more than 100 tickets
   created there. Do you want that done, and if so, before the freeze? This
   spec assumes not: it becomes its own inbox entry.
2. **V7.** This spec documents that no gate checks a stage's document instead
   of adding a built-in one. Do you want a built-in gate (refuse leaving
   `spec` or `plan` with no document unless `--force`)?
3. **V8.** The rule chosen for unattended runs at request is "write from the
   evidence and mark assumptions, then continue". The alternative is "leave
   the item at request and report it". Which do you want?
