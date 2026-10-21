# TCW-99 design: TCW 4.0 project relationships and deployments

The working design for TCW-99. The ticket holds the vision and objective;
this document holds the technical design, every decision taken, and the
questions still open. It is updated as decisions are made, and the spec
stage builds on it.

TCW 4.0 is designed from first principles as the ideal version for the
people who will use it. Earlier versions bind nothing: where the ideal
differs from how TCW works now, the ideal wins, and 4.0 makes a clean
break. The section "Coming from 3.x" records how TCW works now only so
that `tcw migrate` can move the few existing projects over. Agreed with
the user in design sessions on 2026-10-20 and 2026-10-21; it contains
TCW-98 (seeing a project's descendants as well as its ancestors), which
was discarded in its favour.

This is far larger than one piece of work. It is split into child items
(see "Next step").

## Cost and the alternative rejected

- **Cost:** it defines most of what a user sees in TCW 4.0: where a
  project's configuration lives and its format, how every list and show
  command reads data, which commands may write, the CLI's top-level
  command set, and the file that marks each record. Several 3.x commands
  go (`tcw work new --project`, `tcw work edit --blocks`, `tcw init`,
  `tcw projects`, `tcw config`). The cost of the break is small because
  TCW has almost no users yet; the existing projects, this repository's
  included, move over with `tcw migrate`.
- **Alternatives:** keep two kinds of link, a tree for organizing and
  viewing projects plus a separate "builds on" link for content (today's
  `extends`, cleaned up). Rejected in discussion: every view would have to
  merge two graphs, and the rule "never show siblings" would need an
  exception for siblings a project builds on, which is the confusion this
  item exists to remove.

## Requirements for TCW as a whole

These are the user's, and every part of the design below must keep them.

1. TCW's records are trivially readable by an AI agent. Taxonomy and
   capabilities are markdown and YAML files in the repository; work items
   are too, though a work item's stage, request and comments may live on a
   Jira ticket instead.
2. TCW's records are tracked by git. That is where they live; TCW does
   not otherwise depend on git's state, and never refuses to act because a
   working tree has uncommitted changes. (Git worktree support necessarily
   asks git where the main checkout is.)
3. Taxonomy and capabilities support inheritance.
4. TCW configuration supports inheritance.
5. TCW configuration supports personal (local) overrides and overrides
   from environment variables.
6. A folder is a TCW project if it contains a `.tcw/` folder holding
   `tcw-config.yaml`.
7. For any folder, the *active TCW project* is the nearest enclosing
   folder (the folder itself included) that is a TCW project.
8. One repository may contain many TCW projects.
9. Git worktrees are fully supported (see "Git worktrees").

## Coming from 3.x (for migration only)

- **The configuration file** is `tcw-config.yaml` at the project's root,
  with `tcw-config.local.yaml` beside it. Its layers (`LAYERS` in
  `tcw/config.py`) are built-in, project, user-wide and local; they never
  include another project. Today the personal layers cannot set `projects`
  or `extends`.
- **Three mechanisms relate projects:**
  - `projects:` connects projects. A project has at most one parent, and
    parent and child must each name the other. An `upstream` is a
    one-sided, read-only connection. On its own, a connection shares only
    work items, which are read by full slug.
  - A store's `path` and `repository` say only where its folder is.
  - `extends` names, per axis, any connected project (a sibling included)
    whose taxonomy or capabilities this one inherits.
- **No inheritance through folder nesting.** `find_project_root`
  (`tcw/store/fs.py`) stops at the nearest `tcw-config.yaml`.
- **Objects:** a taxonomy entry or a capability is a folder holding
  `meta.yaml` and `description.md`. Capabilities are nested one level, in
  group folders such as `docs/capabilities/work/`, which are not objects
  themselves. A work item is a folder holding `item.yaml`; child items sit
  side by side with their parents and name them in a `parent:` field.
- **Slugs:** a work item's slug today is `<project-id>/<folder-name>`, for
  example `tcw/TCW-99-redesign-how-tcw-projects-relate-...`, with no axis
  in it.
- **Environment variables:** `TCW_PROJECT_<ID>` gives a connected
  project's folder; `TCW_CONFIG_DIR` and `TCW_NO_PERSONAL_CONFIG` control
  the user-wide layer. No variable can set an arbitrary configuration key.
- **`tcw serve`** serves only the project it was started in
  (`docs/guide/web-viewer.md`). Before 3.0 it combined descendants' work
  boards; that was lost in the 3.0 rewrite (TCW-68) without anyone
  deciding to drop it.
- **The registry already exists.** It has `ancestors()` and
  `descendants()` (`tcw/store/project.py`, `tcw/store/base.py`), and
  `descendant_projects()` in `tcw/store/fs.py` has no callers.

## Agreed design

### Principles

1. **Only declared links create relationships.** Where a folder sits on
   disk, or where a store's files are kept, never means anything about how
   projects relate. TCW may look on disk to *find where* a project is (see
   "Locating a project"), but a relationship is only ever declared.
2. **There is one kind of link between projects,** and it means the same
   thing on taxonomy, capabilities and work.
3. **Every object belongs to exactly one project,** the one that declares
   it, wherever it is viewed from and wherever its files are stored. In the
   user's setup, Desktop-App's work items are stored in Docs-and-Plans but
   owned by Desktop-App.
4. **The web app shows only what the CLI can also show.** Every view and
   control in `tcw serve` has a matching command or flag.

### What any store must support, and what is only about folders

The prime directive (`docs/lifecycle/abstraction.md`) asks of every
operation whether a store that is not a folder of files (a database, or
Jira) could implement it. This design has two layers, and only the first
binds every store:

- **The model, which every store implements:** projects and their parent
  links, full identifiers, ownership, inheritance and the load order,
  overrides, `--scope`, and the rule that only the active project changes
  anything. Nothing here assumes a folder: an object is found by its full
  identifier, and how a store keeps it is the store's business.
- **The deployment layer, which is about folders on disk:** the `.tcw/`
  folder, manifests, finding a project's folder ("Locating a project"),
  `.path` addresses, "stores never nest", git worktrees, and state files
  marking which folders are objects. These are how the files store and a
  person's checkout work. A store that is not a folder of files does not
  implement them and is not required to.

The spec states, for each new operation, which layer it is in, and runs
the litmus test on everything in the model.

### The `.tcw/` folder

- Every TCW project has a `.tcw/` folder at its root. Its location is
  fixed: it cannot be configured. It holds:
  - `tcw-config.yaml`: the project's configuration, much as today. It
    declares the project's `id`, its relationships (by ID only), and where
    its stores are (see "Where stores live").
  - `tcw-config.local.yaml`: personal overrides. It should be untracked,
    but keeping it out of git is the repository owner's job, not TCW's.
  - `tcw-manifest.yaml`: where other TCW projects are, as a mapping from
    project ID to a relative path.
  - `tcw-manifest.local.yaml`: the personal counterpart of `tcw-manifest.yaml`,
    for paths that differ from machine to machine. Untracked on the same
    terms as `tcw-config.local.yaml`.
- **Where each axis's records live is configurable** (see "Where stores
  live"). Only `.tcw/` itself is fixed.

### The manifest

- **The manifest says where projects are, and nothing else.** Being in a
  manifest does not make a project a parent, a child or anything else;
  relationships are declared by ID in `tcw-config.yaml` (principle 1).
  A project's location never appears in `tcw-config.yaml`.
- An entry can also carry the repository a project is fetched from, so
  that a project not on this machine can be shown with the command that
  fetches it. The repository may name a branch, with a git-like suffix.
  (The exact shape of an entry, and of the suffix, is for the spec.)
- **The common case:** a monorepo whose root is a TCW project and whose
  packages are TCW projects too. The root's manifest lists each package.
- `tcw validate` checks that every project in the manifest can be reached
  and declares the ID the manifest gives it.

### Locating a project

To find the folder of a project from its ID, starting from **the project
that names it** (the one whose configuration, manifest or record holds the
ID; not necessarily the active project):

1. Look it up in that project's manifest (`tcw-manifest.local.yaml`
   first, then `tcw-manifest.yaml`), then in its ancestors' manifests, and
   then, going down, in the manifests of the children already found. So
   Desktop-App can reach a blocker in Server-App through Shared-Libs'
   manifest, even though Server-App never appears in Desktop-App's views;
   and Docs-and-Plans finds a grandchild that only Shared-Libs' manifest
   lists.
