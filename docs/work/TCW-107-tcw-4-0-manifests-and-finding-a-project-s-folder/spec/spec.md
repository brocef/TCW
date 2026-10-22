# Spec — TCW 4.0: manifests and finding a project's folder

Child 2 of 13 of TCW-99. It carries out these sections of the TCW-99 design
(`docs/work/TCW-99-…/design.md`): "The `.tcw/` folder" (the two manifest
files), "The manifest", "Locating a project", "Git worktrees", and the part of
"A related project that is not on this machine" that concerns finding one.
Built on the `v4` branch, on top of TCW-106 (child 1), whose
`tcw/project_files.py` gives the project marker `.tcw/tcw-config.yaml`
(`SENTINEL`, `tcw/project_files.py:34`), the function turning a file in
`.tcw/` into its project root (`root_of`, `:59`), and the one version check
every `tcw-*.yaml` reader calls (`version_problem`, `:110`).

File and line references are to commit `39603cc4` on `v4`. TCW-106 is still
being finished there, so the plan re-checks them against whatever TCW-106
finally lands.

This item lands before TCW-110 in the children's order, and TCW-110 calls the
lookup this item defines (Design 2.12) rather than providing a stand-in of its
own.

## Capability changes

- **New** `cli/record-where-other-projects-are-in-a-manifest`: a project lists
  where other projects are, by ID, in `.tcw/tcw-manifest.yaml` (shared) and
  `.tcw/tcw-manifest.local.yaml` (this machine only), each entry a relative
  path and optionally the repository, and branch, it is fetched from.
- **New** `cli/find-a-projects-folder-from-its-id`: TCW finds a project's
  folder from its ID through the manifests of the project that names it and
  of that project's family, then in the folders next to it and the folders
  enclosing it, never inside a project; two matches are an error naming both.
- **Changed** `cli/host-multiple-projects-in-one-repo`: `projects:` names
  connected projects by ID only; their locations are in the manifest.
- **Changed** `cli/declare-a-connected-projects-home-repository`: the
  repository moves from the `projects:` entry into the manifest entry, written
  `<url>#<branch>`.
- **Changed** `cli/point-tcw-at-a-project-i-already-have`: `TCW_PROJECT_<ID>`
  is kept, and decides over every manifest and the search.
- **Changed** `cli/run-from-a-git-worktree`: personal files fall back to the
  main checkout's, and paths and searches outside the repository are made
  from the main checkout.
- **Changed** `cli/list-connected-projects`: `--json` says how each project
  was found.
- **Changed** `cli/validate-a-project`: checks every manifest entry.
- **Changed** `cli/provision-declared-stores` and
  `cli/read-from-an-upstream-project`: `tcw provision` no longer fetches
  connected projects; a project not on this machine names
  `tcw project provision <id>` (TCW-115) and the repository its manifest
  entry gives.
- **Changed** `cli/scaffold-the-doc-trees`: `tcw init` also lists the personal
  manifest in `.tcw/.gitignore`.
- **Changed** `cli/override-the-team-configuration-for-myself`: in a git
  worktree with no personal file of its own, the main checkout's is used.
- **Changed** `cli/read-a-file-by-the-format-version-it-records`: manifests
  carry `tcw-version` and are refused by the same rule. (TCW-106 creates this
  capability.)
- **Taxonomy:** new `manifest`; changed `project`, `project-registry`,
  `personal-configuration`.

## Problem

In 3.x a project's location is written into the configuration of every
project that connects to it, beside the relationship itself.

