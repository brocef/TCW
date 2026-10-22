# Spec — TCW 4.0: parent links, per-parent inheritance and the load order

Child 3 of 13 of TCW-99. It carries out these sections of the TCW-99 design
(`docs/work/TCW-99-…/design.md`): "The parent link", "Multiple parents, and
which value wins" (the load order), the part of "A related project that is not
on this machine" that concerns parents and children, and the parts of
"What any store must support" that sort these operations into the model and
the deployment layer.

**Order and blockers** (decided by the user on 2026-10-22). The children are
built on the `v4` branch in the order TCW-106, TCW-107, TCW-110, TCW-108,
TCW-111. This item is blocked by TCW-107 (manifests, and
`FsProjectRegistry.project_folder`, TCW-107 Design 2.12) and by TCW-110 (full
identifiers, which TCW-110 resolves for any project TCW-107's lookup can
locate, TCW-110 Design 6.1). It builds on TCW-106 (the `.tcw/` folder,
`tcw-version`, and the rule that project IDs are lower case). TCW-111 waits for
it. So when this item starts, TCW-110 has already removed the 3.x
`<project>/<folder>` form as input (TCW-110 Design 3.4) and replaced the
records gate's first-folder routing with full identifiers; and the tests
TCW-107 and TCW-110 wrote still name connected projects under the 3.x
`projects:` key, which this item converts (Design 3.5, AC 8).

File and line references are to commit `05d42988` on `v4`, where TCW-107,
TCW-110 and this item are unbuilt. TCW-107 rewrites much of
`tcw/store/project.py` and TCW-110 rewrites `tcw/work/gates.py` and the
reference code, so the plan re-checks every reference against what they
finally land. "TCW-107 Design n" and "TCW-110 Design n" refer to the numbered
rules of those items' specs.

Two terms used throughout:

- **The family** of a project is the project, its **ancestors** (its parents,
  their parents, and so on) and its **descendants** (the children it lists,
  the children they list, and so on). Never a sibling: a parent's other
  children are not in a child's family.
- **The load order** of a project is the list of the project and all its
  ancestors in the order their values are read: the farthest ancestors first,
  the project itself last, so that a later project's value replaces an
  earlier one's.

Every project ID in this spec's criteria is a valid one
(`validate_project_id`, `tcw/store/project.py:29-37`: lower case, and not one
of the reserved IDs `t`, `c`, `w` and `local`). The design's own examples use
single capital letters; Design 4.2 and 4.4 keep them, as abstract names, and
the criteria write each letter doubled in lower case (`A` is `aa`).

## Capability changes

- **New** `cli/name-a-projects-parents`: a project names its parents by ID, in
  order, under `parents:` in `.tcw/tcw-config.yaml`; each parent may say what
  it passes down (`inherit: all`, the default, `none`, or a list drawn from
  `taxonomy`, `capabilities` and `config`). The parent does not have to name
  the child.
- **New** `cli/list-a-projects-children`: a project may list its children by
  ID under `children:`, in its committed configuration, its personal file, or
  both (combined; the personal file can only add). A listed child must name
  the project back as a parent.
- **New** `cli/read-ancestors-in-one-load-order`: TCW reads a project's
  ancestors in one order, computed by C3 so that the last listed parent wins
  and every project's own listing order is kept when any order can keep it;
  otherwise depth-first with a warning; a loop is an error.
- **Changed** `cli/host-multiple-projects-in-one-repo`: relations are
  `parents:` and `children:`, not `projects:`; a project may have several
  parents.
- **Changed** `cli/list-connected-projects`: `tcw projects list` shows the
  parents in listing order and the children, and no upstream; `--json` adds
  each parent's `inherit`, whether a child was listed in the personal file,
  whether a project is read-only from here, and the load order with its
  warning.
- **Changed** `cli/validate-a-project`: reports a load-order warning, a loop,
  a listed child that does not name its parent, a parent, ancestor or listed
  child that is not on this machine as "could not check", and a problem in
  another project's `parents:` as "could not check".
- **Changed** `cli/rely-on-one-output-contract`: a new exit code, 7, for a
  command that needs something inherited that is not available here.
- **Changed** `cli/override-the-team-configuration-for-myself`: the project's
  personal file may add children; the user-wide file may not.
- **Changed** `cli/declare-a-connected-projects-home-repository` and
  `cli/reference-a-tcw-object`: no upstream projects.
- **Changed** `taxonomy/federate-shared-vocabulary` and
  `capabilities/federate`: until TCW-112, `extends` may name only an ancestor
  whose links pass that axis.
- **Changed** `work/delegate-a-work-item-to-another-project`: a project reached
  through a parent that does not list the child is read-only from here (the
  3.x upstream rule, carried over until TCW-114); a sibling can no longer be
  written into; the `jira` block for a project not on this machine is gone
  with `projects:`.
- **Changed** `web/editing`: the create form marks a project that is
  read-only from here, as the CLI decides it, instead of an upstream.
- **Removed** `cli/read-from-an-upstream-project`: an upstream is now an
  ordinary parent link the parent does not list.
- **Taxonomy:** new `parent-link`, `load-order`; changed `project`,
  `project-registry`, `personal-configuration`; removed `upstream-project`.

## Problem

1. **A project has at most one parent.** `projects.parent` may hold one entry
   (`tcw/store/project.py:640-641`), and everything built on it reads that one
   entry: `parent()` takes the first key (`:248-253`), `ancestors()` follows a
   single chain (`:279-287`), and the abstract interface declares a single
   `parent()` (`tcw/store/base.py:271`). TCW-99 "Multiple parents" lets a
   project build on several.
2. **Three mechanisms relate projects, and only one is a relationship.**
   `projects:` holds `parent`, `children` and `upstream` (`tcw/store/project.py:628-639`);
   an upstream is a one-sided, read-only connection whose own connections are
   not followed (`_visit`, `:537-539`; `_follow_edges`, `:543-552`; the
   read-only rule, `read_only_reason`, `:356-389`); and `extends` names, per
   axis, any project in the graph whose taxonomy or capabilities this one
   inherits (`_extends_ids`, `tcw/store/fs.py:904-933`;
   `_extended_component_stores`, `:991-1075`, which looks each ID up with
   `registry.get`, `:1013`). TCW-99 principle 2: one kind of link, meaning
   the same on every axis.
3. **Both sides must declare a parent and child**, and the check is
   symmetric (`_validate_reciprocity`, `tcw/store/project.py:878-938`). TCW-99
   "The parent link": the child's declaration alone gives it the inheritance,
   and a parent lists its children only if it wants the view, in either its
   committed or its personal file. Personal files cannot set any relation
   today (`PERSONAL_KEYS`, `tcw/config.py:45-52`; everything else is "a
   shared key", `:398-404`).
4. **The graph walk reaches siblings.** `_follow_edges` follows every
   project's children and its parent (`tcw/store/project.py:543-552`), so from
   a child it reaches the parent's other children and their descendants.
   TCW-99 "Choosing what a list or show command covers": a family never
   includes siblings.
5. **There is no load order.** Nothing in TCW computes an order over several
   ancestors, because there can be only one chain. Cycle detection walks
   `children` edges only (`_validate_cycles`, `tcw/store/project.py:982-1020`).
6. **A missing project that is inherited from gives the wrong outcome.** A
   project named in `extends` that is not on this machine stops every
   taxonomy or capabilities command, with exit 1 (a `ValueError` built from
   `unreachable_project_note`, `tcw/store/fs.py:1013-1022`), and makes `tcw
   validate` fail rather than report it as unchecked (`docs/use-cases.md`
   UC-6, "Known gaps"; S-6 notes the inconsistent exit codes). TCW-99 "A
   related project that is not on this machine" asks for an exit code of its
   own and "could not check" in `tcw validate`.
7. **Single-parent helpers nobody calls.** `child_projects`, `_routed`,
   `routed_children`, `routed_unreachable_children`, `parent_project`,
   `registered_parent`, `registered_children`, `unreachable_parent`,
   `unreachable_children`, `descendant_projects` and `registered_project_id`
   (`tcw/store/fs.py:413-543`, `:584-592`) have no caller in `tcw/`; three
   of them are reached only from tests (`tests/test_multiproject.py`,
   `tests/test_environment_hardness.py`, `tests/test_store_nodes.py`). Each
   assumes one parent.

## Goals

1. A project names its parents, in order, by ID, and each parent link says
   what it passes down.
2. A project may list its children, in its committed or its personal file;
   every listed child names it back.
3. A project's ancestors are read in one load order, defined exactly, which
   every axis that inherits uses, and which TCW shows.
4. A loop is an error; an order C3 cannot find is a warning, never a failure.
5. A parent that is not on this machine, or whose own links cannot be read,
   stops only a command that needs something it passes down, with exit code
   7; `tcw validate` reports it as "could not check".
6. `projects:` and the upstream relation are gone. (`extends` stays until
   TCW-112; see Non-goals.)
7. A single project (UC-1) needs no new configuration and pays nothing.

## Non-goals

- **What each axis does with what it inherits.** Inherited configuration
  (which keys cross the link, how values merge, `null`, environment
  overrides) is TCW-109's. Inherited taxonomy and capabilities, overrides by
  path, and the warning for two unrelated projects at one path are TCW-112's.
  This item gives both one thing: the list of projects whose content reaches
  a project for an axis, in load order (Design 5), and the rule they apply to
  it (Design 4.8).
- **Removing `extends`: TCW-112's, a recorded decision.** This item's request
  lists it, but the same request puts "what each axis does with inherited
  content" out of scope; TCW-112's request removes `taxonomy.extends` and
  `capabilities.extends` together with the mechanism that replaces them
  (design.md:453-455, "This replaces `taxonomy.extends`…"); and TCW-110, which
  lands before this item, keeps `extends` "as it is" until TCW-112 (TCW-110
  Non-goals, and Design 3.1 and 6.2, which read an inherited object through
  it). Removing it here would leave taxonomy and capabilities with no
  inheritance on `v4` between the two items. The duplicate in the two
  requests is an artifact of splitting the epic, and the lead confirmed
  TCW-112 keeps it on 2026-10-22. Until then `extends` is held to the parent
  links (Design 3.6).
- **Views across projects** (`--scope`, `--project`, mixed capability status,
  and showing an unavailable child in a view): TCW-113. This item provides
  `ancestors()`, `descendants()`, the declared children whether here or not,
  and the load order of any project the registry holds (Design 4.6).
- **`tcw project info`, `tcw project list` and `tcw project provision`**:
  TCW-115. This item puts what `info` shows (parents, children, load order,
  warning) into `tcw projects list --json` (Design 8.2), which TCW-115
  replaces.
- **The rule that only the active project changes anything**, and dropping
  `tcw work new --project` and `tcw work edit --blocks`: TCW-114. Until then
  the 3.x write rule is carried over in terms of parent links (Design 7).
- **Converting 3.x `projects:` and `extends`** in a user's project into
  `parents:`, `children:` and manifest entries: `tcw migrate`, TCW-116. Notes
  lists the mapping. (This repository's own test fixtures are converted here,
  Design 3.5.)
- **Guides and the wording of `docs/use-cases.md`**: TCW-117. Notes lists what
  they must change. The one skill file that lists exit codes is changed here
  (Design 8.3), because an agent reading it would misread exit 7.
- **Locating a project's folder**: TCW-107. This item changes only which
  relations the walk follows and the order of TCW-107 Design 2.2 (b) and (c)
  (Design 3.4).

## Design

Design 1, 2, 4, 5, 6.1-6.4, 6.6 and 7 are the model: every store implements
them. Design 3 is the model except where it names TCW-107's lookup, which is
the deployment layer. Design 6.5 and 8 are what the files store and the CLI
show.

### 1. Parents

1.1. **`parents:`** is an optional top-level key of `.tcw/tcw-config.yaml`:
a list, in order. Each entry is a project ID written as a string, or a
mapping with `id` (required) and `inherit` (optional). No other key is
accepted in an entry.

```yaml
parents:
  - id: workspace
    inherit: none          # view only
  - id: core
    inherit: [taxonomy]    # vocabulary only
  - app                    # everything
```

1.2. **`inherit`** is `all` (the default when the key is absent, and always
for a string entry), `none`, or a non-empty list of distinct values drawn
from `taxonomy`, `capabilities` and `config`, in any order. A list naming all
three means `all`. An empty list is refused with a message saying to write
`inherit: none`, so that each meaning has one spelling.

1.3. **Problems**, each naming `.tcw/tcw-config.yaml` and the key
(`parents[2].inherit`): `parents` not a list; an entry that is neither a
string nor a mapping; a mapping without `id`; an ID that is not a valid
project ID (`validate_project_id`, `tcw/store/project.py:29-37`); an unknown
key in an entry; an `inherit` value that is not `all`, `none` or such a list;
an unknown or repeated axis; `[]`; the same parent listed twice; a project
listing itself (reported as a loop, Design 4.7); a project naming one project
both as a parent and as a child. **In the active project's own
configuration** each one is a configuration problem of the project graph:
like every graph problem today, it makes `tcw validate` fail and every command
that requires a valid graph refuse with exit 1 (`require_valid`,
`tcw/store/project.py:453-456`). **In another project's configuration** (an
ancestor's, a descendant's, or a descendant's other parent's) it is not a
problem of the active project: Design 6.6 says what happens instead. A loop is
a graph problem wherever it is (Design 4.7).

