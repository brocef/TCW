# Spec — From a copy of worktrees kept inside its own main checkout, the search for a project climbs past the copy into the main checkout

## Capability changes

- **Changed:** `tcw.capabilities/cli/run-from-a-git-worktree`. Its
  description gains one sentence saying which folders the search, looking
  from where a project is, does not climb into: the main checkout of a
  linked worktree that is kept inside that main checkout and encloses the
  project, and the folders between the two that belong to the main
  checkout's repository, for a project kept anywhere inside such a
  worktree. No record is written at this stage.
- No new or removed capability, and no taxonomy change.

## Reproduction

Built with this repository's 4.0.0 code (`tcw 4.0.0`, importing from this
checkout) in a scratch folder, using real `git init` and `git worktree add`;
paths below are shortened to `BASE`. The layout is the request's:

```
BASE/MAIN/                         repository X, main checkout; project r
├── .gitignore                     /p/ and /.claude/
├── .tcw/tcw-manifest.yaml         p: { path: p }
├── p/                             repository Y, main checkout; project p (names nothing)
└── .claude/worktrees/w/           X's linked worktree (branch wt); project r
    └── p/                         Y's linked worktree (branch wt); project p
```

`tcw -C BASE/MAIN/.claude/worktrees/w/p project path r`:

1. **MAIN migrated** (both checkouts of X on 4.0):

   ```
   tcw project path: BASE/MAIN/.claude/worktrees/w/p/.tcw/tcw-config.yaml: project 'r' is
   declared by more than one folder near this one: BASE/MAIN/.claude/worktrees/w and
   BASE/MAIN; add an entry for 'r' to .tcw/tcw-manifest.local.yaml (this machine) or
   .tcw/tcw-manifest.yaml (everyone)
   exit 1
   ```

2. **MAIN left as 3.x** (a root `tcw-config.yaml` and no `.tcw/` on branch
   `main`; branch `wt`, checked out at `w`, migrated by hand and committed):

   ```
   tcw project path: BASE/MAIN: is a TCW 3.x project (tcw-config.yaml at its root, no
   .tcw/ folder); run 'tcw migrate' in it to move it to TCW 4
   exit 1
   ```

3. **The same copy kept outside MAIN** (`BASE/elsewhere/w`, with Y's
   worktree at `BASE/elsewhere/w/p`): prints `BASE/elsewhere/w`, exit 0.

Expected in cases 1 and 2: `BASE/MAIN/.claude/worktrees/w`, exit 0, as in
case 3.

Two further layouts, found while checking how wide the defect is, fail the
same way today:

4. **Not a copy.** Y's main checkout beside MAIN (`BASE/Ymain`), and Y's
   linked worktree kept in X's linked worktree's `.worktrees/` folder
   (`BASE/MAIN/.claude/worktrees/w/.worktrees/p`). `project path r` from
   there: the same "declared by more than one folder ... w and BASE/MAIN"
   refusal, exit 1. The worktree is not a copy (Y's main checkout is not
   inside X's), so 4.0 searches it in two rounds, and the first round's
   climb reaches MAIN the same way.
5. **Three repositories deep.** Z's main checkout `ZM` holds X's at `ZM/x`,
   which holds Y's at `ZM/x/y`; Z's linked worktree is
   `ZM/.claude/worktrees/w`, X's is `w/x`, Y's is `w/x/y`. `project path z`
   from `w/x/y`: "project 'z' is declared by more than one folder near this
   one: ZM/.claude/worktrees/w and ZM", exit 1.
6. **A copy that lacks the project reads the original's.** The reported
   layout with `w/.tcw/tcw-config.yaml` deleted from the working folder:
   `project path r` prints `BASE/MAIN`, exit 0. It reads the main checkout
   the copy was made from, which the guide says a copy never does.
7. **A clone in between.** Z's main checkout `ZM`, Z's linked worktree
   `ZM/.claude/worktrees/zw`, a plain clone of X (a main checkout) at
   `zw/x`, and Y's linked worktree at `zw/x/.worktrees/y` (Y's main
   checkout elsewhere). `project path z` from there: "project 'z' is
   declared by more than one folder near this one: ZM/.claude/worktrees/zw
   and ZM", exit 1.

A spec review found two more layouts that fail the same way, by a route the
first draft of this spec had declared out of scope:

8. **A related project's search, made from inside the copy.** X is a
   monorepo: root project `r` at `MAIN`, child project `s` at `MAIN/s`
   naming `r` as its parent. Y's project `p` names `s` as its parent, with
   the manifest entry `s: ../s`. The copy is `MAIN/.claude/worktrees/w`
   with Y's linked worktree at `w/p`. From `w/p`, `project list` and
   `project path r` both fail: "project 'r' is declared by more than one
   folder near this one: MAIN/.claude/worktrees/w and MAIN", exit 1. The
   search for `r` is made from `s`'s folder `w/s`, which is outside the
   active project's worktree `w/p`, so `search_rounds` gives it the plain
   climb (`tcw/store/project.py:382-383`), and that climb reaches `MAIN`.
9. **A plain clone as the active project.** A workspace repository `WS`
   (project `ws`), its linked worktree `WS/.claude/worktrees/w`, and a
   separate repository made with `git init` at `w/x` (project `x`). From
   `w/x`, `project path ws`: "project 'ws' is declared by more than one
   folder near this one: WS/.claude/worktrees/w and WS", exit 1. The active
   project is a main checkout, so it has no worktree information
   (`anchors` is None) and takes the same plain climb.

And one layout that works today and must keep working:

10. **A separate repository between the copy and its main checkout.**
    `MAIN` (project `r`) holds a separate repository at `MAIN/tools`
    (project `tools`), ignored by `MAIN`, and X's linked worktree is kept
    inside that repository, at `MAIN/tools/wt/w`, with Y's at `w/p`. From
    `w/p`, `project path tools` prints `MAIN/tools`, exit 0. `MAIN/tools`
    lies between the linked worktree and its main checkout, but it is not
    part of X: it is a project in its own right, found the way it would be
    found from any folder inside it. (`project path r` from there fails
    today with "declared by more than one folder: MAIN/tools/wt/w and MAIN",
    as case 1 does.)

For contrast, Y's linked worktree kept directly in X's *main* checkout
(`BASE/MAIN/.worktrees/p`, no linked worktree of X involved) prints
`BASE/MAIN`, exit 0, today. That is right and must stay so.

**`tcw migrate`'s prediction is wrong in the same layout.** With p still on
3.x in both of Y's checkouts, naming `r` as a parent at `..`:

- `tcw -C BASE/MAIN/p migrate --dry-run` (Y's main checkout) writes no
  manifest: its prediction of the search finds `r` at `MAIN`, the folder the
  3.x entry names, so the entry is left out (rule M6).
- `tcw -C BASE/MAIN/.claude/worktrees/w/p migrate` (the copy) writes
  `.tcw/tcw-manifest.yaml` with `r: { path: .. }`: its prediction finds `r`
  at both `w` and `MAIN`, two folders, so it keeps an entry. The answer is
  right, but the two branches of Y now differ by a file the person never
  asked for.

The scripts are kept outside the repository; the plan turns each layout into
a test.

## Problem

The search for a project that no manifest entry places tests the folders next
to the asking project and then every folder enclosing it, and **keeps every
match of a round**, refusing when there is more than one
(`_search`, `tcw/store/project.py:615-648`, in particular `:631-646`; the
refusal is built at `:2106-2116`).

Which folders a round tests is decided by `search_rounds`
(`tcw/store/project.py:354-394`):

- The active project `p` is in Y's linked worktree, so `anchors` is
  `(w/p, MAIN/p)` (`_probe_worktree`, `:214-238`; held as `self._anchors`,
  `:742`).
- `w/p`'s parent folder `w` lies in a checkout of another repository (X), so
  `read_as_written(top.parent, anchors)` is true (`:389`, `:253-268`).
- The folder holding the worktree, `w`, is itself a linked worktree whose
  main checkout `MAIN` holds Y's main checkout `MAIN/p`, so the worktree is
  part of a copy and only the first round is used (`:391-393`).
- That round is `as_written = (named_by.parent, named_by,
  list(named_by.parents))` (`:381`): **every** real folder above `w/p`. Those
  are `w`, `MAIN/.claude/worktrees`, `MAIN/.claude`, `MAIN`, and the folders
  above MAIN. `w` declares `r`, and so does `MAIN`, the same project on X's
  other branch.

Nothing in the round tells the two apart:

- `_answer` folds two matches into one only when `_worktree_copy` maps one
  onto the other (`:2106-2109`), and `_worktree_copy` (`:1400-1430`) maps
  paths under the **active** project's main checkout (`MAIN/p`) only. `MAIN`
  is not under it, so `w` and `MAIN` stay two folders: case 1.
- When MAIN is 3.x, its probe is a "legacy" problem (`:646`). A problem in
  the round wins over the match (`:2103-2105`), so the 3.x refusal names
  `MAIN`: case 2.

The copy kept outside MAIN (case 3) works only because `MAIN` is not among
its folders' parents.

The defect is not limited to copies (case 4). When the folder holding the
worktree lies in another repository's checkout but the worktree is no copy,
`search_rounds` returns `[as_written, from_main]` (`:394`), and the first
round's climb is the same unfiltered `list(named_by.parents)`.

Nor is it limited to the nearest checkout holding the worktree (case 5):
`:391` asks only about `top.parent`'s checkout (`w/x`, whose main checkout
`ZM/x` is not above `w/x/y`), while the folder that is climbed into, `ZM`, is
the main checkout of the linked worktree one level further out. And the
checkout in between need not be a linked worktree (case 7). When a plain
clone is kept in a linked worktree, `worktree_anchors(top.parent)` (`:391`)
answers None, because the clone is a main checkout. The linked worktree
around the clone is then never seen.

