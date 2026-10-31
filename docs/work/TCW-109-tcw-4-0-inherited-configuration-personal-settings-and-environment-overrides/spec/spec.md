# Spec — TCW 4.0: inherited configuration, personal settings and environment overrides

Child 4 of 13 of TCW-99. It carries out these sections of the TCW-99 design
(`docs/work/TCW-99-…/design.md`): the configuration bullets of "What is
inherited" (design.md:482-503), and "Personal overrides and environment
variables" (design.md:505-554). It builds on the decisions in "What any store
must support, and what is only about folders" (design.md:113-133).

**Order and blockers.** The children land on the `v4` branch in the order
TCW-106, TCW-107, TCW-110, TCW-108, TCW-111, then this item. This item is
blocked by TCW-108, which gives it the parent links, the load order and
`sources("config")` (TCW-108 Design 4, 5). It builds on TCW-106 (the `.tcw/`
folder, `tcw-version`, and the naming rule that makes every key lower case
letters and digits joined by single hyphens, TCW-106 Design 5.1), TCW-107
(`TCW_PROJECT_<ID>` stays, TCW-107 Design 2.1; personal files in a linked
worktree, Design 4.2) and TCW-110 (store locations, TCW-110 Design 7.1). It
blocks TCW-115 (`tcw project config`, `tcw project info`), TCW-116
(`tcw migrate`) and TCW-118 (the release).

File and line references are to commit `67c4c15a` on `v4`, where TCW-106 is
built and TCW-107, TCW-110, TCW-108 and TCW-111 are not. Those items change
`tcw/store/` heavily but leave the layered configuration reader,
`tcw/config.py`, nearly as it is (TCW-108 adds `children` to it, TCW-108 plan
Step 9), so the plan re-checks every reference against what they land.
"TCW-10n Design m" means rule m of that item's spec.

Terms used throughout:

- **The active project** is the project a command runs in (TCW-99
  requirement 7).
- **A layer** is one place a project's configuration is read from: TCW's own
  defaults (`built-in`), the project's shared `.tcw/tcw-config.yaml`, the
  person's user-wide file, the project's `.tcw/tcw-config.local.yaml`, and,
  new here, the environment (`LAYERS`, `tcw/config.py:54`).
- **The personal layers** are the user-wide file, a project's
  `tcw-config.local.yaml` and the environment variables of Design 4.
- **The configuration sources** of a project are TCW-108's
  `sources("config")` (TCW-108 Design 5.2): its load order, farthest
  ancestor first and the project itself last, keeping only the projects that
  pass `config` to it (TCW-108 Design 5.1).
- **An inherited key** is one of the keys of Design 1.1, the only keys that
  cross a parent link.
- **Declares**: a project declares a key when one of its layers sets it, to
  any value including `null`.

## Capability changes

- **New** `cli/inherit-configuration-from-parents`: a project takes
  `work.tags` and every key under `work.jira` from each parent whose link
  passes `config`; `work.backend` is not inherited, so every project states
  its own and the default is `filesystem`; mappings merge key by key, a list
  or single value is replaced, `null` removes an inherited value, and an
  `inherit: true` entry in `work.tags` adds to the inherited list. A command
  that needs an inherited value it cannot know, because a project it would
  come from is not on this machine, exits 7; listing, reading and moving a
  filesystem project's own items never needs one.
- **New** `cli/override-configuration-from-the-environment`: a variable
  `TCW_<KEY>__<PROJECT>` sets one configuration key of one project, for the
  keys a personal file may set; its name follows from the key and the project
  ID; its value is read by the key's type; the more specific variable wins;
  `TCW_NO_PERSONAL_CONFIG=1` turns it off.
- **Changed** `cli/override-the-team-configuration-for-myself`: the
  environment is a personal layer after `tcw-config.local.yaml`; the person's
  personal settings for an ancestor reach the active project through what
  that ancestor passes down; `TCW_NO_PERSONAL_CONFIG=1` turns off the
  variables as well as the files.
- **Changed** `cli/show-the-effective-configuration`: inherited values and the
  environment layer are shown; with an inherited value that cannot be known,
  `tcw config show` exits 7.
- **Changed** `cli/validate-a-project`: a problem with an override variable is
  an error at `environment`; a configuration check that needs an inherited
  value from a project not on this machine is reported as "could not check".
- **Changed** `work/tag-a-work-item`: inherited tags are registered tags;
  `tcw work tags add` keeps following the parents' list; `tcw work tags rm`
  refuses a tag that is only inherited.
- **Changed** `work/keep-work-items-in-jira`: the Jira settings may come from
  a parent, while `work.backend: jira` is always written in the project
  itself.
- **Taxonomy:** new `environment-override`; changed `config-layer`,
  `personal-configuration`.

## Problem

1. **Configuration never crosses projects.** `load_config` reads one
   project's four layers and nothing else (`tcw/config.py:572-643`): built-in,
   the project's file, the user-wide file, the local file (`LAYERS`,
   `tcw/config.py:54`). TCW-99 requirement 4 asks for configuration that
   supports inheritance, and the design names what crosses: `work.tags`,
   `work.backend` and the Jira settings (design.md:482-492). This spec keeps
   `work.backend` per project, by the user's decision of 2026-10-22 (Design
   1.2, Notes). Today a family sharing one Jira project
   (`docs/use-cases.md` UC-5) repeats its `work.jira` block in every project.
2. **No environment variable can set a configuration key.** The only
   variables TCW reads are `TCW_PROJECT_<ID>` (a project's folder,
   `_resolve_override`, `tcw/store/project.py`), `TCW_CONFIG_DIR` (set by TCW
   for hooks, `tcw/work/hooks.py:77`), `TCW_NO_PERSONAL_CONFIG`
   (`tcw/config.py:40`, `:680-687`) and `TCW_STDIN_TIMEOUT`, plus the
   credential variables a configuration names. TCW-99 requirement 5 asks for
   overrides from environment variables, by a name that follows from the key
   and the project ID (design.md:512-520).
3. **`inherit: true` works only inside one project, and only in chain
   lists.** It is accepted only in a stage's `prompt`, `pre` or `post` list
   and a procedure's list (`_list_problems`, `tcw/config.py:332-335`;
   `_is_chain`, `:293-298`), and stands for the list the layers below resolved
   in that same project (`_chain`, `:464-482`). The design makes it reach
   across the parent link, with `work.tags` as its example (design.md:493-498).
4. **`null` has no consistent meaning.** In the shared file, `null` on a key
   whose lower value is a mapping is ignored (`tcw/config.py:508-511`); on any
   other key it is stored as the value (`:521-524`), and the parser then
   refuses it (`parse_bindings`, `tcw/work/config.py:288-289`; `"backend":
   None`, `:496-500`), or reads it as an empty value (`work.tags: null` is no
   tags, `_parse_tags`, `:451-454`). The design gives it one meaning: it
   removes an inherited value (design.md:499-503).
5. **An inherited setting from a project that is not here has no rule.**
   TCW-108 stops a command that needs inherited content with exit 7
   (`InheritedUnavailable`, TCW-108 Design 6.2), and leaves to this item which
   work settings a work command needs from its parents (TCW-108's handoff on
   this ticket). Every command checks the whole configuration before it runs
   (`tcw/cli.py:655-661`), and most `tcw work` commands open the work store
   (`open_backend`, `tcw/work/open.py:54-79`), some only to read
   configuration that is not inherited (`tcw/work/cli.py:56`, `:71`, `:441`,
   `:455`, `:567`, `:596`). So the obvious construction, folding parents'
   values when the configuration is loaded and refusing it whole when a parent
   is missing, would stop `tcw work list` whenever any parent passing `config`
   is missing, against TCW-99's "commands that need only the project's own
   records still work" (design.md:386-388).
6. **The personal allowlist has no counterpart for the environment.**
   `PERSONAL_KEYS` (`tcw/config.py:45-52`) is applied to the two personal
   files by `_allowed` (`:369-405`). The design keeps one allowed list for
   personal files and variables, and says the spec lists it
   (design.md:535-540).
7. **The tag registry commands write the effective list.** `tcw work tags
   add` and `rm` read the merged `work.tags`, change it, and write the whole
   result into `.tcw/tcw-config.yaml` (`_write_tags`, `tcw/work/cli.py:626-645`).
   Once tags are inherited, that would copy every parent's tag into the
   child's file, which then stops following its parents.

## Goals

1. A fixed, documented list of keys crosses a parent link that passes
   `config`; everything else stays per project.
2. Values combine by one rule over TCW-108's load order: mappings merge key by
   key, lists and single values are replaced, the last project that declares a
   key wins, `null` removes an inherited value, and `inherit: true` in
   `work.tags` adds to the inherited list.
3. A missing parent stops only a command that reads a value that parent could
   have set, with exit 7; a project that sets the value itself is not stopped.
4. Any key a personal file may set can also be set from the environment by a
   variable whose name follows mechanically from the key and the project ID,
   with its value read by the key's type.
5. One allowed list governs personal files and variables, and
   `TCW_NO_PERSONAL_CONFIG=1` turns off both.
6. A single project (UC-1) needs no new configuration and sees no change in
   any command's output.

## Non-goals

- **Showing where each value came from** in the new command group
  (`tcw project config --origin`): TCW-115. This item records, for every
  value, the project and the file or variable it came from (Design 2.6), and
  keeps the existing `tcw config show --origin` truthful about inherited and
  environment values (Design 7.1), since that command runs on `v4` until
  TCW-115 replaces it.
- **The parent link, the load order and `sources`**: TCW-108's. This item
  folds configuration over the order TCW-108 computes and applies TCW-108
  Design 4.8 ("which value wins") to configuration.
- **Inherited taxonomy and capabilities**, and `taxonomy.extends` and
  `capabilities.extends`: TCW-112. Neither key is inherited configuration, and
  neither may be set by a personal file or a variable (Design 5.1).
- **Where projects are on this machine.** A location is not configuration
  (TCW-107 Design 2.1): `TCW_PROJECT_<ID>` stays as it is, and no override
  variable gives a manifest path.
- **Unknown top-level keys** in `.tcw/tcw-config.yaml`, which are accepted
  silently today (`docs/use-cases.md` S-9, "Known gaps"; TCW-106 Non-goals).
  The table of keys TCW knows that Design 4.3 adds could close it, but
  refusing an unknown key in the shared file changes what every existing
  configuration may hold, so it is not done here.
- **Widening what a personal file or a variable may set.** The allowed list
  is the 3.x list, one list for both (Design 5.1; settled by the design,
  Notes, "Settled questions", 2).
- **Guides, skills and `docs/use-cases.md` wording**: TCW-117 (as TCW-108
  decided for its own changes: nothing ships between these items and the 4.0
  release, and TCW-117 lands before TCW-118). Notes lists what they must say.
- **Converting 3.x configurations**: TCW-116. Notes lists the one case a 3.x
  configuration can hit (a credential variable whose name has `__`).

## Design

Design 1, 2, 3 and 5 are the model: any store that keeps a project's
configuration can implement them. Design 4 is how the command line reads a
process's environment. Design 6 and 7 are what the CLI shows. None of it is
the deployment layer of the TCW-99 design.

### 1. What crosses a parent link

1.1. **The inherited keys** are `work.tags`, and `work.jira` with every key
under it (`site`, `project`, `credentials` and its two keys, `fields` and its
four keys, `priorities` and its five keys, `issue-type`, `inbox-query`,
`timeout`: `KEYS`, `CREDENTIAL_KEYS`, `FIELD_KEYS`,
`tcw/work/jira/config.py:31-36`; `PRIORITIES`, `tcw/work/model.py:98`). The
list is one constant in `tcw/config.py`, documented where the configuration
keys are documented, and grows only in a release (design.md:482-484). In this
order (`work.tags`, then `work.jira`) the list is also the order Design 7.1
names undecided keys in.

1.2. **Everything else is the project's own**: `id`, `parents`, `children`,
`taxonomy`, `capabilities`, `user`, and under `work` the keys `backend`,
`path`, `repository`, `documentation`, `procedures`, `stages` and `hooks`
(`WORK_KEYS`, `tcw/work/config.py:41-42`). A value an ancestor sets for one of
these keys never reaches a descendant, whichever layer of the ancestor sets
it.

**`work.backend` is not inherited** (decided by the user, 2026-10-22). The
design lists it among the inherited keys (design.md:484-485); this spec
departs from that. Every project states its own backend in its own shared
file, and a project that states none is in filesystem mode, as today
(`DEFAULT_BACKEND`, `tcw/work/config.py:496`). So whether a project keeps its
items in files or in Jira never depends on another project, a filesystem
child always works on a single clone, and a project's backend is always
known (it is never undecided, Design 3). A Jira-mode child that shares its
parent's Jira project writes `work.backend: jira` itself and takes the rest
of `work.jira` from the parent. Reason: inheriting the backend would save
each Jira child one line, and would cost every filesystem child whose parent
passes `config` its single-clone runs, since its backend would be unknown
without the parent (the review of this spec, U1).