1.4. **Only the committed file names parents.** `parents` is not added to
the personal allowlist, so a personal file (user-wide or
`tcw-config.local.yaml`) that sets it is refused as "a shared key; a personal
file cannot set it", as today (`tcw/config.py:398-404`).

1.5. **The parent need not name the child.** A parent that does not list a
child is a one-sided link: the child inherits from it and it cannot see the
child. That is what a 3.x upstream was.

### 2. Children

2.1. **`children:`** is an optional top-level key: a list of project IDs, as
strings. It may be written in the active project's `.tcw/tcw-config.yaml`,
in its `.tcw/tcw-config.local.yaml`, or in both. The project's children are
the committed list followed by the personal list's IDs that the committed one
does not hold, each in its file's order. An ID in both files is listed once;
a duplicate within one file is a problem; an entry that is not a valid
project ID is a problem; a project listing itself as a child is a problem.

2.2. **The personal file can only add.** There is no syntax for removing a
committed child, and `children: null` in a personal file is refused by the
existing rule that null has no meaning there (`tcw/config.py:378-381`).
`children` is allowed in `tcw-config.local.yaml` only: the user-wide file
(`user_config_path`, read by `_personal_layers`, `tcw/config.py:676-693`)
applies to every project, so a child listed there would be claimed by every
project the person works in; setting it there is a problem naming that file.
(`children` cannot simply join `PERSONAL_KEYS`, which applies to both
personal files; the plan says how the two files are told apart.)

2.3. **The personal list follows the personal-file rules.**
`TCW_NO_PERSONAL_CONFIG=1` drops it (`_personal_layers`,
`tcw/config.py:681-682`). In a linked git worktree with no personal file of
its own, the main checkout's is read (TCW-107 Design 4.2).

2.4. **Only the active project's personal file is read for children.** A
descendant's personal children are not part of the family seen from its
ancestors. Reason: `docs/use-cases.md` S-5 says another project's personal
file is never read, and TCW-99 "The parent link" wants two engineers on the
same commit to get the same totals; a descendant's personal list would make
the totals depend on files nobody else has. (TCW-107 reads other projects'
personal *manifests*, which say where projects are on this machine; a
personal child list says what the family is, which is configuration.)

2.5. **A listed child must name the parent back** among its `parents:`,
whether it is listed in the committed or the personal file. If it does not,
that is a problem recorded against the parent's file that lists it, naming
both projects: `'<child>' is listed as a child of '<parent>' but does not
name '<parent>' among its parents`. The lists checked are the active
project's (both files) and its descendants' committed lists (Design 2.4),
because those are the lists the walk follows (Design 3.1). An ancestor's
`children:` is never followed or checked from below: it is read only as a
list of names, for TCW-107 Design 2.12's "not on this machine" row (Design
3.4), and an entry in it that is not a valid ID names nothing. So a child of
an ancestor that is not on this machine produces no finding from here. A
listed child that is not on this machine, or whose own `parents:` cannot be
read (Design 6.6), cannot be checked; it is reported as Design 6.5 says.

2.6. **Personal children change only what one person sees.** They add rows
to `tcw projects list`, descendants to `descendants()`, and the name-back
checks of 2.5. They change no outcome of a gate or of `tcw validate`'s
errors for someone without them, beyond the checks on the children they add:
in particular the records gate routes a `capabilities.yaml` entry by its full
identifier (TCW-110, which no longer asks `declared_child_ids()`), so a child
listed only in one person's file does not change what `tcw work advance`
decides (AC 32). This item must not bring back a gate decision that depends
on `declared_child_ids()`.

### 3. The family the registry holds

3.1. **The walk** starts at the active project and follows declared links
only:

- **up:** its parents in listing order, and for each parent, that parent's
  own parents, depth-first, before the next parent;
- **down:** after every ancestor has been found, its listed children in
  order (Design 2.1), then theirs, breadth-first.

It never follows an ancestor's children (so a sibling is never reached) or a
descendant's parents other than the one it came from. A project reached twice
is read once.

3.2. **What the registry answers** (`ProjectRegistry`, `tcw/store/base.py:184`,
and `FsProjectRegistry`):

```python
AXES = ("taxonomy", "capabilities", "config")

@dataclass(frozen=True)
class ParentLink:
    id: str
    inherit: frozenset[str]          # a subset of AXES; all three for `all`

@dataclass(frozen=True)
class LoadOrder:
    ids: tuple[str, ...]             # farthest first, the project itself last
    missing: tuple[str, ...]         # the IDs in `ids` not on this machine
    unreadable: tuple[str, ...]      # the IDs in `ids` whose own links could not be read (Design 6.6)
    warning: str | None              # Design 4.5's warning, or None

class ProjectRegistry(ABC):
    def parents(self, project_id=None) -> list[ParentLink]      # declared, in order
    def declared_child_ids(self, project_id=None) -> list[str]  # Design 2.1, here or not
    def children(self, project_id=None) -> list[Project]        # those on this machine
    def ancestors(self, project_id=None) -> list[Project]       # load order without the project, those here
    def descendants(self, project_id=None) -> list[Project]     # breadth-first, those here
    def load_order(self, project_id=None) -> LoadOrder          # Design 4
    def sources(self, axis, project_id=None) -> list[Project]   # Design 5; raises InheritedUnavailable
```

`parents` is abstract, beside the existing abstract `get`, `children`,
`ancestors`, `descendants`, `projects`, `check` and `unreachable`
(`tcw/store/base.py:267-310`). `declared_child_ids` already exists
(`tcw/store/base.py:207-210`); its meaning now includes personal children.
The docstrings of `descendants` (which said depth-first, `:283-285`) and
`projects` (which said siblings are included, `:287-296`) change with their
meaning. `parents` answers for any project a load order reaches, including a
descendant's other parents found on demand (Design 4.6), and records a
project not on this machine as missing rather than answering for it. The
computation of Design 4 and the filtering of Design 5 are one store-neutral
function in `tcw/store/base.py`, given each project's parent links and
whether they are known; `load_order` and `sources` call it, because the order
is a property of the declared links and not of how a store keeps them.
`parent()` and `declared_parent_id()` go (a project may have several
parents), as do `declared_upstream_ids()` (`tcw/store/base.py:212-220`) and
`entry()` (`tcw/store/project.py:391-399`), whose callers in
`tcw/work/open.py:95`, `:131`, `:145` and `:172` ask `unreachable_project`
instead (the plan re-checks these callers after TCW-110).

3.3. **`get(id)` answers for the family only**: the active project, its
ancestors and its descendants. A project found to compute a descendant's load
order (Design 4.6), or found while locating something for a project outside
the family (Design 3.4), is not added to `get`, `ancestors`, `descendants` or
`projects`.

3.4. **TCW-107's lookup with parent links** (the handoff recorded on this
ticket). TCW-107 Design 2.2 and 2.10 read "ancestors" and "descendants" as
the 3.x chain; with parent links:

- (b) becomes: the manifests of the asking project's ancestors found so far,
  in the **reverse of its load order** computed over the projects found so
  far, without the asking project itself. For a single chain that is
  TCW-107's "nearest first"; with several parents it consults first the
  ancestor whose values would win (Design 4.8), so a location and a value
  are decided by the same precedence. When C3 finds no order over the
  projects found so far, Design 4.4's depth-first order over them is used,
  and no warning is made for it (the warning belongs to the complete order,
  Design 4.5).
- (c) becomes: the manifests of the asking project's **descendants found so
  far**: every project already found from which a chain of parent links
  leads up to the asking project, whether or not the asking project lists
  it. They are taken nearest first (fewest links), and among projects at the
  same distance in the order the walk found them, which puts listed children
  in the order of Design 2.1. Counting unlisted descendants is what keeps a
  reader's manifests in use when a project it names has parents of its own:
  from `app: [lib]`, `lib` looks up its own parent `core`, and `app`, which
  names `lib`, is a descendant of `lib` already found, so `app`'s manifests
  are consulted for `core` (AC 29). Under 3.x the same came from
  reciprocity: a parent always listed its child. This reads TCW-99's "the
  children already found" (design.md:174-175) as the projects that name the
  asking project as a parent, which is what a child is in 4.0, where
  listing is optional (Design 1.5).
- 2.10: the lookup is used for every parent and every listed child the walk
  follows. The sentence about upstream manifests goes, since there is no
  upstream; a former upstream is a parent, and its manifest counts as an
  ancestor's.
- 2.11 (a): every parent, in listing order and each with its own ancestors
  (Design 3.1), is found before any child is looked up.
- 2.12, the bullet "When `P` is not in the graph, the registry reads `P`'s
  configuration to learn its parent and children": `P`'s ancestors are found
  by Design 3.1's upward walk from `P`, all of them, since (b) needs `P`'s
  load order; `P`'s `children:` are not followed, and its descendants for
  (c) are the projects already found that reach it by parent links. Reason:
  following them would read projects that are neither in the family nor
  named by the command, and their problems would appear in commands that do
  not concern them. Projects found this way are not added to the family
  (Design 3.3), and a problem in their links is Design 6.6's.
- 2.12, the "not on this machine" and "unknown" rows: "named by a `projects:`
  entry of a project in that walk" becomes "named by a `parents:` or
  `children:` entry of a project whose manifests the lookup consulted". That
  includes an ancestor's `children:` read as names (Design 2.5), so a sibling
  that is not on this machine is "not on this machine", not "unknown". The
  same condition replaces "a manifest or `projects:` entry" in TCW-110
  Design 6.1's table, in TCW-110's code.

3.5. **`projects:` is refused.** A `.tcw/tcw-config.yaml` holding a top-level
`projects` key has a graph problem: `'projects' is not a TCW 4.0 key: name
parents under 'parents:' and children under 'children:', by ID, and say where
projects are in .tcw/tcw-manifest.yaml`. This replaces TCW-107 Design 3,
which keeps `projects:` (IDs only) until this item. The upstream relation,
its read-only bookkeeping (`_upstream_only`, `_upstream_declarers`,
`_read_as_upstream`, `_validate_upstreams`, `tcw/store/project.py:203-209`,
`:863-876`, `:940-959`) and the `jira` block of a `projects:` entry
(`ConnectedProject.jira`, `tcw/store/base.py:717-720`) go with it. **The
fixtures that TCW-107 and TCW-110 leave on `projects:` are converted here**,
by the TCW-116 mapping in Notes: a `projects.parent` entry becomes a
`parents:` entry, `projects.children` becomes `children:` (with the child
naming the parent), and a `projects.upstream` entry becomes a parent whose
`inherit` lists the axes `extends` takes from it, or `none`. In particular
TCW-110's cross-project fixtures (`app` naming `core` under
`projects.upstream`, no `extends`: TCW-110 AC 13 and its plan's Step 7)
become `parents: [{id: core, inherit: none}]`.

3.6. **Until TCW-112, `extends` is held to the parent links.** An `extends`
ID for axis `x` must be a project that passes `x` to the project (Design
5.1), other than the project itself: an ancestor reached by links whose
`inherit` all include `x`. Any other ID (a project outside the family, a
descendant, or an ancestor behind a link that leaves `x` out) is a
configuration problem with the message `'<id>' is in <x>.extends, but '<P>'
does not inherit its <x> from it: name it under 'parents:' with an 'inherit'
that includes <x>`. It is raised where today's "not reachable through
projects" refusal is (`tcw/store/fs.py:1013-1022`, exit 1), refused by
`tcw taxonomy|capabilities extends add` (`:1972`, `:2727`) with the same
message and the exit code it gives an unregistered project today (2, a
`UsageError`, `:1974`), and reported by `tcw validate` as an error. Reason: `extends` and
`inherit` would otherwise disagree, so that `parents: [{id: ws, inherit:
none}]` with `taxonomy.extends: [ws]` would still inherit `ws`'s taxonomy,
the opposite of what the link says; and an `extends` naming a descendant
would be inheritance upwards, which no 4.0 link expresses. The 4.0 form of a
3.x `extends` naming an upstream, a sibling or a descendant is to make that
project a parent passing the axis. An `extends` ID that passes `x` and is not
on this machine raises Design 6.2's error (Design 6.3).

3.7. **A sibling's objects stay readable by full identifier.** TCW-110, which
lands first, reads an object of any project TCW-107's lookup can locate, not
only one in the family (TCW-110 Design 6.1, 6.2), and no longer accepts the
3.x `<project>/<folder>` form (TCW-110 Design 3.4). So `tcw work show
b.work/<folder>` run in `a`, where `a` and `b` are both children of `ws`,
keeps working once the walk stops reaching siblings: `b` is located through
the manifests of `a` and its ancestors, or by the search. When `b` is not on
this machine it is "not on this machine" (exit 5), not "unknown", because
`ws`'s `children:` names it (Design 3.4). What does stop is writing into a
sibling (Design 7.1).

### 4. The load order

4.1. **Definition.** For a project `P` whose parents, in listing order, are
`p1 … pn`, write `R(P)` for the order with the winner first:

```
R(P) = [P] + merge(R(pn), …, R(p1), [pn, …, p1])
```

`merge` repeatedly takes, from the lists in the order given, the first list's
first project that is not in the rest (all but the first project) of any
list, appends it to the result and removes it from every list, until every
list is empty. When no list's first project qualifies, the merge fails. A
project with no parents has `R(P) = [P]`. The **load order** is `R(P)`
reversed. This is C3, the method Python uses to order a class's parents,
applied to the parent lists reversed so that the last listed parent wins.

4.2. **The design's examples are normative** (TCW-99 "Multiple parents").
The capital letters are abstract names; the criteria write them as
lower-case IDs (AC 10-14).

| Parents | Load order |
| --- | --- |
| C: [A, B]; F: [D, E]; G: [C, F] | G: A, B, C, D, E, F, G |
| B parent of C and D; A parent of B; E: [C, D] | E: A, B, C, D, E |
| X: [B]; Y: [A, B]; Z: [X, Y] | Z: A, B, X, Y, Z (depth-first would give B, X, A, Y, Z) |

4.3. **A project reached twice is placed once**, after all its own ancestors.
This follows from 4.1 and is stated because it is what "loaded once" means.

4.4. **Fallback.** When any merge made while computing `R(P)` fails, the
whole load order of `P` is the depth-first order instead: go through `P`'s
parents in listing order; for each, first place its own ancestors by the same
rule, then the parent, skipping any project already placed; `P` goes last.
The design's two shapes:

| Parents | Load order (depth-first) |
| --- | --- |
| X: [A, B]; Y: [B, A]; Z: [X, Y] | Z: A, B, X, Y, Z |
| C parent of D; E: [D, C] | E: C, D, E |

4.5. **The warning.** A fallback order carries one warning, exactly:

```
load order: no order keeps every project's own order of parents (at '<Q>': '<h1>', '<h2>', … cannot be placed); using depth-first order <id>, <id>, …, <P>; to choose a value yourself, set it in '<P>'
```

where `<Q>` is the project whose merge failed (the first one, when several
would) and `<h…>` are the distinct first projects left in its lists when it
failed, each once, in the order of the lists. It is shown by `tcw validate`,
as a `warning` finding at the active project's `.tcw/tcw-config.yaml`, and by
`tcw projects list --json` (Design 8.2), and later by `tcw project info`
(TCW-115). No other command prints it: the fix usually lies in projects the
active one cannot change, and repeating it on every command would be noise
the person cannot act on there.

4.6. **The load order of any project the registry holds.** `load_order(id)`
answers for the active project, an ancestor or a descendant. A descendant may
have parents outside the family (its other parents); they are found when its
load order is asked for, through TCW-107's lookup from that descendant, and
are not added to the family (Design 3.3). TCW-113 needs this to show a
capability as each descendant sees it.

4.7. **A loop is an error.** If a project is its own ancestor, through the
`parents:` links of any projects the registry has read (the walk's, and those
read for Design 3.4 and 4.6), there is no load order. It is a graph problem
recorded against the configuration of the first project in the loop that the
registry read: `loop in parents: <a> -> <b> -> … -> <a>`, where `<a>` is that
project and each next one is a parent of the one before it. A loop among
descendants (a child listing, as its child, a project above it, which names
it as a parent) is found the same way, from their `parents:`. `tcw validate`
fails, and every command that requires a valid graph refuses with exit 1,
whichever project the loop is in: no order exists at all, so there is nothing
to fall back to. This replaces `_validate_cycles`
(`tcw/store/project.py:982-1020`), which walks `children` edges only.

4.8. **Which value wins.** For an axis, the value of a key or the object at a
path comes from the last project in that axis's order (Design 5.2) that
**declares** it. A project that only passes an inherited value along declares
nothing, so it never puts an earlier value back: in 4.2's second example, if
C declares `P` and D does not, E gets C's `P`. Each project's **own**
declarations are folded over the order, never a parent's resolved view. This
is the rule TCW-109 applies to configuration (with its merging of mappings
and `null`) and TCW-112 applies to taxonomy and capabilities (objects by
path); this item defines the order it runs over. No shared helper is built
here, because the two items fold different things (Notes).