Nor is it limited to the active project's own search (case 8), or to an
active project in a linked worktree (case 9). `search_rounds` returns the
plain climb, `list(named_by.parents)` unfiltered, before it looks at any
worktree, when the search is made from a folder outside the active
project's linked worktree, or when the active project is in no linked
worktree at all (`:382-383`: `if anchors is None or _below(named_by,
anchors[0]) is None: return [as_written]`). A related project inside the
copy, and a plain clone kept in the copy, both take that return.

The folder the climb should not reach is always the same kind: **the main
checkout of a linked worktree that encloses the asking project, together
with the folders between that linked worktree and its main checkout that
belong to the main checkout's own repository, reached only because the
linked worktree is stored inside its own main checkout.** A folder between
the two that belongs to a separate repository (case 10) is not of that kind:
it is reached because the worktree is stored inside *it*, and it is searched
as it is from anywhere else inside it. For the active project's own worktree, 4.0 already avoids
exactly this. Its round from the main checkout tests the worktree's own
folders up to its top, then the folders *above* the main checkout, and "the
main checkout's own root is not tested again" (`:384-388`, and the docstring
at `:363-368`). The linked worktrees further out get no such treatment.

**The guide already promises the right answer.** `docs/guide/multi-repo.md`
lines 625-630 say that for a copy made of worktrees one inside another "the
search looks only from the worktree: a project the copy does not have is not
found, rather than read, and perhaps changed, in the folders the copy was
made from". It also says (lines 617-620) that a 3.x copy on the worktree's
side is the one reported, never the main checkout's. Cases 1 and 2 break
both sentences.

**`tcw migrate` predicts the search with the same function.** `search_4`
(`tcw/migrate/family.py:214-238`) iterates `search_rounds(folder, anchors)`
(`:230`) and keeps every match of the first round that has one (`:236-238`).
A run leaves out a manifest entry only when that prediction finds exactly the
entry's folder (`tcw/migrate/config.py:583-590`, `:1338-1339`). Two matches
there make the run write an entry the main checkout's run does not.

**Sweep.** I looked for every other upward climb in `tcw/` (`.parents`) that
might keep more than one match. `enclosing_project`
(`tcw/migrate/config.py:1261-1269`) and `_below` (`tcw/store/project.py:136`)
stop at the first folder. The rest compare paths or make folders. The only
climb that collects every match is the search's, built in one place,
`search_rounds`, and used by both `_search` (through `_search_candidates`,
`tcw/store/project.py:2364-2368`) and `search_4`. Manifest entries and store
paths are read through `read_as_written` and `_worktree_copy`, not by a
climb, and the request reports them unaffected; the evaluator's 32 passing
lookups agree.

## Goals

1. From any folder inside a linked worktree that is stored inside its own
   main checkout, the search's climb does not test that main checkout, or a
   folder between the linked worktree and it that belongs to the main
   checkout's repository. This holds for every such linked worktree
   enclosing the folder the search is made from, however far out and
   whatever checkouts lie between, not only the nearest; and it holds
   whichever folder the search is made from: the active project's, a
   related project's (case 8), or an active project that is a plain clone
   (case 9).
