# Spec — TCW 4.0: `--scope`, `--project` and a project's whole family in the CLI and the web app

Child 8 of 13 of TCW-99. It carries out these sections of the TCW-99 design
(`docs/work/TCW-99-…/design.md`): "Choosing what a list or show command
covers" (design.md:631-665), the web app's half of principle 4
(design.md:110-111) and of "Only the active project can be changed"
(`tcw serve` "is read-only for every object the project it runs in does not
own", design.md:586-587), "A listed child that is not on this machine"
(design.md:376-378), "Work is never inherited" (design.md:450-452), and the
`--project` and mixed-status sentences of "What is inherited"
(design.md:456-462). It delivers TCW-98 (discarded in favour of TCW-99) and
absorbs TCW-22 (the backlog audit across child projects).

**Order.** The children land on the `v4` branch in the order TCW-106,
TCW-107, TCW-110, TCW-108, TCW-111, TCW-109, TCW-112, TCW-114, then this item,
then TCW-115 (decided by the dispatching session, 2026-10-22; the blocker
links on Jira record it). So when this item starts:

- every object has a full identifier `<project>.<namespace>/<id-path>`, every
  command prints it, and every JSON document says `"schema": 2` (TCW-110
  Design 1, 4);
- a project's folder is found from its ID through the command's one registry
  (TCW-107 Design 2.12, TCW-110 Design 6.1);
- a project names its parents under `parents:`, each with what it passes down
  (`inherit`), and its children under `children:`, committed or personal; the
  registry answers `ancestors()`, `descendants()` (breadth-first),
  `declared_child_ids()` (here or not), `load_order(id)` for any project it
  can locate, and `sources(axis, id)`, raising `InheritedUnavailable` (exit 7)
  when a project that passes the axis cannot be read (TCW-108 Design 3.2,
  4.6, 5, 6.2);
- a project read other than as the active one is "read for itself": the
  variables naming it apply, its personal files do not (TCW-109 Design 5.2);
- taxonomy and capabilities are inherited by path: a project's **view** of an
  axis is each id-path once, combined from its sources, and every record
  carries `overrides` (TCW-112 Design 2, 3.3); `list --local` lists the
  project's own objects (TCW-112 Design 3.2);
- every command and web route that writes refuses an object another project
  owns, and the web router makes that check for every route its table marks
  as a write (TCW-114 Design 1.1-1.4).

File and line references to code are to commit `d2d02829` on `v4`, where only
TCW-106 has landed in `tcw/` and `web/`. TCW-108, TCW-110, TCW-111, TCW-112 and
TCW-114 rewrite much of what is cited, so the plan re-checks each reference
against what they land. "TCW-1nn Design n" refers to the numbered rules of
that item's spec.

Words used throughout:

- The **active project** (written `P`) is the project the command runs in
  (TCW-99 requirement 7), or the project `tcw serve` was started in.
- A project's **family** is the project, its **ancestors** (its parents,
  their parents, and so on) and its **descendants** (the children it lists,
  the children they list, and so on), never a sibling (TCW-108 Design 3.1).
- An **axis** is `taxonomy`, `capabilities` or `work`.
- A project's **own objects** on an axis are the objects in its own store
  (TCW-112's "own objects"); each is read **as its owner sees it**: combined
  over its owner's sources (TCW-112 Design 3.1, the full-identifier rows).
- A project's **view** of taxonomy or capabilities is TCW-112 Design 2's: every
  id-path any of its sources has an object at, once, as its **view object**
  (the chain's first member, TCW-112 Design 2.4).
- A **scope** is one of `own`, `up`, `down`, `all`: which of the family's
  projects a command covers (Design 1).
- A **row** is one object a listing prints (one line of its text output, one
  record of its `--json`).
- A project is **unavailable** to a command when the command covers it but
  cannot read what it needs from it (Design 1.6).
- **Breadth-first** order lists a project's children, then all of their
  children, then the next level, rather than following one branch to its end
  first.
- A **fixture** is the set of folders and files a test builds before it runs
  a command.

## Capability changes

- **New** `cli/choose-which-projects-a-list-or-show-command-covers`: `--scope
  own|up|down|all` on `tcw work list|show`, `tcw taxonomy list|show|search`
  and `tcw capabilities list|show|search`, default `own`; `up` adds the
  ancestors, `down` the descendants, `all` both, never a sibling. For work,
  `up` adds each ancestor's own items; for taxonomy and capabilities, `up`
  lists the project's view, what it inherits. `--project <id>` keeps only
  that project's own objects. A covered project that is not on this machine,
  or cannot be read, is named as unavailable on standard error and in
  `--json` whenever something of it is left out, never left out silently.
- **New** `capabilities/see-each-projects-status-for-a-capability`: with
  `--scope down` or `all`, each capability record lists the status each
  project in the scope gives it, marking a status a project inherits without
  ruling on it, and `show` prints them grouped by status.
- **Changed** `work/view-the-board`: `tcw work list` covers the scope's
  projects, each with its own items; `--parent` finds parts filed in other
  projects; `children` and `blocks` in each record are computed across the
  scope.
- **Changed** `work/read-a-work-item`: `tcw work show` finds a folder name or a
  ticket key in any project of the scope; `children` and `blocks` cover the
  scope.
- **Changed** `work/keep-work-items-in-jira`: projects of one scope that keep
  their items in one Jira project on one site, sign in as the same account and
  map their stages to the same statuses are read with one search.
- **Changed** `work/run-a-procedure`: the `audit-backlog` procedure covers the
  project's descendants and says which were unavailable (TCW-22).
- **Changed** `taxonomy/browse-the-term-forest`, `taxonomy/read-a-term`,
  `taxonomy/search-terms`, `capabilities/browse-capabilities-by-status`,
  `capabilities/read-a-capability`, `capabilities/search-capabilities`: the
  default covers only the project's own objects; inherited ones are shown with
  `--scope up`; `--local` is removed; `show` by id-path finds what the scope
  covers.
- **Changed** `cli/rely-on-one-output-contract`: a list or show document
  covering more than one project carries `projects`, naming each project the
  scope covers and why any was unavailable.
- **Changed** `web`: the app has a scope control and a project filter that
  match `--scope` and `--project`; it shows other projects' objects, links to
  them are followed, unavailable projects are named, and capabilities show
  each project's status.
- **Changed** `web/editing`: an object another project owns is shown without
  any control that changes it.
- **Changed** `cli/reference-a-tcw-object`: `tcw serve` follows a link to
  another project's object that is on this machine, rather than showing it as
  a labelled name (its description, `:6-8`, says the opposite today).
- **Changed** `web/see-jira-owned-work-read-only`: another project's Jira
  item, opened from a scoped board or a link, is read-only in its files too,
  and a scoped board's search count follows Design 3.5, not "one search, or
  two while a tag filter is ticked".
- **Taxonomy:** new `scope`; changed `local-web-app`.

## Problem

1. **Every list and show command covers one project and its inherited
   content, never its descendants.** `tcw work list` reads the active
   project's backend alone (`_list`, `tcw/work/cli.py:235-258`, one
   `backend.list(query)` at `:251`); `tcw work show` opens another project only
   when the argument names it (`resolve_item`, `:50-66`). `tcw taxonomy list`
   and `tcw capabilities list` cover the local entries plus those reached
   through `extends` (`list_all`, `tcw/store/fs.py:1785-1793`, `:2409-2423`),
   which TCW-112 replaces with the view. Nothing reads a descendant: the
   registry has `descendants()` (`tcw/store/base.py:284-286`;
   `tcw/store/project.py:289-300`), but `descendant_projects`
   (`tcw/store/fs.py:535-542`) has no caller (design.md:92-94). TCW-99 asks for
   `--scope own|up|down|all` on every list and show command (design.md:633-642).
2. **`--local` is the only coverage control,** and it says the opposite of the
   design's default: today's listings include inherited entries unless
   `--local` is given (`tcw/taxonomy/cli.py:68-69`, `:144`;
   `tcw/capabilities/cli.py:59-61`, `:232-233`), where the design's default is
   `own` (design.md:641-642).
3. **No way to keep one owner's results.** Nothing filters a listing by the
   project that owns each row (design.md:643).
4. **No mixed status.** A capability record carries one status
   (`_record`, `tcw/capabilities/cli.py:37-39`); nothing says how each project
   of a family rules on it (design.md:648-665).
5. **An epic's parts in other projects are invisible from the epic.** `children`
   and `blocks` are computed from the item's own project only (`item_record`,
   `tcw/work/record.py:25-44`, given `_readable(backend)`,
   `tcw/work/cli.py:136-142`), which `docs/use-cases.md` UC-3 records as a known
   gap (`:232-233`, TCW-102). TCW-114 makes a part in another project the
   normal way to split work (TCW-114 Design 3.1), so the gap widens.
6. **A shared Jira project is searched once per TCW project.** Each Jira
   backend's `list` searches the whole Jira project and keeps its own tickets
   afterwards (`tcw/work/jira/backend.py:466`, the filter at `:470`; the reason
   in `tcw/work/jira/jql.py:1-8`), so reading five projects that share one Jira
   project would fetch every ticket five times (`docs/use-cases.md` UC-5 known
   gap, `:339-340`).
7. **The web app serves one project.** The board reads the served project's
   backend alone (`board`, `tcw/serve/work.py:203-234`); an item page finds only
   that project's folders (`item_folder`, `:237-246`); the taxonomy and
   capabilities routes list the served store (`list_terms`,
   `tcw/serve/records.py:70-71`; `list_capabilities`, `:149-150`); a link to
   another project's object is drawn as a name that does not navigate
   (`resolve`, `:234-236`; `SlugLink`, `web/client/src/ui/work-views.tsx:56-84`;
   `docs/guide/web-viewer.md:17-19`). Before 3.0 it combined descendants' boards;
   the 3.0 rewrite lost that without a decision (design.md:88-91). Its only
   read-only display is the "inherited from" badge for taxonomy and capability
   entries (`EditOrInherited`, `web/client/src/ui/content-views.tsx:167-191`).
8. **The backlog audit covers one project** (TCW-22): the `audit-backlog`
   procedure starts from `tcw work list` alone
   (`tcw/work/procedures/audit-backlog.md:7`), so a parent's audit silently
   leaves its children's items out (`docs/use-cases.md` UC-4 known gap, `:301`).

## Goals

1. `--scope own|up|down|all`, default `own`, on every command that lists or
   shows objects, covering exactly the family's projects the design names and
   never a sibling.
2. `--project <id>` keeps only that project's own objects; an override and its
   original stay separate objects.
3. Work is never inherited: `up` and `down` add the other projects' own items.
4. Taxonomy and capabilities in `up` show the active project's view, and in
   `down` and `all` show each capability once with the status each project
   gives it.
5. A project the scope covers but cannot read is named, with the reason and
   how to fetch it, never left out silently.
6. Projects of a scope that share one Jira project, one sign-in and one
   mapping of stages to statuses are read with one search, and each still
   lists exactly what its own `list` gives.
7. `tcw serve` has a scope control and a project filter matching the CLI, shows
   other projects' objects without controls that change them, and relies on
   the server's refusal (TCW-114) for any write that reaches it, with every
   write route naming the object its key names by that object's owner.
8. A single project (UC-1) pays nothing: the default output and cost are
   unchanged, and no other project is opened.

## Non-goals

- **Ordering and limiting list output** (TCW-50, sequenced after this item).
  This item defines one default order for a listing that covers several
  projects (Design 3.1, 4.4) and nothing to choose another.
- **`tcw project info`, `path`, `list`** (TCW-115). Nothing here needs them.
- **Writing.** Every write command, and every web write route, is TCW-114's;
  this item adds no write and changes no refusal's wording. It changes only
  which object the work and files write routes name to TCW-114's ownership
  check, so that it is the owner's (Design 6.5). `--scope` and `--project` are
  accepted by list and show commands only.
- **Commands that do not list or show objects** keep their coverage: `tcw work
  tickets list` (the tickets it lists belong to no project yet,
  `docs/use-cases.md` UC-5, so there is no owner to scope by), `tcw work tags
  list`, `lifecycle`, `docs`, `procedure`, `stage prompt`, the `path` commands,
  `tcw capabilities drift` (which reads the view, TCW-112 Design 7.2), `tcw
  validate`, and the records gate.