1. **Locations live in `tcw-config.yaml`, on every edge.** A `projects:` entry
   is a bare path (`child-id: ../child`) or a mapping with `path` and
   `repository` (`parse_connected_entry`, `tcw/store/base.py:865-916`;
   `ConnectedProject`, `:700-720`). The same project's location is therefore
   written once by each project that names it, and both sides of a
   parent–child pair carry one. TCW then has to check that the two agree
   (`_points_elsewhere`, `tcw/store/project.py:961-980`; the "does not point
   back" problems at `:901-905` and `:929-933`) and report a location that
   does not resolve for a project found another way (`misdirected`,
   `:431-451`, printed by `tcw validate` at `tcw/cli.py:439-443`). TCW-99
   principle 1 and "The manifest" say a project's location never appears in
   `tcw-config.yaml`, and is recorded once, in a manifest.
2. **There is no file for a location that is personal to this machine.** A
   person whose checkout is laid out differently from the committed
   locations has only `TCW_PROJECT_<ID>` (`override_variable`,
   `tcw/store/project.py:40-56`; `_resolve_override`, `:756-790`): personal
   files may not set `projects` (`PERSONAL_KEYS`, `tcw/config.py:45-52`).
3. **Nothing is found without a declaration.** A connected project is found
   only by following its locator, its `repository` declaration, or the
   variable (`_target_path`, `tcw/store/project.py:681-724`). A package one
   folder below its monorepo root must write `../..` to find its parent, and
   a library cloned next to its reader must be written down too. TCW-99
   "Locating a project" adds a bounded search: folders next to the project,
   then folders enclosing it.
4. **Worktree handling covers locators only.** A relative locator leaving the
   worktree is re-read from the main checkout (`_locator_path`,
   `tcw/store/project.py:792-815`), and a path into the main checkout whose
   counterpart in this worktree holds the same project is taken from the
   worktree (`_worktree_copy`, `:817-847`). Personal files are read from the
   worktree only (`_personal_layers`, `tcw/config.py:676-693`, joins
   `root / LOCAL_FILE`), so a new worktree loses its person's settings
   (`docs/use-cases.md`, S-4, first requirement). TCW-106's spec left reading
   the main checkout's personal file to this item.
5. **`tcw provision` fetches connected projects from `projects:` entries**
   (`declared_connected_projects`, `tcw/store/fs.py:3343-3385`, walked by
   `_provision_projects`, `tcw/cli.py:238`, called at `:190`), into a
   declared `checkout` or a cache folder (`checkout_root`,
   `tcw/store/checkouts.py:95-115`). Once the repository moves into the
   manifest, that walk reads nothing; fetching a project becomes
   `tcw project provision` (TCW-115).
6. **The registry is opened again and again in one command, and only answers
   for the projects its graph holds.** `FsProjectRegistry.open` builds a new
   graph every time it is called (`tcw/store/project.py:232-235`); one
   `tcw validate` run opens it at least twice (`tcw/validate.py:395`, `:398`)
   and every store resolution can open it once more (`tcw/store/fs.py:3174`).
   A project ID is answered only when that graph holds it (`get`,
   `tcw/store/project.py:244-246`), so nothing can find a project that no
   `projects:` entry names. TCW-110 needs exactly that, for a full identifier
   naming any project TCW can locate.

## Goals

1. A project's location is recorded only in a manifest
   (`.tcw/tcw-manifest.yaml`, `.tcw/tcw-manifest.local.yaml`), or given by
   `TCW_PROJECT_<ID>`, or found by the search. Never in `tcw-config.yaml`.
2. TCW finds a project's folder from its ID in the order TCW-99 "Locating a
   project" gives, without ever looking inside a project, through one
   function that any caller can use for any project ID.
3. Two folders matching one ID is an error naming both; a manifest entry is
   never second-guessed by the search.
4. One command gives one answer to each lookup, whichever project it runs in
   and however many times the question is asked.
5. A linked git worktree behaves as its main checkout does, with the branch's
   own tracked files and, by default, the main checkout's personal files.
6. `tcw validate` checks every entry in the project's manifests.
7. A single project (UC-1) needs no manifest and pays nothing.

## Non-goals

- **What links projects** (TCW-108). The 3.x `projects:` key, with its
  `parent`, `children` and `upstream` relations, its reciprocity rule and its
  read-only upstreams, still says how projects relate until TCW-108 replaces
  it with parent links. This item changes only where those projects are
  found (Design 3). "Ancestors" and "descendants" below mean what that key
  gives today.
- **Fetching a project that is not here** (`tcw project provision`, TCW-115).
  This item records the repository in the manifest and names the command;
  TCW-115 builds it, and clones into the folder the deciding manifest entry
  gives (Design 1.6). `tcw project path <id>` is TCW-115's too.
- **Environment overrides of configuration keys** (`TCW_<KEY>__<PROJECT>`,
  TCW-109). Design 2.1 says why `TCW_PROJECT_<ID>` stays, and what that
  leaves TCW-109 to decide.
- **Full identifiers** (TCW-110). This item provides the lookup for any
  project ID (Design 2.12), and in this item only the 3.x `projects:` key
  calls it with IDs. Turning a full identifier or a `tcw://` address into a
  project is TCW-110's, through this function; `tcw -C` is TCW-114's.
- **A store's own `repository`** (`work.repository` and the others) and
  store locations written as `.path` addresses (TCW-110). Stores keep their
  3.x declarations here.
- **Converting a 3.x `projects:` entry's locators into manifest entries**
  (`tcw migrate`, TCW-116). Notes lists the mapping it must follow.
- **Guides, skills and the use-case document's wording** (TCW-117), except
  this repository's own `.tcw/.gitignore` (AC 22). Notes lists what they
  must change.

## Design

All of this item is the deployment layer of the TCW-99 design ("What any
store must support, and what is only about folders"): how a folder of files is
found on one machine.

### 1. The manifest files

1.1. A project may hold `.tcw/tcw-manifest.yaml`, shared and meant to be
committed, and `.tcw/tcw-manifest.local.yaml`, personal to this machine. Both
are optional. A missing file has no entries.

1.2. **Format.** Each is a YAML mapping with two top-level keys:
`tcw-version`, which follows TCW-106 Design 3 and is checked by the same
`version_problem`, and `projects`, a mapping from project ID to entry. No
other top-level key is accepted. The entries sit under `projects:` rather than
at the top level so that a project could never be named `tcw-version`. Each
ID must be a valid project ID (`validate_project_id`,
`tcw/store/project.py:29-37`).

```yaml
tcw-version: 4.0.0
projects:
  shared: packages/shared                       # a path alone
  core:
    path: ../core
    repository: https://github.com/example/core.git#release
  server:
    path: ../app/apps/server
    repository: git@github.com:example/app.git
    subfolder: apps/server
```

1.3. **An entry** is either a path written as a string, or a mapping with
`path` (required), `repository` (optional) and `subfolder` (optional, only
with `repository`). No other key is accepted.

1.4. **`path`** is the folder holding the project's `.tcw/`. A relative path
is read from the project root, the folder holding the manifest's `.tcw/`, not
from `.tcw/` itself, and may use `..`. In `tcw-manifest.yaml` it must be
relative: that file is shared by every machine. In
`tcw-manifest.local.yaml` it may also be absolute or start with `~` (the
person's home folder).

1.5. **`repository`** is `<url>` or `<url>#<branch>`. The text before the
first `#` is the URL and must not be empty; the text after it names the
branch (or tag) to fetch and must not be empty or hold spaces or a second
`#`. `#` was chosen because the remote addresses people use for shared
repositories (`https://…`, `ssh://…` and the `git@host:owner/repo` form) do
not contain it, whereas `@` and `:` both appear in the `git@host` form; it
is also the form npm uses for a git dependency's branch. A repository whose
own address holds a `#` (possible for a local folder or a `file://` address)
cannot be written in a manifest entry: everything after the first `#` is
read as the branch.

1.6. **`subfolder`** is where the project sits inside that repository when
it is not the repository's root: relative, without `.` or `..` parts, and
`path` must end with the same folder names. So the repository's own folder
is `path` with `subfolder` removed (Design 6.4 uses this, and TCW-115 clones
the repository there).

1.7. **An entry says where a project is, and nothing else.** Listing a
project in a manifest does not connect it: `tcw projects list` shows only
what `projects:` names.

1.8. **A problem in a manifest** (bad YAML, a `tcw-version` problem, a key or
value Design 1.2-1.6 refuses) is recorded against that manifest's file, as a
problem of the project graph, exactly as a problem in a connected project's
configuration is today (`_problem`, `tcw/store/project.py:1085-1089`).
Commands that require a valid graph refuse with exit 1, and `tcw validate`
reports it as an error. A manifest with a problem is not used for any lookup,
and a lookup that would consult it fails (Design 2.12). The `tcw-version`
problems use `version_problem`'s messages, except a missing `tcw-version`:
`version_problem` reads that as a 3.x file and names `tcw migrate`
(`tcw/project_files.py:116-119`), but 3.x had no manifests, so every manifest
was written by hand or by TCW 4. For a manifest the message is
`has no tcw-version; a manifest starts with 'tcw-version: <running version>'`.

1.9. `tcw init` adds `/tcw-manifest.local.yaml` to `.tcw/.gitignore`
alongside TCW-106's `/tcw-config.local.yaml`, under the same rules
(`ignore_personal_file`, `tcw/store/fs.py:225-237`, called only inside a git
repository, `tcw/cli.py:76-77`): only when no line there already reads it or
`tcw-manifest.local.yaml`, adding the missing line to a file that has the
other. Outside a git repository neither line is written, as today. `tcw init`
writes no manifest. `tcw validate` warns when `.tcw/tcw-manifest.local.yaml`
is tracked, as it does for the personal configuration file
(`personal_file_tracked`, `tcw/store/fs.py:205-222`).

1.10. `TCW_NO_PERSONAL_CONFIG=1` skips `tcw-manifest.local.yaml` in every
project, as it skips `tcw-config.local.yaml` (`_personal_layers`,
`tcw/config.py:676-693`): the switch makes a run read no personal file, so
that it sees only what is committed and what its environment says. It does
not turn off `TCW_PROJECT_<ID>`, which is the environment's own statement and
not a file. Any other value of the switch is the configuration problem it is
today (`tcw/config.py:683-687`), and personal manifests are then not read
either.

### 2. Finding a project's folder from its ID

Asked for the folder of project `X` by the project `P` that names it (the
project whose configuration, manifest or record holds the ID; not necessarily
the active project), TCW takes the first rule below that answers. Every rule
in 2.1-2.8 works for any project ID: none of them needs `X` to be named under
`projects:` (Design 2.12, AC 24).

2.1. **`TCW_PROJECT_<ID>`**, unchanged from 3.x (`_resolve_override`,
`tcw/store/project.py:756-790`): when set to a folder on this machine it
decides, above every manifest and the search; a folder that is not a project
is refused, as a graph problem; a variable naming a folder that is not here
is skipped.
*Decision, left to the spec by TCW-99:* the variable stays. It is the only
way to give a location from the environment (a CI job, a cloud session)
without writing a file, and in 4.0 a location is not configuration, so the
`TCW_<KEY>__<PROJECT>` variables TCW-109 adds for configuration keys cannot
reach it. TCW-109 therefore adds no variable for a manifest path; if it finds
a reason to replace `TCW_PROJECT_<ID>`, that is raised on TCW-99.

2.2. **Manifests**, in this order, each project's
`tcw-manifest.local.yaml` before its `tcw-manifest.yaml`:
(a) `P`'s; (b) each ancestor's, nearest first; (c) each descendant's,
breadth first: `P`'s children in the order its configuration lists them,
then theirs. A project is consulted only once it has itself been found
(Design 2.11 fixes the order in which projects are found); a project whose
own folder is being looked up at that moment is skipped, so the walk always
ends. The first entry for `X` decides. **Entries never merge:** the deciding
entry's `path`, `repository` and `subfolder` are the ones used, and an entry
for `X` in a manifest consulted later is not read, not even for a
`repository` the deciding entry leaves out.
The personal manifest is read for every project in the walk, not only the
active one, because it describes this machine, which is the machine running
the command (Use cases, S-5; Questions for TCW-99).

2.3. **An entry decides, whatever is on disk.** When the entry's folder holds
no project, `X` is not on this machine (Design 6.2), and the search is not
made. When it holds a project with another ID, a 3.x project, or a
configuration whose version this TCW cannot read, that is a graph problem
naming the entry's manifest and the folder.

2.4. **Folders next to `P`'s root**: every folder directly inside the folder
that holds `P`'s root, except `P`'s root itself and any folder named `.tcw`.
A folder matches when its `.tcw/tcw-config.yaml` declares `id: X`. The
`.tcw` exception matters when the folder holding `P`'s root is itself a
project root (`P` at `shared/desktop` beside `shared/.tcw/`): that `.tcw/`
holds a `tcw-config.yaml` with no `.tcw/` of its own, which 2.8 would
otherwise read as a 3.x project. TCW-106's `find_marker` skips it for the
same reason (`tcw/project_files.py:78`).

2.5. **Folders enclosing `P`'s root**, from the nearest outwards to the
filesystem root, each matching the same way. Only the enclosing folder itself
is tested, never its other contents.

2.6. **Never downwards.** The search reads, for each folder named by 2.4 or
2.5, only `<folder>/.tcw/tcw-config.yaml` and `<folder>/tcw-config.yaml`
(for Design 2.8), and lists the contents of one folder only: the one holding
`P`'s root. No folder deeper than that is ever read. So a folder nested
inside a sibling or inside an enclosing project (`node_modules/dep`,
`vendor/x`, `.venv`, a package two levels down) is never matched. `P`'s own
siblings are tested even when the folder holding them is itself a project
root (from `app/shared`, the siblings are `app`'s other subfolders), because
that is what "next to" means; a dependency folder directly inside that
project can then be tested, but only for its own `.tcw/`, never for anything
inside it.

2.7. **Two matches are an error.** Every match from 2.4 and 2.5 is collected
before deciding. Two folders that are different folders (compared by identity,
after Design 4.4) are a graph problem naming both. The message says how to
settle it: `add an entry for '<X>' to .tcw/tcw-manifest.local.yaml (this
machine) or .tcw/tcw-manifest.yaml (everyone)`. A common way to get two
matches is a second clone, or a git worktree of `X` made next to `X`
(`git worktree add ../lib-feature`); Design 4.4 merges only copies of the
active project's own repository. With one match, it is the answer; with
none, `X` is not on this machine (Design 6.2).

2.8. **A search candidate that cannot be read is not a match** and is not
reported: it is not this project's file. This includes a folder TCW is not
allowed to read. The exceptions are candidates that are `X` but cannot be
read as 4.0: one whose `.tcw/tcw-config.yaml` declares `id: X` but fails
`version_problem`, and one holding only a 3.x root `tcw-config.yaml`
declaring `id: X`. Each is a graph problem naming the folder, with
`version_problem`'s message or TCW-106's `legacy_message`
(`tcw/project_files.py:90-93`).

2.9. **One folder per ID in a command.** When two lookups in one command find
`X` at two different folders (compared after Design 4.4), that is a graph
problem naming both, as the duplicate ID is today
(`tcw/store/project.py:524-534`). This holds for every lookup in the command,
not only the graph walk's: a later call (Design 2.12) that finds `X` somewhere
other than an earlier answer reports the duplicate at that point.

2.10. **Where the lookup is used.** In this item, for every project the 3.x
`projects:` key names (parent, children, upstream), from the project whose
configuration names it, in place of the locator ladder in `_target_path`
(`tcw/store/project.py:681-724`). "Ancestors" in 2.2 are the chain of
`projects.parent` entries; "descendants" are `projects.children`, transitively.
An upstream project's own manifests are not consulted, because 3.x does not
follow an upstream's connections (`_visit`, `tcw/store/project.py:537-539`);
TCW-108 turns upstreams into parents, and their manifests then count as
ancestors'. TCW-110 calls the same function for the project of every full
identifier and `.path` address, and TCW-116 for deciding whether a 3.x
locator needs a manifest entry at all.

2.11. **Order, and one answer per question.**
(a) The graph walk visits a project's parent before its children, its
children in the order its configuration lists them, and its upstreams last.
Today it visits children first (`_follow_edges`,
`tcw/store/project.py:543-552`), so a child looked up before its parent's
parent had been found could not use that ancestor's manifest. With the parent
first, a project's parent chain has been found by the time its children are
looked up, so 2.2 (b) can consult it.
(b) Each question, "where is `X`, asked by `P`", is answered once per
command, and the answer is kept, whether it is a folder, "not on this
machine" or a problem. The walk, the reciprocity check (which today runs
`_target_path` again after the walk, `tcw/store/project.py:885`, `:891`,
`:912`, and could get a different answer because more projects had been
found by then) and every later call reuse it.
(c) So within one family, a project gets the same folders whichever project
in its parent chain the command runs in (AC 25). A project whose parent can
be found only through a more distant project's manifest does not find it
when the command runs in that project itself, because nothing else has been
found yet: `k` at `app/plugins/k`, whose parent `a` sits at `app/packages/a`
and is listed only in `app`'s manifest, does not find `a` when run in `k`.
That limit is the design's ("the children already found"); Risks names it,
and an entry in `k`'s own manifest settles it.

2.12. **The function.** The lookup is one method of the files store's project
registry, and every caller uses it:

```python
FsProjectRegistry.project_folder(project_id: str, named_by: Path) -> Path
```

- `project_id` is any valid project ID (`validate_project_id`); the caller
  has parsed it. It need not appear under any `projects:` key.
- `named_by` is the root folder of `P`, the project that names `project_id`.
  It must be a folder this registry has already found: the active project's
  root, a project in its graph, or a folder an earlier call returned; any
  other folder is a programming error (`ValueError`). When `P` is not in the
  graph, the registry reads `P`'s configuration to learn its parent and
  children for 2.2, locating them through this same method, from `P`.
- `project_folder(<the ID P declares>, named_by)` returns `named_by` without
  a lookup.
- It is a method, not a free function, because the answer depends on the
  active project: the worktree rules of Design 4 are anchored on the active
  project's worktree (`self._anchors`, computed once from the active
  project's root, `tcw/store/project.py:229`), and 2.9 and 2.11 (b) compare
  and keep answers across the whole command.

Its outcomes:

| Outcome | When | What the call does |
| --- | --- | --- |
| found | a rule answers with a folder holding a 4.0 project that declares `project_id` | returns that folder, the project's root, after Design 4.4 |
| not on this machine | `project_id` is named by an entry in a manifest the walk of 2.2 consulted, or by a `projects:` entry of a project in that walk, and no rule found it: the deciding entry's folder holds no project (2.3), or no entry has it and the search found nothing (2.7) | raises `Unreachable` (exit 5, `tcw/errors.py:76-77`) with Design 6.2's message; when the deciding entry gives a repository, the message names it and `tcw project provision <id>` |
| unknown | no manifest the walk consulted and no `projects:` entry of a project in the walk names `project_id`, and the search did not find it | raises `UnknownProject` (exit 1) with `no project with ID '<id>' is known or found near this one; check the spelling` |
| graph problem | two matches (2.7); the deciding entry's folder holds a project with another ID, a 3.x project, or a version this TCW cannot read (2.3); a search candidate that is `X` but cannot be read as 4.0 (2.8); a manifest the lookup would consult has a format problem (1.8); `TCW_PROJECT_<ID>` names a folder that is not a project (2.1); the answer differs from the folder an earlier lookup in this command found for `project_id` (2.9) | raises `ProjectGraphError` (exit 1) whose message names the file or folders, and adds the problem to the registry's problems, so a later `check()` lists it |

The "unknown" row narrows the design's rule that a reference into a missing
project is "could not check": that rule is kept for a project something names
but this machine does not have, and a project ID nothing names and nothing
finds is reported as a probable misspelling instead (Notes; Questions for
TCW-99). In this item the graph walk never meets it, since every ID the walk
looks up is named by a `projects:` entry; TCW-110's full identifiers can.

`ProjectGraphError` and its subclass `UnknownProject` are new `TcwError`
classes in `tcw/errors.py`, with the exit code of every other error, 1.
During the graph walk the same outcomes are recorded rather than raised: a
problem through `_problem`, and "not on this machine" as an
`UnreachableProject` (`tcw/store/base.py:124`), so that `tcw validate` lists
them all and commands that need a valid graph refuse through `require_valid`,
as today. A caller outside the walk gets the exception, and `tcw validate`
turns `ProjectGraphError` into an `error` finding and `Unreachable` into
`unresolved`.

2.13. **Cost.** One command opens one registry: `FsProjectRegistry.open(root)`
returns the same registry for the same active project root for the rest of
the command, so the graph, every answer of 2.11 (b) and every folder the
search reads are read once. `tcw serve` uses a fresh registry for each
request, so a change on disk is seen by the next request. A command that
writes a `tcw-config.yaml` or a manifest during its run (`tcw init`, the
`tcw config` editors) drops the shared registry after the write. Within a
registry, each folder of 2.4 is listed at most once, and each candidate's two
files are read at most once (AC 27).

### 3. `projects:` names IDs only

3.1. A `projects.<relation>.<id>` entry is empty (`lib:`, read by YAML as
null) or a mapping holding only `jira` (the delegation block, kept until
TCW-114 drops filing into another project). A string, or a `path` or
`repository` key, is a configuration problem whose message says the location
goes in `.tcw/tcw-manifest.yaml`, showing the entry to write there. An
empty mapping is accepted as well.

3.2. Reciprocity stays as it is, by ID: a child must name its parent and the
reverse (`_validate_reciprocity`, `tcw/store/project.py:878-938`). The checks
that two sides' locators agree, and `misdirected()`, go, because there are no
per-edge locators left to disagree. What they caught is now caught by 2.9:
two projects that look the same ID up and get different folders are reported
as a duplicate ID naming both folders.

3.3. Everything else about `projects:` is unchanged: at most one parent,
upstreams read-only, cycles reported, `extends` naming connected projects.

### 4. Git worktrees

Design 4.2 to 4.4 apply when the active project's root lies inside a linked
git worktree (`worktree_anchors`, `tcw/store/project.py:67-79`, which the
registry calls once, for the active project's root, `:229`). "The repository"
is that worktree's top folder; "the main checkout" is the main worktree's
root; a folder's "counterpart" is the folder at the same place below the main
checkout. 4.2 and 4.3 apply to every project whose root lies inside the
repository: the active project, and any other project of the same repository.

4.1. **Tracked files** are read from the worktree: configuration, the
committed manifest, every record. Nothing changes here.

4.2. **Personal files** (`tcw-config.local.yaml`, `tcw-manifest.local.yaml`)
are read from the worktree's `.tcw/` when the file is there, and otherwise
from the counterpart's `.tcw/`. A file borrowed this way is read as though it
sat in the worktree: its relative paths and `file:` bindings resolve from the
worktree's project root, and `TCW_CONFIG_DIR` names that root. Wherever TCW
names the file it read (`found.file` in Design 6.1, the file a problem is
recorded against, the file `tcw config show` gives as a value's source), it
names the main checkout's file, the one a person has to edit. A file is
personal by its name; TCW does not ask git whether it is tracked
(TCW-99 requirement 2).

4.3. **Outside the repository, from the main checkout.** A relative manifest
path that leads outside the repository is resolved from the counterpart of
the folder it was written in (as `_locator_path` does today,
`tcw/store/project.py:807-814`); an absolute path is read as written. For the
search: when `P`'s root is the repository's top folder, 2.4 lists the folders
next to the main checkout instead; 2.5 tests the worktree's own folders up to
the repository's top folder, then the folders enclosing the main checkout,
from the nearest outwards. The main checkout's root is not tested, because the
worktree's top folder, its counterpart, already was.

4.4. **One project, not two.** A folder found by any rule that lies in the
main checkout, and whose counterpart in the worktree holding the active
project is a project in the same repository, is replaced by that counterpart
(as `_worktree_copy` does today, `tcw/store/project.py:817-847`). Duplicates
(2.7, 2.9) are compared after this, so a project reached both in the worktree
and in its main checkout is never reported twice.

### 5. `tcw validate`

5.1. Every entry in the active project's two manifests is checked, whether or
not `projects:` names that ID:

| # | The entry's folder | Finding |
| - | ------------------ | ------- |
| a | not on this machine | `unresolved`, naming the ID, the path, and, when the entry gives one, the repository and `tcw project provision <id>` |
| b | there, but holds no `.tcw/tcw-config.yaml` and no 3.x `tcw-config.yaml` | `error`: not a TCW project |
| c | a 3.x project | `error`, TCW-106's `legacy_message` |
| d | its configuration's version cannot be read | `error`, `version_problem`'s message |
| e | declares another ID | `error`, naming both IDs |
| f | declares the ID given | nothing |

Each finding's `where` is the manifest's path within the project. An entry
whose folder is not on this machine never fails the run (TCW-99, "A related
project that is not on this machine": CI on one repository must pass).

An entry in `tcw-manifest.yaml` that does not decide on this machine, because
the personal manifest has an entry for the same ID or `TCW_PROJECT_<ID>`
places it, is still checked, but rows b to e are reported as `warning`, with
`(overridden on this machine by <the personal manifest's path, or the
variable>)` added. It is wrong for whoever has no override, so it is worth
saying, but it is not what this machine uses, so it does not fail the run
here. A run with `TCW_NO_PERSONAL_CONFIG=1`, as CI makes, reads no personal
manifest, so the committed entry decides and its problems are errors.

5.2. Manifest format problems (1.8), duplicates (2.7, 2.9) and candidates
that are `X` but unreadable (2.8) are errors, as graph problems are today
(`tcw/cli.py:422-426`).

5.3. The warning for a tracked personal manifest is 1.9's.

### 6. What a person sees

6.1. **`tcw projects list --json`** adds `found` to each row: for a project
on this machine other than the current one, `{"by": "manifest", "file":
"<absolute path of the manifest>"}`, `{"by": "variable", "name":
"TCW_PROJECT_<ID>"}` or `{"by": "search"}`; `null` for the current project and
for a project not on this machine. The plain listing is unchanged. This makes
the lookup visible to a person and to the criteria below, and answers part of
UC-8's known gap (only `tcw validate` says where a variable placed a project).

6.2. **A project not on this machine** is reported, wherever 3.x reports one
(`unreachable_project_note`, `tcw/store/fs.py:564-581`; `tcw validate`,
`tcw/cli.py:428-436`; `open_project`, `tcw/work/open.py:88-99`, whose
"`tcw provision` obtains it" at `:96-97` is no longer true after 6.3), as
either
`project '<id>' is not on this machine: <manifest> places it at <path>`,
followed, when the deciding entry gives a repository, by `, from
<repository>; fetch it with 'tcw project provision <id>'`; or, with no entry,
`project '<id>' is not on this machine: no manifest lists it, and no folder
next to <root> or enclosing it declares it; add it to
.tcw/tcw-manifest.yaml or .tcw/tcw-manifest.local.yaml`, where `<root>` is the
naming project's root. Exit codes do not change (5 from `tcw work show` of an
item in a missing project). `tcw project provision` exists only from TCW-115,
in the same release.

6.3. **`tcw provision` no longer fetches connected projects** (it still
fetches the declared component stores). `_provision_projects` and
`declared_connected_projects` (Problem 5) are removed rather than repointed,
because where a project is cloned changes in 4.0 (into the deciding manifest
entry's folder) and that is TCW-115's to build. Notes lists what TCW-115 must
rebuild.

6.4. **A store whose repository is a project already here** (`resolve_store`
rung 1.5, `_registry_checkout_root`, `tcw/store/fs.py:3157-3179`, asking
`checkout_of`, `tcw/store/project.py:306-344`) is matched against the
`repository` of the entries in every manifest the command has read, instead
of against `projects:` entries. For a matching entry whose ID this machine
has found, by whatever rule, the repository's folder is the found project's
folder with that entry's `subfolder` removed (the folder itself when the
entry has none). When the found folder does not end with the entry's
`subfolder`, that entry gives no answer, and the rung goes on to the next
matching entry, then to the provisioned copy, as it does today when nothing
matches.

## Abstraction litmus test

| Operation | Layer | Verdict |
| --- | --- | --- |
| Reading a manifest (Design 1) | deployment | Filesystem detail, by TCW-99's split: a store that is not a folder of files has no manifest. |
| Finding a project's folder from its ID (Design 2) | deployment | Filesystem detail. The model operation is unchanged: `ProjectRegistry.get(id)` answers with a `Project` whose `locator` is opaque (`tcw/store/base.py:112-121`); how the files store finds the folder behind it is its own business. `project_folder` (2.12) is on `FsProjectRegistry` alone, and returns a folder, which only the files store has. |
| One registry and one answer per command (Design 2.11, 2.13) | deployment | How the files store caches its own reads; another store caches its own way or not at all. |
| `projects:` naming IDs only (Design 3) | model | Passes: any store can record "this project's parent is `app`" without saying where `app` is. It removes a filesystem fact from the shared configuration. |
| Worktree rules (Design 4) | deployment | Filesystem and git detail, kept in the code that resolves projects, as `docs/lifecycle/abstraction.md` already places the git reads TCW makes. |
| Validating manifest entries (Design 5) | deployment | Checks files on disk. |
| `found` in `tcw projects list --json` (Design 6.1) | deployment | Reports which deployment rule answered; another store would report its own (or none). |

No backend operation is added or changed: the twelve operations in
`tcw/work/backend.py` are untouched, and the Jira backend behaves the same.
`ProjectRegistry` (`tcw/store/base.py:184`) keeps its interface;
`project_folder()` and `checkout_of()` are on `FsProjectRegistry` alone, and
`misdirected()` is removed.

## Use cases

- **UC-1 (a single project).** No manifest, no `projects:`: no lookup is
  made, no sibling folder is read, and output is unchanged (AC 21). `tcw
  init` writes one more ignore line.
- **UC-2 and UC-7 (a library others read).** Nothing about readers goes into
  the library: a reader finds it by its own manifest or by the search (a
  library cloned next to its reader needs no entry at all). The library's
  manifest is never read from a reader, since it is an upstream (Design
  2.10). A reader's local manifest may point at a read-only clone anywhere.
- **UC-3 (a monorepo).** The design's common case: the root's
  `tcw-manifest.yaml` lists each package by relative path; a package finds
  the root by the enclosing-folder search with no entry (AC 9); and the root
  never finds a package by searching downwards (AC 10). A package also finds
  a sibling package through its parent's manifest (Design 2.2 b), and gets
  the same answer whether the command runs in it or in the root (AC 25).
- **UC-4 (a planning workspace).** Code repositories cloned inside the
  workspace find it as an enclosing folder (Design 2.5); the workspace lists
  them in its manifest, since it cannot find them downwards. Stores kept in
  the workspace are untouched (Non-goals). The test fixtures use separate git
  repositories (checklist 10).
- **UC-5 (a shared Jira project).** Not affected: nothing here reads or
  writes Jira.
- **UC-6 (a project not on this machine).** A missing project is reported
  with its manifest entry's repository and the command that will fetch it
  (Design 6.2); `tcw validate` reports it as `unresolved`, never as an error
  (Design 5.1 a); commands that need only the project's own records keep
  working, as today. Fetching moves to TCW-115 (Design 6.3). An ID that
  nothing names and nothing finds is a probable misspelling, not a missing
  project (Design 2.12).
- **UC-8 (several families on one machine).** A retired copy of a family
  beside the live one makes the search fail with both folders named (Design
  2.7), and a manifest entry settles it (Design 2.3). `found` (Design 6.1)
  shows where each project came from, including through `TCW_PROJECT_<ID>`.
  The search's cost is bounded by 2.13: one listing of one folder, and two
  files per candidate, per command.
- **S-4 (worktrees, clones).** Design 4 throughout; a fresh clone in CI has
  no siblings and gets `unresolved`, not errors. A worktree of a dependency
  made next to it is a second match (Design 2.7) that one personal entry
  settles.
- **S-5 (personal configuration).** The personal manifest is a personal file:
  ignored by `TCW_NO_PERSONAL_CONFIG=1` (Design 1.10) and listed in
  `.tcw/.gitignore` (Design 1.9). The S-5 requirement "Another project's
  personal file is never read" holds for configuration; a manifest is not
  configuration, and Design 2.2 reads the personal manifests of the projects
  in the walk, because they are statements about this machine, which is the
  machine running the command. TCW-99's design already reads the naming
  project's personal manifest when that is not the active project
  (`design.md:173-174`). This departs from the requirement's wording; the user
  accepted it on 2026-10-22 (Questions for TCW-99), and TCW-117 rewords S-5.
- **S-9 (upgrades).** Manifests carry `tcw-version` and are refused by the
  same rule as configuration (Design 1.2), with a message that does not send
  a person to `tcw migrate` for a file 3.x never had (Design 1.8). A 3.x
  `projects:` entry with a locator is refused with a message saying where it
  goes now (Design 3.1).
- **S-10 (things TCW does not own).** The search never reads inside a
  project (Design 2.6), so a dependency's own `.tcw/` is never taken for a
  parent, child or sibling (AC 10).
- **S-11 (version control).** TCW reads git only to recognise a linked
  worktree and find its main checkout (Design 4), as today, and commits
  nothing. Personal files are recognised by name, not by asking git.

Checklist: 1 (where it looks) Design 2 and 4, with monorepo, workspace and
missing-project fixtures; 2 (whose things) only the active project's
`.tcw/.gitignore` is written; 3 (reading across projects) Design 2.2 reads
other projects' manifests and nothing else of theirs beyond what 3.x reads;
4 (backends) the litmus table; 5 (who is present) nothing asks a person;
6 (harness) the CLI carries everything; 7 (stopping halfway) the only write is
`tcw init`'s ignore lines, written whole; 8 (single project) UC-1 above;
9 (older and newer TCW) S-9 above; 10 (testing the setup claimed) the criteria
build sibling repositories, a monorepo, nested clones and a linked worktree.

## Acceptance criteria

Every fixture project is a TCW 4.0 project (TCW-106), and every manifest
starts with `tcw-version` at the running version, unless the criterion says
otherwise. "Lists `X` with `found` F" means `tcw projects list --json` run in
the named project prints a row for `X` with `present: true`, `path` the
absolute folder, and `found` F. A criterion that names
`FsProjectRegistry.project_folder` is checked by a test that calls the method
on `FsProjectRegistry.open(<the active project's root>)`.

1. **A manifest entry, both forms.** Projects `app` and `lib` side by side;
   `app`'s configuration has `projects: {upstream: {lib: }}` and its
   `.tcw/tcw-manifest.yaml` has `projects: {lib: ../lib}`. `app` lists `lib`
   with `found {"by": "manifest", "file": "<app>/.tcw/tcw-manifest.yaml"}`.
   With the entry written
   `lib: {path: ../lib, repository: https://example.invalid/lib.git#main}`,
   and again without `#main`, the result is the same.
2. **Manifest format problems.** Each of these in `app`'s
   `.tcw/tcw-manifest.yaml` makes `tcw projects list` exit 1, and `tcw
   validate` report an error whose `where` is `.tcw/tcw-manifest.yaml`: no
   `tcw-version` (the message contains `a manifest starts with 'tcw-version:`
   and does not contain `tcw migrate`); `tcw-version: 99.0.0` (TCW-106's
   upgrade message); a top-level key `other`; an entry key `ref`;
   `lib: /abs/lib`; `lib: ~/lib`; an entry mapping with no `path`;
   `repository: https://example.invalid/lib.git#` (empty branch);
   `repository: '#main'` (empty URL); `repository: x#a#b`; `subfolder: ../x`;
   `subfolder: apps/x` with `path: ../app`; `subfolder` without
   `repository`; an entry ID `Lib`.
3. **The personal manifest.** Adding `.tcw/tcw-manifest.local.yaml` with
   `projects: {lib: <absolute path of a second copy of lib>}` makes `app`
   list `lib` at that copy, with `found.file` the local manifest. The same
   with the path written `~/<the copy's path below the home folder>` (the
   test sets `HOME`). With `TCW_NO_PERSONAL_CONFIG=1` the committed entry is
   used again. With `TCW_NO_PERSONAL_CONFIG=true`, `tcw projects list` exits 1
   with the switch's configuration problem, as today.
4. **A manifest entry connects nothing.** `app`'s manifest also lists `other:
   ../other` (a real project), which `projects:` does not name; `tcw
   projects list` in `app` does not print `other`.
5. **An ancestor's manifest.** `<tmp>/shared` is the parent of
   `<tmp>/shared/desktop` (each names the other under `projects:`;
   `shared`'s manifest lists `desktop: desktop`). `desktop` has no manifest
   and declares `upstream: {core: }`; `core` is at `<tmp>/x/core`, which is
   neither next to `desktop` nor enclosing it; `shared`'s manifest lists
   `core: ../x/core`. `desktop` lists `shared` with `found {"by": "search"}`
   and `core` with `found.file` `shared`'s manifest, and `tcw validate` in
   `desktop` reports no finding naming `<tmp>/shared/.tcw`.
5a. **An upstream's manifest is not read.** `app` declares
   `upstream: {lib: , y: }`; `lib` is found next to `app`; only `lib`'s
   manifest lists `y`, and `y` is neither next to `app` nor enclosing it.
   `app` shows `y` with `present: false`.
6. **A descendant's manifest, and the order.** `<tmp>/docs` is the parent
   of `<tmp>/docs/shared` (reciprocal; `docs`'s manifest lists
   `shared: shared`); `docs` declares `upstream: {core: }`; `core` is at
   `<tmp>/x/core`, and only `shared`'s manifest lists it. `docs` lists
   `core` with `found.file` `shared`'s manifest. When `docs`'s own manifest
   also lists `core` at a different copy declaring `id: core`, `docs`'s entry
   is used.
7. **An entry decides; a project not here.** In AC 1, with the entry pointing
   at `../gone` (no such folder) while `../lib` declares `lib`: `tcw projects
   list --json` shows `lib` with `present: false` and `found: null`; `tcw
   validate` reports one `unresolved` finding naming `lib` and `../gone`, and
   exits 0 when nothing else is wrong. With the entry's `repository` set, the
   finding also names it and `tcw project provision lib`. With the committed
   entry giving a repository and a personal entry for `lib` giving only
   `../gone2`, the finding names `../gone2` and no repository (entries never
   merge). With no manifest at all and no `lib` anywhere,
   `tcw work show lib/<any folder>` exits 5 and its message contains
   `no manifest lists it, and no folder next to <app> or enclosing it
   declares it`.
8. **An entry that is wrong.** `tcw validate` in `app` reports an error naming
   the entry for each of: a folder that exists and is not a project; a folder
   holding only a 3.x root `tcw-config.yaml` (TCW-106's `legacy_message`); a
   folder whose `.tcw/tcw-config.yaml` has `tcw-version: 99.0.0`; a folder
   declaring `id: other` (both IDs named). The same holds for an entry no
   `projects:` relation names.
8a. **An overridden entry is a warning.** In AC 8's first case, with a
   personal manifest entry placing `lib` at a real `lib`, `tcw validate`
   reports the committed entry as a `warning` containing `overridden on this
   machine by` and the personal manifest's path, and exits 0. The same with
   `TCW_PROJECT_LIB` set instead, naming the variable. With
   `TCW_NO_PERSONAL_CONFIG=1` (and no variable) it is an error again.
9. **Next to, and enclosing.** With no manifests anywhere: `lib` next to `app`
   is found from `app` (AC 1's relation), with `found {"by": "search"}`. In a
   monorepo `app/` holding `app/packages/shared`, where `app` names
   `children: {shared: }` and its manifest lists `shared: packages/shared`,
   and `shared` names `parent: {app: }` and has no manifest, `shared` lists
   `app` with `found {"by": "search"}`. A parent two folders up
   (`app/a/b/pkg` naming `app`, listed in `app`'s manifest) is found the same
   way. A project in a folder next to an enclosing folder (`app/other` from
   `app/packages/shared`) is not found.
10. **Never downwards.** In that monorepo with no manifest, `tcw projects list
    --json` in `app` shows its child `shared` with `present: false`. A folder
    `app/node_modules/dep/.tcw/tcw-config.yaml` declaring the sought ID is
    never matched, from `app` or from `app/packages/shared`.
11. **Two matches.** `lib` and `lib-copy` next to `app`, both declaring `id:
    lib`, and no manifest entry: `tcw projects list` in `app` exits 1, and
    `tcw validate` reports an error naming both folders and
    `.tcw/tcw-manifest.local.yaml`. Adding a manifest entry for `lib` makes
    both commands succeed, with `lib` from the entry. The same error when one
    match is next to `app` and the other encloses it, and when `lib-copy` is a
    linked git worktree of `lib`.
12. **One folder per ID.** `app` and its child `lib` (reciprocal) each
    declare `upstream: {core: }`, and their manifests place `core` at two
    different folders, each declaring `id: core`: `tcw validate` reports the
    duplicate ID, naming both folders.
13. **Unreadable candidates.** A folder next to `app` whose
    `.tcw/tcw-config.yaml` is not valid YAML, and a folder next to `app` that
    the test makes unreadable (`chmod 000`, skipped where the test runs with
    permission to read it anyway), produce no finding, and `lib` is still
    found. A folder next to `app` declaring `id: lib` with
    `tcw-version: 99.0.0` is an error naming that folder and the upgrade; one
    holding only a 3.x root `tcw-config.yaml` with `id: lib` is an error with
    TCW-106's `legacy_message`.
14. **`TCW_PROJECT_<ID>` decides.** In AC 1, with `TCW_PROJECT_LIB` set to a
    second copy of `lib`, `app` lists `lib` there with `found {"by":
    "variable", "name": "TCW_PROJECT_LIB"}`, and `tcw validate` prints the
    override note it prints today. Set to a folder that is not a project, it
    is refused as today.
15. **`projects:` holds no location.** In `app`'s configuration, each of
    `upstream: {lib: ../lib}`, `upstream: {lib: {path: ../lib}}` and
    `upstream: {lib: {repository: {url: x}}}` is a configuration problem whose
    message names `.tcw/tcw-manifest.yaml`. `upstream: {lib: }`, `upstream:
    {lib: {}}` and `children: {lib: {jira: {project: LIB}}}` are accepted.
    No `tcw validate` message says a locator "does not point back" or "is
    declared at … which is not in this checkout".
16. **Worktree, tracked files.** A git repository holding `app` at its top,
    with `lib` next to the repository, and a linked worktree of it outside
    the main checkout. When the worktree's `.tcw/tcw-manifest.yaml` (changed
    on its branch) places `lib` at `../lib2` and the main checkout's at
    `../lib`, `tcw projects list --json` run in the worktree places `lib` at
    the folder next to the main checkout named `lib2`.
17. **Worktree, personal files.** In AC 16's setup, the main checkout's
    `.tcw/tcw-manifest.local.yaml` places `lib` at an absolute path `L`, and
    the worktree has none: the worktree uses `L` as written, and `found.file`
    is the main checkout's `.tcw/tcw-manifest.local.yaml`. Given its own
    personal manifest placing `lib` at `M`, it uses `M`, and `found.file` is
    the worktree's file. The main checkout's `.tcw/tcw-config.local.yaml`
    setting `user.name` is shown by `tcw config show` in the worktree, with
    the main checkout's file as its source; a `file: docs/x.md` stage binding
    in it composes the worktree's `docs/x.md`, and a command binding in it
    sees `TCW_CONFIG_DIR` set to the worktree's root.
18. **Worktree, outside the repository.** In AC 16's setup with no manifests:
    `lib` next to the main checkout is found from the worktree by the search;
    a project `ws` enclosing the main checkout, named by `app` as its parent,
    naming `app` back and listing it in its manifest (`app: app`), is found
    from the worktree, and `tcw validate` there reports no duplicate ID.
19. **Worktree, one project.** `lib` next to the main checkout is `app`'s
    parent, and `lib`'s manifest places `app` at `../app` (the main
    checkout). Run in the worktree, `tcw validate` reports no duplicate ID and
    no reciprocity problem, and `tcw projects list --json` shows `app`
    (current) at the worktree's folder.
20. **`tcw init` and the ignore rule.** In a git repository, `tcw init --id
    demo` writes `.tcw/.gitignore` holding the lines `/tcw-config.local.yaml`
    and `/tcw-manifest.local.yaml`, once each, and writes no manifest; run
    again it adds nothing; with a `.tcw/.gitignore` holding only the first
    line, it adds the second. Outside a git repository it writes no
    `.tcw/.gitignore`. `tcw validate` warns when
    `.tcw/tcw-manifest.local.yaml` is tracked.
21. **A single project pays nothing.** In a project with no manifest and no
    `projects:`, next to a folder whose `.tcw/tcw-config.yaml` is unreadable
    and a folder declaring the same ID as the project, `tcw work list`,
    `tcw projects list` and `tcw validate` print exactly what they print for
    the same project alone in an empty folder.
22. **Provisioning.** `tcw provision --dry-run` in AC 7's setup (entry with a
    repository, folder absent) lists only component stores and contacts
    nothing for `lib`; `tcw work show lib/<slug>` exits 5 with Design 6.2's
    message naming the repository and `tcw project provision lib`, and no
    message from either command tells the person to run `tcw provision` to
    obtain `lib`.
    A store whose `work.repository.url` equals a manifest entry's repository,
    for a project found here at `path` with `subfolder: apps/server`,
    resolves inside `path` with `apps/server` removed; when that project is
    found instead through `TCW_PROJECT_<ID>` at a folder that does not end
    with `apps/server`, the rung gives no answer and the store resolves as it
    would with no match. This repository's own `.tcw/.gitignore` holds
    `/tcw-manifest.local.yaml`.
23. The full suite, run as CI runs it (bare `pytest`), passes on `v4`.
24. **The function, for any ID.** In a project `app` with no `projects:` key:
    `FsProjectRegistry.project_folder("lib", <app>)` returns `lib`'s root
    when `lib` is next to `app`, and when only `app`'s manifest lists it at
    `../x/lib`; `project_folder("app", <app>)` returns `<app>`. With `app`'s
    manifest placing `lib` at `../gone`, the call raises `Unreachable`, whose
    message is Design 6.2's. `project_folder("nope", <app>)`, with nothing
    naming or holding `nope`, raises `UnknownProject`, exit 1, whose message
    contains `check the spelling`. With two folders next to `app` declaring
    `id: lib`, it raises `ProjectGraphError` naming both. When the graph has
    already found `core` at one folder and a later call from another found
    project, whose manifest places `core` at a second folder declaring
    `id: core`, is made, that call raises `ProjectGraphError` naming both
    folders, and `check()` afterwards lists the problem. A second identical
    call returns the same answer without reading any file (the test counts
    reads).
25. **One answer whichever project runs.** `app` holds `app/packages/a` and
    `app/plugins/k`; `a` names `parent: {app: }` and `children: {k: }`; `k`
    names `parent: {a: }`; `app` names `children: {a: }` and its manifest
    lists `a: packages/a` and `k: plugins/k`; neither `a` nor `k` has a
    manifest. `tcw projects list --json` run in `a` lists `k` at
    `<app>/plugins/k` with `found.file` `app`'s manifest, and `tcw validate`
    in `a` reports no `unresolved` finding for `k`; run in `app`, `k` is at
    the same folder.
26. **A worktree of the active project's repository, found from inside.** In
    AC 16's setup with the worktree made inside the main checkout's folder
    (`<main>/.worktrees/feature`), and `ws` enclosing the main checkout as in
    AC 18, `tcw validate` in the worktree reports no duplicate ID for `app`.
27. **Each candidate read once.** In AC 9's monorepo, during one `tcw
    validate` in `app/packages/shared`, the folder holding its root is listed
    once and each candidate's `.tcw/tcw-config.yaml` is opened at most once
    (the test counts the reads), and two `FsProjectRegistry.open(<root>)`
    calls in that command return the same registry.

### Coverage

| Design rule | Criteria |
| --- | --- |
| 1.1 two optional files | 1, 3, 21 |
| 1.2 format, `tcw-version`, `projects:` only, valid IDs | 2 |
| 1.3 entry forms and keys | 1, 2 |
| 1.4 `path`, relative from the root; absolute or `~` only in the local file | 1, 2, 3 |
| 1.5 `repository` and `#branch` | 1, 2, 7 |
| 1.6 `subfolder` | 2, 22 |
| 1.7 an entry connects nothing | 4 |
| 1.8 manifest problems are graph problems; manifest not used; the missing-version message | 2, 24 |
| 1.9 `tcw init` ignore line, only in a git repository; tracked warning | 20 |
| 1.10 `TCW_NO_PERSONAL_CONFIG`, and an invalid value | 3, 8a |
| 2.1 `TCW_PROJECT_<ID>` first | 14, 8a |
| 2.2 manifest order (a) own, (b) ancestors, (c) descendants; a project being looked up is skipped; entries never merge; personal manifests of the walk | 1, 3 (a); 5, 25 (b); 6 (c, and a before c); 5 (locating `shared` from `desktop` reaches `shared` as `desktop`'s ancestor, and the walk ends); 7 (no merge) |
| 2.3 an entry decides; a wrong one is a problem | 7, 8 |
| 2.4 folders next to the root, `.tcw` excluded | 5, 9, 13 |
| 2.5 enclosing folders, the folder itself only | 9 |
| 2.6 never downwards | 10 |
| 2.7 two matches, and the message naming the personal manifest | 11 |
| 2.8 unreadable candidates | 13 |
| 2.9 one folder per ID, including a later call | 12, 24 |
| 2.10 used for every `projects:` relation; upstream manifests not read | 1 (upstream), 5 (parent chain), 9 (parent and children), 10 (children); 5a (an upstream's manifest unread) |
| 2.11 parent before children; one answer per question | 25, 24 (the repeated call) |
| 2.12 the function: any ID, its four outcomes | 24 (found, not here, unknown, graph problem); 7, 22 (not-here message through a command) |
| 2.13 one registry per command; each candidate read once | 27 |
| 3.1 entries hold no location | 15 |
| 3.2 reciprocity by ID; locator checks gone; duplicates instead | 9, 12, 15, 19 |
| 3.3 the rest of `projects:` unchanged | n/a here: no rule changes (`_validate_upstreams`, `_validate_cycles`, the one-parent check, `tcw/store/project.py:940-959`, `:982-1020`, `:640-641`); the existing registry tests in `tests/test_project_registry.py` (for example `test_relative_layout_and_transitive_descendants`, `:89`) keep covering them, run by 23 |
| 4.1 tracked files from the worktree | 16 |
| 4.2 personal files fall back, read as the worktree's, named as the main checkout's | 17 |
| 4.3 outside the repository from the main checkout; an absolute path as written | 16, 18 (relative and the search); 17 (absolute) |
| 4.4 one project | 19, 26 |
| 5.1 a–f, and an overridden entry | 7 (a), 8 (b–e), 1 (f), 8a (overridden) |
| 5.2 errors for format, duplicates, candidates | 2, 11, 12, 13 |
| 5.3 tracked personal manifest | 20 |
| 6.1 `found`, including `null` | 1, 3, 7, 9, 14, 17 |
| 6.2 not-on-this-machine messages, with and without an entry; exit 5 | 7, 22 |
| 6.3 `tcw provision` fetches no project | 22 |
| 6.4 store rung 1.5 from the manifest, and no answer when the subfolder does not fit | 22 |

## Risks

- **Every connected-project test fixture writes locators under `projects:`**
  (Design 3.1 refuses them). The suite needs a mechanical change to move each
  into a manifest, which risks a test that silently stops testing what it did.
  The plan gives the tests one helper for writing a manifest, as TCW-106 did
  for configuration, and reads each failure rather than editing assertions.
  TCW-106's own AC 13a connects two projects by `../app` under `projects:`,
  and its test is rewritten to use a manifest entry.
- **The worktree rules are subtle and already were** (`_locator_path` and
  `_worktree_copy` carry a long history of fixes, GitHub #39 among them).
  Design 4 keeps their rules and widens where they apply; AC 16-19 and 26
  build a real linked worktree, never a simulated one.
- **The search reads folders TCW was never told about.** It reads only the
  two file names in Design 2.6, ignores what it cannot read (2.8), reads each
  at most once per command (2.13), and is never made for a project with no
  `projects:` entries (AC 21).
- **macOS may ask permission for a project kept directly in the home
  folder.** For a project at `~/proj`, 2.4 tests `~/Documents/.tcw/…`,
  `~/Desktop/.tcw/…` and `~/Downloads/.tcw/…`, which macOS protects; whether
  testing a path inside them makes the system ask the person for access is
  not verified. The implement stage checks it on a Mac. If it does ask, that
  is raised on TCW-99 before the search is changed, since skipping folders is
  a change to "Locating a project".
- **A worktree of a dependency next to it is a second match** (Design 2.7).
  `git worktree add ../lib-feature` is a common layout; the error names the
  personal manifest as the way to choose.
- **A parent found only through a distant manifest** is not found when the
  command runs in the child itself (Design 2.11 c). The child's own manifest
  settles it; TCW-108's parent links do not change it.
- **One registry per command** (Design 2.13) changes when a command sees a
  file it wrote. Commands that write configuration drop the registry; the
  suite's existing tests of `tcw init` and the configuration editors cover
  them.
- **`tcw provision` loses project fetching on `v4` until TCW-115.** Nothing is
  released in between; the message names the command that replaces it.
- **Reading another project's personal manifest** (Design 2.2) departs from the
  letter of S-5's requirement. The user accepted it on 2026-10-22, and
  TCW-117 rewords S-5; until then the use-case document and this spec
  disagree in wording.

## Notes

Decisions the design left to the spec, each with its reason:

- **The entry's shape** (Design 1.3-1.6): a path, or `path` with `repository`
  and `subfolder`. `path` is required because the manifest's job is to say
  where a project is; a repository alone would leave TCW-115 to invent a
  location, which is what 3.x's per-machine cache did and why a provisioned
  project was hard to find. `subfolder` carries 3.x's "folder within the
  repository" (TCW-99, "Versions and migration": address, branch, folder)
  without a second path syntax.
- **Entries never merge** (Design 2.2): one entry says everything about one
  project's location, so what a person reads in the deciding entry is all
  that is used.
- **The branch suffix** is `#<branch>` (Design 1.5), because `@` and `:` are
  already used inside the common git addresses.
- **`TCW_PROJECT_<ID>` stays** (Design 2.1), and TCW-109 adds no variable for
  a manifest path.
- **An entry pointing at a missing folder does not fall back to the search**
  (Design 2.3): what a person reads in the first manifest is what TCW uses,
  and the personal manifest exists to correct it.
- **Search matches are all collected** before deciding (Design 2.7), so a
  second clone is caught whether it sits beside the project or encloses it.
- **The lookup is a registry method** (Design 2.12), because its answer
  depends on the active project's worktree and on what the command has
  already found.
- **Parent before children, and one answer per question** (Design 2.11): the
  design's "children already found" leaves the order open, and without a
  fixed one the same family gave different folders from different projects.
- **A project ID nothing names and nothing finds is an error, not "could not
  check"** (Design 2.12): a typo in a `tcw://` address would otherwise pass
  `tcw validate` for ever, as a project that is simply not on this machine.
- **Personal files are recognised by name** in a worktree (Design 4.2), not by
  asking git, so TCW still does not depend on git's state.
- **`TCW_NO_PERSONAL_CONFIG=1` skips personal manifests** (Design 1.10).

Handoffs, which the dispatching session records on each ticket when this spec
is accepted:

- **TCW-108:** the parent links it adds replace "ancestors" and
  "descendants" in Design 2.2 and 2.10. With several parents, 2.2 (b) needs
  an order; the load order is the natural one. Design 2.11 (a), parent before
  children, carries over.
- **TCW-109:** `TCW_PROJECT_<ID>` stays, and there is no variable for a
  manifest path (Design 2.1).
- **TCW-110:** calls `FsProjectRegistry.project_folder` (Design 2.12) for
  every full identifier and `.path` address, handling all four outcomes, and
  provides no stand-in, since this item lands first.
- **TCW-115:** must rebuild what Design 6.3 removes: fetching a project's
  connected projects in turn, the rule that a project already here is not
  fetched again (`tcw/cli.py:256-275`), and the `--dry-run` listing. It
  clones into the deciding entry's folder with `subfolder` removed (Design
  1.6), and carries `found` (Design 6.1) into `tcw project list`.
- **TCW-116:** converts each 3.x `projects:` entry into a manifest entry: the
  locator becomes `path`; `repository.url` and `repository.ref` become
  `repository: <url>#<ref>`; `repository.path` (the folder within the
  repository) becomes `subfolder`; `repository.checkout`, when relative,
  becomes `path` when there is no locator. A 3.x entry that gives only a
  repository, which 3.x cloned into its per-machine cache
  (`tcw/store/checkouts.py:111-115`), has no `path`: `tcw migrate` must choose
  one, and on a machine holding the cached clone may write its absolute path
  into the personal manifest, since such clones are no longer found on `v4`.
  An entry that Design 2.4 or 2.5 would find anyway needs no manifest entry.
- **TCW-117** (guides, skills, use cases): `docs/use-cases.md` UC-1 and UC-3
  (the nearest `tcw-config.yaml`, `projects:` with paths), UC-6
  (`tcw provision`), UC-8 (its first requirement, and the known gap Design
  6.1 narrows), S-5 (the personal-file requirement means configuration, as
  the user accepted on 2026-10-22), S-10 (the search never looks inside
  a project); `docs/guide/multi-repo.md` and
  `skills/configure/references/projects.md` (locators under `projects:`).

Questions for TCW-99:

1. **Reading related projects' personal manifests** (Design 2.2) departs
   from `docs/use-cases.md` S-5, "Another project's personal file is never
   read". This spec reads them, for the reason in Use cases, S-5, and TCW-117
   rewords S-5 to say that the requirement is about configuration. Accepted
   by the user on 2026-10-22.
2. **A project ID nothing names** (Design 2.12) narrows the design's rule
   that `tcw validate` reports references into a missing project as "could
   not check": that holds for a project a manifest or a `projects:` entry
   names, and an ID that nothing names and the search does not find is an
   error suggesting a misspelling. Accepted by the user on 2026-10-22.