1.3. **Which projects.** A project's configuration is folded over its
configuration sources (the terms above), which are TCW-108's load order kept
to the projects that pass `config`. A project behind a link whose `inherit`
leaves `config` out contributes nothing, whatever its state. The configuration
loader reads that order without raising: a project in it that is not on this
machine or whose parent links could not be read (TCW-108 `LoadOrder.missing`
and `unreadable`, Design 6.4, 6.6) stays in it as a gap, handled by Design 3.
It does not call `sources("config")` in the form that raises
`InheritedUnavailable` on the first gap (TCW-108 Design 6.2), because a gap
stops only a command that reads a value the gap could have set (Design 3.3).

**When the order cannot be had at all**, loading the configuration still
does not raise. That happens when the project's own `parents:` is wrong, when
its ancestors form a loop (TCW-108 Design 4.7), or when the registry fails in
any other way while it is opened or asked for the order. In that case the
project is folded alone, from its own layers. Each key of 1.1 that it does
not decide itself (the rule of Design 3.1) is held as a value that cannot be
used (Design 3.4). It carries the error `tcw work list` gives in the same
project, which exits 1: the registry's graph problems joined as today
(`require_valid`, `tcw/store/project.py:455`), so a loop is named by TCW-108's
own message (`loop in parents: lib -> top -> lib`), and only when the registry
records none, the error it raised. So no command runs on a value half
inherited.

The project's own `parents:` is wrong when TCW-108's reading of the key
refuses it. In the active project's own file that is a graph problem (TCW-108
Design 6.6 keeps it one for the active project), so the registry still says
the project's links can be read, and may answer an order holding the project
alone without raising. The loader therefore reads the project's own
`parents:` itself, and treats a refused value as an order it cannot have; it
does the same for a loop through the project's ancestors, whether or not the
registry raises for it (decided by the dispatching session, 2026-10-22: the
plan re-check found that waiting for the registry to raise would miss the
case this rule was written for, and that a wider test, any graph problem at
all, would newly stop tag commands in a project whose only problem is a
descendant that does not name it back). A command that reads no such key
goes on to its own checks of the project graph, which report the problem as
they do today (TCW-108 Design 1.3). `tcw validate` lists it as a finding,
and its run is not cut short.

1.4. **An inherited value holding a relative path resolves from the project
that declared it** (design.md:489-490). No key of 1.1 holds a path (the Jira
values are a URL, keys, names and numbers: `tcw/work/jira/config.py:31-37`),
so the rule has no case in 4.0. It is kept by recording the declaring
project's root in every value's origin (Design 2.6), which is where a
`file:` binding's folder already comes from (`Origin.folder`,
`tcw/config.py:71-81`).

1.5. **An inherited `work.jira` is ignored when the active project's
`work.backend` is not `jira`.** Today a `work.jira` without `backend: jira`
is a problem (`tcw/work/config.py:503-504`). That stays for a `work.jira` the
active project declares itself; a `work.jira` it only inherits is dropped
without a problem, and outside Jira mode `work.jira` is never undecided
(Design 3.1). The backend is the project's own (1.2), so it is always known
when this rule is applied. Reason: a filesystem child of a Jira-backed parent,
which is the default for a child that writes no `work.backend`, would
otherwise have to write `work.jira: null`.

1.6. **What is read from an ancestor, and whose problem it is.** From each
configuration source other than the active project, only the keys of 1.1 are
taken from each of its layers. They are checked by the rules the active
project's own file is checked by (the naming rule, TCW-106 Design 5.1; the
`inherit` entry's rules, `tcw/config.py:332-346`; the allowlist for a
personal layer, Design 5.1).

**The user-wide file is not another project's layer.** It is read once and
checked once, against the whole allowed list, as the active project's own
personal layer (2.1). Its problems are the active project's own and are
reported once. They are never counted as "broken" below, though the file is
applied again at each configuration source.

**A value refused by the allowlist** in an ancestor's
`tcw-config.local.yaml`, or in a variable naming an ancestor, is never
merged, so it breaks nothing. In a variable it is an error of the active
project, by Design 4.4. In the ancestor's local file, `tcw validate` in the
active project reports it as a `warning` at that file, as for a broken key.

**A problem in an inherited value stops only a command that reads it.** A
key of 1.1 is **broken** in the active project when a value with a problem,
declared by another project's layer, would reach the active project's merged
value: a value found wrong by the checks above, or a value the parser finds
wrong in the merged result when the wrong part was declared by another
project. A later project that replaces the key whole (the rule of Design 3.1)
leaves it unbroken. A broken key is handled as an undecided one is (Design
3), with a different error; a key that is both undecided and broken is
treated as undecided (exit 7), since what reaches it is not known:

- the check every command makes first (`tcw/cli.py:655-661`) does not count
  it, so a command that reads no broken key runs;
- a command that reads it (Design 3.4) stops with exit 1 (a configuration
  problem, as today), with the problem named by the declaring file's whole
  path and the key (as another project's files are named today,
  `tcw/config.py:584-586`), before anything is written or any request made;
- `tcw validate` in the active project reports it as a `warning` at that
  file, and fails only in the project that declared it, where it is that
  project's own problem.

Reason: this is the rule the user chose on 2026-10-22 for a problem in
another project's links (TCW-108 Design 6.6, UC-2): a library's mistake must
not stop its readers' commands that do not need the value. A problem the
active project's own layers cause is its own and stops every command, as
today (exit 1, `tcw/cli.py:658-661`).

A problem in an ancestor's keys outside 1.1 is not read from the descendant
and is not reported there; it is that ancestor's own.

**An ancestor whose shared file cannot be read at all** has unknown parents
and unknown settings. That is a file that is not UTF-8 text, is not valid
YAML, holds a key twice, is not a mapping, or has a `tcw-version` this TCW
cannot read (TCW-106
Design 3; `read_project_file`, `tcw/config.py:257-270`). This spec adds that
case to TCW-108 Design 6.6, which names only problems in `parents:` and a
`projects:` or `connected-projects` key. The case applies when such a
project is an **ancestor** of the active project, or a project **read only
for a lookup** (TCW-108 Design 3.4 or 4.6). Those are the `ancestor` and
`outside` roles of TCW-108's plan. Such a project is placed in the load order
with no parents and listed in `LoadOrder.unreadable`. `tcw validate` reports
TCW-108 Design 6.5 row (d), with the read problem as its text. For
configuration, the project is a gap (1.3). It applies to every axis, as 6.6
does, because the project's parents are what is unknown. This item's plan
builds it in the registry if TCW-108 as landed does not already do so.

**A descendant whose shared file cannot be read stays a graph problem** of
the active project, as today. TCW-108 Design 6.6 keeps a descendant's
committed `children:` problems and its name-back check as graph problems,
for this reason: the active project lists that descendant, and those lists
decide the family it shows. A descendant's file that cannot be read at all
leaves that list unknown in the same way. Configuration never flows up from a
descendant, so treating it as a gap would gain nothing here. A file that can
be read but names no valid `id` stays a graph problem in every role: it does
not say which project it is.

### 2. How values combine

2.1. **The fold.** The configuration of project `P` is built by merging, in
this order:

1. TCW's built-in values, once (`built_in_values`, `tcw/config.py:207-220`);
2. for each project `Q` of `P`'s configuration sources, farthest first and
   `P` last, `Q`'s layers in order: its shared `.tcw/tcw-config.yaml`; then,
   when personal files apply (Design 5.2), the user-wide file and `Q`'s
   `.tcw/tcw-config.local.yaml`; then, when variables apply (5.2, 5.3), the
   variables naming `Q` (Design 4). For `Q` other than `P`, each layer
   contributes only the keys of 1.1 (1.6).

The user-wide file is read once and applied at each `Q`, so every project's
layers come in the same order. Since it is applied again at `P`, after `P`'s
shared file, a value it sets beats the team's for `P`, as today. It is
**checked once**, at `P`, against the whole allowed list (5.1). At each `Q`
other than `P`, only what passed that check is applied, cut to the keys of
1.1. It adds no second problem and no second set-aside record (1.6).

2.2. **Merging** is today's (`_merge`, `tcw/config.py:485-526`): a mapping is
merged key by key, all the way down; a list or a single value replaces the
value below it whole; a chain list (2.4) resolves its `inherit` entry. So a
project that sets only `work.jira.project` keeps its parent's `work.jira.site`,
and one that sets `work.tags` replaces its parent's list (design.md:493-498).

2.3. **The last project that declares a key wins** (TCW-108 Design 4.8). Each
project's own declarations are merged over the order; a project that declares
nothing for a key changes nothing, so it never puts an earlier value back. In
TCW-108's example (`bb` parent of `cc` and `dd`, `ee: [cc, dd]`), when `cc`
declares a key and `dd` does not, `ee` gets `cc`'s value, though `dd` comes
later (AC 5).

2.4. **`inherit: true`.** The entry keeps every rule it has today (it is the
whole entry, only `true` is accepted, one per list:
`tcw/config.py:332-346`) and is now accepted in two kinds of list:

- **`work.tags`**, newly: the entry stands for the tags merged before this
  layer, which includes what the project's configuration sources before it
  declared. So `work.tags: [inherit: true, extra]` in a child is its parents'
  tags plus `extra`. This is the design's "today's `inherit: true` entry …
  now also reaches across the parent link" (design.md:496-498).
- **the chain lists** (a stage's `prompt`, `pre` and `post`, a procedure's
  list; `_is_chain`, `tcw/config.py:293-298`): unchanged. They are not
  inherited (1.2), so the entry stands, as today, for what the project's own
  lower layers resolved.

In any other list the entry is refused as today, and the message names
`work.tags` among the lists that take it.

Because the fold runs over the whole order, an `inherit: true` entry stands
for what the order has merged before that project, not for that project's own
parents' resolved view: with `bb` parent of `cc` and `dd`, `ee: [cc, dd]`,
`cc` declaring `[c]` and `dd` declaring `[inherit: true, d]`, `ee`'s tags
are `c, d`, while `dd`'s own are `bb`'s plus `d` (AC 5). That is TCW-108
Design 4.8 applied to a list: `dd` adds `d` to whatever reaches it.

2.5. **`null` removes an inherited value** (design.md:499-503). In a
project's shared file, `null` at a key of 1.1 or below one (`work.tags`,
`work.jira`, `work.jira.fields.effort`, …) means the key has no value from
any project before it in the order nor from the built-in layer; where the
parser has a default for an absent key, the default applies (an absent
`work.jira.timeout` is 15 seconds, `DEFAULT_TIMEOUT`,
`tcw/work/jira/config.py:29`). A later project may set the key again. `null`
at any other key keeps today's meaning (`tcw/config.py:508-511`, `:521-524`),
so `work:` with nothing under it still means "no settings here", no
inherited value is removed by it, and `work.backend: null` is refused as
today (`tcw/work/config.py:496-500`). In a
personal file `null` is refused as today (`tcw/config.py:378-381`), and in a
variable as Design 4.6 says.

2.6. **Origins.** Every value and list entry records the layer it came from,
the project that declared it, and the file, or for the environment the
variable's name. A problem names that file or variable; a `file:` binding
resolves from that project's folder (1.4, 4.8).

### 3. A parent that passes configuration and is not available

3.1. **An undecided key.** Call a configuration source that is not on this
machine, or whose parent links could not be read, a **gap** (1.3). A key `K`
of the active project's configuration is **undecided** when, for some gap,
no project after the gap in the order (the active project included, all of
its layers included) declares `K`, or a key above `K`, with a value that
replaces it whole: a value that is not a mapping, other than a list holding an
`inherit: true` entry; or `null` (2.5). A mapping is undecided when any key
under it that TCW knows (Design 4.3) is undecided. Only keys of 1.1 can be
undecided: nothing else crosses a link. So `work.backend` is never undecided
(1.2), and outside Jira mode neither is `work.jira`, which is then ignored
(1.5).

So a child that sets `work.tags` itself has decided tags whatever its
parents' state, while a Jira-mode child that sets only `work.jira.project`
still has an undecided `work.jira`, since the missing parent may set its site.