2. The climb then goes on above that main checkout, as it would from the
   copy kept anywhere else, and a folder in a separate repository between
   the linked worktree and its main checkout is still tested (case 10).
3. `tcw migrate`'s prediction (`search_4`) gives the same answer, so
   migrating Y's linked worktree in the copy writes the same manifest as
   migrating its main checkout.
4. Every layout that works today gives the same answer after the change,
   and a layout with no linked worktree around the folder searched from
   pays nothing for it: no extra `git` process.

## Non-goals

- **Changing which worktree counts.** The search made from a related
  project's folder outside the active project's worktree keeps its rule
  (`docs/guide/multi-repo.md:631-634`, "which worktree counts is the one the
  command runs from"): it is still searched from where that folder is, in one
  round, never re-pointed at a main checkout. The change only takes folders
  out of that climb; it adds none and moves none.
- **The folders next to the asking project.** They are the asking project's
  parent folder's other folders. The change removes only folders that
  strictly enclose a linked worktree, which the asking project's parent
  folder never is when the project is inside that worktree.
- **Recognising more layouts as a copy.** The definition at `:391-393` is
  unchanged. Cases 4 and 7 are fixed by the same rule without becoming a
  copy, and keep their second round, from Y's main checkout. That second
  round climbs from Y's main checkout, so this change says nothing about
  it.
- **Manifest entries and store paths.** They do not climb.
- **Workarounds already in place.** An entry for `r` in p's
  `.tcw/tcw-manifest.local.yaml` keeps working, and still decides first.
- **Changing the refusal text** for two matches that really are two
  projects, or the remedy offered when a copy lacks a project (see Notes).

## Design

One change, in `search_rounds` (`tcw/store/project.py:354-394`): the
enclosing folders of the round read as written are filtered by one rule,
wherever that round is returned. That is the early return for a search made
outside the active project's linked worktree, or with none (`:382-383`, cases
8 and 9); the copy's only round (`:393`); and the first of the two rounds
otherwise (`:394`). The round from the main checkout (`from_main`) is not
changed.

**The rule.** Walk the git checkouts that enclose the folder the search is
made from, nearest first:

1. Start at the folder the search is made from, `named_by`, in the early
   return, and at the folder holding the active worktree, `top.parent`, in
   the other two. Ask git for that folder's checkout: its top folder `T`,
   and, when it is a linked worktree, its main checkout `M` (`M == T` for a
   main checkout). Then ask again from `T.parent`, and stop at a folder in
   no checkout. A main checkout does not stop the walk: case 7 and case 9
   have one between the asking project and the linked worktree whose main
   checkout is climbed into. Each `T` is strictly above the last, so the
   walk ends.
2. For each `(T, M)` with `T` a linked worktree inside `M` (`_below(T, M)` is
   not None), leave out of the climb every folder `F` that encloses `T`
   without being `T`, is `M` or inside it, **and is in `M`'s own
   repository**: its git common folder is `M`'s (`_repository_of`, the
   function `read_as_written` already uses). `M` itself always qualifies.
   `MAIN/.claude` and `MAIN/.claude/worktrees` qualify: git places a folder
   in the checkout it lies in whether or not that checkout ignores it.
   `MAIN/tools` in case 10 does not: it is a checkout of its own.
3. The folders above `M` stay in the climb, in order.

"Inside" is decided by folder identity, with `_below`, as every other such
test in this module is, so a disk that ignores letter case behaves the same.

**Cost: the walk is computed only when it can matter.**

- In the round's two later returns, it is computed after the
  `read_as_written(top.parent, anchors)` check (`:389`), so a plain worktree
  of a single project or a monorepo (UC-1, UC-3), for which that check is
  false, returns `[from_main]` without it, exactly as today.
- In the early return, it is computed only when some folder from `named_by`
  up, `named_by` included, has a `.git` that is a **file**: the mark git
  leaves in a linked worktree's top folder (and a submodule's). That test
  reads the disk and starts no git process. A project in no linked worktree,
  such as a single project in an ordinary checkout, a library caller, or
  `tcw serve` run from one, finds no such file and gets today's plain climb
  at the cost of one file test per enclosing folder.
