# Spec — TCW 4.0: the `tcw project` command group

Child 10 of 13 of TCW-99. It carries out these sections of the TCW-99 design
(`docs/work/TCW-99-…/design.md`): "A `tcw project` command group"
(design.md:617-629), the provisioning half of "A related project that is not
on this machine" (design.md:380-396), and "How 4.0 is built"
(design.md:809-841). It absorbs TCW-23 (provision scoping, and how far a
clone may be placed by a configuration found more than one step away), and
answers its question in Design 7.8.

**Order.** The children land on the `v4` branch in the order TCW-106,
TCW-107, TCW-110, TCW-108, TCW-111, TCW-109, TCW-112, TCW-114, then this
item (TCW-113 lands at about the same point and touches none of the same
commands). So when this item starts:

- every project has `.tcw/tcw-config.yaml` with `tcw-version` (TCW-106);
- a project's folder is found from its ID by one registry method,
  `FsProjectRegistry.project_folder` (TCW-107 Design 2.12), through manifests
  (`.tcw/tcw-manifest.yaml` and `.tcw/tcw-manifest.local.yaml`, TCW-107
  Design 1), `TCW_PROJECT_<ID>` (TCW-107 Design 2.1) and a bounded search;
  `tcw provision` no longer fetches projects (TCW-107 Design 6.3);
- projects are linked by `parents:` and `children:`, and the registry
  answers `parents()`, `declared_child_ids()`, `load_order()` and
  `sources()` (TCW-108 Design 3.2);
- configuration is inherited through those links, and every value records
  the project and the file or variable it came from (TCW-109 Design 2.6);
- every taxonomy and capability record carries `overrides` (TCW-112 Design
  3.3);
- `tcw -C <folder or address>` runs any command as if started in that
  folder, and only the active project changes anything (TCW-114 Design 1,
  4); the `read-only` field TCW-108 added to `tcw projects list --json` is
  gone again (TCW-114 Design 1.8).

File and line references are to commit `d2d02829` on `v4`, where TCW-106 is
built and none of TCW-107 to TCW-114 is. Those items change much of the code
cited here (TCW-107 rewrites `tcw/store/project.py` and removes project
fetching from `tcw/cli.py`; TCW-108 rewrites `tcw/projects_cli.py`), so the
plan re-checks every reference against what they land. "TCW-10n Design m"
means rule m of that item's spec.

Terms used throughout, each in the sense of the specs above:

- **The active project** is the project a command runs in (TCW-99
  requirement 7).
- **A project's family** is the project, its ancestors (its parents, their
  parents, and so on) and its descendants (the children it lists, the
  children they list, and so on), never a sibling (TCW-108's terms).
- **The load order** is the list of a project's ancestors and the project
  itself, farthest first, in the order their values are read (TCW-108
  Design 4).
- **The deciding manifest entry** for a project is the first entry for its
  ID in the manifests TCW-107 Design 2.2 consults; entries never merge.
- **A clone** is a copy of a git repository fetched from the address it is
  kept at (its remote). **The repository folder** of a manifest entry is its
  `path` with its `subfolder` removed (TCW-107 Design 1.6): where the whole
  repository goes, as opposed to where the project sits inside it.
- **Not on this machine** is TCW-107 Design 2.12's outcome of that name: a
  project something names, whose folder is absent or empty (TCW-107 Design
  2.3). **Unknown** is its other outcome: a project ID nothing names and
  nothing finds, which is reported as a probable misspelling.

## Capability changes

- **New** `cli/find-where-a-project-is-on-this-machine`: `tcw project path
  <id>` prints the folder of any project TCW can locate from here, or says
  that it is not on this machine and how to fetch it, or that the ID is
  probably misspelt.
- **New** `cli/see-how-a-project-is-assembled`: `tcw project info` shows the
  active project's ID and folder, its parents with what each passes down, its
  children, its load order with any warning, a few settings with the project
  and file each came from, where its stores are, and which of its own
  objects override inherited ones.
- **New** `cli/fetch-a-project-that-is-not-on-this-machine`:
  `tcw project provision` fetches every project of the active project's
  family that is not on this machine, and `tcw project provision <id>`
  fetches one project and its load order; each is cloned into its deciding
  manifest entry's folder, and the projects it names are fetched in turn.
- **Changed** `cli/scaffold-the-doc-trees`: the command is
  `tcw project new`, with `tcw init`'s arguments and behavior.
- **Changed** `cli/list-connected-projects`: the command is
  `tcw project list`; `--json` carries TCW-107's `found` and TCW-108's
  fields, without `read-only`.
- **Changed** `cli/show-the-effective-configuration`: the command is
  `tcw project config`; `--origin` names the project, the layer and the file
  or variable of every value.
- **Changed** `cli/provision-declared-stores`: the command is
  `tcw project provision`; `--component` fetches only the named stores and
  no project; `<id>` fetches one project and no store.
- **Changed** `cli/get-a-suggestion-for-a-mistyped-command`: `tcw init`,
  `tcw projects`, `tcw config` and `tcw provision` are usage errors naming
  their replacement; a synonym valid where it was typed is offered before the
  same word elsewhere, so `tcw work info` still suggests `tcw work show`.
- **Changed**, for the command names in their text only:
  `cli/declare-a-connected-projects-home-repository`,
  `cli/point-tcw-at-a-project-i-already-have`, `cli/locate-tcw-storage-folders`,
  `cli/validate-a-project`, `cli/override-the-team-configuration-for-myself`,
  `cli/host-multiple-projects-in-one-repo`,
  `cli/read-a-file-by-the-format-version-it-records`,
  `work/configure-the-work-store-location`,
  `taxonomy/configure-the-taxonomy-store-location`,
  `capabilities/configure-the-capabilities-store-location`,
  `work/declare-the-work-stores-home-repository`,
  `taxonomy/declare-the-taxonomy-stores-home-repository`,
  `capabilities/declare-the-capabilities-stores-home-repository`.
- **Taxonomy:** changed `cli` (the top-level command set) and
  `project-registry` (the command that lists the projects).

## Problem

1. **What concerns a project itself is spread over four top-level commands.**
   `tcw init` (`tcw/cli.py:557-568`), `tcw provision` (`:570-581`),
   `tcw projects list` (`tcw/projects_cli.py:68-77`, registered at
   `tcw/cli.py:604`) and `tcw config show` (`tcw/config_cli.py:272-287`,
   registered at `tcw/cli.py:605`) sit beside `validate`, `serve` and the
   three axis groups (`docs/taxonomy/cli/description.md:1`). TCW-99 puts the
   first four in one group (design.md:619-626).
2. **Nothing says where an arbitrary project is.** `tcw projects list --json`
   gives a folder only for the projects the configuration connects
   (`connected`, `tcw/projects_cli.py:21-51`). TCW-107 adds a lookup for any
   project ID (TCW-107 Design 2.12) and names `tcw project path <id>` as this
   item's (TCW-107 Non-goals), so a person or an agent told "change it in
   project `app`" (TCW-114 Design 1.3) can find where to run the command.
3. **Nothing shows how a project is assembled in one place.** The load order
   and its warning appear only in `tcw validate` and in `tcw projects list
   --json` (TCW-108 Design 4.5, 8.2); where each setting came from only in
   `tcw config show --origin`, whose labels name a layer and a file but not
   the project (`_Writer.comment`, `tcw/config_cli.py:119-137`); and which
   objects override inherited ones only in each record (TCW-112 Design 3.3,
   3.7).
4. **No command fetches a project.** In 3.x `_provision_projects` walked the
   graph and cloned each connected project that declared a repository
   (`tcw/cli.py:238-376`, called at `:190`), into the declaration's
   `checkout` or a per-machine cache (`checkout_root`,
   `tcw/store/checkouts.py:95-115`). TCW-107 removes that walk (TCW-107
   Design 6.3) because in 4.0 a project is cloned into its deciding manifest
   entry's folder, and its messages already send the person to
   `tcw project provision <id>` (TCW-107 Design 6.2; TCW-108 Design 6.2;
   TCW-109 Design 3.5). The clone code it keeps (`FsStoreProvisioner`,
   `tcw/store/fs.py:3389`, with its project branch, `PROJECT_TARGET`,
   `:3121`, `:3150-3153`) refuses any folder that exists
   (`ensure_available`, `:3437-3445`), while TCW-107 Design 2.3 makes an
   empty folder, or one holding only `.git`, a place a project is simply not
   yet in.
5. **Provisioning cannot be scoped.** `--component` limits only the store
   pass; connected projects are fetched on every run (`tcw/cli.py:190`; the
   description of `cli/provision-declared-stores`). There is no way to fetch
   one named project.
6. **A clone can be placed anywhere by a configuration the person never
   read** (TCW-23). In 3.x a project obtained during the walk could declare
   `repository.checkout` with an absolute path or `..`
   (`parse_repository_declaration`, `tcw/store/base.py:795-862`, `checkout`
   read unbounded at `:837`), and the walk cloned there. In 4.0 the same
   question moves to the manifest of any project other than the active one,
   whose `path` may use `..` (TCW-107 Design 1.4): one fetched in the run,
   and equally one already on this machine that the person never read.
7. **Messages and shipped files name the commands this item removes**:
   `NO_PROJECT` (`tcw/errors.py:13`), the taxonomy and capabilities stores'
   absence (`tcw/taxonomy/cli.py:26`, `tcw/capabilities/cli.py:28`), the
   init refusal for a store with a repository (`tcw/store/fs.py:721`,
   `:727`), an absent store (`:3317`) and an unusable one (`:3444`), a
   configuration with no `id` (`tcw/store/project.py:611`), the `search`
   procedure (`tcw/work/procedures/search.md:27`), the eval fixture builder
   (`evals/seed_fixture.py:761`) and the prompt capture script
   (`tests/fixtures/prompt_fallback/capture.py:67`). TCW-107 already rewrites
   two others (`tcw/cli.py:432`, `tcw/work/open.py:97`).

## Goals

1. Every command about a project itself, rather than its records, is a verb
   of `tcw project`: `new`, `list`, `config`, `provision`, `path`, `info`.
2. A person or an agent can always ask where a project is
   (`tcw project path`) and how the active one was assembled
   (`tcw project info`, `tcw project config --origin`).
3. `tcw project provision` rebuilds every behavior of 3.x project fetching
   that TCW-107 removed, on 4.0's terms: into the deciding manifest entry's
   folder, following the family's links, and never cloning a project that is
   already here.
4. Provisioning can be scoped to one project (`<id>`) or to stores
   (`--component`), and a manifest that is not the active project's own
   places a clone only in a folder directly beside its own project's
   repository, below the home folder, on every run.
5. The removed commands are usage errors that name their replacement, and no
   message or shipped file of the CLI names a removed command.
6. A single project (UC-1) needs no new configuration; its commands differ
   only in name.

## Non-goals

- **`tcw validate` and `tcw serve`**, which stay at the top level
  (design.md:628-629), and `tcw migrate`, which TCW-116 adds at the top level
  as the design names it (design.md:699).
- **What the registry knows.** Parents, children, the load order
  (TCW-108), the lookup and `found` (TCW-107), configuration origins
  (TCW-109) and override records (TCW-112) are their items'; this item only
  shows them. It adds one deployment-layer method to the files store's
  registry (Design 8.1).
- **Fetching another project's stores.** A fetched project whose own store
  declares a repository (`work.repository` and the others) keeps that store
  unfetched; its owner's command fetches it, run there
  (`tcw -C <folder> project provision`, TCW-114 Design 4). Reason: the
  stores pass reads the active project's declarations alone today
  (`declared_repository(project_root, …)`, `tcw/cli.py:137-143`), and
  widening it would put a second, different trust question beside the one
  Design 7.8 settles.
- **Bringing a clone up to date.** As in 3.x, nothing pulls, fetches again
  or switches the branch of a clone already here
  (`cli/provision-declared-stores`).
- **Views across projects** (`--scope`, `--project`, mixed status, showing a
  listed child that is not here as unavailable): TCW-113. The command those
  views name for a missing project, `tcw project provision <id>`, is this
  item's.
- **New options for `tcw project new`**, such as naming parents when a
  project is made. It takes `tcw init`'s arguments unchanged.
- **Rewriting the guides, skills, `docs/use-cases.md` and the migration
  guide** (TCW-117). This item changes each passage there that names a
  removed command only as far as naming its replacement (Design 1.6), so
  the suite's check of documented commands passes; until TCW-117, that prose
  still describes 3.x behavior under the 4.0 command names. Notes lists every
  file outside the CLI that names a removed command.

## Design

Design 2, 3, 4 and 6 show what the model holds (parents, children, the load
order, configuration and its origins, override records), which every store
implements; how they are shown is the CLI's. Design 1 is the CLI's command
set. Design 5 and 7, and the method of Design 8.1, are the deployment layer
(design.md:113-133): folders on this machine and clones of git
repositories.

### 1. The command group

1.1. **`tcw project`** is a command group, registered beside `validate`,
`serve`, `taxonomy`, `capabilities` and `work`, after `work` (the order
matters to Design 1.3's suggestions), with the one-line help
`everything about this project itself: making it, where related projects are,
how it is assembled`. Its verbs:

| Verb | Replaces | Design |
| --- | --- | --- |
| `new` | `tcw init` | 2 |
| `list` | `tcw projects list` | 3 |
| `config` | `tcw config show` | 4 |
| `provision` | `tcw provision` | 7 |
| `path` | (new) | 5 |
| `info` | (new) | 6 |

Each verb's `--help` follows the command standard (`command`,
`tcw/cli_help.py:15-27`): what it is for, `Prints:`, `Writes:`, examples.
`tcw project` with no verb is a usage error (exit 2), as every group is.

1.2. **The removed commands.** `tcw init`, `tcw projects` (any verb),
`tcw config` (any verb) and `tcw provision` are no longer registered, and
`tcw --help` does not list them. Typed, each is argparse's invalid-choice
error (exit 2), and the suggesting parser's one added line
(`SuggestingParser._check_value`, `tcw/cli_suggest.py:107-123`) comes from a
fixed table, checked before every other rule:

| Typed | Added line |
| --- | --- |
| `tcw init …` | `` `tcw init` is now `tcw project new` `` |
| `tcw projects …` | `` `tcw projects list` is now `tcw project list` `` |
| `tcw config …` | `` `tcw config show` is now `tcw project config` `` |
| `tcw provision …` | `` `tcw provision` is now `tcw project provision` `` |

Nothing is run under the new name. Reason: agents and scripts taught 3.x
keep typing these, and the skills that teach them change only in TCW-117;
one line costs nothing and points every harness the same way.

1.3. **Synonyms before the same word elsewhere.** `info` becomes a verb of
`tcw project`, so the suggester's first rule, which names a word that is a
subcommand somewhere else in the tree (`_hint`, `tcw/cli_suggest.py:125-142`),
would answer `tcw work info` with `tcw project info` only, and lose the
synonym `info` → `show` (`SYNONYMS`, `:25-38`) that
`cli/get-a-suggestion-for-a-mistyped-command` promises. So a synonym whose
target is valid at the level where the word was typed is named first, then
the full commands elsewhere, at most three in all: `tcw work info` suggests
`` `tcw work show` or `tcw project info` ``. No other synonym in the table is
a subcommand anywhere, so this rule changes no other suggestion.

The first rule itself does change other suggestions, because `new`, `list`,
`path`, `config` and `provision` become verbs of `tcw project` and the
removed top-level commands leave the tree. Candidates are sorted by depth and
then kept in the order the groups are registered (`_hint`), and at most three
are named (`_MAX`, `tcw/cli_suggest.py:46`); with `project` registered after
`work` (1.1), the suggestions this item changes or adds are:

| Typed | At `d2d02829` | After this item |
| --- | --- | --- |
| `tcw list` | `` one of `tcw projects list`, `tcw taxonomy list`, `tcw capabilities list` `` | `` one of `tcw taxonomy list`, `tcw capabilities list`, `tcw work list` `` |
| `tcw path` | `` one of `tcw taxonomy path`, `tcw capabilities path`, `tcw work path` `` | unchanged (`tcw project path` is the fourth, and dropped) |
| `tcw new` | `` `tcw work new` `` | `` `tcw work new` or `tcw project new` `` |
| `tcw info` | none | `` `tcw project info` `` |

Any other word that named a removed command somewhere else (`tcw work
provision`, `tcw work config`) now names its `tcw project` form. AC 3 pins
the four rows above.

1.4. **No message or shipped file of the CLI names a removed command.**
Every message of Problem 7 names its replacement (`tcw project new`,
`tcw project provision`, `tcw project list`), as does every help text,
comment shown to a person, and file under `tcw/` that TCW ships
(`tcw/work/procedures/`, `tcw/work/prompts/`), the eval fixture builder and
the capture script. This sweep is repository-wide for `tcw/`, `evals/`,
`scripts/` and `tests/` (the tests that run a removed command are changed to
run its replacement, and the plan lists them). For documentation, skills
and the ledger it is narrowed by Design 1.6: `docs/guide/`, `README.md`,
`skills/` and `docs/use-cases.md` are changed here only as far as naming the
replacement, and rewritten by TCW-117 (Non-goals); the capability and
taxonomy records named in Capability changes are rewritten here, because
this item's records stage changes them; `docs/changelogs/`,
`docs/release-notes/` and finished work items record history and are not
changed. The one exception in shipped code is the table of 1.2.

1.5. **Exit codes do not change.** No new code; Design 5, 6 and 7 use 0, 1,
2, 5 and TCW-108's 7 with their documented meanings
(`EXIT_CODES`, `tcw/cli_help.py:38-49`, as TCW-108 Design 8.3 extends it).

1.6. **The passages that name a removed command.** *Corrected after the plan
review, decided by the dispatching session, 2026-10-22: the suite cannot
pass otherwise, and TCW-114 Design 9.5 settled the same question the same
way.* The suite checks every `tcw …` command that a Markdown file git knows
about writes, outside its list of archives (`tests/test_documented_cli_surface.py:38-53`,
`_check`; and `tests/test_shipped_text.py`, `command_problem`, for
`skills/`, `agents/` and `tcw/work/`). Once 1.2 removes the four commands,
every live document that still writes one fails that check: 43 files at
`d2d02829` (`README.md`, 18 capability descriptions, two taxonomy
descriptions, four guides, `docs/use-cases.md`, 15 files under `skills/`,
`tcw/work/procedures/search.md` and `tests/cli/scenarios/13-release-integrity.md`).
So this item changes each such passage **only as far as naming the
replacement command** (`tcw init` becomes `tcw project new`, and so on, with
the same arguments), and adds nothing else. Two rules keep the check strict
while doing so:

- **One token per placeholder after `-C`.** TCW-114 makes the checks skip
  `-C` and exactly one following word, so any passage this item writes that
  names `tcw -C` writes its target as one token (`tcw -C <folder> project
  provision <id>`); a target written as a phrase (`<its project's root>`)
  would leave the rest of the phrase to be read as a command and fail.
- **The list of changed passages is kept.** Each passage changed this way is
  listed, with what it now says, in the implement round; that list is the
  one TCW-117's handoff names, so TCW-117 knows which prose describes 3.x
  behavior under a 4.0 command name.

Keeping the old commands registered until TCW-117 was weighed and rejected:
the check would then pass only because the documents name a command that
still parses, which is what 1.2 removes.

### 2. `tcw project new`

2.1. `tcw project new [axis …] [--id <id>] [--work-path <path>]
[--taxonomy-path <path>] [--capabilities-path <path>]` is `tcw init`
(`run_init`, `tcw/cli.py:45-83`) under a new name, with its arguments,
outputs, refusals and exit codes unchanged as `v4` leaves them: TCW-106's
`.tcw/` folder and version line and its refusal inside a 3.x project
(TCW-106 Design 1.5, 4.1), and TCW-107's second ignore line (TCW-107 Design
1.9). Run again in a project, it scaffolds the axes it is given, as today.
It writes no manifest.