### 5. Per-parent inheritance: which projects pass an axis

5.1. **A project `Q` passes axis `x` to `P`** when `Q` is `P`, or when some
chain of parent links from `P` up to `Q` has `x` in the `inherit` of every
link on it. So `inherit: none` on a link passes nothing through it, including
what lies above it; a link with `inherit: [taxonomy]` passes the parent's
taxonomy, which includes what the parent inherits by taxonomy-carrying links
of its own.

5.2. **`sources(x)`** is the load order (Design 4) keeping only the projects
that pass `x` to the project, in the same order, ending with the project
itself. One load order serves every axis: when C3 found an order, any part of
it keeps every listing order among the projects it holds, so filtering never
breaks an order a project declared.

5.3. **`inherit` changes nothing else.** It does not change the walk, the
family, the load order, the views of TCW-113 or the name-back rule. It is one
link and one viewing rule; only what flows down varies (TCW-99 "The parent
link"). (`extends` is held to it until TCW-112, Design 3.6.)

### 6. A parent, ancestor or child that is not available

6.1. **Commands that need only the project's own records still work**:
listing, reading and moving its own items, reading its own taxonomy and
capabilities (apart from the pre-existing gap of 6.3). A project that is not
on this machine is recorded by the walk as not here (TCW-107 Design 2.12's
"not on this machine"), and a project whose own links cannot be read is
recorded as Design 6.6 says; neither is a graph problem, so `require_valid`
passes.

6.2. **A command that needs something inherited stops** when `sources(x)`
meets a project that would pass `x` (Design 5.1) and is either not on this
machine or in `unreadable` (Design 6.6). It raises `InheritedUnavailable`, a
new `TcwError` in `tcw/errors.py` whose exit code is the new
`INHERITED_UNAVAILABLE = 7` in `tcw/exit.py`, with one of these messages:

```
'<P>' inherits its <axis> from project '<M>', which is not on this machine: <TCW-107 Design 6.2's sentence for M, from after its first colon>
'<P>' inherits its <axis> through project '<M>', whose parents could not be read: <the problem, naming M's .tcw/tcw-config.yaml and the key>
```

TCW-107 Design 6.2's sentence, from after its colon, names where the deciding
manifest entry places `M` and, when the entry gives a repository,
`tcw project provision <M>`; with no entry it says to add one. So the message
says "not on this machine" once. A project that passes nothing for `x` (it
sits behind an `inherit` that leaves `x` out) does not stop the command,
whatever its state. Exit 7 is distinct from 5, which stays "Jira, or a
project whose object the command needs, could not be reached" (TCW-110
Design 6.3).