- When the walk runs, each checkout it passes costs one `git rev-parse`
  (`--show-toplevel --git-common-dir`, which gives both `T` and `M`), plus
  one ending call that finds no checkout, and each folder strictly between a
  linked worktree and its main checkout costs one more (`_repository_of`)
  to tell whether it is in `M`'s repository. All of them are cached per
  folder for the life of the process, as `worktree_anchors` (`:85-97`) and
  `_repository_of` (`:418-432`) cache theirs. In case 1 that is four calls:
  `w`, the folder holding `MAIN`, `MAIN/.claude/worktrees` and
  `MAIN/.claude`.

`search_4` needs no change of its own: it reads the same rounds (Goal 3). The
plan adds tests that it does.

**Callers with no active worktree.** `tcw serve` and library callers reach
the search through the same registry and `search_rounds`, with `anchors`
from the active project as today. Where the folder searched from lies in no
linked worktree, nothing changes for them. Where it does, they get the same
answer as the command line, which is the point of the change. The whole
suite is run to check that no existing caller's answer moves.

Nothing else moves: `_search`, `_answer`, `_worktree_copy`,
`read_as_written` and the definition of a copy are unchanged. When no linked
worktree around the folder searched from is stored inside its own main
checkout, nothing is left out, and every round is what it is today.

## Abstraction litmus test

No new operation, and none changed. `search_rounds` is part of the
filesystem layer that resolves projects (deployment layer, `tcw/store/
project.py`). The git reads it adds (`git rev-parse`) are the kind
`abstraction.md` places "in the code that resolves projects, not in the
model". A store that is not a folder of files has no folders to climb and no
search, so the question of whether a non-filesystem store could implement it
does not arise. Nothing a backend owns is touched.

## Use cases

- **S-4 Copies of a checkout.** The case this fixes: a copy made of linked
  worktrees one inside another, kept inside the main checkout it was made
  from. That is what Claude Code's worktree tool does by default, at
  `.claude/worktrees/<name>`. After the change, the search made from the
  copy's own folders finds the copy's projects and not the main checkout's
  copies of them on another branch, whichever project in the copy it is made
  from. A plain worktree, a worktree kept elsewhere, and a copy kept outside
  the main checkout behave as before. S-4 does not yet describe a copy kept
  inside its own main checkout, so this change adds a requirement saying so.
- **UC-4 Many repositories and a planning workspace.** The layout is UC-4's:
  a workspace repository with a child repository cloned inside it. Its
  requirement that no project is located by git's ignore rules still holds:
  the change asks git only where a checkout, its main checkout and its
  repository are, never what it ignores. A child's worktree kept in the
  workspace's main checkout's `.worktrees/` folder still finds the workspace
  there (it encloses no linked worktree), and one kept in a linked worktree
  of the workspace that lies elsewhere still searches beside its main
  checkout on the second round.
- **S-9 Upgrades.** The 3.x refusal (case 2) names the main checkout today.
  After the change, a 3.x copy on the worktree's side is still the one
  reported, and a 3.x main checkout outside the copy is not read. `tcw
  migrate` run in the copy writes what it writes in the main checkout. No
  file format or key changes.
- **UC-1 A single project, UC-3 a monorepo.** Not affected. Their worktrees
  are inside one repository, so the folder holding the worktree is a checkout
  of the same repository, `read_as_written` is false (`:389`), and the walk
  is never computed. Outside a worktree, no `.git` file is found above the
  project, and no git process starts.
- **UC-2, UC-5 to UC-8, S-1 to S-3, S-5 to S-8, S-10, S-11.** Not affected:
  nothing about stores, backends, Jira, harnesses, people, personal files or
  version control changes, only which folders one search climbs.

Checklist: (1) it locates projects, by the search only; UC-4 and the nested
layouts above are tested with real repositories. (2) It touches no object.
(3) It reads no further across projects than today, and less in the cases
fixed. (4) No backend. (5)-(7) Not applicable: no person, harness or
half-finished state is involved. (8) No cost to a single project: no git
process outside a linked worktree, and none inside a plain one. (9) No file
or key changes. (10) Every test uses real git repositories and linked
worktrees.

## Acceptance criteria

Each layout is built with real `git init` and `git worktree add`, in a
temporary folder, as the reproduction does. "Prints X" means standard output
is exactly X followed by a newline.