2. If no manifest has it, look at the folders next to that project's root
   (the folder holding its `.tcw/`). A folder matches if its
   `.tcw/tcw-config.yaml` declares that `id`.
3. Then check each folder that encloses that project's root, from the
   nearest outwards, up to the filesystem root, matching the same way (the
   enclosing folder itself, not its other contents). This is how a package
   one folder below its parent finds the parent without a manifest entry.
   It only locates the project: an enclosing project is never a parent
   unless the child names it (principle 1).

TCW looks no further than that.

- **Two folders matching one ID is an error** that names both folders: a
  second clone of a repository beside the first, or a retired copy of a
  family with the same IDs (`docs/use-cases.md`, UC-8). The manifest
  decides: an entry in a manifest is never second-guessed by the search.
  (A git worktree and its own main checkout are the one exception; see
  "Git worktrees".)
- **Finding a project is not the same as seeing it:** which projects a
  view includes is decided by `--scope` (below), never by what can be
  found.
- Full identifiers must be unique, so project IDs must be unique across
  every project that can be reached this way. `tcw validate` checks it.

### Full identifiers

- **Every TCW object (a taxonomy entry, a capability or a work item) has a
  full identifier** of the form `<project-id>.<namespace>/<object-id>`:
  - `<project-id>` is the `id` declared in the owning project's
    `tcw-config.yaml`.
  - `<namespace>` is one of `taxonomy`, `capabilities`, `work`. The
    period cannot be confused with part of the project ID, which never
    contains one.
  - `<object-id>` is the object's own ID: in the files store, the name of
    its own folder. It is unique within its project and namespace,
    however deeply the folder is nested.
  - A full example: `my-proj.taxonomy/component-one`, whether its folder
    is `docs/taxonomy/component-one` or
    `docs/taxonomy/main-app/feature-alpha/component-one`.