6.3. **Until TCW-112, `extends` is what needs inherited content.** An
`extends` ID that passes the axis (Design 3.6) and is not on this machine, or
is in `unreadable`, raises 6.2's error (with `<axis>` the store's axis)
instead of today's `ValueError` (`tcw/store/fs.py:1013-1022`), so `tcw
taxonomy` and `tcw capabilities` commands exit 7, not 1. That every such
command stops, including one that reads only the project's own entries, is
the existing UC-6 gap: the store opens what it extends when it opens, and
TCW-112 replaces that mechanism.

6.4. **The load order with a project missing or unreadable.** A project not
on this machine, or in `unreadable`, is placed by the links that name it, as
a project with no parents (its own are unknown); the order is complete only
when `missing` and `unreadable` are both empty. Its position can change once
it is fetched or fixed, if its own parents are also reached another way;
Risks names it.

6.5. **`tcw validate`** reports, each as an `unresolved` finding (which never
fails the run) at the file that names the project:

| # | Not available | Message |
| - | ------------- | ------- |
| a | a parent or another ancestor not on this machine | TCW-107 Design 6.2's, followed by `; could not check what it passes down to '<P>' or the projects above it` |
| b | a listed child not on this machine | TCW-107 Design 6.2's, followed by `; could not check that it names '<P>' as a parent` |
| c | a project `extends` names (6.3), not on this machine | TCW-107 Design 6.2's, followed by `; could not check the <axis> inherited from it` |
| d | a project whose own links could not be read (6.6) | `could not check what '<M>' passes down to '<P>': <the problem>` for an ancestor; `could not check that '<M>' names '<P>' as a parent: <the problem>` for a listed child |

For (c), `tcw validate` catches `InheritedUnavailable` raised while it checks
a store and records this finding instead of failing. **One finding per
project**, however many routes reach it and whichever rows apply. When the
deciding manifest entry of a missing project is in the active project's own
manifests, TCW-107 Design 5.1 (a) already reports it, and TCW-107's plan
drops the walk's finding for it (its choice 2); this item keeps that rule and
appends the row's text above to 5.1 (a)'s message, so that one finding says
both where the project should be and what could not be checked.

6.6. **A problem in another project's links does not stop the active
project** (decided by the user on 2026-10-22, UC-2). When a Design 1.3
problem other than a loop is found in the `parents:` of a project other than
the active one (an ancestor, a descendant, or a project read for Design 3.4
or 4.6):

- it is not a graph problem of the active project, so `require_valid` passes
  and commands that need only the project's own records work;
- that project's own parents are unknown: it is placed in the load order as
  a project with no parents and listed in `LoadOrder.unreadable` (6.4), and
  nothing above it is looked up through it;
- `sources(x)` raises `InheritedUnavailable` (exit 7, 6.2's second message)
  when that project passes `x`, because what reaches it from above is
  unknown; a command that needs nothing it passes is unaffected;
- `tcw validate` reports row (d) of 6.5, and fails only in that project
  itself, where the problem is the active project's own (1.3).

A problem in a descendant's committed `children:` list, and a name-back
failure in it (2.5), stay graph problems, as reciprocity failures are today:
the active project lists that descendant, and those lists decide the family
it shows. An ancestor's `children:` is never checked from below (2.5).

### 7. Writing into another project, until TCW-114

7.1. **The 3.x write rule in terms of parent links.** A project is writable
from the active project (by `tcw work new --project` and `tcw work edit
--blocks`, `tcw/work/open.py:131-136`) when it is reached through links that
both sides declare: a parent that lists the child, or a listed child (which
always names the parent back, Design 2.5). Any other project in the family,
reached across a parent link the parent does not list, is read-only, refused
with exit 3 and the message `'<X>' is read-only from here: '<parent>' does
not list '<child>' among its children`. In 3.x that project was an upstream
and was read-only the same way (`read_only_reason`,
`tcw/store/project.py:356-389`; `tcw/store/base.py:222-232`), so UC-2's and
UC-7's requirement holds on `v4` until TCW-114 makes every project but the
active one read-only.

**A sibling can no longer be written into.** The 3.x rule walked both parent
and child links (`read_only_reason`, `tcw/store/project.py:371-381`) over a
graph that held siblings (`_follow_edges`, `:543-552`), so `tcw work new
--project <sibling>` and `tcw work edit --blocks` into a sibling were
allowed. A sibling is now outside the family, so both are refused with exit
3, as for a project nothing here declares (`_check_declared`,
`tcw/work/open.py:131`). This is an accepted loss, since TCW-114 removes both
commands: until then, run the command in the shared parent that lists both,
or in the sibling itself.

7.2. **The `jira` block is gone.** Filing into a project that is not on this
machine through a `jira` block in its `projects:` entry
(`tcw/work/open.py:172-176`) has no place left to be declared. Such a filing
is refused as for any project not on this machine (exit 3). TCW-99 drops this
case anyway ("Only the active project can be changed": accepted loss).

### 8. What a person sees

8.1. **`tcw projects list`** prints the active project, then its parents in
listing order, then its children in the order of Design 2.1, each once,
whether on this machine or not (`connected`, `tcw/projects_cli.py:21-50`). No
upstream rows, and no ancestors beyond the parents. The plain listing stays
one ID per line, as today; a listed child that is not on this machine is
named, with the command that fetches it, by `tcw validate` (6.5 b) and by
`--json` (`present: false`), and shown as unavailable in views by TCW-113.

8.2. **`tcw projects list --json`** prints
`{"schema": 1, "projects": [...], "load-order": [...], "load-order-complete": <bool>, "load-order-warning": <string or null>}`.
Each row keeps `id`, `relation` (`current`, `parent` or `child`), `present`,
`path` and TCW-107's `found`. A parent row adds `inherit`, the list of axes it
passes in the order of `AXES` (`[]` for `none`). A child row adds `personal`,
true when only the personal file lists it. Every row but the current one adds
`read-only`: true when Design 7.1 refuses writing into it from here, false
when it allows it, and null for a project not on this machine (7.2 refuses
it for that reason instead). `load-order` is `load_order().ids`,
`load-order-complete` is true when `missing` and `unreadable` are empty, and
`load-order-warning` is Design 4.5's warning or null.

8.3. **Exit code 7** is added everywhere the codes are listed or pinned:
`tcw/exit.py` (`:8-14`) and `tcw/errors.py`; the `EXIT_CODES` text that
`tcw --help` prints (`tcw/cli_help.py:38-49`); the documented table
(`docs/guide/cli.md:140-148`); the capability that lists the codes
(`docs/capabilities/cli/rely-on-one-output-contract/description.md`, rows at
`:33-34`, table from `:27`); the exit-code table agents read
(`skills/work/references/commands.md:33-41`); and the tests that pin 0-6
(`tests/test_cli_help_standard.py:151`, `range(7)`;
`tests/work/test_errors.py:18`, the tuple of codes). Its meaning, in each:
"something this project inherits is not available here: a project it
inherits from is not on this machine, or that project's parent links could
not be read". Rows 3 and 5 of the guide's table lose "upstream" and "no
`jira` block".

8.4. **The single-parent helpers of Problem 7 are removed**, with the tests
that reach only them; behavior a remaining test covers through them is kept
by a test of `ancestors()`, `descendants()` or `children()`.

8.5. **The web app shows what the CLI decides.** `tcw serve`'s project answer
(`_projects`, `tcw/serve/work.py:143-148`) replaces `upstream`, which would
now always be false, with `readOnly`, the row's `read-only` of 8.2. The
client changes with it: `TConnectedProject` (`web/client/src/model/types.ts:30-31`),
the create form's label (`web/client/src/ui/work-forms.tsx:587-588`, which
becomes `<id> (read-only from here)`), the fixture
(`web/client/src/test-fixtures.ts:57`) and the form's tests
(`web/client/src/ui/work-forms.test.tsx:204`, `:229`). The bundle is rebuilt
(`pnpm build`, into `tcw/serve/dist`). Reason: TCW-99 principle 4, the web
app shows only what the CLI shows, and without this the form would offer a
one-sided parent as an ordinary target that the server then refuses.

## Abstraction litmus test

| Operation | Layer | Verdict |
| --- | --- | --- |
| Declaring parents, with `inherit` (Design 1) | model | Passes: any store can record "this project's parents are `workspace` (passing nothing) and `core` (passing taxonomy)", in order, by ID. |
| Listing children, committed and personal, and the name-back rule (Design 2) | model | Passes: an ordered set of IDs and a per-person addition to it; a store that keeps no personal settings has no personal children. Reading them from `tcw-config.local.yaml` is how the files store keeps a personal setting. |
| `parents`, `children`, `ancestors`, `descendants` (Design 3.2) | model | Passes: questions about declared links; `parent()` is replaced because "the parent" no longer exists, not because of storage. |
| The walk, and TCW-107's lookup order (Design 3.1, 3.4) | deployment, where it finds folders | Which links are followed is model; finding each project's folder and reading its manifests is TCW-107's files-store detail. |
| Load order, fallback and loop (Design 4) | model | Passes: computed from `parents()` alone, in the base class, by any store. |
| `sources(axis)`, `InheritedUnavailable` and unreadable links (Design 5, 6.2, 6.6) | model | Passes: "declared but not available here" is a state a tracker-backed registry reaches too (`UnreachableProject`, `tcw/store/base.py:124-133`), and so is "declared, but its own declaration is malformed". |
| `extends` held to the links (Design 3.6) | model | Passes: a membership test against `sources(axis)`. |
| The write rule until TCW-114 (Design 7) | model | Passes: decided from which side declares each link. |
| `tcw projects list --json` fields, `tcw validate` findings, the web app's flag (Design 6.5, 8) | CLI | Presentation of model answers. |

No work backend operation is added or changed: the twelve operations in
`tcw/work/backend.py` are untouched, and the Jira backend behaves the same.

## Use cases

- **UC-1 (a single project).** No `parents:` or `children:`: the walk reads
  nothing else, the load order is the project alone, no warning, nothing is
  looked up, and every command's output is unchanged; only `tcw projects list
  --json` gains three keys describing a one-project load order (AC 27).
- **UC-2 (a library others read).** The reader names the library as a parent,
  with `inherit` saying what it takes; the library names nothing about it.
  From the reader the library stays read-only (Design 7.1) and its children
  are not followed (Design 3.1). The library's own parents are now followed,
  because they are the reader's ancestors and pass content down every level
  (design.md:404-406), and they are located through the reader's manifests
  as well as the library's (Design 3.4 c, AC 29). **UC-2's requirement holds:**
  a problem in the library's links does not stop the reader (Design 6.6, AC
  31); only a command that needs what the library passes down stops, with
  exit 7, and a library parent that is not on the reader's machine is "could
  not check". (The requirement's wording names `projects:`; TCW-117 renames
  that key throughout.)
- **UC-3 (a monorepo).** Each package names the root as a parent; the root
  lists its packages. A package that also builds on a library names it as a
  second parent with `inherit: [taxonomy]`. Several levels and two routes to
  one project are the load order's examples (AC 10, 11). A package does not
  see its sibling packages (AC 9), reads their items by full identifier
  (Design 3.7), and can no longer create items in them (Design 7.1, AC 21).
  Inheriting different axes from different parents is `inherit` (AC 17).
- **UC-4 (a planning workspace).** The workspace is a parent of the code
  repository's root with `inherit: none`, and lists it as a child, so it sees
  it and passes nothing down. A fresh clone of the code repository without the
  workspace works, and its `tcw validate` exits 0 with the workspace as
  "could not check" (AC 26, two git repositories). Stores kept in the
  workspace are unchanged (TCW-110's).
- **UC-5 (a shared Jira project).** `inherit: [config]` is where a child will
  take its parent's Jira settings; what crosses is TCW-109's. Filing through a
  `jira` block goes (Design 7.2).
- **UC-6 (a project not on this machine).** Design 6: own records keep
  working; a command needing what a missing project passes down exits 7,
  naming it and how to fetch it; `tcw validate` says "could not check". The
  UC-6 gap that a missing `extends` project gives exit 1 and fails `tcw
  validate` is narrowed: exit 7, and "could not check" in `tcw validate`; the
  gap that it stops reading the project's own entries stays until TCW-112.
- **UC-7 (a public library, private readers).** The reader's link to the
  library is one-sided, so nothing about the reader enters the library. A
  maintainer who wants the top-down view lists private readers in the
  library's untracked `tcw-config.local.yaml`, with their paths in the
  personal manifest (TCW-107), and nothing is committed (AC 5). A malformed
  `parents:` in the public library does not stop its private readers (AC 31).
- **UC-8 (several families on one machine).** The family is only what
  `parents:` and `children:` declare (Design 3.1); TCW-107's search only
  locates a project named by one of them, or by a full identifier.
- **S-1, S-2, S-3.** Nothing asks a person; the CLI carries everything, so
  Claude Code, Codex and Pi see the same; no backend operation changes. The
  one agent-facing exit-code table is updated (Design 8.3).
- **S-4 (worktrees, clones).** A personal child list in the main checkout is
  used by a worktree without one (Design 2.3, TCW-107 Design 4.2). A fresh
  clone in CI reports missing parents as "could not check" and passes.
- **S-5 (personal configuration).** The personal file may add children, never
  remove them or name parents; the user-wide file may not list children;
  `TCW_NO_PERSONAL_CONFIG=1` drops them; another project's personal file is
  never read for children (Design 2.2-2.4).
- **S-6 (unattended runs).** Exit code 7 means one thing: something inherited
  is not available here. A script can tell it from 5 (a project or Jira out
  of reach).
- **S-7 (several people).** Personal children only add, so two people on one
  commit see the same committed family, and no gate decision depends on them
  (Design 2.6, AC 32).
- **S-8 (partial failure).** No command here writes more than one file; a
  missing project is reported, not half-read.
- **S-9 (upgrades).** `projects:` in a 4.0 file is refused with a message
  naming its replacements (Design 3.5). A 3.x file is TCW-106's (refused,
  naming `tcw migrate`). Old code reading new files is not a constraint.
- **S-10 (things TCW does not own).** Nothing is found by scanning; the walk
  follows declared IDs, located by TCW-107's search, which never looks
  downwards.
- **S-11 (version control).** No git reads or writes are added.

Checklist: 1 (where it looks) Design 3, through TCW-107's lookup; tested with
separate repositories (AC 26). 2 (whose things) Design 7: the write rule
carries 3.x's read-only upstream over to one-sided parents, and siblings are
no longer writable. 3 (reading across projects) Design 3-6, several levels
(AC 10-12), a missing project (AC 18-20), an unreadable one (AC 31), UC-5 left
to TCW-109. 4 (backends) the litmus table; Jira unaffected. 5 (who is present)
nothing asks. 6 (harness) CLI only, and the agent-facing exit-code table. 7
(stopping halfway) nothing multi-step. 8 (single project) AC 27. 9 (older and
newer) Design 3.5. 10 (testing the setup claimed) AC 26 builds two git
repositories; the rest are folders of separate projects.

## Acceptance criteria

Every fixture project is a TCW 4.0 project with a valid, lower-case ID;
another project's location is given by a manifest entry or found by TCW-107's
search, as the criterion says or as the fixture's layout makes obvious.
"Rows" means the `projects` list of `tcw projects list --json` run in the
named project; "the load order of P" means its `load-order`, and must equal
`FsProjectRegistry.open(<P>).load_order().ids`. A criterion naming
`sources`, `load_order`, `get` or `descendants` is checked by a test calling
it on `FsProjectRegistry.open(<the active project's root>)`.

1. **Parent entries.** `app` with `parents: [core]`, with
   `parents: [{id: core}]` and with `parents: [{id: core, inherit: all}]`:
   the row for `core` has `relation: "parent"` and
   `inherit: ["taxonomy", "capabilities", "config"]`. With `inherit: none` it
   is `[]`; with `inherit: [config, taxonomy]` it is `["taxonomy", "config"]`;
   with `inherit: [taxonomy, capabilities, config]` it is all three.
2. **Parent problems in the active project.** Each of these in `app`'s
   `.tcw/tcw-config.yaml` makes `tcw projects list` exit 1 and `tcw validate`
   report an error whose `where` is `.tcw/tcw-config.yaml`: `parents: core`;
   an entry `5`; `{inherit: none}` (no `id`); `{id: Core}`; `{id: core, path:
   ../core}`; `inherit: some`; `inherit: [taxonomy, taxonomy]`; `inherit:
   [work]`; `inherit: []` (the message contains `inherit: none`); `parents:
   [core, core]`; `children: [core]` together with `parents: [core]`;
   `children: [app]`. (The same problems in a parent's file are AC 31.)
3. **Parents only in the committed file.** `parents: [core]` in `app`'s
   `.tcw/tcw-config.local.yaml`, and again in the user-wide file, makes `tcw
   validate` and `tcw work list` exit 1 with a problem naming that file and
   containing `a shared key; a personal file cannot set it`.
4. **A one-sided parent.** `app` names `core`; `core` lists no children. In
   `app`, `tcw validate` reports no finding about `core` naming `app`, and the
   row for `core` is present. In `core`, `tcw projects list` prints only
   `core`.
5. **Children, committed and personal.** `ws` has `children: [a]` in
   `.tcw/tcw-config.yaml` and `children: [b, a]` in
   `.tcw/tcw-config.local.yaml`; `a` and `b` each have `parents: [ws]`.
   `tcw projects list` in `ws` prints `ws`, `a`, `b`, one per line; the row
   for `a` has `personal: false`, for `b` `personal: true`. With
   `TCW_NO_PERSONAL_CONFIG=1`, it prints `ws`, `a`. `children: [b]` in the
   user-wide file instead makes `tcw validate` exit 1 with a problem naming
   that file; `children: [a, a]` in either file, and `children: null` in the
   personal file (`null has no meaning in a personal file`), make `tcw
   validate` exit 1.
6. **A listed child must name its parent.** `ws` lists `a` in its committed
   file; `a` has no `parents:`. `tcw validate` in `ws` exits 1 with an error
   containing `'a' is listed as a child of 'ws' but does not name 'ws' among
   its parents`, and `tcw projects list` exits 1. The same when `a` is listed
   only in the personal file. With `a`'s folder absent, `tcw validate` exits 0
   and reports one `unresolved` finding naming `a` and containing `could not
   check that it names 'ws' as a parent`; the row for `a` has
   `present: false`.
7. **Another project's personal children are not read.** In AC 5's layout
   with `a`'s own `.tcw/tcw-config.local.yaml` listing `children: [kid]` and
   `kid` naming `a`: `descendants()` from `ws` is `[a, b]` (IDs), and from `a`
   is `[kid]`.
8. **`projects:` is refused.** `projects: {parent: {ws: }}` in `a`'s
   configuration makes `tcw projects list` exit 1, and `tcw validate` report
   an error containing `parents:` and `tcw-manifest.yaml`. No test or fixture
   under `tests/` writes a `projects:` key except to check this refusal,
   including those TCW-107 and TCW-110 wrote, and
   `grep -rn "declared_upstream_ids\|_upstream_only\|def entry" tcw/` finds
   nothing.
9. **Never a sibling.** `ws` lists `a` and `b`; both name `ws`. In `a`:
   `tcw projects list` prints `a`, `ws`; `get("b")` is None;
   `descendants()` is `[]`; `ancestors()` is `[ws]`. `tcw work show
   b.work/<a folder in b's work store>` run in `a` prints `b`'s item (Design
   3.7); with `b`'s folder absent, it exits 5 with a message containing
   `project 'b' is not on this machine`, not `no project with ID 'b'`, and
   `tcw validate` in `a` reports no finding naming `b`.
10. **Several levels.** `cc: [aa, bb]`, `ff: [dd, ee]`, `gg: [cc, ff]`: the
    load order of `gg` is `aa, bb, cc, dd, ee, ff, gg`, with no warning.
11. **Reached twice, placed once.** `aa` parent of `bb`; `bb` parent of `cc`
    and `dd`; `ee: [cc, dd]`: the load order of `ee` is `aa, bb, cc, dd, ee`.
12. **C3, not depth-first.** `xx: [bb]`, `yy: [aa, bb]`, `zz: [xx, yy]`: the
    load order of `zz` is `aa, bb, xx, yy, zz`, `load-order-warning` is null,
    and `tcw validate` in `zz` reports no warning about the load order.
13. **Fallback: parents that disagree.** `xx: [aa, bb]`, `yy: [bb, aa]`,
    `zz: [xx, yy]`: the load order of `zz` is `aa, bb, xx, yy, zz`; `tcw
    validate` in `zz` exits 0 with a `warning` whose `where` is
    `.tcw/tcw-config.yaml` and whose message is exactly `load order: no order
    keeps every project's own order of parents (at 'zz': 'aa', 'bb' cannot be
    placed); using depth-first order aa, bb, xx, yy, zz; to choose a value
    yourself, set it in 'zz'`; `load-order-warning` is the same text; `tcw
    work list` in `zz` prints nothing on standard error.
14. **Fallback: a child listed before its own parent.** `dd: [cc]`,
    `ee: [dd, cc]`: the load order of `ee` is `cc, dd, ee`, and the warning
    contains `(at 'ee': 'cc', 'dd' cannot be placed)`, each name once.
15. **Loops.** `aa: [bb]`, `bb: [aa]`: in `aa`, `tcw projects list` and `tcw
    work list` exit 1, and `tcw validate` exits 1 with an error containing
    `loop in parents: aa -> bb -> aa`. `aa: [aa]` is reported as `loop in
    parents: aa -> aa`. A loop among descendants that breaks no Design 1.3
    rule: `ws` lists `cc`, `cc` lists `dd`, `dd` lists `ee`, `ee` lists `cc`;
    `cc: [ws, ee]`, `dd: [cc]`, `ee: [dd]`. `tcw validate` in `ws` exits 1
    with an error containing `loop in parents: cc -> ee -> dd -> cc`, and
    reports no problem of a project named both as a parent and as a child.
16. **A descendant's load order.** `ws` lists `a`; `a: [core, ws]`; `core`
    lists no children. From `ws`: `load_order("a").ids` is `(core, ws, a)`;
    `get("core")` is None; `descendants()` is `[a]`; the rows of `tcw projects
    list` in `ws` do not include `core`.
17. **Per-axis sources.** `gg: [{id: ww, inherit: none}, {id: ll, inherit:
    [taxonomy]}]`; `ll: [kk]`; `ww: [vv]`. The load order of `gg` is
    `vv, ww, kk, ll, gg`. `sources("taxonomy")` is `[kk, ll, gg]`;
    `sources("config")` and `sources("capabilities")` are `[gg]`. With
    `ll: [{id: kk, inherit: [config]}]` instead, `sources("taxonomy")` is
    `[ll, gg]` and `sources("config")` is `[gg]`.
18. **A missing parent that passes nothing.** `app: [{id: ws, inherit: none},
    core]`, `core` here, `ws` not on this machine: `tcw work list` in `app`
    exits 0; `sources("taxonomy")` is `[core, app]` and raises nothing; the
    load order of `app` is `ws, core, app` with `load-order-complete: false`;
    `tcw validate` exits 0 and reports one `unresolved` finding naming `ws` and
    containing `could not check what it passes down to 'app'`.
19. **A missing parent that is needed, and `extends`.** `app: [core]`, `core`
    not on this machine. `sources("taxonomy")` raises `InheritedUnavailable`,
    whose `code` is 7 and whose message contains `'app' inherits its taxonomy
    from project 'core', which is not on this machine:` and contains `not on
    this machine` once. With `app`'s manifest entry for `core` giving a
    repository, the message contains `tcw project provision core`. With
    `taxonomy.extends: [core]` in `app` as well: `tcw taxonomy list` in `app`
    exits 7 with that message, and `tcw validate` exits 0 when nothing else
    is wrong, reporting one `unresolved` finding naming `core` and containing
    `could not check the taxonomy inherited from it`, and no error. `extends`
    held to the links, each making `tcw taxonomy list` exit 1 and `tcw
    validate` report an error, with a message containing `does not inherit
    its taxonomy from it` and `parents:`: `taxonomy.extends: [other]`, where
    `other` is not in `app`'s family; `app: [{id: core, inherit: none}]` with
    `core` here and `taxonomy.extends: [core]`; `ws` listing `kid`, `kid:
    [ws]`, and `taxonomy.extends: [kid]` in `ws`. `tcw taxonomy extends add
    other` in `app` exits 2 with the same message and leaves the file
    unchanged.
20. **A missing grandparent.** `app: [lib]`, `lib: [core]`, `core` not on this
    machine: `sources("capabilities")` from `app` raises `InheritedUnavailable`
    naming `core`; the load order of `app` is `core, lib, app` with
    `load-order-complete: false`; `tcw validate` in `app` reports exactly one
    `unresolved` finding naming `core`.
21. **Writing into another project, until TCW-114.** `app: [lib, ws]`; `ws`
    lists `app`; `lib` lists no children; both have work stores with nothing
    uncommitted. In `app`, `tcw work new --project lib 'x'` exits 3 with a
    message containing `read-only` and `'lib' does not list 'app'`, and `lib`'s
    work store is unchanged; `tcw work new --project ws 'x'` succeeds. With
    `lib: [top]` and `top` listing `lib`, `tcw work new --project top 'x'` in
    `app` also exits 3. With `ws` also listing `sib`, which names `ws`, `tcw
    work new --project sib 'x'` in `app` exits 3 and `sib`'s work store is
    unchanged, while the same command run in `ws` succeeds. With `ws`'s
    folder absent, `tcw work new --project ws 'x'` exits 3 and names no
    `jira` block.
22. **TCW-107's lookup order with several parents.** `gg: [cc, ff]`; `gg`
    lists `xx`, which names `gg`; neither `gg`'s manifest nor the search finds
    `xx`; `cc`'s and `ff`'s manifests each place `xx` at a different folder,
    both declaring `id: xx`. The row for `xx` in `gg` has `found.file` `ff`'s
    manifest. With `xx` placed only in the manifest of `aa`, where `cc: [aa]`,
    the row for `xx` has `found.file` `aa`'s manifest (every ancestor is found
    before any child is looked up).