1. **The reported layout, MAIN on 4.0.**
   `tcw -C MAIN/.claude/worktrees/w/p project path r` prints
   `MAIN/.claude/worktrees/w` (resolved), exits 0, and writes nothing to
   standard error.
2. **The reported layout, MAIN on 3.x** (branch `main` of X holds a root
   `tcw-config.yaml` and no `.tcw/`; the branch checked out at `w` is on 4.0).
   The same command prints `MAIN/.claude/worktrees/w` and exits 0, and its
   standard error does not contain `tcw migrate`.
3. **The copy kept outside MAIN** (`elsewhere/w`, `elsewhere/w/p`) still
   prints `elsewhere/w` and exits 0.
4. **Not a copy** (case 4: Y's main checkout beside MAIN, Y's worktree at
   `MAIN/.claude/worktrees/w/.worktrees/p`): `project path r` prints
   `MAIN/.claude/worktrees/w` and exits 0.
5. **Three deep** (case 5): `tcw -C ZM/.claude/worktrees/w/x/y project path
   z` prints `ZM/.claude/worktrees/w` and exits 0.
5a. **A clone in between** (case 7): `tcw -C
   ZM/.claude/worktrees/zw/x/.worktrees/y project path z` prints
   `ZM/.claude/worktrees/zw` and exits 0.
5b. **A related project's search inside the copy** (case 8): from
   `MAIN/.claude/worktrees/w/p`, `project path r` prints
   `MAIN/.claude/worktrees/w` and exits 0, and `project list` exits 0.
5c. **A plain clone as the active project** (case 9): `tcw -C
   WS/.claude/worktrees/w/x project path ws` prints `WS/.claude/worktrees/w`
   and exits 0.
5d. **A separate repository between the copy and its main checkout** (case
   10): from `MAIN/tools/wt/w/p`, `project path tools` prints `MAIN/tools`
   and `project path r` prints `MAIN/tools/wt/w`, each exiting 0.
5e. **A project above the main checkout is still found.** In the reported
   layout, with a project `o` at the folder holding `MAIN`, declared nowhere
   else: from `MAIN/.claude/worktrees/w/p`, `project path o` prints that
   folder and exits 0.