- **Identity does not depend on where a folder sits** (decided
  2026-10-21, replacing an earlier rule that the whole folder path was the
  identifier). Folders above an object organise it, and nothing more.
  Moving an object into another folder never changes its full identifier,
  so no reference breaks and no override detaches. Renaming the object's
  own folder does change it (see "Moving and renaming an object").
- **Object IDs** use lowercase or uppercase letters, digits, hyphens and
  underscores, so they can be written in an address without escaping
  (`#`, `?`, `%` and spaces are not allowed). Work item folders such as
  `TCW-120-add-login` qualify. The exact grammar is for the spec.
  `tcw validate` reports two objects in one project and namespace with the
  same ID.
- **Names.** "Full identifier" is the proper name. "Full id" and "slug" are
  nicknames for the same thing, including where existing text says "slug"
  for a work item.
- **As an address, it is the full identifier after `tcw://`:**
  `tcw://my-proj.work/work-item-1`. The same form with `.path` added after
  the project or the namespace names a folder on disk rather than an
  object:
  - `tcw://p1.work/work-item-1`: the work item `work-item-1` in p1.
  - `tcw://p1.path/`: the root folder of project p1.
  - `tcw://p1.work.path/`: the folder of p1's work store.
  - `tcw://p1.path/docs/p2-work`: a folder inside p1's project folder,
    for example next to p1's work store when that is `docs/work`.
  - `tcw://p1/`: invalid; an address needs a namespace, `.path`, or both.

  Without `.path`, the rest must name an existing TCW object, and
  `tcw validate` checks it. With `.path`, the rest is an ordinary folder
  path and is not checked against TCW's objects.
- **An address never contains a `.` or `..` folder.** Addresses must read
  the same in any general-purpose URL parser, and those parsers (the one
  built into browsers among them) drop `..` at the start of a path:
  `tcw://p1.work.path/../p2-work` would become `tcw://p1.work.path/p2-work`,
  a different folder. Since the project root is always available
  (`tcw://p1.path/`), a folder outside a store is written from the root
  instead. `tcw validate` rejects an address with a `.` or `..` folder.
- **An object's ID is its folder's name.** `docs/work/some-work-item` is
  the work item with ID `some-work-item`. Its state file may repeat it as
  `id:`, but does not have to.
- **Object IDs need not be unique across projects; full identifiers
  must be.**
- **An address is resolved from the project that wrote it.** A store
  address such as `tcw://p1.path/docs/p2-work` in p2's configuration is
  resolved from p2, wherever the command runs, so it names the same folder
  for everyone.
- **References are never shortened.** A reference to an object, in a
  file or anywhere else TCW stores it, is always its full identifier, and
  every command prints full identifiers in its output. A shorter display
  can come later, in the web app or through extra flags.
- **A work item's tracker key stays accepted as command input.** Today's
  work item folder `TCW-99-redesign-how-tcw-projects-relate-...` gives a
  full identifier of about 140 characters; `TCW-99` remains usable wherever
  a command accepts an item, and the full identifier is stored on the
  ticket anyway.
- **Turning a full identifier into a folder** (the files store; another
  store resolves an identifier its own way):
  1. Find the project named by `<project-id>` (see "Locating a project").
  2. Load that project's configuration: its files, inheritance, local
     overrides and environment variables.
  3. From that configuration, find the folder for `<namespace>`.
  4. Find the folder named `<object-id>` that holds the namespace's state
     file, at any depth inside that folder.

### Where stores live

- **A store's location is either a plain path or a `.path` address.** A
  plain path is relative to the project's own root, as today
  (`docs/work`), and may use `..`, since no URL parser reads it. An
  address places the store inside another project, for example
  `tcw://p1.path/docs/p2-work`, so that a project whose work is kept in
  another repository says so without a machine-specific path. Wherever a
  store is, its objects belong only to the project that declares it
  (principle 3).
- **Stores never nest or coincide.** `tcw validate` fails when one
  project's store folder is the same folder as another project's, or lies
  inside it, since the outer project would list the inner one's objects as
  its own. A store elsewhere inside another project's folder is fine.