23. **The plain listing.** `gg: [cc, ff]`, `gg` lists `xx` and `yy`, all
    present: `tcw projects list` in `gg` prints `gg`, `cc`, `ff`, `xx`, `yy`.
    The JSON has exactly the top-level keys `schema`, `projects`,
    `load-order`, `load-order-complete` and `load-order-warning`.
24. **A worktree uses the main checkout's personal children.** A git
    repository holding `ws`, whose main checkout's
    `.tcw/tcw-config.local.yaml` lists `children: [b]`, and a linked worktree
    with no personal file: `tcw projects list` in the worktree prints `b` with
    `personal: true`.
25. **Exit code 7 is documented everywhere the codes are.** `tcw/exit.py`
    defines `INHERITED_UNAVAILABLE = 7`; `InheritedUnavailable.code` is 7;
    `tcw --help` lists a line for 7 (the test at
    `tests/test_cli_help_standard.py` checks `range(8)`);
    `tests/work/test_errors.py` pins the tuple `(0, …, 7)`;
    `docs/guide/cli.md`,
    `docs/capabilities/cli/rely-on-one-output-contract/description.md` and
    `skills/work/references/commands.md` each have a row for 7; none of those
    three tables' rows 3 or 5 contain `upstream` or `jira` block.
26. **A planning workspace, in two repositories.** Repository A holds `ws`,
    which lists `app`; repository B is cloned inside A (and ignored by it) and
    holds `app: [{id: ws, inherit: none}]`. In `ws`, the rows include `app`,
    present. A separate clone of repository B alone: `tcw validate` there
    exits 0 with one `unresolved` finding for `ws`; `sources("config")` is
    `[app]`; `tcw work list` exits 0.