2.2. Its help reads `make this folder a TCW project, or add the named stores
to it`; the store-with-a-repository refusal (`tcw/store/fs.py:721-729`)
names `tcw project provision` and, for the remaining axes,
`tcw project new <axes>`.

### 3. `tcw project list`

3.1. `tcw project list [--json]` is `tcw projects list` as TCW-108 Design
8.1 and 8.2 leave it, under a new name, with two changes from TCW-108's
JSON:

- each row keeps TCW-107's `found` (TCW-107 Design 6.1): `{"by":
  "manifest", "file": …}`, `{"by": "variable", "name": …}`, `{"by":
  "search"}`, or `null` for the current project and for a project not on
  this machine;
- no row carries `read-only` (TCW-114 Design 1.8 removes it, after TCW-108
  handed it to this item; TCW-114 lands later in the order and decides).

So the document is `{"schema": <n>, "projects": [...], "load-order": [...],
"load-order-complete": <bool>, "load-order-warning": <string or null>}`,
`<n>` being what `print_json` writes for every document (2 after TCW-110),
and each row has `id`, `relation` (`current`, `parent`, `child`), `present`,
`path` and `found`, a parent row `inherit`, and a child row `personal`. The
plain listing stays one ID per line: the active project, its parents in
listing order, its children (TCW-108 Design 8.1).

3.2. A graph problem refuses with exit 1, as today (`require_valid`,
`tcw/projects_cli.py:28`). A project not on this machine is a row with
`present: false`, never a refusal.

3.3. The web app's project answer (`_projects`, `tcw/serve/work.py:143-148`)
served the create form's project selector, which TCW-114 Design 2.3 removes,
and TCW-114 Design 1.8 removes its `readOnly`. If `_projects` survives
TCW-114, it keeps reading the same rows (`connected`), wherever this item's
renaming leaves that function, and only its docstring's command name changes;
if TCW-114 removed it, this rule has nothing to do. The plan checks which.

### 4. `tcw project config`

4.1. `tcw project config [--origin]` is `tcw config show` (`_show`,
`tcw/config_cli.py:251-269`) as TCW-109 Design 7.1 leaves it: the merged
configuration as YAML that reads back as itself, inherited and environment
values included; exit 7 with TCW-109 Design 3.3's message, naming the first
undecided key in the order `work.tags`, then `work.jira`, and nothing
printed; exit 1 with TCW-109 Design 1.6's message, and nothing printed, when
a key is broken and none is undecided. Both hold with or without `--origin`.
A problem in the active project's own layers stops plain `config` with exit
1, and with `--origin` everything that could be merged is still printed, then
exit 1, as today (`tcw/config_cli.py:258-268`).

4.2. **The origin label.** With `--origin`, each value and list entry is
followed by a comment naming the project it came from, its layer, and its
file or variable (TCW-109 Design 2.6), in one shape for every layer:

```
# <project-id>, <layer> <file>         a file layer: project, user or local
# <project-id>, environment <NAME>     a variable (TCW-109 Design 4)
# built-in                             TCW's own default
```

`<file>` is written as `shown_in` writes it today (`tcw/config.py`, used at
`tcw/config_cli.py:134`): relative to the active project's root when inside
it, absolute otherwise. So the active project's shared file, which today is
labelled `project` alone (`tcw/config_cli.py:131-134`), now reads
`# app, project .tcw/tcw-config.yaml`, and an inherited value
`# core, project /…/core/.tcw/tcw-config.yaml`. The user-wide file is applied
at each project's layers (TCW-109 Design 2.1), and a value it sets carries the
project at whose layers it was applied last, which is the active project
(`# app, user /…/tcw-config.yaml`). A borrowed personal file in a
git worktree names the main checkout's file (TCW-107 Design 4.2). The
packaged file a built-in entry stands for still follows, after a comma
(`_packaged`, `:104-110`), and the closing block of values a personal file
set that were not used is unchanged (`_set_aside`, `:209-220`).
Reason: the design asks for "the project and file it came from, as
`git config --show-origin` does" (design.md:623), and TCW-109 leaves the new
group's format to this item (TCW-109 Design 7.1). One shape for every layer
lets a reader, or a script, split each label the same way.

4.3. The same label, without the `# `, is the origin `tcw project info`
prints (Design 6.3), and the JSON form of an origin there is
`{"project": <id>, "layer": <layer>, "file": <absolute path>}`,
`{"project": <id>, "layer": "environment", "variable": <name>}` or
`{"layer": "built-in"}`.

### 5. `tcw project path`

5.1. `tcw project path [<id>]` prints one line on standard output: the
absolute folder of project `<id>` on this machine, the folder holding its
`.tcw/`. With no `<id>`, it prints the active project's root. It writes
nothing.