- **A configured default scope.** The scope is a per-run option only, as
  TCW-50's requester chose for its options; no configuration key is added.
- **Looking at a project as another project sees it** (`--as`, which the design
  rules out, design.md:644-647). A full identifier already shows an object as
  its owner sees it (TCW-112 Design 3.1).
- **Reference suggestions in the web app** (`/api/options/work`,
  `_other_items`, `tcw/serve/work.py:545-569`) keep TCW-108's and TCW-114's
  rules.
- **The `search` procedure** (`tcw/work/procedures/search.md`) is unchanged;
  `tcw work list --scope` is available to it.
- **Guides, skills and `docs/use-cases.md`** beyond the passages that name the
  removed `--local` (Design 5): TCW-117. Notes lists what they must say.

## Design

Design 1-4 are the model: every store implements them, and Design 4.10 puts
the one rule that decides rows in `tcw/store/base.py`. Design 3.5 is private
to the Jira backend: the backend interface does not change. Design 5-7 are
what the CLI, the web app and the shipped text show.

### 1. The scope of a command

1.1. **The commands.** `--scope` and `--project` are options of exactly these
eight commands: `tcw work list`, `tcw work show`, `tcw taxonomy list`, `tcw
taxonomy show`, `tcw taxonomy search`, `tcw capabilities list`, `tcw
capabilities show`, `tcw capabilities search`. No other command accepts them;
given to one, argparse refuses them as unknown options (exit 2).

1.2. **Values.** `--scope` takes `own`, `up`, `down` or `all`; any other value
is a usage error (exit 2) from argparse's `choices`. With no `--scope` the
scope is `own`, on every axis (design.md:641-642).

1.3. **The projects a scope covers**, from the registry (TCW-108 Design 3.2):

| Scope | Covers |
| --- | --- |
| `own` | `P` |
| `up` | `P` and every ancestor in `P`'s load order, whatever each link's `inherit` says |
| `down` | `P` and every descendant |
| `all` | every ancestor, `P` and every descendant |

Ancestors are those of `load_order().ids` (TCW-108 Design 4), missing ones
included. Descendants are found breadth-first over `declared_child_ids()` of
`P` and of each descendant on this machine (TCW-108 Design 2.1, 3.1), so a
listed child that is not on this machine is covered, and its own children,
which nobody here can know, are not. `inherit` never narrows the projects a
scope covers (TCW-108 Design 5.3: it "does not change … the views of
TCW-113"): every ancestor is in `projects` (1.8), its work items are listed
under `up`, and `--project <ancestor>` lists its own objects (2.1). What `up`
and `all` list from ancestors on taxonomy and capabilities is `P`'s view,
which `inherit` does shape (Design 4.1; decided by the user, Notes). A sibling, an
ancestor's other descendants, and a descendant's other parents are never
covered (design.md:640), though any of them can still be named by a full
identifier (TCW-108 Design 3.7). Personal children (TCW-108 Design 2.1) are
covered, so a library's maintainer sees readers listed only in their own
`tcw-config.local.yaml` (design.md:363-370).

1.4. **Scope order.** The covered projects, in this order: the ancestors in
load order (farthest first), then `P`, then the descendants in the
breadth-first order of 1.3. Every listing and every `projects` array (1.8)
uses it.

1.5. **How another project is read.** A covered project other than `P` is
located through the command's one registry (TCW-110 Design 6.1) and read for
itself (TCW-109 Design 5.2): its own committed configuration and the
environment variables naming it, never its personal files. Its taxonomy and
capability objects are read as it sees them (TCW-112 Design 3.1); its work
items through its own backend.

1.6. **An unavailable project.** A covered project `Q` other than `P` is
unavailable to the command, with a **reason**, when the command needs to read
something from `Q` (its items, its own objects, or its view at a path) and that
read raises one of the **unavailability errors**:

- any `TcwError` (`tcw/errors.py:16`) except `UsageError` (`:55`) and its
  subclasses;
- the three store errors that are `ValueError`s rather than `TcwError`s:
  `StoreLocationUnusable`, `StoreDeclarationError` and `StoreNotProvisioned`
  (`tcw/store/base.py:50`, `:72`, `:94`);
- `yaml.YAMLError`, a file of `Q`'s that is not valid YAML, which `main`
  reports today as a message rather than as a fault (`tcw/cli.py:679-683`);
- `OSError`, a file of `Q`'s that cannot be read.

The plan keeps these as one tuple in the model, beside the function of 4.10,
so the CLI and the web app catch the same set. Any other exception, a plain
`ValueError` among them, is not a reason: it ends the command as it does today
(`tcw/cli.py:675-678`, exit 1), because an error nobody classified may be a
fault in TCW rather than a fact about `Q`. A `UsageError` is not a reason
either: the command's options are the same for every project, so a usage
error raised while reading `Q` is an error in the command. Design 3.2 says how
`--stage` avoids the one refusal that differs from project to project.

**What the catch surrounds.** Only the reads of `Q`. The command first reads
everything it needs from `P` (`P`'s items or own objects, and `P`'s view where
the scope needs it, 4.9), outside any catch, and only then reads each `Q`. So
a failure on `P`'s side stops the command (1.7) before any `Q` is read, and is
never reported as `Q`'s; a failure in a project only `Q` reaches, such as a
second parent of `Q`, is `Q`'s (AC 20).

The cases this item expects, each with its reason:

| # | `Q` | Reason |
| - | --- | --- |
| a | is not on this machine | TCW-107 Design 6.2's sentence, which names `tcw project provision <Q>` when its manifest entry gives a repository |
| b | has parent links that cannot be read (TCW-108 Design 6.6) | the problem, naming `Q`'s `.tcw/tcw-config.yaml`, raised as `InheritedUnavailable` by `sources(axis, Q)` when the link's project passes the axis |
| c | has its own store for the axis declared but not provisioned here, declared wrongly, or at a location that holds no usable store (`StoreNotProvisioned`, `StoreDeclarationError`, `StoreLocationUnusable`) | the store's own message, which for a store not provisioned names `tcw provision` |
| d | has a configuration key the command reads that is undecided or broken (TCW-109 Design 3, 5.2) | TCW-109's exit-7 or exit-1 message, naming `Q` |
| e | (taxonomy, capabilities) has a view that cannot be built: `sources(axis, Q)` raises, including for a source's store (TCW-112 Design 1.3's third case) | the `InheritedUnavailable` message, naming `Q` as the project inheriting |
| f | (work) has a backend that cannot answer (`Unreachable`, exit 5) or cannot name the person for `--mine` (Design 3.2, `ConfigError`) | the backend's message |
| g | has a store holding a record that cannot be read (an unreadable item, `BackendError`; a version problem, TCW-111 Design 1.5) | the store's message |
| h | has a file of its store that is not valid YAML or cannot be read | the loader's or the system's message, which names the file |

An unavailable project's objects are left out of the result, which says so
(1.8); its unavailability does not change the exit code.

1.7. **The active project is never unavailable.** Whatever stops a command
today when it reads `P` still stops it, with the same exit code: an unreadable
item of `P`, `P`'s Jira not reached (5), a gap in `P`'s configuration (7), or
`P`'s view not built where the scope needs it (Design 4.9). Reason: the person
asked about `P`; leaving `P` out would make the result answer a different
question. Two more things are never made unavailable:

- **the object an input names by its full identifier** (3.4, 4.8), wherever
  it is: it is what the person asked for, so a failure to read it ends the
  command as it does today (exit 5 for a project not on this machine, exit 7
  for its undecided configuration or its view). Only the other projects a
  `show` reads for `children`, `blocks` or `statuses` can be unavailable;
- **a problem TCW-108 and TCW-109 make a graph problem of `P`**: a
  descendant's committed `children:` list that fails its checks, and a
  descendant whose shared configuration file cannot be read (TCW-108 Design
  6.6; TCW-109 Notes, "Decided after the spec review", 22). The active
  project lists that descendant,
  so the problem is reported as those items say, not as an unavailability.

1.8. **What a command says about its scope.**

- **Standard error:** once per unavailable project, before any row,
  `warning: '<Q>' is unavailable, so its <what> are not listed: <reason>`,
  where `<what>` is `work items`, `taxonomy entries` or `capabilities`. A `show`
  says `… so its status is not shown: <reason>` instead (Design 4.6).