3.2. **An undecided key never takes a built-in value**, and the parser
reports no problem for it (no "required", no default): its value is not
known, so neither TCW's default nor a complaint about its absence would be
true. **No check whose rule depends on an undecided key's value runs
either**, whichever key the check is reported at: such a check could only
guess. The keys under an undecided `work.jira` that are decided (those the
active project or a project after the gap declares) are still checked as
today, apart from "required". With the backend always known (1.2), the
checks that depend on it today (a stage `status` outside Jira mode,
`tcw/work/config.py:372-377`; a status for every enabled stage in Jira mode,
`:408-419`; `work.jira` without `backend: jira`, `:503-504`) run as today.

3.3. **A command that reads an undecided key stops** with
`InheritedUnavailable` (TCW-108 Design 6.2, exit 7), naming the key and the
first gap in load order that could have set it:

```
'<P>' inherits its configuration (<key>) from project '<M>', which is not on this machine: <TCW-107 Design 6.2's sentence for M, from after its first colon>
'<P>' inherits its configuration (<key>) through project '<M>', whose parents could not be read: <the problem, naming M's .tcw/tcw-config.yaml and the key>
```

These are TCW-108's two messages with `<axis>` written as
`configuration (<key>)`, the key in dotted form (`work.jira`, `work.tags`).
Nothing is written and no network request is made before the command stops.

3.4. **Which commands read which inherited keys.** This answers TCW-108's
handoff ("which work settings a work command needs from its parents"). A
command **reads** a key when it uses the key's value; the configuration TCW
loads holds an undecided or broken key (1.6) as a value that cannot be used,
and using it raises the error of 3.3 or 1.6. Loading the configuration, and
reading its other keys, never does.

| # | What reads it | Keys read |
| - | ------------- | --------- |
| a | Opening a Jira-mode work store (`open_backend` building a `JiraBackend`, `tcw/work/open.py:75-77`): every `tcw work` command that lists, reads, creates, changes or moves items in a Jira-mode project, `tcw work stage prompt` and `tcw work procedure` given an item there, `tcw work tickets`, `tcw capabilities drift` (it lists the completed items through the backend, `tcw/capabilities/cli.py:201`, `:214`), and the web app's work routes for such a project | every key under `work.jira`; and `work.tags` when tickets are read or written, since a ticket's labels are kept only when registered (`read_props`, `tcw/work/jira/backend.py:354`; `:437`) |
| b | Applying or checking a tag: `tcw work new` and `tcw work edit` given `--tag` (`validate_changes`, `tcw/work/model.py:189-212`, which reads the registered tags only for the tags added; `--untag` reads none in a filesystem project), `tcw work list --tag` (`tcw/work/cli.py:244-246`; `tcw/work/fs_backend.py:342`), `tcw work tags list`, `add` and `rm` (`tcw/work/cli.py:620-665`), the `tags` of the web app's project summary (`GET /api/project`, `tcw/serve/work.py:173`) | `work.tags` |
| c | `tcw config show` (Design 7.1) | every key |
| d | `tcw validate` | as 3.6 says: it never stops on an undecided key |

**Opening a filesystem-mode store reads no inherited key.** So in a
filesystem project every `tcw work` command that lists, reads, creates,
changes or moves items without a tag option is never stopped by a gap
through this item. Two places read `work.tags` today on every create and edit
whether or not a tag is applied (`registered_tags=self.config.tags`,
`tcw/work/fs_backend.py:286`, `tcw/work/jira/backend.py:628`); they must read
it only when a tag is added.

**A command that needs only configuration that is not inherited, or only the
active project's ID, does not open the store for it.** Today these open it
(`open_backend(project_root())`), and in a Jira-mode project with an
undecided `work.jira` they would stop with exit 7 although they need nothing
inherited:

- `tcw work lifecycle` (`tcw/work/cli.py:567`) and `tcw work docs` (`:596`),
  which read stages and documentation entries;
- `tcw work stage prompt` and `tcw work procedure` given no item (`:441`),
  which compose from the stage bindings and the backend kind's fixed facts
  (`external_stages`, a constant of each backend class,
  `tcw/work/jira/backend.py:216`, `tcw/work/fs_backend.py:235`);
- the note of Design 4.9 (`_personal_note`, `:455`) and the write check
  `_own` (`:71`), which compare project IDs;
- `resolve_item` given an item of another project (`:56`): it opens the
  active project's store before it sees that the item is another project's
  (`:64-65`). It must take the project from the argument first, so
  `tcw work show <an item of another project>` reads that project and is not
  stopped by the active project's undecided `work.jira`. A Jira key typed
  where an item is named (`:57-62`) still needs the active project's store.
- `tcw work path` given no item (`:318`), which prints the work path. The
  work path is not inherited.
- Checking a reference into a Jira-mode project, the active one or another:
  a `tcw://` work link, through `tcw/refs.py:139`, and an item's reference
  to another project's item, through `reference_resolver`
  (`tcw/work/open.py:210-241`). Both build a `JiraBackend` and then answer
  from the item folders (`link_exists`), which need no Jira setting. Left as
  they are, a gap would give wrong answers, not a stop. `resolve_tcw_ref`
  catches every exception (`tcw/refs.py:123-124`). So for the first, the
  result would be a false `error` finding in `tcw validate`'s link check
  (`tcw/validate.py:337-348`) and a false answer from `/api/resolve`
  (`tcw/serve/records.py:223`). `reference_resolver` catches only
  `NotFound`, `Unreachable` and `BackendError` (`:222-227`). So for the
  second, an `InheritedUnavailable` from the referenced project would escape
  and stop `tcw validate` with exit 7, against 3.6. No `tcw taxonomy` or
  `tcw capabilities` command calls either; only `tcw validate` and the web
  app do.

They read the configuration as `tcw work tags list` already does
(`read_work_config`, `tcw/work/open.py:48-51`). They read the project ID
from the registry, as `open_backend` does (`:71`). They keep every check
`open_backend` makes before it builds a backend: the project graph is valid
for the active project, and the work path can be found (`:65-74`). So each
of them fails, when it fails, with today's exit code and message. How is the
plan's choice.

