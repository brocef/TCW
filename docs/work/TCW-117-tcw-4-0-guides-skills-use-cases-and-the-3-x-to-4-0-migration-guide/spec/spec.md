# Spec — TCW 4.0: guides, skills, use cases and the 3.x-to-4.0 migration guide

Child 12 of 13 of TCW-99. It carries out the documentation half of the TCW-99
design (`docs/work/TCW-99-…/design.md`): "How 4.0 is built"
(design.md:809-841, "written alongside, finished last"), and the design's
promise that "the migration guide shows each step" of the epic-parts flow
(design.md:605-607). Every earlier child left the user-facing documents to this
item and posted what each must say on this ticket; Notes, "Handoffs answered",
maps every one of those comments and every deferral in a sibling plan's
Documentation Sync step to the rule below that answers it and the criterion
that checks it.

**Order.** This item's implement stage starts after TCW-106 to TCW-116 have
landed on `v4` (the ticket's position in the epic: "finished last"). So when it
starts, the code is 4.0 and the documents still describe 3.x, except where a
sibling changed a passage only as far as naming a working command (TCW-114
Design 9.5, TCW-115 Design 1.6). File and line references to documents are at
`b2fa5810` on `v4`, where TCW-106 is built and TCW-107 is being built; the
siblings move them, so the plan re-finds each passage by its words. References
to a sibling's rule are written "TCW-1nn Design m". This revision answers the
spec review (M1-M7, S1-S12, D1-D4), which read the spec at `1ddf57ed` and
`5a9ca9b7`, where TCW-116's plan landed as a first draft.

Terms used throughout:

- **A live document** is every Markdown file git knows about (tracked, or
  untracked and not ignored) whose path does not start with one of the
  prefixes in `ARCHIVAL` (`tests/test_documented_cli_surface.py:38-51`:
  `docs/work/`, `docs/plan/`, `docs/superpowers/`, `docs/changelogs/`,
  `docs/release-notes/`, `docs/migration-guide-`,
  `docs/tcw-3.0-migration-log.md`). That is exactly the list
  `_doc_files` in that test returns (215 files at `1ddf57ed`). It holds the
  documents a person or an agent reads to learn how TCW works now:
  `README.md`, `AGENTS.md`, `docs/guide/`, `docs/use-cases.md`,
  `docs/lifecycle/`, every skill under `skills/`, the plugin's agents under
  `agents/`, the shipped prompts and procedures under `tcw/work/`, and the
  descriptions in this repository's taxonomy and capabilities ledgers; and
  also `docs/releasing.md`, `docs/procedures/`, `tests/cli/scenarios/*.md` and
  `evals/assets/`. Every other Markdown file git knows about is **archival**.
- **The ledger records** are the `description.md` files under
  `docs/taxonomy/` and `docs/capabilities/`. They are live documents, but
  this repository keeps them, with their `meta.yaml` files and their 3.x
  `tcw://C/…` links, in 3.x form until TCW-118 migrates the repository at the
  merge (TCW-116 Design 9.3), so Design 9.2's test leaves them out until then.
- **A 3.x form** is a command, flag, key, file name or name format that TCW
  3.x has and 4.0 removes or renames (the list is Design 9.2's table).
- **A handoff** is a comment on this ticket, from a sibling, saying what this
  item must write (H1 to H20 in Notes); **a deferral** is a row of a sibling
  plan's Documentation Sync table that says "deferred to TCW-117" (D106 to
  D116 in Notes).

## Capability changes

- **Changed** `skills/work`: beyond TCW-114's one sentence, the skill teaches
  `--scope` and `--project`, running a change in another project with
  `tcw -C <folder>` and `tcw project path <id>`, `--nest` with `--parent`,
  `tcw work move` and `rename`, full identifiers, and exit 7.
- **Changed** `skills/taxonomy`: inheriting through parent links instead of
  `extends`, an override at the same path, `--scope up` for inherited entries,
  and `rename` and `move`.
- **Changed** `skills/capabilities`: the same for capabilities, mixed status
  under `--scope down` and `all`, `--parent` on `add` and `set`, and getting
  another project's wording through `tcw -C` or that project's own issue
  tracker.
- **Changed** `skills/configure`: parent links and what each passes down,
  manifests, store locations as `.path` addresses, inherited configuration,
  personal settings and environment overrides; "connected projects and
  creating items in them" and "inheriting another project's taxonomy" go.
- **Changed** `skills/setup`: a project is made with `tcw project new`, a
  related project is fetched with `tcw project provision`, and a 3.x project
  is moved over with `tcw migrate` and the migration guide.
- **Taxonomy:** no term is added or removed. The terms 4.0 adds or removes
  (`migration`, `parent-link`, `load-order`, `owning-project`,
  `upstream-project`) are declared by the items that change them (TCW-116,
  TCW-108, TCW-114). A term's description whose prose the one-off scan of
  Design 9.8 flags is corrected in prose and listed in the implement round.

The five records exist (`docs/capabilities/skills/{work,taxonomy,capabilities,configure,setup}/`,
checked at `b2fa5810`). **Every record is edited in 3.x form**, as every
sibling's was (TCW-116 spec, Capability changes; S110:167-173): each keeps its
`meta.yaml` and its 3.x `tcw://C/…` links, because this repository's lifecycle
runs on the 3.0.2 `tcw` first on the path until TCW-118 migrates it, and that
`tcw validate` resolves those links in every Markdown file of the stores
(`docs/guide/linking-and-validation.md:80`). Only the prose of a description
says what 4.0 does. Beyond the five, a capability description whose prose
still states a 3.x form when the one-off scan of Design 9.8 runs is corrected
here and added to `capabilities.yaml` under `changed:` at implement. Decided
by the dispatching session, 2026-10-22: the ledger is read by agents through
`tcw capabilities show`, so a stale description is the same defect as a stale
guide; the 3.x links are left for `tcw migrate` to convert at TCW-118 (TCW-116
C16), since rewriting them now would break the 3.x `tcw validate` this
repository's lifecycle runs.

## Problem

Every document a person or an agent reads describes TCW 3.x, and once the
siblings land on `v4`, each of them describes a CLI that no longer exists.
Grounded at `b2fa5810`:

1. **The README teaches removed commands and the 3.x model.** Its command table
   lists `tcw init`, `tcw provision`, `tcw projects list` and
   `tcw config show` (`README.md:263-273`); it says a repository adopts TCW
   with `tcw init`, which "writes a `tcw-config.yaml`" (`:275-282`); its
   "Many repositories" paragraph says projects connect "under `projects`",
   as "an `upstream` it reads", inherit by `extends`, and address items as
   `<project-id>/<folder>` (`:289-300`); and an item's slug is
   `project/folder` (`:255-257`). The cloud section says to run
   `tcw provision` (`:231-235`).
2. **The guide on related projects is built on the three mechanisms 4.0
   removes**: `projects` (`docs/guide/multi-repo.md:25`), `upstream` (`:70`),
   creating an item in another project (`:139`), `tcw provision` (`:223`) and
   `extends` (`:257`); its first line defines a project as "a folder holding
   a `tcw-config.yaml`" (`:3`).
3. **The skills teach 3.x to agents.** The work skill's "Delegation is filing
   into another project, with `tcw work new "<title>" --project <id>`" and its
   exit-code rules (`skills/work/SKILL.md:93-115`); the taxonomy and
   capabilities skills say a project may inherit "a parent, a child, or an
   `upstream`" through `extends add` (`skills/taxonomy/SKILL.md:107-109`,
   `skills/capabilities/SKILL.md:118-121`). The procedures teach 3.x slugs:
   "that project's slugs (`<project>/<folder>`); `tcw projects list`"
   (`tcw/work/procedures/search.md:25-28`) and "Use bare slugs"
   (`tcw/work/procedures/pause-work.md:22`).
4. **The other guides** state 3.x file locations and layers
   (`docs/guide/configuration.md:3`, `:32-33`), the web app serving "one
   project, the one it was started in" (`docs/guide/web-viewer.md:17-19`),
   and "Federating and overriding a capability" through `extends` and
   `overrides:` (`docs/guide/taxonomy-and-capabilities.md:205`).
5. **`docs/use-cases.md` describes 3.x setups**: a family is projects
   "connected … through `projects:`" (`:19-20`); its dimension table has an
   "Inheritance (`extends`)" row and an "upstream" value (`:90`, `:92`); UC-1
   shows a root `tcw-config.yaml` and `find_project_root` (`:109`,
   `:129-131`); UC-2 to UC-6 rest on `upstream`, `extends`, `parent: app:
   ../..`, `--project` and `tcw provision` (`:141-147`, `:185-218`,
   `:247-256`, `:347-365`); S-5 says "Another project's personal file is
   never read" (`:524-525`), which TCW-107 and TCW-109 both narrow; S-10 says
   "The current project is the nearest `tcw-config.yaml`" (`:638-642`). Six
   known gaps are closed or narrowed by 4.0 children and still listed
   (`:232-236`, `:301-303`, `:339-340`, `:369-378`, `:423-424`).
