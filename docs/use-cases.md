# Use cases: the setups TCW must work in

TCW is used in very different project setups. A change that is right for one
can quietly break another, and the defects found so far have mostly been of
that kind: code that assumed the work store sits inside the project's own
repository (issues #15-18, described in
[`lifecycle/implementation.md`](lifecycle/implementation.md)), and instructions
that never considered a requester talking to the agent directly (TCW-100) or an
epic whose parts live in other repositories (TCW-101).

This document lists the setups TCW is used in, or should expect to be used
in, and what each one requires of TCW. **Every spec in this repository names
the cases it touches** (the `## Use cases` section of the spec outline) and
says how the change behaves in each. "None" is an acceptable answer only with a
reason.

A few words used throughout:

- A **family** is a project together with every project connected to it
  through `projects:`.
- An **epic** is a parent item whose parts are separate child items.
- A **round** is a review or qa document written into an item's folder.
- A **handoff** is the note a session writes so another session can resume
  the work.

It is written for people changing TCW. How to set up each arrangement is in the
guides, chiefly [`guide/multi-repo.md`](guide/multi-repo.md) and
[`guide/jira.md`](guide/jira.md).

Each case is marked:

- **Seen**: a real project works this way today. Private projects are
  described by their shape under generic names (`core`, `app`, `workspace`),
  never by their own names or contents, because this repository is public.
- **Expected**: nobody has reported it yet, but TCW's design invites it, so it
  will happen. Its requirements are reasoned, not observed, and say so.

## Contents