A command not in (a)-(c) reads no inherited key and is never stopped by a
gap through this item. That is every `tcw taxonomy` and `tcw capabilities`
command (apart from TCW-108 Design 6.3's `extends`, and `tcw capabilities
drift` in a Jira-mode project, row a), `tcw projects list`, the commands just
listed, and every filesystem-mode command without a tag option.

**The web app** answers a request that reads an undecided key as it answers
any `InheritedUnavailable` (HTTP 500, `tcw/serve/server.py:90-91`, as
TCW-108's plan, choice 7, records), with one exception: the project summary
(`GET /api/project`) gives `tags` as `{"unavailable": <3.3's message>}`, the
shape it already gives a field it cannot read (`unavailable`,
`tcw/serve/work.py:81-82`), and answers its other fields, so that the web app
still opens on a filesystem project whose tags are undecided.

3.5. **The answer to TCW-108's conflict.** TCW-108 asked which work settings
a work command needs from its parents, and whether a missing parent stops it
(TCW-108's handoff on this ticket). With `work.backend` the project's own
(1.2):

- **A filesystem-mode project** lists, reads, creates, changes and moves its
  own items without any parent, as TCW-99 requires (design.md:386-388;
  TCW-108 Design 6.1). Only a command that applies, checks or lists tags is
  stopped, when the project's `work.tags` is undecided; setting `work.tags`
  in the project decides it.
- **A Jira-mode project whose link to a missing parent passes `config`**
  cannot open its store: `work.jira` is then always undecided, because the
  parent could set any key under it, optional ones such as `timeout` and
  `priorities` included, and the project cannot both remove the inherited
  mapping with `null` and set its own keys, since its shared file holds one
  value per key. TCW-99 says this case stops: "a command that needs an
  inherited setting, such as Jira settings a project takes from its parent"
  (design.md:389-393). The remedies are to fetch the parent
  (`tcw project provision <id>`, named by the message) or to leave `config`
  out of that parent's `inherit`; the documentation names both (TCW-117).

**No TCW-108 criterion changes; some of its tests may.** TCW-108's
`tcw work list` sentences hold under this item as written. They run in
filesystem projects with no tag option: AC 18, AC 20 and AC 31, where AC 31
is `app: [lib]` with `lib`'s links unreadable and `tcw work list` in `app`
exiting 0. Their tests are in TCW-108's plan, Step 10. Its `tcw validate`
sentences also hold, since each asks for a finding "naming" a project or
"containing" a phrase. But the `unresolved` finding in some of them gains
3.6's suffix. That happens wherever a parent that passes `config` is missing
or unreadable and the child sets no `work.tags`. The cases are:

- AC 19: `app: [core]`, `core` missing, with `taxonomy.extends: [core]`,
  and its "what lies above is unknown" sentences (`lib` missing, and the same
  with `lib` unreadable, TCW-108 plan, Step 11);
- AC 20: a missing grandparent;
- AC 31: `lib`'s links unreadable.

AC 18 and AC 26 are not among them, because their missing project is behind
`inherit: none`. A TCW-108 test that compares the whole text of such a
finding is amended by this item to the new text (Decision 24). The same goes
for any other test the plan's search finds that runs `tcw validate`, a tag
command, a Jira-mode work command or `tcw config show` with a parent that
passes `config` missing or unreadable. The list is the plan's, not this
spec's.

3.6. **`tcw validate`** never stops on an undecided key. A check that would
read one is skipped: the configuration's parse problems for that key (3.2),
the work store's checks in Jira mode when `work.jira` is undecided, and the
unregistered-tag check when `work.tags` is undecided
(`work_store_problems`, `tcw/work/fs_backend.py:527-536`). TCW-108 already reports
each gap once, as an `unresolved` finding (TCW-108 Design 6.5, rows a and d);
when a check was skipped because of a gap, that finding gains the suffix
`; could not check the configuration inherited from it`, placed after any
row (c) suffix, once. `tcw validate` then exits 0 when nothing else is wrong.

3.7. **The check every command makes first** (`tcw/cli.py:655-661`) does not
treat an undecided key as a problem, so a command that reads none reaches its
own work.

### 4. Environment overrides

4.1. **The name** (design.md:512-520). The variable that sets key `K` of
project `P` is `TCW_` + the key's parts joined by `_` + `__` + the project ID,
all in capitals, with each hyphen written `_`. So `work.jira.credentials.email-env`
of project `my-proj` is `TCW_WORK_JIRA_CREDENTIALS_EMAIL_ENV__MY_PROJ`, and
`user.name` of `tcw` is `TCW_USER_NAME__TCW`.

4.2. **Which variables are overrides.** A variable whose name starts with
`TCW_` and contains `__` is an override; no other variable is
(design.md:546-550). So `TCW_PROJECT_<ID>`, `TCW_CONFIG_DIR`,
`TCW_NO_PERSONAL_CONFIG`, `TCW_STDIN_TIMEOUT`, the variables TCW sets for
hooks, and credential names such as `TCW_JIRA_EMAIL` are untouched. An
override's name must match
`^TCW_[A-Z0-9]+(_[A-Z0-9]+)*__[A-Z0-9]+(_[A-Z0-9]+)*$`; one that does not
(`TCW__ALL__WORK_TAGS`, `TCW_WORK__`, `TCW_WORK___APP`, a lower-case letter)
is a problem:

```
<NAME>: a variable starting TCW_ that holds '__' sets configuration, and is written TCW_<KEY>__<PROJECT>: the key's parts and the project ID in capitals, each '.' and '-' written '_'
```

4.3. **Decoding the key** (design.md:521-526). The key part is matched
against the table of keys TCW knows: every key reachable through mappings in
`.tcw/tcw-config.yaml` (`id`, `parents`, `children`, `user.name`, the
`taxonomy` and `capabilities` sections, whose `extends` keys TCW-112 takes
out of the table, and under `work` the keys of
`WORK_KEYS`, `STAGE_KEYS` for each stage of the stage table, `HOOK_KEYS`,
each procedure of `PROCEDURE_IDS`, and the Jira keys of 1.1:
`tcw/work/config.py:41-44`, `tcw/work/model.py:305-317`,
`tcw/store/base.py:654-655`, `tcw/work/jira/config.py:31-36`). Each `_` in
the key part is read as either `.` or `-`, and the key is the one entry of
the table whose encoding is the key part. A key part that matches no entry is
a problem:

```
<NAME>: no configuration key is written <KEY PART>; a key's parts are joined by '_', and a '-' inside a part is written '_' too
```

**Every key has one name, and every name at most one key.** Because every
key and project ID follows TCW-106 Design 5.1, no name has a doubled `_`
inside its key part or its project part, and `__` splits them. No two entries
of the table encode to the same name; a test over the table checks it (AC 26).
The design foresees a collision where a key part is chosen by the user, such
as a stage or procedure name, and asks `tcw validate` to report one
(design.md:523-526). In 4.0 no mapping key is chosen by the user: stage names
come from the stage table (`_parse_stages` refuses any other,
`tcw/work/config.py:403-405`), procedures from `PROCEDURE_IDS` (refused
otherwise, `:440-445`) and priorities from `PRIORITIES`. So no configuration
can produce a collision, and that check is not built; a release that adds a
user-chosen key adds it.

Keys inside a list entry (a binding's `blob`, `when`, `file`) have no name:
a list is replaced whole, and one entry cannot be overridden
(design.md:541-545).

4.4. **The project part, and when a variable applies.** The project part is
read as a project ID by writing it in lower case with each `_` as `-`, which
is unambiguous because IDs have no `_`. A variable applies to that project's
configuration, at the place Design 2.1 gives it, when that project is one of
the configuration sources being folded, whether for the active project or
for a project read for itself (5.2), and `TCW_NO_PERSONAL_CONFIG` is not set
(5.3). A variable naming a project not folded by this command does nothing.

**Every override in the environment is checked** by every command that loads
configuration, whichever project it names (4.2, 4.3, 4.5, 4.6): the key table
is the same for every project in 4.0 (4.3), so a misspelt key or a shared key
is caught wherever the command runs, and a CI job that sets variables for
several projects learns of a mistake in any of them. A problem is a
configuration problem with no file (shown by `tcw validate` at `environment`,
`tcw/validate.py:375`), and stops every command with exit 1, as a bad
`TCW_NO_PERSONAL_CONFIG` does today (`tcw/config.py:683-687`). A misspelt
project part cannot be caught this way; Risks names it.

**These problems belong to the active project's configuration only.**
Several things read a project for itself (5.2): a reference check, a
lookup, a filing. Such a reading applies only the variables that name the
project and pass every check, and reports no variable problem. Otherwise one
misspelt variable would also give a false `error` for every `tcw://` link
into another project in `tcw validate`, whose link check runs whatever the
configuration holds (`tcw/validate.py:327-348`): opening that project would
raise `ConfigError` (`tcw/work/open.py:43-44`), which `_resolve_work` reports
as the link's failure (`tcw/refs.py:158`). The web app's reads of another
project would fail the same way. The active project's configuration already
stops every command on the problem. (An item's reference into another
project is not reached in that case: `tcw validate` skips the work store's
checks, the reference check among them, when the active project's
configuration has a problem, `tcw/validate.py:571-573`.)

4.5. **Only allowed keys** (design.md:535-540). A variable may set a key of
the allowed list (Design 5.1), or a mapping that leads to one; in that
mapping the keys that are not allowed are refused, one problem per value, as
a personal file's are (`_allowed`, `tcw/config.py:369-405`). A key outside the
list is a problem:

```
<NAME>: <dotted key> is a shared key; an environment variable cannot set it
```

4.6. **Values are read by the key's type** (design.md:541-545), from the
table of 4.3:

- **Text** (`user.name`, the credential variable names): the value exactly as
  written, with no YAML reading, so `no`, `on`, `1.0` and `null` stay text.
  The key's own rules then apply (`user.name` must be a name,
  `tcw/config.py:383-387`; a credential name must look like a variable name,
  `VARIABLE`, `tcw/work/jira/config.py:23`).
- **A list or a mapping** (a stage's `prompt` or `post`, a procedure's list,
  and the mappings above allowed keys, such as `work.stages.spec` or
  `work.jira.credentials`): the value is read as YAML, with duplicate keys
  refused as in a file (`UniqueKeyLoader`, imported at `tcw/config.py:35`),
  and must be that kind. It is merged at its place in the fold exactly as the
  same value in a personal file is (2.2): **a list replaces the whole list**,
  and a chain list's `inherit: true` entry works as in a file (2.4); **a
  mapping is merged key by key**, so it changes only the keys it holds and
  can never remove a key it does not hold. So
  `TCW_WORK_STAGES_SPEC__APP='{prompt: [{blob: p}]}'` changes the spec
  stage's `prompt` and leaves its `status`, `pre` and `enabled` as the team
  set them. The design says a list or mapping "replaces the whole value"
  (design.md:543-545); this spec departs from that for a mapping, because a
  mapping replaced whole would delete keys no personal layer may change
  (5.1), and the allowed list would then protect only the keys a variable
  writes, not the ones it leaves out. A value that is not valid YAML, is the
  wrong kind, or is `null` is a problem:
  `<NAME>: is not valid YAML`; `<NAME>: <dotted key> must be a list` (or
  `a mapping`); `<NAME>: null has no meaning in an environment variable;
  unset it instead`.
- **A boolean or a number**: must be a valid one (`true` or `false`; a number
  as YAML writes one). No allowed key has either type in 4.0 (Design 5.1); the
  rule is stated so the reader handles every type of the table when the list
  grows.

**No problem message contains a variable's value**, since a value can be a
token pasted in by mistake (the rule `tcw/work/jira/config.py:5-8` applies to
credentials).

4.7. **The more specific variable wins** (design.md:532-534). The variables
naming one project are applied in order of the number of parts in their key,
fewest first, so `TCW_WORK_STAGES_SPEC__APP` (a mapping) is applied before
`TCW_WORK_STAGES_SPEC_PROMPT__APP` (one key in it), and the second replaces
the `prompt` the first set. (The design's own example pairs
`TCW_WORK_JIRA__APP` with `TCW_WORK_JIRA_SITE__APP`. The second is refused in
4.0, because `work.jira.site` is not on the allowed list (5.1), and the first
may hold only the credential names under `work.jira`; the rule is the same
for the keys that are allowed.) Two variables with the same number of parts set
different keys, neither inside the other, so their order does not matter.

4.8. **A `file:` or `command:` binding from a variable** belongs to the
project the variable names: a `file:` path is read from that project's root
and may not leave it (`_confinement`, `tcw/config.py:533-554`, with the
project root as the folder), and a command runs with `TCW_CONFIG_DIR` set to
that root (`tcw/work/hooks.py:77`). Reason: a variable has no file, and the
project root is where the shared file's own bindings resolve from
(TCW-106 Design 1.4).

4.9. **A command says when a variable changed what it composed**, as for a
personal file (`docs/use-cases.md` S-5): the `note:` that
`_personal_note` prints (`tcw/work/cli.py:449-460`) names each variable that
set the list being composed, after the files; and a failed `post` command
from a variable names the variable where it names the file today
(`from <file>`, `tcw/work/hooks.py:71-73`), as `from <NAME>`.

### 5. Personal files and variables

5.1. **The allowed list** is `PERSONAL_KEYS` as it is today
(`tcw/config.py:45-52`), for both personal files and variables:

- `user.name`
- `work.stages.<stage>.prompt` and `work.stages.<stage>.post`
- `work.procedures.<procedure>`
- `work.jira.credentials.email-env` and `work.jira.credentials.token-env`

and, from TCW-108 (Design 2.2; its plan's Step 9, `LOCAL_ONLY_KEYS`),
`children`, in the project's `tcw-config.local.yaml` only. So neither a
personal file nor a variable can set a project's `id`, its `parents`, its
store locations (`work.path`, `work.repository`, and the `path` and
`repository` of `taxonomy` and `capabilities`), `extends`, a stage's
`status` or `pre`, `work.backend`, `work.tags`, or any other Jira setting
(design.md:535-540). **No variable sets `children`**: a variable would make
the family, and so every view and count, differ between environments, which
TCW-99 avoids for two engineers on one commit (design.md:371-373) and TCW-108
avoids for the user-wide file (TCW-108 Design 2.2). **No variable sets a
store location**, as TCW-110 recorded (its Questions for TCW-99, 1): the
design's example `TCW_WORK_PATH__MY_PROJ` (design.md:516-518) contradicts its
own rule and is not built. A store elsewhere on one machine is placed by
`tcw-manifest.local.yaml` (TCW-110 Design 7.1), and a project's folder by
`TCW_PROJECT_<ID>` (TCW-107 Design 2.1). `tcw-version` is information about a
file, not a key (TCW-106 Design 3.3), so `TCW_TCW_VERSION__<P>` names no key
(4.3).

5.2. **Whose personal settings apply.** Personal layers apply to the
configuration of the project a command acts on, and to every project in its
configuration sources (2.1): for each such project, the user-wide file, its
`tcw-config.local.yaml` (in a linked worktree with no local file of its own,
the main checkout's, TCW-107 Design 4.2), and the variables naming it. From a
project other than the active one only the keys of 1.1 are taken (1.6), and
of the allowed keys only the credential names are among them, so a person's
credential names for an ancestor reach the active project through what that
ancestor passes. This follows the design: "each project's configuration is
assembled from its own files …, then environment variables, and only then
inherited by its children. So a child that inherits a value gets the
overridden one" (design.md:507-511).

A project read **for itself** rather than as the active project's source (a
project named by a full identifier outside the family, a descendant, the
target of a filing until TCW-114) is folded over its own configuration
sources from their shared files **and the variables naming each of them**,
with no personal file (today's reading uses shared files only:
`load_config(personal=False)`, `tcw/config.py:577-580`;
`open_backend(…, personal=False)`, `tcw/work/open.py:99`).

- **Variables apply**, as the design says ("Load that project's
  configuration: its files, inheritance, local overrides and environment
  variables", design.md:276-281). A variable names its project explicitly,
  so it is the person's stated setting for that project wherever it is read;
  otherwise `TCW_WORK_JIRA_CREDENTIALS_EMAIL_ENV__CORE` would change `core`'s
  credential names when they reach `app` (AC 11) but not when `app` reads
  `core`'s own items.
- **Personal files do not**, which departs from the design's "local
  overrides" in that same sentence. `docs/use-cases.md` S-5 requires that
  "another project's personal file is never read: commands acting on
  another project use only its shared configuration", and the 3.x code keeps
  it (`tcw/work/cli.py:449-452`). A personal file belongs to one checkout,
  and the person acting in another project has not chosen it for this read.
- **A gap in such a project's configuration sources** is handled as for the
  active project (Design 3) when the command reads that project's object by
  its full identifier, or runs in that project: a command that reads an
  undecided key of it stops with exit 7, the message naming that project as
  `<P>` (a broken key, exit 1, likewise, Design 1.6). When the project is one
  of several a scoped listing covers (TCW-113's `--scope up`, `down` or
  `all`), the listing does not stop: it reports that project as unavailable,
  with this message as the reason, on standard error and in `projects`, and
  exits 0 (TCW-113 Design 1.6 d). A command that reads no such key is not
  stopped. (Amended at TCW-113's handoff, 2026-10-22, which follows the
  user's TCW-108 Design 6.6 decision that a problem in another project does
  not stop the active project.)
- **Its configuration sources are found through the command's own
  registry**, the one that found the project. A registry opened afresh with
  that project as the active one would read that project's personal
  `children`, which only the active project's registry reads (TCW-108
  Design 2.1, 2.4). It could also place an ancestor in a different folder
  from the one the command found it in (TCW-108's plan, re-check R4).
- `TCW_NO_PERSONAL_CONFIG=1` turns these variables off too (5.3).

Credential names from a personal layer are set aside, as today, when the
configuration being folded is not in Jira mode (`_without_credentials`,
`tcw/config.py:417-436`, `:627-629`). In Jira mode is decided by the
`work.backend` of the project whose configuration is folded, from its own
shared file (1.2), which personal layers cannot change (5.1).

5.3. **`TCW_NO_PERSONAL_CONFIG=1`** turns off every personal layer: no
user-wide file, no `tcw-config.local.yaml` of any project, and no override
variable is read or checked (design.md:538-540). It does not turn off
`TCW_PROJECT_<ID>`, which says where a project is rather than how it is
configured (TCW-107 Design 1.10). Any other value is the problem it is today
(`tcw/config.py:683-687`), and then no personal file and no override variable
is read either.

### 6. The tag registry commands

6.1. **`tcw work tags list`** prints the merged `work.tags`, inherited tags
included, one per line (`tcw/work/cli.py:620-623`).

6.2. **`tcw work tags add <tag>…`** writes only the active project's own list.
Tags already in the merged list are left alone. Otherwise the written
`work.tags` is the project's own entries plus the new tags, sorted, and keeps
an `inherit: true` entry first when the own list holds one. When the project's
shared file has no `work.tags` and the project has a configuration source
other than itself, the written list is `inherit: true` followed by the new
tags, so the project keeps following its parents, including tags a parent
adds later. That holds whether or not any parent has a tag today: deciding by
the merged list instead would write a plain `[z]` in a child whose parents
have no tags yet, and cut it off from every tag they add afterwards. A
project with no configuration source but itself gets the plain list, as
today. The file is edited as today, changing only those lines
(`config_edit`, `tcw/work/cli.py:633-645`).

6.3. **`tcw work tags rm <tag>…`** removes a tag from the project's own list.
A tag that would still be registered afterwards because it is inherited (an
earlier project in the order declares it and the own list is absent or holds
`inherit: true`) is refused, exit 3, and nothing is written:

```
tag '<tag>' is inherited from '<project>'; to drop it, list this project's tags under work.tags in .tcw/tcw-config.yaml without an 'inherit: true' entry
```

where `<project>` is the last project in the order whose own list holds the
tag. A tag registered nowhere is refused as today (exit 4,
`tcw/work/cli.py:653-665`).

### 7. What a person sees

7.1. **`tcw config show`** prints the merged configuration, inherited values
included. With an undecided key it exits 7 with Design 3.3's message, naming
the first undecided key in the order of Design 1.1's list (`work.tags`
before `work.jira`), and prints nothing, with or without `--origin`; with a
broken key and none undecided, it exits 1 with 1.6's message and prints
nothing: what it would print is not the
configuration the commands run with. `--origin` keeps its labels
(`tcw/config_cli.py:119-137`) and adds two: a value inherited from another
project is labelled with its layer and the declaring file's whole path
(`project: /…/core/.tcw/tcw-config.yaml`), and a value from a variable with
`environment: <NAME>`. The new command group's own format is TCW-115's.

7.2. **`tcw validate`** reports each problem of Design 4 as an `error` whose
`where` is `environment` and whose message starts with the variable's name;
the run fails, as for a personal file's problem.

## Abstraction litmus test

| Operation | Layer | Verdict |
| --- | --- | --- |
| Folding inherited keys over the configuration sources (Design 1, 2) | model | Passes: any store that keeps each project's declared settings can answer "what does each project in this order declare for `work.tags`", and the fold runs in `tcw/config.py` over those answers. The order is TCW-108's, computed from parent links alone. |
| Undecided keys and exit 7 (Design 3) | model | Passes: "a project in the order is declared but its settings cannot be read here" is a state any registry reaches (TCW-108's own verdict for `sources`). |
| Environment overrides (Design 4) | CLI | Not a store operation: they are how the command line reads the process's environment, the same for every store. The name rule, the key table and the type reading are pure functions. |
| The allowed list and whose personal settings apply (Design 5) | model | Passes: a per-person addition to a project's settings, restricted to named keys. Reading it from `tcw-config.local.yaml` and the user-wide file is how the files store keeps a personal setting; a store that keeps no personal settings has none. |
| `tcw work tags add` and `rm` (Design 6) | CLI over the files store | The tag registry is a key of `.tcw/tcw-config.yaml`, which belongs to the repository, not to a work backend (`docs/lifecycle/abstraction.md`, the second question): it is read and edited as a file in both work modes, as today. |
| `tcw config show`, `tcw validate` findings (Design 7) | CLI | Presentation of model answers. |

No work backend operation is added or changed: the twelve operations in
`tcw/work/backend.py` are untouched. A Jira-mode project whose `work.jira`
is inherited opens the same `JiraBackend` with the merged settings
(`tcw/work/open.py:75-77`).

## Use cases

- **UC-1 (a single project).** No `parents:`: the configuration sources are
  the project alone, nothing is folded from elsewhere, nothing is undecided,
  and with no override variable set every command prints what it printed
  before this item (AC 27). The cost is reading the process's environment
  once per command for names starting `TCW_` and holding `__`. `null` on a
  key of 1.1 is new meaning in a file where it was a problem before
  (Problem 4); `work:` with nothing under it keeps its meaning (2.5).
- **UC-2 (a library others read).** A reader whose link to the library passes
  `config` (the default, `inherit: all`) takes the library's tags, and its
  Jira settings when the reader is in Jira mode, unless it sets its own; the
  library's backend never reaches it (1.2). A reader that wants none writes
  `inherit: [taxonomy]` or `[taxonomy, capabilities]`. A problem in the
  library's inherited keys stops only the reader's commands that read that
  key, until the reader overrides the key or the library fixes it (1.6); a
  problem in any other library key does not reach the reader. Nothing about
  the reader is read from or written into the library.
- **UC-3 (a monorepo).** The packages name the root as a parent and take its
  `work.jira` and `work.tags`, so the Jira block is written once; each
  package writes `work.backend: jira` itself (1.2) and maps its own stages to
  Jira statuses (stages are the project's own, design.md:488-490; Notes,
  "Settled questions", 3). A package whose second parent passes only taxonomy
  takes no settings from it (AC 3).
- **UC-4 (a planning workspace).** The workspace is a parent with
  `inherit: none` (TCW-108 UC-4), so nothing in it reaches the code projects
  and a fresh clone of a code repository is never stopped by its absence. A
  workspace that does pass `config` makes a clone without it stop only where
  3.4 says (tag commands, and every store command in Jira mode), and its
  `tcw validate` still exits 0 (AC 29, two git repositories).
- **UC-5 (a shared Jira project).** Inheriting `work.jira.project` puts a
  child's items in the parent's Jira project, told apart by the "TCW Project"
  field as today (`docs/use-cases.md` UC-5; design.md:486-488). Each child
  writes `work.backend: jira` itself (1.2). Credentials stay per person: the
  shared files name variables, and a person may rename them in a personal
  file or an override variable, for the project or an ancestor (5.2).
- **UC-6 (a project not on this machine).** A missing configuration source
  stops only a command that reads an undecided key (Design 3), exit 7, naming
  the project and how to fetch it; `tcw validate` says "could not check" and
  passes. A filesystem project keeps listing, reading and moving its own items
  (AC 13), as UC-6 requires ("A missing child or upstream must not break
  commands that do not need it"). A Jira-mode project that takes its Jira
  settings from the missing parent stops on every store command, as TCW-99
  says it does (design.md:389-393; Design 3.5).
- **UC-7 (a public library, private readers).** Nothing flows up a link. A
  private reader that takes the public library's configuration takes its tags
  (and its Jira settings, if the reader is in Jira mode); such a reader will
  usually write `inherit: [taxonomy]`. The
  person's own personal file in their checkout of the library can rename the
  credential variables the reader inherits (5.2); the library's committed
  files are never written.
- **UC-8 (several families on one machine).** An override variable names a
  project by ID, so, like `TCW_PROJECT_<ID>`, it applies to every family on
  the machine using that ID. Every override in the environment is checked
  wherever a command runs (4.4), so a stale or misspelt key is reported in any
  family.
- **S-1, S-2, S-3.** Nothing asks a person; everything is in the CLI, so
  Claude Code, Codex and Pi see the same; no backend operation changes, and
  the fold is the same for a filesystem and a Jira project. Design 3.4 (a)
  names the one difference: opening a Jira-mode store reads `work.jira`, and
  reading tickets reads `work.tags`, while opening a filesystem store reads
  no inherited key (AC 13, 14).
- **S-4 (worktrees, clones).** An ancestor's `tcw-config.local.yaml` follows
  TCW-107 Design 4.2 in a linked worktree. A fresh clone in CI has no personal
  files; override variables are how such a run names its user and its
  credential variables, and a missing parent there gives exit 7 only where 3.4
  says.
- **S-5 (personal configuration).** One allowed list for files and variables
  (5.1); a note names the variable that changed a prompt (4.9);
  `TCW_NO_PERSONAL_CONFIG=1` drops both (5.3). The requirement "another
  project's personal file is never read" now holds for a project read for
  itself (which takes only the variables naming it), while an ancestor's
  personal credential names reach its children (5.2, following
  design.md:507-511); TCW-117 rewords it (Notes).
- **S-6 (unattended runs).** Exit 7 for an undecided key is the same code
  TCW-108 gives every missing inherited thing; a variable's problem is exit 1,
  like a personal file's.
- **S-7 (several people).** Personal files and variables change only one
  person's configuration and only the allowed keys; two people on one commit
  get the same team settings, inherited ones included.
- **S-8 (partial failure).** `tcw work tags add` and `rm` write one file or
  nothing (Design 6). A command stopped by an undecided key writes nothing
  (3.3).
- **S-9 (upgrades).** A 3.x configuration that names a credential variable
  starting `TCW_` and holding `__` would now be read as an override (4.2);
  TCW-116 reports it (Notes). Old code reading new files is not a constraint.
- **S-10 (things TCW does not own).** Nothing is found by scanning; the fold
  reads only the projects TCW-108's order names.
- **S-11 (version control).** No git reads or writes are added.

Checklist: 1 (where it looks) the configuration sources, through TCW-108 and
TCW-107; a source in another repository is AC 29. 2 (whose things) only the
active project's own `.tcw/tcw-config.yaml` is written (Design 6). 3 (reading
across projects) Design 1-3: several levels (AC 4), two routes to one
project (AC 5), a missing project (AC 13-15), a shared Jira project (AC 1, 6),
a worktree (AC 33).
4 (backends) the litmus table; both work modes (AC 13, 14). 5 (who is
present) nothing asks. 6 (harness) CLI only. 7 (stopping halfway) nothing
multi-step. 8 (single project) AC 27. 9 (older and newer) S-9 above. 10
(testing the setup claimed) AC 29 builds two git repositories.

## Acceptance criteria

Every fixture project is a TCW 4.0 project with a valid ID; parents are
declared with TCW-108's `parents:`, and every other project's folder is
found by a manifest entry or TCW-107's search, as the layout makes obvious.
`core`'s **Jira block** means `work.backend: jira` with
`work.jira: {site: https://core.example.net, project: CORE, credentials:
{email-env: CORE_EMAIL, token-env: CORE_TOKEN}, fields: {project: TCW Project,
item: TCW Item}}`. "**P in Jira mode**" means that `P`'s own shared file
writes `work.backend: jira` (the backend is never inherited, 1.2) and maps
each enabled stage to a status of its own; a project not said to be in Jira
mode writes no `work.backend` and no `status`, which would be a problem in
filesystem mode (`tcw/work/config.py:372-377`). "The tags of P" means the lines `tcw work tags list`
prints in `P`, compared as a set. "P's configuration" means
`tcw.config.load_config(<P's root>)`, called with the environment the
criterion gives; `.work.backend`, `.jira.site` and the like are its fields.
No criterion makes a network request.

1. **The inherited keys cross.** `app: [core]`; `core` has the Jira block and
   `work.tags: [a, b]`; `app` is in Jira mode and sets nothing else.
   `app`'s configuration has `jira.site` `https://core.example.net`,
   `jira.project` `CORE`, `jira.email_env` `CORE_EMAIL`; the tags of `app`
   are `a, b`.
2. **Nothing else crosses.** `core`, in filesystem mode, also sets
   `work.hooks.timeout: 5`, `work.stages.spec.prompt: [{blob: core-text}]`,
   `work.procedures.search: [{blob: core-search}]`, `work.documentation` with
   one entry, and `work.path: elsewhere`. In `app`: `work.hooks.timeout` is
   the built-in value; `tcw work stage prompt spec <an app item>` and `tcw work
   procedure search` print nothing containing `core-text` or `core-search`;
   `tcw work docs` prints `app`'s own entries (none); `tcw work path` is under
   `app`'s folder.
3. **Only a link that passes `config` carries it.** In AC 1's layout with
   `app: [{id: core, inherit: [taxonomy]}]`, `app` in Jira mode setting
   `work.jira.project: APP` and nothing else under `work.jira`: `tcw validate`
   in `app` exits 1 with a `required` error at `work.jira.site`; with `app` instead
   writing no `work.backend` and no statuses, `tcw work tags list` prints
   nothing. With `inherit: [config]` and that second `app`, the tags are
   `a, b`.
4. **Several levels.** `app: [lib]`, `lib: [core]`; `core` sets
   `work.tags: [a]`, `lib` sets no tags: the tags of `app` are `a`. With `lib`
   setting `work.tags: [c]`, they are `c`.
5. **The last project that declares a key wins, over the whole order.** `bb`
   sets `work.tags: [b]`; `cc: [bb]` sets `[c]`; `dd: [bb]` sets none;
   `ee: [cc, dd]` sets none. The tags of `ee` are `c` (not `b`). With `dd`
   setting `[d]`, they are `d`. With `dd` setting `[{inherit: true}, d]`
   instead, the tags of `ee` are `c, d` and the tags of `dd` are `b, d`.
6. **Mappings merge key by key.** In AC 1's layout, `app` sets
   `work.jira.project: APP`: `app`'s `jira.project` is `APP` and its
   `jira.site`, `jira.email_env` and `jira.fields.item` are `core`'s.
7. **Lists are replaced; `inherit: true` adds.** `core` sets `work.tags:
   [a, b]`. `app` setting `[c]`: the tags are `c`. `app` setting
   `[{inherit: true}, c]`: `a, b, c`. A project with no parents setting
   `[{inherit: true}, c]`: `c`, and `tcw validate` reports no problem.
   `work.documentation: [{inherit: true}]` is refused with a message naming
   `work.tags`. Two `inherit: true` entries in `work.tags` are refused with
   `a list may hold one 'inherit' entry`.
8. **`null` removes an inherited value.** In AC 1's layout, with `core` also
   setting `work.jira.fields.effort: Effort`: `app` setting `work.tags: null`
   has no tags; `app` setting `work.jira.fields.effort: null` has
   `jira.fields.effort` None and `jira.site` still `core`'s. `app` setting
   `work:` with nothing under it, and no `work.backend`, keeps `core`'s tags.
   `work.tags: null` in `app`'s `tcw-config.local.yaml` is refused with
   `null has no meaning in a personal file`. `work.backend: null` in `app`'s
   shared file is refused with today's `must be one of` problem.
9. **The backend is not inherited, and an inherited Jira block without Jira
   mode is ignored.** In AC 1's layout, `app` writes no `work.backend` and
   no statuses: `app`'s configuration has `work.backend` `filesystem`,
   `tcw validate` in `app` reports no finding about `work.jira`, and
   `tcw work list` exits 0. The same `app` also writing its own
   `work.jira: {site: https://x.example.net}` gets today's problem
   `'jira' is only read with \`backend: jira\``.
10. **An ancestor's problem in an inherited key stops only what reads it; any
    other is not the reader's.** `app: [core]`, both in filesystem mode;
    `core` sets `work.tags: notalist`. In `app`: `tcw work tags list` and
    `tcw work new y --tag t` exit 1 with a message containing `core`'s
    `.tcw/tcw-config.yaml` as a whole path and `work.tags`, and no item `y`
    is created; `tcw work list`, `tcw work new x` and `tcw taxonomy list`
    exit 0; `tcw validate` exits 0 with a `warning` whose `where` is
    `core`'s `.tcw/tcw-config.yaml` and whose message names `work.tags`.
    `tcw validate` in `core` exits 1. With `app` setting `work.tags: [x]` as
    well, `tcw work tags list` in `app` prints `x` and `tcw validate` there
    reports no such warning. With `core` setting `work.hooks.timeout: soon`
    instead, `tcw work list` and `tcw validate` in `app` exit 0 and report
    nothing about it, and `tcw validate` in `core` exits 1.
11. **Personal settings of an ancestor flow down; a project read for itself
    takes its variables but no personal file.** In AC 1's layout: `core`'s
    `tcw-config.local.yaml` sets `work.jira.credentials.email-env: MINE`, and
    `app`'s `jira.email_env` is `MINE`. With
    `TCW_WORK_JIRA_CREDENTIALS_EMAIL_ENV__CORE=VAR` also set it is `VAR`.
    With `app`'s own `tcw-config.local.yaml` setting `email-env: APPS`, it is
    `APPS`. With `TCW_NO_PERSONAL_CONFIG=1`, it is `CORE_EMAIL`. Reading
    `core` for itself (`load_config(<core's root>, personal=False)`, or
    however the plan names that reading) gives `CORE_EMAIL` with only `core`'s
    personal file set, `VAR` with the variable set too, and `CORE_EMAIL` with
    `TCW_NO_PERSONAL_CONFIG=1` added.
12. **The user-wide file still beats the project's shared file.** The
    user-wide file sets `work.stages.spec.prompt: [{blob: mine}]` and `app`'s
    shared file sets `[{blob: team}]`: `tcw work stage prompt spec <item>` in
    `app` contains `mine` and not `team`, as before this item. With `app:
    [core]` and the user-wide file also setting `work.tags: [u]` (a shared
    key), `tcw validate` in `app` reports exactly one problem for it, an
    error at the user-wide file, as in a project with no parents, and no
    `warning` about `work.tags`; `tcw config show --origin` in `app` lists
    that value once among the values set aside.
13. **A missing parent, in filesystem mode.** `app: [core]`, `core` not on this
    machine, `app` setting nothing under `work` and holding a taxonomy store.
    In `app`: `tcw work list`, `tcw work new x`, `tcw work show <x>` and
    `tcw work advance <x> --dry-run` exit 0; `tcw work new y --tag t` and
    `tcw work tags list` exit 7 with a message containing `'app' inherits its
    configuration (work.tags) from project 'core', which is not on this
    machine:`, and no item `y` is created; `tcw projects list` and
    `tcw taxonomy list` exit 0; `tcw validate` exits 0 with exactly one
    `unresolved` finding naming `core`, containing `could not check the
    configuration inherited from it`, and no error. With `app` also setting
    `work.tags: [t]`, `tcw work new y --tag t` and `tcw work tags list` exit
    0. With the link written `{id: core, inherit: [taxonomy, capabilities]}`
    and `app` setting nothing, `tcw work tags list` exits 0 and prints nothing.
14. **A missing parent, in Jira mode.** `app: [core, {id: lib, inherit:
    none}]`, `core` not on this machine, `lib` here in filesystem mode with one
    item, `app` in Jira mode setting `work.jira.project: APP`. In `app`:
    `tcw work list` exits 7 with a message containing `(work.jira)`, and the
    Jira client makes no request (the test's fake client records none);
    `tcw validate` exits 0 with one `unresolved` finding naming `core`;
    `tcw capabilities drift` exits 7 with a message containing
    `(work.jira)`, and in AC 13's first layout it exits 0. These need no
    inherited key and exit 0: `tcw work lifecycle`, `tcw work docs`,
    `tcw work stage prompt spec` with no item, `tcw work procedure search`
    with no item, `tcw work path` with no item, `tcw taxonomy list`, and
    `tcw work show` given `lib`'s item by its full identifier (TCW-110), which
    prints that item with `lib` as its project. With one of `app`'s
    capability descriptions holding a `tcw://` link to one of `app`'s own
    items, `tcw validate` in `app` reports no finding about it. With one of
    `lib`'s items holding a reference to one of `app`'s items, `tcw validate`
    in `lib` reports no finding about that reference: there `app` is read for
    itself, and its `work.jira` is undecided too.
15. **An unreadable parent.** `app: [core]`, `core` here with
    `parents: notalist` in its file (TCW-108 Design 6.6), `app` setting nothing
    under `work`: `tcw work tags list` in `app` exits 7 with a message
    containing `'app' inherits its configuration (work.tags) through project
    'core', whose parents could not be read`, and `tcw work list` exits 0. The
    same holds with `core`'s shared file not valid YAML instead (Design 1.6),
    and `tcw validate` in `app` then exits 0 with one `unresolved` finding
    naming `core`. TCW-108's AC 31 test passes, amended only as Design 3.5
    says. With `core` instead a **descendant** of `app` (`app` lists `core`,
    and `core: [app]`) and `core`'s file not valid YAML, `tcw validate` in
    `app` reports it as an error, as before this item (Design 1.6). **When the
    order cannot be had** (Design 1.3): with `app`'s own file holding
    `parents: notalist`, and again with `app: [lib]`, `lib: [top]`, `top:
    [lib]` (a loop), `tcw validate` in `app` exits 1, prints TCW-108's graph
    problem as a finding line on standard output and ends standard error
    with its closing count (`… errors, … warnings, … unresolved`), rather
    than stopping with one error message; with `app` also setting
    `work.hooks.timeout: soon`, that problem is a finding of the same run.
    `tcw work list` exits 1, as before this item. `tcw work tags list` exits
    1 with the message `tcw work list` gives, which for the loop contains
    `loop in parents: lib -> top -> lib`. With `app` also setting
    `work.tags: [t]`, `tcw work tags list` prints `t`.
16. **A gap behind a link that passes no configuration stops nothing.**
    `app: [{id: ws, inherit: none}, core]`, `ws` not on this machine, `core`
    here with `work.tags: [a]`: the tags of `app` are `a`, and `tcw work list`
    exits 0.
17. **`tcw config show`.** In AC 1's layout, `tcw config show` in `app` prints
    `work.tags` `a`, `b` and `core`'s `work.jira.site`; with `--origin`, the
    comment on `site` contains `core`'s `.tcw/tcw-config.yaml` as a whole path.
    With `TCW_USER_NAME__APP=Robin`, it prints `user.name` `Robin`, and with
    `--origin` its comment is `environment: TCW_USER_NAME__APP`. In AC 13's
    first layout, `tcw config show` and `tcw config show --origin` exit 7 and
    print nothing on standard output. In AC 14's layout, where `work.tags`
    and `work.jira` are both undecided, `tcw config show` exits 7 with a
    message containing `(work.tags)`. In AC 10's first layout, it exits 1 and
    prints nothing on standard output.
18. **The tag registry commands.** In AC 4's first layout (`app` inherits
    `a`, sets no tags): `tcw work tags add z` in `app` writes `work.tags` as
    `[{inherit: true}, z]` in `app`'s shared file, changes no file of `core` or
    `lib`, and the tags of `app` are `a, z`; `tcw work tags add a` writes
    nothing; `tcw work tags rm a` exits 3 with a message containing `tag 'a' is
    inherited from 'core'` and leaves the file unchanged byte for byte; `tcw
    work tags rm z` leaves `[{inherit: true}]` and the tags are `a`. With
    `app: [core]` and `core` setting no tags, `tcw work tags add z` in `app`
    writes `[{inherit: true}, z]`; when `core` then sets `work.tags: [q]`, the
    tags of `app` are `q, z`. In a project with no parents, `tcw work tags
    add` and `rm` write exactly what they write before this item.
19. **The name of an override.** `TCW_USER_NAME__APP=Robin` sets `app`'s
    `user.name`; `TCW_WORK_JIRA_CREDENTIALS_TOKEN_ENV__MY_PROJ=MY_TOKEN` sets
    `work.jira.credentials.token-env` of project `my-proj` (in Jira mode).
    `TCW_PROCEDURE_X=1`, `TCW_PROJECT_CORE=<a folder>`, `TCW_JIRA_EMAIL=x` and
    `TCW_STDIN_TIMEOUT=3` give no configuration problem.
20. **Malformed names and unknown keys.** Each of `TCW__ALL__WORK_TAGS=x`,
    `TCW_WORK__=x`, `TCW_WORK___APP=x` and `TCW_user_NAME__APP=x` makes `tcw
    work list` in `app` exit 1 with a message starting with the variable's name
    and containing `TCW_<KEY>__<PROJECT>`. Each of
    `TCW_WORK_STAGES_SPEC_PROMPTS__APP=x`, `TCW_TCW_VERSION__APP=x` and
    `TCW_WORK_STAGES_DESIGN_PROMPT__APP=x` (no stage `design`) exits 1 with a
    message containing `no configuration key is written`.
21. **Only allowed keys.** Each of these makes `tcw work list` in `app` exit 1
    with a message containing `is a shared key; an environment variable cannot
    set it`: `TCW_ID__APP=x`, `TCW_PARENTS__APP='[core]'`,
    `TCW_CHILDREN__APP='[kid]'`, `TCW_WORK_PATH__APP=/tmp/x`,
    `TCW_WORK_REPOSITORY__APP=x`, `TCW_TAXONOMY_PATH__APP=x`,
    `TCW_WORK_BACKEND__APP=jira`, `TCW_WORK_TAGS__APP='[a]'`,
    `TCW_WORK_JIRA_SITE__APP=https://x.example.net`,
    `TCW_WORK_STAGES_SPEC_STATUS__APP=x` and `TCW_WORK_STAGES_SPEC_PRE__APP='[]'`.
    `TCW_WORK_STAGES_SPEC__APP='{prompt: [{blob: p}], status: x}'` exits 1 with
    one such problem, for `work.stages.spec.status`. Each of these, with
    the project `elsewhere` in no configuration this command reads, exits 1 in
    `app` too: `TCW_WORK_TAGS__ELSEWHERE='[a]'`; while
    `TCW_USER_NAME__ELSEWHERE=x` exits 0 and changes nothing in `app`.
22. **Values by type.** `TCW_USER_NAME__APP=no` gives `user.name` the text
    `no`; `TCW_USER_NAME__APP=null` gives the text `null`.
    `TCW_WORK_STAGES_SPEC_PROMPT__APP='[{blob: hello}]'`: `tcw work stage prompt
    spec <item>` in `app` prints `hello` and not TCW's built-in spec text; with
    `'[{blob: hello}, {inherit: true}]'` it prints both. Each of these exits 1:
    `TCW_WORK_STAGES_SPEC_PROMPT__APP=hello` (`must be a list`),
    `='[unclosed'` (`is not valid YAML`), `=null` (`null has no meaning in an
    environment variable`), `TCW_WORK_STAGES_SPEC__APP='[a]'` (`must be a
    mapping`), and `TCW_WORK_STAGES_SPEC__APP='{prompt: [], prompt: []}'` (a
    repeated key). For `TCW_WORK_STAGES_SPEC_PROMPT__APP='s3cr3t-token'`, the
    message does not contain `s3cr3t-token`.
23. **The more specific variable wins.** `TCW_WORK_STAGES_SPEC__APP='{prompt:
    [{blob: whole}]}'` and `TCW_WORK_STAGES_SPEC_PROMPT__APP='[{blob: one}]'`
    together: the spec prompt in `app` prints `one` and not `whole`. The same
    with the two set in the other order in the process's environment. **A
    mapping merges.** With `work.stages.spec.pre: [{blob: gate}]` in `app`'s
    shared file and `TCW_WORK_STAGES_SPEC__APP='{prompt: [{blob: p}]}'`,
    `tcw work lifecycle --stage spec` in `app` still lists `app`'s `pre`
    binding `blob:gate`, and the spec prompt prints `p`. With `app` in Jira
    mode mapping `spec` to the status `Specifying`, the same variable leaves
    `app`'s configuration mapping `spec` to `Specifying`.
24. **Bindings and notes from a variable.**
    `TCW_WORK_STAGES_SPEC_PROMPT__APP='[{file: notes.md}]'` with `notes.md` at
    `app`'s root: the spec prompt prints its text, and standard error has a
    line `note: this prompt was changed by personal configuration:` that names
    `TCW_WORK_STAGES_SPEC_PROMPT__APP`. With `'[{file: ../outside.md}]'`,
    `tcw work list` exits 1 with a message containing `resolves outside`.
    `TCW_WORK_STAGES_SPEC_POST__APP='[{command: sh record.sh}]'`, where
    `record.sh` at `app`'s root writes `$TCW_CONFIG_DIR` to a file, and a move
    into `spec` in `app`: the file holds `app`'s root. With
    `TCW_WORK_STAGES_SPEC_POST__APP='[{command: exit 3}]'` instead, the move
    reports the failed `post` hook with a message containing
    `from TCW_WORK_STAGES_SPEC_POST__APP`.
25. **`TCW_NO_PERSONAL_CONFIG=1` turns off the variables.** With it set,
    `TCW_USER_NAME__APP=Robin` does not set `user.name`, and
    `TCW_WORK_TAGS__APP='[a]'` (a shared key) and `TCW__ALL__X=1` (malformed)
    give no problem: `tcw work list` exits 0. With
    `TCW_NO_PERSONAL_CONFIG=true`, `TCW_USER_NAME__APP=Robin` does not set
    `user.name`, and `tcw work list` exits 1 with today's message
    `TCW_NO_PERSONAL_CONFIG must be 1`.
26. **One name per key.** A test over the table of keys TCW knows (4.3),
    with every stage of the stage table, every procedure of `PROCEDURE_IDS`
    and every priority filled in: no two entries encode to the same name, and
    decoding each entry's name gives back that entry.
27. **A single project pays nothing.** A project with no `parents:`, with no
    override variable set and `TCW_PROJECT_X`, `TCW_JIRA_EMAIL` and
    `TCW_STDIN_TIMEOUT` set: `tcw work list`, `tcw work tags list`, `tcw config
    show --origin` and `tcw validate` print the same as with those three
    variables unset, and the existing tests in `tests/config/` (the
    personal-layer suites and `test_config_show.py`) pass unchanged except where a criterion of
    this item changes the behavior they pin (the plan lists each).
28. **Validate reports a variable's problem.** With `TCW_WORK_TAGS__APP='[a]'`,
    `tcw validate` in `app` exits 1 with an `error` whose `where` is
    `environment` and whose message starts with `TCW_WORK_TAGS__APP`. With
    `TCW_WORK_TAGS__LIB='[a]'` instead, and one of `app`'s capability
    descriptions holding a `tcw://` link to an item of `lib` (here, read for
    itself), `tcw validate` in `app` reports that one `environment` error and
    no finding about the link (Design 4.4).
29. **Two repositories.** Repository A holds `ws`, which sets `work.tags:
    [plan]` and lists `app`; repository B, cloned inside A and ignored by it,
    holds `app: [ws]`, with no `work` settings.
    In `app`, the tags are `plan`. In a separate clone of repository B alone:
    `tcw work list` exits 0; `tcw work tags list` exits 7 naming `ws`; `tcw
    validate` exits 0 with one `unresolved` finding naming `ws` and containing
    `could not check the configuration inherited from it`.
30. **The records.** `docs/capabilities/cli/inherit-configuration-from-parents`
    and `docs/capabilities/cli/override-configuration-from-the-environment`
    exist, each record in `capabilities.yaml` says what this spec's Capability
    changes say, the taxonomy term `environment-override` exists, and `tcw
    validate` in this repository passes.
31. **The suite, as CI runs it** (`.github/workflows/test.yml`): bare `pytest`
    after `pip install -e '.[dev]'`, and `pnpm install --frozen-lockfile` then
    `pnpm check:build`, both pass on `v4`.
32. **The web app.** In AC 13's first layout, with `tcw serve` running in
    `app`: `GET /api/project` answers 200 with `tags` a mapping whose
    `unavailable` contains `(work.tags)`, and its other fields as before
    this item; `GET /api/work` answers 200. In AC 14's layout,
    `GET /api/work` answers 500 with an `error` containing `(work.jira)`.
33. **An ancestor's personal file in a linked worktree.** One git repository
    holds `core` at its root and `app: [core]` in a folder `app`, both in Jira
    mode, with `core`'s Jira block; the main checkout's
    `.tcw/tcw-config.local.yaml` for `core` sets
    `work.jira.credentials.email-env: MINE`. In a linked worktree of that
    repository (`git worktree add`) with no local files of its own, `app`'s
    `jira.email_env` read in the worktree is `MINE` (TCW-107 Design 4.2).

### Coverage

| Design rule | Criteria |
| --- | --- |
| 1.1 the inherited keys | 1, 6, 8 |
| 1.2 everything else stays; `work.backend` is the project's own | 2, 9 |
| 1.3 the configuration sources; per-parent `inherit`; read without raising; when the order cannot be had, and the message it carries | 3, 4, 15 (own `parents:` wrong, a loop named by TCW-108's message, a key the project decides itself), 16 |
| 1.4 an inherited relative path resolves from its declarer | n/a: no key of 1.1 holds a path (`tcw/work/jira/config.py:31-37` lists every Jira key; `work.tags` is a list of tags, `tcw/work/config.py:451-467`); the declaring project in each origin is checked by 17 |
| 1.5 an inherited `work.jira` without Jira mode | 9 |
| 1.6 what is read from an ancestor; the user-wide file checked once; a broken key stops only what reads it; an unparseable ancestor file is a gap, a descendant's stays a graph problem | 10 (broken key), 11, 12 (the user-wide file once), 15 (not valid YAML; the descendant), 17 (config show with a broken key) |
| 2.1 the fold order, personal layers per project, user-wide file applied at each source and checked once | 11, 12, 33 |
| 2.2 merging | 6, 7 |
| 2.3 the last declarer wins (TCW-108 AC 11's shape) | 4, 5 |
| 2.4 `inherit: true` in `work.tags`; chain lists unchanged; elsewhere refused | 5, 7, 22 (a chain list from a variable) |
| 2.5 `null` | 8 |
| 2.6 origins | 10 (a problem names the declaring file), 17 |
| 3.1 undecided keys | 13, 14 |
| 3.2 no default, no "required", no check that depends on an undecided value | 13 (an undecided `work.tags` is not empty: `tags list` exits 7 rather than printing nothing), 14 (no "required" for `work.jira.site`: `tcw validate` exits 0) |
| 3.3 exit 7 and the two messages | 13, 14, 15, 29 |
| 3.4 which commands read which keys; commands that do not open the store; references into a Jira-mode project; the web app | 13 (b, and filesystem commands that read none), 14 (a in Jira mode, `tcw capabilities drift`, the commands that must not open the store, and the two kinds of reference), 17 (c), 32 (the web app) |
| 3.5 TCW-108's conflict; TCW-108's criteria unchanged, the suffix in its tests | 13, 14, 15 (TCW-108's AC 31 test) |
| 3.6 `tcw validate` with an undecided key | 13, 14, 29 |
| 3.7 the check every command makes first | 13, 14 (`tcw taxonomy list` exits 0) |
| 4.1 the name | 19 |
| 4.2 which variables are overrides; malformed names | 19, 20 |
| 4.3 decoding against the key table; one name per key | 20, 26 |
| 4.4 the project part; checked everywhere; problems in the active project's configuration only | 11 (a variable naming an ancestor), 21 (`elsewhere`), 28 (no false `error` for a `tcw://` link into another project) |
| 4.5 only allowed keys | 21 |
| 4.6 values by type; a mapping merges, a list replaces; no value in a message | 22, 23 (a mapping merges); booleans and numbers n/a: no allowed key has those types (`tcw/config.py:45-52`) |
| 4.7 the more specific wins | 23 |
| 4.8 `file:` and `command:` bindings from a variable | 24 |
| 4.9 the note and a failed `post` name the variable | 24 |
| 5.1 the allowed list; no `children`, no store location by variable | 21 |
| 5.2 whose personal settings apply; a project read for itself takes its variables, no personal file, and is found through the command's registry; an ancestor's local file in a linked worktree; a gap in a project read for itself | 11, 14 (`lib`'s item read for itself, with `lib` as its project; `app` read for itself from `lib`), 33; a project covered by a scoped listing is TCW-113's (its Design 1.6 d and criteria) |
| 5.3 `TCW_NO_PERSONAL_CONFIG` | 11, 25 |
| 6.1 `tcw work tags list` | 1, 3, 4 |
| 6.2 `tcw work tags add` | 18 |
| 6.3 `tcw work tags rm` | 18 |
| 7.1 `tcw config show` | 17 |
| 7.2 `tcw validate` for a variable's problem | 28 |

## Risks

- **A Jira-mode child of a missing parent cannot open its store** (Design
  3.5). With the default `inherit: all`, a Jira-mode project whose parent is
  missing exits 7 on every command that reads or writes its items, because
  the parent may set any Jira key. This is what TCW-99 says happens
  (design.md:389-393). CI on a single repository is the common case; the
  remedies are to fetch the parent or to leave `config` out of that link. A
  filesystem project is never stopped this way (1.2).
- **A broken inherited value is found late** (1.6). A library whose
  `work.tags` is malformed no longer stops every reader; a reader learns of it
  from a `warning` in `tcw validate` or when a tag command stops with exit 1.
  The message names the library's file. A library's maintainers meet the same
  problem in their own commands first, where it fails `tcw validate`.
- **A misspelt project part does nothing** (4.4). `TCW_USER_NAME__MYPROJ` for
  project `my-proj` names no project and is silently not applied. Checking
  project parts against the family would fail a CI job that sets variables for
  several families. `tcw project config --origin` (TCW-115) shows which
  variable set each value, which is where a person looks when a value is not
  what they set.
- **`inherit: true` follows the whole order, not the declarer's parents**
  (2.4). A list `[inherit: true, d]` in a project reached alongside another
  parent picks up that parent's entries in a grandchild. It is TCW-108 Design
  4.8 applied to lists and matches how the order is defined, but a reader
  expecting "my parents' tags plus mine" in every descendant is surprised.
  AC 5 pins it.
- **The allowed list is narrow** (5.1): a CI job cannot point a project at a
  test Jira site by a variable, and the design's own example of the
  specificity rule, `TCW_WORK_JIRA_SITE__APP` (design.md:532-534), is refused
  (4.7). Widening the list is a release decision; widening it later breaks
  nobody.
- **Commands that open the store today must stop doing so** (3.4). Seven
  places in `tcw/work/cli.py` open it only to read configuration that is not
  inherited, the project ID or the work path (`:56`, `:71`, `:318`, `:441`,
  `:455`, `:567`, `:596`). Two reference checks open a Jira-mode store only
  to answer from its folders (`tcw/refs.py:139`, `tcw/work/open.py:210-241`).
  And `validate_changes` receives the registered tags on every create and
  edit. Missing one leaves a Jira-mode child stopped, or `tcw validate`
  wrong, where nothing inherited is needed. AC 14 names each command.
- **Every command reads its ancestors' configuration files.** The fold opens
  each configuration source's shared and personal files on every command, in
  addition to TCW-108's reads of their links. For a family of a handful of
  projects this is a few small files; UC-1 reads nothing new (AC 27).

## Notes

### Decisions the design left to this spec, each with its reason

1. **The allowed list for variables is the personal-file list**, unchanged
   from 3.x (Design 5.1). The request says personal files and variables "keep
   an allowed list (as `PERSONAL_KEYS` does)". The keys it excludes protect
   team rules (gates, stage statuses, the backend, tags), and an environment
   variable is as much one person's as a file. A list grows in a release;
   narrowing it later would break people.
2. **No variable sets `children`** (Design 5.1): the family would differ by
   environment. TCW-108's handoff suggested the same.
3. **No variable sets a store location, and the design's
   `TCW_WORK_PATH__MY_PROJ` is not built** (Design 5.1): recorded by TCW-110,
   followed here.
4. **`TCW_PROJECT_<ID>` stays** (Non-goals; TCW-107 Design 2.1): a location is
   not configuration, and no variable gives a manifest path.
5. **A missing parent stops a command only when it reads an undecided key**
   (Design 3), rather than whenever any configuration source is missing, so
   that a filesystem project keeps working without its parents (TCW-108's
   conflict, Design 3.5).
6. **An undecided key is defined by whether a later project replaces it
   whole** (Design 3.1), so the rule needs no knowledge of what the missing
   project holds.
7. **Every override variable is checked in every command** (Design 4.4),
   because the key table is the same for every project in 4.0; one naming a
   project not folded is otherwise ignored.
8. **No collision check for user-chosen keys** (Design 4.3): 4.0 has none.
9. **`null` removes only at an inherited key** (Design 2.5); elsewhere it
   keeps its 3.x meaning, so `work:` with nothing under it does not cut a
   child off from its parents.
10. **An inherited `work.jira` is ignored outside Jira mode** (Design 1.5).
11. **Ancestors' personal files contribute what the ancestor passes**
    (Design 5.2), as the design's assembly order says. A project read for
    itself takes the variables naming it but no personal file (decided after
    the review, below).
12. **A `file:` binding from a variable resolves from the named project's
    root** (Design 4.8).
13. **`inherit: true` is accepted in `work.tags`**, the one inherited list
    (Design 2.4), which is the design's own example.
14. **`tcw work tags` writes only the project's own list** (Design 6), so a
    child keeps following its parents.
15. **`tcw config show` exits 7 with an undecided key** (Design 7.1), since
    printing a partial configuration would show values commands do not run
    with.
16. **The messages** of Design 3.3, 4.2-4.6 and 6.3, and the validate suffix
    of 3.6.

### Decided after the spec review (2026-10-22)

17. **`work.backend` is not inherited** (decided by the user, 2026-10-22;
    Design 1.2). Each project states its own; the default is `filesystem`.
    A filesystem child therefore always works on a single clone, and a
    backend is never undecided. The other Jira settings stay inherited, as
    the design says (design.md:485-488), and a Jira-mode child of a missing
    parent stops, as design.md:389-393 says. This departs from the design's
    list (design.md:484-485). It removes the earlier draft's question to the
    user about "commands that need only the project's own records still
    work", the checks that depended on an undecided backend, and the change
    the earlier draft made to the fixture of TCW-108's AC 31 (Design 3.5).
18. **A variable holding a mapping merges key by key**, as a personal file's
    mapping does; a list still replaces whole (Design 4.6). This departs from
    design.md:543-545, because a mapping replaced whole would delete keys the
    allowed list protects.
19. **Commands that need nothing inherited do not open the work store**
    (Design 3.4): `tcw work lifecycle`, `tcw work docs`, `tcw work stage
    prompt` and `tcw work procedure` with no item, `tcw work path` with no
    item, the note of 4.9, the write check, reading another project's item,
    and checking a reference or a `tcw://` work link into a Jira-mode
    project. Each keeps the checks `open_backend` makes before it builds a
    backend, so it fails as it does today when it fails (added after the
    plan review).
20. **A project read for itself takes the variables naming it, and no
    personal file** (Design 5.2). Variables follow design.md:276-281;
    leaving out personal files departs from that sentence's "local
    overrides", to keep `docs/use-cases.md` S-5's "another project's personal
    file is never read".
21. **A problem in an inherited value stops only a command that reads it**
    (Design 1.6), following the user's decision for another project's links
    (TCW-108 Design 6.6).
22. **An ancestor whose shared file cannot be read is a gap**, placed as
    TCW-108 Design 6.6 places a project whose parents cannot be read (Design
    1.6). TCW-108 Design 6.6 does not name this case; this spec does, and its
    plan builds it if TCW-108 as landed does not. It applies to an ancestor
    and to a project read only for a lookup. A descendant whose file cannot
    be read stays a graph problem, for the reason TCW-108 Design 6.6 gives
    for a descendant's `children:` problems (decided by the dispatching
    session after the plan review, following the settled TCW-108 spec).
23. **`tcw work tags add` writes `inherit: true` whenever the project has a
    configuration source other than itself** and no own list (Design 6.2),
    so a child is not cut off from tags its parents add later.
24. **This item's plan owns any change to an earlier item's tests** that this
    item's rules force (Design 3.5). No TCW-108 criterion changes. TCW-108's
    tests of AC 19, 20 and 31 (and of AC 19's "what lies above is unknown"
    sentences) gain 3.6's suffix, and any of them that compares the whole
    text is amended here.

### Decided after the plan review (2026-10-22)

25. **When the registry cannot give the order, the project is folded
    alone** and the inherited keys it does not decide are held back with the
    error `tcw work list` gives in the same project (Design 1.3; how the
    case is seen and which message it carries, Decision 30). Loading the configuration has never
    raised, and every command, `tcw validate` included, loads it before it
    runs, so a raise there would turn `tcw validate`'s list of findings into
    one line in exactly the case where it is most needed.
26. **The user-wide file is checked once, as the active project's own**
    (Design 1.6, 2.1). It belongs to the person running the command, not to
    an ancestor, so its problems are reported once and never make a key
    "broken". A value refused in an ancestor's personal layer is never
    merged and breaks nothing.
27. **Variable problems belong to the active project's configuration only**
    (Design 4.4), so a project read for itself can still be opened when a
    variable is misspelt, and `tcw validate` gives no false `error` for a
    `tcw://` link into it, nor the web app a failed read of it. (Corrected
    after the plan re-check: the first wording said item references would be
    reported "broken", but `tcw validate` never reaches the reference check
    while the active project's configuration has a problem.)
28. **A project read for itself is folded through the command's registry**
    (Design 5.2), not a registry opened with that project as the active one.
29. **`tcw capabilities drift` in a Jira-mode project reads `work.jira`**
    (Design 3.4, row a): it lists the completed items through the backend,
    as its docstring already says (`tcw/capabilities/cli.py:183-189`).

### Decided after the plan re-check (2026-10-22)

30. **The loader itself sees that the active project's own `parents:` is
    wrong or that its ancestors loop** (Design 1.3), and the inherited keys
    it does not decide carry the error `tcw work list` gives (decided by the
    dispatching session, 2026-10-22: TCW-108 keeps the active project's own
    `parents:` problem a graph problem and still says its links can be
    read, so waiting for the registry to raise misses it; and the message
    must be TCW-108's, not the text of a guard inside the order's
    computation).
31. **A project read for itself carries its own ID** (Design 5.2), never the
    ID of the registry's current project, which is the active one; the
    command's registry is used only to find the project's configuration
    sources (decided by the dispatching session, 2026-10-22: reading the ID
    from the passed registry would give every backend opened for another
    project the active project's ID).
32. **A gap in a project covered by a scoped listing makes it unavailable,
    exit 0** (Design 5.2), and still stops, with exit 7, a command that reads
    that project's object by full identifier or runs in it (TCW-113's
    handoff, 2026-10-22, following the user's TCW-108 Design 6.6 decision).

### Settled questions

1. **"Commands that need only the project's own records still work"**
   (design.md:386-388): settled by Decision 17. A filesystem project's own
   records never need an inherited setting; a Jira-mode project's do when its
   Jira settings come from a parent, and then the design's next sentence
   governs (design.md:389-393).
2. **Variables reach the same keys as personal files** (settled by the design,
   as the dispatching session confirmed on 2026-10-22): "Personal files and
   variables keep an allowed list" (design.md:535-540), one list for both
   (Design 5.1).
3. **A stage's Jira `status` stays per project** (settled by the design, as the
   dispatching session confirmed on 2026-10-22): "stages and their bindings"
   are the project's own (design.md:488-490). A child in a shared Jira project
   maps its stages to statuses itself (`tcw/work/config.py:408-419`).

### Handoffs from earlier items, answered

- **TCW-106** (the naming rule, so every key has one variable name): relied on
  in Design 4.3; AC 26 checks it over the whole table.
- **TCW-107** (`TCW_PROJECT_<ID>` stays; no manifest-path variable): Design
  5.1 and Non-goals.
- **TCW-108**: Design 4.8 is applied over the configuration sources, folding
  each project's own declarations (Design 2.3), with AC 11's shape as AC 5.
  `parents` is not on the allowed list, and `children` stays in the local file
  only (Design 5.1). No variable sets `parents` or `children` (Design 5.1).
  The conflict over `work.backend` and `work.tags` is answered by Design 1.2
  (the backend is not inherited), 3.4 and 3.5. No TCW-108 criterion or plan
  step changes. Some of its `tcw validate` tests gain 3.6's suffix (Design
  3.5, Decision 24). Design 1.6 adds to TCW-108 Design 6.6 the case of an
  ancestor whose shared file cannot be read at all, and keeps a descendant's
  as a graph problem.
- **TCW-110** (store locations cannot be overridden; do not build
  `TCW_WORK_PATH__MY_PROJ`): Design 5.1, AC 21. TCW-110's refusal of absolute
  and `~` store paths in the shared file is unaffected: no personal layer can
  give a store path at all.

### Handoffs to later items

These are recorded on each ticket when this spec is accepted.

- **TCW-99:** the departures from the design that this spec makes, for the
  design's record: `work.backend` is not inherited (Decision 17, the user's);
  a variable's mapping merges (18); a project read for itself takes no
  personal file (20); the allowed list refuses the design's
  `TCW_WORK_JIRA_SITE__APP` and `TCW_WORK_PATH__MY_PROJ` examples (4.7, 5.1);
  no collision check is built (4.3).
- **TCW-112:** `taxonomy.extends` and `capabilities.extends` are not inherited
  configuration and are not on the allowed list; nothing here depends on them.
  When TCW-112 removes them, it removes them from the table of keys TCW knows
  (Design 4.3) too, so a variable naming one then names no key. The table is
  used only to decode variables and, for `work.tags` and `work.jira`, to
  decide which keys are undecided (Design 3.1); the loader never reports a
  key of a file because the table lacks it, and from another project's file
  it reads only the keys of Design 1.1 (1.6), so an `extends` there is never
  read and never makes that project unreadable. An ancestor whose shared
  file cannot be read is a gap for every axis (Design 1.6); a descendant's
  stays a graph problem.
- **TCW-113:** a project read for `--scope up` or `--scope down` is read for
  itself (Design 5.2): it takes the variables naming it and no personal file,
  it is folded through the command's own registry, it reports no variable
  problem (4.4), and a gap in its own configuration sources makes it
  unavailable in a scoped listing (exit 0, TCW-109's message as the reason),
  and still stops with exit 7 a command that reads its object by full
  identifier or runs in it.
- **TCW-115:** `tcw project config` replaces `tcw config show` with Design
  7.1's behavior (exit 7 with an undecided key, exit 1 with a broken one) and
  shows, with `--origin`, each value's project and file or variable from the
  origins of Design 2.6. `tcw project info`'s "important configuration
  values" should include `work.backend` and `work.jira.project`, marking
  `work.jira.project` inherited when it is.
- **TCW-116:** report a 3.x configuration whose credential variable names
  (`work.jira.credentials.*`, a `projects:` entry's `jira` block) start with
  `TCW_` and hold `__`, since 4.0 reads such a variable as an override
  (Design 4.2); report a `null` at a key of Design 1.1 in a 3.x file, which
  now removes an inherited value.
- **TCW-117:** document Design 1.1's list where the configuration keys are
  documented (`skills/configure/references/`, `docs/guide/configuration.md`),
  that `work.backend` is never inherited, the override name rule with
  examples, that a variable's mapping merges, the allowed list, what exit 7
  means for configuration and its two remedies (Design 3.5), and
  `tcw work tags` in a child. In `docs/use-cases.md`: S-5's "another
  project's personal file is never read" becomes "never read for a project
  read for itself; an ancestor's personal credential names reach its
  children"; UC-5 gains the inherited `work.jira` and the child's own
  `work.backend: jira`; UC-6 gains exit 7 for an undecided setting. TCW-108
  Design 6.1's "listing, reading and moving its own items ... still work"
  holds for a filesystem project and not for a Jira-mode project whose Jira
  settings come from a missing parent; the guides say which.
- **TCW-118:** nothing beyond the release notes, which TCW-117's guides feed.