- **`--json`:** when the scope is not `own`, the document gains `projects`, an
  array in scope order of `{"id": <id>, "relation": <"ancestor" | "current" |
  "descendant">}`, each unavailable project's object adding `"unavailable":
  <reason>`. Under `own` the document is unchanged.
- **Only what is left out is reported.** A covered project the command needs
  nothing from is named in `projects` without `unavailable`, and gets no
  warning, whether or not it is on this machine, because its absence changes
  nothing in the result. That is so for the ancestors on taxonomy and
  capabilities under `up`, and on taxonomy under `all`, when no `--project`
  is given: those read ancestors only through `P`'s view (4.1), whose failure
  stops the command (4.9) rather than making a project unavailable. Under
  `all` on capabilities, `statuses` reads every covered project's view (4.6),
  ancestors included, so there an ancestor can be unavailable.
- **Standard output** keeps one full identifier per line for a listing
  (`cli/rely-on-one-output-contract`), and the record for `show`.

The design's "shown as present but unavailable, with the command that fetches
it" (design.md:376-378) is met by the warning and by `projects`: a listing's
text output has one identifier per line and an unavailable project has no
identifier to print.

1.9. **A project with no family pays nothing.** When `P` has no parents and
lists no children, every scope covers `P` alone: `up`, `down` and `all` print
exactly what `own` prints (with `projects` holding `P` alone under `--json`),
and no command of this item asks the registry to locate another project or
opens another project's store (UC-1). With no `--scope`, every command prints
what it prints after TCW-112 with `--local` (taxonomy and capabilities) or
exactly what it prints today (work).

### 2. `--project`

2.1. **What it keeps.** `--project <id>` keeps only `<id>`'s own objects among
what the scope covers: for work, `<id>`'s items; for taxonomy and
capabilities, `<id>`'s own objects as `<id>` sees them, each its own row, never
combined into another project's row (Design 4.3 does not apply). So an override
and its original are separate objects: in `app`, which overrides `core`'s
`cli/x`, `--scope up --project core` lists `core.capabilities/cli/x`, which
`--scope up` alone does not (design.md:459-461; TCW-112's handoff). Likewise
an ancestor that passes the axis to nobody between it and `P` has no row under
`up` (4.1), and `--scope up --project <that ancestor>` lists its own objects.
`--project <P>` gives the same rows as `--scope own`.

2.2. **It must be covered.** `<id>` must be a valid project ID and one of the
projects the scope covers (1.3), unavailable ones included; otherwise the
command refuses with a usage error (exit 2), reading nothing:

```
--project <id>: '<id>' is not covered by --scope <scope> in '<P>', which covers <ids in scope order>[; --scope <w> covers it | ; it is neither an ancestor nor a descendant of '<P>']
```

where `<w>` is the first of `up`, `down`, `all` that covers it. A project
covered but unavailable gives no rows, the warning of 1.8, and exit 0.
Reason: an empty result for a sibling would read as "it has nothing", which
is the silent incompleteness the design forbids (design.md:376-378).

2.3. **On `show`,** `--project <id>` makes an input that is not a full
identifier name `<id>`'s object: an id-path `X` names `<id>.<axis>/X` (as
TCW-112 Design 3.1 reads that identifier); a work folder name or ticket key is
looked up in `<id>`'s backend only. A full identifier whose project is not
`<id>` is a usage error naming both (exit 2).

### 3. Work items

3.1. **Listing.** `tcw work list --scope <s>` prints, in scope order, each
covered project's own items that match the query, each project's in the order
its backend gives them (TCW-50 changes order later). Work is never inherited
(design.md:450-452): no item appears under any project but its owner.

3.2. **The filters, across projects.** Each filter applies to every covered
project:

- `--stage`: the stage names are TCW's one table (`STAGES`), the same in every
  project. A project that does not enable a stage named has no item at it.
  So, for each covered project `Q` other than `P`, the caller removes from the
  query's stages those `Q`'s lifecycle does not enable (its `work.stages`,
  read for itself, 1.5: a fact of its configuration, which needs no network);
  when none remains, `Q` lists nothing and its backend is not asked. `Q`'s
  backend therefore never meets the refusal it gives today for a stage it does
  not enable (the Jira backend's "no Jira status is configured for this
  stage", `tcw/work/jira/backend.py:443-447`), and 1.6's rule that a usage
  error is never a reason has no exception. For `P` the query is passed
  unchanged, so the refusal stands (1.7).
- `--tag`: matched as today in each project; the "not in this project's
  registry" warning (`tcw/work/cli.py:245-247`) checks `P`'s registry only.
- `--parent <item>`: the item is parsed from `P` as today, and every covered
  project lists the items whose `parent` is it, so `tcw work list --scope down
  --parent <epic>` lists an epic's parts in other projects (TCW-114 Design
  3.1-3.3, including Jira's recorded parents).
- `--assignee <name>`: matched literally in each project, through each
  backend's own form (`account` for Jira, `tcw/work/jira/backend.py:458-460`).
- `--mine`: "who is running the command" is one person, named in each
  project's own form: for a files-backend project, `P`'s `user.name` (the
  person's name is not a fact of the project read, and that project's personal
  files are not read, 1.5); for a Jira project, the account its credentials
  sign in as. A covered project other than `P` that can name nobody is
  unavailable (1.6 f) with `_me`'s message (`tcw/work/cli.py:78-89`).
- `--all`: as today, in each project.

3.3. **`children` and `blocks` cover the scope.** Every record that `tcw work
list --json` and `tcw work show` print computes `children` and `blocks` from
the items of every covered project that is not unavailable (`item_record`'s
`items`, `tcw/work/record.py:25-27`), not only the item's own project. So `tcw
work show <epic> --scope down` lists the epic's parts in its descendants,
closing UC-3's known gap (`docs/use-cases.md:232-233`). Under `own`, today's
computation from the item's own project is kept.

3.4. **`show`.** The input names the item as follows:

- a full identifier: that item, in any project TCW can locate, whatever the
  scope (TCW-110 Design 6.1; exit 5 when its project is not on this machine,
  as today). The scope decides only `children` and `blocks` (3.3);
- a folder name (an id-path) or a ticket key: looked up in each covered project
  that is not unavailable, `P` first and then in scope order. One match is the
  item. None is not found (exit 4); under `own`, when a wider scope's lookup is
  not attempted, the message is today's. Several are a usage error (exit 2):
  `'<input>' names <n> items in --scope <s>: <full ids>; name one by its full
  identifier`.

3.5. **A shared Jira project is searched once: a search kept for one
command.** Each covered project is listed by its own backend's **list**, with
its own query, its own credentials and its own filter on `TCW Project`, as a
project's own list is today. The backend interface does not change. What
changes is private to the Jira backend: within one command, a search is made
once and its result kept, and a later search made in the same command with
the same **search key** is answered from what was kept instead of from Jira.
The search key is all of:

- the site;
- the account the credentials sign in as (the value of the variable
  `work.jira.credentials.email-env` names, `tcw/work/jira/config.py:34`), so
  a search is never answered with tickets fetched under another account's
  permissions;
- the exact search text (`jql.item_query`, `tcw/work/jira/jql.py:38`), which
  holds the Jira project, the custom field id for `TCW Item`, the statuses
  the query's stages map to, and any parent, assignee or labels;
- the fields requested (`read_fields`), which hold the field ids of `TCW
  Project` and `TCW Item`.

So projects that keep their items in one Jira project on one site, sign in
as the same account, use the same field ids and map their stages to the same
statuses, which is the usual UC-5 setup (a child inherits `work.jira` from
its parent, TCW-109), make one search between them; any difference makes
another search, which is what that project's own list would make. Each
project then keeps, from the result, the tickets whose `TCW Project` is that
project, exactly as its own `list` does (`tcw/work/jira/backend.py:470`), so
each list is exactly what that project's own **list** gives, and a ticket of
a TCW project outside the scope is never listed.

**How long a search is kept.** From `begin_command` to `end_command`
(`tcw/config.py:657-665`), the span the CLI already uses to read the active
project's configuration once (`tcw/cli.py:645`, `:693`); outside a command (a
library caller, a test) nothing is kept. `tcw serve` makes each request that
reads more than one project one command for this purpose. Nothing is kept
across commands, and nothing is written to disk. Each caller gets the result
as the search returned it, and none changes it.

Litmus verdict: no operation is added (abstraction section); any backend may
make the same saving privately.

### 4. Taxonomy and capabilities

4.1. **What a scope lists on taxonomy and capabilities** (decided by the user
on 2026-10-22, Notes). Ancestors are listed only through `P`'s view:

| Scope | Rows |
| --- | --- |
| `own` | `P`'s own objects |
| `up` | `P`'s view: each id-path once, as its view object (TCW-112 Design 2, 2.4) |
| `down` | one row per group (4.2, 4.3) of `P`'s own objects and the descendants' own objects |
| `all` | one row per group of `P`'s view objects and the descendants' own objects |

An ancestor that passes the axis to nobody between it and `P` therefore has
no row under `up` or `all`, though it is covered (1.3): it is named in
`projects`, and `--project <it>` lists its own objects (2.1). Reason: `up` is
how a person or an agent finds the vocabulary and the capabilities the
project can actually use, and listing an ancestor's terms the project does
not inherit would invite using them.

For an id-path `X` under `down` and `all`:

- the **scope objects** at `X` are `V(X)` and the own objects at `X` of every
  descendant that is not unavailable, each as its owner sees it;
- in `all`, `V(X)` is `P`'s view object at `X`, when `P`'s view has one; in
  `down`, `V(X)` is `P`'s own object at `X`, when there is one.

4.2. **Groups.** The scope objects at `X` fall into **groups**: an object is
in the same group as the object it overrides (its record's `overrides`,
TCW-112 Design 2.4), when that object is a scope object. In `all`, `V(X)`'s
group also holds every member of `V(X)`'s chain, the objects `P`'s view
combined at `X` (TCW-112 Design 2.1), so an ancestor's object that `P`
overrides counts in `statuses` (4.6), and a descendant's object that
overrides any of them joins that group. A group is everything connected by
these links.

4.3. **Rows** under `down` and `all`. A listing prints one row per group:
`V(X)` when the group holds it, and otherwise the group's one object that
overrides no other object of the group. (A group without `V(X)` is held
together by `overrides` links alone, and each object overrides at most one
other, so exactly one such object exists.) So:

- `down` lists `P`'s own objects, and each descendant's object that does not
  override one of them (directly or through another descendant's) as a row of
  its own. A descendant's override of an object `P` merely inherits is its own
  row in `down`, since `down` does not cover what `P` inherits; `all` puts that
  object back and groups the overrides under it. `all` is therefore the
  family's overview, one row per capability, and `down` answers "what do this
  project and its descendants declare" (AC 19; TCW-117's skills say so);
- `all` lists `P`'s view, with each descendant's override grouped under the
  view object it overrides, and each descendant's object that overrides
  nothing in the view as a row of its own;
- with `--project`, Design 2.1 applies instead.

4.4. **Order.** Rows are ordered by their id-path, compared folder name by
folder name (today's rule, `_ordered`, `tcw/taxonomy/cli.py:49-56`), then by
their owner's place in scope order.

4.5. **Filters and `search`.** `--namespace` keeps rows whose id-path's first
folder is the one named. `--status <s>` keeps, under `own` and `up`, rows whose
combined `Status` is `<s>`; under `down` and `all`, rows of which any entry of
`statuses` (4.6) has `<s>`, so `--status Supported --scope down` in a library
finds what any descendant supports. `search` covers the rows of the scope and
matches each row's own combined name and body (TCW-112 Design 3.2), not those
of the objects grouped under it.

4.6. **The status each project gives a capability** (mixed status, `down` and
`all` only, design.md:648-665). Each capability row's record, and the record
`show` prints, gains `statuses`: for each covered project `Q` that is not
unavailable, in scope order, whose own view object at `X` is in the row's
group, one entry `{"project": "<Q>", "status": <its view object's combined
Status, or null>, "inherited": <bool>}`. `inherited` is true when `Q` has no
own object at `X`, or has one that does not set `Status` (the rule of TCW-112
Design 7.2, "never ruled on here"), and false otherwise. A view object is in
a group when its full identifier (its chain's first member's, TCW-112 Design
2.4) is that of an object in the group, so a project that inherits `X`
unchanged counts in the group of the object it inherits. So a project counts
once per capability, and a project that inherits a status without changing it
counts with that status, marked (design.md:653-655). Under `own` and `up` no
record has `statuses`: one project's view decides one status.

The text form of `tcw capabilities show` under `down` or `all` adds, after the
record's fields:

```
status by project:
  <Status>: <id>[ (inherited)], <id>…
  …
  unavailable: <id>, …
```

one line per status, in the order each status first appears in scope order
(which gives the design's `Missing(1), Supported(1), Omitted(1)` order for its
example, design.md:651-652), the projects on each line in scope order; a
`null` status is written `(no status)`; the `unavailable:` line names the
covered projects that were unavailable, and is left out when none was.
Plain listings print no status, as they print none today: each line stays one
full identifier, and the summary of a list is in its `--json` records
(`statuses`), in `show`, and in the web app's rows (Design 6.9). This departs
from the design's "a list shows a short summary" (design.md:649-651) and from
the request's "a summary in lists", and was decided by the user on
2026-10-22 (Notes).

4.7. **What overrides an object, in `down` and `all`.** Each taxonomy and
capability record gains `overridden-by`: the full identifiers of the scope
objects whose `overrides` is this object, in their owners' scope order (empty
when none). `show` prints `overridden by: <full ids>` after TCW-112's
`overrides:` line when there are any. So a descendant's override grouped into
another row (4.3) is still marked, as the design asks of every override
(design.md:467-470).

4.8. **`show`.** The input names the object as follows:

- a full identifier: that object as its owner sees it, whatever the scope
  (TCW-112 Design 3.1). In `down` and `all`, when it is a scope object or
  `V(X)`, its record carries 4.6 and 4.7 for its group; otherwise neither key;
- an id-path `X` under `up`: `P`'s view object at `X`, which is exactly one
  object or none, so `show X --scope up` is never ambiguous;
- an id-path `X` under `down` and `all`: the row at `X` of the scope's listing
  (4.3). One row is shown. None is not found (exit 4). Several (two groups at
  `X`, such as two descendants each with a new object at `X`, or two
  descendants each overriding an object `P` only inherits, under `down`) are
  a usage error (exit 2): `'<X>' names <n> objects in --scope <s>: <full
  ids>; name one by its full identifier`.

Under `own`, an id-path names `P`'s own object only. When `P` has none at `X`
but its view has one, the not-found message adds `; '<P>' inherits <full id>
there: add --scope up, or name it by that full identifier`. Building the view
for that hint never changes the outcome: when the view cannot be built, the
hint is left out and the command still exits 4. The design settles this
default for `show` as for `list` ("The default is `own` on every axis", under
the heading for list and show commands, design.md:631-642).

**This changes TCW-112 Design 3.1 for `show` only.** TCW-112's first row,
"an id-path `X` names the object at `X` in the active project's view", stays
true for every other reader of an id-path: `add`, `set`, `reset` and `rm`
(TCW-112 Design 4.1-4.4), the web app's `PATCH` route keys (TCW-114 Design
1.4), and `tcw://` links that give an id-path (TCW-110 Design 2). `list` and
`search` take no id-path; what they cover is the scope's (4.1). So in a
reader, `tcw capabilities set cli/x --status Supported` still finds the
inherited `cli/x`, while `tcw capabilities show cli/x` needs `--scope up`.
This item replaces two rows of TCW-112 Design 3.5's table, "which commands
need inherited content":