6. **A copy lacking the project does not find the original's.** The
   reported layout with `r`'s configuration removed from `w` (deleted from
   the working folder only): `project path r` exits non-zero, prints nothing
   to standard output, the path of `MAIN` appears in neither standard output
   nor standard error, and the error is the "not found" one ("no project
   with ID 'r' is known or found").
7. **`tcw migrate`'s prediction agrees.** In the reported layout,
   `tcw.migrate.family.search_4(MAIN/.claude/worktrees/w/p, "r")` returns
   exactly `[MAIN/.claude/worktrees/w]`, and
   `search_4(MAIN/p, "r")` returns exactly `[MAIN]`. With p on 3.x in both
   checkouts of Y, naming `r` as a parent at `..`, `tcw migrate --no-jira`
   run in `MAIN/.claude/worktrees/w/p` writes no `.tcw/tcw-manifest.yaml`
   entry for `r`, as the same run in `MAIN/p` writes none.
8. **Unchanged layouts still pass**, in particular these existing tests:
   `test_ac18_outside_the_repository_from_the_main_checkout`,
   `test_ac26_a_worktree_inside_the_main_checkout`,
   `test_a_worktree_in_a_workspace_repositorys_worktrees_folder_finds_a_sibling`,
   `test_a_worktree_in_a_home_folder_kept_in_git_finds_a_sibling`,
   `test_a_plain_worktree_elsewhere_finds_a_sibling_beside_the_main`,
   `test_nested_worktrees_search_the_copy_for_an_enclosing_project` and
   `test_nested_worktrees_lacking_a_sibling_do_not_find_the_real_one` in
   `tests/test_manifest_worktree.py`, and every test in
   `tests/migrate/test_migrate_search_worktrees.py`.
9. **A worktree kept in a main checkout's `.worktrees/` folder still finds
   that checkout's project.** With Y's linked worktree at
   `MAIN/.worktrees/p` (inside X's *main* checkout, no linked worktree of X
   involved), `project path r` prints `MAIN` and exits 0.
10. The whole suite passes as CI runs it (bare `pytest`), which also checks
    that `tcw serve` and library callers' answers do not move.
11. `docs/guide/multi-repo.md` ("Git worktrees"), the capability's
    `description.md`, and `docs/use-cases.md` S-4 each state the rule as the
    code keeps it, in plain words: looking from where a worktree is, the
    search does not climb into the main checkout of a linked worktree kept
    inside that main checkout, nor into the folders between them that
    belong to the main checkout's repository, for a project kept anywhere
    inside such a worktree; it goes on above that main checkout. None of
    them claims more than that (no "never" covering the second round from
    the main checkout). A `docs/changelogs/upcoming/` and a
    `docs/release-notes/upcoming/` file, each named by this item's folder
    name, describe the fix.

Criteria 1, 2, 4, 5, 5a, 5b, 5c, 6 and the `tcw migrate` half of 7 were run
on the tree today, as reproduction cases 1, 2, 4, 5, 7, 8, 9 and 6 above, and
fail. Criteria 3, 9 and the `tools` half of 5d were run and pass. The
`search_4` half of 7 was run in case 1's layout and returns
`[MAIN/.claude/worktrees/w, MAIN]` today.

## Risks

- **Leaving out a folder someone relied on.** A project declared in the main
  checkout (or a folder of its repository between the linked worktree and
  it) that the copy does not have was found today, wrongly by the guide's
  own rule. After the change it is "not on this machine" from the copy, with
  the usual remedy (a manifest entry). This is the documented behaviour for
  copies, and case 4's second round still reads beside Y's main checkout.
- **A separate repository kept between the two.** Handled by the
  same-repository test in step 2 of the rule, and tested (AC 5d).
- **Cost.** Stated under Design. Only a search made from inside a linked
  worktree whose folder lies in another repository's checkout, or from a
  folder with a linked worktree above it, starts any new git process.
- **A main checkout above the copy that is reached by another route.** The
  folders above `M` are kept, so a project enclosing the main checkout, such
  as a workspace two levels up, is still found from the copy, as it would be
  from a copy kept elsewhere under the same folder (AC 5e).
- **Submodules.** A submodule's top folder also has a `.git` file, so it
  triggers the walk in the early return. The walk treats the submodule as a
  checkout of its own and goes on outward to its superproject's checkout,
  so a superproject's linked worktree kept inside its main checkout is seen
  through it. A submodule's own linked worktree kept inside the submodule's
  checkout has the submodule's checkout as its main checkout, read from
  `core.worktree` as `worktree_anchors` reads it (implement round 2, S1;
  `test_a_submodules_own_worktree_kept_inside_it_finds_the_root_in_the_copy`).

## Notes

- TCW-119 (a separate item, on `tcw migrate`'s reading of a child's term in
  `capabilities.yaml`) is planned to ship in the same 4.1.0 release; the two
  share no code, so this item does not cut the version.
- Workaround until then: an entry for `r` in p's
  `.tcw/tcw-manifest.local.yaml`.
- **A separate change, not made here:** when a copy lacks a project (case
  6), the refusal says "check the spelling", which misleads, since the
  spelling is right and the project is simply not in the copy. A better
  remedy names the manifest entry. It needs its own item.
- **Known behaviour, kept (the code review, N1):** with a bare repository
  kept as `project/.git` and its linked worktrees beside it in `project/`,
  git names the common folder `.git`, so the container folder `project`
  counts as the worktrees' main checkout, and a search from a plain clone
  kept inside one of those worktrees leaves `project` out of its climb. A
  project declared at `project` is then not found from there, which is what
  4.0.0 already answers from the worktree itself.
- **A separate change, not made here (the code review, N5):** `_git_lines`
  in `tcw/store/project.py` catches `CalledProcessError` and `OSError` but
  not `UnicodeDecodeError`, so git output that is not valid UTF-8, such as
  a path in another encoding, raises rather than answering None. It needs
  its own item.
- **Known behaviour, not changed here (the review's recheck):** a main
  checkout made with `git init --separate-git-dir` keeps its git folder
  elsewhere, and git records no main checkout for its linked worktrees
  (`git worktree list` names the git folder, and there is no
  `core.worktree`). So the climb cannot tell which folder to leave out, and
  a search from a copy kept inside such a checkout still reaches it: when
  the checkout is TCW 3.x, the answer is still that it needs `tcw migrate`.
  4.0.0's `worktree_anchors` already ignores this layout. Recognising it
  needs its own item.