- **No loops.** `tcw validate` fails when store locations are defined in
  terms of each other in a loop.

### Objects, folders and state files

- **A folder is an object only if it holds the state file for its
  namespace.** The state files are renamed with a `tcw-` prefix, one name
  per namespace: `tcw-taxonomy.yaml`, `tcw-capability.yaml` and
  `tcw-work-item.yaml` (replacing `meta.yaml` and `item.yaml`). Anyone
  reading a folder can tell at once what it is.
- **An object's folder is a bounded set** (decided 2026-10-21): its fixed
  files (for a work item, the state file, the stage documents, rounds,
  handoffs and `comments/`, as today), the folders of its child objects,
  and one `resources/` folder for anything else that belongs to it. The
  names TCW uses for its fixed files and folders, and `resources`, are
  reserved: no object may be named with one. This keeps the rule in
  `docs/lifecycle/abstraction.md` that an item folder is not an open set
  of files, extended to allow child folders and `resources/`; the change
  amends that document deliberately. Taxonomy and capability folders
  follow the same shape.
- **A folder without a state file is allowed between objects** (an
  organising folder, like today's capability group folders). It is not an
  object, never appears in an object listing, and is not part of any full
  identifier.
- **Folder nesting does not declare a parent.** For taxonomy,
  capabilities and work alike, which object is another's parent is
  declared in its state file (`parent:`), never by where its folder sits.
  But TCW should *encourage* nesting a child's folder inside its parent's,
  through the plugin's skills and the stage prompts, so that the folders
  read the way the objects relate. Where the folder and `parent:`
  disagree, `parent:` decides and `tcw validate` warns. (Projects are the
  exception: they never nest this way, since a project's parents are in
  its configuration.)
- **The work backends change shape.** Today both refuse an item name
  containing `/` and look only at the top of the work folder. In 4.0 an
  item is found by its ID wherever it is nested; the spec states the new
  backend operations (`read`, `rename`, `lookup` and the test for an item
  folder).

### The parent link

- A project names its parent or parents, by ID, in `tcw-config.yaml`. That
  one link does two jobs. **Content flows down:** a child inherits its
  parents' taxonomy, capabilities and configuration, and can override
  them. **Views look down:** a parent's views can include its children.
- **Each parent entry may say what it passes down** (decided 2026-10-21):
  `inherit: all` (the default), `inherit: none`, or a list drawn from
  `taxonomy`, `capabilities` and `config`. It is still one link and one
  viewing rule; only what flows down varies. A planning repository or
  monorepo root that only wants the top-down view is a parent with
  `inherit: none`; a private project can take a public library's
  vocabulary with `inherit: [taxonomy]` without its settings.

  ```yaml
  parents:
    - id: workspace
      inherit: none          # view only
    - id: core
      inherit: [taxonomy]    # vocabulary only
    - app                    # everything
  ```
- **The child's declaration alone gives it the inheritance.** The
  child finds the parent's folder as "Locating a project" describes.
- **A parent may list its children by ID; it does not have to.** It can
  list them in the committed `tcw-config.yaml`, for an organization whose
  engineers can be expected to have every child repository. Or it can list
  them in the personal `tcw-config.local.yaml`, with their paths in
  `tcw-manifest.local.yaml`, for one person who wants the top-down view
  without committing the children's names (for example, a public library's
  maintainer viewing private readers). This replaces today's `upstream`: a
  one-sided link is an ordinary parent link the parent does not list.
- **Children listed in both files are combined.** The local file can add
  children but not remove committed ones, so two engineers on the same
  commit always get the same totals.
- **A listed child must name the parent back,** whether it is listed in
  the committed file or the local one. If it does not, that is an error.
- **A listed child that is not on this machine** is shown as present but
  unavailable, with the command that fetches it. It is never left out
  silently, or totals would look complete when they are not.

### A related project that is not on this machine

Decided 2026-10-21 (`docs/use-cases.md`, UC-6 and S-4): a fresh clone,
CI, or an outsider building on a public library may not have every
parent.

- **Commands that need only the project's own records still work:**
  listing, reading and moving its own items, reading its own taxonomy and
  capabilities.
- **A command that needs something inherited stops,** naming the missing
  project and the command that fetches it (`tcw project provision <id>`),
  with an exit code of its own. That includes a command that needs an
  inherited setting, such as Jira settings a project takes from its
  parent.
- **`tcw validate` reports references into a missing project as "could
  not check",** not as broken, so CI on a single repository can run it.
- **Reading another project over the network is never implicit.**

### Multiple parents, and which value wins

- A project may have several parents.
- **Parents are listed in order, and the last one wins.** If a project's
  parents are [A, B, C] and each declares an inheritable value or object
  `P`, the project uses C's `P`. Its own declaration beats all of them.
- **Several levels.** If C's parents are [A, B], F's are [D, E] and G's
  are [C, F], G's load order is [A, B, C, D, E, F, G]: each parent's own
  ancestors come before it, in listing order.