| Command | Needs the view because |
| --- | --- |
| `list` and `search` under `up`, `down` or `all` (under `own` they need none) | they list the view, or group under it (4.1, 4.9) |
| `show` of an id-path under `up`, `down` or `all`, or of another project's full identifier; `show` of an id-path under `own` only for its hint, which never changes the outcome | the object comes from another project, or is grouped with others |

4.9. **Which scopes need `P`'s view.** `up`, `down` and `all` need `P`'s view
(4.1, 4.6), and stop with `InheritedUnavailable` (exit 7, TCW-112 Design 3.5)
when it cannot be built. Only `own` reads `P`'s own objects without it,
exactly as TCW-112 Design 3.4 reads them for `--local`: each record marked
`partial`, the warning on standard error, exit 0. An ancestor that passes the
axis to `P` is part of `P`'s view, so its absence stops the command (1.7); an
ancestor that passes it to nobody below is read only for `--project <it>`
and, on capabilities under `all`, for `statuses` (1.8), and is unavailable
(1.6) when it cannot be read there.

**Why `down` stops rather than degrading as `own` does.** `down` covers no
ancestor, but it needs `P`'s view all the same: `V(X)` is `P`'s own object as
`P` sees it, combined over `P`'s sources, and `P`'s entry in `statuses` is its
view object. A `down` that degraded would also find every descendant that
inherits through `P` unable to build its own view, for the same cause, and
would report each of them unavailable, naming the missing project once per
descendant. That puts a failure on `P`'s side on each `Q`, which 1.6 rules
out. Stopping with exit 7 names the cause once, where it is. `own` is the
command that keeps working, as TCW-112 Design 3.4 keeps it.

4.10. **One store-neutral function.** Given, for an id-path, each covered
project's own declarations, each object's `overrides`, `V(X)` and its chain,
each covered project's view object, and the scope, Design 4.1-4.7 compute the
groups, the rows, `statuses` and `overridden-by` without reading a file. The
function lives in `tcw/store/base.py` beside TCW-112 Design 2.6's combination,
so another kind of store uses the same rule.

### 5. `--local` is removed

5.1. `tcw taxonomy list --local` and `tcw capabilities list --local` are
refused as a usage error (exit 2), before anything is read:

```
list --local is removed in TCW 4: --scope own, the default, already lists only this project's own objects; drop --local
```