5.2. It asks `FsProjectRegistry.project_folder(<id>, <active root>)`
(TCW-107 Design 2.12) on the command's one registry, so it answers for any
project TCW can locate from here, in the family or not (a sibling named by an
ancestor's `children:`, a project only a manifest lists), and gives the same
folder every other command in this project would use, after TCW-107's
worktree rule (TCW-107 Design 4.4). Its outcomes:

| Outcome (TCW-107 Design 2.12) | Exit | Standard error |
| --- | --- | --- |
| found | 0 | nothing |
| not on this machine | 5 | TCW-107 Design 6.2's message, which names the repository and `tcw project provision <id>` when the deciding entry gives a repository |
| unknown | 1 | `no project with ID '<id>' is known or found near this one; check the spelling` |
| graph problem | 1 | its message |

5.3. An `<id>` that is not a valid project ID (`validate_project_id`,
`tcw/store/project.py:29-37`) is a usage error (exit 2) naming the rule.
Outside any project the command fails as every project command does
(`NO_PROJECT`, exit 1).

### 6. `tcw project info`

6.1. **What it shows**, all about the active project:

1. its ID and its root folder;
2. its parents, in listing order (`parents()`, TCW-108 Design 3.2), each
   with what it passes down (`inherit`) and whether it is on this machine;
3. its children (`declared_child_ids()`), each with whether only the
   personal file lists it and whether it is on this machine;
4. its load order (`load_order()`), the projects in it that are not on this
   machine (`missing`) or whose links could not be read (`unreadable`), and
   TCW-108 Design 4.5's warning when there is one (design.md:442-443);
5. these settings, each with its origin (Design 4.2): `work.backend`, and in
   Jira mode `work.jira.site` and `work.jira.project`, a value inherited from
   another project being marked so (TCW-109's handoff). A setting no layer
   sets is shown with its default and the origin `built-in`
   (`work.backend` is `filesystem`, `DEFAULT_BACKEND`,
   `tcw/work/config.py:27`);
6. where each of its three stores is: the folder `tcw <axis> path` prints, or
   the reason that command gives when there is none;
7. for taxonomy and capabilities, its own objects that override an inherited
   one, each with the full identifier it overrides, and the count of
   TCW-112 Design 2.5's warnings (two unrelated projects with an object at
   one path), both read from the records of `list --local` and the warnings
   that command prints (TCW-112 Design 3.7). TCW-112 lands first, so this
   item adds them (TCW-112's handoff).

6.2. **It reports; it never stops for what is missing.** A parent, child or
load-order project not on this machine is shown as such. A setting that is
undecided (TCW-109 Design 3.1) is shown with TCW-109 Design 3.3's message in
place of a value, and a broken one (TCW-109 Design 1.6) with that message. A
store that cannot be found, or an axis whose view cannot be built because
inherited content is unavailable (TCW-112 Design 3.4), is shown with the
reason. None of these changes the exit code, which is 0: a person runs
`info` to find out what is missing, so it must not exit 7 for the very thing
it is asked about. What stops it is what stops `tcw project list`: a graph
problem (exit 1), a problem in the active project's own configuration (the
check every command makes first, `tcw/cli.py:655-661`, exit 1), or no project
here.

6.3. **Text.** Standard output, in this order, one fact per line; a list
that is empty is written `none` after its label:

```
id: app
path: /abs/app
parents:
  core (inherit: taxonomy)
  workspace (inherit: none; not on this machine)
children:
  plugin-a
  plugin-b (personal)
load order: core, workspace, app
load order incomplete: not on this machine: workspace
load order warning: <TCW-108 Design 4.5's warning>
settings:
  work.backend: jira (app, project .tcw/tcw-config.yaml)
  work.jira.site: https://example.atlassian.net (core, project /abs/core/.tcw/tcw-config.yaml; inherited)
  work.jira.project: undecided: <TCW-109 Design 3.3's message>
stores:
  taxonomy: /abs/app/docs/taxonomy
  capabilities: /abs/app/docs/capabilities
  work: /abs/app/docs/work
overrides:
  taxonomy: none
  capabilities:
    app.capabilities/cli/export overrides core.capabilities/cli/export
same path in two unrelated projects: taxonomy 0, capabilities 1
```

`inherit` is written `all`, `none`, or the axes it lists in the order
taxonomy, capabilities, config, joined by `, `. The two `load order`
follow-up lines appear only when they apply; the first names the `missing`
projects after `not on this machine: `, then the `unreadable` ones after
`; links unreadable: `, each part only when it has a project. An axis whose
view could not be built reads `<axis>: could not check: <the message>` under
`overrides:`, and its count `?`.

6.4. **`--json`** prints `{"schema": <n>, "project": {...}}` with: `id`,
`path`; `parents`, a list of `{"id", "inherit", "present", "path"}` with
`inherit` as in `tcw project list`; `children`, a list of `{"id",
"personal", "present", "path"}`; `load-order`, `load-order-complete`,
`load-order-missing`, `load-order-unreadable`, `load-order-warning`;
`settings`, a mapping from each key of 6.1 (5) to `{"value", "origin",
"inherited"}` (origin as in Design 4.3; `inherited` true when its project is
not the active one), or `{"undecided": <message>}`, or `{"broken":
<message>}`; `stores`, a mapping from each axis to `{"path": <folder>}` or
`{"unavailable": <message>}`; `overrides`, a mapping from `taxonomy` and
`capabilities` to a list of `{"id", "overrides"}` or `{"unavailable":
<message>}`; `same-path-warnings`, a mapping from the two axes to a count, or
`null` for an axis that could not be checked.

6.5. `info` takes no project argument. To see another project as it sees
itself, run it there (`tcw -C <folder> project info`, the folder from
`tcw project path`), as the design says of every view (design.md:644-647).

### 7. `tcw project provision`

7.1. **Forms.**

```
tcw project provision [--component <axis>]... [--dry-run]
tcw project provision <id> [--dry-run]
```

- **No argument:** the stores of 7.2, then every project of 7.3 (a).
- **`--component <axis>`** (repeatable, `work`, `taxonomy` or
  `capabilities`): only those stores, and no project. This is the scoping
  TCW-23 asked about: a run that names a store contacts no project's remote.
- **`<id>`:** the project `<id>` and its load order, 7.3 (b), and no store.
  `<id>` together with `--component` is a usage error (exit 2), and so is an
  `<id>` that is not a valid project ID. An `<id>` the lookup reports as
  unknown (TCW-107 Design 2.12) refuses with exit 1 and `no project with ID
  '<id>' is known or found near this one; check the spelling, or, if a
  project that is not on this machine yet names it, fetch that project
  first`: a project named only in the files of a project not fetched yet is
  unknown until that project is here.
- **`--dry-run`:** 7.12.

Everything it says goes to standard error; it prints nothing on standard
output (TCW-73 Design 1.7, as `run_provision` today, `tcw/cli.py:97-99`).

7.2. **Stores** are provisioned exactly as `run_provision` does today for
the active project's declared component stores (`tcw/cli.py:137-189`),
including its refusals: a configuration that cannot be read (`:106-112`), a
malformed `repository` declaration (`:145-151`), and a store already here,
which is never fetched into (`:166-180`). Its messages name
`tcw project provision` where they named `tcw provision`. The message for a
store that is declared with a repository and not yet fetched
(`StoreNotProvisioned`, `tcw/store/fs.py:3314-3318`) names the command that
fetches *that* store: `tcw project provision --component <axis>` when the
store is the active project's, and `tcw -C <its project's root> project
provision --component <axis>` when it is another project's. The second case
arises when TCW-112 Design 1.3's third message carries this message into a
project that inherits from that one; there, `tcw project provision` alone
would provision the wrong project's stores (Non-goals).

A store that fails does not stop the run: the projects pass follows, as
3.x's did (`tcw/cli.py:165-191`), and the failure counts in 7.13. A
configuration that cannot be read still refuses before anything
(`:106-112`). The store's clone gets the same protection as a project's
against an address read as an option: `--` before the URL, and `--` after
the `ref` it checks out (`git -C <staging> checkout --quiet <ref> --`),
which makes git fail on a `ref` that names no branch, tag or commit rather
than read it as a file. *Decided by the dispatching session, 2026-10-22,
after the plan review;* the store keeps its separate checkout, unlike a
project (7.9), because a store's `ref` may name a commit, which `git clone
--branch` does not accept.

7.3. **Which projects.** A project is fetched only when the registry records
it as not on this machine (TCW-107 Design 2.12), never because a manifest
gives a repository for it:

- (a) **No argument:** every project of the active project's family that is
  not on this machine: its ancestors (by `parents:`) and its descendants (by
  the `children:` lists the registry follows, the active project's personal
  list included, TCW-108 Design 2.1 and 3.1). After each round the registry
  is read again (7.11), so a fetched parent's parents and a fetched child's
  listed children are fetched in the next round, and so on. Siblings are
  never fetched: the registry's walk never reaches them (TCW-108 Design
  3.1). So a parent's `children:` never causes a fetch from a child, which is
  what 3.x's "an upstream's own connections are not followed" protected
  (`tcw/cli.py:306-311`): a public library cannot make its readers fetch the
  private projects it lists.
- (b) **`<id>`:** the project `<id>`, located from the active project
  (`project_folder(<id>, <active root>)`), and every project of its load
  order (`load_order(<id>)`, TCW-108 Design 4.6) that is not on this machine,
  round by round as in (a), upward only. Its children are not fetched.
  `<id>` may be any project TCW can locate from here, including the active
  project itself, which fetches its missing ancestors only.

**A round** is the set of projects found not on this machine in one reading
of the registry, less any project an earlier round of this run attempted.
The checks of 7.5 to 7.8 are made for the whole round before any remote of
the round is contacted, so a dry run (7.12) and a round with a conflict
(7.7) fail before anything is fetched; then each clone of the round is
attempted, one after another, in the order the registry found the projects
(TCW-107 Design 2.11 (a): parents before children), and **each is checked
again immediately before it writes anything** (7.8, "The folder checked is
the folder written"), because an earlier clone of the same round may have
added a folder or a symbolic link that one of its paths now passes through;
then the registry is read again, once (7.11). The run ends when a round is
empty, or when 7.11 stops it. So each project is attempted at most once in
a run.

7.4. **A project already here is never fetched.** "Already here" is the
lookup's `found`, whatever rule found it: a manifest entry (any manifest in
the walk, an ancestor's included), `TCW_PROJECT_<ID>` naming a folder on
this machine, or the search. So a repository in a manifest is never on its
own a reason to fetch: a project found at its deciding entry's folder, or
placed by `TCW_PROJECT_<ID>`, is never fetched, whatever other manifests say
about it. A variable naming a folder that is not here is skipped by the
lookup (TCW-107 Design 2.1), so the deciding manifest entry decides, and the
project is fetched into that entry's folder, not into the variable's. A
project already here is still read for its own links: the registry's walk
goes through it, so what it names is reached (in 3.x, `tcw/cli.py:335-348`).

**Answers are kept for the whole run.** Reading the registry again after a
round (7.11) forgets its earlier answers (TCW-107 Design 2.13), and a
manifest fetched in the round can change them: TCW-107 Design 2.2 and
TCW-108 Design 3.4 (b) consult an ancestor's manifests before the search, so
a parent `core` fetched into `<tmp>/repos/core`, whose manifest gives
`lib: ../lib` (`<tmp>/repos/lib`, which does not exist), turns `lib`, found
at `<tmp>/lib` next to `app` (`<tmp>/app`) by the search, into "not on this
machine". So the run records, before its first clone, the folder of
every project the registry has found, and adds each project it fetches once
the next reading finds it. After every reading, each recorded project is
looked up again from the project that named it, and when the answer differs
(another folder, or not on this machine), that project is refused as a graph
problem: `<id>: was at <folder> when this run started, but <file>, fetched in
this run, now places it at <other folder>; add an entry for '<id>' to
.tcw/tcw-manifest.local.yaml in <the naming project's root>, which that
lookup reads first, to keep it where it is`. Nothing is fetched for it, the
run makes no further round, and it exits 1. This is TCW-107 Design 2.9's
"one folder per ID in a command", kept across the readings of one run.

A changed answer is normally decided by a manifest fetched in the run, which
the message names. One other way to change an answer is stopped before it
happens: a clone made for a project with a `subfolder` is placed whole at
its repository folder, next to other projects, and TCW-107 Design 2.4's
search reads that folder's own `.tcw/`. When the clone's top folder declares
an ID this run has kept an answer for at another folder, placing it would
give that ID a second folder, so 7.9 refuses the clone before it is moved.
*Corrected after the plan review, decided by the dispatching session,
2026-10-22: the first draft said such a change "cannot arise", and the
review showed this case.* Should an answer still change with no manifest
deciding the new one, the message reads `this run's fetches` in place of
`<file>, fetched in this run,`.

7.5. **What is fetched comes from the deciding manifest entry** (Design 8.1),
whichever project's manifest holds it: the active project's, an ancestor's
or a descendant's (TCW-107 Design 2.2), so a declaration is followed from
anywhere in the walk, as 3.x's `_declared_projects_in_graph` did
(`tcw/cli.py:195-235`). Where that entry may place the clone is 7.8's. A
project not on this machine whose deciding entry gives no `repository`, or
which no manifest lists (it is named only by a `parents:` or `children:`
entry), cannot be fetched: it is reported, as `<id>: not on this machine,
and no manifest entry gives the repository to fetch it from` followed by
TCW-107 Design 6.2's sentence for it, and is not a failure (7.13).

7.6. **The repository folder.** A project is cloned into its deciding entry's
repository folder: the entry's `path`, resolved as TCW-107 Design 2.3 resolves
it (relative to the manifest's project root; in a linked git worktree, a path
leading outside the repository from the main checkout, TCW-107 Design 4.3),
with `subfolder` removed (TCW-107 Design 1.6). Before any remote is
contacted for that project, the repository folder must be absent or empty,
holding no entries at all.

For a trusted entry (7.8) whose repository folder's parent folders do not
all exist, the missing ones are made just before the staging folder (7.9)
is, one folder at a time, and never in a dry run. *Decided by the
dispatching session, 2026-10-22: the staging folder sits in that parent, so
the parent must exist first; and a refusal must leave nothing behind (AC
25).* When the project is then refused or its clone fails, the folders this
run made for it are removed again, deepest first, each only while it is
still empty. A bounded entry never needs this: its repository folder's
parent is the bound, which exists (7.8).

- **A folder holding only `.git`** (a file or a folder) is refused: `<id>:
  <folder> holds only .git (a clone or a submodule update that stopped);
  finish or remove it with git, then run again`. Its remote is not
  contacted, and nothing in the folder is touched. *Decided at the spec
  review on 2026-10-22*: moving or replacing that `.git` would change git
  state, which TCW never does (`docs/lifecycle/abstraction.md:98-103`), and a
  submodule's `.git` file holds a path relative to where it sits
  (`gitdir: ../.git/modules/<name>`), so moving it breaks the submodule's
  link to its superproject. The user's decision recorded in TCW-107 Design
  2.3 covers only the lookup, which counts such a folder as "not on this
  machine" so that a run does not fail on it; it does not make the folder a
  place to clone into.
- **Anything else is occupied**: that project is refused, with `<id>:
  <folder> is not empty; move it aside, or correct the manifest entry in
  <file>`, its remote is not contacted, nothing in the folder is touched,
  and the run goes on with the other projects. With a `subfolder`, the
  entry's own folder may be absent while the repository folder is occupied
  (a clone of something else is there); that is refused the same way.

7.7. **One repository folder, one clone.** Before any remote is contacted,
the projects of a round are grouped by repository folder (compared after
resolving, as 7.8 does). Entries whose repository folder is the same must
name the same repository (compared by `normalized_url`,
`tcw/store/checkouts.py:21-57`) and the same branch; then one clone serves
them all, and the others are found in it at the next reading (7.11), as
3.x's "two entries naming one repository share one working copy"
(`tcw/cli.py:252-254`). Entries that place different repositories, or
different branches of one, at the same folder are all refused, each naming
the folder and the other entries' manifests, and none is fetched. A
repository named by entries with different repository folders is cloned
once into each: each entry says where its project is. When the clone made
for one project holds no project at another's `subfolder`, that other
project is refused with `<id>: the clone of <url> made for '<first>' at
<folder> has no TCW project at <subfolder>`.

7.8. **How far a clone may be placed** (TCW-23). *Decided by the user on
2026-10-22: a manifest that is not the active project's own is always
bounded, on every run.*

- **Trusted manifests** are the active project's own two:
  `.tcw/tcw-manifest.yaml` and `.tcw/tcw-manifest.local.yaml` (in a linked
  worktree, the personal one it borrows from the main checkout, TCW-107
  Design 4.2). An entry in either may place a clone wherever TCW-107 Design
  1.4 lets it, and the clone's missing parent folders are made.
- **Bounded manifests** are every other manifest the lookup reads: an
  ancestor's or a descendant's, committed or personal, whether its project
  was on this machine when the command started or was fetched during it.
  Being on this machine is not being read: a parent cloned last month, or a
  personal manifest committed into a remote by mistake (personal is a
  file's name, not its git status, TCW-107 Design 4.2), was never checked
  by the person either.
- **Which manifest is trusted** is decided by the folder that holds it: an
  entry is trusted when its owner (the project whose `.tcw/` holds the
  deciding manifest, or, for a personal file a linked worktree borrows, the
  worktree, TCW-107 Design 4.2) is the active project itself, compared as
  folders by identity (below), never by how a file's path is written.
- **The bound** of a bounded manifest is the parent folder of its owner's
  repository folder, both resolved (below). The owner's repository folder
  is the folder this run cloned it into, when it was fetched in this run
  (recorded resolved); otherwise the top folder of the git repository
  holding the owner's root (`git rev-parse --show-toplevel`, one of the git
  reads TCW already makes to find a repository's root), or the owner's root
  when it is in no git repository. So a package of a monorepo is bounded by
  the folder holding the monorepo, not by the folder holding the package.
  "In no git repository" means that neither the owner's root nor any folder
  above it holds a `.git` entry (a file or a folder). When one does and git
  cannot say which repository it is (git is missing, or refuses with an
  error such as "dubious ownership" or a broken `.git` file), the bound
  cannot be known, and every bounded entry of that manifest is refused with
  the third message below. *Decided by the dispatching session, 2026-10-22,
  after the plan review:* falling back to the owner's root on such an error
  would silently move the bound inside a monorepo (`mono/packages`), which
  is the case this rule exists for; refusing is the safer option, and
  looking for `.git` does not depend on the words of git's messages.
- **What a bounded entry may name.** Its repository folder (7.6), resolved,
  must be a direct child of the bound, resolved, whose name does not begin
  with `.`. So `../lib`, and `../mono` with `subfolder: apps/x`, are
  allowed; `../x/lib`, `../../lib`, a folder inside the owner's own clone
  (`vendor/lib`) and `../.config` are refused. A direct child of the bound
  cannot be inside any other folder there, so a bounded entry can never
  place a clone inside another project, inside a clone made in this run, or
  inside a hidden folder.
- **An absolute path and a `~` path are refused in a bounded entry**, as
  written, whatever they resolve to. *Corrected after the plan review,
  decided by the dispatching session, 2026-10-22:* the first draft gave this
  as a consequence of the direct-child rule, and it is not one, since an
  absolute path can name a folder directly inside the bound. It is a
  separate check, made before anything is resolved: a manifest that is not
  the active project's own may only describe where a project is relative to
  its own project.
- **Resolved** means with every symbolic link and every `..` followed, as
  `os.path.realpath` follows them, and with the folder that would hold the
  repository folder required to exist: for a bounded entry, the repository
  folder's path as written (the entry's `path` with `subfolder` removed),
  less its last part, must resolve completely to an existing folder
  (`realpath(…, strict=True)`), or the entry is refused with the first
  message. Without that, `realpath` collapses a `..` after a folder that does
  not exist yet by text alone, and `../A/l/../../B` would be judged as
  `<bound>/B` before a clone of `A` commits `l` as a link leading elsewhere.
  So a symbolic link committed in a fetched repository (`up -> ../../..` with
  the entry `up/x`), a `..` after such a link, or a target folder that is
  itself a link, is judged by the folder it really leads to.
- **Folders are compared by identity**, never as text: two paths name the
  same folder when they are the same file on disk (`os.stat`'s device and
  inode numbers, as `os.path.samefile` compares them). "Directly inside the
  bound" means the repository folder's parent is the same folder as the
  bound; "at or above the home folder" means the bound is the same folder as
  the home folder or as one of the folders above it. *Decided by the
  dispatching session, 2026-10-22, after the plan review:* macOS's file
  system ignores letter case and treats two Unicode spellings of one name as
  one, so `/Users/ROBIN` is the home folder `/Users/robin` there while
  comparing text says it is not; comparing whole path components as text (`<tmp>/repos-x` is not
  inside `<tmp>/repos`) stays right, but is not enough.
- **A bound at or above the home folder, or inside a hidden folder below
  it, is refused outright.** When the bound is the person's home folder
  (`Path.home()`, resolved), any folder above it, or the filesystem root, or
  when any folder below the home folder down to the bound, the bound
  included, has a name beginning with `.` (`~/.local`, `~/.config/x`), no
  bounded entry of that manifest may place a clone. Reason: a person who
  keeps repositories directly in their home folder would otherwise let a
  fetched manifest create `~/bin` or `~/.local`-style folders that shells and
  editors read at their next start, and a bound inside `~/.local` would let
  it create `~/.local/bin`, which is often on `PATH`; no rule about names
  makes those folders safe. *The hidden-folder part was decided by the
  dispatching session, 2026-10-22, after the plan review:* it costs nothing
  in the usual layout of projects side by side.
- **The folder checked is the folder written.** *Decided by the dispatching
  session, 2026-10-22, after the plan review, which placed a clone outside
  the bound through a link committed by an earlier clone of the same
  round.* Every check of 7.6 to 7.8 is made once for the whole round (7.3)
  and then again for each project immediately before its clone writes
  anything, on folders resolved again at that moment; the repository folder
  must then resolve to the same folder it resolved to when the round was
  checked, or the project is refused (`<id>: <path> led to <folder> when
  this round was checked, and now leads to <other folder>; nothing was
  fetched for it`). Every later step uses that one resolved folder, never
  the path as written: the parent folders made for a trusted entry (7.6),
  the staging folder (7.9) and the move into place (7.10). The staging
  folder and the move are made relative to the repository folder's parent,
  held open from the moment it is checked, so the folder written into is the
  folder checked even if a path to it changes; folders are made with a call
  that fails on any existing name, a symbolic link included, and never
  follows a link at the name it makes. Just before the move (7.10), the
  entry's path is resolved once more and must still lead to the same
  folder. What this defends against is anything a fetched repository or a
  manifest contains, including links committed by earlier clones of the run;
  another program on this machine changing folders while the run works is
  outside it, since such a program could as easily change the manifests.
- **The refusal** is made before the project's remote is contacted, the run
  goes on with the other projects, and the run exits 1. Its message is one
  of `<id>: <file> places it at <folder>, outside <bound>; a manifest that is
  not this project's own may place a clone only in a folder directly inside
  <bound>`; `<id>: <file> places it at <folder>; '<owner>' sits in <bound>,
  which is the home folder, a folder above it, or inside a hidden folder
  below it, so a manifest that is not this project's own may not place a
  clone there`; or `<id>: <file> places it at <folder>, but git could not
  say which repository holds '<owner>' (<git's reason>), so the folder a
  manifest that is not this project's own may use is not known`; each is
  followed by the way out. The
  way out names a manifest the lookup reads before `<file>` (TCW-107 Design
  2.2 (a): the asking project's own manifests come first, its personal one
  before its committed one; TCW-108 Design 3.4 (b) and (c) put ancestors and
  then descendants after them):
  - when the project that names `<id>` (the asking project, TCW-107 Design
    2) is the active project: `add an entry for '<id>' to
    .tcw/tcw-manifest.local.yaml (this machine) or .tcw/tcw-manifest.yaml
    (everyone) in this project; they are read first`;
  - otherwise: `read <file>; to fetch it as written, run 'tcw -C <asking
    project's root> project provision <id>', where that manifest is the
    active project's own` (only when `<file>` is the asking project's own
    manifest), and always `to place it elsewhere, add an entry for '<id>' to
    <asking project's root>/.tcw/tcw-manifest.local.yaml, which is read
    before <file>, and run 'tcw -C <asking project's root> project provision
    <id>'`. The entry the person adds is a manifest of a project other than
    the one active in later runs, so it is itself bounded when those runs
    place a clone; by then the clone is made, and the lookup only finds it.

  The active project's own personal manifest is not the way out for a
  project another project names: for that lookup it is read last, as a
  descendant's (TCW-108 Design 3.4 (c)), so the bounded entry would still
  decide.

Reason: an entry such as `../../../.config/x` in a manifest the person never
read would otherwise plant a clone anywhere the person can write. The usual
layout, projects cloned side by side, is inside the bound. The active
project's own files are trusted because the person runs the command in that
project, and every other command there already follows them.

7.9. **Making the clone.** For each project of a round, in turn:

- a `repository` whose URL or branch begins with `-` is refused before
  anything is run (`<id>: <file> gives a repository beginning with '-'`),
  since git would read it as an option; and git is always given `--` before
  the URL (`git clone --quiet -- <url> <folder>`);
- the remote is printed before it is contacted, as `→ <id>: <url>[ at
  <branch>] → <repository folder>` (as 3.x does, `tcw/cli.py:355`, and as
  the stores pass does, `:182`);
- the repository is cloned into a staging folder, with a branch as the
  branch to check out (`git clone --quiet --branch <branch> -- <url>
  <folder>`, one call; a branch the remote does not have fails the clone,
  and git leaves nothing). *Decided by the dispatching session, 2026-10-22,
  after the plan review:* a separate `git checkout <branch>` after the clone
  reads a branch name that matches a file in the repository as that file,
  exits 0 and stays on the default branch, so a mistyped branch would
  silently fetch the wrong one. Git runs with its standard input closed and
  with no way to prompt (`_git` and `_no_prompt_env`, `tcw/store/fs.py:147`,
  `:164`), so a remote that asks for credentials fails instead of waiting.
  The staging folder is `<parent>/.tcw-staging-<8 random hex digits>/<folder
  name>`, `<parent>` being the repository folder's parent; the hidden folder
  is made with an exclusive `mkdir`, so an existing name is never reused or
  written into, and when five random names in a row are taken the project
  is refused with `<id>: could not make a staging folder in <parent>: five
  names in a row were already taken`. Reason: today's staging name
  (`.<name>.tcw-<hex>`, `_obtain`, `tcw/store/fs.py:3488`) puts the clone's
  `.tcw/` directly in a folder next to the projects, where TCW-107 Design
  2.4's search would match a copy left by a run that was killed; one level
  deeper, the search never reads it (TCW-107 Design 2.6);
- the staging copy must hold, at `subfolder` (or its top), a
  `.tcw/tcw-config.yaml` that `version_problem` accepts (TCW-106 Design 3)
  and that declares `id: <id>`. Otherwise the project is refused and the
  staging folder removed, so nothing is left behind (as `_obtain` does,
  `tcw/store/fs.py:3477-3497`), with one of: `<url> has no TCW project at
  '<subfolder or .>'`, `<url> holds project '<other>' at '<subfolder or .>',
  not '<id>'`, TCW-106's message for a 3.x project (`legacy_message`), or
  `version_problem`'s message. These checks are new code: the project branch
  of `FsStoreProvisioner` that 3.x provisioning used checks only that the
  file exists (`_is_store_layout`, `tcw/store/fs.py:3150-3153`);
- with a `subfolder`, that folder in the staging copy, resolved, must lie
  inside the staging copy (compared by identity, 7.8): a committed symbolic
  link at the `subfolder` leading out of the clone is refused with `<url>
  has a link at '<subfolder>' that leads outside the clone`, so the check
  above never reads a project somewhere else on this machine. *Decided by
  the dispatching session, 2026-10-22, after the plan review;* it applies to
  trusted and bounded entries alike, since the link comes from the remote,
  not from the person's manifest;
- with a `subfolder`, when the staging copy's top folder holds a
  `.tcw/tcw-config.yaml` declaring an ID that this run has kept an answer
  for at another folder (7.4), and that is not a project this clone is made
  for (7.7), the project is refused with `<id>: the clone of <url> holds
  project '<x>' at its top, but '<x>' is already at <folder>; placing the
  clone at <repository folder> would give '<x>' a second folder`. A
  monorepo whose top folder is a project of its own, with an ID nothing else
  has, is placed as usual;
- only then is it moved into place (7.10).

When the staging folder cannot be removed afterwards, the run prints a
warning naming it (`could not remove the staging folder <folder>: <the
system's reason>; remove it by hand`), and the project's own outcome, a
success or the refusal that caused the cleanup, is reported unchanged. The
search never reads that folder (above), so without the warning the person
would never learn it is there.

Nothing is written into a fetched project beyond the clone itself: no
configuration, manifest or record of it is changed, and nothing about the
active project is written into it (UC-7).

7.10. **Moving into place.** The staging copy is renamed to the repository
folder: an absent one becomes the clone, and an empty one is replaced by it
(a rename onto an empty folder). Just before, the entry's path is resolved
again and must lead to the same folder (7.8, "The folder checked is the
folder written"), and the folder is checked again without following a link
at its own name: anything that appeared in it since 7.6, or a symbolic link
in its place, refuses the project as occupied. The rename is made within the
parent folder held open since the check (7.8).
When the rename fails (the folder is a mount point, or the operating system
refuses), the project is refused with `<id>: could not move the clone into
<folder>: <the system's reason>`, the staging folder is removed, and the
folder is left as it was. The empty staging parent is removed in every case,
and so are any parent folders made for this project when it is refused
(7.6).

7.11. **After each round.** The shared registry is dropped
(`forget_registries()`, TCW-107 Design 2.13): a clone is not written through
`_atomic_write_all`, so without this the rest of the command would not see the
new projects. The registry is opened again, once per round, and then:

- each project fetched in the round must be found by the lookup at its
  entry's folder;
- the answers kept since the run began are compared (7.4), and a change
  stops the run as 7.4 says;
- a problem in a fetched project's manifests or links that the registry
  records as a graph problem (TCW-107 Design 1.8 and 2.2: a manifest the
  lookup consults that cannot be read; TCW-108 Design 6.6 forgives only a
  malformed `parents:`) fails the run (exit 1), and the run makes no further
  round, since the registry cannot be read past it. The clone stays: it is
  the project the entry names, and the problem is in that project's own
  files. The message says what follows and how to undo it: `<id>: fetched
  into <folder>, but <file> has a problem: <its message>. Until it is
  corrected, commands in '<active>' that read the project graph refuse;
  remove <folder> to undo the fetch, or add an entry for '<id>' to
  .tcw/tcw-manifest.local.yaml pointing elsewhere`;
- a problem the registry records as making that project's links unreadable
  (TCW-108 Design 6.6) is printed as a warning; nothing above it can be
  followed, and the run goes on.

7.12. **`--dry-run`** contacts no remote, writes nothing, and prints the
plan for the first round: for each project 7.3 would fetch now, its `→` line
(7.9) and `<id>: would fetch into <repository folder>`, followed by `<id>:
any projects it names cannot be listed until it is fetched`; for a project
another planned clone would bring with it (7.7), `<id>: would come with the
clone for '<first>'`. It applies 7.5 to 7.9's checks made before contact, as
a real run does, the bound of 7.8 included, so a project that cannot be
fetched is reported, and an occupied or `.git`-only folder, conflicting
entries and a target outside the bound fail the dry run with exit 1, exactly
as they would fail the run. It never says "would fetch" for a project already
here (7.4), and lists nothing beyond the first round, since the manifests
that would name it are not on this machine yet (as 3.x,
`tcw/cli.py:363-369`).

7.13. **Output and exit codes.** A project already here is named only when
it is `<id>` (`<id>: already on this machine at <folder>`). When nothing was
missing the run ends with `nothing to fetch: every project it names is on
this machine`. Each fetched project gets `<id>: fetched into <folder>`. When
anything failed, the last line is `fetched <n>, failed <m>; what was fetched
stays, and running the command again fetches the rest`, so a run that stopped
partway says what was done and how to finish (S-8). `<n>` and `<m>` count
stores and projects together: each store or project fetched, and each that
failed. Exit codes:

| Exit | When |
| --- | --- |
| 0 | nothing failed; projects that cannot be fetched for want of a repository (7.5) do not count as failures, except as below |
| 1 | a store or project failed: a clone failed, a folder was occupied or held only `.git` (7.6), entries conflicted (7.7), a target was outside the bound, the bound was at or above the home folder or inside a hidden folder below it, git could not say which repository holds a manifest's owner, or a path led somewhere else when checked again (7.8), a repository began with `-`, a clone held no matching project, its `subfolder` led outside it, its top folder would give a kept project a second folder, or no staging folder could be made (7.9), the move into place failed (7.10), a kept answer changed (7.4) or a fetched project has a graph problem (7.11); also a graph problem before anything is fetched (7.14), and `<id>` unknown (7.1) |
| 2 | a usage error (7.1) |
| 5 | `<id>` itself is still not on this machine at the end because no manifest entry gives its repository, and nothing failed |

7.14. **Before anything is fetched**, the registry must be valid
(`require_valid`): a graph problem (a manifest that cannot be read, two
folders for one ID, a `TCW_PROJECT_<ID>` naming a folder that is not a
project, TCW-107 Design 2.12's graph-problem row) refuses with exit 1, naming
the file and the key, and contacts nothing. That covers 3.x's "a malformed
declaration refuses and names the line" (`tcw/cli.py:153-159`) and its
refusal of a wrong override (`:114-135`). A project that is merely not on
this machine is not a graph problem, which is why the command can run at all
(TCW-108 Design 6.1).

### 8. What this item needs from the items before it

8.1. **The deciding entry of a project that is not on this machine**: one
deployment-layer method on `FsProjectRegistry`, returning for a project ID and
the root of the project that names it:

- `asked_by`: the root of the project whose lookup decided (7.8's way out
  names it);
- the folder found, or none;
- the deciding manifest entry, or none: its file, `path` as written and
  resolved to a folder, `repository` URL, branch and `subfolder`;
- `owner`: the root of the project whose `.tcw/` holds that manifest, or,
  for a personal file a linked worktree borrows (TCW-107 Design 4.2), the
  worktree's root, since that is the project that reads it (7.8's trust and
  bound);
- `repository_folder`: the entry's resolved folder with `subfolder` removed
  (7.6).

*Corrected after the plan review, decided by the dispatching session,
2026-10-22:* the first draft named only the entry's fields, while 7.8 needs
the owner and the asking project. TCW-107's registry already keeps this in
each answer (its plan, Step 3, `_Answer`'s "deciding manifest entry"); this
item makes it readable. It is not on `ProjectRegistry`
(`tcw/store/base.py:184`): a store that is not a folder of files has no
manifest.

8.2. Used as their items define them: `project_folder`, `found`,
`forget_registries` (TCW-107 Design 2.12, 6.1, 2.13); `parents`,
`declared_child_ids`, `load_order` and the personal flag of a child
(TCW-108 Design 3.2, 8.2); configuration origins and the undecided and broken
states (TCW-109 Design 2.6, 3.1, 1.6); `overrides` and the same-path warnings
(TCW-112 Design 3.3, 2.5); `tcw -C` (TCW-114 Design 4). The plan checks each
against what landed and corrects this spec where one differs.

## Abstraction litmus test

| Operation | Layer | Verdict |
| --- | --- | --- |
| The `tcw project` group and the removed-command table (Design 1) | CLI | No operation: names for existing ones. |
| `tcw project new` (Design 2) | deployment | Makes a `.tcw/` folder and store folders on disk, as `tcw init` does; another store would create its project its own way. |
| `tcw project list` (Design 3) | model, shown by the CLI | Reads parents, children and the load order, which any store answers (TCW-108's verdict); `path` and `found` are the files store's report of where each is. |
| `tcw project config` (Design 4) | model, shown by the CLI | Passes: any store can hold a project's configuration and say where each value came from; a file path in an origin is how the files store names its source, as a database would name a row. |
| `tcw project path` (Design 5) | deployment | Prints a folder, which only the files store has; it asks TCW-107's deployment-layer lookup. |
| `tcw project info` (Design 6) | model, shown by the CLI | Reads only operations other items have already judged (TCW-108, TCW-109, TCW-112); `path` and `stores` are the files store's folders. |
| `tcw project provision` (Design 7) | deployment | Clones git repositories into folders; a store that is not a folder of files does not implement it and is not required to (design.md:125-131). TCW makes new clones and changes no existing repository: a folder holding only a `.git` is refused rather than moved (7.6), since `docs/lifecycle/abstraction.md:98-103` says TCW never changes git state. Its one git read beyond cloning, the repository's top folder for the bound (7.8), is of the kind that file allows ("finding the repository's root") in the code that resolves projects, and is made only when a `.git` entry shows there is a repository to ask about; the clone code stays inside the files store (`tcw/store/fs.py`, beside `FsStoreProvisioner`). |
| The deciding-entry method (Design 8.1) | deployment | On `FsProjectRegistry` alone. |

No backend operation is added or changed: the twelve operations in
`tcw/work/backend.py` are untouched, and the Jira backend behaves the same.
`ProjectRegistry` (`tcw/store/base.py:184`) keeps the interface the items
before this one give it, less `reached_by_both_sides` (TCW-114's rename of
`read_only_reason`, kept by TCW-114 for 3.x provisioning alone) when no
caller is left once this item replaces that provisioning; removing a method
no code calls changes no store's behavior.

## Use cases

- **UC-1 (a single project).** No manifest, no parents: `tcw project new`,
  `list` and `config` behave as `tcw init`, `tcw projects list` and
  `tcw config show` did, apart from the origin label's shape (Design 4.2);
  `tcw project provision` has nothing to fetch and says so; `info` shows no
  parents, no children and a load order of the project alone (AC 34).
- **UC-2 and UC-7 (a library others read; a public one read by private
  projects).** A reader fetches the library, a parent, with
  `tcw project provision`, from its manifest entry's public URL with no
  credentials and no prompt (Design 7.9); nothing is written into the library
  (7.9); the library's `children:` are never followed from a reader (7.3 a),
  so a public library cannot make a reader fetch a private project; the
  library's manifest, never the reader's own, can place a clone only directly
  beside the library's clone, and nowhere at or above the home folder (7.8).
- **UC-3 (a monorepo).** Packages inside one repository are found by the root's
  manifest and never fetched. A package's parent outside the repository is
  fetched into its entry's folder; two packages of another monorepo named by
  entries with one repository folder share one clone (7.7, AC 23).
- **UC-4 (a planning workspace).** Run in the workspace, `tcw project
  provision` fetches every listed code project into its manifest entry's
  folder (7.3 a), which is how the planner gets each code project checked out
  (design.md:592-593). `tcw project path <id>` gives the folder to run a
  change in (TCW-114 Design 1.6 refuses it from the workspace and names the
  folder). Test fixtures use separate git repositories as remotes (checklist
  10).
- **UC-5 (a shared Jira project).** `info` shows `work.jira.project` and
  whether it is inherited (Design 6.1); `config --origin` shows which project
  set it. Nothing here contacts Jira.
- **UC-6 (a project not on this machine).** The command every message names
  exists: `tcw project provision <id>` (7.1). `tcw project path <id>` exits 5
  for it (5.2), `info` shows it as missing and exits 0 (6.2), and an ID that
  nothing names is reported as a probable misspelling (5.2, 7.1).
- **UC-8 (several families on one machine).** A project already here,
  wherever the lookup found it, is never cloned again, and a manifest fetched
  during the run cannot move it to another folder (7.4); a folder holding
  something else is never cloned into (7.6); `found` in `tcw project list
  --json` shows how a project was found, including `TCW_PROJECT_<ID>` (Design
  3.1), and `tcw project path` gives its folder (5.1), which narrows UC-8's
  known gap further.
- **S-4 (worktrees, clones, CI).** A fresh clone in CI fetches its parents
  with `tcw project provision` (with `TCW_NO_PERSONAL_CONFIG=1`, the
  committed manifest decides where). In a linked worktree a relative entry
  leading outside the repository is cloned next to the main checkout, where
  the lookup then finds it (7.6, TCW-107 Design 4.3) (AC 29).
- **S-5 (personal configuration).** A project's personal manifest is read
  before its committed one, for the lookups that project asks (TCW-107
  Design 2.2 (a)). So the active project's personal manifest decides where a
  project the active project names is cloned, and its absolute or `~` paths
  are trusted (7.8). For a project that another project names, the personal
  manifest that decides is that other project's, which is bounded unless the
  command runs there (`tcw -C <its root> project provision <id>`), and the
  refusal names it (7.8).
- **S-6 (unattended runs).** Nothing asks: git cannot prompt (7.9), and
  every outcome has an exit code (7.13).
- **S-8 (partial failure).** Each clone is made in a staging folder beside its
  folder and moved in only when complete (7.9, 7.10); a staging copy left by a
  killed run is never taken for a project (7.9); a run that stops partway names what it fetched and
  how to finish, and running it again fetches the rest without fetching
  anything twice (7.4, 7.13) (AC 26).
- **S-9 (upgrades).** A fetched repository holding a 3.x project, or one
  whose version this TCW cannot read, is refused and removed (7.9). Removed
  commands give a usage error naming their replacement (1.2).
- **S-10 (things TCW does not own).** Provisioning reads only the folders the
  lookup reads, and clones only into folders a manifest names.
- **S-11 (version control).** TCW makes new clones and changes no existing
  repository; a folder holding only a `.git` is refused and left untouched,
  with the advice to finish or remove it with git (7.6). It never commits,
  pulls or pushes.

Checklist: 1 (where it looks) Design 5 and 7 through TCW-107's lookup, with
monorepo, workspace and missing-project fixtures; 2 (whose things) only
clones are written, into folders a manifest names, and nothing into any
existing project (7.9); 3 (reading across projects) `info` and `list` read
the family through the registry, and provisioning follows only the family's
links (7.3); 4 (backends) the litmus table; 5 (who is present) nothing asks a
person; 6 (harness) the CLI carries everything, and the removed-command table
points every harness the same way; 7 (stopping halfway) S-8 above; 8 (single
project) UC-1 above; 9 (older and newer TCW) S-9 above; 10 (testing the setup
claimed) the criteria build real git repositories as remotes, a monorepo, a
workspace with separate repositories, and a real linked worktree.

## Acceptance criteria

Every fixture project is a TCW 4.0 project, connected by `parents:`,
`children:` and manifest entries as TCW-107 and TCW-108 define them. A
**remote** is a git repository the test makes in its own temporary folder,
committed, and named in a manifest entry's `repository` by its path; no
criterion contacts a network address. Commands run through `tcw.cli.main` or
the `tcw` script from the named project's root. "Exits n" includes that
nothing else is printed on standard output unless the criterion says what is.
**The stand-in `git`** is a script put first on `PATH` that records each call,
fails the test when called with `clone`, `fetch`, `ls-remote` or `pull`, and
otherwise runs the real git. It cannot fail on every call, because the
registry itself runs `git rev-parse` and `git config` to find the active
project and its worktree (`tcw/store/project.py:135-157`). "Contacts no
remote" means the stand-in saw none of those four; "counts `clone` calls"
means it lets `clone` through to the real git and counts it.
**`<tmp>`** is the test's temporary folder; it lies below the home folder
only when a criterion says so. Every provisioning test sets `HOME` for the
run: to a folder outside `<tmp>` unless the criterion names another, so a
developer whose temporary folder happens to be below their own home folder
gets the same results as CI.

1. **The group.** `tcw --help` lists `project` and does not list `init`,
   `projects`, `config` or `provision`. `tcw project --help` lists `new`,
   `list`, `config`, `provision`, `path` and `info`, and each verb's `--help`
   has a `Prints:` line, a `Writes:` line and an example (the existing walk
   in `tests/test_cli_help_standard.py` covers the new verbs). `tcw project`
   alone exits 2.
2. **Removed commands.** `tcw init --id x`, `tcw projects list`,
   `tcw config show --origin` and `tcw provision --dry-run` each exit 2, write
   nothing, and print on standard error a line containing, respectively,
   `` `tcw init` is now `tcw project new` ``,
   `` `tcw projects list` is now `tcw project list` ``,
   `` `tcw config show` is now `tcw project config` `` and
   `` `tcw provision` is now `tcw project provision` ``.
3. **Synonyms first, and the suggestions that change.** `tcw work info x`
   exits 2 and its added line is
   `` did you mean `tcw work show` or `tcw project info`? ``. `tcw info`,
   `tcw list`, `tcw path` and `tcw new` each exit 2 and suggest exactly what
   Design 1.3's table gives after this item. Every other case of the
   existing suggestion tests (`tests/test_command_suggestions.py`,
   `tests/work/test_cli_surface.py`) passes, unchanged except where it named
   a removed command (each such change listed by the plan).
4. **The sweep.** Over `tcw/`, `evals/`, `scripts/` and `tests/fixtures/`, no
   file contains `tcw init`, `tcw projects`, `tcw config show` or
   `tcw provision` as whole words (so `tcw initial…` does not count) except
   the table of Design 1.2 (checked by a test in
   `tests/test_shipped_text.py` that searches those folders, excluding
   `tcw/serve/dist/`). That search cannot see a command written as an
   argument list (`_run(dest, "init", …)`, `evals/seed_fixture.py:761`;
   `tests/fixtures/prompt_fallback/capture.py:67`), so those two files are
   changed by hand and AC 33's and the eval builder's own runs exercise
   them. Each message of Problem 7 is produced by a test and
   names its replacement: `NO_PROJECT` from `tcw work list` outside a project
   names `tcw project new --id <id>`; `tcw taxonomy list` in a project with no
   taxonomy store names `tcw project new taxonomy`; the init refusal for a
   store with a repository names `tcw project provision`.
5. **`new`.** In an empty folder inside a git repository, `tcw project new
   --id demo` exits 0 and writes exactly what TCW-106 AC 1 and TCW-107 AC 20
   say `tcw init --id demo` writes; `tcw project new work --work-path
   ../board` behaves as `tcw init work --work-path ../board`; run again with
   `taxonomy`, it scaffolds the taxonomy store. Inside a 3.x project it is
   refused as TCW-106 Design 4.1 refuses `tcw init`. It writes no manifest.
   The existing `tcw init` tests, run with `project new`, pass.
6. **`list`.** `app` has `parents: [{id: core, inherit: [taxonomy]}]` and
   `children: [k]`; `core` is next to `app` and in no manifest; `k` is at
   `<tmp>/x/k`, names `app` among its parents, and is listed in `app`'s
   manifest as `k: ../x/k`. `tcw project list` prints
   `app`, `core`, `k`, one per line; `--json` prints the document of Design
   3.1, with `core`'s row `inherit: ["taxonomy"]` and `found: {"by":
   "search"}`, `k`'s row `personal: false` and `found: {"by": "manifest",
   "file": <app's manifest>}`, the current row `found: null`, and no row
   holding a `read-only` key. With `k`'s folder absent, `k`'s row has
   `present: false`, `path: null`, `found: null`, and the command exits 0.
7. **`config`.** In a project `app` with `parents: [core]` (passing
   everything), `app` in Jira mode, `core` setting `work.jira.site`, and,
   with personal files turned on for the test, `app`'s own
   `.tcw/tcw-config.local.yaml` setting `work.procedures.search` and the
   variable `TCW_USER_NAME__APP=Robin` set: `tcw project config --origin`
   exits 0; the line for `work.jira.site` ends with
   `# core, project <core's absolute .tcw/tcw-config.yaml>`, the line for
   `id` with `# app, project .tcw/tcw-config.yaml`, the `work.procedures.search`
   entries with `# app, local .tcw/tcw-config.local.yaml`, the line for
   `user.name` with `# app, environment TCW_USER_NAME__APP`, and a built-in
   stage prompt entry with `# built-in, tcw/work/prompts/<stage>.md`. With
   the variable unset and the user-wide file the test points TCW at setting
   `user.name`, that line ends with `# app, user <that file's absolute
   path>`.
   Without `--origin`, the output reads back with `yaml.safe_load` as the
   same values as with it.
8. **`config` with something missing.** With `core` absent and `app` in
   Jira mode inheriting `config` from it, `tcw project config` and
   `tcw project config --origin` each exit 7, print nothing on standard
   output, and name `work.jira` and `core`. With `core` present and its
   `work.tags` holding a value TCW-109 Design 1.6 finds wrong (an entry that
   is not a valid tag name), and `app` setting no `work.tags`: each form
   exits 1, prints nothing on standard output, and names `core`'s file. With
   `app` setting `work.tags` itself, the key is not broken, and `config`
   exits 0. A problem in `app`'s own file stops plain `config` with exit 1,
   while `--origin` prints what it merged and exits 1.
9. **`path`, found.** From `app` in AC 6: `tcw project path core` prints
   `core`'s absolute root and exits 0; `tcw project path k` prints `k`'s;
   `tcw project path` and `tcw project path app` print `app`'s root. Run
   from `app/docs` (a subfolder), the answers are the same. **A sibling:**
   `ws` at `<tmp>/ws` lists `children: [app2, b]`, both name `ws` among their
   parents, and `ws`'s manifest lists `app2: app2` and `b: b`; run in
   `<tmp>/ws/app2`, `tcw project path b` prints `<tmp>/ws/b`, although `b` is
   not in `app2`'s family.
10. **`path`, not found.** With `k`'s entry giving `repository:
    <remote>#main` and `k`'s folder absent, `tcw project path k` exits 5 and
    its message contains `tcw project provision k` and the remote. With no
    repository in the entry, it exits 5 and does not contain
    `tcw project provision`. `tcw project path nope` exits 1 with `check the
    spelling`. `tcw project path Nope` exits 2. With two folders next to
    `app` declaring `id: lib` and nothing listing `lib`, `tcw project path
    lib` exits 1 naming both folders.
11. **`path` in a worktree.** In a linked git worktree of a repository whose
    top folder is `app`, `tcw project path` prints the worktree's folder,
    and `tcw project path lib` for `lib` next to the main checkout prints
    that folder (TCW-107 Design 4.3, 4.4).
12. **`info`, text.** For `app` of AC 6, with `ws` added as a second parent
    `{id: ws, inherit: none}` and absent, a personal child `p` listed in
    `app`'s `.tcw/tcw-config.local.yaml` (personal files turned on for the
    test), and `app` in filesystem mode: `tcw project info` exits 0 and its
    standard output holds, in this order, the lines `id: app`, `path:
    <app's root>`, `parents:`, `  core (inherit: taxonomy)`, `  ws (inherit:
    none; not on this machine)`, `children:`, `  k`, `  p (personal; not on
    this machine)`, `load order: core, ws, app`, `load order incomplete: not
    on this machine: ws`, `settings:`, `  work.backend: filesystem
    (built-in)`, `stores:`, three store lines, `overrides:`, and the
    same-path line. No `work.jira` line is printed outside Jira mode.
13. **`info`, settings.** `app` has `parents: [core]` (passing everything),
    `work.backend: jira` in its own file, and no `work.jira`; `core`, present,
    sets `work.jira.site` and `work.jira.project`. Then `info` prints
    `  work.backend: jira (app, project .tcw/tcw-config.yaml)` and lines for
    `work.jira.site` and `work.jira.project` ending `(core, project <core's
    file>; inherited)`. With `app` setting `work.jira.project` itself, that
    line ends `(app, project .tcw/tcw-config.yaml)` without `; inherited`.
    With `core` absent, `info` exits 0 and both `work.jira` lines read
    `undecided: ` followed by TCW-109 Design 3.3's message.
14. **`info`, load-order warning.** In TCW-108 Design 4.4's first shape
    (`zz: [xx, yy]`, `xx: [aa, bb]`, `yy: [bb, aa]`), `tcw project info` in
    `zz` prints `load order: aa, bb, xx, yy, zz` and a `load order warning: `
    line holding TCW-108 Design 4.5's warning, and exits 0. Without it, no
    warning line.
15. **`info`, overrides.** With `app` inheriting `core`'s capabilities and
    holding `app.capabilities/cli/x` at `core`'s path `cli/x`, `info` lists
    `app.capabilities/cli/x overrides core.capabilities/cli/x` under
    `capabilities:` and `taxonomy: none`; with two unrelated parents each
    holding a term at `term/a`, the same-path line counts `taxonomy 1`. With
    `core` absent, the capabilities entry reads `capabilities: could not
    check: ` followed by the `InheritedUnavailable` message, its count is
    `?`, and the command exits 0.
16. **`info`, stores.** In a project whose `work.repository` names a remote
    not yet provisioned, the `work:` store line reads the reason
    `tcw work path` gives (naming `tcw project provision`), and the command
    exits 0.
17. **`info --json`.** For AC 12's and AC 13's projects, `--json` prints the
    document of Design 6.4: `parents` holding `{"id": "ws", "inherit": [],
    "present": false, "path": null}`, `children` holding `{"id": "p",
    "personal": true, "present": false, "path": null}`,
    `load-order-missing: ["ws"]`, `load-order-complete: false`,
    `settings["work.jira.site"]` with `inherited: true` and `origin
    {"project": "core", "layer": "project", "file": <absolute>}`, and, with
    `core` absent, `settings["work.jira.project"]` holding only `undecided`.
18. **`info` refuses only what `list` refuses.** A graph problem (two
    folders declaring a parent's ID) makes `tcw project info` exit 1 with
    its message, as `tcw project list` does; a problem in `app`'s own
    configuration exits 1. `tcw project info core` is a usage error (exit 2):
    `info` takes no project.
19. **Provision a parent.** Machine holds only `app`, a git repository whose
    `parents: [core]` and whose manifest has `core: {path: ../core,
    repository: <remote>#main}`; the remote holds `core` at its top on
    branch `main`. `tcw project provision` exits 0, prints the `→ core:` line
    naming the remote before `core: fetched into <tmp>/core`, and afterwards
    `tcw project list --json` in `app` shows `core` with `present: true` and
    `found.file` `app`'s manifest. A second run exits 0, contacts no remote
    (the stand-in `git`), and prints `nothing to fetch`. In the first run
    the stand-in saw `clone --quiet --branch main -- <remote> …` (`--`
    before the URL) and no `checkout`;
    after either run, `<tmp>` holds no `.tcw-staging-…` folder. Nothing in the remote, nor any file of the fetched
    `core` other than the clone itself, has changed (its working tree is
    clean and its `.tcw/tcw-config.yaml` is the remote's).
20. **In turn, and never a sibling.** `core`'s committed config names
    `parents: [base]` and its manifest gives `base: {path: ../base,
    repository: <remote-base>}`, and `core`'s `children:` lists `other` with
    a manifest entry and a repository. From AC 19's `app`, one
    `tcw project provision` fetches `core`, then `base`, and never contacts
    `other`'s remote. A child `k` of `app`, absent with a repository, whose
    own remote lists child `kk` with a repository at `../kk`, is fetched and
    `kk` after it, in the next round.
21. **Scoped to one project.** With `core` and `k` both absent and fetchable,
    `tcw project provision core` fetches `core` and `base` and not `k`, and
    `tcw project provision k` fetches `k` and not `kk` (children are not
    followed for `<id>`). `tcw project provision app` fetches `app`'s
    missing ancestors only. With a store declaring a repository,
    `tcw project provision core` does not touch it, and
    `tcw project provision --component work` fetches the store and no
    project. `tcw project provision core --component work` exits 2.
22. **Already here, by every rule.** In each of these cases
    `tcw project provision` and its `--dry-run` exit 0, contact no remote
    (the stand-in `git`) and print no `would fetch` and no
    `fetched` line for `core`: (a) `core` is at `app`'s own manifest entry's
    folder, with no repository, while the manifest of `app`'s other parent
    `ws` gives `core` a repository and another path (entries never merge,
    and `app`'s decides); (b) `app`'s entry gives `core` a repository and an
    absent folder, and `TCW_PROJECT_CORE` names a copy of `core` elsewhere;
    (c) `core` has no manifest entry anywhere and is found next to `app` by
    the search. With `TCW_PROJECT_CORE` naming a folder that does not exist,
    `core` is fetched into `app`'s manifest entry's folder and nothing is
    made at the variable's folder. In (a), with `core`'s own committed
    `parents: [base]` and an entry giving `base` a repository at `../base`,
    `base` is fetched: a project already here is still read for its links.
23. **One clone for one repository folder.** One remote holds `apps/server`
    (`id: server`) and `apps/client` (`id: client`); `app` names both as
    parents, and its manifest gives `server: {path: ../mono/apps/server,
    repository: <remote>, subfolder: apps/server}` and `client` likewise.
    `tcw project provision` contacts the remote once (the stand-in `git`
    counts `clone` calls), makes `<tmp>/mono`, and both are then found.
    With `client`'s entry naming a different remote at the same repository
    folder, both are refused before any `clone`, each message naming the
    folder, and the run exits 1. With the remote lacking `apps/client`,
    `server` is fetched and `client` is refused with `has no TCW project at
    apps/client`, exit 1.
24. **Occupied, empty and `.git`-only folders.** In AC 19, with `<tmp>/core`
    holding a file `f`: exit 1, no `clone` call, `f` unchanged, and the
    message names the folder and `app`'s manifest. With `<tmp>/core` empty:
    fetched into it, exit 0. With `<tmp>/core` holding only a `.git` file
    (`gitdir: ../.git/modules/core`), and again only a `.git` folder holding
    a file `HEAD`: exit 1, no `clone` call, the message is Design 7.6's
    (`holds only .git`, `finish or remove it with git`), the folder and its
    `.git` are byte for byte as they were, and nothing new is in `<tmp>`.
    With a `.DS_Store` file beside the `.git`: refused as occupied.
25. **What a clone must hold.** In AC 19, each of these remotes is refused
    with exit 1, its message, and no folder left at `<tmp>/core` or any
    staging folder beside it: one with no `.tcw/` (`has no TCW project at
    '.'`); one declaring `id: other` (`holds project 'other'`); one holding a
    3.x root `tcw-config.yaml` (TCW-106's `legacy_message`); one with
    `tcw-version: 99.0.0` (`version_problem`'s message). A remote that
    `git clone` cannot read (a path that is not a repository), and an entry
    naming a branch the remote does not have (`<remote>#nosuch`), each fail
    with exit 1 and leave nothing behind. With `app`'s entry placing `core`
    at `../new/core` (trusted, `<tmp>/new` absent), each of those refusals
    also leaves no `<tmp>/new`. A library test in which removing the staging
    folder fails prints the warning naming it and reports the project's own
    outcome unchanged; one in which five staging names in a row are taken
    refuses with 7.9's message.
26. **Partial failure.** `app` names two absent parents, `aa` fetchable and
    `bb` whose folder is occupied: the run fetches `aa`, refuses `bb`, ends
    with `fetched 1, failed 1; what was fetched stays, and running the
    command again fetches the rest`, and exits 1; after `bb`'s folder is
    cleared, a second run fetches only `bb`. With, in addition, `app`'s work
    store declaring a repository that cannot be cloned, the store fails, the
    projects pass still runs, and the last line reads `fetched 1, failed 2`.
27. **The bound** (TCW-23). `app` is at `<tmp>/app` and its manifest places
    `core` at `../repos/core`, so `core`'s repository folder is
    `<tmp>/repos/core` and the bound for `core`'s manifests is `<tmp>/repos`.
    `core`'s committed manifest places its parent `base`, in turn, at each
    of: `../../base-far` (`<tmp>/base-far`), `../x/base` (not directly inside
    the bound), `vendor/base` (inside `core`'s own clone) and `../.base`
    (hidden); and, with personal files turned on for the test, at the
    absolute path `<tmp>/repos/base` in a `.tcw/tcw-manifest.local.yaml`
    committed into `core`'s remote: a folder directly inside the bound, so
    only the separate rule for absolute paths refuses it (Design 7.8). Each
    time `base` is refused before its remote is
    contacted (the stand-in `git` saw one `clone`, for `core`), with Design
    7.8's first message naming `<tmp>/repos`, nothing is made for `base`,
    `core` stays, and the run exits 1. At `../base`, `base` is fetched into
    `<tmp>/repos/base`.
    **On every run:** with `core` now here, a second `tcw project provision`
    refuses `../../base-far` the same way.
    **The way out works:** the refusal contains `tcw -C <tmp>/repos/core
    project provision base` and `<tmp>/repos/core/.tcw/tcw-manifest.local.yaml`,
    and does not name `app`'s personal manifest. Running that `-C` command
    fetches `base` into `<tmp>/base-far`, after which `tcw project provision`
    in `app` exits 0 with `nothing to fetch`. In a fresh fixture, an entry
    `base: <tmp>/elsewhere/base` written into
    `<tmp>/repos/core/.tcw/tcw-manifest.local.yaml`, then the same `-C`
    command, fetches `base` there.
    **Trusted:** `app`'s own personal manifest placing `core` at an absolute
    path outside `<tmp>/repos`, and `app`'s committed manifest placing it at
    `../../far/core`, are each honoured, their missing parent folders made.
    **A manifest already here is bounded too:** `app`'s second parent `ws`
    is already at `<tmp>/ws` (in no git repository, so the bound for its
    manifest is `<tmp>`); `app`'s third parent `wp` has no entry in `app`'s
    manifests, and `ws`'s manifest places it at `../x/wp` with a repository.
    `wp` is refused with the first message of 7.8 naming `<tmp>`, and the way
    out it names is `app`'s own manifests (`in this project; they are read
    first`). With `wp: ../x/wp` added to `app`'s
    `.tcw/tcw-manifest.local.yaml`, the next run fetches it into
    `<tmp>/x/wp`.
28. **Unfetchable projects.** `app` names parent `nn` with no manifest entry
    and parent `mm` whose entry gives no repository, both absent: plain
    `tcw project provision` exits 0 and names both, each with `no manifest
    entry gives the repository`; `tcw project provision mm` exits 5;
    `tcw project provision nope` exits 1 with `check the spelling`;
    `tcw project provision Nope` exits 2.
29. **A worktree.** In a linked git worktree of `app` made outside the main
    checkout, with `app`'s manifest entry `core: {path: ../core, repository:
    <remote>}`: `tcw project provision` in the worktree clones `core` next to
    the main checkout, and `tcw project path core` in the worktree then
    prints that folder.
30. **Dry run.** In AC 20's setup, `tcw project provision --dry-run` exits 0,
    makes no `clone` call and no folder, and prints `core: would fetch into
    <tmp>/core` and `core: any projects it names cannot be listed until it is
    fetched`, and nothing about `base`. In AC 23, it prints `would fetch` for
    one of the two and `would come with the clone for '<first>'` for the
    other. In AC 24's occupied and `.git`-only cases, AC 23's conflicting
    case and AC 27's `wp` case (a bounded entry in the first round), the dry
    run exits 1 with the same messages as the run. With every project here,
    it prints `nothing to fetch` and never `would fetch`.
31. **Graph problems first.** With `app`'s manifest holding an entry key
    `ref` (a TCW-107 Design 1.8 problem), `tcw project provision` and
    `--dry-run` exit 1, name `.tcw/tcw-manifest.yaml` and the key, and make
    no `clone` call. With `TCW_PROJECT_CORE` naming a folder that is not a
    project, the same, naming the variable.
32. **A fetched project's own problem.** `core`'s remote holds a manifest
    with a TCW-107 Design 1.8 problem: `core` is fetched and stays, its
    problem is printed naming its manifest and saying to remove `<tmp>/core`
    to undo the fetch, the run makes no further round (`base`, which `core`'s
    committed config names as a parent, is not attempted), and the run exits
    1. A remote
    whose `parents:` is malformed (TCW-108 Design 6.6) is fetched, a warning
    names the problem, and the run exits 0 when nothing else failed.
33. **Stores unchanged.** The existing tests of `tcw provision` for stores
    (`tests/test_init_provision_contract.py`, `tests/work/test_init_provision.py`,
    the store sections of `tests/test_store_provisioning.py`), run as
    `tcw project provision`, pass, and their messages name
    `tcw project provision`.
34. **A single project pays nothing.** In a project with no manifest, no
    parents and no children: `tcw project provision` exits 0, contacts
    nothing, and prints `nothing to fetch` (and the stores pass's "Nothing to
    provision" line when no store declares a repository); `tcw project list`
    prints only its ID; `tcw project info` prints `parents: none`,
    `children: none` and `load order: <id>`.
35. **A manifest fetched in the run cannot move a project already here**
    (Design 7.4). `app` at `<tmp>/app` has `parents: [core, lib]`; `lib` is
    at `<tmp>/lib`, in no manifest, so the search finds it; `app`'s manifest
    places `core` at `../repos/core` with a repository, and `core`'s
    committed manifest gives `lib: {path: ../lib, repository: <remote-lib>}`
    (`<tmp>/repos/lib`, absent). `tcw project provision` fetches `core`,
    then refuses `lib` with 7.4's message naming `<tmp>/lib`,
    `<tmp>/repos/lib` and `core`'s manifest; the stand-in `git` saw one
    `clone`, nothing is made at `<tmp>/repos/lib`, and the run exits 1. With
    `lib: ../lib` added to `app`'s `.tcw/tcw-manifest.local.yaml`, the next
    run exits 0 with `nothing to fetch`.
    **A clone that would give a kept project a second folder** (Design 7.4,
    7.9): with `lib` at `<tmp>/lib` as above and found by the search, `app`
    names a parent `server`, which `app`'s manifest places at
    `../mono/apps/server` with `subfolder: apps/server`, in a remote whose
    top folder's `.tcw/tcw-config.yaml` declares `id: lib`. `server` is
    refused with 7.9's message naming `lib` and `<tmp>/lib`, nothing is made
    at `<tmp>/mono`, `tcw project path lib` still prints `<tmp>/lib`, and the
    run exits 1. With the remote's top folder declaring `id: mono` instead,
    `server` is fetched.
36. **The bound is judged on resolved folders, and never at the home
    folder** (Design 7.8). In AC 27's setup: (a) `core`'s remote commits a
    symbolic link `up -> ../..` and its manifest places `base` at `up/base`
    (`<tmp>/base` on disk): refused, the message naming `<tmp>/base`, and
    nothing made there; with a committed link `lnk -> ..` and `base` at
    `lnk/base` (`<tmp>/repos/base` on disk), `base` is fetched. (b) With a
    folder `<tmp>/repos-x` present, `base` at `../../repos-x/base` is
    refused, although its text begins with `<tmp>/repos`. (c) With `HOME`
    set to `<tmp>/home`, `app` at `<tmp>/home/app` and `app`'s manifest
    placing `core` at `../core`, `core`'s bound is the home folder:
    `core` is fetched (its entry is `app`'s own), and `base` at `../base` is
    refused with 7.8's second message, nothing being made at
    `<tmp>/home/base`. The same with `HOME` set to `<tmp>/home/inner`, a
    folder below the bound. With `HOME` set to `<tmp>/home` and `app` at
    `<tmp>/home/.local/app` instead, `core` is fetched into
    `<tmp>/home/.local/core` and `base` at `../base` is refused with the
    same message (a hidden folder below the home folder).
    (d) **A link committed by an earlier clone of the same round:** `core`'s
    manifest names two parents of `core`, `aa` at `../aa` and `bb` at
    `../aa/l/../../bb`, in that order, and `aa`'s remote commits `l ->
    ../../far/x`. `bb` is refused before its remote is contacted, with 7.8's
    first message (its path passes through `<tmp>/repos/aa/l`, which does
    not exist when the round is checked, so it cannot be resolved
    completely), `aa` is fetched, nothing is made at `<tmp>/bb`,
    `<tmp>/far` or anywhere outside `<tmp>/repos`, and the run exits 1. This
    is the layout the plan review used to place a clone outside the bound.
    Because a clone only fills an absent or empty folder, the complete
    resolution already refuses every such bounded path when the round is
    checked;
    the checks made again before each clone and before each move are
    pinned by library tests: one in which the repository folder resolves
    elsewhere when checked again before its clone refuses with 7.8's "now
    leads to" message and runs no `clone`, and one in which it does so just
    before the move refuses and leaves nothing at either folder.
    (e) **Letter case:** where the temporary folder's file system ignores
    letter case (the test makes `a` and looks for `A`; skipped elsewhere,
    so CI on Linux skips it and the implement round records a run on
    macOS), `app`'s personal manifest places `core` at the home folder's
    path written in other letter case plus `/core`, with `HOME` set to
    `<tmp>/home` and `<tmp>/home` holding nothing else: `core` is fetched
    (its entry is `app`'s own), and `core`'s `base` at `../base` is refused
    with 7.8's second message.
    (f) **Git cannot say:** in AC 27's `ws` case, with `<tmp>/ws/.git` a
    file reading `gitdir: <tmp>/nowhere`, `wp` is refused with 7.8's third
    message and the run exits 1; with no `.git` there, the bound is `<tmp>`
    as AC 27 says.
    (g) **A `subfolder` that is a link:** `app`'s manifest places `server`
    at `../mono/apps/server` with `subfolder: apps/server`, and the remote
    commits `apps/server` as a link to `../../other`, where `<tmp>/other`
    holds a project declaring `id: server`. `server` is refused with 7.9's
    `leads outside the clone`, nothing is made at `<tmp>/mono`, and the run
    exits 1.
37. **Staging copies and addresses that look like options** (Design 7.9). A
    folder `<tmp>/.tcw-staging-0123abcd/core` holding a copy of `core`, as a
    killed run leaves it, is never taken for a project: in AC 19,
    `tcw project provision` fetches `core` into `<tmp>/core` and leaves that
    folder as it was; and with `lib` at `<tmp>/lib`, in no manifest, and a
    leftover `<tmp>/.tcw-staging-0123abcd/lib` holding a second copy of
    `lib`, `tcw project path lib` from `app` prints `<tmp>/lib` and exits 0,
    reporting no second match. An entry in `app`'s
    manifest whose repository is `--template=<tmp>/t`, and one whose branch
    is `<remote>#--orphan`, are each refused with exit 1 and `beginning with
    '-'`, and the stand-in `git` saw no `clone`. (If TCW-107 has made such a
    repository a manifest problem, as its handoff (2) asks, these two exit 1
    through 7.14 with TCW-107's message instead, still with no `clone`, and
    7.9's own check is pinned by a library test.) A library test in which the
    move into place raises `OSError` refuses with 7.10's message, and leaves
    no staging folder and nothing at the repository folder; one in which a
    symbolic link appears at the repository folder after the check refuses
    as occupied and writes nothing through the link.
38. **Another project's store names the command run there** (Design 7.2).
    `app` inherits `core`'s taxonomy, and `core`'s `taxonomy.repository`
    names a remote that is not fetched. In `app`, `tcw taxonomy list` exits
    7 (TCW-112 Design 1.3's third message) and its message contains
    `tcw -C <core's root> project provision --component taxonomy`; in
    `core`, the same command's message contains `tcw project provision
    --component taxonomy` and no `-C`.
39. The full suite, run as CI runs it (bare `pytest`), passes on `v4`.
40. **The documents** (Design 1.6). `tests/test_documented_cli_surface.py`
    and `tests/test_shipped_text.py` pass with the four commands removed; no
    Markdown file outside that test's archives writes `tcw init`,
    `tcw projects`, `tcw config show` or `tcw provision` as a command; every
    passage this item writes that names `tcw -C` gives its target as one
    token; and the implement round lists each passage changed, with what it
    now says.

### Coverage

The axes are the Design rules above. A cell is the criteria that check the
rule, or `n/a` with the line that makes it so.

| Design rule | Criteria |
| --- | --- |
| 1.1 the group and its verbs, help standard, registered after `work` | 1, 3 (the order shows in the suggestions) |
| 1.2 removed commands, the table, exit 2 | 2 |
| 1.3 synonyms before the same word elsewhere; the suggestions that change | 3 |
| 1.4 the sweep, narrowed for documentation | 4 |
| 1.5 no new exit code | n/a: no code is added; the codes each criterion asserts (0, 1, 2, 5, 7) are TCW-108 Design 8.3's list, pinned by `tests/test_cli_help_standard.py:151` and `tests/work/test_errors.py:18`, which this item does not change; run by 39 |
| 1.6 the passages that name a removed command: renamed only, one token after `-C`, listed for TCW-117 | 40 |
| 2.1 `new` is `init` renamed | 5 |
| 2.2 its help and refusal text | 4, 5 |
| 3.1 `list`: `found`, TCW-108's fields, no `read-only` | 6 |
| 3.2 graph problem refuses; absent is a row | 6, 18 |
| 3.3 the web app's rows | n/a: whether `_projects` (`tcw/serve/work.py:143-148`) survives TCW-114 Design 2.3 is settled by the plan; if it does, it keeps only `id`, `relation` and `present` of `connected`'s rows, none of which this item changes, and the existing `tests/serve/` suite runs it, by 39 |
| 4.1 `config`: exit 7, exit 1, own problems | 8 |
| 4.2 the origin label, the user-wide file's project | 7 |
| 4.3 the label in `info`, and its JSON | 13, 17 |
| 5.1 `path` prints a folder, default the active root | 9 |
| 5.2 any locatable project; the four outcomes | 9, 10, 11 |
| 5.3 invalid ID; no project | 10, 4 (`NO_PROJECT`) |
| 6.1 (1)-(4) ID, path, parents, children, load order | 12, 14 |
| 6.1 (5) settings, inherited mark, default | 12, 13 |
| 6.1 (6) stores | 12, 16 |
| 6.1 (7) overrides and same-path count | 15 |
| 6.2 never stops for what is missing; what does stop it | 12, 13, 15, 16, 18 |
| 6.3 text | 12, 13, 14, 15 |
| 6.4 JSON | 17 |
| 6.5 no project argument | 18 |
| 7.1 forms, scoping, `<id>` with `--component`, unknown `<id>` | 21, 28 |
| 7.2 stores as today; another project's store names `-C`; a store's failure does not stop the projects pass; `--` around the store's clone | 33, 21 (`--component`), 38, 26 (a failed store) |
| 7.3 (a) the family round by round; never a sibling | 19, 20 |
| 7.3 (b) `<id>` and its load order, upward only | 21 |
| 7.3 rounds: checks for the whole round before contact, one reading per round | 20 (`kk` in the next round), 26, 30 |
| 7.4 already here by every rule; still read | 22 |
| 7.4 answers kept for the whole run; a clone that would give a kept project a second folder | 35 |
| 7.5 the deciding entry from any manifest; no repository | 20 (an ancestor's manifest), 22, 28 |
| 7.6 the repository folder; empty; `.git`-only refused; occupied refused before contact; a trusted entry's parent folders made, and removed on a refusal | 24, 23 (with `subfolder`), 29 (worktree), 27 (trusted, parents made), 25 (parents removed) |
| 7.7 one clone per folder; conflicts; a clone missing a subfolder | 23 |
| 7.8 trusted and bounded manifests; trust by the owner's folder; on every run; direct child, not hidden; absolute and `~` paths refused as written | 27 |
| 7.8 the owner's repository folder; git cannot say | 27 (`ws` in no repository), 36 (f) |
| 7.8 resolved folders, completely; compared by identity; the home folder and hidden folders below it | 36 (a)-(e) |
| 7.8 the folder checked is the folder written: checked again before each clone and before the move | 36 (d) |
| 7.8 the way out names a manifest read first | 27 |
| 7.9 the clone: `-` refused, `--`, `--branch`, printed first, no prompt, staging never matched, five names taken, checked, a `subfolder` link, a second folder for a kept project, cleanup warning, nothing left | 19, 25, 35, 36 (g), 37 |
| 7.10 absent, empty; resolved and checked again without following a link; a failed move | 19, 24, 36 (d) and 37 (library tests) |
| 7.11 one reading per round; a fetched project's problems stop further rounds | 19 (found afterwards), 20 (in turn), 32, 35 |
| 7.12 dry run, the bound included | 30 |
| 7.13 output and exit codes; stores and projects counted together | 19, 26, 28, 35 |
| 7.14 graph problems before anything | 31 |
| 8.1 the deciding-entry method | 19, 23, 27 (through the command; the plan adds a library test) |
| 8.2 the interfaces relied on | 6 (`found`, TCW-108's fields), 7, 8 (TCW-109's origins and states), 9, 10 (`project_folder`), 12-17 (TCW-108's, TCW-109's and TCW-112's reads), 19, 20, 35 (`forget_registries`), 38 (TCW-112's third message) |

## Risks

- **Many tests run the removed commands.** Every test that calls `init`,
  `provision`, `projects list` or `config show` through `tcw.cli.main` or the
  script changes to the new name (`grep -rn` at the start of implement finds
  them; at `d2d02829` about 65 test files run one of the four). A
  mechanical rename can hide a test that stops testing what it did; the plan
  renames through one helper and reads each failure rather than editing
  assertions.
- **Agents on `v4` are taught the old names until TCW-117.** The skills and
  guides name `tcw init`, `tcw provision` and `tcw config show`, and the eval
  cases measure agents that read them. Design 1.2's line points them to the
  replacement on their first try; the eval fixture builder itself is changed
  here (Problem 7).
- **The origin label's shape changes** (Design 4.2), so a script that parsed
  3.x's `# project` and `# local: <path>` comments breaks. 4.0 is a clean
  break (design.md:8-12), and nothing is released between the children.
  TCW-109's own tests of `--origin` (its plan, Step 9: `<layer>: <whole
  path>` for an inherited value, `environment: <NAME>` for a variable) are
  changed here to the new shape, which keeps every fact they check.
- **Transitive fetching contacts remotes the person did not write.** That was
  3.x's behavior too (`tcw/cli.py:242-250`), and the safeguards stay: every
  remote is printed before it is contacted, `--dry-run` shows the first round
  without contacting anything, git cannot prompt, siblings are never
  followed, and Design 7.8 bounds where any manifest other than the active
  project's own may place a clone, on every run. This is the trust boundary
  TCW-23 asked to have stated: the person is trusted for the project they run
  the command in, and nothing else is trusted to choose a folder.
- **The active project's own committed manifest is trusted without a
  bound**, even in a repository the person has just cloned and not read
  (Design 7.8). That is the user's decision: it is the file every other
  command in that project already follows, and the person chose to run the
  command there. Its entries are still printed before any remote is
  contacted, and `--dry-run` shows them first.
- **The bound refuses legitimate layouts**: a fetched project whose
  manifest places its parent two folders up or in a subfolder of a sibling,
  and every bounded entry at all for a person who keeps repositories directly
  in their home folder (Design 7.8). The message names a manifest the lookup
  reads first, and the `tcw -C` command that makes the owner's manifest the
  active project's own. One run in the owner's folder settles each such
  project for good, since a project already here is never placed again.
  The same holds for a person who keeps repositories inside a hidden
  folder below their home folder, and for a manifest whose owner git cannot
  place in a repository (a broken `.git`, a missing `git`, or git's "dubious
  ownership" refusal): its bounded entries are refused until that is fixed
  or the `-C` way out is taken.
- **A bound below the home folder is not checked for what else lives
  there.** A bounded entry may create any new, non-hidden folder directly
  inside the bound, such as a folder beside the person's repositories in
  `/opt` or `/srv`. The home rule and the hidden-name rule cover the folders
  that programs read at start-up; a folder of repositories is where TCW is
  asked to put repositories.
- **Fetching a parent can change where the next command finds a project
  already here** (Design 7.4): TCW-107 Design 2.2 and TCW-108 Design 3.4 (b)
  read an ancestor's manifests before the search, so a fetched parent's
  entry for a project found by the search now decides for it. Within the
  provisioning run this is refused and explained; for later commands it is
  TCW-107's and TCW-108's lookup order, raised with them (handoffs).
- **A staging folder left by a killed run** (`.tcw-staging-<hex>`, Design
  7.9) stays until the person removes it; it is never matched by the search
  and never reused, and TCW does not remove what it did not make in this run.
- **A folder holding only `.git` is refused, not cloned into** (Design 7.6).
  A CI job that cloned without initialising a submodule leaves an empty
  folder, which is still cloned into; only a clone or submodule update that
  stopped partway leaves a lone `.git`, and finishing or removing it with git
  is the person's step. This narrows TCW-107's handoff, which said such a
  folder "is a valid target": the user's decision recorded in TCW-107 Design
  2.3 covers only the lookup (such a folder counts as "not on this machine",
  so validation does not fail), and refusing was decided at this spec's
  review on 2026-10-22, because moving the `.git` would change git state and
  break a submodule's `.git` file.
- **An empty folder that is a mount point** cannot be renamed onto, so a
  clone into it fails with 7.10's message naming the system's reason; CI jobs
  that mount an empty volume where a project should go need a different
  folder in the active project's personal manifest.
- **Cloning into an uninitialised submodule's folder** makes a standalone
  clone where the superproject expects its submodule. Git then shows that
  submodule as changed if the clone's commit differs from the one the
  superproject records. TCW does not read `.gitmodules` to warn about it
  (S-11: TCW reads git only to find a repository's root and recognise a
  worktree); `git submodule update --init` remains the person's choice
  before running `tcw project provision`.
- **The interfaces of TCW-107 to TCW-114 may land differently** from their
  specs. The plan re-checks each one (Design 8.2) and corrects this spec where
  the code disproves it, as TCW-106's implement stage did.

## Notes

### Decisions the design left to this spec, each with its reason

- **`tcw provision` is removed too** (Design 1.2). The request's list of
  removed commands names `tcw init`, `tcw projects` and `tcw config`; its
  product changes and the design's table (design.md:624) make
  `tcw project provision` the replacement for `tcw provision`, and keeping
  both would be two names for one command.
- **Removed commands are usage errors with a pointer** (Design 1.2), not
  aliases: one name per command, and one line that teaches the new one.
- **A synonym valid where it was typed comes before the word elsewhere**
  (Design 1.3), so adding `info` does not take away the `info` → `show`
  suggestion the ledger promises.
- **`tcw project new` keeps `tcw init`'s arguments** (Design 2), including
  `--id`; a positional ID would collide with the positional axes.
- **The origin label is one shape for every layer** (Design 4.2), naming the
  project, as the design asks.
- **`tcw project path` takes the ID as optional** (Design 5.1): with none it
  prints the active project's root, which an agent in a subfolder otherwise
  has to work out.
- **`tcw project info` shows** `work.backend`, and in Jira mode
  `work.jira.site` and `work.jira.project` (TCW-109's handoff named the first
  and last; the site says which Jira the project is in), the stores' folders,
  and TCW-112's override records; it **never exits 7** (Design 6.2), because
  it exists to show what is missing.
- **`tcw project provision` with no argument fetches the family; with `<id>`,
  that project and its load order** (Design 7.3). The no-argument form
  rebuilds 3.x's walk; `<id>` is what every "not on this machine" message
  names, so it fetches what that project needs to be read (its ancestors) and
  nothing it does not.
- **`--component` fetches no project** (Design 7.1), the scoping TCW-23's
  first question asked for (dropped there as convenience, kept here because
  the request asks for scoping).
- **The bound** (Design 7.8) answers TCW-23's second question with its first
  option, "bound it", adapted to 4.0's manifests. *Decided by the user on
  2026-10-22:* any manifest other than the active project's own files is
  always bounded, on every run, not only in the run that fetched it; a
  deeper or wider layout needs an entry in a manifest that is the active
  project's own. This spec makes the bound exact: the folder directly inside
  the parent of the owner's repository folder, not hidden, judged on folders
  resolved completely and compared by identity, checked again before each
  clone writes, and never when that parent is the home folder, above it, or
  inside a hidden folder below it. The
  way out is a manifest the lookup reads first (TCW-107 Design 2.2 (a)),
  which for a project another project names is that project's, made the
  active project's own by `tcw -C` (7.8). This **answers TCW-23**, which was
  already moved to `discarded` on 2026-10-21 as absorbed into this item: it
  stays there, nothing of it is left open, and its closing note can point at
  this rule once this item is completed.
- **The answers of one run are kept across its readings of the registry**
  (Design 7.4), so a manifest fetched during the run cannot move a project
  that was already here; the run refuses instead and says which entry to add.
- **A folder holding only `.git` is refused** (Design 7.6), with the advice
  to finish or remove it with git; *decided at the spec review on
  2026-10-22*, because moving it would change git state
  (`docs/lifecycle/abstraction.md:98-103`) and break a submodule's `.git`
  file. An empty folder is still cloned into.
- **Staging one folder deeper** (Design 7.9), so a copy left by a killed run
  is never found by the search; and `--` before every URL, with a
  repository or branch beginning with `-` refused.
- **A round** (Design 7.3) is one reading of the registry: every check of
  the round before any contact, then its clones, then one new reading.
- **A fetched project's graph problem fails the run but keeps the clone**
  (Design 7.11), as 3.x counted "a declaration error on an obtained node"
  as a failure (`tcw/cli.py:315-320`).
- **Exit 5 only for `<id>` itself** (Design 7.13): the no-argument form
  promises to fetch what can be fetched, and `<id>` promises one project.

### TCW-107's handoff, item by item

| What TCW-107 removed (its handoff on this ticket) | Here |
| --- | --- |
| fetching a declared project, and its connected projects in turn, following declarations from anywhere in the graph | Design 7.3, 7.5, 7.11; AC 19, 20 |
| a project already here is not fetched again (`tcw/cli.py:256-275`), including an ancestor's sibling | Design 7.4 (already here is the lookup's answer, from any manifest of the walk); AC 22. A sibling itself is never fetched in 4.0 (7.3 a). |
| a project already here is still read for its own declarations | Design 7.4; AC 22, last sentence |
| the `--dry-run` listing, never "would obtain" for a project already here | Design 7.12; AC 30 |
| two entries naming one repository share one working copy | Design 7.7; AC 23 |
| a fetched repository with no project at the expected folder is refused | Design 7.9, 7.7; AC 23, 25 |
| an occupied folder is refused before anything is fetched | Design 7.6; AC 24 |
| a malformed declaration refuses and names the line; a declaration error on a fetched project fails the run | Design 7.14, 7.11; AC 31, 32 |
| an upstream fetched into a reader-only checkout, without following its own connections | Design 7.3 (a parent's children are never followed), 7.9 (nothing written into it); AC 19, 20. A parent's own parents are followed, since in 4.0 they are in the load order (TCW-108). |
| `TCW_PROJECT_<ID>` never fetched; a variable naming a folder not here falls through to the entry's repository | Design 7.4; AC 22 |
| clone into the deciding entry's folder with `subfolder` removed | Design 7.6; AC 23 |
| an empty folder, or one holding only `.git`, is a valid target | Narrowed. An empty folder is cloned into (Design 7.6, 7.10; AC 24). A folder holding only `.git` is refused and left untouched (Design 7.6; AC 24): the user's TCW-107 decision covers only the lookup, and moving the `.git` would change git state (Notes, Risks). |
| `forget_registries()` after cloning | Design 7.11, once per round, with the run's earlier answers kept and compared (7.4); AC 19, 20, 35 |
| `found` in `tcw project list` | Design 3.1; AC 6 |
| `FsStoreProvisioner`'s project branch is kept for reuse | Design 7.9 reuses its pattern (clone beside, check, rename in); its checks of the clone are written anew, since that branch checks only that the configuration file exists (`tcw/store/fs.py:3150-3153`); the branch itself is removed once nothing calls it |

### Other handoffs on this ticket

- **TCW-108:** `tcw project info` prints `parents()`, `declared_child_ids()`,
  `load_order()` and its warning (Design 6.1, 6.3; AC 12, 14).
  `tcw project list` carries Design 8.2's fields (Design 3.1; AC 6), except
  `read-only`, which TCW-114 Design 1.8 removes after TCW-108's handoff named
  it; TCW-114 is the later decision and lands first.
- **TCW-109:** `tcw project config` has Design 7.1's exits 7 and 1 (Design
  4.1; AC 8) and, with `--origin`, each value's project and file or variable
  (Design 4.2; AC 7). `tcw project info` shows `work.backend` and
  `work.jira.project`, the latter marked when inherited (Design 6.1; AC 13).
- **TCW-112:** `tcw project info` shows, per axis, the active project's own
  overrides and the count of same-path warnings (Design 6.1 (7); AC 15).
- **TCW-114:** its refusal of another project's object (TCW-114 Design 1.3)
  may add `tcw project provision <id>` for a project not on this machine now
  that the command exists. Left to TCW-114's code as written: its message
  already names the repository, and adding the command is a one-line change
  the plan makes if TCW-114 has not.

### Handoffs back to earlier items

These come from this spec's review and are recorded on each ticket when
this spec is accepted. None changes an earlier item's own criteria; each is
either a message that should say more, or a question about the lookup order
that this item works around and does not settle.

- **TCW-107:** (1) a folder holding only `.git` is refused by
  `tcw project provision` (Design 7.6), so Design 6.2's "not on this
  machine" message, when the deciding entry's folder holds only `.git`,
  should say so and name git (`<path> holds only .git; finish or remove it
  with git`) rather than, or before, naming `tcw project provision <id>`.
  (2) Design 1.5 accepts a `repository` URL or branch beginning with `-`;
  this item refuses one before running git (Design 7.9), and refusing it as
  a manifest problem (Design 1.8) would catch it in `tcw validate` too.
  (3) Design 1.6's sentence "TCW-115 clones the repository there" holds,
  with Design 7.8's bound for entries outside the active project's own
  manifests.
- **TCW-108:** Design 3.4 (b) reads an ancestor's manifests before the
  search, so fetching a parent whose manifest has an entry for a project
  that the search already finds next to the active project changes where
  every later command finds that project (Design 7.4 and Risks here).
  Provisioning refuses that within its own run; whether the order should
  change for later commands is the lookup's question, not this item's.
- **TCW-112:** the store message that Design 1.3's third message carries
  (`StoreNotProvisioned`) now names `tcw -C <that project's root> project
  provision --component <axis>` when the store is not the active project's
  (Design 7.2; AC 38). TCW-112's tests that match that message's text
  change with it.
- **TCW-113:** its table's rows a and c (TCW-113 spec:319, :321) and its AC
  29 (:1208) say the store message names `tcw provision`; after this item it
  names `tcw project provision --component <axis>`, or the `-C` form when the
  store is another project's (Design 7.2). TCW-113 lands at about the same
  point, so its row c and AC 29 should say "names the provisioning command",
  and its test should assert the words `has not been provisioned here` and
  `provision`, which hold both before and after this item; then this item
  edits none of TCW-113's tests.
- **TCW-114:** `reached_by_both_sides`, which TCW-114 keeps for 3.x
  provisioning alone, is removed by this item with its tests once nothing
  calls it (Abstraction litmus test). This item relies on TCW-114's `-C`
  skip in the three document checks taking exactly one token (Design 1.6).
- **TCW-107:** `git_root` (`tcw/store/fs.py:240-255`) returns `None` for
  every git failure, so a lookup that uses it reads "dubious ownership" or a
  missing `git` as "in no repository". This item does not use it for the
  bound (Design 7.8 asks git only where a `.git` entry exists, and refuses
  when git cannot answer); whether TCW-107's worktree rules should tell the
  two apart is TCW-107's question.

### Corrected after the plan review

The plan review of 2026-10-22 found these defects in the first accepted
spec; each is corrected above, *decided by the dispatching session,
2026-10-22*, with the reason given where it is corrected:

1. Design 1.4 left the documents that name a removed command to TCW-117,
   which the suite's document checks cannot allow (now Design 1.6, AC 40).
2. Design 8.1 named fewer fields than 7.8 needs (now lists `asked_by`,
   `owner` and `repository_folder`).
3. Design 7.8 gave refusing an absolute or `~` path as a consequence of the
   direct-child rule; it is a separate rule.
4. TCW-113's message text: a handoff above, not a change here.
5. Design 7.4's changed answer can arise with no deciding manifest: through
   a clone's top folder placed next to other projects, which 7.9 now
   refuses before the move, with a fallback text for anything else.
6. Design 1.4 and the TCW-117 handoff named `AGENTS.md`, which names no
   removed command; removed from both.

The same review found the folder checked could differ from the folder
written (7.8's "The folder checked is the folder written", "Resolved" and
"Folders are compared by identity"), and led to the decisions on a hidden
bound, a git failure, `git clone --branch`, a `subfolder` link, the
parent folders of a trusted entry, staging collisions and cleanup, and a
store's failure; each is marked where it is made.

### Handoffs to later items

These are recorded on each ticket when this spec is accepted.

- **TCW-116 (`tcw migrate`):** a 3.x project connected by a `repository`
  declaration with no `path` was cloned into the per-machine cache
  (`tcw/store/checkouts.py:111-115`); after migration, `tcw project provision`
  clones only into a manifest entry's folder, so the migrated entry needs a
  `path` (TCW-107's handoff says the same). The clone 3.x left in that cache
  is not found by 4.0's lookup, so without more `tcw project provision`
  would make a second copy and leave the first, possibly holding local
  changes, on disk. `tcw migrate` should write the migrated entry's `path`
  into the active project's personal manifest pointing at the cache clone
  when one is there (or, failing that, name it in its report), so that the
  project is found rather than fetched again. `tcw migrate` stays a
  top-level command (design.md:699).
- **TCW-117 (guides and skills):** every file outside the CLI that names a
  removed command has had its command names changed by this item (Design
  1.6), and TCW-117 rewrites what each passage says for 4.0; the implement
  round of this item lists every passage changed, with what it now says. At
  `d2d02829`: `README.md`, `docs/guide/cli.md`, `docs/guide/configuration.md`,
  `docs/guide/multi-repo.md`, `docs/guide/work.md`, `docs/use-cases.md`
  (UC-6 names `tcw provision`; its known gap "TCW-23 (provision scoping)" is
  closed by this item), `skills/README.md`, `skills/capabilities/SKILL.md`,
  `skills/configure/SKILL.md` and its references `personal.md`,
  `projects.md`, `stores.md`, `work.md`, `skills/setup/SKILL.md` and its
  references `capabilities.md`, `install.md`, `project.md`, `taxonomy.md`,
  `skills/taxonomy/SKILL.md`, `skills/work/SKILL.md` and
  `skills/work/references/commands.md`. The setup skill teaches
  `tcw project new`; the configure skill teaches `tcw project config
  --origin` and `tcw project info`; the work skill teaches
  `tcw project path <id>` as the way to find where to run a change in
  another project, with `tcw -C`. The migration guide lists the four removed
  commands and their replacements (Design 1.2's table) and the two new
  verbs, says that the `--origin` comments changed shape (Design 4.2) for
  scripts that read them, and explains the bound (Design 7.8): which
  manifests are trusted, the direct-child and home-folder rules, and the
  `tcw -C <folder> project provision <id>` way out. The guide on related
  projects says a folder holding only `.git` is refused and why (Design
  7.6), and that a `.tcw-staging-<hex>` folder is what a killed run leaves
  (Design 7.9). Every `tcw -C` command TCW-117 writes gives its target as
  one token (Design 1.6). The bound's explanation also says that a hidden
  folder below the home folder is refused like the home folder, and that a
  manifest whose owner git cannot place in a repository is refused (7.8).
- **TCW-118 (release):** the release notes name the `tcw project` group and
  the four removed commands, and say that provisioning places a clone from a
  manifest other than the active project's own only directly beside that
  project, never at or above the home folder or inside a hidden folder below
  it, and refuses a folder holding only `.git`.

### Questions for TCW-99

None that this item needs answered. The lookup-order consequence in the
TCW-108 handoff above may become one if TCW-108 decides it belongs to the
design rather than to its own spec. Every rule above either carries out the design or decides what it
leaves open (above). The one place this spec narrows the design's wording,
"a misspelled project ID is an error, not 'could not check'" (Design 5.2,
7.1), is TCW-107's decision, accepted by the user on 2026-10-22, applied here.