- **Only a project that actually declares or overrides a value replaces
  it.** A project that only passes an inherited value along does not put
  the original back. This matters only when two parents share an
  ancestor. Example: B is the parent of C and D, E's parents are [C, D], C
  overrides `P` and D does not. E gets C's `P`, not B's, even though D is
  listed later: D merely passes B's value along. (Resolving each parent
  fully and letting the last one win would have given B's `P` and silently
  lost C's override; the user chose the rule above on 2026-10-21.)
- **A project reached twice is loaded once,** after all of its own
  ancestors. In the example, B is reached through both C and D, and E's
  load order is [A, B, C, D, E].
- **The algorithm is C3, with a depth-first fallback** (decided
  2026-10-21, replacing plain depth-first). C3 is the algorithm Python
  uses to order a class's parents, mirrored so that the last listed wins.
  It finds an order that keeps every project's own parent order whenever
  such an order exists. Plain depth-first does not: with Z's parents
  [X, Y], X's [B] and Y's [A, B], depth-first gives [B, X, A, Y, Z] and Z
  takes A's value, although X and Y both see B's and [A, B, X, Y, Z]
  satisfies everyone. C3 gives that order. (Found by the 2026-10-21 multi
  review and checked by running both.)
- **When C3 finds no order, TCW falls back to depth-first and warns,**
  rather than failing. Depth-first: go through the parents in listing
  order; for each, first place its own ancestors by the same rule, then
  the parent, skipping any project already placed; the active project
  goes last. The two shapes with no consistent order:
  - Parents that disagree: Z's parents are [X, Y], X's are [A, B] and Y's
    are [B, A]. The fallback gives [A, B, X, Y, Z], so B's values win in Z
    although Y alone would see A's.
  - A child listed before its own parent: E's parents are [D, C] and C is
    D's parent. The fallback gives [C, D, E]; an ancestor always comes
    first, whatever the listing order says.

  These warn rather than fail because the fix usually lies in projects
  the active one cannot change (only the active project can be changed),
  so a failure would leave it stuck. The warning names the projects, so
  the active project can override the value itself. `tcw validate` and
  `tcw project info` both show it.
- **A loop is an error.** If a project is its own ancestor, there is no
  order; `tcw validate`, and any command that loads the project, reject
  it.

### What is inherited

- **Work is never inherited.** A project does not take on its parents'
  work items. Ancestors' or descendants' items appear only when a command
  is asked for them with `--scope`.
- **Taxonomy and capabilities:** everything, from each parent whose
  `inherit` includes that axis (see "The parent link"). This replaces
  `taxonomy.extends` and `capabilities.extends`.
- **Overrides are separate objects that say what they override.**
  Desktop-App's override of `shared-libs.capabilities/abc` is its own
  object, owned by Desktop-App, whose state file names the original with
  `overrides: shared-libs.capabilities/abc` (as 3.x's overrides already
  do). It is matched by that pointer, never by sharing a name or a folder
  position, so moving either object never detaches it. An override merges
  with its original field by field, as in 3.x, so one that changes only
  the status keeps following the original's description. So
  `--project shared-libs` returns only the original, and a mixed-status
  summary counts one status per project. An override whose original is
  gone is reported by `tcw validate`.
- **Two parents defining the same object is reported,** not settled
  silently (`docs/use-cases.md`, UC-3): when two projects in the load
  order each have an object with the same ID and neither overrides the
  other, the load order picks one and `tcw validate` and the listing warn.
  A child's own override is never a warning.
- **Configuration:** a fixed list of keys, which TCW documents and grows
  only in a release (decided 2026-10-21), crosses the link from each
  parent whose `inherit` includes `config`. To start: `work.tags`,
  `work.backend`, and the Jira settings (`work.jira`: site, project,
  fields and credential variable names). Inheriting `work.jira.project`
  means a child's items go into the parent's Jira project, told apart by
  the existing "TCW Project" field. Everything else is the project's own:
  its `id`, parents, children, store locations, stages and their
  bindings, hooks, procedures and documentation entries. An inherited
  value holding a relative path resolves from the project that declared
  it.
- **How values combine:** a mapping is merged key by key, all the way
  down; a list or a single value is replaced whole. So a child that sets
  only `work.jira.project` keeps its parent's `work.jira.site`, and a
  child that sets `work.tags` replaces the parent's list. To add to an
  inherited list instead, the child includes today's `inherit: true`
  entry in its list, which now also reaches across the parent link.
- **`null` removes an inherited value.** A child that sets a key to
  `null` has no value for it. Inherited objects cannot be removed: a
  taxonomy entry has no way to be, and a capability can only be given the
  status "omitted". A way to remove inherited objects can be added if a
  real case needs it.

### Personal overrides and environment variables