27. **A single project pays nothing.** A project with no `parents:` or
    `children:`, next to another project: `tcw work list`, `tcw projects list`
    and `tcw validate` print what they print for the same project alone in an
    empty folder; `tcw projects list --json` has one row, `load-order` equal
    to the project's ID alone, `load-order-complete: true` and
    `load-order-warning: null`; no other project's configuration file is
    opened (the test counts reads).
28. **The single-parent helpers are gone.** None of the names in Problem 7,
    nor `ProjectRegistry.parent`, `declared_parent_id` or
    `declared_upstream_ids`, is defined in `tcw/`.
29. **A one-sided parent's own parents are found through the reader's
    manifests.** `app: [lib]`, `lib: [core]`, `lib` lists no children; `core`
    is at a folder that is neither next to `app` or `lib` nor encloses
    either, and is placed only by an entry in `app`'s
    `.tcw/tcw-manifest.local.yaml`. From `app`: `get("core")`'s root is that
    folder; the load order is `core, lib, app` with `load-order-complete:
    true`; `tcw validate` reports no finding about `core`. The same with the
    entry in `app`'s `.tcw/tcw-manifest.yaml` instead.
30. **Descendants' manifests, in order.** `ws` lists `a`, `b` and `kid`, all
    naming `ws`; `ws`'s manifest places `a` and `b`; nothing in `ws`'s
    manifest and nothing the search finds places `kid`; `a`'s and `b`'s
    manifests each place `kid` at a different folder, both declaring `id:
    kid`. The row for `kid` in `ws` has `found.file` `a`'s manifest. With
    `ws` listing `b`, `a`, `kid` instead, it is `b`'s manifest.
31. **A problem in a parent's links does not stop the reader.** `app: [lib]`,
    `lib`'s `.tcw/tcw-config.yaml` holding `parents: core` (not a list). In
    `app`: `tcw projects list` and `tcw work list` exit 0; `tcw validate`
    exits 0 with one `unresolved` finding naming `lib` and containing `could
    not check what 'lib' passes down to 'app'`; the load order is `lib, app`
    with `load-order-complete: false`; `sources("taxonomy")` raises
    `InheritedUnavailable`, code 7, with a message containing `'app' inherits
    its taxonomy through project 'lib', whose parents could not be read`.
    With `app: [{id: lib, inherit: none}]` instead, `sources("taxonomy")` is
    `[app]` and raises nothing. In `lib` itself, `tcw projects list` exits 1.
    With `lib: [top]` and `top: [lib]` instead (a loop), `tcw work list` in
    `app` exits 1.
32. **Personal children do not change a gate.** `ws` keeps a capabilities
    ledger; `b` names `ws`, keeps a ledger holding `x`, and is listed only in
    `ws`'s `.tcw/tcw-config.local.yaml`; an item of `ws` has a
    `capabilities.yaml` with `changed: [b.capabilities/x]`. `tcw work advance
    <item> --dry-run` to the stage that runs the records gate gives the same
    exit code and the same standard error with and without
    `TCW_NO_PERSONAL_CONFIG=1`.
33. **The web app marks a read-only project.** In AC 21's layout, the
    project answer of `tcw serve` for `app` has rows for `lib` with
    `readOnly: true` and for `ws` with `readOnly: false`, and no row has an
    `upstream` key; `tcw projects list --json` in `app` gives the same values
    as `read-only`; a client test renders the create form's target for
    `lib` as `lib (read-only from here)`.
34. The full suite, run as CI runs it (bare `pytest`), passes on `v4`, and
    so do `pnpm test`, `pnpm typecheck` and `pnpm lint` in `web/client`.

### Coverage

