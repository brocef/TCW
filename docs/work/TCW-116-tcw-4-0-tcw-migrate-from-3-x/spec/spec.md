# Spec — TCW 4.0: `tcw migrate` from 3.x

Child 11 of 13 of TCW-99. It carries out the migration part of the TCW-99
design (`docs/work/TCW-99-…/design.md`): "Versions and migration"
(design.md:686-750), "Coming from 3.x" (design.md:60-94), the success
criteria (design.md:795-807) and "How 4.0 is built" (design.md:809-841). It
converts everything the ten items before it leave in 3.x form, and answers
every handoff those items posted on this ticket (Notes, "Handoffs answered").

**Order.** This item is built after TCW-106 to TCW-115 have landed on `v4`
(the ticket's blockers). So when it starts, 4.0 reads only 4.0 files: a
project is a folder holding `.tcw/tcw-config.yaml` (TCW-106 Design 2.2),
projects are related by `parents:` and `children:` (TCW-108 Design 1-2) and
located through manifests (TCW-107 Design 1-2), configuration is inherited
(TCW-109), objects are named by full identifiers (TCW-110), each object's
folder holds a `tcw-` state file (TCW-111), an override is an object at its
original's path (TCW-112), only the active project changes anything and
objects can be moved (TCW-114), and the project commands are `tcw project
…` (TCW-115). Every one of those items refuses or reports the 3.x form of
what it replaces, naming `tcw migrate`.

File and line references to code are to commit `32c510f0` on `v4`, where
TCW-106 is built and TCW-107 to TCW-115 are not. **The 3.x behaviour this
spec describes is that of the released 3.x, tag `v3.0.2`**, and that tag,
not `32c510f0`, is what migration's 3.x readers are copied from (Design
8.2): `32c510f0` already holds TCW-106's changes to some of those very
readers (`load_config` refusing a file with no `tcw-version`,
`parse_connected_entry` skipping some unknown keys, the personal layer read
from `.tcw/`), so a copy from it would not read a 3.x project the way 3.x
did. `main`'s `tcw/` is exactly the tag's (`git diff v3.0.2 main -- tcw/` is
empty, checked 2026-10-22; `main` differs from the tag only in records under
`docs/`). Where the code is the same, a line cited at `32c510f0` is the
tag's plus a fixed offset; "Citations at `v3.0.2`" (Notes) gives each copied
reader's place at the tag. Several of
those items delete the 3.x readers cited here (TCW-108 Step 8b, TCW-111,
TCW-112), so the plan recreates what migration needs from the tag (Design
8.2) and re-checks every reference against what has landed. TCW-107 is landing
while this spec is written; "Citations at HEAD" (Notes) gives, for every
cited file it has changed so far, where the cited code sits at `ebce3fd6`.
"TCW-10n Design m" means rule m of that item's spec; `S10n:L` means line L
of that item's `spec/spec.md`, and `P10n:L` its `plan/plan.md`.

**Build order: the engine first, then related projects** (decided by the
dispatching session, 2026-10-22: TCW-116 stays one item, as TCW-111 and
TCW-114 did, and is built in two parts so that the part this repository
needs lands and is proven first). This repository has no `projects:` key,
no `extends` and no `overrides:` pointer (its two configuration files and
its ledger, checked at `ebce3fd6`), and TCW-118 needs it migrated, so:

- **Part 1, the engine**, is complete on its own: everything a single
  project needs, its files and its Jira tickets. It is Design 1 (the
  command, `--dry-run`, `--no-jira`), Design 2 (the plan, the phases, the
  progress record, stopping and running again, nothing lost, and every
  blocker and report that a single project can give), C1, C2, C5 for a
  location inside the project, C7, C9 to C13, C16 for references to the
  project's own objects and for work slugs, Design 4.2, Design 5 (Jira),
  Design 7's writing of the record, Design 8 and Design 9, and the reports
  D5 and D7. Its criteria are 1-7, 8 (for B1-B3, B5-B8, B10's "no
  capabilities ledger" form, B11 and B14-B17), 10-20, 29-31, 33-37, 41 (the
  rows not naming another project), 42-44, 49, 51 (on F-single), 52-60,
  62, 63 and 65-69.
- **Part 2, related projects**, builds on part 1 and changes none of its
  rules: C3, C4, C5 for a location outside the project, C6, C8, C14, C15,
  C16 for references owned by another project, Design 6, Design 7's
  reading of the record, Design 8.5, and the reports D1 to D4, D6 and D8.
  Its criteria are 8 (for B4, B9, B10's other forms, B12 and B13), 9,
  21-28, 32, 38-40, 41 (the rows naming another project), 45-48, 50, 51 (on
  F-full), 61 and 64. B4, B9, B10's other forms, B12 and B13 can arise only
  from part 2's conversions: `route_capability_path`'s one ambiguity needs
  a declared child, a bare path's needs an `extends` source, B9 needs
  `overrides:`, B12 a replaced block (part 1 only renames keys and removes
  scalars), B13 manifests, B4 `extends`; and criterion 9 names B9 (decided
  by the dispatching session, 2026-10-22: the plan review's spec issue 3,
  checked against `route_capability_path` at `v3.0.2`,
  `tcw/work/gates.py:331-380`).

The plan lands part 1 and proves it on this repository (Design 9.2)
before it starts part 2. Until part 2 lands, part 1 gives B5 for any 3.x
form that part 2 converts, so a project that needs part 2 is refused
rather than half converted.

Terms used throughout:

- **The active project** is the project a command runs in (TCW-99
  requirement 7): the nearest folder, from the current one outwards, that
  holds a project marker (TCW-106 Design 2).
- **A 3.x form** is anything written the way TCW 3.x writes it: a root
  `tcw-config.yaml`, a `meta.yaml` or `item.yaml`, a `projects:` key, an
  `extends` list, an `overrides:` pointer, an `id: cap-…`, a reference
  written `<project>/<folder>` or `tcw://C/…`, a Jira `TCW Item` value with
  no `.` before its first `/`.
- **A related project** is any project the active project's 3.x
  configuration names (under `projects:` or in an `extends` list), and any
  project those name in turn, as far as the conversion needs to read.
- **A conversion** (C1 to C17, Design 3 to 5) turns one 3.x form into its
  4.0 form. **A report** says something the person should look at; it
  stops nothing. **A blocker** (B1 to B17, Design 2.9) is something
  migration cannot convert without guessing or losing something; it stops
  the whole run before anything is written.
- **Atomic** writing of a file means writing the new content to a
  temporary file in the same folder and then renaming it over the old one,
  so that a run that stops leaves either the old file or the new one, never
  half of one.

## Capability changes

- **New** `cli/migrate-a-tcw-3-x-project-to-tcw-4`: `tcw migrate` converts
  the active project from TCW 3.x to 4.0 in place, files first and Jira
  tickets last; `tcw migrate --dry-run` lists every file and ticket it
  would change, and every report and blocker, and changes nothing;
  `tcw migrate --no-jira` converts the files only, never contacts Jira,
  and says what the Jira step would do; a run that stops partway is
  finished by running it again, and a run with nothing left to do changes
  nothing.
- **Changed** `cli/read-a-file-by-the-format-version-it-records`: its text
  names `tcw migrate` where it says "the command that converts a TCW 3.x
  file to TCW 4" (TCW-106's implement round, `I106:142-146`, left it
  unnamed because the verb did not exist yet).
- **Taxonomy:** new term `migration` (converting a project's files, and its
  Jira tickets, from one format version to the next, and the record a
  migration leaves in `.tcw/tcw-migration.yaml`).

This repository's own ledger stays in 3.x form until it is migrated (Design
9), so these records are written in 3.x form, as every sibling's are
(S110:167-173).

## Problem

1. **No 3.x project can be used by 4.0, and nothing converts one.** Every
   command run in or below a 3.x project refuses it first
   (`refuse_legacy_project`, `tcw/store/fs.py:310-315`, called before every
   command at `tcw/cli.py:647-649`), naming `tcw migrate`
   (`legacy_message`, `tcw/project_files.py:122`). That command does not
   exist: `build_parser` (`tcw/cli.py:549-614`) registers no `migrate`, and
   because the refusal runs before any command, a `migrate` added the
   ordinary way would refuse itself.
2. **The siblings each leave their 3.x data to this item.** Each refuses or
   reports its 3.x form and names `tcw migrate`: the root configuration
   (S106:228-232), a missing version (S106:192-197), `projects:` (S108:442-464),
   `extends` (S112:332-358), `overrides:` (S112:877-884), `id: cap-…`
   (S112:831-835), a 3.x state file (S111:447), a 3.x stored reference or
   link (S110:289-297, :469-481), a 3.x `TCW Item` (S110:483-506), and a
   move whose ticket holds one (S114:1046-1051). The handoffs on this
   ticket list what each needs converted, reported or refused (Notes).
3. **A 3.x project is spread over several files and Jira.** Its
   configuration is one root file plus an untracked personal file
   (`LEGACY_SENTINEL`, `tcw/project_files.py:38`); its relations are a
   `projects:` mapping with `parent`, `children` and `upstream`
   (`tcw/store/project.py:616-631`), each entry a locator, a `repository`
   declaration, or both, and an optional `jira` block
   (`parse_connected_entry`, `tcw/store/base.py:866-917`); content is
   inherited only through `taxonomy.extends` and `capabilities.extends`
   (`_extends_ids`, `tcw/store/fs.py:904-933`); a store is a `path`, a
   `repository`, or both (`resolve_store`, `tcw/store/fs.py:3182-3318`).
   Each object's folder holds `meta.yaml` or `item.yaml`; a Jira ticket's
   `TCW Item` holds `<project>/<folder>` (`rename` writes it,
   `tcw/work/jira/backend.py:890-893`). A conversion that changes one of
   these without the others leaves a project neither version can read.
4. **3.x meanings are not all visible in the files.** An override points at
   its original by an opaque id minted at random (`_mint_cap_id`,
   `tcw/store/fs.py:2211-2213`), either bare or prefixed with the extended
   project's ID, and is matched by that id, not by its folder
   (`_apply_override`, `tcw/store/fs.py:2344-2389`, the match at `:2352`).
   The id of the original lives in another project, so once that project
   has dropped its ids, a reader's pointer can no longer be resolved. A
   reference's owner is decided by 3.x rules: a bare capability path is the
   project's own if it has one, else the one inherited source that has it,
   else ambiguous (`get`, `tcw/store/fs.py:2425-2440`); a `capabilities.yaml`
   entry is routed by its first folder (`route_capability_path`,
   `tcw/work/gates.py:331-380`); a 3.x taxonomy term is every folder in the
   store, with or without a `meta.yaml` (`_local_slugs`,
   `tcw/store/fs.py:1763-1769`). Migration has to read these the way 3.x did.
5. **Related projects migrate separately.** The design has each project
   migrate itself and never another (design.md:699-711), so a family is in
   a mixed state between runs. Several conversions depend on another
   project's files (whether an `extends` target is already inherited,
   whether a link must be inverted, what an override pointer names), and
   the other project may be in either format when they are read.
6. **This repository is itself 3.x on `v4`.** Its lifecycle is driven by
   the `tcw` first on `PATH`, the primary checkout's editable install of
   `main`, which reports 3.0.2 (S110:1167-1171). On `v4` it keeps a 3.x root
   `tcw-config.yaml` beside a 4.0 `.tcw/tcw-config.yaml`, held equal by
   `tests/test_repo_config_pair.py:33-40`; its 58 work items hold `item.yaml`,
   its 140 ledger objects `meta.yaml` (91 of them an `id: cap-…`; counted in
   the `v4` worktree on 2026-10-22), two item
   folders hold a loose file (`docs/work/TCW-99-…/design.md`,
   `docs/work/TCW-76-…/notes-from-tcw-74.md`), and its Jira tickets hold 3.x
   `TCW Item` values (P110:35-39). Once TCW-111 lands, `v4`'s own code finds none of its
   items (S111:1231-1254).

## Goals

1. One command, `tcw migrate`, that converts the active project's every 3.x
   form to 4.0, in place, files first and Jira tickets last.
2. A dry run that lists every file and every Jira ticket the real run would
   change, with every report and blocker (all but A12, which only the
   checks after a real run can give, Design 2.1), and changes nothing; and
   a way to convert the files without contacting Jira (`--no-jira`).
3. Safety, each checkable: the full plan is made before anything is
   written; a blocker stops the run before anything is written; running it
   again finishes a run that stopped; a run with nothing left changes
   nothing; nothing is lost; it works in a monorepo migrated one project at
   a time and in a planning workspace with many repositories.
4. Every handoff on this ticket answered (Notes).
5. This repository's migration proven on a copy, with an exact procedure
   for the real one at the merge of `v4` into `main` (Design 9).

## Non-goals