The option stays in the parser only to give this message and is hidden from
`--help` (argparse's `SUPPRESS`); the message has the shape of TCW-114
Design 2.1-2.2's refusals of removed options. Reason: with
`own` the default, `--local` and `--scope own` would be two spellings of one
thing; TCW-112's handoff states the equivalence ("`--scope own` is
`--local`").

5.2. **Passages that name it** change here, since the shipped-text scans would
fail (`test_documented_verbs_and_flags_exist`,
`tests/test_documented_cli_surface.py`): `README.md:413`,
`skills/capabilities/SKILL.md:176`, `docs/guide/taxonomy-and-capabilities.md:32`
and `:98`, and the capability records `taxonomy/browse-the-term-forest` and
`capabilities/browse-capabilities-by-status` (rewritten in implement, in this
repository's 3.x layout, as TCW-112 Design 8.2 does). Each says that the
default lists the project's own objects and `--scope up` adds the inherited
ones. The plan's sweep is `grep -rn -- '--local' skills/ agents/ tcw/ README.md
docs/guide docs/capabilities`, ignoring `tcw-config.local` and
`manifest.local`.

### 6. The web app

6.1. **Query parameters.** These read routes take `scope` and `project` query
parameters with the CLI's values and rules (1.2, 2.2): `GET /api/work`, `GET
/api/work/<key>`, `GET /api/taxonomy`, `GET /api/taxonomy/<key>`, `GET
/api/capabilities`, `GET /api/capabilities/<key>`. An unknown `scope`, or a
`project` that 2.2 refuses, answers `400` with `{"code": "usage"}` and 2.2's
message. With no `scope`, the scope is `own`.

6.2. **Answers.**

- `GET /api/work` keeps its envelope and its rule that `items` is exactly what
  `tcw work list [--all] [--tag …] --json` prints (`board`,
  `tcw/serve/work.py:203-207`), now with the same `--scope` and `--project`, and
  adds `projects` (1.8) when the scope is not `own`. The fallback of a project
  whose backend cannot answer (`:216-226`) applies to `P` alone; any other
  project is unavailable (1.6).
- `GET /api/taxonomy` and `GET /api/capabilities` answer an object: `{"terms":
  [...]}` and `{"capabilities": [...]}`, each array exactly the records `tcw
  <axis> list --scope … --json` prints, plus `projects` when the scope is not
  `own` (today's bare array, `tcw/serve/records.py:70-71`, `:149-150`, goes).
- the detail routes answer the records `show --json` prints for the same
  input and scope, inside today's envelope, plus `projects` when the scope is
  not `own`.
- `GET /api/project` gains `scopes`: `{"own": [...], "up": [...], "down":
  [...], "all": [...]}`, each the IDs 1.3 covers, in scope order, unavailable
  ones included.
- `InheritedUnavailable` answers `503` with `{"code": "inherited-unavailable"}`
  (TCW-112 Design 4.5), which settles TCW-108's plan, choice 7.

6.3. **Route keys.** The route key of an object the served project owns is its
id-path; of every other object, in any namespace, its whole full identifier,
percent-encoded in the URL (TCW-110 Design 4.5, which states it for inherited
taxonomy and capability entries; here it applies to work items too).

6.4. **Any object TCW can locate can be read.** A work route key names an
item in one of two ways, decided by one function, the **work route key**
rule, used by every work and files route, read or write:

- a full identifier (`<project>.work/<folder>`, percent-encoded) names that
  project's item at that folder. Its owner is the project the identifier
  names, read from the identifier alone, without opening anything;
- anything else (a folder name or a ticket key) names an item of the served
  project, found as `item_folder` finds it today (`tcw/serve/work.py:237-246`),
  so its owner is the served project.

Each read route (`GET /api/work/<key>`, `GET /api/work/<key>/files/…`, `GET
/api/work/<key>/declaration`) reads the item from its owner: its files and
declaration from the owner's store, and its record, request and comments
through the owner's backend, read for itself (1.5), inside the scope or not,
as `show` does (3.4). A backend that cannot answer degrades as today
(`degrading`, `tcw/serve/work.py:85-98`). The taxonomy and capability detail
routes already take a full identifier as their key (TCW-110 Design 4.5,
`find_tree`) and read the owner's object as `show` does (4.8). `POST
/api/resolve` answers `{"ok": true, "axis": …, "key": <full id>}` for a link
to another project's object that exists, in any namespace; `other-project`
(`tcw/serve/records.py:234-236`) stays only for a project that is not on this
machine.

6.5. **Every write names the object by its owner.** TCW-114 Design 1.4 has
the router call the ownership check, before the route's own code runs, with
the objects each write route's `writes` function names; TCW-114's plan (Step
4) makes the work and files routes' function answer "the item the path names
(`item_folder`, made into the active project's full identifier)". That label
is right only while `item_folder` can name nothing but the served project's
items. With 6.4, a key can name another project's item, so this item changes
those functions: every work and files write route's `writes` (`PATCH
/api/work/<key>`, `POST /api/work/<key>/comments`, `PUT
/api/work/<key>/files/<path>`, `POST /api/work/<key>/files`, `PUT
/api/work/<key>/declaration`) answers the full identifier the work route key
rule gives, with the **owner's** project in it. So a write to
`desktop.work/<folder>` served from `shared` is checked as `desktop`'s object
and refused, `403 {"code": "read-only"}` with TCW-114 Design 1.3's message,
whether or not the item exists, and nothing is read or written.

The write handlers themselves resolve a key only within the served project:
a folder name or ticket key through `item_folder`, and the served project's
own full identifier to its folder; a full identifier naming another project
answers 404. So even a write route whose `writes` were missed could not reach
another project's folder: it would answer 404, never write. The
taxonomy and capability `PATCH` routes need no change: their `writes`
resolves the key with `find_tree` and answers the owner's full identifier
already (TCW-114 plan, Step 4). This item adds no write route.

6.6. **The scope control and the project filter** (client). The header gains
a scope control offering `own`, `up`, `down` and `all`, labelled with what each
covers, default `own`, shown only when `scopes.all` (6.2) names more than one
project. Beside it, a project filter offers the projects of the current
scope's `scopes` entry and "all of them" (the default), matching `--project`.
Both are kept in the URL's query string (`?scope=down&project=desktop`) on
every path, so a link reproduces the view and names the CLI flags it matches,
and both apply to all three axes. Changing either reloads the lists (today's
`loadBoard` and `loadRecords`, `web/client/src/ui/app.tsx:257-279`) with the
same parameters.

6.7. **Read-only display** (client). A record whose `owner` is not the served
project shows a badge `owned by <owner>`, and no control that would write:
no Edit button (replacing `EditOrInherited`'s "inherited from" badge,
`web/client/src/ui/content-views.tsx:167-191`), and on a work item's page no
property form, comment box, file editing, new-file action or declaration
editing. Board and tree rows of another project carry the same badge. A link
to another project's object navigates to its page (6.4), replacing
`SlugLink`'s non-navigating label (`web/client/src/ui/work-views.tsx:56-84`)
for any object the server resolves `ok`. The server refuses any write that
reaches it anyway (6.5).

6.8. **Unavailable projects** (client). When a list answer's `projects` names
an unavailable project, the page shows one notice per such project above the
list, with its reason, which names the fetch command where 1.6 a gives one.

6.9. **Mixed status** (client). Under `down` and `all`, each capability row in
the list and tree shows a summary built from its `statuses`: each status with
its count, in the order of 4.6, as `Missing(1), Supported(1), Omitted(1)`
(design.md:651-652). The capability page shows one line per status with its
projects, those marked `inherited` saying so, and each project that has an own
object at the path linked to that object's page, which shows it as that
project sees it (design.md:652-653). An `unavailable` line lists the
unavailable projects.

6.10. **The bundle is rebuilt** (`pnpm build`, into `tcw/serve/dist`) and the
client's tests cover 6.6-6.9.

### 7. Shipped text

7.1. **The `audit-backlog` procedure covers the family** (TCW-22;
`tcw/work/procedures/audit-backlog.md`, printed by `tcw work procedure
audit-backlog`, and already changed by TCW-114 Design 9.2). Its start becomes:
start with `tcw work list --scope down --json`, which lists every unfinished
item of this project and of each descendant; name every project in its
`projects`, and report each one marked `unavailable` as not audited, with its
reason, never as clean. The per-item reporting stays per item, grouped under
one heading per project in scope order; the across-items checks (duplicates,
missing blockers) read the whole scope, and read `tcw work list --scope down
--all` where they read `tcw work list --all` today; a blocker in another
project is looked up with `tcw work show <its full identifier>`. Its final
check compares `tcw work list --scope down --all --json` before and after.

7.2. **Command help.** Each of the eight commands' `--scope` and `--project`
help strings say what Design 1.3 and 2.1 say in one line each; their examples
gain one `--scope` example each, as their neighbours' contracts do
(`tcw/cli_help.py`'s `command`).

7.3. **Documentation entries** (`tcw work docs`). The release note and the
changelog get this item's `upcoming/` files. `README.md` (Public-API) and the
passages of 5.2 change here; the skills (`skills/work`, `skills/taxonomy`,
`skills/capabilities`), the guides (`docs/guide/cli.md`,
`docs/guide/web-viewer.md`, `docs/guide/taxonomy-and-capabilities.md`,
`docs/guide/multi-repo.md`, `docs/guide/jira.md`) and `docs/use-cases.md` are
TCW-117's, as the dispatching session decided for the siblings on 2026-10-22:
nothing ships between the 4.0 children, and TCW-117 lands before TCW-118 cuts
the release. Notes lists what each must say.

## Abstraction litmus test

| Operation | Layer | Verdict |
| --- | --- | --- |
| The projects a scope covers, and scope order (Design 1.3, 1.4) | model | Passes: questions about declared links, answered by the registry's `ancestors`, `descendants`, `declared_child_ids` and `load_order` (TCW-108 Design 3.2), which any store implements. |
| Reading another project for itself; an unavailable project (Design 1.5, 1.6) | model | Passes: "declared but not readable here" is a state any registry reaches (TCW-108's verdict for `sources`). Locating its folder is TCW-107's deployment layer. |
| `--project` (Design 2) | model | Passes: a filter on each row's owner, a fact every object has (TCW-110 Design 1.4). |
| Work listing and show across projects; `children` and `blocks` across the scope (Design 3.1-3.4) | model | Passes: each project's items come from its own backend's **list**, **read** and **lookup**; nothing reads a folder. |
| A search kept for one command (Design 3.5) | private to the Jira backend | Not an operation: every project is still read by its own **list**. Keeping a result for one command, keyed by site, account, search text and fields, is a saving any backend can make or skip without changing an answer. |
| Groups, rows, `statuses`, `overridden-by` (Design 4.1-4.7, 4.10) | model | Passes: computed in `tcw/store/base.py` from declarations, `overrides` and the registry's answers, without reading a file. |
| `show` by id-path or full identifier in a scope (Design 4.8) | model | Passes: by path and owner, both store-neutral (TCW-110 Design 1). |
| `--local` refused (Design 5) | CLI | Not a store operation. |
| Web query parameters, answers, route keys, the client's controls and display (Design 6) | CLI and web | Presentation of model answers; the server reads only through the operations above. |
| The procedure text and command help (Design 7) | shipped text | Not an operation. |

The work backend interface is unchanged.

## Use cases

- **UC-1 (a single project).** No parents or children: every scope covers the
  project alone and opens nothing else (1.9). The one change a single project
  sees is TCW-112's default made explicit: `tcw taxonomy list` and `tcw
  capabilities list` list its own objects, which, with no parents, is
  everything; and `--local`, which changed nothing for it, is refused with a
  message naming the fix (5.1). The scope control is hidden in the web app
  (6.6).
- **UC-2 and UC-7 (a library others read; a public library).** From a reader,
  `--scope up` shows the library's objects read-only; nothing is written into
  it (Non-goals; 6.5). The library names none of its readers, so from the
  library `down` covers nothing of theirs, unless its maintainer lists readers
  in their own `tcw-config.local.yaml` (TCW-108 Design 2.1), which this item
  covers (1.3) while nobody else sees them. A reader fetched from a public URL
  needs no credentials for it: reading another project's taxonomy and
  capabilities needs only its files (1.5). Nothing a reader runs prints its
  names into the library's files.
- **UC-3 (a monorepo).** A root with listed children sees every child with
  `down` (1.3), each child's items and objects read from its own folder; an
  epic in the root lists its parts in the children with `show --scope down`
  (3.3), closing that known gap. Each child is read from its own configuration
  through the one registry (1.5), wherever it sits in the repository.
- **UC-4 (a planning workspace).** The workspace's items are its own; `tcw work
  list --scope down` in the workspace lists each code project's items, read
  through that project's own configuration, whose work store may be a folder
  of the workspace's repository (TCW-110 Design 7). A code project not cloned
  is unavailable with the fetch command (1.6 a). The audit covers every
  descendant (7.1), closing the TCW-22 gap.
- **UC-5 (one Jira project for several TCW projects).** A scope's projects that
  share one Jira project, sign in as one account and map their stages alike
  are read with one search, and each still keeps only its own tickets by `TCW
  Project` (3.5), so a sibling's tickets in the same Jira project are never
  shown. Projects whose people use different accounts, as UC-5 allows when
  they name different credential variables, are searched separately, so no
  project is shown tickets fetched under another account's permissions. The
  inbox's tickets, which belong to no project, keep `tcw work tickets list`
  (Non-goals). The known gap that a list's cost grows with the whole family is
  narrowed for scoped listings: the cost is one search per account and
  workflow mapping, not one per project.
- **UC-6 (a related project not on this machine).** A missing child or
  ancestor that the command needed something from is unavailable, named with
  the fetch command, and the rest of the listing exits 0 (1.6 a, 1.8); one
  whose absence changes nothing in the result, such as an ancestor that
  passes nothing under `up` on taxonomy, is named in `projects` and warns of
  nothing (1.8). An ancestor that passes taxonomy or
  capabilities to `P` is part of `P`'s view, so `up`, `down` and `all` stop
  with exit 7 as TCW-112 does, and `own` still works (4.9).
- **UC-8 (several families on one machine).** Projects are found only through
  the command's one registry (1.5); two families with the same IDs are told
  apart by it (TCW-107).
- **S-1 (who decides).** Nothing here decides anything; every command is a
  read. The audit stays read-only and asks for approval as before (7.1).
- **S-2 (harness).** Everything is in the CLI; the web app's controls each
  match a flag (6.6), and the audit procedure is CLI-shipped text, the same
  under every harness.
- **S-3 (backend).** Both backends answer every operation, and the interface
  is unchanged; the Jira backend's saving is private to it (3.5). A scope that
  mixes files and Jira projects reads each through its own backend.
- **S-4 (copies of a checkout, CI).** In a fresh clone the descendants are
  usually not present, and a present one may keep its taxonomy or
  capabilities in another repository not yet provisioned: each is
  unavailable, with exit 0 (1.6 a, c; AC 29). A linked worktree's family is
  TCW-107's.
- **S-5 (personal configuration).** Only `P`'s personal files are read; a
  project read for itself takes its variables only (1.5, TCW-109 Design 5.2).
  `P`'s personal children are covered (1.3), and change only what that person
  sees.
- **S-6 (unattended runs).** Exit codes keep their meanings: an unavailable
  project other than `P` is not a failure, so a script that needs completeness
  reads `projects` in `--json`, where every unavailable project is named with
  its reason (1.8). `P`'s own failures keep their codes (1.7).
- **S-7 (several people).** Read-only; nothing here writes.
- **S-8 (stopping halfway).** Nothing writes, so nothing is left half-done; a
  project that fails to read partway is unavailable, and the result says so.
- **S-9 (versions).** No file format changes. JSON documents gain `projects`,
  `statuses` and `overridden-by` only under scopes that did not exist before,
  and keep `"schema": 2`, since nothing ships between TCW-110 and this item
  (TCW-112 Design 3.3's reasoning). A record of a covered project whose files
  carry a newer version is unavailable (1.6 g).
- **S-10 (things TCW does not own).** Projects are reached only through
  declared links (1.3); nothing looks inside a project's folders for others.
- **S-11 (version control).** Nothing reads or changes git.

The checklist: (1) it finds projects only through the registry, in other
repositories too (UC-4), and names those not here (UC-6); (2) it writes
nothing; (3) it reads across projects along declared links, several levels
(1.3), with a missing project unavailable or, where `P`'s view needs it,
exit 7, and a shared Jira project read once per account and filtered per
project (UC-5); (4) it passes the litmus test with no new interface
operation; (5) nobody's decision is assumed (the user's decisions are in
Notes); (6) the CLI carries
everything and the web app mirrors it; (7) nothing has more than one step;
(8) a single project pays nothing (1.9); (9) no file format changes, and the
removed `--local` gives a message; (10) the criteria use projects in separate
folders, one in a second git repository (AC 25), and projects absent from the
machine (AC 8, 21, 22).

## Acceptance criteria

**The family `F`** is used by most criteria. Each project is a TCW 4.0 project
in its own folder, side by side, keeps its work in files unless a criterion
says otherwise, and is located by a manifest entry:

- `docs` has no parents and `children: [shared, other]`;
- `shared` has `parents: [{id: docs, inherit: none}]` and `children: [desktop,
  server, mobile]`;
- `desktop` and `server` each have `parents: [shared]`;
- `other` has `parents: [docs]` (a sibling of `shared`);
- `mobile` is listed by `shared` and named in `shared`'s
  `.tcw/tcw-manifest.yaml` at a folder that does not exist, with `repository:
  https://example.invalid/mobile.git`.

Objects: `shared` has capabilities `abc` (`name: Abc`, `Status: Missing`) and
`ghi` (`Status: Missing`) and the term `invoice`; `desktop` has its own `abc`
holding only `Status: Supported`, and `def` (`Status: Supported`, complete);
`server` has its own `abc` holding only `Status: Omitted`; `docs` has the term
`plan`. Each of `docs`, `shared`, `desktop`, `server` and `other` has one
unfinished work item, `2026-10-01-<id>-item`. An object "complete" or "with"
fields is as TCW-112's criteria define. "In `x`" means run in `x`'s folder.
Unless a criterion says otherwise, a command exits 0.

1. **The eight commands.** In `shared`, each of the eight commands of Design 1.1
   accepts `--scope down` and exits 0 (each `show` given an object it names).
   `tcw work tickets list --scope up`, `tcw work tags list --scope up` and `tcw
   capabilities drift --scope up` exit 2. `tcw work list --scope sideways`
   exits 2.
2. **`own` is the default.** In `desktop`, `tcw capabilities list` prints exactly
   `desktop.capabilities/abc` and `desktop.capabilities/def`, the same as with
   `--scope own`; `tcw taxonomy list` prints nothing; `tcw work list` prints
   exactly `desktop.work/2026-10-01-desktop-item`. Each `--json` document has no
   `projects` key.
3. **Scope order and `projects`.** In `shared`, `tcw work list --scope all
   --json` has `projects` with ids, in order, `docs`, `shared`, `desktop`,
   `server`, `mobile`, relations `ancestor`, `current`, `descendant`,
   `descendant`, `descendant`; only `mobile`'s entry has `unavailable`, whose
   text contains `tcw project provision mobile`. Its standard output (without
   `--json`) is the four items of `docs`, `shared`, `desktop`, `server`, in that
   order; standard error has one line starting `warning: 'mobile' is
   unavailable, so its work items are not listed`.
4. **Never a sibling.** In `shared`, no scope's `tcw work list` prints an item of
   `other`, and no `projects` array names `other`. `tcw work list --project
   other --scope all` exits 2 with a message containing `is neither an
   ancestor nor a descendant of 'shared'`, and prints nothing on standard
   output. `tcw work show other.work/2026-10-01-other-item` in `shared` exits 0.
5. **`up` and `down` for work.** In `desktop`, `--scope up` prints the items of
   `docs`, `shared` and `desktop` and not `server`'s; in `shared`, `--scope down`
   prints those of `shared`, `desktop` and `server`, and not `docs`'s.
6. **`--project`.** In `shared`, `tcw work list --scope down --project desktop`
   prints only `desktop`'s item; `--scope own --project desktop` exits 2 with a
   message containing `--scope down covers it`; `--scope down --project mobile`
   prints nothing, gives `mobile`'s warning, and exits 0; `--project Bad_Id`
   exits 2.
7. **A single project opens no other.** In a project `solo` with no parents and
   no children, each of the eight commands with each scope prints the same
   standard output as with `--scope own`; and a test that records every call
   of `project_folder` and every store opened sees, for each, only `solo`'s.
8. **An unavailable child in taxonomy and capabilities.** In `shared`, `tcw
   capabilities list --scope down` and `tcw taxonomy list --scope down` each
   give one `warning: 'mobile' is unavailable` line and exit 0;
   `tcw capabilities show abc --scope down` prints the line `unavailable:
   mobile` in its `status by project:` block, and its standard error has one
   line starting `warning: 'mobile' is unavailable, so its status is not
   shown`.
9. **`up` is the view.** In `desktop`, `tcw capabilities list --scope up`
   prints exactly `desktop.capabilities/abc`, `desktop.capabilities/def`,
   `shared.capabilities/ghi`; each record of its `--json` has the `overrides`
   TCW-112 gives (`shared.capabilities/abc` for `abc`, `null` for the others)
   and no `statuses` key.
10. **An ancestor that passes nothing is covered, and listed only by
    `--project`.** In `desktop`, `tcw taxonomy list --scope up` prints
    exactly `shared.taxonomy/invoice`; its `--json` has `projects` with ids,
    in order, `docs`, `shared`, `desktop`, relations `ancestor`, `ancestor`,
    `current`, and no `unavailable`. `tcw taxonomy list --scope up --project
    docs` prints exactly `docs.taxonomy/plan`; `tcw taxonomy show plan --scope
    up` exits 4; `tcw taxonomy show docs.taxonomy/plan --json` has `full-id`
    `docs.taxonomy/plan`. With `docs`'s folder removed (its manifest entry
    kept), `tcw taxonomy list --scope up` exits 0, prints
    `shared.taxonomy/invoice`, and gives no warning naming `docs`; `tcw
    taxonomy list --scope up --project docs` exits 0, prints nothing, and
    warns that `'docs' is unavailable`.
11. **`--project` keeps an override and its original apart.** In `desktop`,
    `tcw capabilities list --scope up --project shared` prints exactly
    `shared.capabilities/abc` and `shared.capabilities/ghi`, and `--project
    desktop` prints exactly `desktop.capabilities/abc` and
    `desktop.capabilities/def`.
12. **Grouped rows in `down`.** In `shared`, `tcw capabilities list --scope
    down` prints exactly `shared.capabilities/abc`, `desktop.capabilities/def`,
    `shared.capabilities/ghi`, in that order.
13. **`statuses` and `overridden-by`.** In 12's listing with `--json`, the `abc`
    record has `statuses` equal to `[{"project": "shared", "status": "Missing",
    "inherited": false}, {"project": "desktop", "status": "Supported",
    "inherited": false}, {"project": "server", "status": "Omitted",
    "inherited": false}]` and `overridden-by` equal to
    `["desktop.capabilities/abc", "server.capabilities/abc"]`; the `ghi` record
    has `statuses` `shared` `Missing` false, `desktop` `Missing` true, `server`
    `Missing` true, and `overridden-by` `[]`; the `def` record has `statuses`
    with the one entry `desktop` `Supported` false.
14. **`show` prints the status by project.** In `shared`, `tcw capabilities show
    abc --scope down` and `tcw capabilities show shared.capabilities/abc --scope
    down` each print, after the fields, these five lines, in this order and
    with these indents (two spaces before each status):

    ```
    status by project:
      Missing: shared
      Supported: desktop
      Omitted: server
      unavailable: mobile
    ```

    and the line `overridden by: desktop.capabilities/abc,
    server.capabilities/abc` (one line). `tcw capabilities show abc` (scope
    `own`) prints neither `status by project:` nor `overridden by:`.
15. **A status inherited without a ruling.** With `server`'s `abc` holding only
    `Priority: P2` instead of `Status`, the `abc` record of 13 has the entry
    `{"project": "server", "status": "Missing", "inherited": true}`, and 14's
    block begins:

    ```
    status by project:
      Missing: shared, server (inherited)
      Supported: desktop
    ```
16. **`--status` across the scope.** In `shared`, `tcw capabilities list --scope
    down --status Supported` prints exactly `shared.capabilities/abc` and
    `desktop.capabilities/def`; `tcw capabilities list --status Supported`
    (scope `own`) prints nothing.
17. **`show` by id-path follows the scope.** In `desktop`, `tcw capabilities
    show ghi` exits 4 with a message containing `--scope up` and
    `shared.capabilities/ghi`; `tcw capabilities show ghi --scope up --json`
    has `full-id` `shared.capabilities/ghi`. With `shared`'s folder removed,
    `tcw capabilities show ghi` exits 4, not 7.
18. **Two groups at one path.** `desktop` and `server` each also have a new,
    complete capability `zz`, which `shared` does not have. In `shared`, `tcw
    capabilities list --scope down` lists both `desktop.capabilities/zz` and
    `server.capabilities/zz`; `tcw capabilities show zz --scope down` exits 2
    with a message naming both; `tcw capabilities show zz --scope down
    --project server --json` has `full-id` `server.capabilities/zz`; `tcw
    capabilities show desktop.capabilities/zz --scope down --project server`
    exits 2 with a message naming `desktop` and `server`.
19. **What `down` leaves out, `all` puts back.** `docs` passes capabilities
    (`shared`'s link to `docs` set to `inherit: all`), `docs` has a capability
    `xyz` (`Status: Missing`, complete), and `desktop` and `server` each have
    their own `xyz` holding only a `Status`. In `shared`, `--scope down` lists
    `desktop.capabilities/xyz` and `server.capabilities/xyz` and not
    `docs.capabilities/xyz`; `--scope all` lists `docs.capabilities/xyz` once
    and neither override, and its `--json` record's `statuses` names `docs`,
    `shared` (inherited), `desktop` and `server`, in that order.
20. **A descendant whose view cannot be built.** `desktop` also has a second
    parent `ext`, with `inherit: [capabilities]`, located by a manifest entry
    at a folder that does not exist. In
    `shared`, `tcw capabilities list --scope down` exits 0, prints
    `shared.capabilities/abc` and `shared.capabilities/ghi` and nothing of
    `desktop`'s, warns `'desktop' is unavailable` with a reason containing
    `'desktop' inherits its capabilities from project 'ext'`, and the `abc`
    record's `statuses` has no `desktop` entry. In `desktop`, `tcw capabilities
    list --scope up` exits 7.
21. **`P`'s view is needed outside `own`.** In `desktop` with `shared`'s folder
    removed: `tcw capabilities list` exits 0 and its `--json` records have
    `"partial": true` (TCW-112 Design 3.4); `tcw capabilities list --scope up`,
    `--scope down` and `--scope all` each exit 7. A failure on `P`'s side is
    not put on a descendant: with `shared`'s link to `docs` set to `inherit:
    all` and `docs`'s folder removed, `tcw capabilities list --scope down` in
    `shared` exits 7, and its standard error has no line containing
    `is unavailable`.
22. **A descendant whose configuration is undecided.** `server` keeps its work
    in Jira (`work.backend: jira`) and takes `work.jira` from a second parent
    `cfg` that passes `config` and is not on this machine. In `shared`, `tcw
    work list --scope down` exits 0, prints the items of `shared` and
    `desktop`, and warns `'server' is unavailable` with TCW-109's message
    naming `server`. In `server`, `tcw work list` exits 7. In `shared`, `tcw
    work show server.work/2026-10-01-server-item` exits 7: an object named by
    its full identifier is never made unavailable (Design 1.7).
23. **A project read for itself.** `server`'s `.tcw/tcw-config.local.yaml` holds
    text that is not valid YAML. In `shared`, `tcw work list --scope down` exits
    0 and prints `server`'s item; in `server`, `tcw work list` exits 1.
24. **`tcw work show` in a scope.** In `shared`, `tcw work show
    2026-10-01-desktop-item` exits 4; with `--scope down` it shows `desktop`'s
    item (`full-id` `desktop.work/2026-10-01-desktop-item`). With a folder of
    the same name also in `server`, `--scope down` exits 2 with a message naming
    both full identifiers.
25. **An epic's parts across projects.** `shared` has an item `epic`, and
    `desktop`, kept in a second git repository beside `shared`'s, has an item
    `part` with `parent: shared.work/<epic>`. In `shared`, `tcw work show
    <epic> --json` has `children` `[]`; with `--scope down` it has `children`
    `["desktop.work/<part>"]`; `tcw work list --scope down --parent
    shared.work/<epic>` prints exactly `desktop.work/<part>`.
26. **A stage another project does not enable.** `server` keeps its work in
    Jira (a fake Jira) and does not enable `review`, so maps no status to it.
    In `shared`, `tcw work list --scope down --stage review` exits 0, gives no
    warning about `server`, and the fake records no search; `tcw work list
    --scope down --stage review --stage spec` makes one search, whose
    statuses are `spec`'s alone. In `server`, `tcw work list --stage review`
    exits 2.
27. **`--mine` in each project's own form.** `shared`'s personal file sets
    `user.name: ann`; `desktop`'s item is assigned to `ann`; `server` keeps its
    work in a fake Jira whose credentials sign in as account `a-1`, and its item
    is assigned to `a-1`. In `shared`, `tcw work list --scope down --mine`
    prints exactly `desktop`'s and `server`'s items.
28. **One search per shared Jira project and account.** `shared`, `desktop`
    and `server` keep their work in one Jira project `APP` on one site (a fake
    that counts searches), with the same field ids, the same stage statuses
    and credential variables whose email values are the same, and so does
    `other`. In `shared`, `tcw work list --scope down` makes exactly one
    search naming `project = "APP"` that is not a key search, prints the same
    items, project by project, that `tcw work list` prints in each of the
    three, and prints no item of `other`. With `desktop` moved to a Jira
    project `DESK` on the same site, it makes exactly two such searches, one
    naming `project = "APP"` and one naming `project = "DESK"`. With
    `desktop` back in `APP` but its credential variables holding a different
    email, it makes exactly two searches naming `project = "APP"`, the one
    for `desktop` signed in with `desktop`'s email. A second `tcw work list
    --scope down` makes its own search again: nothing is kept between
    commands.
29. **A descendant whose own store is not provisioned.** `server`'s
    capabilities store is declared in another repository
    (`https://example.invalid/server-caps.git`) that has not been provisioned
    on this machine. In `shared`, `tcw capabilities list --scope down` exits
    0, prints exactly `shared.capabilities/abc`, `desktop.capabilities/def`,
    `shared.capabilities/ghi`, and warns `'server' is unavailable` with a
    reason containing `tcw provision`; the `abc` record's `statuses` has no
    `server` entry. Separately, with `desktop`'s `def` folder holding a
    `meta.yaml` that is not valid YAML, the same command exits 0 and warns
    `'desktop' is unavailable` with a reason naming that file.
30. **`--local` is removed.** `tcw taxonomy list --local` and `tcw capabilities
    list --local` exit 2 with a message containing `--scope own` and `drop
    --local`; `tcw taxonomy list --help` and `tcw capabilities list --help` do
    not contain `--local`.
31. **`search` in a scope.** In `desktop`, with `shared`'s `ghi` description
    holding `Ledger text`: `tcw capabilities search "Ledger text"` prints
    nothing; with `--scope up` it prints `shared.capabilities/ghi`.
32. **Row order.** In `shared` with 18's `zz` objects, `tcw capabilities list
    --scope down` prints `desktop.capabilities/zz` before
    `server.capabilities/zz`, and every row in id-path order (`abc`, `def`,
    `ghi`, `zz`, `zz`).
33. **Web: scope and project parameters.** `tcw serve` in `shared`: `GET
    /api/capabilities?scope=down` answers an object whose `capabilities` equals
    the `capabilities` of `tcw capabilities list --scope down --json` and whose
    `projects` names `mobile` as unavailable; `GET /api/capabilities` answers an
    object with `capabilities` and no `projects`; `GET /api/work?scope=sideways`
    and `GET /api/work?scope=down&project=other` answer 400 with `code`
    `usage`; `GET /api/project` has `scopes.down` equal to `["shared",
    "desktop", "server", "mobile"]`. `GET /api/work?scope=down` answers
    `items` equal to the records of `tcw work list --scope down --json`,
    `projects` naming `mobile` as unavailable, and `fallback` false; with
    `desktop`'s work kept in a fake Jira that cannot be reached, it answers
    `fallback` false and `projects` naming `desktop` as unavailable, while
    served from `desktop` itself `GET /api/work` answers `fallback` true
    (Design 6.2: the fallback is `P`'s alone).
34. **Web: another project's object, read-only.** `tcw serve` in `shared`,
    with `K` the key `desktop.work%2F2026-10-01-desktop-item`: `GET
    /api/work/K` answers 200 with that item's record, and `GET
    /api/work/K/files/<one of its files>` and `GET /api/work/K/declaration`
    answer 200 with what `desktop`'s folder holds. Each of `PATCH
    /api/work/K`, `POST /api/work/K/comments`, `PUT /api/work/K/files/<that
    file>`, `POST /api/work/K/files` and `PUT /api/work/K/declaration`
    answers 403 with `code` `read-only` and a message containing `belongs to
    project 'desktop'`, and afterwards every file under `desktop`'s folder is
    byte for byte what it was; so does a `PATCH` of
    `desktop.work%2Fno-such-item`. `GET
    /api/capabilities/desktop.capabilities%2Fabc?scope=down` answers 200 with
    that record. `POST /api/resolve` with
    `tcw://desktop.work/2026-10-01-desktop-item` answers `ok` with that full
    identifier as `key`; with `tcw://mobile.work/x` it answers `other-project`.
35. **Web: the client.** The client's tests show: the scope control is hidden
    when `scopes.all` has one project and otherwise offers `own`, `up`, `down`,
    `all`, default `own`; choosing `down` requests the three lists with
    `scope=down` and puts `?scope=down` in the URL; a capability whose `owner` is
    not the served project shows `owned by <owner>` and no Edit button; a
    board row and a tree row of another project's object show the same
    badge; another project's work item page has no property form, comment
    box, file editing, new-file action or declaration editing; an unavailable
    project's notice shows its reason; a
    capability row under `down` shows `Missing(1), Supported(1), Omitted(1)` for
    13's `abc`, and its page lists each status with its projects, `inherited`
    marked.
36. **The bundle.** `pnpm build` in `web/client` leaves `tcw/serve/dist` equal to
    what is committed, and the client's test suite passes.
37. **The audit procedure covers the family.** `tcw work procedure
    audit-backlog` prints text containing `tcw work list --scope down --json`,
    `unavailable` and `tcw work list --scope down --all --json`, and no line
    telling the agent to start from a bare `tcw work list`.
38. **`--tag`, `--assignee` and `--all` across projects.** `desktop`'s item
    carries the tag `ui`, which is in `desktop`'s `work.tags` and not in
    `shared`'s, and is assigned to `ann`; `desktop` also has a completed item
    `2026-10-02-desktop-done`. In `shared`: `tcw work list --scope down --tag
    ui` prints exactly `desktop.work/2026-10-01-desktop-item`, and its
    standard error has exactly one line, `warning: tag 'ui' is not in this
    project's registry`; `tcw work list --scope down --assignee ann` prints
    exactly `desktop.work/2026-10-01-desktop-item`; `tcw work list --scope
    down --all` prints `desktop.work/2026-10-02-desktop-done` and `tcw work
    list --scope down` does not. With `server` in a fake Jira whose user `ann`
    has account `a-1`, and `server`'s item assigned to `a-1`, `--scope down
    --assignee ann` also prints `server`'s item.
39. **Shipped text.** `test_every_command_named_in_shipped_text_exists` and
    `test_documented_verbs_and_flags_exist` pass, and Design 5.2's sweep finds
    no `--local` given to a `list` command.
40. **`--namespace`, and `search` matching a row's own text.** `shared` also
    has a complete capability `cli/run`, and `desktop` an override of it
    whose body holds `Desktop words`. In `shared`: `tcw capabilities list
    --scope down --namespace cli` prints exactly `shared.capabilities/cli/run`;
    `tcw capabilities search "Desktop words" --scope down` prints nothing;
    with `--project desktop` it prints `desktop.capabilities/cli/run`.
41. **The suite passes as CI runs it** (bare `pytest`).

### Coverage

Each design rule against the criteria that check it. A cell reading `n/a`
gives the line that makes it so.

| Design rule | Criteria |
| --- | --- |
| 1.1 the eight commands; others refuse the options | 1 |
| 1.2 values; default `own` | 1, 2 |
| 1.3 projects covered: ancestors whatever `inherit`, descendants breadth-first with missing listed children, never siblings, personal children | 3, 4, 5, 10; personal children: n/a as a separate criterion, they reach the scope only through `declared_child_ids()`, whose meaning TCW-108 Design 3.2 fixes and TCW-108's own criteria test (its Design 2.1) |
| 1.4 scope order | 3, 10, 13, 19, 32 |
| 1.5 another project read for itself | 22, 23 |
| 1.6 the unavailability errors; a usage error is never a reason | 20, 22, 29 (the store errors and `yaml.YAMLError`), 26 (no `--stage` refusal reaches `Q`); a plain `ValueError` ending the command: n/a as a criterion, it is today's behavior of `main` (`tcw/cli.py:675-678`), unchanged |
| 1.6 the catch surrounds only reads of `Q` | 20 (a second parent of `Q` is `Q`'s), 21 (a failure on `P`'s side names no descendant) |
| 1.6 a not on this machine | 3, 6, 8, 10 |
| 1.6 b links unreadable | n/a as a criterion: it raises through the same `sources(axis, Q)` as 1.6 e (TCW-108 Design 6.6), which 20 checks |
| 1.6 c `Q`'s own store not provisioned, declared wrongly, or unusable | 29 (not provisioned); the other two are the same tuple of 1.6 and the same catch, n/a as separate criteria |
| 1.6 d configuration undecided | 22 |
| 1.6 e view not built | 20 |
| 1.6 f backend cannot answer, `--mine` | 27 (the person named in each backend), 33 (`Unreachable`, in the web app) |
| 1.6 g a record cannot be read | n/a as a separate criterion: `BackendError` (`tcw/work/fs_backend.py:335-339`) is a `TcwError`, caught by the same tuple as 22's |
| 1.6 h a file not valid YAML or unreadable | 29 (YAML); `OSError`: n/a as a separate criterion, the same tuple |
| 1.7 the active project never unavailable; a full identifier's object never unavailable; graph problems | 21, 26 (the stage refusal stays in `server` itself), 22 (exit 7 in `server` itself, and for `server`'s item by full identifier); graph problems: n/a here, TCW-108 Design 6.6 and TCW-109's decision 22 define them and their criteria test them |
| 1.8 standard error, `projects`, only what is left out | 2, 3, 8, 10 (an ancestor needed for nothing gives no warning), 33 |
| 1.9 a single project pays nothing | 2, 7 |
| 2.1 `--project` keeps one owner's own objects, not grouped; an ancestor that passes nothing | 6, 10, 11, 18, 40 |
| 2.2 must be covered; refusal | 4, 6 |
| 2.3 on `show` | 18 (an id-path, and a full identifier of another project) |
| 3.1 work listing in scope order | 3, 5 |
| 3.2 filters across projects | 25 (`--parent`), 26 (`--stage`), 27 (`--mine`), 38 (`--tag` and its warning, `--assignee` in both backends, `--all`) |
| 3.3 `children` and `blocks` across the scope | 25 |
| 3.4 `tcw work show` input forms | 4 (a full identifier outside the scope), 22 (a full identifier is never unavailable), 24 |
| 3.5 a search kept for one command; its key | 28 (Jira project, account, nothing kept between commands); field ids and stage statuses: n/a as separate criteria, both are part of the search text and the requested fields, so they are the same key as 28's Jira project |
| 4.1 what each scope lists; scope objects and `V(X)` | 9, 10, 12, 19 |
| 4.2 groups | 12, 13, 19 |
| 4.3 rows | 9, 12, 18, 19 |
| 4.4 order | 10, 12, 32 |
| 4.5 filters and `search` | 16, 31, 40 |
| 4.6 `statuses`; the `show` block; plain listings carry no status | 8, 13, 14, 15, 19, 20, 29; plain listings: 12 (exact lines) |
| 4.7 `overridden-by` | 13, 14 |
| 4.8 `show` by id-path and full identifier; `up` never ambiguous; the hint; ambiguity; the change to TCW-112 3.1 and 3.5 | 10 (`up`, not found), 14, 17, 18; the readers TCW-112 3.1 keeps: n/a here, TCW-112's and TCW-114's criteria for `set`, `add`, `rm` and the web `PATCH` stay unchanged and pass under 41 |
| 4.9 which scopes need `P`'s view; why `down` stops | 17 (hint left out, exit 4), 20, 21 |
| 4.10 one store-neutral function | 12, 13, 19 (each reaches it through the store) |
| 5.1 `--local` refused | 30 |
| 5.2 passages that name it | 39 |
| 6.1 query parameters | 33 |
| 6.2 answers, `scopes`, the fallback for `P` alone, 503 | 33; 503: n/a here, TCW-112 Design 4.5 adds it and its AC 33 checks it |
| 6.3 route keys | 34 |
| 6.4 the work route key rule; any locatable object read; `/api/resolve` | 34 |
| 6.5 every write route names the owner; handlers stay within the served project | 34 (each of the five work and files write routes, and a key naming no item); a handler's own 404: n/a as a criterion, it is reachable only if a route's `writes` were missed, which TCW-114's route-table test (its AC 4) rules out |
| 6.6 scope control and project filter | 35 |
| 6.7 read-only display | 35 |
| 6.8 unavailable notice | 35 |
| 6.9 mixed status in the client | 35 |
| 6.10 bundle | 36 |
| 7.1 audit procedure | 37 |
| 7.2 command help | 30 (`--local` absent); the `--scope` help text: n/a as a criterion, `tests/test_cli_help_standard.py` checks every command's help contract for every command `tcw/cli_help.py` registers |
| 7.3 documentation entries | 39, and the documentation gate when the item leaves implementation |

## Risks

- **The default changes what a reader sees.** In 3.x, `tcw capabilities list`
  in a reader lists inherited capabilities; after this item it lists only the
  reader's own, and `show <id-path>` of an inherited object needs `--scope up`
  (Design 4.8). The design chose the default (design.md:641-642); the hint of
  4.8 and the migration guide (TCW-117) are what soften it. TCW-112's tests that
  read the view through `list` or `show <id-path>` (its AC 1, 3, 5, 8, 10 and
  others) gain `--scope up` here; the plan reads each failure rather than
  editing its assertion.
- **Views of a large family are expensive.** `down` and `all` build each
  descendant's view and read each descendant's store, possibly in many
  repositories. Each project's own objects are read once per command, and
  Jira is searched once per search key (3.5); nothing is kept across
  commands. TCW-50's limits come after.
- **Exit 0 with a project left out.** A script reading only the exit code
  cannot tell that a project was unavailable; `projects` in `--json` says so,
  and standard error does for a person (1.8). Stopping instead would make every
  fresh clone's `down` view fail for one missing child, which the design rules
  out ("never left out", not "stop"), and the user's decision for another
  project's links (TCW-108 Design 6.6) already chose not to stop.
- **Groups can surprise.** `down` shows a descendant's override of something
  `P` only inherits as its own row (4.3), so `show <that path> --scope down`
  can exit 2, and two unrelated objects at one path are two rows; `all` is
  the overview, and `--project` lists one owner's objects. The rule is one
  function with its examples as criteria (12, 18, 19).
- **A kept search must never answer for another account or another
  question.** The search key holds the account and the exact search text and
  fields (3.5), and each project keeps its own filter on `TCW Project`; AC 28
  compares the result with each project's own `list`, checks the account
  case, and checks that nothing is kept between commands.
- **A missed write route.** If a work or files write route's `writes` kept
  the active project's label, a write to another project's item would pass
  the ownership check. Design 6.5 names the five routes, AC 34 sends a write
  to each, and the write handlers resolve only within the served project, so
  a missed route answers 404 rather than writing.
- **The web app reads other projects' items through their backends.** A
  descendant kept in Jira needs that project's credentials on this machine (its
  variables, TCW-109 Design 5.2); without them its item page degrades as a
  Jira-owned page does today, and its board rows make it unavailable.
- **The item is large.** It touches every list and show command, the Jira
  backend, the server and the client (41 criteria). Replacing the new backend
  operation with a search kept for one command (3.5) removed the interface
  change, `docs/lifecycle/abstraction.md` and two criteria. The plan may land
  it in steps on `v4` (the model and CLI first, then the web app, Design 6 and
  AC 33-36), as one item.

## Notes

### Decisions the design left to this spec

1. **Which commands take `--scope`** (Design 1.1): the eight that list or show
   objects. `tcw work tickets list` lists tickets with no owner, and the other
   commands list configuration or check rather than show objects.
2. **`up` covers every ancestor, whatever `inherit` says, and lists
   taxonomy and capabilities as `P`'s view** (Design 1.3, 4.1). Every
   ancestor is in `projects`, its work items are listed, and `--project
   <it>` lists its own objects, so TCW-108 Design 5.3 ("`inherit` does not
   change … the views of TCW-113") holds for the projects covered. The rows
   on taxonomy and capabilities are the view, as TCW-112's handoff says ("the
   view is what `--scope up` lists"). The user chose this reading (below,
   N2).
3. **A covered project other than `P` that cannot be read is unavailable, not
   a stop** (Design 1.6, 1.7), including a gap in its configuration. Reason:
   it extends the user's decision of 2026-10-22 for another project's links,
   "a problem in another project's links does not stop the active project"
   (TCW-108 Design 6.6), which TCW-109 already adopted for broken inherited
   values (TCW-109 Notes, "Decided after the spec review", 21). The unavailable project's reason is
   TCW-109's own message, and two reads keep TCW-109 Design 5.2's exit 7: a
   command run in that project itself (AC 22), and a read of that project's
   object by its full identifier (Design 1.7, AC 22). TCW-109's Design 5.2
   text says otherwise for a descendant and is amended by the handoff below.
   `P` itself is never unavailable.
4. **Rows in `down` and `all` are grouped, one per capability, with the status
   each project gives it** (Design 4.2-4.6), so a family's overview lists each
   capability once (TCW-98's request: "Running TCW in Docs-and-Plans should show
   the combined status"). That overview is `all`; `down` lists what `P` and its
   descendants declare, so a descendant's override of something `P` only
   inherits is its own row there (Design 4.3). Overrides grouped under a row
   stay visible (`overridden-by`, 4.7), and `--project` lists them separately
   (2.1), as the design's "`--project shared-libs` returns only the original"
   requires.
5. **A capability's statuses are each project's view at the path** (Design
   4.6). TCW-112's handoff reads them as "each project's own object … as that
   project sees it"; a project with no own object at the path then has none,
   but the design counts it ("a project that inherits a status without
   overriding it counts with that status, marked as inherited",
   design.md:653-655). The view gives both. "Inherited" uses TCW-112 Design
   7.2's rule (no own object, or one that does not set `Status`).
6. **`--project` must name a covered project** (Design 2.2), refused otherwise,
   so a sibling's empty result never reads as complete.
7. **`show` by id-path follows the scope, with a hint under `own`** (Design
   3.4, 4.8). The design settles the default for `show` (below, "Settled
   questions").
8. **`--local` is removed with a message** (Design 5), one spelling per
   meaning.
9. **A shared Jira project is searched once by keeping a search for one
   command, not by a new backend operation** (Design 3.5). The first draft
   added a thirteenth operation, "list together", which grouped projects by
   Jira project and loosened the search. The review found that the grouping
   could sign in as one project's account to list another's tickets, and
   that projects may configure different field ids. A search kept for one
   command, keyed by site, account, search text and fields, keeps every
   project's list exactly its own by construction, and needs no change to the
   interface, to `docs/lifecycle/abstraction.md` or to its test. It costs one
   extra search where projects sharing a Jira project map their stages to
   different statuses, which UC-5's usual setup (a child inheriting
   `work.jira`) does not do.
10. **`children` and `blocks` cover the scope** (Design 3.3), so `show --scope
    down` answers UC-3's known gap.
11. **Exit codes do not change.** No new code: an unavailable project is
    reported, not failed; `P`'s failures keep theirs.
12. **The web app's scope and project live in the URL** (Design 6.6), so a view
    is a link and names the flags it matches (principle 4).
13. **Documentation entries** as the siblings settled (Design 7.3).
14. **Every web write names the object by its owner** (Design 6.5): one work
    route key rule decides the owner for reads and writes, so widening what a
    read can reach can never widen what a write can reach.
15. **What makes a project unavailable is a named set of errors** (Design
    1.6): `TcwError` except usage errors, the three store errors that are
    `ValueError`s, `yaml.YAMLError` and `OSError`; anything else ends the
    command as today, and the catch surrounds only the reads of `Q`.

### Decided by the user on 2026-10-22

- **N1. Plain `list` output stays one identifier per line, with no
  mixed-status summary.** The summary is in the `--json` records
  (`statuses`), in `show`'s `status by project:` block, and in the web app's
  rows (Design 4.6, 6.9). This departs from the design's "a list shows a short
  summary" (design.md:649-651) and from the request's "a summary in lists";
  it matches the user's earlier decision that override marks go in records,
  not in text (TCW-112 Design 3.2). TCW-117 amends that line of the design.
- **N2. `--scope up` rows for taxonomy and capabilities are the project's
  view only** (TCW-112's view). `projects` still names every ancestor, and
  `--project <ancestor>` lists that ancestor's own objects (Design 1.3, 2.1,
  4.1; AC 10). This also settles the review's finding that `show <id-path>
  --scope up` could be ambiguous: under `up` an id-path names `P`'s view
  object, which is one object or none (Design 4.8).

### Settled questions

The first draft asked TCW-99 two questions. Both are answered:

1. **The default `own` and `show` by id-path.** Settled by the design: "The
   default is `own` on every axis", under the heading for list and show
   commands (design.md:631-642). `tcw capabilities show cli/x` in a reader no
   longer finds the inherited `cli/x` without `--scope up`; the hint of
   Design 4.8 says so, and the migration guide (TCW-117) carries it. Design
   4.8 records that this changes TCW-112 Design 3.1 for `show` only.
2. **"A summary in lists" for mixed status.** Decided by the user: N1 above.

### Departures from the design

Each is stated where it applies; this is the one list.

1. **Statuses need `--scope down` or `all`.** The design's sketch
   (design.md:657-665) runs `tcw capabilities show <full id>` with no
   `--scope` and prints statuses by project. Under the default `own` this
   item prints none (Design 4.6, AC 14), because `own` covers one project,
   and one project's view gives one status. The sketch's output is what
   `--scope down` prints.
2. **No summary in text listings** (N1).
3. **`up` on taxonomy and capabilities is the view** (N2). This follows the
   design's parenthetical "(for work, which is not inherited, the ancestors'
   own items)" (design.md:635-636), read as: for the axes that are inherited,
   `up` adds what is inherited. It is listed here because TCW-108 Design 5.3
   could be read as asking `up` to list every ancestor's objects; Design 1.3
   says how both hold.
4. **`--project` must name a covered project** (Design 2.2). The design says
   only that it "keeps only results owned by that project" (design.md:643);
   the refusal is an addition, so that a sibling's empty result never reads
   as complete.
5. **One search per Jira project and account, when the projects map their
   stages alike** (Design 3.5). The request says "grouped, one per Jira
   project". Projects whose people sign in with different accounts must be
   searched separately, or one would see tickets under another's
   permissions; projects that map their stages to different statuses are
   searched separately too, as the cost of keeping the interface unchanged
   (decision 9).

### Revised after the spec review (2026-10-22)

- Design 6.4 and 6.5 give one work route key rule, and every work and files
  write route names the item by its owner, so TCW-114's router refuses a
  write to another project's item (review M1); AC 34 sends a write to each of
  the five routes.
- Design 1.6 names the unavailability errors, adds the three store errors
  that are `ValueError`s and case h, and says the catch surrounds only the
  reads of `Q`; 1.7 adds the object named by a full identifier and the graph
  problems TCW-108 and TCW-109 define (review M2); AC 29 is new.
- Design 3.5's new backend operation is replaced by a search kept for one
  command (review M3); Design 7.2 (abstraction.md) and the criteria for the
  operation (old AC 29 and 38) are gone.
- N1 and N2 are recorded as the user's decisions; Design 4.1-4.3 and 4.8 are
  rewritten for N2, and AC 10 with them (review N2, S1).
- Decision 3 cites TCW-108 Design 6.6, and TCW-109 is asked to amend its
  Design 5.2 (review S2).
- `all` is named the overview, and `down`'s split rows are stated as a
  consequence, not a surprise (review S3).
- The two missing ledger records are declared (review S4); the departures are
  listed in one place (S5).
- `--stage` removes each project's disabled stages before asking its backend,
  so no usage error is caught (review S6).
- Design 4.8 says which readers of TCW-112 Design 3.1 change, and replaces
  two rows of its 3.5 table (review S7).
- AC 14, 15 and 28 are reworded (review S8); 4.9 gives the reason `down`
  stops (review S9).
- New criteria for the coverage gaps the review listed: AC 8 (the `show`
  warning), 18 (2.3), 22 (a full identifier), 26 (no search), 33 (`GET
  /api/work`), 34 (the declaration route), 35 (badges on rows), 38 (`--tag`,
  `--assignee`, `--all`), 40 (`--namespace`, `search`).

### Handoffs

Recorded on each ticket by the dispatching session when this spec is
accepted.

- **TCW-108** (landed): this item uses `ancestors()`, `descendants()`
  (breadth-first), `declared_child_ids()` for listed children not on this
  machine, `load_order(id)` and `sources(axis, id)` for each covered project
  (Design 1.3, 1.4, 4.6), as its handoff named. Its plan's choice 7 (exit 7 in
  the web app answered as a 500) is settled by TCW-112 Design 4.5's 503, which
  this item's routes inherit (Design 6.2). Design 1.3 reads its 5.3 as:
  `inherit` never narrows the projects a scope covers, while `up` on taxonomy
  and capabilities lists the view, which `inherit` shapes. A descendant's
  `children:` problems stay its graph problems, never an unavailability
  (Design 1.7).
- **TCW-109** (landed): a covered project is read for itself (Design 1.5). A
  gap in its configuration makes it unavailable in a scoped listing, with
  TCW-109's own message as the reason, rather than stopping the command
  (Design 1.6 d; Decisions, 3). Its Design 5.2 third bullet and its handoff
  to this item are amended to say so: a scoped listing reports the project
  unavailable (exit 0), and a read of its object by full identifier, or a
  command run in it, still stops with exit 7.
- **TCW-110** (landed): the route key rule of its Design 4.5 is extended to
  work items and to every object another project owns (Design 6.3), and
  `/api/resolve` answers `ok` with a full identifier for an existing object of
  another project on this machine, keeping `other-project` only for a project
  not on this machine (Design 6.4).
- **TCW-111** (landed): nothing further; nested items are listed per project
  as its walk gives them.
- **TCW-112** (landed): `--scope up` lists its view (Design 4.1), `--scope own`
  its `--local` result, and `--local` itself is removed (Design 5); its tests
  that read the view through `list` or `show <id-path>` gain `--scope up`
  (Risks). Design 4.8 changes its Design 3.1 for `show` only and replaces two
  rows of its 3.5 table; its spec needs no change. Its Design 4.5's read-only
  rule for the web app is replaced by Design 6.5 and 6.7. `statuses` use each
  project's view at the path (Decisions, 5).
- **TCW-114** (landed): the work and files write routes' `writes` functions
  answer the owner's full identifier from the work route key rule (Design
  6.5), not the active project's; no write route is added.
- **TCW-115:** nothing is needed. The refusal of Design 2.2 may add `tcw
  project path <id>` once that command exists.
- **TCW-116:** nothing to migrate: no file or key changes. Scripts that pass
  `--local` are the migration guide's (TCW-117).
- **TCW-117:**
  - the `work`, `taxonomy` and `capabilities` skills teach `--scope` and
    `--project`, that the default is `own`, that inherited objects need
    `--scope up`, that a family's overview is `--scope all` (and that `down`
    lists what the project and its descendants declare), and that a status
    summary is read from `--json` or `show`, never from a plain listing;
  - `docs/guide/cli.md` documents both options and the `projects` key;
    `docs/guide/web-viewer.md` replaces "The app serves one project"
    (`:17-19`) with the scope control, the read-only display and followed
    links; `docs/guide/taxonomy-and-capabilities.md` explains mixed status;
    `docs/guide/multi-repo.md` shows family views; `docs/guide/jira.md` says
    when a scope's projects sharing one Jira project are read with one search;
  - `docs/use-cases.md`: UC-3's known gaps on TCW-102 and TCW-98, and UC-4's on
    TCW-22, are closed; UC-5's cost gap is narrowed for scoped listings; UC-6
    gains "unavailable, exit 0" for a covered project and exit 7 where the
    active project's view needs it;
  - the migration guide: the default listings no longer include inherited
    objects (`--scope up`), `--local` is removed, `show <id-path>` of an
    inherited object needs `--scope up`;
  - the TCW-99 design: its "a list shows a short summary" line (N1) and its
    sketch with no `--scope` (Departures, 1) are amended.
- **TCW-50:** a listing covering several projects is ordered as Design 3.1 and
  4.4 say; its "one section per node" becomes one section per covered project
  in scope order, and its limits apply per project.