- Each project's configuration is assembled from its own files
  (`tcw-config.yaml`, then the user-wide file, then
  `tcw-config.local.yaml`), then environment variables, and only then
  inherited by its children. So a child that inherits a value gets the
  overridden one.
- **Any configuration value can be overridden by an environment variable
  whose name follows mechanically from the key and the project ID:**
  `TCW_<KEY>__<PROJECT>`. The key's parts are joined with a single `_`,
  the project ID follows a double `__`, everything is uppercase, and each
  hyphen becomes `_`, since shells reject hyphens in variable names. For
  project `my-proj`, `work.path` is overridden by
  `TCW_WORK_PATH__MY_PROJ=/other/path`. Shells accept only letters,
  digits and underscores in a variable's name, so no other separator
  (`.`, `-`, `,`) is usable.
- **The key part is decoded against the keys TCW knows.** A hyphen and a
  dot both become `_`, so `..._EMAIL_ENV__...` could on its face mean
  `email-env` or `email.env`; TCW picks the one that is a real key. Two
  keys can encode to the same name only where a key part is chosen by the
  user, such as a stage or procedure name, and `tcw validate` reports such
  a configuration as an error.
- **Project IDs and every configuration key,** including names the user
  chooses such as a stage or procedure name, are restricted to lowercase
  letters and digits in groups joined by single hyphens (no leading,
  trailing or doubled hyphen), so every name has a variable and decodes
  one way only. `tcw validate` enforces it.
- **The more specific variable wins.** If both `TCW_WORK_JIRA__APP` (the
  whole mapping) and `TCW_WORK_JIRA_SITE__APP` (one key in it) are set,
  the whole mapping is applied first and the single key on top of it.
- **Personal files and variables keep an allowed list,** as 3.x's
  `PERSONAL_KEYS` does (`docs/use-cases.md`, S-5). Neither can change a
  project's `id`, its parents, or its store locations; a personal file can
  add children but not remove committed ones (see "The parent link"); and
  `TCW_NO_PERSONAL_CONFIG=1` turns off the variables as well as the
  personal files. The spec lists the allowed keys.
- **Values are read by the key's type.** A string stays exactly as
  written, so `no`, `on` and `1.0` are not turned into booleans or
  numbers. A boolean or number must be a valid one. A list or mapping is
  read as YAML and replaces the whole value; there is no way to override
  one entry of a list. A variable that names no real key is an error.
- **A name with `__` is an override; one without is not.** So the
  existing `TCW_PROJECT_<ID>`, `TCW_CONFIG_DIR`, `TCW_NO_PERSONAL_CONFIG`
  and user-chosen credential names such as `TCW_JIRA_EMAIL` keep working.
  `TCW_PROJECT_<ID>` may become redundant once a manifest path can be
  overridden; the spec decides.
- Codex was consulted on the naming (2026-10-21) and proposed
  `TCW__PROJECT__<ID>__<KEY>` with a separate `TCW__ALL__<KEY>` form; the
  user chose the shorter form above.

### Git worktrees

TCW in a git worktree behaves as it does in the main checkout, with the
branch's own changes:

- **Tracked files** (configuration, manifests, every record) are read from
  the worktree, because that is where the branch's changes are.
- **Untracked files** (`tcw-config.local.yaml`, `tcw-manifest.local.yaml`)
  are read from the worktree if it has them, and otherwise from the main
  checkout. So a worktree has the main checkout's personal settings by
  default, and a person can give one worktree its own `tcw-manifest.local.yaml`
  to point it at a different copy of another project.
- **A path that leads outside the repository** (a manifest entry such as
  `../shared-libs`) is resolved from the main checkout's location, since a
  worktree usually lives elsewhere on disk. The same goes for the
  sibling-folder search and for the walk through enclosing folders beyond
  the repository in "Locating a project": from a worktree at
  `/tmp/app-branch`, a parent enclosing the main checkout is still found.
- **A project found both in the worktree and in its main checkout is one
  project,** not two with the same ID. This happens when a worktree is
  made inside its own repository's folder and the walk up through
  enclosing folders reaches the main checkout. The worktree's copy is
  used, and `tcw validate` does not report it as a duplicate.

### Only the active project can be changed

- **TCW commands create, change and delete objects only in the active
  project.** An inherited object is never changed from below, and a
  descendant's object is never changed from above.
- **Overriding an inherited object is allowed,** because the override is a
  new object owned by the active project.
- **`tcw serve`** is read-only for every object the project it runs in
  does not own.
- **The active project means the owning project, wherever its store
  sits** (decided 2026-10-21). In a planning workspace that holds other
  projects' work stores (`docs/use-cases.md`, UC-4), the workspace cannot
  create, advance or comment on those items; that is done from the owning
  project's folder, which a refusal names. Accepted cost: the planner needs
  each code project checked out.