- **Reading 2.x projects** (the request's "Out of scope"). A 2.x key is a
  blocker naming the 3.0 migration guide (B2).
- **Other migrations.** The design allows later migrations to convert one
  object at a time when a command touches it (design.md:704-707); this
  item builds only the whole-project 3.x-to-4.0 one.
- **Changing another project**, even one in the same repository. Each
  project is migrated by running `tcw migrate` in it (design.md:708-711).
- **Nesting existing work items.** A 3.x child item stays beside its parent
  and keeps its folder name, so its id-path is its folder name, as TCW-111
  decided for migrated children (S111:1398-1401); nesting is `tcw work
  move`'s (TCW-114).
- **Renaming objects whose names 4.0 refuses.** That is a choice of name
  only the person can make (B8).
- **Rewriting prose.** Plain text that mentions a 3.x slug or a 3.x key in a
  stage document, a comment, or a ticket's description is history, and is
  left as written; only the fields and links of C16 are converted, and
  exact mentions of moved files in the project's own stores (C13). A
  ticket's description is never read, so a mention of a moved file there
  is neither rewritten nor reported.
- **The migration guide** for people and for scripts (removed commands and
  flags, `--local`, the epic-parts flow): TCW-117.
- **Merging `v4` into `main` and running the real migration of this
  repository and of the user's setups:** TCW-118, by the procedure of
  Design 9.

## Design

### 1. The command

1.1. **Form.** `tcw migrate [--dry-run] [--no-jira]`, a top-level command
beside `tcw validate` and `tcw serve`, not in the `tcw project` group
(S115:190-191). It takes no project or object argument (design.md:699-701);
an argument is a usage error (exit 2). `tcw -C <folder> migrate` runs it in
that folder, as every command (TCW-114 Design 4).

- **`--dry-run`** changes nothing (Design 2.3).
- **`--no-jira`** converts the files only. It never contacts Jira, so it
  needs no credentials, lists no ticket and edits none, and skips phase F
  (Design 2.4). Its summary says what the Jira step would do:
  `tickets not converted (--no-jira): the TCW Item of every ticket of Jira
  project <KEY> whose TCW Project is '<id>' and that holds a 3.x value;
  run 'tcw migrate' to convert them`. A later `tcw migrate` without the
  flag finds the files already converted and does only phase F
  (Design 2.6). In a project whose work is kept in files, the flag changes
  nothing. It combines with `--dry-run`. Decided by the dispatching
  session, 2026-10-22: protecting the live board must be something a
  person can see in the command they type, not an environment variable
  being unset; this user's shell sets the Jira credentials for every
  command, so "unset them" is easy to forget. This reverses the first
  draft's choice of no flag.

  **What makes `--no-jira` safe is structural, not only tested.** With the
  flag, the run never builds a Jira client or a Jira backend, so no code
  path in the run holds anything that can send a request. Three places
  could build one, and each is closed:
  - **Planning the tickets.** One function plans the Jira half, and it is
    the only code that imports the one module of migration that builds a
    Jira client or backend. Every run calls it, whether it plans afresh
    or follows a progress record (Design 2.7), and with the flag (or for a
    project whose work is kept in files) it returns before that import.
  - **Phase F.** Phase F uses only what that function returned, and with
    the flag it returned nothing, so phase F has nothing to run.
  - **The check after the run** (Design 2.1). For a project whose work is
    kept in Jira, 4.0's work-store checks open the Jira backend, which
    builds a client even though those checks send nothing. So with the
    flag, the check after the run leaves out the work-store checks. Every
    other check still runs. The summary says what was left out:
    `work store not checked after the run (--no-jira): run 'tcw validate'
    to check it`.

  Decided by the dispatching session, 2026-10-22, after the plan's
  re-check (its N1 and N2). Before this, 4.0's check after the run built
  the backend on every Jira-backed run, and a re-run following a progress
  record searched Jira from code that nothing named. Skipping the
  work-store checks is the smallest change that keeps "never builds" true.
  The other choice, a files-only mode inside `tcw validate`, would change
  a command every user runs, to serve one caller.

  Separately, every run that plans the Jira half hands the planning code
  a read-only wrapper of the client. The wrapper passes on only the reading calls planning makes
  (`search`, `issue`, `edit_metadata`, `project`, `create_metadata`,
  `myself`). Any other attribute raises: every writing call, the
  client's own request helpers, and any writing call a later item adds.
  Only phase F is given the client itself. So a dry run cannot edit a
  ticket even through a mistake in the planning code (decided by the
  dispatching session, 2026-10-22: the plan review's S1; a guard the
  code's shape gives costs a few lines, and a mistyped proof command
  against the live board is the one risk it closes). The wrapper names
  the calls it allows, not the ones it refuses (decided by the
  dispatching session, 2026-10-22, the re-check's S8). A list of refused
  calls would still let through the request helpers and any writing call
  added later, and naming the allowed calls costs no more.

1.2. **Which project.** The nearest project marker from the current folder
outwards (`find_marker`, `tcw/project_files.py:96`), 3.x or 4.0. `migrate`
is exempt from **every check `_dispatch` makes before it runs a command**,
because those checks read exactly the files that are its input. At
`32c510f0` they are the 3.x refusal (`refuse_legacy_project`,
`tcw/cli.py:649`), the 2.x-key refusal (`refuse_retired_config`, `:654`)
and the configuration check (`:658-661`, skipped by a command that sets
`own_config`); at `ebce3fd6` the same three sit at `tcw/cli.py:467`, `:472`
and `:476-479`. Siblings may add more checks there before this item is
built (TCW-109's environment check, TCW-114's `-C`), so the rule is stated
as "every check made before the command", and the plan lists them on the
final `v4`. With no marker it exits 1 with the message every command gives
outside a project. A 4.0 project is migrated too: whatever 3.x forms it
still holds are its input (a run that stopped, a person whose personal
file is still 3.x, a branch merged after the migration that brought 3.x
files, Design 2.11).

1.3. **What it reads.** The active project's files in either format; the
user-wide personal file (`$XDG_CONFIG_HOME/tcw/config.yaml`), read and never
written; related projects' files in either format, read and never
written; and, for a project whose work is kept in Jira and unless
`--no-jira` is given, the tickets of its own Jira project (Design 5).

1.4. **What it writes.** Only the active project's own files: its
configuration, its manifests, its `.tcw/.gitignore`, its record
(`.tcw/tcw-migration.yaml`, Design 7), and its own stores' objects wherever
those stores sit, and the `TCW Item` field of its own tickets. While a run
is unfinished it also keeps its progress record,
`.tcw/tcw-migration-progress.yaml` (Design 2.7). A store that
sits in another repository (UC-4) is still the active project's own
(design.md:588-593); its changed files are listed at the end under
`left in another repository: <repository folder>`, as a 3.x filing into
another project names them (`_uncommitted_in`, `tcw/work/open.py:202`;
`docs/use-cases.md`, UC-4). A store that 3.x fetched into its per-machine
cache is listed the same way, since its changed files have to be
committed and pushed from that cache clone.

1.5. **Output.** Every line goes to standard error and nothing to standard
output, as for `tcw project provision` (S115 Design 7.1). A real run prints
one line per change as it makes it; a dry run prints the same lines with
`would` before the verb. Each change line names the file or ticket, the
action (`write`, `move`, `delete`, `edit`) and its conversion
(`C9 meta.yaml -> tcw-capability.yaml`); a ticket's line also gives its
old and new value (`C17 TCW-12 TCW Item: tcw/TCW-12-x ->
tcw.work/TCW-12-x`). Reports follow, grouped as "needs attention" and
"reads differently in TCW 4" (Design 2.9), then blockers, then the summary
(Design 2.10).

1.6. **Exit codes** are the existing ones (`EXIT_CODES`,
`tcw/cli_help.py:38-49`; the numbers, `tcw/exit.py`); no new code. A Jira
failure keeps the code the Jira backend already gives it (`_jira`,
`tcw/work/jira/backend.py:73-95`): Jira not reachable, or limiting
requests, is `Unreachable`, exit 5 (`:80-83`); missing or refused
credentials (`TrackerAuthError`, raised before any request when a
credential variable is unset, `tcw/work/jira/client.py:152-159`), a
refused permission and a missing site are `BackendError`, exit 1
(`:84-89`). Migration does not remap them (decided by the dispatching
session, 2026-10-22: every other command gives these codes for these
failures, and a script that already reads them needs nothing new):

| Code | When |
| --- | --- |
| 0 | finished, or nothing to migrate; with `--no-jira`, the files finished and Jira not contacted; for `--dry-run`, a plan with no blocker |
| 1 | a local step failed partway (Design 2.7); Jira refused the credentials, or they are not set, or another Jira error that is not "unreachable"; no project here |
| 2 | an argument was given |
| 3 | refused: one or more blockers; nothing was written |
| 5 | Jira could not be reached, or limited requests |

Whether anything was written when Jira failed depends only on when it
failed (Design 2.3, 5.3): while planning, nothing was written; in phase F,
every local phase is finished and the tickets named are not.

1.7. **Git.** `tcw migrate` does not check git and does not refuse because a
working tree has changes (design.md:715-716, requirement 2). It makes only
the git reads TCW already makes (whether a folder is inside a repository,
for `.tcw/.gitignore`, S106:145-148), and never commits, stages or changes
git state (`docs/lifecycle/abstraction.md:98-103`).

### 2. How a run proceeds

2.1. **The plan comes first.** Every run, real or dry, first reads
everything of Design 1.3 and works out every change, report and blocker,
in memory, before it writes anything. For a project whose work is kept in
Jira, and unless `--no-jira` is given, reading the tickets is part of the
plan. The requests it makes are: the search of Design 5.1, which is a
`POST` that only reads (`client.search`, `tcw/work/jira/client.py:242-270`)
and is paged, so one request per page; the reads the backend makes to find
its field ids (`metadata`, `tcw/work/jira/backend.py:253-296`: the Jira
project, its paged create screen, and `GET /myself` when the project
answers 404); and, when at least one ticket is to be edited, one request
for the edit screen of the first such ticket (`edit_metadata`,
`tcw/work/jira/client.py:370-373`), which must offer the `TCW Item` field
(B16). None of them is a `PUT`, and no `POST` but the search's is made. A
failure of any stops the run before anything is written (Design 2.3).

**Checking the planned result as 4.0 would read it** happens at two
points, chosen so that no 4.0 reader has to read files that are not on
disk (decided by the dispatching session, 2026-10-22: a temporary copy of
the project and its family, or a layer under 4.0's file reads, would cost
a copy of every store on a repository of this size, or a change to every
reader, for findings `tcw validate` gives anyway):

- **Before writing, file by file.** Each planned configuration, manifest
  and state file is given, as text, to the 4.0 function that parses that
  one kind of file (TCW-106 Design 5, TCW-107 Design 1, TCW-108 Design 1-3,
  TCW-109, TCW-110 Design 7, TCW-111 Design 1); a refusal is B3. The
  planned parent links of the family, the active project's planned ones and
  each related project's actual or predicted ones (Design 6.1), are given
  in memory to TCW-108's load-order rule; a loop is B4 and a fallback D8.
  None of this reads the planned files from disk.
- **After the local phases, the whole project.** A real run that has
  finished phase E runs 4.0's `tcw validate` checks on the project as now
  written, offline (`remote` off, so this check never contacts Jira), and
  lists each finding as Design 2.9's A12 defines. With `--no-jira`, in a
  project whose work is kept in Jira, the work-store checks are left out
  and the summary says so (Design 1.1). That is because they open the Jira
  backend. A dry run
  says that these findings are known only after a real run. Nothing is
  undone because of them: each is a finding 4.0 gives anyway, and B3 has
  already refused every file 4.0 could not read.

2.2. **A blocker refuses the whole run.** If the plan holds any blocker, the
run prints every change it would have made, every report and every
blocker, writes nothing, edits no ticket, and exits 3. The person fixes the
blockers, in 3.x or by hand, and runs it again.

2.3. **`--dry-run`, and Jira while planning.** A dry run prints the plan
and changes nothing: no file, no folder, no ticket. Without `--no-jira` it
searches Jira to list the tickets it would edit (Design 5.1), and edits
none.

When the plan's Jira requests fail (Design 2.1), what happens depends on
the kind of run, and the code is the backend's (Design 1.6):

| Run | Jira fails while planning |
| --- | --- |
| real | nothing is written and no ticket edited; it prints the local changes it would have made, the Jira error, and `nothing was written; 'tcw migrate --no-jira' converts the files without Jira`; exit 5 or 1 |
| `--dry-run` | it lists the local changes, says the tickets could not be listed, and exits 5 or 1 |
| either, with `--no-jira` | Jira is never contacted, so it cannot fail |

Decided by the dispatching session, 2026-10-22: a real run that cannot
plan the Jira half writes nothing, rather than writing the files and
stopping at phase F, because from phase D on 4.0's `tcw work list` hides
every ticket still holding a 3.x value (Design 5.3), and a person who
wants that state anyway asks for it with `--no-jira`.

2.4. **The order of writes** is fixed. Each phase uses only what is
recorded in the progress record (2.7) or is still on disk when it starts:

| Phase | What | Why here |
| --- | --- | --- |
| A | write, in this order, `.tcw/tcw-migration.yaml` (Design 7), then (inside a git repository) the line `/tcw-migration-progress.yaml` in `.tcw/.gitignore`, then the progress record `.tcw/tcw-migration-progress.yaml` (2.7) | the record keeps every `cap-…` id and removed value before any is removed; the progress record keeps every decision a later phase destroys the input of; the ignore line comes before the file it ignores, so the progress record, which holds personal values, is never on disk unignored |
| B | move folders and files: overrides to their original's path (C14), then loose entries into `resources/` (C13) | a move is the one write that changes where later writes go, so every move comes before any file is written at its final place |
| C | write each 4.0 state file, once, at its final place, with every edit of C9 to C12, C14 and C16 in that one write (the `cap-…` id removal included), then delete its 3.x state file; write every other changed store file (C13's mentions, C16's links and `capabilities.yaml` entries, C12's new `description.md`) | every input was read while planning and is in the progress record |
| D | write `.tcw/tcw-config.yaml`, `.tcw/tcw-config.local.yaml`, the manifests and the rest of `.tcw/.gitignore` (C1 to C8) | from here the project is 4.0 (`find_marker` reports `.tcw/tcw-config.yaml` first, `tcw/project_files.py:106-111`), so it comes after every store change |
| E | delete the root `tcw-config.yaml` and `tcw-config.local.yaml`, then delete the progress record | only once their `.tcw/` copies are written and equal the planned content |
| F | edit the Jira tickets (C17), unless `--no-jira` | last, as the design requires (design.md:717-720) |

Writing each state file once is what makes a stop inside phase C
harmless: there is never a moment when a 4.0 state file exists in a form
other than its final one. The first draft removed the `cap-…` ids in a
separate write at the end of phase C; that bought nothing, since C14 uses
the *sources'* ids, never the project's own (a pointer to one of the
project's own is B9), and the project's own are recorded in phase A.

The progress record is deleted at the end of phase E, not after phase F,
because phase F needs nothing from it: which tickets are left is read
from Jira again by the next run (Design 5.2), and their new values follow
from the active project's ID alone.

2.5. **Each write is whole.** A file is written atomically. Renaming a
state file (`meta.yaml` to `tcw-capability.yaml`) writes the new file,
reads it back, and only then deletes the old one. A folder or file that
moves (C13, C14) is moved by one rename. **A move whose source and target
are on different filesystems is refused, not copied**: when the rename
fails with the cross-device error, the run stops before that move, exits
1, and says `<old> and <new> are on different filesystems; tcw migrate does
not copy across them: move it by hand, keeping its contents, then run 'tcw
migrate' again`. The progress record already finishes that: the next run
finds the move done when the old path is gone and the new one holds the
recorded files with their digests (Design 2.7). Decided by the dispatching
session, 2026-10-22 (the plan review's D1): C13's moves stay inside one
object folder and C14's inside one store, so the error can only come from
a mount point inside a store; a copy, compare and delete path for that case
needed a stop point of its own and still lost track of a partial copy or a
half-deleted source. A
**write**, wherever this spec counts them (criterion 11), is one of: a file
written, a file or folder renamed or moved, a file deleted, a ticket
edited.

2.6. **Never repeats a change.** Every conversion looks for a 3.x form and
writes its 4.0 form; a 4.0 form is never converted again. It is still
**read**: the objects of a store are those in either form, 3.x state files
and 4.0 ones alike (Design 4.1), so that the owner of a reference and
whether a path is taken are decided over everything the store holds. A
run after a finished one finds nothing to convert, prints
`nothing to migrate`, writes nothing, edits no ticket (Design 5.2 skips a
ticket already in 4.0 form), and exits 0. For a project whose work is kept
in Jira, knowing that no ticket is left needs the search of Design 5.1:
offline, such a run prints `nothing to migrate in the files; the tickets
could not be checked` and exits 5 or 1 (Design 1.6); with `--no-jira` it
prints `nothing to migrate in the files; tickets not checked (--no-jira)`
and exits 0.

2.7. **A run that stops partway is finished by running it again.**

**The progress record.** Phase A writes `.tcw/tcw-migration-progress.yaml`:
the whole plan's local steps, in order, each with what a later run needs
to finish it without working anything out again from a disk that the
earlier phases have changed:

- every move, with its old and new path (C13, C14), and for a folder the
  list of files it holds with each one's SHA-256 digest;
- every file write, with its final path, the digest of the bytes the plan
  read (or `absent` for a new file), and the bytes to write;
- every deletion, with the path, the SHA-256 digest of the file it deletes
  as the plan read it, and the 4.0 file it waits for with that file's
  digest (the progress record's own deletion at the end of phase E is the
  one exception: it is the run's own file);
- the owner each converted reference was given (C16) and the id-path each
  override pointer was resolved to (C14), so that the record says why
  every planned byte is what it is.

It holds personal values (the planned `.tcw/tcw-config.local.yaml` and
personal manifest), so inside a git repository it is ignored from phase A
on, and a stopped run's message says `do not save these files in version
control until 'tcw migrate' finishes`. That wording keeps the meaning of
"do not commit" while passing TCW-73's guard against git words in
messages (Design 8.6). It is deleted at the end of phase E. Its size is
about the size of the files it rewrites. It also records the active
project's ID and whether its work is kept in Jira or in files. A run that
follows it then decides about the Jira half from the record, the same way
the first run did, without reading a configuration that phases D and E may
have changed.

**A run that finds a progress record** does not plan again. It walks the
recorded steps in order. A step whose result is already on disk (the file
holds the bytes to write; the moved path is at its new place, holding the
recorded files with their digests, and gone from the old; the deleted file
is gone) is skipped. A step not yet done is done
when what it reads is still as recorded (the file's digest matches, or the
file is still absent; the source of a move is present with its recorded
digests and its target absent; the file to delete still has its recorded
digest and the 4.0 file it waits for holds its recorded digest). If it is
not, the run stops before that step with blocker B17, naming the file and
saying: restore it as it was, or restore the project from version control,
delete `.tcw/tcw-migration-progress.yaml`, and run again. So a hand edit
made between a stopped run and its re-run, to a 3.x file the plan meant to
delete, stops the run instead of being deleted with the file (decided by
the dispatching session, 2026-10-22: the plan review's M3; without the
deleted file's own digest, a stop at P7 followed by an edit of that
`meta.yaml` lost the edit silently). Phases D and E follow the same rule.

**The Jira half of a run that follows a progress record** is planned
before the run follows the record, by the same function a fresh run uses
(Design 1.1). That function makes the same requests through the same
read-only wrapper (Design 2.1), and runs the same B16 check. It is
skipped with `--no-jira`, and for a project whose work is kept in files,
as the progress record says (above). Its tickets need only the project's
ID and its own Jira settings (Design 5.1, 5.2), and both read the same
whether the files are 3.x, 4.0 or halfway. A Jira failure or a B16 at
that point is handled as in Design 2.3 and 2.2. Nothing more is written
and no ticket is edited, and the message names the progress record:
`nothing more was written; 'tcw migrate --no-jira' finishes the files
without Jira`. The run exits with the backend's code, or 3 for B16. Once
the record's steps are done, phase F edits the tickets planned.
`--dry-run` with a progress record present lists the steps still to do
and, unless `--no-jira`, the ticket edits planned, and changes nothing.
Decided by the dispatching session, 2026-10-22, the re-check's N2: one
function at one point in the run, for both kinds of run, so that the
`--no-jira` guard covers both. Planning before any write also keeps "a
failure while planning writes nothing" true for a re-run. The cost is
small: with Jira down, a stopped run is finished with `--no-jira`, which
the message names, just as a fresh run is.

When a step fails, the run stops there and prints what it did, what it did
not do, and `run 'tcw migrate' again to finish`, exiting 1 (or the Jira
code of Design 1.6 when the failure is in phase F). A failure of the
operating system (a refused permission, a full disk) is such a failure:
migration turns it into this message itself, rather than letting it reach
the one-line error every other command prints for an `OSError`
(`_dispatch`, `tcw/cli.py:494-498` at `5a9ca9b7`), which would lose the
instruction to run again.

**Every point where a run can stop**, and what finishes it:

| # | Stop point | What the next run does | Criterion |
| --- | --- | --- | --- |
| P1 | before any write | plans from the start (no progress record) | 11 |
| P2 | phase A, the record (and the ignore line) written, the progress record not | plans from the start; the record's entries and the ignore line are rewritten only if their content differs | 11, 60 |
| P3 | phase A finished | follows the progress record from phase B | 11, 60 |
| P4 | phase B, an override's folder moved, its `overrides:` key still in its state file | the move is done (old path gone, new path present); phase C writes the state file without the key. Not B9: the target holds the very object the record moved there | 61 |
| P5 | phase B, a move refused because its source and target are on different filesystems (Design 2.5) | when the person has moved it by hand, finds the move done and goes on; when not, refuses it again the same way | 60 |
| P6 | phase B, a loose file moved into `resources/`, its `prependedDocs` entry and mentions not yet rewritten | the move is done; phase C writes the entry and mentions from the recorded bytes, which no longer depend on finding the loose file | 60 |
| P7 | phase C, a 4.0 state file written, its 3.x one not yet deleted | the write is done (the bytes match); the deletion is done next, when the 3.x file still has its recorded digest; changed by hand meanwhile, B17 | 60 |
| P8 | phase C, some state files converted and some not | follows the record; the converted ones are skipped, and every owner was decided while planning | 11, 60 |
| P9 | phase D, `.tcw/tcw-config.yaml` written, the manifests or personal file not yet | the project is now 4.0 by its marker; `tcw migrate` still finds the progress record and writes the rest | 60 |
| P10 | phase E, between the two root deletions, or before the progress record is deleted | deletes what is left; then phase F | 11 |
| P11 | phase F, some tickets edited | no progress record: plans again, finds no local change, edits the tickets still holding a 3.x value | 12 |
| P12 | a run made with `--no-jira` finished | as P11 | 57 |

**Both files present without a progress record.** The progress record
handles every pair of files a stopped migration leaves, so this rule is
only for pairs migration did not make: this repository's root and `.tcw/`
configuration pair (Design 9.4), a project someone part-converted by hand,
or a branch merged after the migration that brought back a `meta.yaml`
beside a `tcw-capability.yaml`. When a 3.x file and its 4.0 counterpart
both exist (`meta.yaml` and a `tcw-` state file in one folder;
`tcw-config.yaml` at the root and `.tcw/tcw-config.yaml`; the two personal
files), the run compares the **parsed values** of the 4.0 file, without its
`tcw-version`, with the parsed values that converting the 3.x file gives.
Equal: the 4.0 file is kept as it stands, comments included, and the 3.x
file is deleted (in phase C or E). Different: blocker B11, naming both
files and the first key that differs; migration never chooses between two
versions of one record. Parsed values, not text, because what holds this
repository's pair equal is `tests/test_repo_config_pair.py`, which compares
parsed values (`_as_3x_keys(without_version(new)) == old`, `:33-40`): the
test allows the two files to differ in comments or layout, so a text
comparison could stop with B11 on a pair the test accepts. (At `ebce3fd6`
the two files differ only in the version line and `not-tags`.)

2.8. **Nothing is lost.**

- **Text is edited, not regenerated.** A converted YAML file keeps every
  line the conversion does not touch byte for byte: comments, blank
  lines, key order, quoting, and YAML anchors (a name given to a value,
  `&name`, and reused elsewhere, `*name`, as this repository's
  configuration does). A conversion that replaces a whole block (a
  `projects:` mapping, an `extends` list) writes the new block in TCW's
  usual style and reports a comment it drops from inside the old block. A
  replaced block that defines an anchor used outside it is blocker B12.
  The plan reuses the editor TCW already has for this,
  `tcw/store/config_edit.py`, which splices each edit into the original
  text at the positions the YAML parser gives, checks every edit, and
  refuses (`ConfigEditRefused`, `:47`) an edit that would lose a comment or
  touch an anchor used elsewhere; it is extended to state files. B12 is
  that existing refusal, named, not a new rule.
- **Moved files keep their bytes.** C13 and C14 move files without
  changing them; only `prependedDocs` and `appendedDocs` entries pointing
  at them are rewritten.
- **The only deletions** are a 3.x file whose 4.0 copy has been written
  and read back (Design 2.5, 2.7), the old location of a moved file or
  folder, and the progress record once its run's phase E is done.
- **A value with no 4.0 home is recorded** in `.tcw/tcw-migration.yaml`
  (Design 7) before it is removed: every `cap-…` id with its id-path, every
  override's move, and every `jira` block of a `projects:` entry. Every
  other removed value is
  written in its 4.0 form elsewhere (an `extends` as a parent link, an
  `overrides:` pointer as the folder's new path, a locator as a manifest
  entry).

2.9. **What a run can find, besides conversions.**

**Blockers** stop the run (Design 2.2). Each line names the file, key or
folder, says why, and says what to do.

| # | Blocker | Why it cannot be converted |
| --- | --- | --- |
| B1 | a configuration key 4.0 refuses that has no known 4.0 name (`key_problems`, `tcw/project_files.py:182`; the one rename known is `not_tags`, `_RENAMED_KEYS`, `:55`) | renaming it would be a guess |
| B2 | `connected-projects`, the 2.x name of `projects` (`RETIRED_PROJECTS_KEY`, `tcw/store/base.py:470`) | a 2.x file; 3.x refuses it too (`retired_key_problem`, `:474-481`); out of scope |
| B3 | a planned configuration or manifest file that 4.0's readers refuse (Design 2.1), for example a `repository` URL containing `#` (S107 Design 1.5) or a locator that does not end with the `repository.path` it declares (S107 Design 1.6) | 4.0 could not read the result |
| B4 | an `extends` whose conversion makes a loop: two projects extending each other, or a project extending a descendant that is not its own listed child (E5) | 4.0 has no form for it (P108:936-940) |
| B5 | a related project whose content a conversion must read is not on this machine: to tell E1 from E4 (whether it is already an ancestor, through which links), to resolve an override pointer into it (C14), or to find the owner of a bare reference among the sources (C16). E2 and E3 are decided from the active project's own file and need no other project (Design 6.5). In part 1 of the build order, also any 3.x form only part 2 converts | the conversion would have to guess what it holds |
| B6 | an absolute or `~` store location that lies inside no TCW project (C5) | 4.0's shared file accepts only a relative path or a `.path` address (S110 Design 7.1) |
| B7 | two stores that are the same folder or one inside the other: two of the project's own, or one of its own and one of a related project's (S110 Design 7.4) | migrating either would convert the other's objects as its own |
| B8 | an object whose folder name breaks the grammar (S110 Design 1.1), is a reserved name (S111 Design 2.4), or whose full identifier would be over 255 characters (S111 Design 4.2) | it cannot be named, so references to it cannot be written; renaming it is the person's choice |
| B9 | an `overrides:` pointer that names nothing, names more than one capability, names one of the project's own, or whose target path is taken by another object; two overrides of one original; or a pointer resolved through a source's record to an id-path that source no longer has (C14, Design 7). The message gives the fix by hand: move the folder to the original's path and delete the key, as TCW-112's own message does (S112:877-884) | the design says to report rather than guess (design.md:741-744) |
| B10 | a stored reference 3.x gives no single owner: one 3.x reads as ambiguous (`AmbiguousRef`, `tcw/store/fs.py:2439`, and for taxonomy `:1816`; `route_capability_path`'s refusal, `tcw/work/gates.py:364-371`), or a `capabilities.yaml` entry `route_capability_path` answers with a problem instead of a ledger: the project keeps no capabilities ledger and the entry names no child (`:377-380` at `v3.0.2`), or it names a child but no capability (`:358-359`). The "no capabilities ledger" form needs no related project, so part 1 gives it | its owner would be a guess |
| B11 | a 3.x file and its 4.0 counterpart both present and different (Design 2.7) | which one is right is the person's decision |
| B12 | a replaced YAML block that defines an anchor used outside it (Design 2.8) | the rest of the file would lose the value |
| B13 | the shared manifest's path `../<name>` chosen by M5 already holds something other than the project | the entry would point at the wrong folder |
| B14 | a 3.x file that cannot be read (bad YAML, not a mapping, a duplicate key) | its content is unknown |
| B15 | a project with no `id` (an empty `.tcw/tcw-config.yaml` and no root file to supply one, or a root file without `id`) | full identifiers need it |
| B16 | a ticket to be edited whose edit screen does not offer the `TCW Item` field (Design 2.1) | phase F would fail on every ticket after the files were already 4.0 |
| B17 | a run following a progress record finds a file to write, a file to delete, the 4.0 file a deletion waits for, or a move's source, not as the record says (Design 2.7) | the recorded bytes were planned from the old content; writing them, or deleting the file, would lose a change |

**Needs attention** (reported; 4.0 reads the project, and `tcw validate`
or a later command would say the same):

| # | Report |
| --- | --- |
| A1 | a hand-written `id:` in a taxonomy or work state file that differs from its folder's name (S111 Design 1.3, row k; P111:1483-1489) |
| A2 | a file under a `resources/` folder named like a state file (`tcw-*.yaml`, `meta.yaml`, `item.yaml`), which makes `rm` refuse (S111 Design 2.5) |
| A3 | a mention of a file moved by C13 that C13 does not rewrite, in a Markdown or YAML file of the project's own stores: the text `/<file>` preceded by the object's folder name in full, or by a leading part of it that ends in `-` and is followed by `…` or `...` (for example `TCW-99-…/design.md`), anywhere other than an exact mention C13 rewrote. Files outside the stores are not searched (S-10), and a ticket's text is not read (Non-goals) |
| A4 | a root `.gitignore` line `/tcw-config.local.yaml`, now ignoring nothing (S106:442-444); the root `.gitignore` is not TCW's file, so it is left as written |
| A5 | `not_tags` in the user-wide personal file, which 4.0 refuses (S106 Design 5.5), with the line to change; the file is shared with any 3.x TCW on the machine, which needs the 3.x spelling, so migration does not change it |
| A6 | a project fetched by 3.x into its per-machine cache: when the clone is not on this machine, where `tcw project provision` will now fetch it (M5); when it is, that the personal manifest now points into a cache folder, which cleaning tools may empty, and that moving the clone to the `../<name>` folder the shared manifest names and deleting the personal entry keeps it safe |
| A7 | in a linked git worktree, a 3.x personal file in the main checkout, which this run does not touch (Design 6.6); its message names only the main checkout and `tcw migrate` there (Design 8.6) |
| A8 | a related project still in 3.x form, with `tcw -C <its folder> migrate` (Design 2.10) |
| A9 | a credential variable name (`work.jira.credentials.*`, or a `projects:` entry's `jira` block) that starts with `TCW_` and contains `__`, which 4.0 reads as an override (S109 Design 4.2) |
| A10 | a ticket of this project whose `TCW Item` is neither a 3.x nor a 4.0 value of this project, or whose 4.0 value would be over 255 characters (Design 5.2) |
| A11 | `TCW_PROJECT_<ID>` set while migrating; manifest entries are decided from the declared locations, not from the variable (M6) |
| A12 | a finding 4.0's `tcw validate` gives on the project after the local phases (Design 2.1) that the project already had in 3.x: a finding whose counterpart 3.x's own `tcw validate` gave before the run (the same file or object, the same kind of problem), such as a capability with no `Status`; passed on as 4.0 words it. A real run lists them; a dry run cannot. The run cannot run 3.x's validate, so it lists as A12 every finding that is not the finding another report of the run predicts (each report names the 4.0 finding it predicts, by file and kind; a finding in the same file but of another kind is not absorbed by it). Whether every listed A12 really has a 3.x counterpart is what criterion 51 checks, against 3.x's recorded `tcw validate` output for each fixture: a finding a conversion caused fails it |
| A13 | a command bound in the configuration (a stage's `pre` or `post`, a hook, a procedure's `command:`) whose text names a command or flag 4.0 removes: `tcw provision`, `tcw projects`, `tcw init`, `--project`, `--blocks` (S115 Design 1.2; TCW-114); the binding is left as written, and the line is named |

**Reads differently in TCW 4** (reported, for the person to review; the
design asks for each to be printed, design.md:727-730, :737-740):

| # | Report |
| --- | --- |
| D1 | what a converted parent link now passes down that 3.x did not: the projects and axes newly inherited, and the configuration keys (`work.tags`, `work.jira`, S109 Design 1.1) a parent sets and this project does not |
| D2 | each of the project's own taxonomy entries or capabilities at an id-path an ancestor also has, which in 4.0 overrides it and merges with it field by field (TCW-112) |
| D3 | each 3.x override that lists no `prependedDocs` or `appendedDocs` while its original does, since its body now includes the original's (S112:1566-1570) |
| D4 | each override in a middle project, which 3.x did not apply below it and 4.0 does (P112:292-305, choice 8) |
| D5 | a `null` at `work.tags`, `work.jira` or a key below them in the shared file, which now removes an inherited value (S109 Design 2.5) |
| D6 | each link dropped by inverting an `extends` (E3), and each `jira` block dropped (C6) |
| D7 | each state file, `name` or empty `description.md` written where 3.x had none (C11, C12) |
| D8 | a load order for which C3 finds no consistent order, so 4.0 falls back and warns (design.md:427-443) |

2.10. **The summary** of every run says how many files and tickets were
changed (or would be), lists the files left in another repository (Design
1.4), and lists every related project found on this machine that is still
in 3.x form, each with `tcw -C <folder> migrate`, parents first (Design
6.2). With `--no-jira` it says what the Jira step would do and, for a
project whose work is kept in Jira, that the work store was not checked
after the run (Design 1.1).

2.11. **A second person or machine.** After one person has migrated and
committed, another who pulls has a 4.0 project whose tracked files are
converted and whose untracked ones may not be: a root
`tcw-config.local.yaml`, and the per-machine paths of C4 (M4, M5). Their
`tcw migrate` converts exactly those and writes their
`.tcw/tcw-manifest.local.yaml`. It changes a tracked file only where one
is still in 3.x form, and edits only the tickets still holding a 3.x value:
none, when the first person's run finished phase F; all of them, when the
first person ran with `--no-jira`, as this repository's own migration does
(Design 9.3). A store in a cache clone that is still 3.x on this machine is
the same: converting it changes files in that clone, listed as left in
another repository (Design 1.4).

**Branches merged after the migration** bring 3.x files back into a 4.0
tree. `tcw migrate` run after such a merge converts what the branch brought,
resolving its references over the store's objects in either form (Design
2.6), and treats a 3.x state file beside a 4.0 one by the both-files rule
(Design 2.7).

### 3. The configuration

C1. **The configuration moves into `.tcw/`.** The root `tcw-config.yaml`
becomes `.tcw/tcw-config.yaml`, and the root `tcw-config.local.yaml`
becomes `.tcw/tcw-config.local.yaml`, each with
`tcw-version: <running version>` as its first line (S106 Design 3.1-3.3).
Paths inside need no rewriting: they keep their meaning relative to the
project's root (S106:124-140). `.tcw/.gitignore` gets the lines
`/tcw-config.local.yaml` and `/tcw-manifest.local.yaml` as TCW-106 and
TCW-107 write them (`ignore_personal_file`, `tcw/store/fs.py:225`;
S107 Design 1.9), only inside a git repository, beside the line
`/tcw-migration-progress.yaml` that phase A wrote (Design 2.4), which stays
for any later run.

**Empty files** (TCW-106's review, S2). An empty `.tcw/` file (0 bytes,
or YAML that reads as nothing) stays refused by every other command, as
any file with no `tcw-version` is: the design's rule that a file with no
version is a 3.x file (design.md:698) has no exception, and an exemption
would make an accidental empty file a valid configuration with no `id`.
`tcw migrate` treats such a file as not yet written: an empty
`.tcw/tcw-config.local.yaml` gets its version line (an empty personal file
sets nothing); an empty `.tcw/tcw-config.yaml` gets the converted root file
when there is one, and is blocker B15 when there is not.

C2. **Keys renamed.** `not_tags` becomes `not-tags` wherever it is a key
(`_RENAMED_KEYS`, `tcw/project_files.py:55`). Any other key 4.0 refuses is
B1.

C3. **`projects:` becomes `parents:` and `children:`** in
`.tcw/tcw-config.yaml` (S108 Design 1.1, 2.1; the mapping, S108:1454-1464):

- `projects.parent.<id>` becomes `parents: [<id>]`: a plain ID, so it
  passes everything down (`inherit: all`, S108:220-238), as the design and
  TCW-108 say. What now flows down that 3.x did not is D1. 3.x refuses more
  than one parent (`tcw/store/project.py:628-629`); a file that has several
  anyway converts them in the order written.
- `projects.children.<id>` becomes an entry of `children:`, in the shared
  file, as 3.x's personal files could not set `projects`
  (`PERSONAL_KEYS`, `tcw/config.py:44-51`).
- `projects.upstream.<id>` becomes a parent `{id: <id>, inherit: <axes>}`,
  where `<axes>` are the axes whose `extends` names it (`taxonomy`,
  `capabilities`), or `none` when no `extends` does (design.md:737-740).
- Each entry's location becomes a manifest entry (C4), and its `jira`
  block is dropped (C6).
- The `projects:` key is removed. A parent or child dropped by E3 is not
  written.

C4. **Manifest entries.** For each project C3, C5 or E4 names, the 3.x
entry's location becomes an entry of `.tcw/tcw-manifest.yaml` (shared) or
`.tcw/tcw-manifest.local.yaml` (personal), in TCW-107's format
(S107 Design 1.2-1.6), by TCW-107's mapping (S107:1097-1106):

| # | 3.x | 4.0 |
| --- | --- | --- |
| M1 | a locator: a string, or `path:` | shared `path`, written as the 3.x text when relative; when absolute or `~`, which a shared manifest refuses (S107 Design 1.4), the personal manifest gets it and the shared entry gets M5's path |
| M2 | `repository.url` and `repository.ref` | `repository: <url>` or `<url>#<ref>`; a URL holding `#` is B3 |
| M3 | `repository.path` (the folder within the repository) | `subfolder`; the entry's `path` must end with it (S107 Design 1.6), else B3 |
| M4 | `repository.checkout`, with no locator | relative: the shared `path` (with `subfolder` appended); absolute or `~`: the personal `path`, and the shared entry gets M5's path |
| M5 | a `repository` and no locator or `checkout`: 3.x cloned it into its per-machine cache (`checkout_root` and `provisioned_root`, `tcw/store/checkouts.py:95-127`) | shared `path: ../<name>`, where `<name>` is the URL's last part without `.git`, with `subfolder` appended; B13 if that folder holds something else. When the cache clone is on this machine and holds the project, the personal manifest gets its absolute folder (an entry in the active project's own manifest is trusted wherever it points, S115 Design 7.8), so the clone is found and not fetched again; when it is not, A6 |
| M6 | an entry 4.0 would find anyway | no entry, when the project declares no `repository` and 4.0's lookup from the active project would find the same folder 3.x resolved, using only the active project's own manifests and the search of S107 Design 2.4 (folders next to the project's root) and 2.5 (folders enclosing it). An entry with a `repository` is always written, since otherwise the repository would be lost |

M6 deliberately does not consult a parent's manifests (S107 Design 2.2
would), because whether a parent has been migrated yet would then change
this project's result (Design 6.1). `TCW_PROJECT_<ID>` is left out of the
comparison (A11); 4.0 still honours it (S107 Design 2.1).

C5. **Store locations** (`taxonomy.path`, `capabilities.path`, `work.path`),
so that each passes S110 Design 7.1:

- a relative path inside the project: unchanged;
- a relative path leading out of the project (`..`), naming a folder inside
  a TCW project W that 4.0 would locate from here (C4 included) at the same
  folder: `tcw://W.path/<rest>` (S110 Design 2.1, 7.2), so that it no longer
  depends on how the checkouts sit on disk (S110:722-728); otherwise it is
  kept, as 4.0 accepts it;
- an absolute or `~` path inside the active project: the relative path;
  inside another TCW project W: `tcw://W.path/<rest>`, with a personal
  manifest entry for W at its absolute folder unless C4 or the search finds
  it; inside no TCW project: B6;
- a store's `repository` declaration is kept unchanged, since 4.0 as built
  still reads it and provisions from it: TCW-107 keeps the stores' 3.x
  declarations (S107:150-152) and TCW-115 provisions stores exactly as
  `run_provision` does today (S115 Design 7.2). This departs from the
  design, which moves a store's repository into a manifest entry
  (design.md:745-749), and from the request's "store `path` plus
  `repository` to one location". TCW-110 left the move to TCW-107, TCW-115
  and this item (S110:160-162); neither sibling made it, and this item
  does not either (Notes, decision 4), and raises it on TCW-99.

Every converted location must name the same folder, on this machine, as
3.x resolved (`resolve_store`, `tcw/store/fs.py:3182-3318`).

C6. **`jira` blocks of `projects:` entries are dropped,** each reported (D6)
and recorded (Design 7): they served filing into another project, which 4.0
removes (S108:466-469; design.md:594-597). Their credential names are
checked by A9 first.

C7. **The user-wide personal file** is not converted (A5).

C8. **`extends` becomes parent links,** and `taxonomy.extends` and
`capabilities.extends` are deleted, with the `taxonomy:` or `capabilities:`
section when nothing else is left in it (S112 Design 1.5; design.md:724-732).
For each axis X and each project T an `extends` names, in this order:

| # | When | Conversion |
| --- | --- | --- |
| E1 | T is already an ancestor through the converted parent links, and every link on the way passes X | nothing (design.md:730-732); reported as "already inherited" |
| E2 | T is an upstream (C3) | X is added to T's parent entry's `inherit` |
| E3 | T is a child the project lists (`projects.children`) | inverted (S108:1458-1461): T becomes a parent `{id: T, inherit: [X]}`, the project no longer lists T as a child, and T, when it is migrated, no longer lists the project as a parent (Design 6.1); D6 |
| E4 | anything else (a sibling, a cousin, an ancestor whose links do not pass X, a project connected only through another) | T becomes one more parent `{id: T, inherit: [X]}`, or X is added to an entry made for T already. A new parent is appended after the existing ones (P108:403-406), except that one which is an ancestor of an existing parent is put before the first such parent, so that C3 keeps its order (design.md:435-437) |
| E5 | the result would be a loop, or T is a descendant of the project that is not its own listed child | B4 |

To classify T, migration reads the related projects' configurations
(Design 6.1); a related project it needs that is not on this machine is
B5.

**TCW-109's checks** apply to the planned configuration: A9 for credential names, D5 for a
`null` that now removes an inherited value.

### 4. The stores

4.1. **Which objects.** Every object 3.x lists becomes an object at the
same id-path, and nothing 3.x does not list becomes one: in taxonomy, every
folder of the store (`_local_slugs`, `tcw/store/fs.py:1763-1769`); in
capabilities, every folder holding `meta.yaml` (`_is_capability`,
`:2255-2256`), an override included; in work, every folder of the work
store holding `item.yaml`, in both backends. Work items are found by their
folders, never by the backend's listing: the Jira backend's `list` is a
Jira search that drops a ticket whose folder is not here
(`tcw/work/jira/backend.py:433-483`), and would list nothing offline, while
its folders are on disk (`is_item_folder`, `:311-312`; the folder's
`item.yaml` holds `ticket:`). A 3.x capability group folder with no
`meta.yaml` stays an organising folder (S111 Design 2.3). Each object's
id-path is its 3.x identity (S110 Design 1.3).

**The objects already in 4.0 form** (a folder holding a `tcw-` state file,
S111 Design 1.1) are read with the rest (Design 2.6): they are not
converted, but they count for every rule that asks whether the project has
an object (C11's enclosing object, C14's taken target, C16's owner).

C9. **State files are renamed** (S111 Design 1.1-1.2): `meta.yaml` to
`tcw-taxonomy.yaml` or `tcw-capability.yaml`, and `item.yaml` to
`tcw-work-item.yaml`, in both work backends, with
`tcw-version: <running version>` as the first line and the rest of the file
kept byte for byte, except the edits of C10, C11 and C16.

C10. **Ids.** Each `id: cap-…` is recorded with its id-path in
`.tcw/tcw-migration.yaml` (phase A) and removed in the one write of its
state file in phase C (S111:1286-1287; S112 Design 5.3; Design 2.4 says why
not later). An `id:` that equals its
folder's name is kept. Any other `id:` in a taxonomy or work state file is
A1.

C11. **`parent:` for nested objects.** A taxonomy entry or capability whose
folder sits inside another object's folder gets
`parent: <project>.<namespace>/<that object's id-path>` (S111 Design 3.1),
so that 4.0 does not warn that its folder and its `parent:` disagree
(S111:1216-1218). A taxonomy folder with no `meta.yaml`, a term in 3.x,
gets a state file (S111:1213-1215); D7.

C12. **Completing objects that override nothing** (S112 Design 6.1). A
taxonomy entry or capability that overrides nothing in 4.0 and lacks a
`name` gets `name:` from its folder's name (3.x's fallback), and one that
lacks `description.md` gets an empty one; D7. A capability with no
`Status` is not completed: 3.x requires one (`check` reports "missing Status", `tcw/store/fs.py:2829`), so a project 3.x
validates has none missing; one missing anyway is reported by 4.0's
`tcw validate` and listed by the run as A12.

C13. **Loose entries go into `resources/`** (S111 Design 2.2). Every file or
folder in an object's folder that 4.0 would report as out of place (S111
Design 2.6 rows a and b: not a fixed file or folder of S111 Design 2.1, and
not a child object's folder) moves into that object's `resources/`,
keeping its name and its contents. In a capability, each
`prependedDocs` or `appendedDocs` entry naming a moved file becomes
`resources/<entry>` (S111:324-327). A mention of a moved file's old path is
rewritten where it is exact and inside the project's own stores: a
relative Markdown link from within the same object folder, and the text
`<store path>/<id-path>/<file>`, which becomes
`<store path>/<id-path>/resources/<file>`. Every other mention is A3.

C14. **Overrides move to their original's path** (S112:1788-1796, as revised
by P112:1887-1896; design.md:741-744). For each capability with an
`overrides:` pointer, bare `<cap-id>` or `<alias>/<cap-id>`:

1. Resolve the pointer the way 3.x matched it (`_apply_override`,
   `tcw/store/fs.py:2352`): among the projects the 3.x `capabilities.extends`
   names (only the one named `<alias>` when there is one), find the
   capability whose id is `<cap-id>`. A source still in 3.x form is read for
   the id in its state files; a source already migrated is read in its
   `.tcw/tcw-migration.yaml` (Design 7), and the id-path found there must
   exist in the source now (B9 otherwise).
2. The target is that capability's id-path. It is never derived from the
   override's own folder name, which 3.x did not use (P112:967-971).
3. Move the override's folder to the target, with everything in it
   (phase B), and write its state file there without the `overrides:` key
   (phase C, Design 2.4); C9 and C13 apply to it at its new place.
   References to its old id-path are rewritten (C16). An override whose
   folder is already at its original's id-path does not move; only its key
   is removed. It is not B9: the target holds this object itself. A
   folder that 3.x used only to hold overrides (an `<alias>/` folder,
   S110:1056-1059) may be left empty by the moves; it is left in place,
   since it holds no file and git does not record an empty folder.
4. B9 when the pointer resolves to nothing, to more than one capability,
   or to one of the project's own; when the target id-path already holds
   another of the project's objects (design.md:743-744); and when two
   overrides resolve to one original.
5. D3 and D4 are reported for it.

C15. **Taxonomy has no pointer.** A term at the same path as an inherited
one was a separate term in 3.x ("bare-wins-local", S112:157-160); in 4.0 it
overrides the inherited one. Nothing moves; D2 reports it.

C16. **References are rewritten to full identifiers** (S110 Design 5.1-5.3),
in every field of S110 Design 5.1's table: a files-backend work item's
`parent` and `blocked-by`; every entry of an item's `capabilities.yaml`; a
term's `relatesTo` and `vocabulary`; a capability's `Subject`, `Feature`,
`Superseded by`, `Blocked by`, `Roles` and `When` (keeping `!` and the
`roles/` and `conditions/` id-paths); and every `](tcw://…)` link in a
Markdown file of the project's stores. A field holds the full identifier;
a link holds `tcw://` and the full identifier (S110 Design 2.6). Each 3.x
value gets the owner 3.x gives it:

- a work slug `<project>/<folder>` becomes `<project>.work/<folder>`;
- a taxonomy or capability path prefixed with an `extends` project's ID
  (`core/term`) becomes that project's identifier (`core.taxonomy/term`,
  S110 Design 1.4); a bare one is the project's own when it has the object,
  else the one inherited source that has it, as 3.x reads it
  (`tcw/store/fs.py:2425-2440`, and the taxonomy reader's equivalent);
  ambiguous is B10;
- a `capabilities.yaml` entry under `new:`, `changed:` or `removed:` is
  routed as `route_capability_path` routes it (`tcw/work/gates.py:331-380`):
  a first folder naming an `extends` project is that project's, one naming
  a listed child is the child's, anything else the project's own; an entry
  the router answers with a problem rather than a ledger is B10. An entry
  naming a capability that does not exist yet (a `new:` declaration) is
  converted by the same routing, since 3.x does not require it to exist.
  An entry under `taxonomy:` is a term, and is read as the records gate
  reads it, through the taxonomy store's `get` (`_LedgerReader.term`,
  `tcw/work/gates.py:430-437`): the project's own when it has the term, else
  the one inherited source that has it, ambiguous B10; a term that exists
  nowhere yet is the project's own;
- a link is read as 3.x reads it (`parse_tcw_uri` and `resolve_tcw_ref`,
  `tcw/refs.py:59`, `:84`), only where 3.x's link check reads it: outside
  fenced and inline code (`_strip_code`, `tcw/validate.py:70-72`, scanned at
  `:326-345`). An example inside code is left as written.

A reference to an object that C14 moved names its new id-path; a reference
to an object another, already migrated project moved names the new id-path
that project's record gives (Design 7, `moved:`). A dangling
reference (one 3.x `tcw validate` already reports) keeps its routing's
owner and is reported by 4.0's `tcw validate` as before.

4.2. **Name blockers** (B8) are found before anything is written: a folder
name that breaks S110 Design 1.1, a reserved name (S111 Design 2.4:
`resources` in every store, and `comments` and every stage name in work),
and a full identifier over 255 characters, for every object and organising
folder 4.1 finds. B7 is checked over the planned store locations.

### 5. Jira

5.1. **Which tickets.** For a project whose work is kept in Jira, one search
lists the tickets of its Jira project that carry a `TCW Item`, with no
status or other filter (`jql.item_query`, `tcw/work/jira/jql.py:38-56`, as
`list` uses it, `tcw/work/jira/backend.py:462-466`). Only those whose
`TCW Project` field is the active project's ID are considered, as `list`
keeps them (`:470`), so in a Jira project shared by several TCW projects
(UC-5) each project converts only its own. The search is paged as the
backend's searches are paged today, and the plan names the page size.

**Which Jira settings.** Phase F, and the search while planning, use the
`work.jira` of the active project's **own layers**, read raw from whichever
files hold them when the run plans, and merged by 3.x's layering rule
(`_merge` and `PERSONAL_KEYS`, copied from `v3.0.2`, Design 8.2), never
inherited from a parent:

| Layer | Read from |
| --- | --- |
| shared | the root `tcw-config.yaml` when there is one (3.x, or the both-files case of Design 2.7, where the two are equal or the run is B11); else `.tcw/tcw-config.yaml` |
| user-wide | `$XDG_CONFIG_HOME/tcw/config.yaml`, as it stands |
| personal | the root `tcw-config.local.yaml` when there is one (a 3.x personal file may set `work.jira.credentials.*` and no other Jira key, `PERSONAL_KEYS`, `tcw/config.py:44-51` at `v3.0.2`); else `.tcw/tcw-config.local.yaml` |

Only the `work.jira` part of each layer is read, and it is checked by the
Jira configuration parser (`parse_jira_config`); nothing else in those
files is parsed for this. So the same rule serves a project still in 3.x
form, and a project whose files are already 4.0: the re-run after a phase F
stop (P11), and the plain run after a `--no-jira` run (P12), which is this
repository's own path at TCW-118 (Design 9.3 step 6). A problem elsewhere
in a layer that 4.0's configuration loader would refuse (for example
`not_tags` in the user-wide file, A5, which 3.x accepts) does not stop the
Jira half, since that loader is not used. A `work.jira` that is missing a
key 3.x requires, or that the parser refuses, is a Jira failure while
planning (Design 2.3): nothing is written, exit 1, and the message names the
file and key and `--no-jira`. TCW-109's environment overrides are not
applied, as 3.x applied none. Decided by the dispatching session,
2026-10-22 (the plan review's M4): the first draft read the 3.x files only,
which phase E has deleted by the time P11 and P12 run; 4.0's own loader
was the other choice, but it refuses the whole configuration for a problem
unrelated to Jira (A5's `not_tags`), and would let a parent's value decide
which board a migrated project's tickets are on.

Its field ids come from `work.jira.fields` as
today (`metadata`, `tcw/work/jira/backend.py:248`, field ids at
`:280-296`). These are also the settings 4.0 uses for this project
afterwards, for the keys that decide which board and which fields its
tickets are found by: 3.x requires `site`, `project`, `credentials` and
`fields` (with `fields.project` and `fields.item`) in the project's
effective configuration (`REQUIRED`, `REQUIRED_FIELDS`,
`tcw/work/jira/config.py:34-37`), and 3.x configuration is not inherited,
so the project declares each of them in its own layers (its shared file,
the user-wide file or its personal file). In 4.0 the active project's
layers are merged last (S109 Design 2.1-2.2), so its own value of each
still wins over any parent's. The keys 3.x does not require (`fields.effort`,
`fields.complexity`, `priorities`, `issue-type`, `inbox-query`, `timeout`)
may now be inherited from a parent that sets them where this project does
not; that is D1, and is not a change to which tickets are this project's.
Decided by the dispatching session, 2026-10-22: no extra keys are written
into the project's file, since no key that finds the tickets can change.

5.2. **What changes.** A ticket whose `TCW Item` is a 3.x value of this
project (`<project>/<folder>`, with no `.` before the first `/` and the
project part equal to the active project's ID, S110:489-491) gets
`<project>.work/<folder>` (S111 Design 6.2), by one edit that sends that
field alone (`edit_issue`, as `rename` sends it, `:893`). A ticket already
holding the 4.0 value is skipped. Any other value is A10, as is a 4.0
value that would be over 255 characters; neither is edited. A ticket is
converted whether or not its folder is in this checkout, since the
conversion needs only the value: items keep their folder names (Non-goals).
Status, links, comments, labels and every other field are untouched, so
the board's columns and links stay as they were.

5.3. **Last, and resumable.** The edits run in phase F, after every local
write. A ticket whose edit fails is listed; the others are still tried;
the run then exits with the code of Design 1.6 (5 when Jira could not be
reached, else 1), naming the tickets left, and a re-run edits only those
(Design 2.6). Between phase D and the end of phase F, 4.0's
`tcw work list` leaves the remaining tickets out with TCW-110's warning
(S110:493-497), and a move that would touch one is refused
(S114:1046-1051). That happens only in that window, and after a run made
with `--no-jira` until the next run without it. B16 (Design 2.1) makes a
refusal of every edit unlikely; a refusal of some tickets only (a
permission set per ticket) is finished by a re-run once the permission is
given.

5.4. **Inside the Jira backend.** The search and the edits are two methods
of the Jira backend, `item_values()` (the search, made while planning) and
`set_item_values(pairs)` (the edits, made in phase F), used only by
`tcw migrate`; they cannot be one call, since the search runs before any
local write and the edits after the last (decided by the dispatching
session, 2026-10-22: the plan review's spec issue 1). The files backend has
nothing to convert in its backend (its references are files, C16). Neither
is one of the twelve backend operations (Abstraction litmus test).
`set_item_values` takes the list of `(ticket, old value, new value)` it is to apply
and checks each ticket's current value against the old one before editing
it, so the same method run with the pairs swapped puts the 3.x values
back; that is the way back for the tickets (Design 9.3), and needs no
command of its own. The code that runs the way back takes the Jira client
as an argument, so a test hands it the fake, never a client built from the
folder it runs in. The edit it sends is the one `rename` sends today for
the same field (`edit_issue`, `tcw/work/jira/backend.py:890-893`), a request
already in use on every 3.x rename.

### 6. Related projects

6.1. **Reading another project in either format.** A related project's
configuration is read whether it is 3.x or 4.0, and never written. For a
3.x one, migration works out the 4.0 form the same conversion would give
it (C3, C8), and uses that, so the active project's result does not depend
on whether the other project has been migrated yet. The two sides of an
inverted link (E3) each drop their own half: the extender drops its child
entry, and the extended project, when migrated, drops its parent entry
naming a project that, in either format, extends it as a listed child.
M6 uses only the active project's own manifests for the same reason.

6.2. **A monorepo migrates one project at a time; parents first is the
order to use** (TCW-106's review, S1). `tcw migrate` run in a package
converts only that package (Design 1.4), and the files it writes are the
same whichever of the family's projects were migrated before it (6.1), so
any order gives the same end state (criterion 45).

What works **between runs** is narrower than "a package's own records".
A converted parent link is a plain `parents: [root]`, which passes
everything down (C3), and a parent still in 3.x form cannot be read by 4.0
(S107 Design 2.8). So in a 4.0 package below a 3.x root:

- a command that reads an inherited taxonomy or capability from the root
  stops (exit 7, `InheritedUnavailable`, TCW-108 Design 6.2);
- a command that reads an inherited configuration key the package does not
  set itself stops the same way (S109 Design 3.1-3.3). `work.jira` is such
  a key unless the package sets every key under it TCW knows (S109:443-451),
  which a 3.x package does not (only some are required, Design 5.1), so in
  a Jira-backed package **every command that reaches Jira stops**, and so
  does any command reading `work.tags` when the package sets no tags;
- what reads only the package's own records and own keys works, as S109
  Design 3.4 lists per command;
- a command run in the 3.x root is refused there, and `tcw project new`
  inside a 3.x root stays refused (S106 Design 4.1; S115:354-355).

So the order to use is **parents before children**: migrate the root, then
its packages. That leaves no 4.0 project below a 3.x one at any moment, and
nothing in between stops. Migrating a package first is still allowed, and
gives the same files; its summary says that its parent is still 3.x, that
the commands listed above stop until the parent is migrated, and gives
`tcw -C <root> migrate`. Each run's summary lists the family's projects
still in 3.x form, parents first (Design 2.10). Decided by the dispatching
session, 2026-10-22: recommend the order and say what stops, rather than
refuse a child before its parent, because a family split across
repositories and people cannot always migrate in one order, and the
result does not depend on it.

6.3. **A planning workspace with many repositories** (UC-4). A project
whose store sits in the workspace's repository converts that store itself,
and lists its files as left in that repository (Design 1.4). The
workspace's own migration converts only its own stores and never the other
projects' stores held in its folder, since they are not its own
(design.md:588-593). A `../docs/<project>/work` location becomes
`tcw://<workspace>.path/docs/<project>/work` when the workspace can be
located (C5).

6.4. **A library read by others** (UC-2, UC-7). A library that migrates
first records its `cap-…` ids (Design 7), so a reader that migrates later
still resolves its overrides; the record is committed, so a reader that
pulls the library gets it.

6.5. **A related project not on this machine** (UC-6). A parent, child or
upstream named only for its location is converted without reading it (C3,
C4), and so is one that only E2 or E3 names (both are decided from the
active project's own file). One whose content a conversion must read (to
tell E1 from E4, C14, C16) is B5, naming the project and the folder its
manifest entry will name. Every command other than `tcw migrate` is
refused in a 3.x project (Design 1.2), `tcw project provision` included
(S115 Design 7), so B5's message says: fetch it into that folder with
`git clone <repository> <folder>` (the repository and folder written out
when the 3.x entry declares a `repository`), and run `tcw migrate` again;
once this project is migrated, `tcw project provision` fetches every
related project its manifests name (S115 Design 7.1-7.2). `tcw provision`,
which the first draft named, is removed in 4.0 (S115 Design 1.2).

6.6. **A linked git worktree** (S-4). Tracked files are read and written in
the worktree, as everywhere in 4.0 (design.md:560-566). A 3.x personal file
there is converted; one only in the main checkout is A7, left for a run in
the main checkout.

### 7. The migration record

`.tcw/tcw-migration.yaml` is written in phase A of the first run that has
something to record, and added to by later runs (an entry already there
with the same content is left as it is):

```yaml
tcw-version: 4.0.0
capability-ids:          # every cap-… id removed, with its id-path now
  cap-4f0a61: cli/read-a-file-by-the-format-version-it-records
moved:                   # every object C14 moved: 3.x id-path to id-path now
  ov/login: auth/login
removed:                 # every value removed with no 4.0 home
  - file: tcw-config.yaml
    key: projects.children.app.jira
    value: {project: APP}
```

`capability-ids` gives each id the id-path the capability has **after**
this run, so a source's own overrides are recorded where C14 put them, and
`moved` lets a reader's prefixed reference to a moved object
(`M/ov/login`) find it (C16).

It is meant to be committed, like the rest of `.tcw/` except the personal
files and the progress record, so that readers of the project on other
machines can resolve their overrides (Design 6.4). Only `tcw migrate` reads
it, and `tcw validate` does not report it.

**It stays correct when the source moves something later.** 4.0's move and
rename (TCW-114) change an object's id-path. When the project being changed
holds a `.tcw/tcw-migration.yaml`, the move also rewrites every
`capability-ids` value and every `moved` value that is the moved object's
id-path or lies below it, in the same run as its other reference rewrites
(Design 8.5). So a reader that migrates after its source moved a
capability still finds it. A reader that finds a recorded id-path the
source no longer has (the record edited by hand, or a move made without
it) gets B9 with the fix by hand (Design 2.9).

**When it is removed: not in TCW 4** (decided by the dispatching session,
2026-10-22). The two automatic rules considered, "`tcw migrate` removes it
once no project still to migrate needs it" and "`tcw validate` reports it
once nothing reads it", both need to know every project that reads the
source, and neither can: in 4.0 a source records no list of its readers
(only `children:`, and a reader can name any project as a parent), and a
public library's readers are private (UC-7). A rule that guessed would cost
a late reader its overrides, with B9 as the only sign. So the record is
kept for as long as TCW can migrate a 3.x project, which is the whole of
4.x. It is small, and nothing but `tcw migrate` reads it. The release that
stops reading 3.x projects says it can be deleted. A person who knows that
every reader has migrated may delete it sooner; the migration guide
(TCW-117) says so, and says to keep it in a library others read.

### 8. What this item changes in other code

8.1. **The command is registered** in `build_parser` (`tcw/cli.py:549-614`
at `32c510f0`, `:367` at `ebce3fd6`) and exempted, by name, from every
check `_dispatch` makes before the command (`:641-662` at `32c510f0`,
`:459-480` at `ebce3fd6`; Design 1.2), as `validate` is exempted from
`refuse_retired_config` today. The plan lists those checks as they stand on
the final `v4`.

8.2. **The 3.x readers migration needs are kept in one place,** used by
nothing else: reading `projects:` (`tcw/store/project.py:616-667`,
`parse_connected_entry`, `tcw/store/base.py:866-917`), `extends`
(`tcw/store/fs.py:904-933`), the 3.x cache location
(`tcw/store/checkouts.py:95-127`), the 3.x override match
(`tcw/store/fs.py:2301-2309`, `:2344-2389`), the 3.x reference readers
(`tcw/refs.py`, `tcw/store/fs.py:2425-2440`, `tcw/work/gates.py:331-380`)
and 3.x link scanning (`tcw/validate.py:49-72`). Where a sibling has
deleted one (TCW-108 Step 8b deletes the `projects:` reader; TCW-111 and
TCW-112 the `meta.yaml` and pointer readers), the plan restores what
migration needs **from tag `v3.0.2`** (the released 3.x, whose `tcw/`
`main` matches exactly) into that place, not from `32c510f0`, which holds
TCW-106's changes to several of these readers (header; "Citations at
`v3.0.2`", Notes). 4.0's own readers do not read 3.x forms (they refuse
them, Problem 2).

**The siblings' guard tests make room for that place, and only that
place.** Three sibling items add a permanent test that forbids, anywhere in
TCW's code, exactly what migration's 3.x readers and its fixtures must
contain:

| Guard (sibling plan) | What it forbids that migration needs | Exempted folder |
| --- | --- | --- |
| TCW-110's `tests/test_identifier_sweep.py` (P110:1189-1196) | `parse_tcw_uri`, `.qualified`, `tcw://C/`, `tcw://T/`, `tcw://W/` outside `tcw/ids.py`, and a project ID joined to a name with `/` by hand, under `tcw/` (test files are already outside its scope) | `tcw/migrate/` |
| TCW-111's `tests/test_object_folder_sweep.py` (P111:1387-1398) | `meta.yaml`, `item.yaml` or `ITEM_FILE` outside `tcw/object_folders.py`, and a folder listing not on its allowlist, under `tcw/` (test files already outside its scope) | `tcw/migrate/` |
| TCW-112's `tests/test_no_3x_inheritance.py` (P112:1802-1810) | under `tcw/`, defining or calling `_mint_cap_id`, `_apply_override` and the rest of its list (migration's copies are renamed, but each names the 3.x function it was copied from); in test files, writing `extends:`, `overrides:` or `id: cap-` | `tcw/migrate/` for its rules over `tcw/`, `tests/migrate/` for its rule over test files |

Each exemption is one named constant in its guard, matched by whole path
parts. It is `MIGRATION_FOLDERS` in TCW-110's and TCW-111's guards. In
TCW-112's guard, which has rules over two kinds of file, it is two
constants: `MIGRATION_CODE` for its rules over `tcw/` and `MIGRATION_TESTS`
for its rule over test files. These are the names the handoffs below ask
for (decided by the dispatching session, 2026-10-22, the re-check's S1:
one guard with two kinds of rule needs two constants, and the handoffs
already used these names). Each is matched by whole path parts (so `tcw/migrate/legacy.py` is exempt and
`tcw/migrate_old.py` or `tests/migrate_x/` is not), with a comment naming
this item and Design 8.2, and with a test in the same guard that the
exemption covers only those folders: the forbidden text placed in a
temporary file under the exempted folder passes, and the same text in a
file anywhere else fails. Each exemption is added in the step of this
item's plan that first puts such text there, not before. Decided by the
dispatching session, 2026-10-22 (the plan review's M1, checked against the
three sibling plans): without the exemptions the suite goes red the first
time a 3.x reader is copied; a whole-file allowlist entry per migration
module would have to grow with every step, and using TCW-110's
`is_3x_address` instead of a copy would read links by 4.0's rule, not by
the rule 3.x read them with (Problem 4).

8.3. **The messages and records name `tcw migrate`.** The capability record
of Capability changes names it; the messages that already name it
(TCW-106 to TCW-114) now name a command that exists, and
`tests/test_documented_cli_surface.py`, which refuses a record naming a verb
the CLI lacks (`I106:142-146`), passes with it named.

8.4. **This repository's tests that read its own records by their 3.x file
names** (for example `tests/test_ledger_3_0.py`, which reads `meta.yaml`,
P111:1483-1489) find each record by whichever state file it holds, so the
merge's migration (Design 9) needs no change to them. The plan's sweep
lists every test reading the repository's own `docs/` records or root
configuration. **No test this item adds reads this repository's root
`tcw-config.yaml`**, which the merge's migration deletes: a test that needs
its contents (criteria 15 and 63) reads a frozen copy kept under
`tests/migrate/`, with the commit it was copied from recorded beside it.
Today only `tests/test_repo_config_pair.py` reads the root file (checked
2026-10-22), and it is deleted at the merge (Design 9.3 step 3). Decided by
the dispatching session, 2026-10-22 (the plan review's M6): otherwise these
tests fail in the proof clone and at TCW-118, against criterion 54.

8.5. **TCW-114's move and rename keep the record correct** (Design 7).
When the project they change holds `.tcw/tcw-migration.yaml`, they rewrite
the record's `capability-ids` and `moved` values for the moved object and
everything below it, as one more file among the references they already
rewrite (S114's litmus test, "Rewriting the backend's own references"). This
item adds that to TCW-114's code, which is built before it; nothing in
TCW-114 changes before then.

8.6. **Migration's messages pass TCW-73's guard against git words.**
`tests/test_static_guards.py::test_no_git_word_outside_the_exempt_functions`
reads every string holding a space in every `tcw/**/*.py` file. It refuses
`git`, `commit`, `push`, `pull`, `worktree`, `trunk` and `branch` in any
of their forms, outside the functions its `EXEMPT` set names. Each message
of this item is settled case by case. Decided by the dispatching session,
2026-10-22, the re-check's N3:

| Message | Settled by |
| --- | --- |
| the stopped run's warning (Design 2.7) | reworded: `do not save these files in version control until 'tcw migrate' finishes`. Same meaning, no git word |
| A6's advice about the cache clone | reworded: "moving the clone to the `../<name>` folder the shared manifest names". The folder is named by where it is written, not by its being committed |
| A7 | reworded: "a 3.x personal file in the main checkout, which this run does not convert; run `tcw migrate` there". `checkout` is not a git word |
| B13 | reworded: "the shared manifest's path `../<name>` already holds something other than the project" |
| B17's fix | already free of git words: "restore the project from version control" |
| B5's fetch line (Design 6.5), `git clone <repository> <folder>` | an exemption. The line is a command the person must type, and every `tcw` command, `tcw project provision` included, is refused in a 3.x project, so no other wording gives them a way to fetch it. `EXEMPT` gains one entry, `("migrate/family.py", "absent_project_message")`: the one function that builds B5's message, and nothing else. Its comment names this item, Design 6.5, and the reason. This is TCW-73 Design 9.2's form, as `FsStoreProvisioner`'s clone is exempted today |

Every other message of this item holds no git word, and the guard checks
that; `.tcw/.gitignore` does not match, since the guard's words are whole
words. The exemption is added in the step that creates the function, since
the guard's own test refuses an entry naming a function that does not
exist (`test_every_exempt_function_still_exists`).

The same item adds `tcw/migrate/` to the files that
`tests/work/test_git_write_scan.py` scans (`SCANNED`, TCW-70's guard that
no git command TCW runs writes anything). So migration's own git reads
(`rev-parse`, `ls-files`, `status` with `--no-optional-locks`,
`check-ignore`; criterion 4) are held to that guard as well as to
criterion 4's test.

### 9. This repository

9.1. **Until `v4` merges, this repository's records stay 3.x on `v4`,**
with the root and `.tcw/` configuration pair, because the lifecycle `tcw`
(3.0.2, from `main`) reads them; nothing in this item migrates them on
`v4` (decided by the dispatching session, 2026-10-22: migrating them on
`v4` would stop the 3.0.2 lifecycle from reading this repository's items,
and deleting the root `tcw-config.yaml` would send 3.0.2, run in this
worktree, up to the enclosing primary checkout's `tcw-config.yaml`, so its
commands would act on `main`'s records).

9.2. **The proof.** TCW-116's implement stage proves migration on scratch
clones of this repository in which `v4` is merged into `main` (made outside
both checkouts, nothing pushed), so that each holds both branches' records,
as the real run will. In each clone, with the `v4` code (a virtual
environment, as CLAUDE.md describes for worktrees). It is made when part 1
of the build order has landed, and again when part 2 has.

**Every command below runs the virtual environment's `tcw` by its full
path.** A bare `tcw` is the lifecycle's 3.0.2, which has no `migrate`, and
putting the virtual environment first on `PATH` instead is how a lifecycle
command would end up run by 4.0. Every step after step 1 also sets
`https_proxy` and `HTTPS_PROXY` to an address nothing listens on
(`http://127.0.0.1:9`), so that a request, if one were made, could not
leave the machine; step 6's suite runs without that setting (the suite's
own servers listen on this machine) and with the credential variables
unset.

1. `tcw migrate --dry-run`, with the Jira credentials set, run through a
   short script kept in the scratchpad that records the method and path of
   every request before it is sent: it searches the live board, asks for
   one ticket's edit screen (B16), and edits nothing; the record shows no
   `PUT` and no `POST` but the search's; the listed tickets are this
   project's, each with its old and new value.
2. `tcw migrate --no-jira`: the local phases finish, nothing is sent to
   Jira, exit 0, and the summary says the tickets are not converted.
3. `tcw migrate --no-jira` again: `nothing to migrate in the files`, no
   file changes (`git status --porcelain`, saved outside the clone, is the
   same before and after), exit 0.
4. In a second clone, the stop and the finish on real data: make one item
   folder unwritable (`chmod a-w`) that phase C writes into **and that
   phase B moves nothing into** (so the stop falls in phase C, not B), run
   `tcw migrate --no-jira` (it stops with exit 1 and
   `run 'tcw migrate' again to finish`, leaving the progress record), make
   the folder writable again, run it again (exit 0, no progress record
   left), and compare the result with the first clone's. **The comparison
   is of the files git would track, and of their contents**, not of the
   raw folders: each clone's list of tracked and untracked-but-not-ignored
   files (`git ls-files --cached --others --exclude-standard`), each with
   its SHA-256 digest, is the same in both. Raw folders differ in build
   leftovers that are not migration's: `*.egg-info`, `__pycache__`,
   `.venv`, `.pytest_cache`, and everything else `.gitignore` names.
5. In a third clone, the refusal without Jira: `tcw migrate` without
   `--no-jira` and with the credential variables unset exits 1, names
   `--no-jira`, and `git status --porcelain` is empty: nothing was written.
6. In the first clone, delete `tests/test_repo_config_pair.py`; run the
   suite as CI runs it, and 4.0's `tcw validate`.

Decided by the dispatching session, 2026-10-22 (the plan review's M7, S1
and S2, and spec issue 5).

The implement round records the counts (work items, ledger objects, ids
recorded, files moved into `resources/`, references and links rewritten,
tickets listed, A3 mentions reported) and every report.

9.3. **The real migration is a step of the merge** (TCW-118), in this
order, so that `main` never holds 4.0 code with 3.x records and no
lifecycle command runs in between (S111:1287-1290):

0. **Before starting,** the session carrying out the merge tells every
   agent and session working in this repository to run no `tcw` command
   until step 7 is done, and the user runs none on another machine. This
   is a rule for people and agents, so it is said out loud, not assumed.
1. **In a clone made for the merge,** outside the primary checkout and the
   `v4` worktree (so that the primary checkout's editable install, which is
   the lifecycle `tcw`, stays 3.0.2 until step 5), make a branch from an
   up-to-date `main` and merge `v4`.
2. In that clone, with that branch's code in a virtual environment, its
   `tcw` run by its full path as in Design 9.2, run
   `tcw migrate --dry-run` with the Jira credentials set. It lists every
   ticket with its old and new value, and checks that `TCW Item` can be
   edited (B16), editing nothing. Save its output outside the repository
   as a cross-check for the way back (step 6's own output is the list the
   way back uses). Review it, then run
   `tcw migrate --no-jira`: the files only, exit 0. The flag, not unset
   variables, is what keeps this step off the live board.
3. Delete `tests/test_repo_config_pair.py`, and the root `.gitignore` line
   `/tcw-config.local.yaml` (A4). Delete `UNMIGRATED_RECORDS` from
   `tests/test_docs_describe_4_0.py` (TCW-117's handoff to TCW-118), so
   that its scan now reads the migrated records, and fix in this step every
   hit it reports in `docs/taxonomy/` or `docs/capabilities/`. Run the
   suite as CI runs it, with the Jira credential variables unset as in
   Design 9.2 step 6, and `tcw validate`. Fixing those hits is editing
   files only, so it runs no `tcw` command and keeps step 0's rule. Its
   size is known in advance from TCW-116's second proof (Design 9.2, made
   again after part 2), which deletes the tuple in a proof clone and
   records the list of hits, when TCW-117 has landed by then.
4. Commit the migration after the merge commit, and bring `main` to that
   commit by a fast-forward, so the merge and the migration reach `main`
   together. Pushing `main`, and the plugin marketplace reading `main`
   before PyPI has 4.0, are TCW-118's to order.
5. Bring the primary checkout to that `main` (`git pull --ff-only` from the
   merge clone's folder, or from the remote once TCW-118 has pushed) and run
   `pip install -e '.[dev]'` there again, since 4.0 may change its
   dependencies. Its editable install, the lifecycle `tcw`, is now 4.0. Its
   untracked root `tcw-config.local.yaml`, if any, is still 3.x.
6. **The first write to a real Jira.** Before this step, the edit has been
   proven against the fake Jira client, whose recorded request is the one
   `rename` sends today on every 3.x rename (criterion 65), and step 2's
   dry run has confirmed on the live board that the field can be edited.
   Decided by the dispatching session, 2026-10-22: no throwaway Jira
   project is made, since creating one needs Jira administrator rights,
   and the request is one this board already accepts. Then run
   `tcw migrate` in the primary checkout with the Jira credentials set: it
   converts the personal file (Design 2.11) and then every ticket's
   `TCW Item` (phase F). Its output is saved outside the repository: its
   `C17` lines are the edits this run really made, and the way back uses
   them. While it runs, `tcw work list` leaves the
   remaining tickets out with a warning (Design 5.3), and the board's
   columns, links and statuses are unchanged (Design 5.2).
7. Run `tcw migrate` once more (`nothing to migrate`) and
   `tcw validate --remote`. The rule of step 0 ends here.
8. **Other checkouts.** The `v4` worktree and every agent's worktree still
   hold 3.x records, and the shared `tcw` is now 4.0, which refuses them.
   Each is removed (`git worktree remove`), or brought up to `main` and
   migrated with `tcw migrate` before any other `tcw` command runs in it. A
   branch still in progress that merges later brings 3.x files with it;
   `tcw migrate` after that merge converts them (Design 2.11).

**The way back.** Until step 4's fast-forward, deleting the merge clone
undoes everything. After it, the files go back by reverting the migration
commit (and the merge, if 4.0 is withdrawn) and reinstalling 3.0.2. The
tickets go back with the edits step 6 reported, from its saved output,
with step 2's list as a cross-check (a ticket in one and not the other is
read before anything is put back): the Jira backend's method
of Design 5.4, given each ticket's pair the other way round, puts every
3.x value back and edits no other field, so the board is as it was. That
needs no command of its own; TCW-118 runs it from Python if it is ever
needed. Decided by the dispatching session, 2026-10-22, the re-check's S9.
The way back undoes what step 6 did, so it reads step 6's own report.
Step 2's dry run was made earlier, in another checkout, and could differ if
a ticket changed in between. Step 3 names the tuple's deletion, so that
TCW-118 does not have to merge this procedure with TCW-117's handoff. And
step 3's suite runs with the credentials unset, as the proof's does.

So the lifecycle `tcw` switches from 3.0.2 to 4.0 at step 5: after this
repository's files are migrated (steps 2 to 4), and before its tickets are
(step 6). Until step 4, 3.0.2 drives every lifecycle command, on `v4` and on
`main`; from step 5 on, 4.0 does.

9.4. **The configuration pair ends** at step 2's `tcw migrate --no-jira`:
the root `tcw-config.yaml` and `.tcw/tcw-config.yaml` are both present and
no progress record exists, so the both-files rule (Design 2.7) compares
their parsed values. They are equal exactly when
`tests/test_repo_config_pair.py` passes (`:33-40`: the same settings, the
version line, and `not-tags` for `not_tags`), so the `.tcw/` file is kept
as it is and the root file deleted. If a 3.x change merged into the root
file has not reached the `.tcw/` copy, the run stops with B11 before
writing anything, and the copy is brought in step first. The test is
deleted at step 3, since its subject is gone.

9.5. **The user's own setups** are private and are not named here. During
TCW-116's qa, `tcw migrate --dry-run` is run in each, with the `v4` code,
and its counts, reports and blockers are recorded without naming them; the
real migration of each is the user's, after 4.0 is published (TCW-118's
success criterion; design.md:800-802).

## Abstraction litmus test

| Operation | Layer | Verdict |
| --- | --- | --- |
| `tcw migrate`'s conversion of configuration, manifests, `.tcw/`, state files, `resources/`, override folders and file names (Design 3, 4.1-4.2, C9-C15) | deployment | About files and folders on disk (design.md:125-131): another store does not keep a `meta.yaml` or a root `tcw-config.yaml` and has nothing of this to convert. Kept in the files store's code (Design 8.2). |
| Rewriting stored references to full identifiers (C16) | repository | Tree-store state files, `capabilities.yaml` and Markdown are repository files in both modes (`docs/lifecycle/abstraction.md:14-17`); the files backend's `parent` and `blocked-by` are in its state files, which it owns and rewrites, as TCW-114 rewrites them (S114 litmus, "Rewriting the backend's own references"). Passes. |
| Converting the Jira backend's stored `TCW Item` values (Design 5) | model, inside the Jira backend | The backend owns the value, so it converts it; a store that is not files would update a column holding the identifier. A one-time conversion of an old format is not one of the twelve operations: they stay twelve, and `tcw migrate` calls the Jira backend's own method. Passes. |
| The migration record and the progress record (Design 7, 2.7) | deployment | Files in `.tcw/`, read only by migration; the record is also kept current by TCW-114's move (Design 8.5), which already rewrites the files store's own references. |
| Reading related projects in either format (Design 6) | deployment | Locating and reading other projects' folders is the deployment layer's (design.md:125-131); the relations it reads are model facts any store has (parents, children, IDs). |
| No git check, no git change (Design 1.7) | — | Keeps `docs/lifecycle/abstraction.md:98-103`. |

## Use cases

- **UC-1 (a single project).** The common case: C1, C9, C10, C16 and C17,
  no relations. Afterwards the configuration is the 3.x file plus one line,
  so 4.0 needs no more configuration than 3.x (design.md:803-804).
- **UC-2 and UC-7 (a library others read; a public library).** The library
  migrates itself and never its readers; its `cap-…` ids are recorded and
  committed (Design 7), so private readers migrate whenever they choose and
  still resolve their overrides (6.4). Nothing of a reader is written into
  the library, and nothing private reaches it.
- **UC-3 (a monorepo).** One project at a time, parents first, though any
  order gives the same result (Design 6.1-6.2); between runs, a package
  below a 3.x root stops on what it inherits (Design 6.2). The root's `children` become `children:` and
  manifest entries (never downwards, S107 Design 2.6); a package's parent,
  which encloses it, needs no entry (M6); a package's `extends` naming a
  sibling becomes one more parent (E4), and one naming a project the root
  already passes down adds nothing (E1). The shared Jira project is UC-5.
- **UC-4 (many repositories and a planning workspace).** A project's store
  in the workspace's repository is converted by its owner and named as left
  in that repository (Design 1.4, 6.3); `../` locations become `.path`
  addresses (C5); `upstream: core` becomes a parent with `inherit` from the
  `extends` (C3). Tested with two real git repositories (criterion 47).
- **UC-5 (one Jira project shared by several TCW projects).** Each project
  edits only tickets whose `TCW Project` is its own ID (Design 5.1), so one
  project's migration leaves the others' tickets in 3.x form until they
  migrate.
- **UC-6 (a related project not on this machine).** Converted where its
  location is all that is needed; B5 where its content is needed
  (Design 6.5).
- **UC-8 (several separate families on one machine).** M6 writes an entry
  whenever the search would find two folders for one ID (S107 Design 2.7),
  so the manifest decides; migration reads only declared relations, never
  every project on disk.
- **S-1 and S-6 (who decides; unattended runs).** No prompt: the dry run is
  the review, and exit codes 0, 1, 3 and 5 tell a script what happened;
  `--no-jira` lets an unattended run convert files without credentials.
- **S-2 (harness).** A CLI command; the same under Claude Code, Codex and
  Pi.
- **S-3 (backend).** Both work backends' files are converted; only the Jira
  backend has tickets (Design 5).
- **S-4 (worktrees, clones, other machines).** Design 2.11 and 6.6.
- **S-5 (personal configuration).** The project's personal file is converted
  (C1); the user-wide file is reported, not changed (A5).
- **S-7 (several people).** One person migrates and commits; each other
  person's run converts only their untracked files (Design 2.11). Two runs
  of phase F at once write the same values.
- **S-8 (partial failure).** Design 2.4-2.7 and 5.3: what was done, what was
  not, and `run 'tcw migrate' again to finish`; the progress record lets a
  re-run finish every stop point of Design 2.7's table without working
  anything out again, and a re-run never repeats a change.
- **S-9 (upgrades).** This item is the upgrade. Old code reading migrated
  files is not a constraint (`docs/use-cases.md`, S-9); a 3.0.2 `tcw` run
  in a migrated project no longer finds its root file and may act on an
  enclosing 3.x project (Risks).
- **S-10 (things TCW does not own).** Migration reads only the project's
  configuration, its stores and declared relations; it never walks into
  `node_modules` or other folders, and it rewrites only TCW's own files
  (the root `.gitignore` is reported, A4).
- **S-11 (version control).** No git check, no git change (Design 1.7);
  works in a folder that is not a git repository, without writing
  `.gitignore`.

Checklist (`docs/use-cases.md`, "The checklist"): 1 Design 6, C4, C5; 2
Design 1.4; 3 Design 6.1-6.5; 4 the litmus test and Design 5.1; 5 S-1;
6 S-2; 7 Design 2.7; 8 UC-1; 9 S-9; 10 criteria 46 and 47 use the setups
they claim.

## Acceptance criteria

Fixtures are built in temporary folders, with real git repositories where
a criterion names a repository, and a fake Jira client that records every
search and edit (the suite's existing Jira fakes). "Snapshot" means every
path, its bytes and its modification time, for the active project, every
related project and the user-wide file. **F-full** is one fixture family
that exercises every conversion C1 to C17 and every report A1 to A13 and
D1 to D8, with no blocker; its active project keeps its work in Jira.
**F-single** is the part of F-full that one project with no related
project exercises (part 1 of the build order): every conversion and
report part 1 makes. A criterion that names F-full is run on F-single
when part 1 lands and on F-full when part 2 does. Criteria 57 onwards were
added when the spec was revised; each is placed in the group it belongs
to.

**The command**

1. `tcw migrate --help` shows `[--dry-run]` and `[--no-jira]` and no other
   argument;
   `tcw migrate x` exits 2; outside any project, `tcw migrate` exits 1 with
   the message every command gives there; no run of `tcw migrate` in these
   criteria writes anything to standard output.
2. In a 3.x project (root `tcw-config.yaml`, no `.tcw/`), `tcw migrate
   --dry-run` is not refused and exits 0, while `tcw work list` there is
   still refused with TCW-106's message (exit 1).
3. From a 4.0 project, `tcw -C <3.x project's folder> migrate --dry-run`
   gives the same lines and exit code as criterion 2 run in that folder.
4. Run in a git repository with uncommitted changes, and in a copy outside
   any git repository, `tcw migrate` makes the same changes (apart from
   `.tcw/.gitignore`, written only in the first) and exits 0; a `git` shim
   on `PATH` records that no git command other than read-only ones
   (`rev-parse`, `ls-files`, `status`, `check-ignore`) is run, and that
   every `status` carries `--no-optional-locks` (a plain `git status` may
   rewrite `.git/index`).

**The plan, the dry run and blockers**

5. `tcw migrate --dry-run` on F-full leaves the snapshot unchanged; the fake
   Jira client records the search (one request per page), one edit-screen
   request, the field-id reads `metadata` makes, and no `PUT` and no `POST`
   other than the search's; exit 0.
6. On F-full, the set of `(path, action)` in the dry run's lines equals the
   set of paths the real run then changes, by comparing snapshots, and the
   ticket keys the dry run lists equal the keys the real run edits. The
   progress record (written and deleted within the run, so never in the
   snapshot difference) and folders (which the snapshot records but no
   change line names) are left out of both sets.
7. Every change line on F-full names its conversion (`C1` to `C17`), and
   every report line its number (`A1` to `A13`, `D1` to `D8`); every
   ticket line gives the ticket's old and new value.
8. For each blocker B1 to B17, a fixture holding it alone (B17 after a
   stopped run, with a file changed before the re-run): the dry run and
   the real run each exit 3, name the file, key or folder and the blocker's
   reason; after the real run the snapshot is unchanged and the Jira client
   records no edit.
9. A fixture holding B1, B8 and B9 lists all three in one run.
57. `--no-jira`: on F-full, with a fake Jira client that fails any request,
    `tcw migrate --no-jira` makes every local change the plain run makes,
    records no request, exits 0, and its summary names the Jira project,
    says the tickets are not converted, and says the work store was not
    checked after the run (Design 1.1); its A12 list still holds every
    finding outside the work store; `tcw migrate` afterwards changes no
    file and edits exactly the tickets the plain run would have edited;
    `tcw migrate --dry-run --no-jira` records no request and exits 0; in a
    project keeping its work in files, `--no-jira` changes nothing about
    the run.
58. Jira failing while planning: on F-full with Jira unreachable, a real run
    exits 5; with the credential variables unset, it exits 1; with the
    credentials refused, it exits 1. In each, the snapshot is unchanged, no
    edit is recorded, and the message says nothing was written and names
    `tcw migrate --no-jira`. A dry run in the same three cases lists every
    local change and exits 5, 1 and 1.
59. B16: with the fake's edit screen for the first ticket to edit lacking the
    `TCW Item` field, the real run exits 3, the snapshot is unchanged, and
    no edit is recorded.
66. `--no-jira` is safe by the code's shape (Design 1.1): with the Jira
    client's and the Jira backend's constructors made to fail, `tcw migrate
    --no-jira` and `tcw migrate --dry-run --no-jira` on F-full finish as
    criterion 57 says, the check after the run included; so do the same two
    runs made with a progress record present (a run stopped after phase A),
    the real one finishing the local steps and the fake recording no
    request; only one module of `tcw/migrate/` imports from
    `tcw.work.jira`, and only the function that plans the Jira half imports
    that module; a dry run whose planning code is made to call
    `edit_issue` on the client it was given fails with the read-only
    wrapper's error, with no edit recorded, both on a fresh plan and with a
    progress record present; and the read-only wrapper refuses every
    attribute other than its six reading calls.

**Order, stopping and running again**

10. On F-full, the order of writes the run records is: phase A (the
    record, the progress record and its ignore line) before any other
    write; every move (C14, then C13) before the first state file is
    written; each 4.0 state file written exactly once; every store write
    before `.tcw/tcw-config.yaml` is written; the root files and then the
    progress record deleted after the configuration is written; every Jira
    edit after every file write.
11. On F-full, for each k from 1 to the number of writes N (a write as
    Design 2.5 defines it), a run made to fail at its k-th write (an
    injected error) exits 1, or for a ticket edit the Jira code, prints
    `run 'tcw migrate' again to finish` and lists what it did; a second run
    without the fault exits 0; the final snapshot (ignoring modification
    times) and the tickets' values equal those of one uninterrupted run,
    and no `.tcw/tcw-migration-progress.yaml` is left.
12. On F-full with Jira reachable while planning and unreachable in phase
    F, every local write is made, the run exits 5 and names the tickets not
    converted; a second run with Jira reachable edits exactly those tickets
    and changes no file. The same with Jira refusing the credentials in
    phase F exits 1.
13. Both-files rule, with no progress record: a folder holding `meta.yaml`
    and a `tcw-capability.yaml` whose parsed values equal its conversion
    ends with only the latter, its bytes unchanged; one where they differ
    is B11, naming both; likewise for a root `tcw-config.yaml` beside
    `.tcw/tcw-config.yaml`, equal and different; and a pair that differs
    only in a comment counts as equal.
14. A second run after a finished one prints `nothing to migrate`, exits 0,
    leaves the snapshot unchanged, and the fake records the search's
    requests and the field-id reads and no edit; with Jira
    unreachable it prints `nothing to migrate in the files; the tickets
    could not be checked` and exits 5; with `--no-jira` it exits 0 and the
    fake records no request.
60. The stop points of Design 2.7 for one project: for each of P2, P3, P6,
    P7, P8 and P9, a run of F-single stopped there (an injected error at
    that write) leaves `.tcw/tcw-migration-progress.yaml`, listed in
    `.tcw/.gitignore` inside a git repository; a second run follows it
    (the plan-making code is not called, which the test checks), gives the
    snapshot of one uninterrupted run, and leaves no progress record. After
    a stop at P8, with one not-yet-converted file changed by hand, the
    second run stops with B17 naming that file, exits 3, and writes
    nothing more; after a stop at P7, with the 3.x state file that waits to
    be deleted changed by hand, the same, and that file is still there with
    the hand edit. P5: with the rename of one C13 move failing with the
    cross-device error, the run exits 1, names both folders and says to
    move it by hand, and copies nothing; after the test moves it by hand, a
    second run finishes with the snapshot of one uninterrupted run.
61. The stop point of Design 2.7 for overrides: a run of F-full stopped at
    P4 (an override's folder moved, its key still there) is finished by a
    second run with no B9 and the snapshot of one uninterrupted run.
62. Objects in either form: in a migrated project, a branch brings back one
    capability in 3.x form (`meta.yaml`) whose `Subject` names a bare path
    that only a 4.0 capability of the project has, and one item whose
    `blocked-by` names a 4.0 item; `tcw migrate` converts only those two,
    each reference given the project as owner, and a `meta.yaml` that
    reappears beside its folder's `tcw-capability.yaml` with different
    values is B11.

**Nothing lost**

15. A frozen copy of this repository's root `tcw-config.yaml` (with its
    comments, anchors and `not_tags`), kept under `tests/migrate/` with the
    commit it was copied from (Design 8.4), converted, gives exactly
    `tcw-version: <running>` followed by that text with `not_tags` written
    `not-tags`; in F-full,
    every converted YAML file differs from its original only in the lines
    the plan names (a line-by-line comparison).
16. Every file moved by C13 or C14 has the same bytes after the move; the
    only paths that no longer exist after F-full are 3.x state and
    configuration files whose 4.0 copies exist, and the old places of moved
    files and folders.
17. After F-full, `.tcw/tcw-migration.yaml` holds every `cap-…` id the
    fixture had, each with its id-path after the run (an override's at its
    moved path), every C14 move under `moved:`, and every `jira` block,
    each with its file and key; and its first line is
    `tcw-version: <running>`.

**The configuration**

18. C1: `.tcw/tcw-config.yaml` and `.tcw/tcw-config.local.yaml` begin with
    `tcw-version: <running version>`; `.tcw/.gitignore` holds
    `/tcw-config.local.yaml`, `/tcw-manifest.local.yaml` and
    `/tcw-migration-progress.yaml` inside a git repository and does not
    exist outside one; store paths are unchanged
    text.
19. Empty files: an empty `.tcw/tcw-config.local.yaml` gains only its
    version line; an empty `.tcw/tcw-config.yaml` beside a root 3.x file
    gets the root file's conversion; an empty one with no root file is B15;
    `tcw work list` in a project whose `.tcw/tcw-config.yaml` is empty is
    still refused with TCW-106's missing-version message.
20. C2: `not_tags` becomes `not-tags` in every place it is a key, in both
    project files; a key such as `work_tags` is B1.
21. C3: fixtures for a 3.x parent, children and upstream give, in order,
    `parents: [<id>]`, `children: [<ids>]` and
    `parents: [{id: core, inherit: [taxonomy]}]` (upstream extended for
    taxonomy) or `inherit: none` (not extended); no `projects:` key is left;
    4.0's reader of TCW-108 loads each without a problem.
22. C4: a table-driven test with one fixture per row M1 to M6 gives the
    shared and personal manifest entries in the table, including an
    absolute locator going to the personal manifest and a URL with `#`
    giving B3.
23. M5: with a 3.x cache clone of the project present under
    `$XDG_CACHE_HOME/tcw/stores/…`, the personal manifest names its absolute
    folder and 4.0's lookup finds the project there; with it absent, A6
    names the folder `tcw project provision` will fetch into.
24. M6: a parent that encloses the project, and a sibling next to its root,
    with no `repository`, get no entry; the same with a `repository` get an
    entry; a sibling found twice by the search gets an entry; setting
    `TCW_PROJECT_<ID>` for the parent to another folder changes none of
    these entries and gives A11.
25. E1 to E4: one fixture each gives the parent entries of Design 3, C8's
    table, including an ancestor added by E4 placed before the parent it is
    an ancestor of, and 4.0's load order for each has no C3 warning.
26. E3 on both sides, and order: a project `p` extending its listed child
    `k`, migrated `p` then `k` and `k` then `p`, ends with `p`'s parents
    holding `k` with `inherit: [<axis>]`, neither listing the other as child
    or parent the other way, identical files in both orders, and D6
    reported in each run.
27. C6 and B2: a `jira` block is dropped, reported (D6) and recorded;
    `connected-projects` is B2 naming the 3.0 migration guide.
28. C5: a relative store path inside the project is unchanged; `../` into a
    locatable project becomes `tcw://<id>.path/<rest>`; an absolute path
    inside another project becomes an address plus a personal manifest
    entry; one inside no project is B6; a store `repository` declaration is
    unchanged; and each converted store resolves, in 4.0, to the folder 3.x
    resolved.
29. TCW-109's checks: a credential name `TCW_JIRA__EMAIL` is A9; a
    `work.tags: null` in the shared file is D5.
30. A5: a user-wide file holding `not_tags` is reported with the line to
    change, and its bytes are unchanged.
31. A4: a root `.gitignore` holding `/tcw-config.local.yaml` is reported and
    unchanged.
32. D1 and D2: a 3.x parent setting `work.tags` and holding a capability at
    `cli/x`, and a child with no `work.tags` and its own `cli/x`, give D1
    naming `work.tags` and the axes now inherited, and D2 naming
    `cli/x`.
63. A13: a stage `post` binding `tcw provision` and a procedure command
    holding `--blocks` are each reported with their key and text, and the
    configuration's bytes for those lines are unchanged; the bindings in
    criterion 15's frozen copy of this repository's configuration
    (`tcw validate`, `require_artifact.py`, `commit-item-after-move.sh`)
    give no A13.

**The stores**

33. C9: in taxonomy, capabilities, files-backend work and Jira-backend work,
    each 3.x state file becomes its 4.0 name with the version first and the
    rest of the bytes unchanged (except C10, C11, C16 edits).
34. C10: every `id: cap-…` is gone and recorded; an `id:` equal to its
    folder name stays; a differing one in a taxonomy state file is A1.
35. C11: a nested term and a capability nested in another capability get
    `parent:` with their parent's full identifier; 4.0's `tcw validate`
    gives no folder-and-parent warning for them.
36. C11 and C12: a 3.x taxonomy folder with no `meta.yaml` and no
    `description.md` gets `tcw-taxonomy.yaml` with `name:` from its folder,
    and an empty `description.md`, each reported (D7); a capability with
    no `description.md` gets an empty one.
37. C13: a loose file and a loose folder in an item folder move into its
    `resources/`; a capability's `prependedDocs: [camera.md]` becomes
    `[resources/camera.md]` and its body in 4.0 includes the file; the
    exact text `docs/work/<folder>/design.md` in another item's spec
    becomes `docs/work/<folder>/resources/design.md`; the shortened
    `TCW-99-…/design.md` and `TCW-99-.../design.md` in a third item's spec
    are left as written and each is reported (A3) with its file and line;
    the exact text in a file outside the stores is left and not reported.
38. C14: overrides by bare id, by `<alias>/<id>`, from an unrelated folder
    (`ov/login` overriding `auth/login`), and in a middle project, each move
    to the original's id-path with `overrides:` removed; one already at its
    original's id-path does not move, loses only its key, and is not B9;
    4.0 shows each as overriding its original, with the same fields 3.x
    showed; D3 and D4 are reported where they apply.
39. C14 with a migrated source: a reader whose override's source has
    already been migrated resolves the pointer through the source's
    `.tcw/tcw-migration.yaml`; with that file deleted, B9; with the file
    naming an id-path the source no longer has, B9 whose message gives the
    fix by hand.
40. C14 blockers: a pointer to nothing, an ambiguous bare id, a pointer to
    the project's own capability, a target taken by another object, and two
    overrides of one original are each B9.
41. C16: one fixture per row of S110 Design 5.1's table converts each 3.x
    value to the full identifier 3.x resolves it to, including a bare
    capability path resolved locally and through `extends`, a
    `capabilities.yaml` entry routed to a child, and a `new:` entry naming
    a capability that does not exist, a `taxonomy:` entry resolved through
    the taxonomy store, a cross-project `blocked-by: other/<folder>`
    written by 3.x `--blocks`, and a prefixed reference to an override the
    source's migration moved (resolved through its `moved:`); a
    `](tcw://C/cli/x)` link outside code
    becomes `](tcw://<id>.capabilities/cli/x)` and the same inside a code
    span is unchanged; an ambiguous bare reference is B10.
42. B8 and B7: a folder named `has.dot`, a term named `resources`, a work
    item folder whose full identifier would be 256 characters, and a
    capabilities store containing the taxonomy store are each refused
    before anything is written.

**Jira**

43. In a fake Jira project shared by projects `app` and `lib`, `app`'s run
    edits each of `app`'s tickets with a 3.x value once, sending only the
    `TCW Item` field, to `app.work/<folder>`; `lib`'s tickets, `app`'s
    tickets already in 4.0 form, and tickets with no `TCW Item` get no edit.
44. A ticket of `app` whose value is `app/<folder>` with no such folder in
    the checkout is still converted; one whose 4.0 value would be over 255
    characters, and one holding `other/<folder>`, are A10 and not edited.
65. The edit and its settings: the fake records, for each converted ticket,
    exactly the request `rename` sends for the same field and value
    (`tcw/work/jira/backend.py:890-893`, compared request by request); the
    search and the edits use the field ids of the project's 3.x
    `work.jira.fields`, also when a 4.0 parent sets `fields.effort`
    differently (which is D1); and the backend method given the pairs the
    other way round puts every 3.x value back, editing no other field.
68. The Jira settings of a project already in 4.0 form (Design 5.1): after
    `tcw migrate --no-jira` on F-single, with `fields.item` in
    `.tcw/tcw-config.yaml` then changed by hand to another field name, the
    plain `tcw migrate` searches and edits that field; with the credential
    names set only in a 3.x root `tcw-config.local.yaml`, they are used;
    F-single's user-wide `not_tags` (A5) does not stop the run; and with
    `work.jira.project` removed from every layer, the run exits 1, names the
    file and key and `--no-jira`, writes nothing and edits no ticket.

**Families**

45. Order does not matter: F-full's family migrated in two different orders
    of its projects ends with identical files in every project.
46. Monorepo (UC-3, one git repository holding a root and three packages
    with UC-3's `extends`, one package keeping its work in Jira with only
    the keys 3.x requires): migrating that package first, its
    `tcw work list` stops with exit 7 naming the root and `work.jira`, a
    taxonomy listing with `--scope up` stops with exit 7, and its summary
    names the root as still 3.x with `tcw -C <root> migrate`; migrating the
    root next, the same `tcw work list` works; after each run the summary
    lists the projects still in 3.x form, parents first, with
    `tcw -C <folder> migrate`; after all four, 4.0's `tcw validate` passes
    in each (D8's warning allowed), and each package's taxonomy listing
    with `--scope up` holds the entries 3.x listed plus exactly those its
    D1 and D2 reports name.
47. Planning workspace (UC-4, two real git repositories): `app`, whose work
    store is `../docs/app/work` inside the workspace's repository, converts
    that store, names its files as left in the workspace's repository, and
    gets `work.path: tcw://<workspace>.path/docs/app/work`; the workspace's
    run changes nothing under `docs/app/work`.
48. A related project not on this machine: a parent named only for its
    location converts (C3, C4), and so do an upstream named by an `extends`
    (E2) and a listed child named by one (E3); one whose content E1 must
    read is B5, naming it and the folder, with a `git clone` line holding
    its repository and folder, and naming `tcw project provision` for after
    the migration.
49. Linked worktree: run in a worktree, migration changes files only in the
    worktree, and a 3.x personal file present only in the main checkout is
    A7 and unchanged.
50. Second person (Design 2.11): in a migrated project with a root
    `tcw-config.local.yaml` and a 3.x cache clone, a run moves the personal
    file into `.tcw/`, writes the personal manifest entry, changes no
    tracked file, and edits no ticket; the same after a first run made with
    `--no-jira` edits every ticket still holding a 3.x value.
64. The record after a move: a source `M`, migrated, whose capability
    `cli/x` had `id: cap-1`, is then changed by 4.0's move of `cli/x` to
    `cli/y`; the move rewrites `cap-1`'s value in `M`'s record to `cli/y`,
    and a 3.x reader of `M` with `overrides: M/cap-1`, migrated afterwards,
    moves its override to `cli/y`. Separately, `M`'s own override moved
    from `ov/login` to `auth/login` by its migration is under `moved:`, and
    a reader's 3.x reference `M/ov/login` becomes
    `M.capabilities/auth/login`.

**After a migration**

51. After F-full, 4.0's `tcw validate` reports exactly the findings A1 to
    A13 the run reported, and the load-order warning of each D8 the run
    reported, and nothing else; and the run's A12 findings are exactly the
    4.0 counterparts of the findings 3.x's own `tcw validate` gave on the
    fixture, written out once per fixture as a fixed expected list from the
    recorded 3.x output (so a finding a conversion caused, which 3.x did not
    give, fails the test even though the run listed it). `tcw work list`,
    `tcw taxonomy list --scope up` and `tcw capabilities list --scope up`
    list the same objects, by id-path and owner, as the fixture's recorded
    3.x listing, with the differences the run reported taken out first:
    the objects of each project and axis D1 names as newly inherited are
    removed from the 4.0 listing, and each object D2 or D4 names is
    compared by id-path and owner only, not by its fields.
52. The capability record `cli/migrate-a-tcw-3-x-project-to-tcw-4` exists
    with `Status: Supported`, the format-version record names `tcw migrate`,
    and `tests/test_documented_cli_surface.py` passes.

**This repository**

53. The proof of Design 9.2 is made, and recorded in the implement round
    with its counts: the dry run lists this project's tickets with their old
    and new values and edits none; the `--no-jira` run exits 0 after the
    local phases and sends nothing to Jira; the second `--no-jira` run
    changes no file; the stopped run of step 4 exits 1 and its re-run
    gives the same files git would track, with the same contents, as the
    first clone (Design 9.2 step 4); the run of step 5 exits 1 and
    writes nothing; with `tests/test_repo_config_pair.py` deleted the suite
    passes as CI runs it, and 4.0's `tcw validate` reports no error. The
    two loose files are under `resources/`, and the run reports as A3 each
    shortened mention `TCW-99-…/design.md` in the work store's specs (12 at
    `ebce3fd6`), each left as written; the count is recorded.
54. Every test that reads this repository's own records by a state file's
    name finds the record under either name (Design 8.4), and no test this
    item adds reads the root `tcw-config.yaml`, so in the proof
    clone the only test change the suite needs is deleting
    `tests/test_repo_config_pair.py`.
67. The guard exemptions (Design 8.2): each of TCW-110's, TCW-111's and
    TCW-112's guard tests exempts exactly the folders Design 8.2's table
    names, through its constants (`MIGRATION_FOLDERS` in TCW-110's and
    TCW-111's, `MIGRATION_CODE` and `MIGRATION_TESTS` in TCW-112's); in
    each, a test places
    the guard's forbidden text in a temporary file under an exempted folder
    (it passes) and in `tcw/migrate_x.py`, `tcw/store/x.py` and, for
    TCW-112's test-file rule, `tests/migrate_x/test_x.py` (each fails, naming
    the file).
55. No `TCW Item` on the live `TCW` board is edited by this item's
    implement or qa: every real run of the proof is made with `--no-jira`
    or without credentials (step 5, which refuses before writing), each
    with the unreachable proxy of Design 9.2, and only the dry run reads
    the board, its recorded requests holding no `PUT` and no `POST` but the
    search's.
56. The user's two setups: the qa findings record the dry run's counts,
    reports and blockers for each, without naming either (Design 9.5).
69. Migration's messages and git calls pass the existing guards (Design
    8.6): `tests/test_static_guards.py` passes with `tcw/migrate/` present,
    its `EXEMPT` set gaining only `("migrate/family.py",
    "absent_project_message")`; a stopped run prints `do not save these
    files in version control until 'tcw migrate' finishes`; B5's message
    holds the `git clone <repository> <folder>` line; and
    `tests/work/test_git_write_scan.py` scans `tcw/migrate/` and passes.

### Coverage

The axes are the Design rules above, and the blocker and report tables. A
cell is the criteria that check the rule, or `n/a` with the line that makes
it so.

| Design rule | Criteria |
| --- | --- |
| Build order: part 1 complete on its own, part 2 on top | F-single runs of 5-17, 51 and 60, and 66-68 (part 1 alone); 53 made after part 1 lands |
| 1.1 form, top level, no argument, `-C`; `--dry-run`; `--no-jira`; the Jira client never built with `--no-jira` (planning, phase F, the check after the run); read-only while planning, by an allowed list | 1, 3, 57, 66 |
| 1.2 nearest marker; exempt from every check before the command; no project | 1, 2, 3 |
| 1.3 what it reads; the user-wide file never written | 5, 30 |
| 1.4 only its own files; files left in another repository or a cache clone; the progress record | 47, 46, 60 |
| 1.5 standard error only; line form, ticket lines with both values | 1, 7 |
| 1.6 exit codes, Jira's kept as the backend gives them | 1 (2, 1), 8 (3), 12 (5, 1), 11 (1), 14 (0, 5), 57 (0), 58 (5, 1) |
| 1.7 no git check, no git change | 4 |
| 2.1 plan first, Jira included (the search's pages, the field-id reads, the edit screen); 4.0's file checks before writing, `tcw validate` after, offline | 5, 8 (B3, B16), 21, 51, 58, 59 |
| 2.2 a blocker refuses the whole run | 8, 9 |
| 2.3 dry run; Jira failing while planning writes nothing | 5, 6, 58 |
| 2.4 phases A to F; each state file written once; progress record deleted after E | 10, 11 |
| 2.5 each write whole; what a write is; a move across filesystems refused | 11, 13, 16, 60 (P5) |
| 2.6 never repeats a change; objects in either form are read; offline re-run | 14, 12, 62 |
| 2.7 progress record; following it; a deletion's own digest; B17; the stop points P1-P12; both-files rule; an operating-system failure stops with the run-again message; the Jira half of a re-run planned before it follows the record | 11, 12, 13, 57 (P12), 60, 61, 66 (the re-run's Jira half), 68 (P11, P12 settings), 69 (the message) |
| 2.8 text edited not regenerated (`config_edit`); moved bytes kept; only listed deletions; values recorded | 15, 16, 17 |
| 2.9 B1 | 8, 9, 20 |
| 2.9 B2 | 8, 27 |
| 2.9 B3 | 8, 22 |
| 2.9 B4 | 8 |
| 2.9 B5 | 8, 48 |
| 2.9 B6 | 8, 28 |
| 2.9 B7 | 8, 42 |
| 2.9 B8 | 8, 9, 42 |
| 2.9 B9 | 8, 9, 39, 40 |
| 2.9 B10 | 8, 41 |
| 2.9 B11 | 8, 13, 62 |
| 2.9 B12 | 8 |
| 2.9 B13 | 8 |
| 2.9 B14 | 8 |
| 2.9 B15 | 8, 19 |
| 2.9 B16 | 8, 59 |
| 2.9 B17 | 8, 60 |
| 2.9 A1 | 7, 34 |
| 2.9 A2 | 7, 51 |
| 2.9 A3 | 7, 37, 53 |
| 2.9 A4 | 7, 31 |
| 2.9 A5 | 7, 30 |
| 2.9 A6 | 7, 23 |
| 2.9 A7 | 7, 49 |
| 2.9 A8 | 7, 46 |
| 2.9 A9 | 7, 29 |
| 2.9 A10 | 7, 44 |
| 2.9 A11 | 7, 24 |
| 2.9 A12 | 7, 51 |
| 2.9 A13 | 7, 63 |
| 2.9 D1, D2 | 7, 32, 51, 65 (D1 for `fields.effort`) |
| 2.9 D3, D4 | 7, 38, 51 |
| 2.9 D5 | 7, 29 |
| 2.9 D6 | 7, 26, 27 |
| 2.9 D7 | 7, 36 |
| 2.9 D8 | 7, 25 (none arises from E4's placement), 46, 51 |
| 2.10 the summary | 46, 47, 57 |
| 2.11 a second person or machine; branches merged later | 50, 62 |
| C1 into `.tcw/`, version, `.gitignore`; empty files | 18, 19, 15 |
| C2 key renames | 20 |
| C3 `projects:` to `parents:`, `children:` | 21 |
| C4 M1 to M6 | 22, 23, 24 |
| C5 store locations; the store `repository` kept | 28, 47 |
| C6 `jira` blocks | 27, 17 |
| C7 the user-wide file | 30 |
| C8 E1 to E5 | 25, 26, 8 (E5 as B4) |
| C9 state files renamed | 33 |
| C10 ids | 34, 17 |
| C11 `parent:`; taxonomy folders without `meta.yaml` | 35, 36 |
| C12 completing objects | 36 |
| C13 `resources/`; exact mentions rewritten, shortened ones A3 | 37, 53 |
| C14 overrides; already at the original's path; through a source's record | 38, 39, 40, 61, 64 |
| C15 taxonomy at an inherited path | 32 (D2) |
| C16 references and links; `taxonomy:` entries; through a source's `moved:` | 41, 62, 64 |
| C17 Jira (Design 5.1-5.3) | 43, 44, 12, 65 |
| 4.1 which objects; work items by their folders; objects in 4.0 form read | 33, 36, 51, 62 |
| 4.2 name blockers before writing | 42 |
| 5.1 which tickets; the own layers' settings, in either form | 43, 65, 68 |
| 5.3 last, resumable; the window in which tickets are hidden | 12, 57 |
| 5.4 two methods inside the Jira backend; the same request as `rename`; the way back, given its client | 43, 65 |
| 6.1 either format; order does not matter | 26, 45 |
| 6.2 monorepo one at a time, parents first; what stops between runs | 46 |
| 6.3 planning workspace | 47 |
| 6.4 a library read by others | 39 |
| 6.5 a related project not here; B5 narrowed; its message | 48 |
| 6.6 a linked worktree | 49 |
| 7 the record; `moved:`; kept correct after a move; kept through 4.x | 17, 39, 64; "kept through 4.x" is n/a as behaviour: it is the absence of any removal rule (Design 7) |
| 8.1 registration and exemption | 2 |
| 8.2 3.x readers in one place, copied from `v3.0.2`; the siblings' guard exemptions | 67 (the exemptions); where the readers live is n/a as behaviour, and the readers it names (`tcw/store/project.py:616-667`, `tcw/store/fs.py:2344-2389`, `tcw/work/gates.py:331-380`) are exercised by criteria 21 to 41 against 3.0.2's recorded output |
| 8.3 records name `tcw migrate` | 52 |
| 8.4 tests reading the repository's records; no new test reads the root configuration | 54, 15, 63 |
| 8.5 TCW-114's move keeps the record correct | 64 |
| 8.6 messages pass the git-word guard, one exemption for B5's fetch line; `tcw/migrate/` in the git-write scan | 69, 48 |
| 9.1 records stay 3.x on `v4` | 55 (the live board), and this item's own records written in 3.x form (Capability changes) |
| 9.2 the proof | 53, 55 |
| 9.3 the real migration at the merge | n/a here: TCW-118 carries it out (`docs/work/TCW-99-…/design.md:831-833`, TCW-116 before TCW-118). What 9.2 proves of it: steps 2 and 3 (53); the request of step 6 (65) and step 2's edit-screen check (59). Steps 0, 1, 4, 5, 7 and 8 and the way back are TCW-118's to carry out and check |
| 9.4 the pair ends | 13, 15, 53 |
| 9.5 the user's setups | 56 |

## Risks

- **A 3.0.2 `tcw` in a migrated project.** It finds no root
  `tcw-config.yaml` and walks outwards, so in a project nested in a 3.x
  project, or in a worktree inside a 3.x primary checkout, it acts on the
  enclosing one. Old code reading new files is not a constraint
  (`docs/use-cases.md`, S-9); for this repository, Design 9.1 and 9.3 keep
  the two from meeting, and the migration guide (TCW-117) says to upgrade
  everyone who works on a project together.
- **New inheritance.** A 3.x parent link passed only work; a 4.0 one passes
  everything unless it says otherwise. A child may find its own objects
  merged with its parent's (D2) or new tags inherited (D1). D1 and D2 list
  each; the design's sign that the model is wrong is "many `null`
  removals or `inherit` lists" after migrating (design.md:806-807), and the
  qa dry runs in the user's setups (Design 9.5) are where it would show.
- **The record outlives its use.** `.tcw/tcw-migration.yaml` is kept
  through 4.x (Design 7); deleting it early turns late readers' pointers
  into B9. The migration guide (TCW-117) says to keep it.
- **Store `repository` declarations stay on the store**, while the design
  says a store's repository goes into a manifest entry (design.md:745-749).
  TCW-110 assigned that move to TCW-107, TCW-115 and this item
  (S110:160-162); TCW-107 kept the stores' declarations (S107:150-152) and
  TCW-115 provisions stores as today (S115 Design 7.2), so 4.0 as built
  reads `<component>.repository`, and migration writes what 4.0 reads
  (Notes, decision 4). The departure is raised on TCW-99.
- **The progress record holds personal values.** It is ignored by git from
  phase A, and deleted at the end of phase E; a person who commits a
  stopped run with `git add -f` commits it. The stopped run's message says
  `do not save these files in version control until 'tcw migrate'
  finishes` (Design 2.7, 8.6).
- **A ticket edit refused for some tickets only** (a permission set per
  ticket, which B16's check of one ticket cannot see) leaves those tickets
  hidden from `tcw work list` until a re-run converts them (Design 5.3).
- **A partly migrated family stops on what it inherits** (Design 6.2).
  Parents first avoids it; the summary says so.
- **Big repositories.** Phase C may rewrite many files. Each is written
  whole, and a stop is finished by running again; the cost is time, not
  safety.
- **Jira rate limits.** One edit per ticket; a run stopped by a refused
  request is finished by running again (Design 5.3).
- **A store with a mount point inside it.** A move across the mount point
  is refused, not copied (Design 2.5); the person moves the folder by hand
  and runs again. Rare, since every move stays inside one object folder or
  one store.
- **Text matched exactly.** C13 rewrites only exact mentions inside the
  stores; any other spelling of a moved file's path is A3, so a link can be
  left stale outside the stores. It is reported, never silent.

## Notes

### Decisions, each decided by the dispatching session, 2026-10-22

1. **A blocker stops the whole run before anything is written** (Design
   2.2): the simpler and safer of "refuse everything" and "convert what
   can be converted and report the rest", since a half-converted project
   is what the design's resumability exists to avoid. Most blockers are
   something 3.x `tcw validate` already reports or 4.0 could not read; the
   others (B5, B11, B13, B16, B17) are states in which migration would have
   to guess or overwrite.
2. **The user-wide file is reported, not converted** (A5; TCW-106's handoff
   1): it is outside every project, and any 3.x TCW on the same machine
   needs `not_tags` in it, as this repository's own 3.0.2 lifecycle does
   until the merge.
3. **Empty `.tcw/` files are not exempt** from the missing-version refusal
   (C1; TCW-106's review, S2): the design's rule that a file with no
   version is 3.x has no exception, and an exempt empty file would be a
   configuration with no `id`; `tcw migrate` fills them in.
4. **A store's `repository` declaration is kept on the store** (C5).
   TCW-110 left the move of a store's repository into a manifest entry to
   TCW-107, TCW-115 and this item (S110:160-162, which the first draft
   misread as TCW-110 keeping it). TCW-107 kept the stores' 3.x
   declarations (S107:150-152) and TCW-115 provisions stores exactly as
   today (S115 Design 7.2), so 4.0 as built reads `<component>.repository`;
   and a store whose repository holds no TCW project has no ID to key a
   manifest entry by. Migration writes what 4.0 reads. The design's "one
   location" is met only for the path, which becomes a plain path or a
   `.path` address. This departs from design.md:745-749 and from the
   request's "store `path` plus `repository` to one location"; as the
   request's Constraints require, it is raised on TCW-99 (the note in this
   revision's report), not settled here alone.
5. **A 3.x parent link becomes a plain parent ID** (C3), as the design and
   TCW-108's mapping say, with what newly flows down reported (D1, D2),
   rather than an `inherit` list reproducing 3.x: following the design is
   the rule for this item, and the report is what lets the person review it.
6. **A monorepo migrates one project at a time, in any order** (Design
   6.2; TCW-106's review, S1), with each conversion computed the same way
   whatever the other projects' state (Design 6.1), because the design has
   each project migrate itself (design.md:708-711).
7. **The opaque ids are kept in a record** (Design 7) rather than requiring
   readers to migrate before their sources: a public library cannot know
   its private readers (UC-7), so any order requirement could not be met.
8. **M5's committed path is `../<repository name>`**: TCW-107 left the
   choice to this item (S107:1103-1105); a folder beside the project is the
   layout 4.0's search already finds (S107 Design 2.4), and the personal
   manifest keeps this machine's cache clone in use.
9. **`--no-jira`** (Design 1.1), reversing the first draft's "no flag":
   the live board is protected by a flag a person can see, not by unset
   variables, which this user's shell sets for every command; the
   stopped-run path is exercised on real data by Design 9.2 step 4
   instead.
10. **Prose is not rewritten** (Non-goals), except exact mentions of moved
    files inside the stores (C13), which are mechanical and keep this
    repository's specs pointing at `design.md`.
11. **This repository is migrated at the merge, not on `v4`** (Design 9.1):
    the reasons are in 9.1; TCW-106's handoff ("prove it on a copy of
    `main`, then delete the root file on `v4`") is met by proving it on a
    clone holding both branches, and deleting the root file in the merge's
    migration commit, which is the first change after which no 3.x
    lifecycle reads this repository.
12. **A 3.x child item stays flat** (Non-goals), as TCW-111 decided
    (S111:1398-1401).
13. **`connected-projects` is a blocker** (B2), though TCW-108's handoff
    asks migrate to "handle" it: it is a 2.x key 3.x also refuses
    (`tcw/store/base.py:470-481`), and 2.x is out of scope by the request.
14. **No split** (build order, at the top): TCW-116 stays one item, as the
    earlier choices for TCW-111 and TCW-114 did; it is built as part 1, the
    engine this repository needs, landed and proven first, then part 2.
15. **A re-run follows a progress record** (Design 2.7) rather than
    planning again from a disk that phases B and C have changed: what a
    move or a resolved owner was cannot always be worked out again from
    what is left.
16. **Each 4.0 state file is written once** (Design 2.4), the `cap-…` id
    removal included, so a stop inside phase C never leaves a state file in
    a form other than its final one.
17. **A real run whose plan cannot reach Jira writes nothing** (Design 2.3),
    and Jira's exit codes stay the backend's (Design 1.6).
18. **The planned result is checked file by file before writing, and as a
    whole by `tcw validate` after** (Design 2.1), rather than through a
    temporary copy of the family.
19. **A monorepo is migrated parents first by recommendation, not by rule**
    (Design 6.2).
20. **Phase F uses the `work.jira` of the project's own layers, read raw
    from whichever files hold them, and writes no extra key** (Design 5.1,
    revised 2026-10-22 for the plan review's M4): the keys that find the
    tickets are the project's own in 3.x and stay its own in 4.0, and the
    same reading serves a project whose 3.x files phase E has already
    deleted.
21. **The record is kept through 4.x** (Design 7), and kept correct by
    TCW-114's move (Design 8.5).
22. **B5 is narrowed and its message names `git clone` now and
    `tcw project provision` after** (Design 6.5).
23. **The way back for the tickets is the same backend method with the
    pairs swapped** (Design 5.4, 9.3), and the first live write rests on
    the fake plus the request `rename` already sends (Design 9.3 step 6),
    not on a throwaway Jira project.
24. **`jira` blocks stay recorded** (Design 7), against the review's
    suggestion to report them only: recording them costs one list, and a
    project outside git has no history to find them in.
25. **A ticket's text is not read** (Non-goals): A3 searches only the
    project's stores, so a mention of a moved file in a ticket's
    description stays as written, as prose does.

Added when the spec and plan were revised after the plan's review
(2026-10-22), each decided by the dispatching session on that date:

26. **The 3.x readers are copied from tag `v3.0.2`** (header, Design 8.2):
    `32c510f0` already holds TCW-106's changes to them, and the goldens are
    recorded by 3.0.2.
27. **A deletion records the digest of the file it deletes** (Design 2.7):
    a hand edit between a stopped run and its re-run stops the run (B17)
    instead of being deleted.
28. **A move across filesystems is refused, not copied** (Design 2.5; the
    review's D1): it needs a mount point inside a store, and the copy path
    had holes a stop could fall into.
29. **`--no-jira` never builds a Jira client, and planning gets a read-only
    one** (Design 1.1; the review's S1).
30. **The Jira settings come from the project's own layers, in either
    form** (Design 5.1; the review's M4); see decision 20.
31. **The siblings' three guard tests each exempt `tcw/migrate/` (and
    TCW-112's test-file rule `tests/migrate/`), by a named constant matched
    by whole path parts, with a test of its reach** (Design 8.2; the
    review's M1).
32. **No new test reads this repository's root configuration**; criteria 15
    and 63 read a frozen copy (Design 8.4; the review's M6).
33. **The proof compares the files git would track, with their contents**,
    runs the virtual environment's `tcw` by its full path, and keeps every
    run after the dry run behind an unreachable proxy (Design 9.2; the
    review's M7, S1, S2).
34. **A12 is defined against 3.x's own `tcw validate`** (Design 2.9; the
    review's D3): the run lists what no report predicts, and criterion 51
    checks that list against 3.x's recorded output, so the criterion cannot
    pass by construction.
35. **A `capabilities.yaml` entry 3.x's router gives no ledger is B10**
    (Design 2.9; the review's question 4), including the part 1 case of a
    project that keeps no capabilities ledger.

Added after the re-check of the revised spec and plan (2026-10-22), each
decided by the dispatching session on that date:

36. **With `--no-jira`, the check after the run leaves out the work-store
    checks of a Jira-backed project, and says so** (Design 1.1, 2.1; the
    re-check's N1). Those checks build the Jira backend and client,
    though they send nothing. This keeps "never builds" true without a new
    mode in `tcw validate`.
37. **One function plans the Jira half, for a fresh run and for a run
    following a progress record, before anything is written** (Design 1.1,
    2.7; the re-check's N2). The progress record holds the project's ID and
    backend, so the re-run decides the same way. A Jira failure there
    writes nothing more.
38. **The read-only wrapper names the calls it allows** (Design 1.1; the
    re-check's S8).
39. **The messages are reworded to avoid git words, except B5's
    `git clone` line, which is exempted in one function** (Design 8.6; the
    re-check's N3). `tcw/migrate/` joins the git-write scan.
40. **The guards' constants are `MIGRATION_FOLDERS`, and `MIGRATION_CODE`
    with `MIGRATION_TESTS` for TCW-112's** (Design 8.2; the re-check's S1).
41. **The way back reads step 6's own output, and step 3 deletes
    `UNMIGRATED_RECORDS`** (Design 9.3; the re-check's S9).

### Handoffs answered

Every comment on this ticket, newest first, with the rule that answers it.
The comment of 18:50:52 headed "Handoff from TCW-109 (spec and plan,
revised)" was posted by mistake, as the correction of 18:51:17 says; it is
answered by the earlier TCW-109 row.

| From | What it asks | Design rule | Criteria |
| --- | --- | --- | --- |
| TCW-114 (19:01) | the delegate capability is deleted in 3.x form before migration: one record fewer | 4.1 (the conversion converts what is there) | 51 |
| TCW-114 (19:01) | `skills/work`'s record changes in 3.x form | 4.1, C9, C16 | 33, 41 |
| TCW-114 (19:01, 18:01) | a move is refused while a ticket holds a 3.x `TCW Item`; migration may convert by the folder the value names | 5.2, 5.3 (the value alone suffices, since items stay flat) | 43, 44, 12 |
| TCW-113 (19:00) | nothing to migrate; `--local` belongs in the guide | Non-goals (TCW-117) | n/a: no file or key changes (S113:1753-1754) |
| TCW-112 plan (18:54) | resolve each pointer to its target, never from the folder name; report a move onto a taken path and two overrides of one original | C14 steps 1-4, B9 | 38, 40 |
| TCW-112 plan (18:54) | remove `id: cap-…`; complete objects lacking `name`/`description.md`; report the attached-documents body change; this repository's records are 3.x | C10, C12, D3, Design 9 | 34, 36, 38, 53 |
| TCW-109 (18:50, mistaken) | — | see TCW-109 (17:59) | — |
| TCW-115 (18:49) | a repository-only connection's cache clone: write its path into the personal manifest when present, else name it | C4 M5, A6 | 23, 50 |
| TCW-112 (18:04) | move overrides and drop `overrides:`; drop `id: cap-…`; `extends` to parents; fill in `name` and `description.md`; report body changes | C14, C10, C8, C12, D3 | 38, 34, 25, 36 |
| TCW-114 (18:01) | as above | 5.2 | 43 |
| TCW-109 (17:59) | report `TCW_…__…` credential names; report a `null` at `work.tags`/`work.jira` | A9, D5 | 29 |
| TCW-106 review (17:48) S1 | a monorepo partly migrated: one at a time, or as a whole | 6.2, decision 6 | 46 |
| TCW-106 review (17:48) S2 | is an empty `.tcw/` file exempt from the missing-version refusal | C1 "Empty files", decision 3 | 19 |
| TCW-111 revised (17:03) | `rm` refuses on 3.x files below; a state file under `resources/` blocks removal: report it; `resources/` leaves the YAML check | A2, C13 | 37, 51 |
| TCW-108 revised (16:45) | invert an `extends` naming a listed child, dropping both halves, reported; handle locators, several parents and `connected-projects` | E3, C3, C4, B2 (decision 13), 6.1 | 26, 21, 22, 27 |
| TCW-106 (16:08) 1 | convert or only report the user-wide file's `not_tags` | C7, A5, decision 2 | 30 |
| TCW-106 (16:08) 2 | prove on a copy of `main`; delete the root `tcw-config.yaml` and the pair test | 9.2, 9.3, 9.4, decision 11 | 53, 13 |
| TCW-108 (15:43) | `parent` to `parents: [<id>]`; `children`; `upstream` with `inherit`; sibling or descendant `extends`; already-inherited to nothing; drop `jira` blocks | C3, C8 (E1-E4), C6 | 21, 25, 26, 27 |
| TCW-111 (15:42) | rename state files with a version; `parent:` for nested objects; state files for taxonomy folders; `resources/` with attached documents rewritten and links reported; reserved names and over 255; remove `cap-…` after overrides move; this repository at the merge | C9, C11, C13, A3, B8, C10 with phase order (2.4), 9.1-9.3 | 33, 35, 36, 37, 42, 10, 53 |
| TCW-107 and TCW-110 (14:45) | `projects:` entries to manifest entries (locator, `repository#ref`, `subfolder`, `checkout`, cache clones); no entry where 2.4 or 2.5 finds it | C4 M1-M6 | 22, 23, 24 |
| TCW-107 and TCW-110 (14:45) | report names breaking 1.1, stores nesting or coinciding, absolute or `~` store paths, 3.x `TCW Item` values, override folders at `<alias>/<path>` | B8, B7, C5/B6, C17, C14 | 42, 28, 43, 38 |

Things the siblings' specs and plans leave to migration that no comment
names, found by reading them:

- the root `.gitignore` line left dead (S106:442-444): A4;
- 3.x stored references and links in every field of S110 Design 5.1, and
  this repository's links and `capabilities.yaml` files (S110:167-173,
  P110:1311-1316): C16;
- a hand-written `id:` that differs from its folder (P111:1483-1489): A1;
- `tests/test_ledger_3_0.py` reading `meta.yaml` by name (P111:1483-1489):
  Design 8.4;
- a 3.x taxonomy term at an inherited path becoming an override (S112:157-160):
  C15, D2;
- a middle project's override now applied below (P112:292-305, choice 8): D4;
- `extends` targets in a project whose 3.x links did not pass them on, and
  several levels of `extends` now passing down (design.md:730-732): E1, E4, D1;
- the stale message "migrate with `tcw init --id`"
  (`tcw/store/project.py:596`): the plan checks whether TCW-107 or TCW-115
  has replaced it, and points it at `tcw project new` or `tcw migrate`;
- the 3.x `tcw://` link shapes (S110 Design 2.4): C16;
- a project fetched into the 3.x cache through a store's `repository`: kept
  working unchanged, since 4.0 provisions stores as 3.x did (S115 Design 7.2).

### Handoffs to later items

These are recorded on each ticket when this spec is accepted.

- **TCW-117 (guides, skills, use cases, migration guide):** document
  `tcw migrate`, `--dry-run` and `--no-jira`, the exit codes 0, 1, 3 and 5
  and which Jira failures give 1 and which 5; the blocker, "needs
  attention" and "reads differently" lists; that a run writes nothing when
  its plan cannot reach Jira; the progress record (what it is, that it is
  never committed, that a stopped run says `do not save these files in
  version control until 'tcw migrate' finishes`, and that deleting it while
  a run is unfinished means restoring the project first); migrating a family parents first, each
  project in its own folder or with `tcw -C`, and what stops in a package
  below a 3.x parent; that everyone working on a project upgrades
  together; how a second person finishes (Design 2.11), and running
  `tcw migrate` after merging a branch made before the migration; the
  user-wide file's `not_tags` (A5); commit or back up before a real run,
  and that a folder outside git has no way back; and
  `.tcw/tcw-migration.yaml`: what it is, that it is kept through 4.x, and
  to keep it in a library others read. Add the term `migration` where the
  format version is explained. `docs/use-cases.md` S-9 gains the 3.x-to-4.0
  migration as a seen case, and S-8 the progress record and its
  stop-and-run-again rule. A store's `repository` declaration stays on the
  store in 4.0 (decision 4).
- **TCW-118 (release):** carry out Design 9.3 at the merge of `v4` into
  `main`, steps 0 to 8 in that order, with the way back ready; then the
  user's setups (Design 9.5) after publication, for the success criterion
  "nothing fixed by hand".
- **TCW-108 (parent links):** its Step 8b deletes the 3.x `projects:` reader;
  this item restores what it needs from tag `v3.0.2` into its own
  module (Design 8.2), so Step 8b need not keep anything for migration.
- **TCW-111 and TCW-112:** the same for the `meta.yaml`, override pointer and
  `cap-…` readers they remove (Design 8.2). Their guard tests, and
  TCW-110's: see the handoffs below.
- **TCW-114 (moves):** nothing to build now. This item later adds to
  TCW-114's move and rename the rewrite of `.tcw/tcw-migration.yaml`
  (Design 8.5); keep the reference rewrites in one place, so that one more
  file can join them.
- **TCW-115 (`tcw project`):** nothing to change. `tcw project new` and
  `tcw project provision` stay refused inside a 3.x project, as every
  command but `tcw migrate` is; B5's message names `git clone` for now and
  `tcw project provision` for after the migration (Design 6.5). The
  cache-clone handoff is answered by C4 M5 and A6.

### Handoff to TCW-110

Handoff from TCW-116 (spec and plan, revised). TCW-116 copies 3.x readers
into `tcw/migrate/` that hold exactly what your guard
`tests/test_identifier_sweep.py` (P110 Step 15) forbids: `parse_tcw_uri`,
`.qualified`, `tcw://C/` and the other 3.x link shapes, and a project ID
joined to a folder name with `/` (the 3.x `TCW Item` and work-slug forms
it recognises). TCW-116 adds a named exemption for `tcw/migrate/` to that
guard (TCW-116 Design 8.2). To make that a one-line change rather than a
rewrite of your test, please:

- write the guard's scan as one function of a root folder (for example
  `findings(root) -> list[str]`), which the test calls on the repository;
- keep the folders it skips in one module constant, matched by whole path
  parts, and add `MIGRATION_FOLDERS = ()` beside it, empty in your item,
  which the scan also skips; TCW-116 sets it to `("tcw/migrate",)` and adds
  the test that the exemption reaches only that folder.

If your guard lands in another shape, TCW-116's plan (Step 2) reshapes it
that way with no change to what it finds, and says so in its implement
round. Nothing else in your item changes.

### Handoff to TCW-111

Handoff from TCW-116 (spec and plan, revised). TCW-116's `tcw/migrate/`
reads 3.x stores by `meta.yaml` and `item.yaml` and lists their folders,
which your guard `tests/test_object_folder_sweep.py` (P111 Step 17)
forbids outside `tcw/object_folders.py` and outside its allowlist. TCW-116
adds a named exemption for `tcw/migrate/` to both of its rules (TCW-116
Design 8.2). Please write the guard's scan as one function of a root
folder, and add `MIGRATION_FOLDERS = ()` beside its other skipped paths,
matched by whole path parts and skipped by both rules; TCW-116 sets it to
`("tcw/migrate",)` and tests its reach. If it lands in another shape,
TCW-116's Step 2 reshapes it with no change to what it finds.

### Handoff to TCW-112

Handoff from TCW-116 (spec and plan, revised). Your guard
`tests/test_no_3x_inheritance.py` (P112 Step 20) has two kinds of rule,
and TCW-116 needs an exemption from each: its rules over `tcw/` (the 3.x
federation messages and the names `_mint_cap_id`, `_apply_override` and
the rest), because each of migration's renamed copies names the 3.x
function it was copied from; and its rule over test files (`extends:`,
`overrides:`, `id: cap-`), because migration's fixtures under
`tests/migrate/` are 3.x projects. Please write each kind of rule's scan
as a function of a root folder, and add two constants,
`MIGRATION_CODE = ()` for the `tcw/` rules and `MIGRATION_TESTS = ()`
for the test-file rule, matched by whole path parts; TCW-116 sets them to
`("tcw/migrate",)` and `("tests/migrate",)`, keeps the files your test
already names for its refusal tests unchanged, and tests each exemption's
reach. If it lands in another shape, TCW-116's Steps 2 and 15 reshape it
with no change to what it finds.

### Handoff to TCW-114

Handoff from TCW-116 (spec and plan, revised). In addition to the TCW-114
entry above:

- `tests/move_stops.py`: TCW-116 drives it over a Python function as well as
  over a command (its executor's every-stop test runs before the command
  can convert anything). If the helper can take a callable that performs
  one run, nothing changes; if it takes only a command, TCW-116's Step 3
  adds that form beside it, with no change to how commands are driven.
  Please keep its patch of `_atomic_write_all` on the module attribute
  (`tcw.store.fs._atomic_write_all`); TCW-116 calls it through the module so
  the patch reaches it.
- `tests/processes.py`'s `allowed_read_only_git` stays as your item leaves
  it. TCW-116 needs `ls-files`, `status` (with `--no-optional-locks`) and
  `check-ignore` as well, and composes its own rule in its own test rather
  than widening yours, which also governs `move`.

### Handoff to TCW-117

Handoff from TCW-116 (spec and plan, revised). In addition to the TCW-117
entry above, the migration guide says:

- a move across filesystems (a store with a mount point inside it) is
  refused with a message, and is finished by moving the folder by hand and
  running `tcw migrate` again (Design 2.5);
- `--no-jira` never builds a Jira client, so it needs no credentials and
  cannot reach Jira; a dry run cannot edit a ticket (Design 1.1); with
  `--no-jira`, the check after the run leaves out the work store, and the
  person runs `tcw validate` for it;
- a stopped run, run again while Jira cannot be reached, writes nothing
  more; `tcw migrate --no-jira` finishes its files (Design 2.7);
- the Jira settings a run uses are the project's own `work.jira`, in its
  3.x or 4.0 files, never a parent's; a problem elsewhere in the
  configuration does not stop the ticket conversion (Design 5.1);
- a hand edit to a file between a stopped run and its re-run stops the
  re-run (B17), whether the file was to be rewritten or deleted (Design
  2.7);
- A12 lists findings the project already had in 3.x; a `capabilities.yaml`
  entry that 3.x could not route (no capabilities ledger and no child) is
  B10 (Design 2.9).

### Handoff to TCW-118

Handoff from TCW-116 (spec and plan, revised). For the merge procedure of
Design 9.3:

- run the merge clone's 4.0 `tcw` by its full path, never a bare `tcw`
  and never with the virtual environment first on `PATH` while a lifecycle
  command may run (Design 9.2);
- compare trees by the files git would track and their contents
  (`git ls-files --cached --others --exclude-standard` with a digest of
  each), never by raw folders, which differ in build leftovers;
- step 6's `tcw migrate` reads its Jira settings from the project's own
  `work.jira` in `.tcw/` (Design 5.1), so it does not depend on the 3.x root
  file deleted at step 2; a `not_tags` left in the user-wide file does not
  stop it, but every other 4.0 command refuses that file, so fix it before
  step 5 (A5 names the line);
- the way back for the tickets takes the Jira client as an argument
  (Design 5.4); build that client by hand from `.tcw/tcw-config.yaml` only
  when it is really needed;
- save step 6's output outside the repository; the way back undoes the
  edits it reports, and step 2's dry-run list is only a cross-check
  (Design 9.3);
- step 3 also deletes `UNMIGRATED_RECORDS` (TCW-117's handoff) and fixes
  the hits in that step; TCW-116's second proof records how many there
  are; step 3's suite runs with the credential variables unset.

### Citations at `v3.0.2`

Where each 3.x reader Design 8.2 copies sits at the tag (checked
2026-10-22). Every `tcw/store/fs.py` line this spec cites at `32c510f0`
from line 900 on is 20 lines later there than at the tag (`_same_folder`,
12); the content to copy is the tag's.

| Reader | At `v3.0.2` |
| --- | --- |
| the `projects:` reading, `_relation` | `tcw/store/project.py:614-668` |
| `RETIRED_PROJECTS_KEY`, `retired_key_problem`, `parse_connected_entry` | `tcw/store/base.py:469`, `:473`, `:865` |
| `_extends_ids` | `tcw/store/fs.py:884` |
| `_local_slugs`; the taxonomy `AmbiguousRef` | `tcw/store/fs.py:1743`; `:1796` |
| `_mint_cap_id`, `_is_capability`, `_all_meta_dirs` | `tcw/store/fs.py:2191`, `:2235`, `:2238` |
| `_override_index`, `_apply_override` (the match at `:2332`) | `tcw/store/fs.py:2281`, `:2324` |
| capabilities `get` and its `AmbiguousRef` | `tcw/store/fs.py:2405`, `:2419` |
| "missing Status" | `tcw/store/fs.py:2809` |
| `resolve_store` | `tcw/store/fs.py:3162-3300` |
| `_same_folder`, `_in_folder` | `tcw/store/fs.py:583`, `:593` |
| `_cache_root`, `_cache_key`, `checkout_root`, `provisioned_root` | `tcw/store/checkouts.py:60`, `:71`, `:95`, `:118` |
| `parse_tcw_uri`, `resolve_tcw_ref` | `tcw/refs.py:59`, `:84` |
| `route_capability_path`; `_LedgerReader.term` | `tcw/work/gates.py:331-380`; `:430` |
| `_LINK_RE`, `_strip_code` | `tcw/validate.py:48`, `:69` |
| `PERSONAL_KEYS`, `_merge` | `tcw/config.py:44`, `:454` |

### Citations at HEAD

Where the cited 3.x code sits at `ebce3fd6`, for every cited file TCW-107
has changed since `32c510f0` (`tcw/cli.py`, `tcw/config.py`,
`tcw/errors.py`, `tcw/store/base.py`, `tcw/store/fs.py`,
`tcw/store/project.py`, `tcw/validate.py`, `tcw/work/open.py`). The other
cited files (`tcw/project_files.py`, `tcw/refs.py`, `tcw/cli_help.py`,
`tcw/store/checkouts.py`, `tcw/store/config_edit.py`, `tcw/work/gates.py`,
`tcw/work/jira/*`) have not changed, so their lines hold at both commits.

| Cited at `32c510f0` | At `ebce3fd6` |
| --- | --- |
| `_dispatch`, `tcw/cli.py:641`; its checks `:649`, `:654`, `:658` | `tcw/cli.py:459`; `:467`, `:472`, `:476` |
| `build_parser`, `tcw/cli.py:549` | `tcw/cli.py:367` |
| `PERSONAL_KEYS`, `tcw/config.py:44` | unchanged, `:44` |
| `refuse_legacy_project`, `tcw/store/fs.py:310` | `tcw/store/fs.py:318` |
| `ignore_personal_file`, `tcw/store/fs.py:225` | `:229` |
| `_extends_ids`, `tcw/store/fs.py:904` | `:914` |
| `_local_slugs`, `tcw/store/fs.py:1763`; taxonomy `AmbiguousRef` `:1816` | `:1782`; `:1835` |
| `_mint_cap_id` `:2211`, `_is_capability` `:2255`, `_override_index` `:2301`, `_apply_override` `:2344` | `:2230`, `:2274`, `:2320`, `:2363` |
| `get`'s `AmbiguousRef`, `tcw/store/fs.py:2439` | `:2458` |
| "missing Status", `tcw/store/fs.py:2829` | `:2848` |
| `resolve_store` `:3182`; `StoreNotProvisioned` `:3314` | `:3201`; `:3333` |
| `projects:` reading, `tcw/store/project.py:616`; the stale `tcw init --id` message `:596` | `:855`; `:835` (still there) |
| `RETIRED_PROJECTS_KEY` `tcw/store/base.py:470`, `retired_key_problem` `:474`, `parse_connected_entry` `:866` | `:477`, `:481`, `:873` |
| `_strip_code`, `tcw/validate.py:70` | unchanged, `:70` |
| `_uncommitted_in`, `tcw/work/open.py:202` | `:209` |