| Design rule | Criteria |
| --- | --- |
| 1.1 `parents:` list, string or mapping, order | 1, 10, 23 |
| 1.2 `inherit` values, default, `[]` refused | 1, 2 |
| 1.3 parent problems: in the active project, exit 1; in another, 6.6 | 2, 15 (self-loop), 31 |
| 1.4 parents only in the committed file | 3 |
| 1.5 one-sided parent | 4, 21, 29 |
| 2.1 `children:` in either file, combined, duplicates, self | 2 (self), 5, 23 |
| 2.2 personal can only add; not in the user-wide file | 5 |
| 2.3 `TCW_NO_PERSONAL_CONFIG`; worktree fallback | 5, 24 |
| 2.4 another project's personal children not read | 7 |
| 2.5 a listed child names its parent; which lists are checked; one not here | 6, 9 (an ancestor's other child gives no finding), 15 |
| 2.6 personal children change no gate | 32 |
| 3.1 the walk: up depth-first, then down breadth-first; never siblings | 9, 22 |
| 3.2 the interface; `parent()`, `entry()`, `declared_upstream_ids()` gone | 9, 16, 17, 28 |
| 3.3 `get` answers for the family only | 9, 16, 29 |
| 3.4 TCW-107's lookup: (b) reverse load order; (c) descendants found so far, listed or not; 2.10; 2.11 (a); the 2.12 bullet for a project outside the graph; the 2.12 rows | 22 (b and 2.11 a); 30 (c, listing order); 29 (c, an unlisted descendant); 16 (the 2.12 bullet: a descendant's other parent found from it, not added to the family); 9, 18, 20 and 6 (the 2.12 rows: an ID named only by `parents:` or `children:`, including an ancestor's `children:`, and not here is "not on this machine", never "unknown") |
| 3.5 `projects:` refused; upstream and `jira` block gone; earlier items' fixtures converted | 8, 21 |
| 3.6 `extends` held to the links | 19 |
| 3.7 a sibling's objects readable by full identifier | 9 |
| 4.1 C3 definition | 10, 11, 12 |
| 4.2 the design's examples | 10, 11, 12 |
| 4.3 reached twice, placed once | 11 |
| 4.4 depth-first fallback | 13, 14 |
| 4.5 the warning, its names distinct, where it is shown and where not | 13, 14 |
| 4.6 a descendant's load order, outside the family | 16 |
| 4.7 a loop is an error, among ancestors or descendants, wherever it is | 15, 31 (a loop above the active project) |
| 4.8 the last declaring project wins | n/a here: no axis applies it in this item. Configuration applies it in TCW-109 ("How values combine", `docs/work/TCW-99-…/design.md:493`) and taxonomy and capabilities in TCW-112 ("An override is an object at the same path", `design.md:456`); the rule itself is `design.md:407`. The order it runs over is checked by 11 and 17, and the handoffs give both items AC 11's shape as a test |
| 5.1 which projects pass an axis | 17, 18 |
| 5.2 `sources(axis)` is the filtered load order | 17, 18, 26 |
| 5.3 `inherit` changes nothing else | 1 and 18 (the load order includes an `inherit: none` parent), 26 (an `inherit: none` parent still sees its child) |
| 6.1 own records keep working | 18, 26, 31 |
| 6.2 `InheritedUnavailable`, exit 7, the two messages | 19, 20, 31 |
| 6.3 `extends` naming a missing project exits 7 | 19 |
| 6.4 the load order with a project missing or unreadable | 18, 20, 31 |
| 6.5 `tcw validate`: (a) ancestor, (b) child, (c) `extends`, (d) unreadable; one finding per project | 18, 20, 26 (a); 6 (b); 19 (c); 31 (d); 20 (one finding) |
| 6.6 a problem in another project's links | 31 |
| 7.1 the write rule until TCW-114, siblings refused | 21 |
| 7.2 the `jira` block gone | 21, 8 |
| 8.1 `tcw projects list` plain | 5, 9, 23 |
| 8.2 `--json` fields, `read-only` included | 1, 5, 13, 18, 23, 27, 33 |
| 8.3 exit code 7 documented and pinned | 25 |
| 8.4 single-parent helpers removed | 28, 34 |
| 8.5 the web app's flag | 33, 34 |

## Risks

- **Every connected-project fixture writes `projects:`.** About fifty test
  files mention `projects` or `upstream` (`grep -rln` over `tests/`), and
  TCW-107 and TCW-110 will have added more, with their locators already in
  manifests. Each relation becomes `parents:`/`children:`, and each upstream
  a one-sided parent. Sibling `extends`, which the federation tests use
  heavily (`tests/test_capabilities_federation.py`, `tests/test_multiproject.py`),
  must become a parent link passing the axis (Design 3.6). The plan gives the
  tests one helper for writing relations, reads each failure rather than
  editing assertions, and keeps the tests of behavior that no longer exists
  (upstream bookkeeping) only where a 4.0 rule replaces them (Design 7.1).
- **A broken library makes inheritance through it unavailable** (Design 6.6).
  A reader is no longer stopped by it, but every command that needs an axis
  the library passes exits 7 until the library is fixed or the reader's link
  leaves that axis out. A loop anywhere still stops every command, because no
  order exists.
- **The load order can change when a missing or unreadable project becomes
  available** (Design 6.4), if that project's own parents are also reached
  another way and its listing reorders them. The order is marked incomplete
  until then, and `tcw validate` reports the project.
- **TCW-107 Design 2.11 (c) holds less often.** Answers depend on which
  projects were found first: from `app: [lib]`, `core` placed only in `app`'s
  manifest is found when the command runs in `app` and not when it runs in
  `lib` (Design 3.4 c). TCW-107's remedy stands: an entry in the project's
  own manifest settles it.
- **C3 is subtle.** Every example in the design is a criterion (AC 10-14), and
  the plan adds a property test comparing the implementation against a
  direct transcription of 4.1 on generated graphs.
- **`extends` keeps working by different rules for one or two items**
  (Design 3.6): a 3.x configuration extending a sibling, an upstream not
  named as a parent, or a descendant is refused on `v4` until it names that
  project as a parent passing the axis. UC-2's own example
  (`taxonomy.extends: [shared, core]`, `docs/use-cases.md:142-147`) has this
  shape. Nothing is released in between.
- **Writing into a sibling stops at this item** (Design 7.1), one or two
  items before TCW-114 removes those commands. Nothing is released in
  between.
- **The write rule is carried over, not decided** (Design 7.1): it lasts only
  until TCW-114, and loosening it by accident would let a reader write into a
  public library. AC 21 checks it.

## Notes

Decisions, each with its reason:

- **TCW-110 lands before this item** (user, 2026-10-22). The children's order
  is TCW-106, TCW-107, TCW-110, TCW-108, TCW-111. So a sibling is read by
  full identifier (Design 3.7), the records gate no longer depends on
  declared children (Design 2.6), and this item converts the `projects:`
  fixtures TCW-107 and TCW-110 leave (Design 3.5).
- **A problem in a non-active project's `parents:` does not stop the reader**
  (user, 2026-10-22, the review's option b). Other than a loop, it is recorded
  as "could not check" against that project, and only a command that needs
  what that project passes down fails, with exit 7 (Design 1.3, 6.6). A
  descendant's `children:` problems stay graph problems (Design 6.6), since
  the active project lists that descendant.
- **`extends` is removed in TCW-112, not here** (Non-goals), settled by the
  two requests and TCW-110, and confirmed by the lead on 2026-10-22. Until
  then it is held to the parent links (Design 3.6), so that `inherit` and
  `extends` never disagree.
- **Project IDs in the criteria are valid, lower-case IDs** (TCW-106's
  naming rule), the design's capital letters written doubled.
- **`inherit: []` is refused** in favour of `inherit: none` (Design 1.2), so
  each meaning has one spelling; a list of all three is accepted as `all`.
- **A project listed as both parent and child is a problem**, reported
  directly rather than only as the loop it implies (Design 1.3).
- **Children may not go in the user-wide file** (Design 2.2), since it applies
  to every project.
- **Only the active project's personal file adds children** (Design 2.4).
- **Name-back is checked for the lists the walk follows only** (Design 2.5):
  the active project's and its descendants'.
- **The walk never reaches siblings**, and `get` answers for the family only
  (Design 3.1, 3.3); naming any other project is TCW-110's full identifiers,
  located by TCW-107's `project_folder`.
- **TCW-107's ancestor manifests are read in reverse load order** (Design
  3.4 b), so a location and a value follow one precedence (the handoff's
  "natural" order); **its descendant manifests include unlisted descendants**
  (Design 3.4 c), so a reader's manifests serve the library's parents.
- **A project outside the graph is read upwards only** for a lookup (Design
  3.4, the 2.12 bullet).
- **One load order serves every axis**, filtered per axis (Design 5.2), so
  there is one order and one warning to show.
- **If any merge fails, the whole order falls back** (Design 4.4), rather than
  mixing C3 and depth-first within one order.
- **The fallback warning is shown only by `tcw validate`, `tcw projects list
  --json` and later `tcw project info`** (Design 4.5).
- **A loop is a graph problem wherever it is**, so it refuses the commands
  every graph problem refuses today; "any command that loads the project" in
  the design is read as every command that requires a valid graph
  (`require_valid`, called by `find_component_project`, `tcw/store/fs.py:356`,
  among others).
- **Exit code 7, `INHERITED_UNAVAILABLE`, raised as `InheritedUnavailable`**
  (Design 6.2), the next free number; named for what is unavailable rather
  than for a missing project, because an unreadable one raises it too.
- **A project behind an `inherit` that leaves the axis out never stops a
  command** (Design 6.2), so a code repository's CI need not clone a
  view-only workspace (UC-4).
- **`extends` naming a missing ancestor exits 7 now** (Design 6.3), so the
  new code has a real command behind it before TCW-112, and `tcw validate` in
  CI stops failing on it.
- **One `tcw validate` finding per missing project** (Design 6.5), extending
  TCW-107's plan's rule for its manifest entries.
- **No shared helper for "only a declaring project replaces"** (Design 4.8):
  TCW-109 folds configuration mappings with `null` and TCW-112 folds objects
  by path, so a helper written here would be redesigned by each. The rule,
  and AC 11's shape as a test, go to both in the handoffs.
- **The 3.x write rule carries over** as "links both sides declare" (Design
  7.1), siblings are no longer writable, and the `jira` block goes with
  `projects:` (Design 7.2).
- **What `tcw project info` will show is put in `tcw projects list --json`**
  now (Design 8.2), so it can be checked before TCW-115.
- **The agent-facing exit-code table is changed here, not in TCW-117**
  (Design 8.3): it states a contract agents act on.

Handoffs, which the dispatching session records on each ticket when this spec
is accepted:

- **TCW-107:** Design 3.4 replaces "ancestors" and "descendants" in TCW-107
  Design 2.2 and 2.10 with parent links: (b) reads ancestors' manifests in
  reverse load order (depth-first over the projects found so far when C3
  fails on them); (c) reads the manifests of every descendant already found,
  listed or not (a project that names the asking one as a parent), nearest
  first. 2.11 (a) carries over for several parents. The 2.12 bullet for a
  project not in the graph reads its `parents:` upwards only, never its
  `children:`. The "not on this machine" and "unknown" rows read "a
  `parents:` or `children:` entry". Design 3.5 replaces TCW-107 Design 3.
  2.11 (c) holds less often (Risks). TCW-107's plan needs no change for this:
  its `_locate` order and single-parent `_follow_edges` are rewritten here.
- **TCW-109:** applies Design 4.8 over `sources("config")`, folding each
  project's own declarations and never a parent's resolved view, and tests
  AC 11's shape (`bb` parent of `cc` and `dd`, `ee: [cc, dd]`, `cc` declares a
  key and `dd` does not: `ee` gets `cc`'s). Adds nothing to the personal
  allowlist for `parents`; `children` is already allowed in the project's
  personal file only (Design 2.2). Environment variables must not set
  `parents`; whether one may add a child is TCW-109's to decide (this spec
  suggests not, since it would make the family differ by environment).
  **A conflict to decide:** `work.backend` and `work.tags` are inheritable
  (design.md:482-488); if `tcw work list` reads them through
  `sources("config")`, a missing `inherit: all` parent makes it exit 7,
  against "commands that need only the project's own records still work"
  (Design 6.1). TCW-109 must say which work settings a work command needs from
  its parents, and whether a missing parent stops it.
- **TCW-110** (lands before this item; nothing in its documents needs to
  change): this item converts its `projects:` fixtures (AC 13, AC 12, the
  plan's Step 7 tests and any others) by the mapping in Design 3.5, so an
  `app` naming `core` under `projects.upstream` becomes `parents: [{id: core,
  inherit: none}]`, and an `app` extending `core` gets a parent link passing
  that axis (Design 3.6). If convenient, write those fixtures through one
  helper, so that the conversion is in one place. This item rewrites "named
  by a manifest or `projects:` entry" in TCW-110's code (its Design 6.1
  table) to "a manifest, `parents:` or `children:` entry". An inherited
  object read through `extends` (its Design 3.1, 6.2) is read only from an
  ancestor passing that axis. A missing project's object stays exit 5;
  missing inherited content is exit 7. Its records gate, which no longer asks
  `declared_child_ids()`, is relied on (Design 2.6).
- **TCW-111** (lands after this item): its fixtures cannot use `projects:`,
  which this item refuses. AC 15's "`app` naming `core` under `projects:`"
  becomes `app` with `parents: [{id: core, inherit: none}]` (or `core` placed
  by a manifest entry, if no relation is wanted): either keeps `core`'s
  absence "could not check" rather than "unknown". With the parent link, `tcw
  validate` also reports one `unresolved` finding for `core` itself (Design
  6.5 a), which a criterion counting findings must allow for.
- **TCW-112:** removes `taxonomy.extends`, `capabilities.extends` and `tcw
  taxonomy|capabilities extends add|rm`, and with them Design 3.6's interim
  rule; applies Design 4.8 over `sources("taxonomy")` and
  `sources("capabilities")`, folding each project's own objects, and tests
  AC 11's shape; raises `InheritedUnavailable` only when inherited content is
  needed, closing the UC-6 gap that a missing `extends` project stops reading
  the project's own entries.
- **TCW-113:** uses `ancestors()`, `descendants()`, `declared_child_ids()`
  (for a listed child not here, shown unavailable with the command that
  fetches it) and `load_order(id)` of each descendant (Design 4.6) for mixed
  status.
- **TCW-114:** replaces Design 7.1's interim write rule, and the `read-only`
  row field and the web app's `readOnly` (Design 8.2, 8.5), with "only the
  active project"; the `jira` block path is already gone (Design 7.2).
- **TCW-115:** `tcw project info` prints `parents()`, `declared_child_ids()`,
  `load_order()` and its warning; `tcw project list` carries Design 8.2's
  fields.
- **TCW-116:** converts `projects.parent` to `parents: [<id>]`;
  `projects.children` to `children:`; each `projects.upstream` entry to a
  parent whose `inherit` lists the axes `extends` took from it (`none` if
  none); an `extends` naming a sibling or a descendant to one more parent
  inheriting only the named axes; an `extends` naming a project already
  inherited through another parent to nothing; and drops `jira` blocks,
  reporting each.
- **TCW-117:** `docs/use-cases.md` UC-2 (rename `projects:`; the requirement
  itself holds, Design 6.6), UC-3 (`parents:` instead of `parent: app:
  ../..`; packages no longer write into each other), UC-4 (the workspace as an
  `inherit: none` parent), UC-6 (the `jira` block and exit 5 for inherited
  content; exit 7), S-6 (exit codes); `docs/guide/multi-repo.md`,
  `skills/configure/references/projects.md` and
  `docs/guide/taxonomy-and-capabilities.md` (upstream, `projects:`, and
  `extends` held to the links).

Questions for TCW-99: none. The one this spec raised (where `extends` is
removed) is now a recorded decision (Non-goals).