6. **There is no guide from 3.x to 4.0.** `README.md:760` links eight
   migration guides, the last 2.8 to 3.0; TCW-116 leaves the guide for
   people and scripts to this item (TCW-116 Non-goals, "The migration
   guide").
7. **The agent guides and the eval cases name 3.x paths.** `AGENTS.md:39`,
   `:52` and `:170` say the bindings and documentation entries are in
   `tcw-config.yaml`; `docs/lifecycle/implementation.md:24` draws a layout
   with a root `tcw-config.yaml`; the eval case B11 grades that
   `tcw-config.yaml` alone changed (`evals/evals.json:973-978`), though the
   fixture now writes `.tcw/tcw-config.yaml` (TCW-106, deferred here by
   TCW-106's spec, Non-goals).
8. **Seven passages of the TCW-99 design no longer say what was decided.**
   design.md:467-470 says listings mark each override, and :649-651 that a list
   shows a mixed-status summary; the user decided on 2026-10-22 that a plain
   listing stays one identifier per line (TCW-112 Notes; TCW-113 Notes). The
   sketch at :657-665 shows statuses with no `--scope`, which they need
   (TCW-113). design.md:745-746 moves a store's `repository` into the
   manifest, which TCW-116 decision 4 departs from and the dispatching session
   settled on TCW-99 (2026-10-22, 21:06). design.md:484-485 lists
   `work.backend` among the inherited keys, though the user decided on
   2026-10-22 that it is never inherited (TCW-109's note on TCW-99, 17:59).
   design.md:516-518 gives `TCW_WORK_PATH__MY_PROJ` as an example, which the
   user said should be corrected (TCW-99 comment of 15:28), and :531-533
   gives `TCW_WORK_JIRA__APP` and `TCW_WORK_JIRA_SITE__APP`, which the allowed
   list refuses (TCW-109's note on TCW-99, 17:59, departure 4).

## Goals

- Every live document describes 4.0 as it landed on `v4`, and names no 3.x
  form except in a passage about moving from 3.x.
- A 3.x user, or an agent acting for one, can move a project or a family to
  4.0 with one guide: what to do first, how to run `tcw migrate`, how to read
  what it prints, and what replaces each removed command, flag, key and file.
- `docs/use-cases.md` describes each setup as 4.0 handles it, with every gap
  4.0 closes removed and every gap it narrows re-marked.
- Every handoff and deferral addressed to this item is answered, and the
  answer is checkable.
- A permanent test keeps 3.x forms out of live documents.

## Non-goals

- **Release notes for 4.0** (the request's "Out of scope"; TCW-118). This item
  writes only its own `upcoming/` entry files (Design 10), which TCW-118's
  version cut combines.
- **Changing what any command does, or any message it prints.** Where the code
  disagrees with a sibling's spec, the document follows the code and the
  disagreement is reported to the dispatching session (Design 1.1); it is not
  fixed here.
- **Archival documents**: finished work items, changelogs, release notes, the
  earlier migration guides and `docs/tcw-3.0-migration-log.md` record history
  and are not changed. The one exception is the TCW-99 design, which Design 8
  amends where a recorded decision departs from it.
- **New eval cases.** A case for the epic-parts flow through `tcw -C` needs a
  fixture of two related projects, which `evals/seed_fixture.py` does not
  build. Only the cases whose expected files or wording 4.0 changes are
  updated (Design 9.6). Decided by the dispatching session, 2026-10-22: a new
  fixture is its own change. The existing cases measure routing and the
  single-project flows only, which is why a paid run of them is not an
  acceptance criterion here (Design 9.6 (c)).
- **Renaming documents.** `docs/guide/multi-repo.md` keeps its file name (Design
  4.5), and `tests/test_docs_describe_3_0.py` keeps its name.
- **Migrating this repository** (TCW-118, by TCW-116 Design 9.3).
- **A design decision.** Where a document needs a rule no sibling or the
  design settled, it is raised on TCW-99, not settled here (the request's
  Constraints). Design 8 amends the design only where a decision is already
  recorded.

## Design

The documents are the deployment of every sibling's design, so each rule
below names the facts a document must state and where each fact is decided.
How a document is worded is the implement stage's; what it must contain is
fixed here.

### 1. Rules for every document

1.1. **The code decides.** Each statement is checked against the code on `v4`
when it is written (running the command where it can be run), not against a
sibling's spec alone. Where a sibling's implement round records that the code
departs from its spec, the code wins. A disagreement found while writing is
listed in this item's implement round and reported to the dispatching session.

1.2. **Starting points.** Several siblings changed a passage only as far as
its own change needed, and left what the passage means to this item. Each
such passage is rewritten here for 4.0, and the implement round of this item
lists each with what it now says. The lists, each read from that sibling's
implement round as landed (or, where the round has no list, from the plan
step named). A passage a sibling rewrote in full for 4.0 (its own prompts and
procedures) is kept as that sibling wrote it, except that a 3.x form the scan
or the grep of Design 9 still finds in it is fixed here, with the smallest
change of wording, and listed in the implement round with the sibling it came
from (Decided by the dispatching session, 2026-10-22, plan review M2: the
scan of every live document cannot pass otherwise, and every sibling is
complete by the time this item is implemented):

- TCW-107: `skills/work/SKILL.md:115`, what to suggest on exit 5 (TCW-107
  plan, Documentation Sync; H2);
- TCW-108: the exit-code table in `docs/guide/cli.md` (TCW-108 plan, Step 3)
  and the exit-code table in `skills/work/references/commands.md` (H4);
- TCW-112: the passages of its Steps 5a and 19, which name no removed command
  and state no removed override rule but explain nothing more (H12);
- TCW-113: `README.md:413`, `docs/guide/taxonomy-and-capabilities.md:32` and
  `:98`, and `skills/capabilities/SKILL.md:176`, changed only as far as
  `--local` (TCW-113 plan, Step 12b; H16);
- TCW-114: the passages of its Step 7 (H14);
- TCW-115: the passages of its Design 1.6, in 43 files (H15).

Decided by the dispatching session, 2026-10-22: the grep and the scan of
Design 9 look for forms, not for stale meaning, so a passage left in its
"only as far as" state would pass them; the lists are the only record of
where those passages are.

1.3. **Plain language** (this repository's `AGENTS.md`, "Generic instructions",
and the user's instructions): every technical term is defined in the sentence
where a document first uses it. "Full identifier" is the proper name; each
document that says "slug" says once that it is a nickname for the full
identifier (TCW-110 Notes; design.md:234-236).

1.4. **One token after `-C`.** Every `tcw -C` a live document writes gives its
target as one word (`tcw -C <folder> …`, `tcw -C tcw://<id>.path/ …`), because
the three document checks skip `-C` and exactly one following word (TCW-115
Design 1.6; H15).

1.5. **One home per fact.** Each fact has one home document that states it in
full; every other document states it in a sentence and links there. The homes:

| Fact | Home |
| --- | --- |
| The `.tcw/` folder, its files, the version line, layers, inherited keys, `null`, `inherit: true`, environment overrides, the allowed list | `docs/guide/configuration.md`, with every key's exact shape in `skills/configure/references/` |
| Parent links, children, manifests, locating a project, the load order, a related project not here, stores in another repository, provisioning and its bound, worktrees | `docs/guide/multi-repo.md` |
| Full identifiers, their input forms, `tcw://` addresses, `tcw validate`'s findings | `docs/guide/linking-and-validation.md`, with input forms in `docs/guide/cli.md` |
| Inheritance and overrides of taxonomy and capabilities, mixed status | `docs/guide/taxonomy-and-capabilities.md` |
| `--scope`, `--project`, `-C`, output records, exit codes | `docs/guide/cli.md` |
| What a command does to a ticket | `docs/guide/jira.md` |
| The work item folder, nested items, moving and renaming items | `docs/guide/work.md` |
| What changes from 3.x and how to move over | `docs/migration-guide-3.X-to-4.0.0.md` |

1.6. **A 3.x form only in a passage about 3.x.** A live document may name a
3.x form only in a paragraph that also names `tcw migrate` or links the
migration guide (Design 9.2 checks the second half; review checks the first,
that the paragraph says the form is 3.x's). Three limits on this:

- (a) **The allowance never covers a removed command or flag.** Once TCW-112
  to TCW-115 land, `test_documented_cli_surface` fails on a removed command
  or flag in any code span of a live document, whatever the paragraph says
  (TCW-115 Design 1.6), and the grep of Design 9.3 forbids them in prose too.
  So outside the migration guide, which is archival, a removed command is
  named by its verb alone (`init`, in a table whose header says the verbs are
  removed) and never written as `tcw <verb>`. The allowance covers keys,
  file names, and address and slug forms only.
- (b) **A fenced code block cannot carry the allowance.** `blocks` reads each
  line of a fenced block as a block of its own (`tests/doc_vocabulary.py:70-99`),
  so no line of it can also name `tcw migrate`. A live document shows no 3.x
  example in a fenced block; it describes the 3.x form in a sentence and
  links the migration guide, which holds the examples.
- (c) **A passage about 3.x says so without the words the 3.0 scan bans.**
  `PATTERNS` in `tests/doc_vocabulary.py:51-52` bans "no longer",
  "previously" and "since 3.0" in the README, the guides, the lifecycle
  documents and the configure skill. Such a passage is written "In 3.x, …; in
  4.0, …" or "a 3.x project …". The 3.0 table is not loosened (decided by the
  dispatching session, 2026-10-22: it guards against documents written as a
  history of changes, which is still the rule for 4.0's documents).

1.7. **Two layers, said once.** Where a guide describes manifests, locating a
project's folder, `.path` addresses, provisioning or worktrees, it says these
are about folders on this machine (the deployment layer, design.md:113-133),
and that parent links, full identifiers, ownership, inheritance, overrides
and `--scope` are what every store keeps.

1.8. **Every harness.** No skill change makes a required step depend on a
Claude-only feature; every `` !`cmd` `` injection keeps its written fallback
(`docs/lifecycle/harness.md`; `test_every_injection_has_a_manual_fallback`).

### 2. The migration guide

2.1. **The file** is `docs/migration-guide-3.X-to-4.0.0.md`, following the
names of the guides before it (`docs/migration-guide-1.X-to-2.0.0.md`). Its
path starts with `docs/migration-guide-`, which `ARCHIVAL` already excludes
from the command check, so its 3.x columns may name removed commands; its 4.0
columns are checked by a test of its own (Design 9.4). It is linked from the
README's documentation index, from `docs/use-cases.md` S-9, from the `setup`
skill, and from `docs/guide/configuration.md` where a 3.x project is described.
It is written for a person and an agent alike: steps in order, each command
written out.

2.2. **Its level-2 sections, in this order:**

1. `## Before you start`
2. `## Migrating one project`
3. `## Migrating related projects`
4. `## What each 3.x name becomes`
5. `## The epic-parts flow, step by step`
6. `## Personal settings and environment variables`
7. `## Where provisioning may place a clone`
8. `## Scripts, hooks and agent instructions`

2.3. **Before you start** says:

- (a) 4.0 migrates 3.x projects only; a project still in 2.x form first
  follows [`migration-guide-2.8-to-3.0.0.md`](migration-guide-2.8-to-3.0.0.md)
  with a 3.x `tcw` (design.md:688-689);
- (b) commit or back up the project first; a folder that is not in git has no
  way back (H18);
- (c) everyone working on a project upgrades the CLI and the plugin together,
  because 4.0 reads only 4.0 files and refuses a 3.x project it reaches
  (`docs/use-cases.md` S-9; design.md:708-711; H18);
- (d) how to install the 4.0 CLI and plugin (the commands the README gives);
- (e) a project whose work is kept in Jira needs its Jira credentials for the
  ticket step, or runs with `--no-jira` and converts the tickets later;
- (f) continuous integration (CI) jobs and other automation that install
  `tcw-cli` without a version limit get 4.0 as soon as it is published, and
  fail on a project not yet migrated: limit them below 4 (for example
  `pipx install 'tcw-cli<4'`) until the project is migrated, then raise the
  limit in the same change as the migration (spec review S3).

2.4. **Migrating one project** says, from TCW-116 as landed (H18, H19, H20):

- (a) `tcw migrate --dry-run` first: it lists every file and ticket it would
  change and changes nothing (TCW-116 Design 2.3);
- (b) the three lists a run prints and what each means, with their printed
  headings: `refused:`, the blockers, which refuse the whole run and write
  nothing; `needs attention:`; and `reads differently in TCW 4:` (TCW-116
  Design 2.9, 1.5); and the line forms the guide quotes, as TCW-116's plan
  gives them in its Decided 14 ("Line forms"): `write <path>: …`,
  `move <old> -> <new>: …`, `delete <path>: …`,
  `edit <KEY>: … TCW Item: <old> -> <new>`, each with `would ` first in a dry
  run; `<An|Dn> <where>: <text>` under the two report headings; and
  `<Bn> <where>: <why>; <what to do>` under `refused:`. The plan is cited by
  its words, since it was a first draft when this spec was revised; each form
  is checked against `tcw migrate`'s output on `v4` (Design 1.1) (M7);
- (c) `tcw migrate`, and `--no-jira`, which converts the files only, never
  contacts Jira, and is the way to keep a run off a live board, and to convert
  the files when Jira cannot be reached; a later `tcw migrate` then converts
  only the tickets (TCW-116 Design 1.1; TCW-116 plan, Step 27). Until that
  later run finishes, 4.0's `tcw work list` leaves out every ticket that still
  holds a 3.x value, with one warning naming their keys and `tcw migrate`, so
  the board looks emptier than it is (TCW-116 Design 2.3, 5.3) (S3);
- (d) a real run whose plan cannot reach Jira writes nothing, and says to use
  `--no-jira` (TCW-116 Design 2.3);
- (e) a table of exit codes whose rows are exactly 0, 1, 2, 3 and 5, each with
  TCW-116 Design 1.6's meaning; it says a Jira failure keeps the code every
  command gives it: 5 when Jira cannot be reached or limits requests, 1 when
  credentials are missing or refused;
- (f) the progress record `.tcw/tcw-migration-progress.yaml`: what it is, that
  it is never committed (inside git it is ignored), that a run that stops is
  finished by running `tcw migrate` again, and that deleting it while a run is
  unfinished means restoring the project from the commit or backup of
  2.3 (b) first (TCW-116 Design 2.7); and that a run stopped partway names its
  progress record and says, quoted as printed,
  `do not save these files in version control until 'tcw migrate' finishes`
  (TCW-116 plan, Step 27; H20) (M7);
- (g) a second person, after pulling the migrated project, runs `tcw migrate`
  too, which converts their own untracked files; anyone runs it again after
  merging a branch made before the migration (TCW-116 Design 2.11);
- (h) the migration record `.tcw/tcw-migration.yaml`: what it holds, that it
  is committed, that it is kept through 4.x, that a library others read must
  keep it, and that a project whose every reader has migrated may delete it
  (TCW-116 Design 7);
- (i) `not_tags` in the user-wide file is reported, not changed, because a 3.x
  `tcw` on the same machine reads that file too; the report gives the line to
  change once no 3.x `tcw` is used (TCW-116 A5);
- (j) `tcw migrate` does not check git and commits nothing (TCW-116 Design
  1.7);
- (k) placed first in the section: a project with parents or children reads
  "Migrating related projects" before running anything (spec review S3);
- (l) the way back: restoring the commit or backup of 2.3 (b) brings the
  files back at any time, but not the tickets: once a run has converted them,
  no command puts a ticket's 3.x `TCW Item` back (TCW-116 Design 5.4, 9.3). So a project whose work is kept in Jira runs
  `--no-jira` first, checks the result (`tcw validate`), and converts the
  tickets last (S3);
- (m) a store with a mount point inside it (a move across filesystems) is
  refused with a message, and is finished by moving the folder by hand and
  running `tcw migrate` again (TCW-116 Design 2.5; H19);
- (n) `--no-jira` never builds a Jira client, so it needs no credentials and
  cannot reach Jira; a dry run cannot edit a ticket (TCW-116 Design 1.1; H19);
- (o) the Jira settings a run uses are the project's own `work.jira`, in its
  3.x or 4.0 files, never a parent's, and a problem elsewhere in the
  configuration does not stop the ticket conversion (TCW-116 Design 5.1; H19);
- (p) a hand edit to a file between a stopped run and its re-run stops the
  re-run (B17), whether that file was to be rewritten or deleted (TCW-116
  Design 2.7; H19);
- (q) A12 lists findings the project already had in 3.x, and a
  `capabilities.yaml` entry that 3.x could not route (no capabilities ledger
  and no child) is B10 (TCW-116 Design 2.9; H19);
- (r) with `--no-jira`, in a project whose work is kept in Jira, the check
  after the run leaves out the work store, and the summary says, quoted as
  printed,
  `work store not checked after the run (--no-jira): run 'tcw validate' to check it`
  (H20);
- (s) a run stopped partway and run again while Jira cannot be reached writes
  nothing more, exits with Jira's code (as (e) gives it), and says, quoted as
  printed,
  `nothing more was written; 'tcw migrate --no-jira' finishes the files without Jira`
  (H20).

2.5. **Migrating related projects** says:

- (a) each project is migrated by running `tcw migrate` in it, from its own
  folder or with `tcw -C <folder> migrate`; a run never changes another
  project (TCW-116 Design 1.4);
- (b) parents before children, and why: in a 4.0 package below a 3.x parent,
  every command that needs something inherited stops with exit 7 until the
  parent is migrated, which for a Jira-backed package is every command that
  reaches Jira; commands reading only the package's own records and keys work
  (TCW-116 Design 6.2; H18);
- (c) each run's summary lists the family's projects still in 3.x form,
  parents first, each with its `tcw -C <folder> migrate` (TCW-116 Design 2.10);
- (d) a planning workspace holding other projects' stores: each project
  converts its own store, and the files changed in another repository are
  listed under "left in another repository" for that repository's people to
  commit (TCW-116 Design 1.4, 6.3);
- (e) a related project whose content a conversion must read and that is not
  on this machine stops the run, naming the `git clone` command; after the
  migration `tcw project provision` fetches related projects (TCW-116 Design
  6.5);
- (f) a link `extends` made to a sibling becomes a parent link inheriting only
  the axes it named, an `upstream` becomes a parent link, and each is printed
  for review (design.md:724-740; TCW-116 D1, D6).

2.6. **What each 3.x name becomes** is one or more mapping tables. A mapping
table is one whose header's first cell begins with `3.x`; its first column
holds a 3.x form, its second what replaces it (empty is not allowed; "removed"
with what to do instead is a replacement). Together the tables hold a row for
every 3.x form of Design 9.2's table, and these rows in particular:

- (a) the removed commands and their replacements: `tcw init` → `tcw project
  new`, `tcw projects list` → `tcw project list`, `tcw config show` →
  `tcw project config` (with `--origin`), `tcw provision` →
  `tcw project provision` (TCW-115 Design 1.2; H10, D115);
- (b) the removed flags: `tcw work new --project` and `tcw work edit --blocks`
  (TCW-114 Design 3.1, rows a and f), and `--local` on the list commands
  (TCW-113; H13);
- (c) `tcw taxonomy extends add|rm` and `tcw capabilities extends add|rm`, and
  the `taxonomy.extends` and `capabilities.extends` keys → a parent link with
  `inherit` (TCW-112; H9);
- (d) the configuration: the root `tcw-config.yaml` and
  `tcw-config.local.yaml` → `.tcw/`; `not_tags` → `not-tags`;
  `projects.parent`, `projects.children`, `projects.upstream` → `parents:`,
  `children:` and manifest entries; a connection's `repository` → the
  manifest entry; a `jira` block under `projects:` → removed; an absolute or
  `~` store path → a relative path or a `.path` address; a store's
  `repository` **stays on the store** (TCW-116 decision 4; settled by the
  dispatching session on TCW-99, 2026-10-22, 21:06; H18);
- (e) the files: `meta.yaml` → `tcw-taxonomy.yaml` or `tcw-capability.yaml`,
  `item.yaml` → `tcw-work-item.yaml`, each with a `tcw-version` line; an
  `overrides:` pointer → an object at the original's path; a capability's
  `cap-…` id → none (TCW-106, TCW-111, TCW-112);
- (f) names and addresses: a slug `<project>/<folder>` →
  `<project>.work/<folder>`; `tcw://C/…`, `tcw://W/…`, `tcw://<id>/T/…` →
  `tcw://<project>.<namespace>/<id-path>`; a ticket's 3.x `TCW Item` value →
  the full identifier (TCW-110; H5);
- (g) output a script reads: JSON `"schema": 1` → `2`, with `full-id` and
  `owner`; the `--origin` comment → `# <project>, <layer> <file>` (TCW-110
  Design, TCW-115 Design 4.2; H10).

It also lists, after the tables, what reads differently with no name change:

- (h) plain `tcw taxonomy list` and `tcw capabilities list` list only the
  project's own entries, and `--scope up` adds inherited ones; `show <id-path>`
  of an inherited entry needs `--scope up` (TCW-113; H13);
- (i) a plain listing carries no override mark and no status summary; both are
  in `--json` and `show` (TCW-112 and TCW-113 Notes; H9, H13);
- (j) a command that needs a related project that is not here, or a setting
  only it could give, exits 7 instead of 5 or 1, and says how to fetch it
  (TCW-108 Design 6.2; TCW-109 Design 3.3);
- (k) only the project that owns an object changes it (TCW-114).

A table "New in 4.0" lists `tcw project path`, `tcw project info`, `tcw -C`,
`--scope`, `--project`, `tcw work move`, `tcw taxonomy rename|move`,
`tcw capabilities rename|move` and `tcw work new --nest`, each with a link to
its home document.

2.7. **The epic-parts flow, step by step** holds a table with one row for each
step a to f of TCW-114 Design 3.1 as landed, its 3.x column and its 4.0
column, and the sentence that an agent taught the 3.0.1 or 3.0.2 flow changes
one thing: it runs each part's command in the part's own project with
`tcw -C` (design.md:605-607; H8).

2.8. **Personal settings and environment variables** says (TCW-109; H7):

- (a) the personal files are `.tcw/tcw-config.local.yaml` and
  `.tcw/tcw-manifest.local.yaml`, both untracked;
- (b) the variable naming rule `TCW_<KEY>__<PROJECT>`, with at least two
  examples, one for a project whose ID holds a hyphen and one for a key two
  levels deep (TCW-109 Design 4.1). Every example names a key the allowed
  list accepts (TCW-109 Design 5.1), such as `TCW_USER_NAME__MY_PROJ` or
  `TCW_WORK_JIRA_CREDENTIALS_TOKEN_ENV__APP`; never a store location or
  `work.jira.site`, which the design's own examples used and the allowed list
  refuses (Design 8.6, 8.7; S7);
- (c) a variable holding a mapping merges; a list or a single value replaces;
  the more specific variable wins (TCW-109 Design 4.6, 4.7);
- (d) personal files and variables may set only the allowed keys, linking to
  `skills/configure/references/personal.md` for the list (TCW-109 Design 5.1);
- (e) `TCW_NO_PERSONAL_CONFIG=1` turns the variables off as well as the files
  (TCW-109 Design 5.3);
- (f) `TCW_PROJECT_<ID>`, `TCW_CONFIG_DIR` and credential variables named
  without `__` work as before (TCW-107 Design 2.1; TCW-109 Design 4.2);
- (g) a credential variable name that starts with `TCW_` and holds `__` is
  read as an override in 4.0 and must be renamed (TCW-116 A9).

2.9. **Where provisioning may place a clone** says (TCW-115 Design 7.6-7.9;
H10, H15, H17):

- (a) the active project's own two manifests are trusted;
- (b) any other manifest may place a clone only in a non-hidden folder directly
  inside the folder holding its owner's repository, and never when that folder
  is the home folder or above it;
- (c) a hidden folder below the home folder is refused like the home folder;
- (d) a manifest whose owner has a `.git` that git cannot read is refused until
  that is fixed or the way out is taken;
- (e) a manifest inside a git submodule may place a clone beside the
  submodule, inside the superproject;
- (f) in a linked worktree, the bound is beside the main checkout;
- (g) the way out: `tcw -C <folder> project provision <id>`, or an entry in
  the named project's `.tcw/tcw-manifest.local.yaml`;
- (h) a folder holding only `.git` is refused, and is finished or removed with
  git;
- (i) a `.tcw-staging-<hex>` folder is what a stopped run leaves, and is safe
  to delete.

2.10. **Scripts, hooks and agent instructions** says:

- (a) look for removed commands and flags in a project's own `CLAUDE.md`,
  `AGENTS.md`, agent memories, and the commands bound to stages, hooks and
  procedures; `tcw migrate` names the bindings it finds and leaves them as
  written (TCW-116 A13);
- (b) a script that reads `--json` output reads `"schema": 2` and full
  identifiers; one that reads `--origin` comments reads the new shape;
- (c) a script that checks exit 5 for a missing related project checks 7;
- (d) a 3.x command typed into 4.0 is refused with a line naming its
  replacement (TCW-115 Design 1.2), and gives each line word for word as `v4`
  prints it, split in two in a mapping table whose header's first cell is
  "3.x command typed" and whose second is "the rest of the line" (for example
  `tcw init` | is now `tcw project new`). Decided by the dispatching session,
  2026-10-22 (plan review Q1.2): each printed line starts with the 3.x command
  in a code span, which 9.4 (d) refuses anywhere but a mapping table's first
  column; splitting the line at the command keeps its exact words and passes
  (d);
- (e) automation that installs `tcw-cli` keeps the version limit of
  2.3 (f) until the project is migrated (S3).

### 3. The README

3.1. **The command table** (`README.md:263-273`) lists `tcw project` (with its
six verbs), `tcw migrate`, `tcw validate`, `tcw serve` and the three axis
groups, and no removed command. The adoption example uses
`tcw project new --id my-project` and says it writes `.tcw/tcw-config.yaml`
(D106, D115).

3.2. **The overview** names an object by its full identifier
(`<project>.<namespace>/<id-path>`, with an example) and says "slug" is its
nickname (`:255-257`; H5); says in a sentence that a link is written
`tcw://` followed by the full identifier, linking the linking guide for the
grammar (H5, D110); and names each object's state file
(`tcw-work-item.yaml`, `tcw-taxonomy.yaml`, `tcw-capability.yaml`) and an
item folder's `resources/` folder, linking the work guide (D111).

3.3. **"Many repositories, one model"** (`:289-300`) is rewritten: projects
relate only by declared parent links, each saying what it passes down; a
manifest says where projects are; `--scope` chooses how much of a family a
command shows; only the owning project changes an object, and `tcw -C` runs a
command in another project's folder; a related project not on this machine
stops only what needs it, with `tcw project provision <id>`; and, in a
sentence linking the configuration guide, that a parent shares its tags and
Jira settings with its children (never which backend they use), and that a
setting a personal file may set can also be set by an environment variable
named `TCW_<KEY>__<PROJECT>` (H2, H4, H8, H13, D108, D109).

3.4. **The cloud section** (`:231-235`) names `tcw project provision` and says
what it fetches (H2).

3.5. **Each axis's CLI table** shows `--scope`, `rename` and `move`, and the
work table shows `tcw work new --parent <epic> --nest` and `tcw work move`
(D111, D113, D114). The `tcw capabilities list` row is the one TCW-113 changed
only as far as `--local` (H16), rewritten here.

3.6. **The documentation index** (`:760`) links the new guide first among the
migration guides.

### 4. The guides

4.1. **`docs/guide/cli.md`**:

- (a) a section on the global option `-C <folder or address>`: runs any
  command as if started there, as that project, with its own settings and
  checks; works only for a project on this machine (TCW-114 Design 4; D114);
- (b) "Naming a work item" (`:120`) becomes "Naming an object": the input forms
  of TCW-110 Design 3.1 (a full identifier, its address, a tracker key bare or
  as `<project>.work/<KEY>`, a bare id-path in the active project) and that
  output always prints full identifiers (H5);
- (c) `--scope own|up|down|all` (default `own`, never a sibling) and
  `--project <id>` (keeps one owner's results, and never groups: its records
  carry no `statuses` and no `overridden-by`, TCW-113 plan, choice 7) on every
  list and show command (TCW-113; H13, H16);
- (d) the output records: `"schema": 2`, `full-id`, `owner`, and the
  `projects`, `statuses`, `overridden-by` and `partial` keys where they occur
  (TCW-110, TCW-112, TCW-113; H5, H13);
- (e) the exit-code table's examples for 3, 4 and 5 (`:144-146` at
  `1ddf57ed`, which name upstream projects, filing into another project and
  "`tcw provision` obtains it"), the row for 7 as TCW-108's Step 3 adds it,
  and the passage under the table (`:148-150`, "Creating an item in another
  project (`tcw work new --project <id>`) …") say what 3, 5 and 7 mean in 4.0
  (H2, H8);
- (f) `tcw work new --parent <epic> --nest` (D111);
- (g) a mistyped or removed command gets a suggestion, linking the migration
  guide (TCW-115 Design 1.2, 1.3; H10). The four removed commands are shown
  as a table of verbs, with a header saying they are 3.x commands 4.0
  removed: `init` → `tcw project new`, `projects` → `tcw project list`,
  `config` → `tcw project config`, `provision` → `tcw project provision`.
  The full suggestion lines, which write `tcw <verb>`, are only in the
  migration guide, in the table of Design 2.10 (d) (Design 1.6 (a); decided by the dispatching session,
  2026-10-22: `test_documented_cli_surface` fails on `tcw init` in any code
  span of `cli.md` once TCW-115 lands, and the grep of 9.3 forbids it in
  prose) (M5). The section also says, in prose with the mistyped words
  outside any code span ("typing new straight after tcw"), that new suggests
  `tcw work new` or `tcw project new`, and that list alone suggests no
  project command (TCW-115 Design 1.3; H10 (5)), each checked by running it
  on `v4`. Decided by the dispatching session, 2026-10-22 (plan review Q1.3):
  `_check` (`tests/test_documented_cli_surface.py:197-216`) reports a
  mistyped command in a code span as "no such verb", so only the suggestions
  go in code spans.

4.2. **`docs/guide/configuration.md`**:

- (a) the files are in `.tcw/` (`tcw-config.yaml`, `tcw-config.local.yaml`),
  whose location is fixed; a 3.x project, with a root `tcw-config.yaml`, is
  refused with `tcw migrate`, linking the guide (`:3`; D106);
- (b) every file TCW writes carries `tcw-version`, the version it was created
  or last migrated with, so a file with none is 3.x; the word **migration** is
  defined here, as converting a file to a newer format (H18, the term TCW-116
  adds);
- (c) the layers: built-in, the project's file, the user-wide file, the
  personal file, then environment variables, and only then inherited by
  children (design.md:507-511; TCW-109 Design 2.1);
- (d) the inherited keys (`work.tags`, `work.jira` and its keys), that
  `work.backend` is never inherited, `null` removing an inherited value, and
  `inherit: true` in `work.tags` reaching across the parent link (TCW-109
  Design 1.1, 1.2, 2.4, 2.5; H7);
- (e) environment overrides and the allowed list, in a sentence each, linking
  to their homes (Design 2.8 and `skills/configure/references/personal.md`);
- (f) a command that reads a setting only a missing parent could give exits 7,
  with its two remedies: fetch the parent, or leave `config` out of that
  parent link's `inherit` (TCW-109 Design 3.3, 3.5; H7);
- (g) whose problem a mistake is: one in the person's own user-wide file is
  reported once, as their own error, in every project; one in an ancestor's
  shared file is a warning in its readers; a descendant's unreadable file is an
  error in the project that lists it; the "broken inherited value" warning
  (TCW-109 Design 1.6; H7, H11);
- (h) `tcw project config --origin` and its comment shape (TCW-115 Design 4.2;
  H10);
- (i) `not-tags` (D106);
- (j) for a filesystem project, listing, reading and moving its own items work
  with a parent missing; for a Jira-mode project whose Jira settings come from
  that parent, they stop with exit 7 (H7, H11); and in either kind of
  project, `tcw work path`, `tcw work lifecycle`, `tcw work docs`, and
  `tcw work stage prompt` and `tcw work procedure` given no item, never stop
  on a missing parent (H11, TCW-109's comment of 18:50) (S1).

4.3. **`docs/guide/jira.md`**:

- (a) `TCW Item` holds the item's full identifier, nested id-path included; a
  key is found at any depth; the item folder holds `tcw-work-item.yaml`
  (TCW-110, TCW-111; H5, D111);
- (b) tickets still holding a 3.x value are left out of `tcw work list` with
  one warning naming their keys and `tcw migrate`, and `tcw validate --remote`
  reports each (H5);
- (c) `work.jira` may come from a parent; `work.backend: jira` is always the
  project's own; a credential variable name may come from a variable (TCW-109;
  H7, D109);
- (d) projects in one scope read with one search share one Jira project, one
  account (email and token) and one stage mapping; a write in the same
  command or request makes the next search ask Jira again (TCW-113 Design 3.5;
  H13, H16);
- (e) a parent or blocker that Jira cannot link is recorded in the item's
  folder, and Jira does not show it (TCW-114 Design 3.3; H8);
- (f) a move or rename edits each ticket's `TCW Item` (TCW-114);
- (g) "Creating an item in another project" (`:233`) becomes "Working on
  another project's items": the command is run in that project with `tcw -C`;
  filing through a `jira` block is gone; the web create form accepts a blocker
  in another project (H4, H8, D108, D114);
- (h) no passage names an `upstream` project (`:245`; H4);
- (i) `tcw migrate` edits each ticket's `TCW Item` and no other field, and
  between a `--no-jira` run (or a run that stopped) and the run that
  finishes, the tickets still holding a 3.x value are left out of
  `tcw work list` as (b) says; the section links the migration guide
  (TCW-116 Design 5.2, 5.3; TCW-116 plan, Documentation Sync) (M7).

4.4. **`docs/guide/linking-and-validation.md`**:

- (a) the `tcw://` grammar: `tcw://<project>.<namespace>/<id-path>` for an
  object, `tcw://<project>[.<namespace>].path/<folder>` for a folder, no `.` or
  `..` folder in an address (design.md:237-257; H5);
- (b) a link may name an object in any project TCW can locate, not only an
  ancestor (H5);
- (c) 3.x links are reported as needing `tcw migrate` (H5);
- (d) a reference into a project not on this machine is "could not check"
  (design.md:394-395);
- (e) the findings 4.0 adds: TCW-111's rows a to n, an incomplete override and
  two unrelated projects at one path (TCW-112), stores that nest, coincide or
  loop (TCW-110), manifest entries that cannot be reached or declare another
  ID (TCW-107), and load-order warnings and loops (TCW-108) (D111);
- (f) "A leftover inheritance file from before 2.5.0" (`:130`) is kept only if
  4.0 still reports that file, and says what 4.0 prints (Design 1.1).

4.5. **`docs/guide/multi-repo.md`** keeps its file name, since other documents
and tests link it, and is retitled "Related projects". It is rewritten whole
(Problem 2; H2, H4, H8, H10, H13, H15, H17, H18, D107, D108):

- (a) a project is a folder holding `.tcw/tcw-config.yaml`; the active project
  is the nearest one enclosing the current folder (design.md:53-58);
- (b) parent links: `parents:` in order, each with `inherit` (`all`, `none`, or
  a list of `taxonomy`, `capabilities`, `config`); children listed in the
  shared or the personal file, combined; a listed child must name the parent
  back (design.md:339-378; TCW-108);
- (c) the load order (last listed wins, an ancestor before its child, a project
  reached twice loaded once), the warning when no consistent order exists, and
  that `tcw project info` shows it (design.md:398-446);
- (d) manifests: `.tcw/tcw-manifest.yaml` and `.tcw/tcw-manifest.local.yaml`,
  an entry's shape (path, `repository` with an optional branch, `subfolder`),
  and that a manifest says where a project is and nothing else (TCW-107
  Design 1);
- (e) locating a project with no entry: the folders next to the naming
  project's root, then the folders enclosing it; never downwards; two matches
  are an error naming both; an entry whose folder is empty or holds only
  `.git` counts as not on this machine; `TCW_PROJECT_<ID>` (TCW-107 Design 2;
  H2);
- (f) a related project not on this machine: what still works, exit 7 for what
  needs it, "could not check" in `tcw validate`, and "unavailable, exit 0" for a
  listed child in a `--scope` view, with the warning each `show` gives for it
  (`… so its status is not shown: <reason>` and its two siblings, TCW-113
  plan, choice 6, worded as `v4` prints them) (design.md:380-396; TCW-113;
  H13, H16);
- (g) family views with `--scope` (H13);
- (h) only the owning project changes an object; to change another project's
  object, `tcw project path <id>` gives its folder and `tcw -C` runs the
  command there; a blocker in another project is the one exception
  (design.md:579-615; H8);
- (i) stores in another repository: a store location is a relative path or a
  `.path` address; an absolute or `~` path in the shared file is refused;
  stores may not nest, coincide or loop; a store's `repository` stays on the
  store (TCW-110 Design 7; TCW-116 decision 4, settled on TCW-99 on
  2026-10-22; H5, H18);
- (j) `tcw project provision` and Design 2.9's bound, stated in full here, with
  the migration guide linking here (H10, H15, H17);
- (k) git worktrees: tracked files from the worktree, personal files from the
  worktree or else the main checkout, paths outside the repository from the
  main checkout (design.md:555-577);
- (l) Design 1.7's two layers.

4.6. **`docs/guide/taxonomy-and-capabilities.md`**:

- (a) a project inherits the taxonomy and capabilities of every parent whose
  `inherit` includes that axis, every level up (TCW-112; H4, H9);
- (b) "Federating and overriding a capability" (`:205`) becomes "Inheriting and
  overriding": an override is an object at the same path, holds only what it
  changes and merges field by field; `tcw capabilities set` and `tcw taxonomy
  add` at an inherited path write one; `reset` and `rm`; an override whose
  original moved is reported as incomplete; two unrelated parents at one path
  warn (TCW-112; H9, H12);
- (c) a listing marks overrides in its records (`--json`, the web app), and
  plain `list` stays one identifier per line (H9);
- (d) mixed status under `--scope down` and `all`, read from `--json`
  (`statuses`) or `show`, never from a plain listing (TCW-113; H13);
- (e) no capability `id`; `--parent` on `add` and `set`; `rename` and `move`
  (TCW-111, TCW-112, TCW-114; H3);
- (f) `tcw capabilities drift` in a Jira-mode project whose Jira settings come
  from a missing parent exits 7 (H11);
- (g) "A project with no ledger of its own" (`:169`) says what 4.0 does.

4.7. **`docs/guide/web-viewer.md`**:

- (a) "The app serves one project" (`:17-19`) becomes the scope control and
  the project filter, the read-only display of other projects' objects, and
  followed links; and that the app's records carry the keys of the CLI's
  `--json` records (TCW-113 plan, choice 9) (TCW-113; H13, H16);
- (b) the reference pickers offer what the served project can reference
  (its view of taxonomy and capabilities, its own work items), whatever the
  scope control shows; choosing one project in the filter shows no status
  summary (TCW-113 Design 6.6, 6.9; H16);
- (c) the create form's "inside the parent's folder" option; no project choice
  and no "Blocks (add)" section; a body edit changes only the capability's own
  description (TCW-111, TCW-114, TCW-112 Design 4.5; H12, D111, D114).

4.8. **`docs/guide/work.md`**:

- (a) "The item folder" (`:105`): `tcw-work-item.yaml`, the bounded set, child
  item folders and `resources/`, and that a long design document goes in
  `resources/` (TCW-111; H3);
- (b) "Creating and changing items" (`:320`): `--parent` with `--nest`,
  `tcw work move`, `rename` of an item holding nested items, and the
  passages at `:332` and `:351` (TCW-114; H8);
- (c) "References, and what `tcw validate` reports" (`:364`) and the passages
  at `:383` and `:414` (TCW-107; H2);
- (d) `tcw work tags add` in a child writes `inherit: true` first, so it keeps
  following its parents (TCW-109 Design 6.2; H7); and `tcw work tags rm` in a
  child removes only the child's own tags, and refuses a tag a parent
  declares (exit 3, TCW-109 Design 6.3; TCW-109 plan, Step 10) (S1).

### 5. The skills and other shipped text

5.1. **`skills/work/SKILL.md`** and its references:

- (a) the description and the "Delegation" bullet (`:4`, `:93-101`): an epic's
  part in another project is made there, `tcw -C <folder> work new "<title>"
  --parent <epic> --nest`, and `tcw project path <id>` gives the folder; a
  blocker in another project is recorded on the blocked item with
  `--blocked-by` (TCW-114; H8, H15);
- (b) "Epics are parents" (`:90-92`) and `references/commands.md:10` always
  pass `--nest` with `--parent` (TCW-111 Design 9.3; H3);
- (c) "Another project's exit codes" (`:103-115`) becomes: exit 3 for a change
  outside the owning project, naming the folder to run it in; exit 7, "report
  which project the command needs and pass on how to fetch it; do not retry";
  for exit 7 naming a configuration setting, report which project it comes
  from and the two remedies (TCW-108 Design 7.1, 7.2; TCW-109 Design 3.5; H6,
  H7);
- (d) `--scope own|up|down|all` and `--project`, the default `own`, that the
  family's overview is `--scope all` and `--scope down` lists what the project
  and its descendants declare (TCW-113; H13);
- (e) every component's names and input forms (H5);
- (f) the backlog audit names every item by its full identifier and recommends
  changes to another project's item with `tcw -C` (TCW-113 Design 7.1; H16);
- (g) `tcw work move` and `rename` for nested items (TCW-114; H8);
- (h) `tcw work tags add` and `rm` in a child, as 4.8 (d) (H7, S1);
- (i) `references/commands.md:11`, `:19`, `:28` and its exit-code table (D108,
  H2, H14);
- (j) a project refused as 3.x is moved over with `tcw migrate`, naming the
  migration guide by its file and GitHub address as 5.5 does (TCW-116 plan,
  Documentation Sync: "the `setup` and `work` skills name how a 3.x project
  is upgraded") (M7);
- (k) where provisioning may place a clone, in a sentence linking the guide,
  as 5.7 bounds it (H10 (2)) (S1).

5.2. **`skills/taxonomy/SKILL.md`**: "Inheritance (federation)" (`:105-110`)
becomes inheritance through parent links passing `taxonomy`; an override at an
inherited path; `--scope up` for inherited entries; the nesting bullet (`:91`)
says `--parent` also records `parent:`; `rename` and `move`; exit 7 (H3, H6,
H9, H13).

5.3. **`skills/capabilities/SKILL.md`**: "Federation" (`:118-125`) as 5.2 for
capabilities; no opaque `id` (`:29`); `set` on an inherited capability writes
the project's own object at the same path, and what `tcw validate` now checks
(`:141-147`); mixed status read from `--json` or `show`; `--project` gives one
owner's objects with no `statuses` and no `overridden-by` (TCW-113 Design 2.1);
`--parent` on `add` and `set`; the "ask another project for wording" flow
(`:153`, `:181`) becomes `tcw -C` into that project when it is on this
machine, and that project's own issue tracker otherwise (UC-7) (H3, H8, H9,
H12, H13, H16).

5.4. **`skills/configure/SKILL.md`** and `references/`:

- (a) `projects.md`: parent links and `inherit`, children in either file, the
  manifests and their entries (`path`, `repository` written `<url>` or
  `<url>#<branch>`, `subfolder`; `tcw/store/manifest.py:36-58`), locating
  rules in a sentence linking the guide, and no `projects:` locators,
  `upstream` or `--project` (`:157-163`, `:170`, `:199`, `:380`; H2, H4, H8);
- (b) `stores.md`: a store location is a relative path or a `.path` address,
  never absolute or `~` in the shared file; no nesting, coinciding or loops;
  `repository` on a store (`:88`; H5, H18);
- (c) `personal.md`: the allowed list as TCW-109 Design 5.1 lands it, the
  override variable rule, `TCW_NO_PERSONAL_CONFIG`, and `.tcw/` locations
  (H7);
- (d) `work.md`: `not-tags` and `tcw-version` (D106), records carrying
  `full-id` and `owner` (H5), and the inherited keys (H7);
- (e) `jira.md` and `docs-sync.md`: `.tcw/tcw-config.yaml` as the file named;
- (f) `SKILL.md` teaches `tcw project config --origin` and `tcw project info`
  (TCW-115 handoff) and where provisioning may place a clone, in a sentence
  linking the guide, as 5.7 bounds it (H10).

5.5. **`skills/setup/SKILL.md`** and `references/`: `tcw project new` makes a
project (`references/project.md:51-70`); `tcw project provision` fetches a
related project (`references/install.md:59`); a project refused as 3.x is
moved over with `tcw migrate`, naming the migration guide; where provisioning
may place a clone, in a sentence, as 5.7 bounds it (H2, H10, D115). The skill
names the guide as a file in the TCW repository, as
`skills/configure/references/jira.md:9` names the Jira guide, and gives its
address on GitHub
(`https://github.com/brocef/TCW/blob/main/docs/migration-guide-3.X-to-4.0.0.md`),
as `skills/extras-report/SKILL.md:20` gives the issue list's, rather than a
relative link: a plugin installed for Codex or Pi may not carry `docs/`
(decided by the dispatching session, 2026-10-22). The address points at
`main`, where the guide exists only once TCW-118 merges `v4`; nothing ships
before then.

5.6. **Other shipped text**:

- (a) `tcw/work/procedures/search.md:25-28` and `pause-work.md:22` teach full
  identifiers and `--scope`, not `<project>/<folder>` or bare slugs (TCW-110;
  H5);
- (b) `agents/backlog-auditor.md` and `agents/reviewer.md` take "a work item's
  full identifier or tracker key" where they say "a work item slug" (H5);
- (c) `skills/README.md`'s row for `setup` names `tcw project new`;
- (d) every other skill, prompt and procedure is checked by the scan of Design
  9.2 and changed only where it finds a 3.x form.

5.7. **The shipped-text git check stays as strict as it is.**
`tests/test_shipped_text.py:31-55` bans `git`, `commit…`, `push…`, `pull…`,
`worktree(s)`, `trunk` and `branch…` in every skill, agent, prompt and
procedure, except exact phrases in `GIT_ALLOWED`. `GIT_WORDS` is not changed.
Decided case by case by the dispatching session, 2026-10-22 (S10):

- (a) **One new phrase is allowed:** `` `<url>#<branch>` `` in
  `skills/configure/references/projects.md`, with the reason "the written
  shape of a manifest entry's `repository` value
  (`tcw/store/manifest.py:42-58`), not an instruction to run git (TCW-117
  Design 5.4 (a))". That reference is the home of every key's exact shape
  (Design 1.5), so the value's form must be written there.
- (b) **The provisioning bound is stated without the banned words.** The
  `work`, `configure` and `setup` skills say, in a sentence, that a manifest
  other than the active project's own two may place a clone only in a
  non-hidden folder directly inside the folder holding its owner's
  repository, never in or above the home folder, and that
  `tcw -C <folder> project provision <id>` or an entry in that project's
  `.tcw/tcw-manifest.local.yaml` is the way out; then they link the guide on
  related projects for the cases that need the banned words (a submodule, a
  linked worktree, an unreadable `.git`, a folder holding only `.git`). No
  phrase is added for them: a skill does not need those cases to act, and the
  guide, which no git check reads, states them in full.
- (c) Any other passage a skill rule needs that the check refuses is
  reworded, or moved to its home guide and linked; a further `GIT_ALLOWED`
  phrase is a departure the implement round reports to the dispatching
  session with its reason.

### 6. `docs/use-cases.md`

6.1. **The opening words and the dimension table.** A family is "a project
together with every project related to it by parent links" (`:19-20`). The
"Projects per family" row replaces "upstream" with "a parent that does not list
its children"; the "Inheritance (`extends`)" row becomes "Inheritance (parent
links)", with "different `inherit` for different parents"; the "Where each
store is" row adds "addressed as `tcw://<project>.path/…`" (H9, H12).

6.2. **Each architecture**, rewritten for 4.0. Each requirement stays a
statement a reviewer can check against the code, with the file that shows it,
re-found on `v4`:

- **UC-1**: the layout shows `.tcw/tcw-config.yaml`; "no `projects:`
  section" becomes "no `parents:`"; `tcw project new`; the project root is the
  nearest folder holding `.tcw/tcw-config.yaml` (D106, H2).
- **UC-2**: the library is a parent its readers name and that does not list
  them; "read-only from the reader" becomes the owning-project rule;
  `tcw://core.taxonomy/…` links; the gap names TCW-114's move, which lists the
  identifiers it changed so they can be passed on (TCW-27 was absorbed into
  TCW-114, design.md:835-841) (H4, H9).
- **UC-3**: `parents:` in each package instead of `parent: app: ../..`;
  packages no longer write into each other; "a bare reference … refused as
  ambiguous" becomes "the load order decides and warns", and "a local term …
  wins without a warning" becomes "an override, marked in records"; the
  epic-parts requirement is rewritten for `tcw -C`, with the parent resolved
  from the part's project (TCW-114 Design 3.1); its known gaps on TCW-102,
  TCW-103 and TCW-98/TCW-99 are closed (H4, H8, H9, H13).
- **UC-4**: the workspace is a parent with `inherit: none`; a store location
  is `tcw://workspace.path/docs/app/work`; the planning workspace cannot
  change other projects' items, and a refusal names the owning project's
  folder (design.md:588-593); "A move in one project can leave files in
  another repository" and "A store with changes not yet committed blocks the
  next filing" are rewritten for 4.0, where the filing is gone; its gaps on
  TCW-22 and TCW-23 are closed (H4, H5, H8, H13, D115).
- **UC-5**: the inherited `work.jira` and the child's own `work.backend:
  jira`; the cost gap narrowed to one search per Jira project, account and
  stage mapping, marked TCW-113 (H7, H13).
- **UC-6**: retitled "A related project that is not on this machine";
  `tcw project provision`; exit 7 for inherited content and an undecided
  setting; "unavailable, exit 0" for a covered project in a `--scope` view;
  the `jira` block and its filing gone; its gaps on `extends`, on 3.x
  taxonomy and capability links, and on TCW-23 are closed (H2, H4, H5, H7,
  H9, H13, D115).
- **UC-7**: the library's readers name it as a parent with whatever `inherit`
  they need; suggesting work for it goes to its own issue tracker (H8).
- **UC-8**: the first requirement becomes "the manifest decides; the search
  only finds a project no manifest names; two matches are an error";
  `TCW_PROJECT_<ID>` as TCW-107 keeps it; the gap narrowed by `found` in
  `tcw project list --json`, marked TCW-107 (H2).

6.3. **Each situation**:

- **S-3**: the cross-backend requirement stands and is met: a parent or blocker
  Jira cannot link is recorded in the item's folder (TCW-114 Design 3.3; H8).
- **S-4**: personal files in a worktree come from the main checkout when the
  worktree has none; the `extends` sentence goes (H9, design.md:555-577).
- **S-5**: the third requirement becomes: "Another project's personal
  configuration file is never read for a project read for itself, which takes
  only the variables naming it; an ancestor's personal credential names reach
  its children. A related project's personal manifest is read, because it
  says only where projects are" (TCW-109 Notes; TCW-107 Questions for TCW-99,
  1, accepted by the user on 2026-10-22; H2, H7).
- **S-6**: exit codes: a missing related project gives 7 from every
  component (TCW-108; H4, H9).
- **S-8**: gains `tcw migrate`'s progress record and its rule: a run that stops
  is finished by running it again, which never repeats a change (TCW-116 Design
  2.7; H18).
- **S-9**: "Seen" gains the 3.x-to-4.0 migration, linking the new guide; the
  first requirement says 4.0 refuses a 3.x file naming `tcw migrate`
  (`tcw/project_files.py:119`, `:150`, `:157`) (H18).
- **S-10**: "The current project is the nearest `tcw-config.yaml`" becomes the
  nearest `.tcw/tcw-config.yaml`; "the search never looks inside a project, so
  a dependency's own `.tcw/` is never taken for a project"; "an item folder"
  becomes "an object folder" (TCW-107 Design 2.6; TCW-111; H2, H3).
- **S-11**: `tcw project provision` makes new clones; "cross-project filing
  refuses a store that is not in a git repository" is replaced by whatever
  check on `v4` still depends on git, or removed if none does (Design 1.1).

6.4. **Known gaps.** Each gap is decided against the code on `v4`: removed when
4.0 closes it, re-marked with the item that narrows it, or kept with "No item
yet". Expected, from the siblings' specs:

| Gap | Expected outcome |
| --- | --- |
| UC-2: a library cannot warn before a breaking rename (TCW-27) | kept; marked TCW-114, whose move lists the changed identifiers |
| UC-3: `children:` shows only children on its own board (TCW-102) | removed: `--scope down` (TCW-113) |
| UC-3: `--parent` when filing into another project (TCW-103) | removed: the part is made in its own project with `--parent` (TCW-114) |
| UC-3: TCW-98 and TCW-99 will change how a parent sees children | removed: on `v4` a parent sees its children with `--scope down` (TCW-113); the document describes 4.0 and does not say TCW-99 is done, which it is only at TCW-118 |
| UC-4: two places rebuild a store's path from the project root | removed if TCW-110 Design 7.5's one function serves both; otherwise kept |
| UC-4: TCW-22, the backlog audit | removed (TCW-113) |
| UC-4: TCW-23, provision scoping | removed (TCW-115) |
| UC-5: a list fetches every ticket in the shared Jira project | narrowed, marked TCW-113 |
| UC-6: a missing project named in `extends` stops every command | removed (TCW-108, TCW-112) |
| UC-6: `tcw://<id>/T/…` into a missing project is an error | removed (TCW-110) |
| UC-6: TCW-23 | removed (TCW-115) |
| UC-8: only `tcw validate` says where `TCW_PROJECT_<ID>` placed a project | narrowed, marked TCW-107 |
| S-7, S-8 (two gaps), S-9 (unknown top-level keys) | kept, "No item yet": 4.0 does not change them (TCW-106 Non-goals for the keys) |
| S-9: a 2.x work store is listed as empty | decided at implement: 4.0 refuses a project with a root `tcw-config.yaml` until migrated, so the gap is removed if `tcw migrate` refuses a 2.x store, and reworded otherwise |

6.5. **The checklist** (`:669-698`): question 2 becomes "Can it change an object
the active project does not own? If so, it is wrong (TCW-114)"; question 3
reads "inherit records through parent links"; question 1 adds "located through
a manifest or the search (TCW-107)".

6.6. **The closing paragraph** (`:713-715`, "When TCW-99 changes how projects
relate, the architecture cases change with it") is replaced by a sentence
saying the cases describe 4.0.

### 7. Agent guides and lifecycle documents

7.1. **`AGENTS.md`** (and so `CLAUDE.md`, a link to it): `:39`, `:52` and
`:170` name `.tcw/tcw-config.yaml`. Its "Working in a git worktree" section is
checked against TCW-107 Design 4 (personal files from the main checkout) and
changed only if it says otherwise. Decided by the dispatching session,
2026-10-22: on `v4` this repository holds both configuration files until the
merge (TCW-106 Non-goals), and the `.tcw/` one is the one 4.0 reads and the
only one after TCW-118's migration, so the guide names it now. Until then the
3.0.2 lifecycle reads the root file, and `tests/test_repo_config_pair.py`
fails when the two differ, so an agent that edits only the file `AGENTS.md`
names is stopped by the suite; `AGENTS.md` gets no temporary sentence about
it, since that sentence would be false after TCW-118 (spec review, Notes).

7.2. **`docs/lifecycle/implementation.md`**: the layout at `:16-24` shows
`.tcw/tcw-config.yaml` and a `work.path` written as a relative path or a
`.path` address; `:41-44` names the functions that walk projects as they are on
`v4`. The comment lines at the top of each lifecycle document name
`.tcw/tcw-config.yaml`. `docs/lifecycle/abstraction.md` is TCW-111's, and is
only scanned here.

### 8. Amendments to the TCW-99 design

Each is made in `design.md` with a dated line saying who decided it and where
it is recorded; none is a new decision (Non-goals). The design is an archival
file (`docs/work/`), so no document check reads it; the review reads each
amendment:

8.1. design.md:467-470: a listing marks an override in its records (`--json`,
the web app), and plain `list` output stays one identifier per line (the user,
2026-10-22; TCW-112 Notes; H9).

8.2. design.md:649-651: a plain listing shows no status summary; the summary is
in `--json` (`statuses`) and `show` (the user, 2026-10-22; TCW-113 Notes; H13).

8.3. design.md:657-665: the sketch's command gains `--scope down`, since
statuses from several projects need a scope that includes them (TCW-113's
decision, TCW-113 spec, Departures 1; H13) (S8).

8.4. design.md:745-746: the line is rewritten to say that a connection's
`repository` goes into the manifest entry, and a store's `repository` stays
on the store, with the dated line "decided by the dispatching session,
2026-10-22, on TCW-99 (comment of 21:06), under the user's instruction to
settle the remaining open questions: one place to declare a store's
repository already exists and every 4.0 child uses it; no follow-up item"
(TCW-116 decision 4; H18) (D1).

8.5. design.md:484-485: `work.backend` leaves the list of inherited keys,
with the dated line "the user's decision, 2026-10-22: each project states
its own backend, and the default is filesystem; recorded in TCW-109's note on
TCW-99 (17:59)" (S7).

8.6. design.md:516-518: the example `TCW_WORK_PATH__MY_PROJ=/other/path` is
replaced by one for a key the allowed list accepts (`TCW_USER_NAME__MY_PROJ`,
with the hyphen in `my-proj` still shown becoming `_`), with the dated line
"the user, 2026-10-22: store locations cannot be overridden, so the example
contradicted the design's own rule; TCW-99 comment of 15:28, and TCW-109
Design 5.1" (S7).

8.7. design.md:531-533: the two examples become
`TCW_WORK_JIRA_CREDENTIALS__APP` (the whole mapping) and
`TCW_WORK_JIRA_CREDENTIALS_TOKEN_ENV__APP` (one key in it), with the dated
line "TCW-109's departure 4, 2026-10-22 (its note on TCW-99, 17:59): the
allowed list refuses `work.jira` and `work.jira.site` from a variable" (S7).
The examples of 8.6 and 8.7 are run on `v4` before they are written
(Design 1.1).

### 9. Checks

9.1. **The existing document checks** pass unchanged in what they check:
`tests/test_documented_cli_surface.py` (every `tcw` command in a live
Markdown file exists), `tests/test_shipped_text.py` (no git, no 2.x
vocabulary, only real commands, every injection with a fallback),
`tests/test_docs_describe_3_0.py` (2.x vocabulary, links and commands in the
README, guides, lifecycle documents and configure skill),
`tests/test_cli_guide.py` (the exit table), `tests/test_doc_vocabulary.py`,
`tests/test_skill_flow.py`, `tests/test_skill_path_pointers.py`,
`tests/test_dynamic_skill_marker.py`, `tests/test_configuration_text_home.py`,
`tests/test_documentation_*.py`, `tests/test_upcoming_entries.py`,
`tests/test_migration_guide.py` and `tests/test_eval_*.py`. A test whose
expected text is a 3.x passage this item rewrites is changed to the new text,
and the round lists each such change with its reason. Two tables are not
loosened at all: `PATTERNS` in `tests/doc_vocabulary.py` (the 3.0 scan,
Design 1.6 (c)) and `GIT_WORDS` in `tests/test_shipped_text.py` (Design 5.7);
`GIT_ALLOWED` gains only the phrase of 5.7 (a) (S10, S12).

9.2. **A permanent scan for 3.x forms.** `tests/doc_vocabulary.py` gains a
second table, `THREE_X_PATTERNS`, each entry a regular expression and the
reason it goes. Every reason names the item that removed the form and ends
"(scan: TCW-117)", so a later change that brings a form back (a new `--local`
flag, say) knows which row to delete (D3).

| # | Pattern | Reason |
| --- | --- | --- |
| P1 | `tcw (init\|provision\|projects\|config)\b` | removed commands (TCW-115 Design 1.2) |
| P2 | `` tcw work new [^`]*--project\b `` | removed flag (TCW-114) |
| P3 | `--blocks\b` | removed flag (TCW-114) |
| P4 | `--local\b` | removed flag (TCW-113) |
| P5 | `extends (add\|rm)\b`, `(taxonomy\|capabilities)\.extends\b`, `\bextends:` | removed commands and keys (TCW-112) |
| P6 | `\bupstream (project\|connection\|link\|relation)s?\b`, `\bupstream:`, `projects\.(upstream\|parent\|children)\b` | removed relations and keys (TCW-108) |
| P7 | `(?<![\w-])(meta\|item)\.yaml\b` | renamed state files (TCW-111) |
| P8 | `tcw://[CTW]/`, `tcw://[a-z0-9-]+/[CTW]/` | 3.x addresses (TCW-110) |
| P9 | `\bcap-[0-9a-f]{6}\b` | removed capability ids (TCW-112) |
| P10 | `\bnot_tags\b` | renamed key (TCW-106) |
| P11 | `<project(-id)?>/<`, `\btcw/TCW-[0-9]` | 3.x slug forms (TCW-110) |
| P12 | `^\s*overrides:\s*[^\s./]+/` | removed override pointer (TCW-112) |

Three corrections from the first draft (spec review M1, M2, S6), each checked
with Python's `re` on 2026-10-22:

- P7's look-behind `(?<![\w-])` keeps it off the 4.0 file name
  `tcw-work-item.yaml`, where `\b` matched between `-` and `item`
  (`re.findall(r'\b(meta|item)\.yaml\b', 'tcw-work-item.yaml')` returns
  `['item']`; with the look-behind it returns nothing, and it still finds a
  bare `item.yaml`).
- P6 has no `\bprojects:`: `projects` is a top-level key of the 4.0 manifest
  (`_TOP_KEYS = (VERSION_KEY, "projects")`, `tcw/store/manifest.py:37`), which
  the multi-repo guide and `projects.md` must show, and the pattern also
  matched English prose ("four TCW projects:"). The 3.x shape `projects:` with
  `parent:` or `upstream:` below it is caught by `\bupstream:` and by
  `projects\.(upstream|parent|children)` where a document names the keys
  inline; a fenced 3.x example cannot be allowed anyway (Design 1.6 (b)), and
  the review reads every fenced YAML block in a live document (criterion 42).
- P2 stops at a backtick (`` [^`]* ``), as the grep of 9.3 does, so a paragraph
  naming `tcw work new` and then `tcw work list --project app`, a valid 4.0
  option, does not fail.

A fourth correction, after the plan review (D1), checked with Python's `re`
on 2026-10-22: P12 matches only an `overrides:` value whose part before the
first `/` holds no dot (`overrides: core/cap-1a2b3c`,
`overrides: <alias>/<cap-id>`). 4.0's `show` prints `overrides: <full id>`
for an override (TCW-112 plan, choice 7 and its "Records" step, which add the
key and the printed line; TCW-113 plan choice 8 only places `overridden by:`
after it), and a full identifier always holds a dot before its first `/`
(`<project>.<namespace>/<id-path>`, TCW-110 spec, Goals 1), so
`overrides: app.capabilities/billing` passes and real 4.0 output may be shown
in a fenced block. Decided by the dispatching session, 2026-10-22: the first
form, `^\s*overrides:`, refused that output; narrowing it to values holding
`cap-` would only repeat P9 and lose the placeholder pointer, which only P12
catches. If TCW-110's code on `v4` prints a full identifier with no dot before
its first `/`, the implement round reports it and P12 is not loosened to fit.

**Case.** The table is matched case-sensitively, so the prose "TCW projects"
is not the command `tcw projects`. `scan` compiles every pattern with
`re.IGNORECASE` today (`tests/doc_vocabulary.py:128`), so it gains a keyword
argument `flags=re.IGNORECASE`, which every existing caller keeps by default,
and the new test passes `flags=0` (S5). A test shows that `scan` with the
3.0 table still matches regardless of case, and that `THREE_X_PATTERNS` with
`flags=0` does not match "TCW projects".

**What it reads.** A new `tests/test_docs_describe_4_0.py` scans every live
document (the files of `test_documented_cli_surface._doc_files`, which
already exclude `ARCHIVAL`) with `THREE_X_PATTERNS`, over the blocks
`doc_vocabulary.blocks` gives. A hit fails unless its block (a paragraph, a
list item or a table row) also contains `tcw migrate` or
`migration-guide-3.X-to-4.0.0`. A hit on a line of a fenced block always
fails, even when that same line names `tcw migrate` (Design 1.6 (b)). Decided
by the dispatching session, 2026-10-22 (plan review D3): the first revision let
a fenced line carry the allowance by its own comment, which 1.6 (b) forbids,
and no 4.0 document needs it; dry-run output holding 3.x names belongs in the
migration guide, which is archival. Until TCW-118 migrates this repository, the
test leaves out the ledger records, in one named tuple:

```python
# This repository's taxonomy and capability records stay in 3.x form, with
# their 3.x tcw:// links, until TCW-118 migrates the repository at the merge
# (TCW-116 Design 9.3). TCW-118 deletes this tuple after that migration.
UNMIGRATED_RECORDS = ("docs/taxonomy/", "docs/capabilities/")
```

Decided by the dispatching session, 2026-10-22 (M3): the records' 3.x links
are real links the 3.0.2 `tcw validate` resolves, so "fix the hit" would break
this repository's lifecycle and "leave it" would fail the test; leaving the
two trees out, with the switch-on handed to TCW-118 at the step where the
repository is migrated and the suite is run (TCW-116 Design 9.3, step 3), is
simpler than an exception per pattern per tree, and still honest, because
Design 9.8 runs the same scan over the records once at implement and fixes
their prose here. Scanning them only in a migrated proof clone was rejected:
it would test a copy, not the files that ship.

**Its own tests.** Inserting a hit for each pattern into a scratch document
outside the record trees fails; the same hit in a block naming `tcw migrate`
passes, except on a line of a fenced block, which fails even when the line
itself names `tcw migrate`; a hit inside `docs/capabilities/` is not reported
while `UNMIGRATED_RECORDS` exists; and `tcw-work-item.yaml`, a manifest's
`projects:` key, the prose "TCW projects:" and a fenced 4.0 line
`overrides: app.capabilities/billing` each pass. Each failing case asserts
the label of the row it is for (`P12:` and so on), so a sample that another
row also matches cannot hide a broken pattern.

Decided by the dispatching session, 2026-10-22: an allowance by paragraph
rather than a table of exceptions, because 4.0's own documents must say what
a 3.x project looks like (the refusal of a root `tcw-config.yaml`,
`tcw migrate`'s capability record), and every such passage names
`tcw migrate`. The scan is kept permanently (D3): it is cheap, and the keys,
file names, address and slug forms it looks for are caught by no other test.
For removed commands and flags it mostly repeats `test_documented_cli_surface`
once TCW-112 to TCW-115 land, which is acceptable.

9.3. **A grep for removed commands and flags.** P1 to P5 have no allowance in
the documents a person or an agent learns from. The command, run from the
repository root,

```sh
git grep -nE 'tcw (init|provision|projects|config)([^a-z-]|$)|tcw work new [^`]*--project([^a-z-]|$)|--blocks([^a-z-]|$)|--local([^a-z-]|$)|extends (add|rm)([^a-z]|$)' -- README.md AGENTS.md 'docs/guide/*' docs/use-cases.md 'docs/lifecycle/*' 'skills/*' 'agents/*' 'tcw/work/prompts/*' 'tcw/work/procedures/*'
```

prints nothing. It spells each word's end as `([^a-z-]|$)` rather than `\b`,
which `git grep -E` does not support on every platform; at `2adac9c9` it
prints 125 lines. `docs/guide/cli.md` passes it because
it names the removed commands by their verbs alone (Design 4.1 (g)). The
ledgers are left out of this one command, since a record describing
`tcw migrate` or a mistyped command's suggestion may name a removed command
in a paragraph naming `tcw migrate`.

9.4. **The migration guide's own test**, `tests/test_migration_guide_4_0.py`,
built like `tests/test_migration_guide.py` and reusing its helpers:

- (a) the level-2 headings are exactly Design 2.2's, in order;
- (b) every name in a fixed tuple, `THREE_X_NAMES` (the first-column names of
  Design 2.6 (a) to (g)), appears in the first column of a mapping table;
- (c) every mapping row's second column is non-empty;
- (d) every `tcw …` command the guide writes, in a code span or a fenced
  block, resolves in the 4.0 CLI's visible surface: `_check`
  (`tests/test_documented_cli_surface.py:197-216`) against the command tree
  that module reads from `--help` (its `_walk`), which refuses an option
  hidden from `--help`, and `command_problem`
  (`tests/test_shipped_text.py:283`), which adds the procedure and stage
  names; except those in the first column of a
  mapping table and in the 3.x column of the epic-parts table. The guide's
  path is archival, so `test_documented_cli_surface` skips the whole file, and
  without this the commands a reader copies (`tcw migrate --dry-run`,
  `tcw -C <folder> migrate`, `tcw project provision <id>`) would go unchecked
  (S4). Decided by the dispatching session, 2026-10-22 (plan review M3):
  `command_problem` alone accepts every option the parser registers,
  including those registered with `help=argparse.SUPPRESS`, which TCW-113
  and TCW-114 keep (`--local`, and `--project` and `--blocks` on `tcw work`)
  so that they can print a refusal; the surface read from `--help` is the one
  live documents are already held to, and it needs no list of removed flags
  kept up to date by hand. A case of the test proves that
  `tcw work new "t" --project app` is refused. The guide therefore writes a
  3.x command only in those two places; any prose about one points to the
  table;
- (e) the epic-parts table has rows a to f;
- (f) the exit-code table under "Migrating one project" has rows 0, 1, 2, 3
  and 5;
- (g) every relative link resolves (`link_problems`,
  `tests/test_docs_describe_3_0.py:204`);
- (h) every entry of `THREE_X_PATTERNS` (each regular expression of each row,
  so 18 in all) matches, case-sensitively, at least one first-column cell of
  a mapping table, read with its backticks removed and its spaces trimmed. So
  the scan and the guide's mapping cannot drift apart: a form the scan
  refuses always has a row saying what replaces it (S4). The guide's first
  column writes an example of each form where a pattern needs one (a
  `cap-1a2b3c` id, a `tcw://C/…` link).

9.5. **The README's index test**
(`test_the_documentation_index_links_the_guides_it_must`,
`tests/test_docs_describe_3_0.py:438-444`) also requires
`docs/migration-guide-3.X-to-4.0.0.md`.

9.6. **The skills, read in a fresh session.** pytest proves a skill says the
right words, never that an agent reads them; the `evals/` harness measures that
(`AGENTS.md`, "Measuring the skill layer"). In this item:

- (a) `evals/evals.json` is changed where 4.0 changes what a case expects: B11's
  `files_changed_exactly` names `.tcw/tcw-config.yaml` (`:973-978`), and every
  case's assertion text and `note` that names `tcw-config.yaml`, `tcw init`,
  `item.yaml` or `meta.yaml` names the 4.0 form (TCW-106 Non-goals; D106);
- (b) at implement, `.venv/bin/python -m evals.run_evals --axis a --dry-run`
  and `--axis b --dry-run` list every arm and spend nothing, and the
  `tests/test_eval_*.py` tests pass;
- (c) **a paid run is not an acceptance criterion.** Decided by the dispatching
  session, 2026-10-22 (D2): none of the five cases that drive the five
  rewritten skills uses a 4.0 feature (B1 builds a CSV export, B3 closes out
  an item, B4 adds two terms, B11 tracks the README, B12 sets a project up),
  so a run shows that the rewrite did not break routing or the single-project
  flows, and does not show that an agent follows `--scope`, `-C`, `move` or
  parent links. The QA plan lists it as an optional check the user may choose
  to run at qa, with the exact commands, what it measures and what it does
  not, and the rule that its expected cost is stated to the user before it
  runs. Its commands, from the worktree's root with the worktree's own Python
  (S9): first
  `.venv/bin/python -m evals.run_evals --case B1 --case B3 --case B4 --case B11 --case B12 --out <a folder outside this checkout> --dry-run`,
  whose `agent's tcw: …, imports from …` line (`evals/run_evals.py:347`) must
  name the worktree; then the same command without `--dry-run`; then
  `.venv/bin/python -m evals.grade <that folder>`. New eval cases for 4.0's
  features stay out of scope (Non-goals).

9.7. **The migration guide, read cold.** At qa, a fresh agent session with no
context but the guide (a session started for it in the scratch copy's folder,
not a subagent of a session that has this repository's context) migrates a
scratch copy of this repository's `main` checkout, which is a real 3.x
project, using the 4.0 `tcw` from `v4`. It must reach `tcw validate` exit 0
there using only the guide; each place it had to guess, or a command it ran
that failed, is a qa finding. Decided by the dispatching session, 2026-10-22
(M6): the copy must be unable to write to the live TCW Jira board by
construction, not by instruction, because `main` is a Jira-mode project
pointed at the real `TCW` Jira project (`tcw-config.yaml`, `work.jira`), and
a run without `--no-jira` would rewrite every real ticket's `TCW Item`, with
no command to put them back (TCW-116 Design 9.3). So, before the session
starts, the qa runner:

- (a) makes the copy with `git clone` of `main` into a scratch folder outside
  this checkout and the `v4` worktree, and removes its remote
  (`git -C <copy> remote remove origin`), so nothing can be pushed from it;
- (b) edits the copy's `tcw-config.yaml` so that `work.jira.site` is
  `https://jira.invalid` (a name reserved never to resolve) and
  `work.jira.credentials.email-env` and `token-env` name variables set
  nowhere (`TCW_COLDREAD_NO_EMAIL`, `TCW_COLDREAD_NO_TOKEN`). The copy is
  still a 3.x Jira-mode project, so every Jira step of the guide is met as a
  reader meets it; a real run that tries Jira stops before any request
  (`TrackerAuthError` is raised when a credential variable is unset, TCW-116
  Design 1.6) and writes nothing (TCW-116 Design 2.3);
- (c) starts the session with every `TCW_JIRA_*` variable removed from its
  environment (`env -u TCW_JIRA_EMAIL -u TCW_JIRA_API_KEY …`, every such name
  `env | grep '^TCW_JIRA'` lists), without sourcing `~/.bashrc`, with
  `XDG_CONFIG_HOME` and `XDG_CACHE_HOME` set to two new empty folders in the
  scratch area, and with `<v4 worktree>/.venv/bin` first on its `PATH`.
  `XDG_CONFIG_HOME` decides where TCW reads the user-wide file
  (`$XDG_CONFIG_HOME/tcw/config.yaml`, else `~/.config/tcw/config.yaml`;
  `tcw/config.py:192-205`), so the person's own file is neither read, where
  it could name other credential variables, nor written by a 4.0 run.
  `XDG_CACHE_HOME` decides where TCW keeps its working copies of stores held
  in another repository (`tcw/store/checkouts.py:60-68`, else
  `~/.cache/tcw/stores`). `HOME` is left as it is, because the reader's agent
  session keeps its own sign-in and settings there; with both variables set,
  TCW otherwise reads `HOME` only to expand a `~` a configuration names and
  for the provisioning bound, which a one-project migration does not reach.
  Before handing over, the qa runner records that `env | grep -c '^TCW_JIRA'`
  prints 0, that `tcw --version` in the copy prints 4.0.0, and the state of
  the person's own user-wide file and store cache
  (`shasum -a 256 ~/.config/tcw/config.yaml`, or that the file does not
  exist; `ls -A ~/.cache/tcw/stores`); after the session it records both
  again, and each must be unchanged. Decided by the dispatching session,
  2026-10-22 (plan review M1): the first revision named `TCW_CONFIG_DIR`,
  which is only the folder TCW tells a hook its `file:` binding is read from
  (`tcw/config.py:76`, `tcw/work/hooks.py:54`, `:77`) and moves no file, so
  it isolated nothing;
- (d) gives the instruction "Move this project to TCW 4.0 by following the
  guide at <the absolute path of `docs/migration-guide-3.X-to-4.0.0.md` in the
  `v4` worktree>". The path is absolute because the copy of `main` has no such
  file, and it is the `v4` worktree's copy so that the guide's relative links
  open the 4.0 documents, not the copy's 3.x ones. The QA plan writes the
  path out.

The instruction does not mention Jira: what the reader does about the ticket
step is part of what the read tests. The cold read exercises only the
one-project path; related projects are covered by the review against
TCW-116's tests (criterion 4). The Jira half is TCW-116's tests' and
TCW-118's real migration's.

9.8. **The ledger.** The five capability records of Capability changes are
rewritten in prose for 4.0, in 3.x form (each keeps its `meta.yaml` and its
3.x `tcw://` links). At implement, the scan of 9.2 is also run once over the
two record trees (a short script calling `doc_vocabulary.scan` with
`THREE_X_PATTERNS` and `flags=0`, its output pasted in the implement round),
and every hit except P8, a 3.x link that `tcw migrate` converts at TCW-118,
is fixed in prose; each capability record so changed is added to
`capabilities.yaml` under `changed:`, and each taxonomy record so changed is
listed in the implement round. The records are checked with the `tcw` first
on the path, the primary checkout's 3.0.2 (`tcw --version` prints 3.0.2), run
from the worktree's root: `tcw validate` exits 0 there, as it does at
`5a9ca9b7` (checked on 2026-10-22: "0 errors, 0 warnings, 0 unresolved").
The worktree's `.venv/bin/tcw` is not used for this, since once TCW-111 lands
it reports every 3.x object folder (TCW-111 Risks; TCW-116 Problem 6) (M4).

### 10. Upcoming entries

10.1. Following `AGENTS.md`, "Versioning", this item writes its own two files,
named `TCW-117-tcw-4-0-guides-skills-use-cases-and-the-3-x-to-4-0-migration-guide.md`:

- `docs/release-notes/upcoming/`: in plain language, a guide for moving a
  project from 3.x to 4.0, and the guides and skills describe 4.0;
- `docs/changelogs/upcoming/`: under **Changed** (the documents and skills,
  `evals/evals.json`) and **Internal** (`THREE_X_PATTERNS`, `scan`'s `flags`
  argument, `tests/test_docs_describe_4_0.py` and its `UNMIGRATED_RECORDS`,
  `tests/test_migration_guide_4_0.py`, the index test, the one
  `GIT_ALLOWED` phrase).

### 11. Building it in parts

The item stays one item (decided by the dispatching session, 2026-10-22, D4:
its documents describe one 4.0, and a split would put the same facts in two
items' reviews). The plan builds it in three parts, each committed on its own
with the suite as CI runs it green after it, as TCW-111 did:

1. **The migration guide and its test**: `THREE_X_PATTERNS` and `scan`'s
   `flags` argument in `tests/doc_vocabulary.py` (9.2, which 9.4 (h) reads),
   `docs/migration-guide-3.X-to-4.0.0.md`, `tests/test_migration_guide_4_0.py`
   (9.4), and the README index line with its test (3.6, 9.5).
2. **The README, the guides, the use cases, the agent and lifecycle documents
   and the design amendments**: Design 3 (but 3.6), 4, 6, 7 and 8.
3. **The skills, the other shipped text, the evals, the ledger and the
   scan's test**: Design 5, 9.6 (a) and (b), 9.8, and
   `tests/test_docs_describe_4_0.py` (9.2), which goes in last because it
   fails until every live document is rewritten; and the upcoming entries
   (10).

Before part 1, one commit formats with `prettier` every Markdown file in
scope that the item will change, and changes nothing else, with the suite
passing after it; each part's commit then shows only content. Decided by the
dispatching session, 2026-10-22 (plan review D2): criterion 39 formats every
changed Markdown file, prettier alone changes over a hundred lines of some of
them (`README.md`, the TCW-99 design), and mixing that into the content
commits would bury the changes the review must read. CI does not run
prettier (`.github/workflows/test.yml` runs `pytest` and `pnpm check:build`),
so criterion 39 is this repository's own rule, checked locally.

## Abstraction litmus test

No operation is added or changed: this item changes documents, eval data and
tests only. The documents it writes describe both layers of design.md:113-133,
and Design 1.7 makes each guide say which is which, so a reader does not take
a deployment-layer fact (a manifest, the search, `.path`, provisioning,
worktrees) for something every store must support.

## Use cases

Every case is touched, because this item rewrites `docs/use-cases.md` and the
guides that describe each setup; Design 6 says how each case's text changes.
How each case reads the documents:

- **UC-1**: the README, `docs/guide/configuration.md` and the setup skill show
  a single project needing no more than in 3.x: `tcw project new`, one
  `.tcw/tcw-config.yaml`, no parent links (TCW-99 success criterion 3). The
  migration guide's "Migrating one project" is all such a project reads.
- **UC-2, UC-7**: the multi-repo guide and the migration guide say a library
  keeps `.tcw/tcw-migration.yaml`, and that readers name it as a parent it
  does not list back (Design 2.4 (h), 4.5 (b)). Nothing in the documents asks
  a library to name its readers.
- **UC-3**: the migration guide's parents-first order and what stops in a
  package below a 3.x parent (Design 2.5 (b)); the epic-parts table (2.7).
- **UC-4**: "left in another repository" (Design 2.5 (d)), the workspace as an
  `inherit: none` parent, and running a change in the owning project with
  `tcw -C` (4.5 (h)).
- **UC-5**: one search per Jira project, account and stage mapping (4.3 (d));
  the inherited `work.jira` (4.2 (d)).
- **UC-6**: exit 7, "could not check", "unavailable, exit 0", and
  `tcw project provision` (4.5 (f), (j)).
- **UC-8**: the manifest decides, two matches are an error, and
  `TCW_PROJECT_<ID>` (4.5 (e)).
- **S-1, S-6**: the cold read of Design 9.7 is run by the qa stage, and the
  optional eval run of 9.6 (c) only if the user chooses it; the person who
  decides qa on this project decides on their findings. Nothing in the
  documents changes who decides.
- **S-2**: the skills keep every command fallback (Design 1.8), and the eval
  run, if the user chooses it, uses the harness that pins the plugin and the
  `tcw` to this checkout, started with the worktree's own Python (9.6 (c)).
- **S-3**: the Jira guide says what Jira does not show (4.3 (e)).
- **S-4**: worktrees in the multi-repo guide (4.5 (k)); the bound in a linked
  worktree (2.9 (f)).
- **S-5**: personal settings and environment overrides (Design 2.8, 4.2 (e));
  S-5's reworded requirement (6.3).
- **S-7**: everyone upgrades together, and a second person's `tcw migrate`
  (Design 2.3 (c), 2.4 (g)).
- **S-8**: the progress record and running again (Design 2.4 (f)).
- **S-9**: the migration guide itself; the scan of 9.2 is the requirement that
  new documents name no retired form, made a test.
- **S-10**: the search never looks inside a project (6.3).
- **S-11**: `tcw migrate` does not check git and commits nothing; the guide
  tells the person to commit or back up (Design 2.3 (b), 2.4 (j)). No shipped
  text tells an agent to commit (`test_no_shipped_text_names_git`).

The checklist: (1) where it looks: no code; (2) whose things it touches: only
this repository's documents, eval data, tests and five ledger records; (3)
reads across projects: no; (4) backends: the Jira guide and the migration
guide cover both; (5) who: qa's person decides; (6) harness: Design 1.8;
(7) stops halfway: the guide's progress-record section; (8) single project:
Design 2.4 is all it reads; (9) older or newer TCW: the guide is the answer;
(10) the setup it claims: the cold read uses a real 3.x project.

## Acceptance criteria

Each criterion is checked against the files on `v4` after this item's
implement stage. "The review lists" means the review round names each lettered
item as present or absent, with the line where it is.

1. `docs/migration-guide-3.X-to-4.0.0.md` exists, and its level-2 headings are
   Design 2.2's, in that order (`test_migration_guide_4_0`, 9.4 (a)).
2. Its "Before you start" holds Design 2.3 (a) to (f), and (a) links
   `migration-guide-2.8-to-3.0.0.md` (the review lists; the link by 9.4 (g)).
3. Its "Migrating one project" holds Design 2.4 (a) to (s), with (k) first,
   and its exit-code table's rows are exactly 0, 1, 2, 3 and 5 (the review
   lists; the rows by 9.4 (f)). Each meaning, and each line form and heading
   of 2.4 (b), matches `tcw migrate`'s behaviour and output on `v4`
   (`tcw migrate --help`, a dry run in a scratch 3.x project pasted in the
   implement round, and TCW-116's tests named in its implement round).
4. Its "Migrating related projects" holds Design 2.5 (a) to (f) (the review
   lists, and compares each with TCW-116's tests for it).
5. Every name of `THREE_X_NAMES` is in the first column of a mapping table, no
   mapping row's second column is empty, every `tcw …` command the guide
   writes outside a mapping table's first column and the epic-parts table's
   3.x column resolves in the 4.0 parser, and every `THREE_X_PATTERNS` entry
   matches a first-column cell (`test_migration_guide_4_0`, 9.4 (b) to (d)
   and (h)).
6. The guide holds Design 2.6 (h) to (k) and the "New in 4.0" table naming each
   command of 2.6 with a link (the review lists).
7. The epic-parts table has rows a to f, each 4.0 command resolves, and its rows
   say what TCW-114 Design 3.1 says as landed (`test_migration_guide_4_0`
   9.4 (d), (e); the review compares the rows).
8. "Personal settings and environment variables" holds Design 2.8 (a) to (g),
   every example variable names a key on the allowed list, and each, set in a
   scratch project with that ID, changes the value
   `tcw project config --origin` prints for that key (the review lists; the
   implement round shows the run).
9. "Where provisioning may place a clone" holds Design 2.9 (a) to (i), and the
   multi-repo guide states the same rules (the review lists both).
10. "Scripts, hooks and agent instructions" holds Design 2.10 (a) to (e) (the
    review lists).
11. The README holds Design 3.1 to 3.6 (the review lists), and the index test
    requires the new guide (9.5).
12. `docs/guide/cli.md` holds Design 4.1 (a) to (g), names the removed
    commands by their verbs only, and `test_cli_guide` passes (the review
    lists).
13. `docs/guide/configuration.md` holds Design 4.2 (a) to (j) (the review
    lists).
14. `docs/guide/jira.md` holds Design 4.3 (a) to (i) (the review lists).
15. `docs/guide/linking-and-validation.md` holds Design 4.4 (a) to (f), and each
    finding of (e) is worded as `tcw validate` on `v4` prints it (the review
    lists and compares).
16. `docs/guide/multi-repo.md` is titled "Related projects" and holds Design
    4.5 (a) to (l) (the review lists).
17. `docs/guide/taxonomy-and-capabilities.md` holds Design 4.6 (a) to (g) (the
    review lists).
18. `docs/guide/web-viewer.md` holds Design 4.7 (a) to (c) (the review lists).
19. `docs/guide/work.md` holds Design 4.8 (a) to (d) (the review lists).
20. The `work` skill and its references hold Design 5.1 (a) to (k) (the review
    lists).
21. The `taxonomy` skill holds Design 5.2, and the `capabilities` skill Design
    5.3 (the review lists).
22. The `configure` skill and its references hold Design 5.4 (a) to (f) (the
    review lists).
23. The `setup` skill and its references hold Design 5.5, naming the
    migration guide by its file and GitHub address (the review lists).
24. Design 5.6 (a) to (c) hold (the review lists), and (d) holds by criterion
    31.
25. `docs/use-cases.md` holds Design 6.1, and each UC of Design 6.2 says what
    6.2 gives it (the review lists, case by case).
26. Each S of Design 6.3 says what 6.3 gives it (the review lists).
27. Each known gap of Design 6.4's table is removed, re-marked or kept, and the
    implement round gives, for each, the file and line on `v4` that decided it
    (the review checks each against the code).
28. Design 6.5 and 6.6 hold (the review lists).
29. `AGENTS.md` and the lifecycle documents hold Design 7.1 and 7.2 (the review
    lists).
30. `design.md` holds Design 8.1 to 8.7, each with its dated line naming who
    decided it and where it is recorded (the review lists).
31. `tests/test_docs_describe_4_0.py` passes; its own tests of 9.2 pass (a hit
    for each pattern in a scratch document outside a block naming
    `tcw migrate` fails, the same hit in such a block passes, a hit under
    `docs/capabilities/` is not reported while `UNMIGRATED_RECORDS` exists,
    and `tcw-work-item.yaml`, a manifest's `projects:` key and the prose "TCW
    projects:" pass); `THREE_X_PATTERNS` holds P1 to P12 as Design 9.2's
    table gives them, each reason ending "(scan: TCW-117)"; and
    `UNMIGRATED_RECORDS` holds exactly `docs/taxonomy/` and
    `docs/capabilities/`, with its comment naming TCW-118 (the suite; the
    review reads the table).
32. The grep of Design 9.3 prints nothing (the review runs it and pastes the
    empty result).
33. Every test of Design 9.1 passes, and the implement round lists each test
    whose expected text changed, with its reason.
34. `evals/evals.json` holds Design 9.6 (a):
    `grep -nE '(^|[^/])tcw-config\.yaml|tcw init|(^|[^-a-z])(item|meta)\.yaml' evals/evals.json`
    prints nothing (a `tcw-config.yaml` is allowed only as
    `.tcw/tcw-config.yaml`, and `tcw-work-item.yaml` is not matched); the dry
    runs of 9.6 (b) print every arm; `tests/test_eval_*.py` pass.
35. At qa, the cold read of Design 9.7 reaches `tcw validate` exit 0 in the
    scratch copy, and the qa round records, before the session starts, the
    copy's removed remote, its Jira site and credential names as 9.7 (b) sets
    them, the two empty folders `XDG_CONFIG_HOME` and `XDG_CACHE_HOME` name,
    `env | grep -c '^TCW_JIRA'` printing 0 and `tcw --version` printing
    4.0.0; it records the person's own user-wide file and store cache as
    unchanged after the session; and it lists every guess or failed command,
    each a finding (the qa round).
36. The five capability records of Capability changes, and any the one-off
    scan of 9.8 led to, describe 4.0 in their prose, are in 3.x form (a
    `meta.yaml` each, their `tcw://` links unchanged), are listed in
    `capabilities.yaml`; the scan's output is in the implement round, with
    every hit outside P8 fixed; and `tcw validate`, run from the worktree's
    root with the `tcw` first on the path (which prints 3.0.2), exits 0 (9.8).
37. Every `tcw -C` in a live document gives its target as one word (criterion
    33's command checks fail otherwise; the review greps
    `git grep -n 'tcw -C' -- <the live documents>`).
38. Both upcoming files of Design 10 exist and pass `test_upcoming_entries`.
39. The suite as CI runs it: bare `.venv/bin/pytest` from the worktree's root
    passes, and `pnpm exec prettier --check` passes over every Markdown file
    this item changed that `.prettierignore` does not exclude.
40. Every row of Notes, "Handoffs answered", is answered in the documents, and
    the review round marks each row (the review).
41. Every technical term is defined where a document first uses it, and no
    document uses the shorthand the user's instructions forbid (the review,
    document by document).
42. The two strict tables are unchanged: `git diff <base> -- tests/doc_vocabulary.py`
    changes no entry of `PATTERNS` and touches `scan` only by adding `flags`;
    `git diff <base> -- tests/test_shipped_text.py` changes nothing in
    `GIT_WORDS`, and adds to `GIT_ALLOWED` only the phrase of Design 5.7 (a),
    with its reason (`<base>` being the commit before this item's first). The
    review also reads every fenced block of YAML in a live document, and
    finds none showing a 3.x shape (Design 1.6 (b)) (the review pastes the
    diffs).
43. The item was built as Design 11 gives it: one formatting-only commit,
    then the three parts, each a commit of its own, with the suite as CI runs
    it passing after each of the four (the implement round names each commit
    and its suite result, and shows that `git diff --word-diff -w` of the
    formatting commit changes only Markdown markup).

### Coverage

The numbered rules are Design 1 to 11; each row names the criteria that check
it and how.

| Rule | Criteria | Checked by |
| --- | --- | --- |
| 1.1 the code decides | 3, 8, 15, 27 | runs on `v4`, recorded in the implement round |
| 1.2 the starting lists | 40 | review against each sibling's implement round or plan step |
| 1.3 plain language, "slug" | 41 | review |
| 1.4 one token after `-C` | 37, 33 | `test_documented_cli_surface`, `test_shipped_text`, `test_docs_describe_3_0` |
| 1.5 one home per fact | 11-24 | review (each home holds the full statement) |
| 1.6 3.x forms only about 3.x; (a) no removed command; (b) no fenced example; (c) the 3.0 words | 31, 32, 12, 42, 33 | `test_docs_describe_4_0`; the grep; the review of cli.md and of fenced blocks; `test_docs_describe_3_0` |
| 1.7 two layers | 16 (4.5 (l)) | review |
| 1.8 every harness | 33 | `test_every_injection_has_a_manual_fallback` |
| 2.1 the file and its links | 1, 11, 23, 26 | `test_migration_guide_4_0`; index test; review |
| 2.2 the sections | 1 | `test_migration_guide_4_0` (a) |
| 2.3 before you start | 2 | review; link check |
| 2.4 one project | 3 | review; exit table test (f); the dry run on `v4` |
| 2.5 related projects | 4 | review against TCW-116's tests |
| 2.6 the mapping | 5, 6 | `test_migration_guide_4_0` (b)-(d), (h); review |
| 2.7 epic parts | 7 | `test_migration_guide_4_0` (d), (e); review |
| 2.8 personal and environment | 8 | review; the scratch run |
| 2.9 the bound | 9 | review |
| 2.10 scripts and instructions | 10 | review |
| 3.1-3.6 README | 11 | review; index test |
| 4.1 cli.md | 12 | review; `test_cli_guide`; the grep |
| 4.2 configuration.md | 13 | review |
| 4.3 jira.md | 14 | review |
| 4.4 linking-and-validation.md | 15 | review against `tcw validate` output |
| 4.5 multi-repo.md | 9, 16 | review |
| 4.6 taxonomy-and-capabilities.md | 17 | review |
| 4.7 web-viewer.md | 18 | review |
| 4.8 work.md | 19 | review |
| 5.1 work skill | 20 | review; `test_shipped_text` |
| 5.2, 5.3 taxonomy, capabilities skills | 21 | review; `test_shipped_text` |
| 5.4 configure skill | 22 | review; `test_docs_describe_3_0` |
| 5.5 setup skill | 23 | review |
| 5.6 other shipped text | 24, 31 | review; `test_docs_describe_4_0` |
| 5.7 the git check | 42, 33 | the diff; `test_no_shipped_text_names_git`, `test_every_git_allowance_is_still_needed` |
| 6.1 use-cases opening | 25 | review |
| 6.2 the architectures | 25 | review |
| 6.3 the situations | 26 | review |
| 6.4 known gaps | 27 | review against the code |
| 6.5, 6.6 checklist, closing | 28 | review |
| 7.1, 7.2 agent and lifecycle documents | 29, 32 | review; the grep |
| 8.1-8.7 design amendments | 30 | review |
| 9.1 existing checks, the strict tables | 33, 42 | the suite; the diff |
| 9.2 the scan, its case, its exclusion | 31 | `test_docs_describe_4_0` and its own tests |
| 9.3 the grep | 32 | the grep |
| 9.4 the guide's test | 1, 5, 7 | `test_migration_guide_4_0` |
| 9.5 the index test | 11 | `test_the_documentation_index_links_the_guides_it_must` |
| 9.6 evals (a), (b) | 34 | grep; dry runs; `tests/test_eval_*.py` |
| 9.6 (c) the optional paid run | none: not an acceptance criterion (D2) | the QA plan's optional check, if the user chooses it |
| 9.7 cold read and its safeguards | 35 | qa |
| 9.8 ledger | 36 | the one-off scan; `tcw validate` (3.0.2) |
| 10.1 upcoming entries | 38 | `test_upcoming_entries` |
| 11 the three parts | 43 | the implement round |

## Risks

- **The documents can be written before the code they describe is final.**
  This item is finished last, but a sibling's review or qa can still change
  behaviour after its text here is written. Design 1.1 has every statement
  checked on `v4` when written; the review re-runs the commands its criteria
  name.
- **Line numbers drift.** Every passage cited here moves as the siblings land.
  The criteria are by content, not by line, and the plan re-finds each passage
  by its words.
- **The paragraph allowance of 9.2 is looser than an exception table.** A
  paragraph naming `tcw migrate` could still teach a removed command as if it
  worked. Criterion 32's grep has no allowance for removed commands and flags
  in the teaching documents, and the review reads each allowed hit.
- **The ledger records are not guarded by the scan until TCW-118.**
  `UNMIGRATED_RECORDS` leaves them out of the test (Design 9.2), so a record
  changed after this item's one-off scan (9.8) can state a 3.x form in prose
  unnoticed until TCW-118 deletes the tuple. The window is short (no item
  after this one but TCW-118 changes records on `v4`), and TCW-118's step 3
  runs the suite with the tuple gone before the migration is committed.
- **The eval run, if the user chooses it, costs money and can be noisy.** It
  is optional (Design 9.6 (c)); its cost is stated to the user before it runs,
  and a failure is read with the case's `note` before it is called a defect.
- **An agent editing configuration on `v4` edits the file `AGENTS.md` names,
  `.tcw/tcw-config.yaml`, while the 3.0.2 lifecycle reads the root file.**
  `tests/test_repo_config_pair.py` fails when the two differ, so the suite
  stops it until TCW-118 removes the root file (Design 7.1).
- **The cold read can fail for a reason that is not the guide** (a migration
  defect). A failure is reported to the dispatching session with the command
  and its output; it is a TCW-116 defect if `tcw migrate` misbehaves, and this
  item's if the guide misled.
- **Agents on `v4` are taught 3.x until this item lands** (TCW-115 Risks). The
  removed commands' suggestion lines soften it; nothing is released before
  TCW-118.

## Notes

### Decisions, each decided by the dispatching session, 2026-10-22

Decisions 16 to 25 were added in the revision after the spec review, and 26
to 32 after the plan review.

1. **The guide's name and place**, `docs/migration-guide-3.X-to-4.0.0.md`
   (Design 2.1): it follows the earlier guides' names, and the prefix
   `docs/migration-guide-` is already archival for the command check, so its
   3.x column needs no exception.
2. **A short guide built on `tcw migrate`** (Design 2.2): unlike the 2.8 to 3.0
   guide, which was a manual procedure in 13 steps, `tcw migrate` does the
   conversion, so the guide says how to run it and read it, then maps every
   name.
3. **No new guide besides the migration guide; `multi-repo.md` keeps its
   name** (Design 4.5): other documents and tests link it, and a rename is a
   change of its own.
4. **The passages siblings changed only partway are rewritten from the
   siblings' lists** (Design 1.2), from TCW-107, TCW-108, TCW-112, TCW-113,
   TCW-114 and TCW-115, not only the last two: the grep and the scan look for
   forms, not meaning (S2).
5. **A permanent scan with a paragraph allowance, plus a strict grep for
   commands and flags** (Design 9.2, 9.3): the reason is given at 9.2.
6. **No paid eval run in the criteria; no new cases** (Design 9.6 (c),
   Non-goals; D2): none of the five cases uses a 4.0 feature, so a run would
   not show the 4.0 skills work; it is an optional qa check the user may
   choose, its cost stated first.
7. **A cold read of the guide at qa on a scratch copy of `main` that cannot
   reach the live board by construction** (Design 9.7; M6): a removed remote,
   an unresolvable Jira site, credential names set nowhere, and no
   `TCW_JIRA_*` variable in the session; the guide given by its absolute path
   in the `v4` worktree.
8. **The TCW-99 design is amended only where a decision is already recorded**
   (Design 8): the request's Constraints keep design disagreements on TCW-99.
9. **Five skill capability records change, all records are edited in 3.x
   form, and prose leftovers a one-off scan finds are fixed here**
   (Capability changes, Design 9.8; M3, M4).
10. **`AGENTS.md` and the lifecycle documents name `.tcw/tcw-config.yaml` now**
    (Design 7.1).
11. **Known gaps are decided against the code**, with the expected outcomes of
    Design 6.4: the siblings' specs say what each should close, but only the
    code shows what did.
12. **This item writes its own upcoming entries** (Design 10): the house rule
    is one pair per item, combined at the cut; "release notes for 4.0" in the
    request's Out of scope is the combined notes, TCW-118's.
13. **The two procedures TCW-110 named are this item's** (Design 5.6 (a)); the
    other prompts and procedures are their siblings', and only the scan reads
    them here.
14. **S-5's wording combines TCW-107's and TCW-109's** (Design 6.3): both
    narrow the same sentence, one for manifests and one for configuration.
15. **The setup skill names the migration guide by file and GitHub address**
    (Design 5.5): a skill may be installed without the repository's `docs/`.
    The work skill does the same (5.1 (j)).
16. **The scan leaves the ledger records out until TCW-118 migrates the
    repository** (Design 9.2; M3): the reason is given at 9.2; TCW-118
    deletes `UNMIGRATED_RECORDS` (Handoff to TCW-118).
17. **The records are checked with the 3.0.2 `tcw` on the path** (Design 9.8;
    M4): v4's own `tcw` reports every 3.x object folder.
18. **`cli.md` names the removed commands by verb only; the full suggestion
    lines are only in the migration guide** (Design 1.6 (a), 4.1 (g); M5).
19. **P6 drops `\bprojects:`, P7 gains a look-behind, P2 stops at a
    backtick, and the table is matched case-sensitively through a `flags`
    argument to `scan`** (Design 9.2; M1, M2, S5, S6).
20. **The scan is permanent, each reason naming TCW-117** (Design 9.2; D3).
21. **One item, built in three parts** (Design 11; D4).
22. **One new `GIT_ALLOWED` phrase, `` `<url>#<branch>` `` in `projects.md`;
    the provisioning bound stated without the banned words** (Design 5.7;
    S10).
23. **The 3.0 scan's `PATTERNS` is not loosened; passages about 3.x avoid its
    words** (Design 1.6 (c); S12).
24. **Amendment 8.4 states the store's `repository` as settled**, citing the
    dispatching session's comment on TCW-99 of 2026-10-22, 21:06 (D1); and
    8.5 to 8.7 record the user's and TCW-109's corrections (S7).
25. **The migration guide's commands are checked by its own test, and every
    scan pattern must have a mapping row** (Design 9.4 (d), (h); S4).
26. **P12 matches only a 3.x pointer, `^\s*overrides:\s*[^\s./]+/`** (Design
    9.2; plan review D1): 4.0's `show` prints `overrides: <full id>`, whose
    first part always holds a dot.
27. **A fenced line never carries the allowance** (Design 9.2, 1.6 (b); plan
    review D3).
28. **The migration guide's commands are checked against the surface read
    from `--help`** (Design 9.4 (d); plan review M3), so a hidden, removed
    flag fails.
29. **The removed commands' printed lines are given word for word, split at
    the command in a two-column table; a mistyped command is written in
    prose** (Design 2.10 (d), 4.1 (g); plan review Q1.2, Q1.3).
30. **One formatting-only commit comes before part 1** (Design 11; plan
    review D2).
31. **Scratch runs and the cold read set `XDG_CONFIG_HOME` and
    `XDG_CACHE_HOME`, never `TCW_CONFIG_DIR`** (Design 9.7 (c); plan review
    M1); the plan also sets `HOME` for its own scratch runs.
32. **A 3.x form left in a passage a sibling rewrote in full is fixed here**
    (Design 1.2; plan review M2).

### Handoffs answered

The comments on this ticket, oldest first, and the sibling plans'
Documentation Sync deferrals. "H" rows are comments; "D" rows are plan rows
not already in a comment.

| # | From | What it asks | Design | Criteria |
| --- | --- | --- | --- | --- |
| H1 | sibling specs, 14:45 | TCW-107's list (UC-1, UC-3, UC-6, UC-8, S-5, S-10; multi-repo and projects.md locators) | 4.5, 5.4 (a), 6.2, 6.3 | 16, 22, 25, 26 |
| H2 | TCW-107, 15:35 | README `:232`, `:263`, `:299`; cli.md `:147`; work.md `:383`, `:414`; multi-repo; UC-1, UC-3, UC-6, UC-8, S-5, S-10; projects.md, stores.md `:88`, setup project.md and install.md, commands.md `:28`; empty or `.git`-only folder | 3.1, 3.3, 3.4, 4.1 (e), 4.5 (e), 4.8 (c), 5.1 (i), 5.4 (a), (b), 5.5, 6.2, 6.3 | 11, 12, 16, 19, 20, 22, 23, 25, 26 |
| H3 | TCW-111, 15:42 | `--nest` with `--parent` in the work skill and commands.md `:10`; taxonomy skill `:91`; capabilities `--parent`; `meta.yaml`/`item.yaml`; S-10 "object folder"; designs in `resources/` | 4.6 (e), 4.8 (a), 5.1 (b), 5.2, 5.3, 6.3, 9.2 P7 | 17, 19, 20, 21, 26, 31 |
| H4 | TCW-108, 15:43 | UC-2, UC-3, UC-4, UC-6, S-6; multi-repo, projects.md, taxonomy-and-capabilities: upstream, `projects:`, `extends` | 3.3, 4.3 (g), (h), 4.5 (b), 4.6 (a), 5.4 (a), 6.2, 6.3 | 14, 16, 17, 22, 25, 26 |
| H5 | TCW-110, 15:44 | `tcw://` grammar in README and linking guide; links to any project; 3.x links; store locations; `TCW Item`; `full-id`, `owner`, schema 2; UC-4, UC-6; skills' names and input forms; search.md `:27`, pause-work.md `:22` | 2.6 (f), (g), 3.2, 4.1 (b), (d), 4.3 (a), (b), 4.4 (a)-(c), 4.5 (i), 5.1 (e), 5.4 (b), (d), 5.6 (a), (b), 6.2 | 5, 11, 12, 14, 15, 16, 20, 22, 24, 25 |
| H6 | TCW-108, 16:45 | the work skill's exit codes (exit 3, exit 7 advice); `extends` wording in two skills | 5.1 (c), 5.2, 5.3 | 20, 21 |
| H7 | TCW-109, 17:59 | inherited keys, backend own, naming rule, merge, allowed list, exit 7 and remedies, broken-value warning, tags in a child; S-5, UC-5, UC-6; filesystem versus Jira-mode with a missing parent | 2.8, 4.2 (d)-(g), (j), 4.3 (c), 4.8 (d) (`add` and `rm`), 5.1 (c), (h), 5.4 (c), (d), 6.2, 6.3, 8.5-8.7 | 8, 13, 14, 19, 20, 22, 25, 26, 30 |
| H8 | TCW-114, 18:01 | the 3.1 table and `--blocks`; skills and guides teaching `--project`/`--blocks`; the wording flow; move and rename; recorded parents and blockers in Jira; UC-3, UC-4; S-3 | 2.6 (b), 2.7, 3.3, 4.1 (e), 4.3 (e), (g), 4.5 (h), 4.8 (b), 5.1 (a), (g), 5.3, 6.2, 6.3 | 5, 7, 11, 12, 14, 16, 19, 20, 21, 25, 26 |
| H9 | TCW-112, 18:04 | the fuller rewrite; UC-2, UC-3, UC-6, S-4, S-6, the "Inheritance" row; design.md:467-470 | 2.6 (c), (i), 4.6 (a)-(c), 5.2, 5.3, 6.1, 6.2, 6.3, 8.1 | 5, 6, 17, 21, 25, 26, 30 |
| H10 | TCW-115, 18:49 | `--origin` shape; where a clone may go; `.git`-only; `.tcw-staging`; `tcw new` and `tcw list` suggestions | 2.6 (a), (g), 2.9, 4.1 (g) (with `tcw new` and `tcw list`), 4.2 (h), 4.5 (j), 5.1 (k), 5.4 (f), 5.5, 5.7 (b) | 5, 9, 12, 13, 16, 20, 22, 23, 42 |
| H11 | TCW-109, 18:50 | drift exits 7; commands that never stop; whose mistake is reported how | 4.2 (g), (j) (with the commands that never stop), 4.6 (f) | 13, 17 |
| H12 | TCW-112, 18:54 | Steps 5a and 19's passages; use-cases `:92`, `:142-189`, `:369`, `:509`; the web body edit | 4.6 (b), 4.7 (c), 5.3, 6.1, 6.2 | 17, 18, 21, 25 |
| H13 | TCW-113, 19:00 | skills on `--scope`; cli.md, web-viewer `:17-19`, mixed status, family views, one search; UC-3, UC-4, UC-5, UC-6; the guide on default listings, `--local`, `show <id-path>`; design.md:649-651 and :657-665 | 2.6 (b), (h), (i), 3.3, 3.5, 4.1 (c), (d), 4.3 (d), 4.5 (f), (g), 4.6 (d), 4.7 (a), 5.1 (d), 5.2, 5.3, 6.2, 8.2, 8.3 | 5, 6, 11, 12, 14, 16, 17, 18, 20, 21, 25, 30 |
| H14 | TCW-114, 19:01 | the passages Step 7 changed, by line | 1.2, 5.1 (a), (i), 5.3, 5.4 (a), 4.1 (e), 4.3 (g), 4.5 (h), 4.8 (b), 3.5, 6.2 | 40, and those rows' criteria |
| H15 | TCW-115, 19:45 | the 43 renamed files; its implement list; `AGENTS.md` off the list; one-token `-C`; hidden folder; unreadable `.git` | 1.2, 1.4, 2.9 (c), (d) | 9, 37, 40 |
| H16 | TCW-113, 19:50 | web pickers and filter; token sharing and a write; backlog audit and `-C`; `--project` with no `statuses`; plan extras (show warning, web records, never grouping, the README row) | 3.5, 4.1 (c) (never grouping), 4.3 (d), 4.5 (f) (the `show` warning), 4.7 (a) (web records), (b), 5.1 (f), 5.3 | 11, 12, 14, 16, 18, 20, 21 |
| H17 | TCW-115, 20:18 | the bound in a submodule and a linked worktree | 2.9 (e), (f), 4.5 (j) | 9, 16 |
| H18 | TCW-116, 20:35 | `tcw migrate`, `--dry-run`, `--no-jira`; exit codes; the three lists; Jira while planning; the progress record; back up; parents first and what stops; everyone upgrades; `not_tags`; the migration record; the term `migration`; S-8, S-9; `repository` on a store | 2.3 (b), (c), 2.4, 2.5, 2.6 (d), 4.2 (b), 4.3 (i), 4.5 (i), 5.4 (b), 6.3, 8.4 | 2, 3, 4, 5, 13, 14, 16, 22, 26, 30 |
| H19 | TCW-116, 21:30 | a move across filesystems; `--no-jira` needs no credentials, and a dry run edits no ticket; whose `work.jira` a run uses; a hand edit between runs (B17); A12 and B10 | 2.4 (m) to (q) | 3 |
| H20 | TCW-116, 21:53 | the stopped run's line, quoted; `--no-jira` leaves the work store unchecked, and the summary's line; a re-run while Jira cannot be reached writes nothing more, and its line | 2.4 (f), (r), (s) | 3 |
| D106 | TCW-106 plan Step 8 | README (configuration location), guides, skills (file location), configure references (`not-tags`, `tcw-version`), UC-1 layout; the eval cases (spec Non-goals) | 2.6 (d), 3.1, 4.2 (a), (i), 5.4 (d), 6.2, 9.6 (a) | 5, 11, 13, 22, 25, 34 |
| D107 | TCW-107 plan, Documentation Sync | H2's list, and `skills/work/SKILL.md:115` changed partway | as H2, 1.2 | as H2, 40 |
| D108 | TCW-108 plan Step 15 | README (parent links, no upstream, exit 7); jira.md `:245`; commands.md table already changed | 3.3, 4.3 (g), (h), 5.1 (i) | 11, 14, 20 |
| D109 | TCW-109 plan Step 13 | README (settings shared down, variables); jira.md (`work.jira` from a parent) | 2.8, 3.3, 4.2 (d), 4.3 (c) | 8, 11, 13, 14 |
| D110 | TCW-110 plan Step 18 | as H5, and 3.2's linking sentence | as H5, 3.2 | as H5, 11 |
| D111 | TCW-111 plan Steps 19-20 | README (state files, `resources/`, `--nest`); jira.md (state file, nested `TCW Item`, key at any depth); validate rows a-n; web "inside the parent's folder"; `tcw work new --nest` in cli.md | 3.2 (state files, `resources/`), 3.5, 4.1 (f), 4.3 (a), 4.4 (e), 4.7 (c) | 11, 12, 14, 15, 18 |
| D112 | TCW-112 plan Step 23 | as H9 and H12 | as H9, H12 | as H9, H12 |
| D113 | TCW-113 plan Step 19 | README (`--scope`, `--project`, `--local`, scope control); as H13 | 3.3, 3.5, as H13 | 11, as H13 |
| D114 | TCW-114 plan Steps 23-24 | `-C` in cli.md's global options; move commands; Jira-mode create form and blockers; README `:608` | 3.5, 4.1 (a), 4.3 (g), 4.7 (c) | 11, 12, 14, 18 |
| D115 | TCW-115 spec Handoffs and plan Step 19 | setup teaches `tcw project new`; configure teaches `--origin` and `project info`; work teaches `project path`; the removed-command table and two new verbs; UC-6's TCW-23 gap closed | 2.6 (a), 5.1 (a), 5.4 (f), 5.5, 6.2, 6.4 | 5, 6, 20, 22, 23, 25, 27 |

| D116 | TCW-116 plan (`5a9ca9b7`, first draft), Step 27 and Documentation Sync | the line forms of Decided 14, with `refused:`; `--no-jira` keeps a run off the live board; a stopped run names its progress record and says not to commit; `jira.md`: `tcw migrate` edits `TCW Item`, and the window in which tickets are hidden; the `setup` **and** `work` skills name how a 3.x project is upgraded; README (a new command); `docs/use-cases.md` S-8, S-9 | 2.4 (b), (c), (f), 3.1, 4.3 (i), 5.1 (j), 5.5, 6.3 | 3, 11, 14, 20, 23, 26 |

TCW-109's note that TCW-111 and TCW-116 need nothing new (18:50) asks
nothing of this item. The TCW-116 plan is cited by its words, not its line
numbers, since its review may move them; if its revision changes a line form
or the hidden-ticket window, the code on `v4` decides (Design 1.1).

### Handoff to TCW-118

Handoff from TCW-117 (spec, revised). Three steps for the release:

- **Switch the scan on for the records.** At TCW-116 Design 9.3 step 3, in
  the merge clone, after `tcw migrate --no-jira` has converted this
  repository's records, delete `UNMIGRATED_RECORDS` from
  `tests/test_docs_describe_4_0.py` (its comment names TCW-118) and run the
  suite as CI runs it. Every hit it then reports in `docs/taxonomy/` or
  `docs/capabilities/` is fixed in that same step, before step 4's commit.
  Done when: `grep -n UNMIGRATED_RECORDS tests/test_docs_describe_4_0.py`
  prints nothing, and bare `pytest` passes in the merge clone.
- **The release notes** link `docs/migration-guide-3.X-to-4.0.0.md` as the
  way across, and repeat its advice to keep automation that installs
  `tcw-cli` below 4 until a project is migrated (Design 2.3 (f)).
- **The eval run** is not part of TCW-117's acceptance (Design 9.6 (c)). If
  the user wants one before the release, it is the optional check in
  TCW-117's QA plan, run on the merged code; nothing in the release depends
  on it.

### Handoff to TCW-116

Handoff from TCW-117 (spec, revised). Nothing to build. If the cold read of
Design 9.7 finds `tcw migrate` misbehaving, it is reported on TCW-116 with
the command and its output. The migration guide quotes TCW-116's line forms
(its plan's Decided 14); a change to them after this item lands is a
documentation change that item makes in the guide too.