- **`tcw work new --project <id>` and `tcw work edit --blocks` are
  dropped,** because each one changes another project. Accepted loss:
  today you can file a ticket into the Jira project of a project you have
  not cloned. That is no longer possible.
- **One stated exception: a blocker in another project.** An item can
  name a blocker in another project. The link belongs to the blocked item.
  In Jira it is an issue link, which also shows on the other project's
  ticket; that is not a change to the other item's record, and is allowed
  (decided 2026-10-21).

### A `tcw project` command group

| Today | Becomes |
| --- | --- |
| `tcw init` | `tcw project new` |
| `tcw projects list` | `tcw project list` |
| `tcw config show` | `tcw project config`; with `--origin`, each value is printed with the project and file it came from, as `git config --show-origin` does |
| `tcw provision` | `tcw project provision` |
| (new) | `tcw project path <id>`: the folder of that project on this machine, so a person or an agent knows where to run a command that changes it |
| (new) | `tcw project info`: the active project's ID, parents, children, load order with any load-order warnings, and important configuration values |

`tcw validate` and `tcw serve` stay at the top level, since they act on
all three axes rather than on the project's own settings.

### Choosing what a list or show command covers

- **`--scope`** has four settings:
  - `own`: only the active project's objects.
  - `up`: own, plus everything from ancestors (for work, which is not
    inherited, the ancestors' own items).
  - `down`: own, plus everything from descendants.
  - `all`: ancestors, own and descendants. Never siblings, nor anything
    else in another branch.

  **The default is `own` on every axis.** The web app has a matching
  control.
- **`--project <id>`** keeps only results owned by that project.
- **There is no `--as`.** To see things as another project sees them,
  change into that project's folder and run the command there
  (`tcw project path <id>` gives the folder). That is more explicit than a
  flag, and it is what a change to that project needs anyway.
- **Mixed capability status** (shown when the scope includes several
  projects, `down` or `all`). Where projects in the view give a
  capability different statuses, a list shows a short summary such as
  "Missing(1), Supported(1), Omitted(1)". The detail view shows which
  project has which status. To open the capability as one of those
  projects sees it, run the command in that project's folder. A project that inherits a status
  without overriding it counts with that status, marked as inherited. A
  sketch:

  ```
  $ tcw capabilities show shared-libs.capabilities/abc
  full id: shared-libs.capabilities/abc
  owner: shared-libs
  status:
    missing:   [shared-libs]
    supported: [desktop-app]
    omitted:   [server-app]
  ```

### Moving and renaming an object

- **Moving an object into another folder changes nothing** about its
  identity: no reference breaks, no override detaches.
- **Renaming an object's own folder changes its full identifier.** A
  rename command rewrites the active project's own references to it (and,
  in Jira, the ticket's "TCW Item" field, as `tcw work rename` does today).
  References held by other projects cannot be rewritten from here, so
  **`tcw validate` fails** in those projects while they name the old
  identifier. TCW-27 (a rename command for taxonomy and capabilities) and
  TCW-87 (following renamed slugs) are settled against this rule when the
  item is split.

### Versions and migration

- **This is TCW 4.0.** The changes are large enough for a new major
  version. 4.0 migrates 3.x projects; 2.x projects are not supported.
- **Every file TCW writes carries a version**: the configuration files,
  the manifests and the objects' state files, all of which are named
  `tcw-*.yaml` (so the manifests are `tcw-manifest.yaml` and
  `tcw-manifest.local.yaml`). The field's name is for the spec.
- **The version is the TCW CLI's version when the file was created or last
  migrated.** Ordinary edits never change it, so it records which format
  the file follows. A file created by 4.0 and later edited by 4.3 still
  says 4.0.
- **A file with no version is a 3.x file,** since 3.x never wrote one.
- **`tcw migrate`** migrates the active project, in place: every one of
  its files that is in an older format. It takes no project or object
  argument for now, and, like every change, never touches another
  project. To find a 3.x project, which has no `.tcw/` folder, it also
  recognises `tcw-config.yaml` at a project's root.
- **Other commands may migrate an object silently** when they touch it,
  for future migrations that change one kind of object at a time. The
  3.x-to-4.0 migration is whole-project only, since it moves the
  configuration and rewrites every reference together.
- **Related projects are migrated together.** 4.0 assumes every project
  it reaches is 4.x; the person runs `tcw migrate` in each one. A 3.x
  project that a 4.0 project reaches is reported as needing
  `tcw migrate`, not read.
- **`tcw migrate --dry-run`** lists every file and Jira ticket it would
  change, and changes nothing. (A ticket stores its item's slug in the
  "TCW Item" field, so migrating changes tickets too.)
- **`tcw migrate` does not check git.** It runs whether or not the working
  tree has uncommitted changes (see requirement 2).
- **A migration that stops partway can be finished** (`docs/use-cases.md`,
  S-8). It changes local files first and Jira tickets last, can be run
  again to finish, and never repeats a change already made. When it
  stops, it says what was done, what was not, and how to finish.
- **What it cannot convert, it reports** rather than guessing: for
  example a store named only in a personal file whose project is not on
  this machine.
- **A 3.x `extends` naming a sibling becomes a parent link:** the project
  it extended becomes one more parent. Siblings never extend each other in
  4.0; the parent link is the only way content is inherited. The
  conversion keeps exactly the content the project depended on, since the
  new parent entry's `inherit` lists only the axes the `extends` named,
  and `tcw migrate` prints each such conversion, and `--dry-run` lists it,
  for the person to review. An `extends` naming a project already inherited
  through another parent adds nothing, since 4.0 inheritance passes down
  every level (3.x `extends` did not, so it was often repeated).
- **The other 3.x relationships convert as follows:**
  - `parent` and `children` become parent and child IDs in
    `tcw-config.yaml`. Their paths become manifest entries, except where
    "Locating a project" would find the project anyway.
  - `upstream` becomes a parent link with `inherit` matching what the
    project's 3.x `extends` took from it (`inherit: none` if nothing),
    printed and listed for review. A sibling `extends` likewise becomes a
    parent link inheriting only the axes it named.
  - A 3.x override's `overrides:` pointer is kept, rewritten to a full
    identifier.
  - A connection's or a store's `repository` (address, branch, folder)
    goes into the manifest entry, with the branch carried over.
  - A store written both as a path and as a `repository` becomes one
    location: a plain path when the store is inside the project, otherwise
    a `.path` address from the root of the project whose folder holds it.
  - Work item slugs become full identifiers, in files and on tickets.

### The user's example, rearranged under this model

```
Docs-and-Plans
└── Shared-Libs
    ├── Desktop-App
    └── Server-App
```

Desktop-App and Server-App now inherit from Shared-Libs through the parent
link instead of `extends`. Docs-and-Plans still sees everything.
Shared-Libs sees itself and both apps. Desktop-App sees Shared-Libs and
Docs-and-Plans, but never Server-App, though it can still name an
object in Server-App by its full identifier.

## Open questions

None at the request level. The spec writes the remaining detail: the
shape of a manifest entry and its branch suffix, the version field's
name, the grammar of object IDs, the keys personal files may set, the new
work backend operations, and the migration step by step. Two of the
user's multi-repository setups were described to Claude in anonymized
form on 2026-10-21 and shaped the rules above; nothing specific to them
is recorded here, as they are private.

## Review history

A multi review on 2026-10-21 (Claude's adversarial spec reviewer, Codex,
and the local model on five slices, one of which timed out) gave
"proceed after fixes". The user decided eight questions it raised (load
order, identity, per-parent inheritance, which settings are inherited,
the planning workspace, cross-project blockers, a missing parent, and
item folders), and the accepted fixes are folded into the sections above.

## Next step

1. Check every case in `docs/use-cases.md` against this design and update
   the architecture cases (UC-1 to UC-8) to describe 4.0, as that
   document asks.
2. Write success criteria: what shows 4.0 is finished, and what result
   would show the model was wrong (for example, how many `null` or
   `inherit` overrides migrated projects need).
3. Work backwards: list every command, flag, configuration key, document
   and web view that has to change, and split this item into child items
   in dependency order. The renamed files, full identifiers, `.tcw/` and
   `tcw migrate` ship together; say how `main` stays releasable meanwhile.
4. Settle the related items: TCW-27 and TCW-87 (renames), TCW-22 and
   TCW-23 (become `--scope` and `tcw project provision` questions), TCW-85
   (answered here), TCW-50 (touches the same list commands), TCW-102 and
   TCW-103 (filing into other projects, which 4.0 drops).

## Origin

Design discussions with the user on 2026-10-20 (starting from TCW-98) and
2026-10-21 (from the user's notes on requirements, configuration, full
identifiers and locating projects). The user asked for this item as the
record of those discussions.

## References

- TCW-98 (discarded, replaced by this item): the request this design grew
  out of, with top-down views in every command and in `tcw serve`, and
  mixed capability status. Its comment of 2026-10-20 records the first
  part of the discussion.
- TCW-54 (discarded): the earlier web-only attempt at descendants'
  taxonomy and capabilities in `tcw serve`; lists the reference and
  overlap problems.
- TCW-68: the 3.0 rewrite in which descendant board aggregation was lost.
- TCW-22: the backlog audit ignores child projects; the same problem for
  one procedure.
- TCW-85: how a capability path names a connected project; largely
  answered by full identifiers, which are never shortened.
- `docs/guide/multi-repo.md`, `skills/configure/references/projects.md`,
  `docs/guide/taxonomy-and-capabilities.md`: today's three mechanisms.

No known blockers.