- [How to use this document](#how-to-use-this-document)
- [What varies between setups](#what-varies-between-setups)
- Architectures
  - [UC-1 A single project in its own repository](#uc-1-a-single-project-in-its-own-repository)
  - [UC-2 A library other projects read](#uc-2-a-library-other-projects-read)
  - [UC-3 A monorepo of several projects](#uc-3-a-monorepo-of-several-projects)
  - [UC-4 Many repositories and a planning workspace](#uc-4-many-repositories-and-a-planning-workspace)
  - [UC-5 One Jira project shared by several TCW projects](#uc-5-one-jira-project-shared-by-several-tcw-projects)
  - [UC-6 A connected project that is not on this machine](#uc-6-a-connected-project-that-is-not-on-this-machine)
  - [UC-7 A library published to the public, read by private projects](#uc-7-a-library-published-to-the-public-read-by-private-projects)
  - [UC-8 Several separate families on one machine](#uc-8-several-separate-families-on-one-machine)
- Situations that cut across architectures
  - [S-1 Who decides, and whether they are present](#s-1-who-decides-and-whether-they-are-present)
  - [S-2 Which agent harness](#s-2-which-agent-harness)
  - [S-3 Which backend keeps the work](#s-3-which-backend-keeps-the-work)
  - [S-4 Copies of a checkout: worktrees, clones, other machines](#s-4-copies-of-a-checkout-worktrees-clones-other-machines)
  - [S-5 Personal configuration](#s-5-personal-configuration)
  - [S-6 Unattended and automated runs](#s-6-unattended-and-automated-runs)
  - [S-7 Several people at once](#s-7-several-people-at-once)
  - [S-8 Partial failure: offline, unreachable, half-finished](#s-8-partial-failure-offline-unreachable-half-finished)
  - [S-9 Upgrades: an old tcw, a new tcw, mixed versions](#s-9-upgrades-an-old-tcw-a-new-tcw-mixed-versions)
  - [S-10 Things TCW does not own that sit inside a project](#s-10-things-tcw-does-not-own-that-sit-inside-a-project)
  - [S-11 Version control](#s-11-version-control)
- [The checklist](#the-checklist)
- [Adding a case](#adding-a-case)

## How to use this document

When writing a spec:

1. Read the list of dimensions below and decide which ones your change touches.
   Most changes touch two or three.
2. For each architecture (UC) and situation (S) involving those dimensions,
   read its requirements and say in the spec's `## Use cases` section how your
   change meets each one, or why it does not apply.
3. Run [the checklist](#the-checklist).
4. If your change reveals a setup this document does not describe, add it
   ([Adding a case](#adding-a-case)) in the same change.

When reviewing, check that the spec's `## Use cases` section is honest: a
change to how a store is found that says "UC-4 not affected" deserves a hard
look.

## What varies between setups

These are the dimensions. A real setup is a combination of them.

| Dimension | Values seen or expected |
| --- | --- |
| Repositories | one repository; one repository holding several projects (monorepo); several repositories; a repository that holds only planning |
| Projects per family | one; a parent with children; children with their own children; a project read by others that names none of them (upstream) |
| Where each store is | inside the project (`docs/<component>/`); elsewhere in the same repository; in a different repository; not on this machine yet |
| Inheritance (`extends`) | none; one level; several levels (server → shared → core); different lists for taxonomy and capabilities |
| Work backend | files; Jira, one Jira project per TCW project; Jira, one Jira project for several TCW projects |
| Who is present | the person who decides, talking to the agent; an engineer, with the requester elsewhere (on Jira); nobody (unattended) |
| Harness | Claude Code; Codex; Pi; a person typing `tcw` themselves; a script or CI job |
| Machine | everything checked out; some connected projects missing; a linked worktree; a fresh clone; CI |
| Version control | git, which TCW reads but never changes; no version control (expected); a store in a repository other than the code's |

## Architectures

### UC-1 A single project in its own repository

**Seen.** TCW itself keeps its work in Jira (the `TCW` project) and its
documents under `docs/work/`. The library `core` of UC-2 keeps its work in
files.

```
my-project/            one git repository
├── tcw-config.yaml    no projects: section
└── docs/
    ├── taxonomy/
    ├── capabilities/
    └── work/
```

This is the simplest setup and the one every new user starts in. It is also
the one a change is most likely to be tested in, so its risk is the reverse of
the others: a change can work here and nowhere else.

**Requirements**

- With no `projects:` section, every command behaves as if the family were
  this one project. Nothing asks for a parent, warns about missing children,
  or reads the network for other projects.
- Every store defaults to `docs/<component>/` inside the project, with no
  configuration.
- The project works as soon as `tcw project new` has run, before any stage, hook or
  procedure is configured (TCW's built-in stage instructions apply).
- The project root is the nearest folder above the current directory holding
  a `tcw-config.yaml` file (`find_project_root` in `tcw/store/fs.py`), so any
  subfolder works as a starting point.
- A feature built for families must cost a single project nothing: no extra
  configuration, no extra output, no slower commands.

**Known gaps**: none recorded.

### UC-2 A library other projects read

**Seen.** A private library, here `core`, has its own repository and its own
TCW project, keeping its work in files. A family of applications reads it as
an **upstream** project, and their taxonomies inherit from it
(`taxonomy.extends: [core]`). Its own configuration names none of them.

```
core/                      its own repository; tcw-config.yaml with no projects:
app/tcw-config.yaml        projects.upstream.core: ../core
app/apps/server/...        taxonomy.extends: [shared, core]
```

A library is both a UC-1 project in its own right (its maintainers work it
alone) and a dependency of others. Its maintainers may never run anything
from the readers' side.

**Requirements**

- Nothing about a reader is written into the library: not its ID, its paths,
  or its work items. An upstream connection is declared by the reader alone
  ([`guide/multi-repo.md`](guide/multi-repo.md), "Reading a project that does
  not name you").
- From the reader, the library is read-only. Creating or changing anything in
  it (in 3.x, also through the `--project` option of `tcw work new` and the
  `--blocks` option of `tcw work edit`, both removed in 4.0) is refused
  with exit code 3.
- The library's own `projects:` connections are not followed from the reader,
  and a problem in them does not stop the reader.
- Renaming or removing a taxonomy term or capability in the library is a
  breaking change for its readers. Their links (`tcw://core/T/...`)
  break, and only the readers' `tcw validate` notices. Nothing in the library
  can see this. A change that renames entries must say what readers see.
- The library's maintainers must be able to work in it with no reader
  checked out.

**Known gaps**

- The library cannot know who reads it, so it cannot warn before a breaking
  rename. This is a deliberate cost of one-sided connections; TCW-27 (a rename
  verb) should consider readers.

### UC-3 A monorepo of several projects

**Seen.** A private product, here `app`, is one git repository holding four
TCW projects:

```
app/                       one git repository
├── tcw-config.yaml        id: app; children below; parent: the workspace (UC-4)
├── packages/shared/       id: shared;  taxonomy.extends: [core]
├── apps/server/           id: server;  taxonomy.extends: [shared, core]
│                                       capabilities.extends: [shared]
└── apps/mobile/           id: mobile;  same extends as the server
```

Each child declares `parent: app: ../..`, and the root declares
each child under `children:`. All four keep their work in the same Jira
project (UC-5), and their work stores sit in a different repository (UC-4).

**Requirements**

- Which project a command acts on depends on the current directory: the
  nearest `tcw-config.yaml` above it. From `apps/server`, `tcw work list`
  lists the server's items, not the monorepo root's. Instructions that tell an
  agent to run a command "from inside that project" depend on this. Any
  command that changes directory, or runs a hook, must keep it in mind.
- A project folder can sit inside another project's folder. Nothing may treat
  "inside a project's folder" as "belongs to that project": a project's
  contents end where a nested project begins.
- Inheritance can be several levels deep and differ per axis: the server
  inherits taxonomy from two projects and capabilities from one. Each
  inherited entry must be read from exactly one project, however many routes
  reach it. A bare reference to a name defined in two inherited projects is
  refused as ambiguous, never resolved to one of them (`get` in
  `tcw/store/fs.py`). A local term with the same name wins without a warning.
- An epic in the root project can have parts in the children. In 3.x, filing a
  part into a child went through the `--project` option of `tcw work new`,
  which is removed in 4.0; a part is made in the child, with
  `tcw -C <folder> work new "<title>" --parent <full id>` (the plan prompt's
  step 6). `tcw work edit` accepts
  a parent in another project; its check for parent cycles covers only the
  item's own project (`tcw/work/model.py`).
- A hook runs once per move, with the root of the project whose item moved
  as its current directory and with `TCW_PROJECT_ROOT` and `TCW_ITEM_PATH` set
  (`tcw/work/hooks.py`, `tcw/work/advance.py`). It may assume nothing about
  where that project sits in the repository: a project's hooks must work
  whether it is the repository's root or a subfolder. A cross-project filing
  runs none of the target project's hooks.
- Several projects share one git index. A hook that commits after a move must
  commit only the moved item's files, or one project's move includes
  another's unrelated changes. The shipped example,
  `docs/guide/examples/commit-item-after-move.sh`, does this.

**Known gaps**

- An item's `children:` line in `tcw work show` lists only children on its own
  board, not those filed into the other projects (TCW-102).
- `--parent` cannot be set when filing into another project (TCW-103).
- TCW-98 (descendants on all three axes) and TCW-99 (redesigning how projects
  relate) will change how a parent sees its children.

### UC-4 Many repositories and a planning workspace

**Seen.** A private `workspace` repository holds planning only: its own work
store and the work stores of the projects in `app`. Each of those projects
keeps its taxonomy and capabilities beside its code, and `core` keeps all
three of its stores in its own repository. The code lives in other
repositories, cloned inside it and ignored by it:

```
workspace/                 repository A: planning only; ignores everything it does not list
├── tcw-config.yaml        id: product; Jira APP; children: app; upstream: core
├── docs/
│   ├── work/              the workspace's own work store
│   ├── app/work/          the monorepo root's work store
│   ├── server/work/       the server's work store
│   ├── mobile/work/
│   └── shared/work/
├── app/                   repository B, its own clone (UC-3); work.path: ../docs/app/work
└── core/                  repository C, its own clone (UC-2); keeps its own store
```

Planning happens in one place; code changes happen in several. A single
piece of work often has a record in repository A and code in repository B,
committed separately.

**Requirements**

- **A project's root and its store's location vary independently.** Code that
  rebuilds a store's path from the project root plus `docs/work`, runs git in
  the project root to ask about the store, or treats "a `docs/work` folder
  exists" as "this is a project" is wrong here, usually without an error.
  Resolve a store through `work_path` / `open_backend` (`tcw/work/open.py`)
  and find the repository holding it with `git_root` (`tcw/store/fs.py`).
- **"Ignored by git, therefore not a project" is false.** The workspace
  ignores its child clones, which are projects. Any pruning of folders by
  git's ignore rules must stop at a nested repository and re-evaluate there.
  Projects are found from declared connections (`descendant_projects` in
  `tcw/store/fs.py` reads the registry, not the folder tree), and that must
  stay true.
- **A move in one project can leave files in another repository.** Filing into
  another project writes into that project's store, which may be in a third
  repository. TCW names each such file as "left uncommitted" in that
  repository (`_uncommitted_in` in `tcw/work/open.py`). It never commits:
  committing belongs to the project's own hooks and people.
- **A store with changes not yet committed blocks the next filing into it.**
  For a filesystem target the filing is refused; for a Jira target the ticket
  is created and stays in the Jira inbox (`_check_target` in
  `tcw/work/open.py`, `_cannot_make_item` in `tcw/work/jira/tickets.py`).
  Instructions that file several parts must say to record the changes between
  filings (TCW-101).
- **Hooks that commit must commit in the store's repository**, not the
  code's. This repository's example, `commit-item-after-move.sh`, is written
  for that.
- **A test of anything in this list needs two real git repositories in the
  fixture.** A single-repository fixture reproduces none of it
  ([`lifecycle/implementation.md`](lifecycle/implementation.md)).

**Known gaps**

- Two places still rebuild a store's path from the project root:
  `tree_store_present` in `tcw/store/fs.py` checks for a literal
  `docs/<component>` folder, and `tcw validate` falls back to `docs/work`
  when the work store cannot be found (`tcw/validate.py`). No item yet.
- TCW-22: the backlog audit should cover every connected work root.
- TCW-23: `tcw project provision` cannot be scoped, and a configuration three hops
  away can name a checkout directory.

### UC-5 One Jira project shared by several TCW projects

**Seen.** The five projects of UC-3 and UC-4 (`product`, `app`, `server`,
`mobile`, `shared`) all keep their items in one Jira project, here `APP`.
Each ticket's `TCW Project` field says which
TCW project it belongs to, and `TCW Item` holds its slug
([`guide/jira.md`](guide/jira.md)).

**Requirements**

- Every list of a project's items built from a Jira search keeps only the
  tickets whose `TCW Project` is this project. The filter is applied to the
  search results, not written into the query (`tcw/work/jira/jql.py` says
  why), so a search still fetches the other projects' tickets. An unfiltered
  list shows one project another's tickets, and an adoption can take a ticket
  into the wrong project; `tcw work tickets adopt` refuses a ticket set to
  another project.
- Ticket keys are unique across the Jira project, not per TCW project: the
  server's items and the mobile app's are numbered from one sequence (APP-257
  in the server, APP-262 in mobile). Nothing may assume a project's keys are
  consecutive or that a key's number says which project it belongs to.
- The inbox (Triage) is shared. A ticket with no `TCW Project` value yet
  belongs to no project, and every project sharing the inbox lists it. A
  person decides which project takes it, unless the cross-project filing that
  created it already set its `TCW Project`.
- A Jira workflow change made for one project affects all of them. `tcw
  validate --remote` in any one of them must report a status that a stage
  needs and the shared workflow no longer offers.
- Credentials are per person, not per project. Each project's configuration
  names the environment variables that hold them, so one person's values
  serve every project only when the projects name the same variables.

**Known gaps**

- A `tcw work list` fetches every ticket in the shared Jira project before
  keeping its own, so its cost grows with the whole family. No item yet.

### UC-6 A connected project that is not on this machine

**Seen** in part: a contributor to the server need not clone the mobile app.
**Expected** in full: a team where nobody has every repository.

A connection can name a `repository` to fetch the project from
(`projects.<relation>.<id>.repository`), and a store can name where to fetch
it (`work.repository`). `tcw project provision` fetches what is missing. A project
known only by a `jira` block in this project's entry for it can still receive
filed work, as a ticket in its Jira inbox.

**Requirements**

- A missing child or upstream must not break commands that do not need it:
  listing this project's items, moving them, reading its own records. A
  command that does need it says which project is missing and how to get it
  (`tcw project provision`), with a distinct exit code (5 for `tcw work show` of an
  item in a missing project).
- Reading another project's records over the network is never implicit.
- `tcw validate` reports references into a missing project as unresolved, not
  as broken.
- Filing into a project that is not here, with a `jira` block, creates the
  ticket and nothing else, and says so ([`guide/multi-repo.md`](guide/multi-repo.md),
  "Creating an item in another project", case 4).

**Known gaps**

- A project named in `taxonomy.extends` or `capabilities.extends` that is not
  on this machine stops every taxonomy or capabilities command in the reader,
  including reading its own entries, with exit 1 rather than 5. It also makes
  `tcw validate` fail with an error rather than report it as unresolved, so a
  fresh clone in CI fails (S-4). No item yet.
- In `tcw validate`, a `tcw://<id>/T/…` or `tcw://<id>/C/…` reference into a
  project that is not on this machine is reported as an error, not as
  unresolved. References to its work items are correctly unresolved. No item
  yet.
- TCW-23 (provision scoping).

### UC-7 A library published to the public, read by private projects

**Expected.** UC-2 with an access boundary: an open-source library whose
readers are private company projects. TCW's upstream connection was designed
for this ("A public library read by a private application must not carry the
application's name in its own files", [`guide/multi-repo.md`](guide/multi-repo.md)).

**Requirements** (reasoned)

- Nothing a reader does may publish its names, paths, ticket keys or work
  into the library, including through error messages a library maintainer
  might be sent, or through records written into the library's store.
- The reader must work with the library fetched read-only from a public URL,
  with no credentials for it.
- A reader's agent instructions must not suggest filing work into the library
  as if it were a family member; that is refused, and the right path is the
  library's own issue tracker (as the `extras-report` skill does for TCW
  itself: an issue on the library's public tracker).

**Known gaps**: none recorded; no such setup is known yet.

### UC-8 Several separate families on one machine

**Seen.** One developer's machine holds TCW itself, a small skills
repository, the workspace family of UC-4, and an older, retired copy of that
family that uses most of the same project IDs, with several folders inside it
that share one ID (copies and worktrees of the same project).

**Requirements**

- A project's family is what its configuration declares, never what happens
  to be nearby on disk. Two copies of a project with the same ID in different
  folders must not be confused. `TCW_PROJECT_<ID>`, when it is set and names
  a folder on this machine, decides; otherwise the declared path does.
- `TCW_PROJECT_<ID>` set for one family applies to every family on the
  machine that uses that ID. Anything that reads it must say where a project
  was found, so a stale variable is noticed.
- One user's `~/.claude` plugin, one `tcw` on the PATH, and possibly one
  editable install serve every family at once. A family that needs a
  different TCW version (S-9) needs its own environment.

**Known gaps**

- Only `tcw validate` says where a `TCW_PROJECT_<ID>` variable placed a
  project. Every other command uses it silently. No item yet.

## Situations that cut across architectures

### S-1 Who decides, and whether they are present

**Seen.** Three arrangements:

1. **The person who decides is talking to the agent.** The requester of a
   Jira ticket is often the engineer driving the agent. They say "move it on"
   or "accepted" in the conversation (TCW-100).
2. **The person who decides is elsewhere.** A product manager writes a Jira
   ticket and accepts work at QA by moving the ticket. They never see the
   agent. The engineer in the conversation is not the person who decides.
3. **Nobody is present.** An unattended run with advisors in place of the
   person (S-6).

**Requirements**

- At a stage the backend keeps (request and QA in Jira), a person decides.
  The agent moves the item only when that person tells it to, in the
  conversation. A question, an implied yes, or an instruction given before
  the person has seen the QA findings is not that.
- The agent must not assume the person in the conversation is the one who
  decides. When it is unclear, it asks.
- An advisor in an unattended run never stands in for the person who decides.
- Every move made on a person's word says who said it in the `--reason`
  text, which becomes a comment on the ticket ("Moved from X to Y. Reason:
  …"). TCW records a name only if the reason contains one, and a forward move
  does not require a reason.

### S-2 Which agent harness

**Seen.** Claude Code, Codex and Pi load the same `skills/` folder; people
also run `tcw` by hand ([`lifecycle/harness.md`](lifecycle/harness.md)).

**Requirements**

- Anything that must happen belongs in the `tcw` CLI, which behaves the same
  everywhere. A Claude-only feature (hooks, `!` command injection, agents)
  may only make something easier, never be the only way it happens.
- A stage's instructions come from `tcw work stage prompt`, and the prompt
  must stand on its own: an agent without TCW's skills reads only the prompt,
  ending with its generated last line saying how the item moves on. Rules
  that live only in a skill are missed by such an agent (the TCW-100 multi
  review found one).
- A person running `tcw` by hand reads the same messages an agent does.
  Messages must be complete sentences that say what to do next.

### S-3 Which backend keeps the work

**Seen.** Files (`core`) and Jira (TCW, the UC-3 and UC-4 family).

**Requirements**

- The abstraction litmus test ([`lifecycle/abstraction.md`](lifecycle/abstraction.md)):
  any operation on what a backend owns must be one a non-file store could
  implement.
- Text that differs by backend goes in backend passages, marked
  `<!-- backend: jira -->`, which only projects using that backend read.
- In Jira, the request and the QA verdict belong to Jira and its people; the
  repository holds the spec, plan and rounds. Nothing may copy a fact between
  the two.
- A filing that crosses backends (from a file-kept project into a Jira one, or
  the reverse) must work, and must say what it left unfinished.

### S-4 Copies of a checkout: worktrees, clones, other machines

**Seen.** Contributors to TCW use git worktrees, with a virtual environment
per worktree ([`CLAUDE.md`](../CLAUDE.md), "Working in a git worktree").
**Expected**: a project worked on from two machines, and CI checking out a
fresh clone.

**Requirements**

- A linked worktree has no copy of untracked files, such as
  `tcw-config.local.yaml` (S-5). TCW must behave sensibly when it is missing,
  and say what it is missing when that matters.
- A store whose `path` resolves inside a worktree and one that resolves to
  the primary checkout are different stores; nothing may silently use the
  other.
- A fresh clone in CI has no connected projects and no credentials. `tcw
  validate` there must run without them, and report what it could not check
  rather than failing for that reason (TCW-14 asks for this as a gate). Today
  this holds for a missing connected project, but not for a missing project
  named in `extends` (UC-6, known gaps).

### S-5 Personal configuration

**Seen.** `tcw-config.local.yaml`, beside `tcw-config.yaml` and not tracked,
holds one person's additions, such as their own stage instructions or
credential variable names ([`guide/configuration.md`](guide/configuration.md)).

**Requirements**

- A personal file may set only what the allowlist permits; shared keys are
  refused.
- When personal files changed what a command composed, the command says so
  (a `note:` on standard error), so a person can tell their own additions
  from the team's.
- Another project's personal file is never read: commands acting on another
  project use only its shared configuration.

### S-6 Unattended and automated runs

**Seen.** The `extras-autonomous-work` skill drives items without asking,
consulting advisors (Codex and a separate read-only agent) at each checkpoint.
**Expected**: TCW driven from a scheduled job or CI, with no harness at all.

**Requirements**

- An unattended run stops at a hard blocker: something it cannot resolve
  without a person. It never moves a Jira-kept QA,
  and moves a Jira-kept request only when the user's own instruction for that
  run explicitly said to.
- Nothing waits on standard input for longer than `TCW_STDIN_TIMEOUT` (2
  seconds by default); a terminal is never read, and hooks and git get no
  standard input (`tcw/stdin.py`, `tcw/work/hooks.py`). A command that would
  ask must refuse with a clear message and an exit code instead.
- Every decision taken without a person is recorded where a person will read
  it (the round, or the findings comment).
- Exit codes are the interface for scripts: they must stay stable and mean
  one thing each (`tcw/exit.py`). Today a missing project gives 5 from
  `tcw work` but 1 from `tcw taxonomy` and `tcw capabilities` (UC-6).

### S-7 Several people at once

**Expected**, and partly **seen** (people and agents working one Jira board
together).

**Requirements**

- Two people moving the same item at once: the second move must notice the
  item has moved, not overwrite it. A Jira transition that is no longer
  available fails cleanly, listing what Jira offered.
- Two people editing the same record through the web viewer: a save must name
  the revision it was edited from, and a stale save is refused (3.0.0 release
  notes).
- Item folders are named by ticket key, or by date plus title words, so two
  people collide only when they give the same title on the same day. On one
  machine the second is refused; across clones it shows up when the changes
  are merged.
- A handoff written by one session is read by another; it must say when it
  was written, and the reader must check for anything newer.

**Known gaps**

- A move does not check that the item is still at the stage it was read at.
  With files, a second move overwrites the first. In Jira, a move to the
  status the ticket already has counts as success. No item yet.

### S-8 Partial failure: offline, unreachable, half-finished

**Seen.** A cross-project filing that created the Jira ticket but could not
make the item (TCW-101). Jira discards a comment sent with a transition that
has no screen (the form Jira can show during a transition); `set_stage` in
`tcw/work/jira/backend.py` posts it separately.

**Requirements**

- Any operation with more than one step (create the ticket, then the folder,
  then move it) must, when it stops partway, say what was done, what was not,
  and the command that finishes it (for example
  `tcw work tickets adopt <KEY>`).
- With Jira unreachable, commands that need only the repository (reading a
  spec, writing a round, `tcw work path`) still work.
- A retry after a dropped connection must not repeat the half that succeeded
  (a second ticket, a duplicated comment). Comments meet this: after a dropped
  connection, `set_stage` looks for a comment that arrived since it started
  before posting again.

**Known gaps**

- A ticket creation that loses its connection reports "Jira could not be
  reached" without saying a ticket may exist, so a retry can create a
  duplicate. No item yet.
- Re-running `tcw work advance` after "the move may have happened" can move
  the item a second stage, because the target is worked out afresh. No item
  yet.

### S-9 Upgrades: an old tcw, a new tcw, mixed versions

**Seen.** The 2.x to 3.0 migration ([`migration-guide-2.8-to-3.0.0.md`](migration-guide-2.8-to-3.0.0.md));
a plugin updated while the CLI on the PATH stayed old.

**Requirements**

- New code must read every file an older version wrote, or refuse it with a
  message naming the migration guide. Retired configuration keys are refused
  this way (`refuse_retired_config` in `tcw/store/fs.py`).
- Old code reading files a newer version wrote is **not** a constraint. A
  project that upgrades upgrades everyone working on it.
- A family whose projects pin different TCW versions is expected. A command
  reading another project's configuration must refuse clearly on a key it
  does not know, rather than misreading it.
- The plugin and the CLI are released together, at one version. Under Claude
  Code the version check at session start reports a mismatch; Codex and Pi
  have no session-start hook, and rely on the skills telling them to run the
  check.

**Known gaps**

- A work store still in the 2.x layout is listed as empty by `tcw work list`,
  with exit 0; only `tcw validate` names the migration guide. A real private
  project on file storage is in exactly this state. No item yet.
- Unknown keys at the top level of `tcw-config.yaml` and under `taxonomy:` are
  accepted silently; only keys under `work:` and `projects:` are checked. No
  item yet.

### S-10 Things TCW does not own that sit inside a project

**Expected.**

- A dependency folder (`node_modules`, `vendor`, a virtual environment) can
  contain another package's `tcw-config.yaml`, if that package itself uses
  TCW. The current project is the nearest `tcw-config.yaml` above the current
  directory, so a command run from inside it would treat that package as the
  project. Connected projects are found only through declared connections,
  never by scanning folders, and that must stay true.
- Generated or build output (`build/`, `web-dist/`) can contain copies of
  shipped text. Searches for wording that must be gone should exclude it.
- A project's own `docs/` holds documents TCW does not own beside the stores.
  TCW must touch only its stores, and treat an item folder as a bounded set
  of files ([`lifecycle/abstraction.md`](lifecycle/abstraction.md)).

### S-11 Version control

**Seen**: git everywhere. **Expected**: a project with no version control, or
another system.

**Requirements**

- TCW reads git (finding a repository's root, checking a store for changes
  not yet committed, recognising a linked worktree). It never commits, pulls
  or pushes, or changes an existing repository; `tcw project provision` makes new
  clones. Committing, pulling and pushing belong to the project's hooks and
  people.
- TCW's shipped instructions name no git command and never tell an agent to
  commit (`test_no_shipped_text_names_git` in `tests/test_shipped_text.py`).
  Where an instruction needs it, it says "record the changes in the project's
  version control, the way that project does".
- Where a check depends on git (cross-project filing refuses a store that is
  not in a git repository), the refusal says so, rather than failing
  obscurely.

## The checklist

For each question, answer it in the spec or say why it does not apply.

1. **Where does it look for things?** Does it locate a project, a store or a
   file? Does it work when the store is in another repository (UC-4), the
   project is a subfolder of a monorepo (UC-3), or the project is not on this
   machine (UC-6)?
2. **Whose things does it touch?** Can it write into a project other than the
   current one? If so, is that project allowed to be written (not upstream,
   UC-2 and UC-7), and does it name every file it left uncommitted (UC-4)?
3. **Does it read across projects?** Does it follow connections, inherit
   records, or list another project's items? What happens with several levels
   of inheritance (UC-3), a missing project (UC-6), or a shared Jira project
   (UC-5)?
4. **Which backends?** Does it pass the abstraction litmus test, and does it
   behave the same for files and Jira (S-3)? Does every list it builds from
   a Jira search keep only this project's tickets (UC-5)?
5. **Who is it for?** Does it assume a person is present, or that the person
   present is the one who decides (S-1, S-6)?
6. **Which harness?** Is anything required carried only by a Claude feature
   (S-2)? Does the stage prompt alone say enough?
7. **What if it stops halfway?** Does it say what was done and how to finish
   (S-8)?
8. **What about the single project?** Does it cost a UC-1 project anything:
   configuration, output, time?
9. **What does an older or newer TCW see?** Does it change a file format or a
   key (S-9)?
10. **Does it test the setup it claims?** A store-location change tested with
    one repository proves nothing about UC-4.

## Adding a case

Add a case when a real project shows a setup this document does not
describe, or when a defect is traced to a setup nobody considered. Give it:

- **Seen** or **Expected**, with the real project described by its shape
  under a generic name (this repository is public: never a private project's
  name, keys, paths or contents), or the reasoning for expecting it;
- a layout sketch, where the layout is the point;
- requirements, each one a statement a reviewer can check against the code,
  with the file that shows it where there is one;
- known gaps, by work item, or "No item yet" until one is filed.

When a known gap's item is finished, remove it from the list in the same
change. When TCW-99 changes how projects relate, the architecture cases change
with it.
