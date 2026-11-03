# Spec — From a copy of worktrees kept inside its own main checkout, the search for a project climbs past the copy into the main checkout

## Capability changes

- **Changed:** `tcw.capabilities/cli/run-from-a-git-worktree`. Its
  description gains one sentence saying which folders the search does not
  climb into from a worktree kept inside another repository's linked
  worktree: the folders between that linked worktree and its own main
  checkout, and the main checkout itself, when the linked worktree is stored
  inside its main checkout. No record is written at this stage.
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
the main checkout of the linked worktree one level further out.

The folder the climb should not reach is always the same kind: **the main
checkout of a linked worktree that encloses the asking project, together
with the folders between that linked worktree and its main checkout,
reached only because the linked worktree is stored inside its own main
checkout.** For the active project's own worktree, 4.0 already avoids
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

1. From a project in a linked worktree whose folder lies inside another
   repository's checkout, the search's climb does not test a folder that is
   the main checkout of a linked worktree enclosing the project, or lies
   between that linked worktree and its main checkout, when the linked
   worktree is stored inside its main checkout. This holds for every such
   linked worktree, however far out, not only the nearest.
2. The climb then goes on above that main checkout, as it would from the
   copy kept anywhere else.
3. `tcw migrate`'s prediction (`search_4`) gives the same answer, so
   migrating Y's linked worktree in the copy writes the same manifest as
   migrating its main checkout.
4. Every layout that works today gives the same answer after the change.

## Non-goals

- **The search made from a related project's folder that is outside the
  active project's worktree.** `search_rounds` gives that one the plain
  climb (`:382-383`), by the documented rule that "which worktree counts is
  the one the command runs from" (`docs/guide/multi-repo.md:631-634`). From
  `w` the plain climb reaches `MAIN` only when searching for a project `MAIN`
  itself declares, which `r` never searches for. Changing which worktree
  counts is a separate decision.
- **The folders next to the asking project.** They are the asking project's
  parent folder's other folders, always inside the checkout holding the
  worktree, never in the range this change removes.
- **Recognising more layouts as a copy.** The definition at `:391-393` is
  unchanged. Case 4 is fixed by the same rule without becoming a copy, and
  keeps its second round from Y's main checkout.
- **Manifest entries and store paths.** They do not climb.
- **Workarounds already in place.** An entry for `r` in p's
  `.tcw/tcw-manifest.local.yaml` keeps working, and still decides first.
- **Changing the refusal text** for two matches that really are two
  projects.

## Design

One change, in `search_rounds` (`tcw/store/project.py:354-394`), to the round
read as written, in both places it is returned. That is the copy's only
round (`:393`) and the first of the two rounds otherwise (`:394`):

1. Starting from the folder holding the active worktree (`top.parent`), find
   each linked worktree that encloses it, nearest first. Ask
   `worktree_anchors` of the folder; when it gives `(T, M)`, that is one;
   ask again from `T.parent`; stop when it gives None. Each answer's `T` is
   strictly above the last, so this ends. `worktree_anchors` is cached per
   folder (`:85-97`), so the nearest one costs nothing new; each further
   level is one `git rev-parse`.
2. For each `(T, M)` with `T` inside `M` (`_below(T, M)` is not None), leave
   out of the climb every folder `F` that encloses `T` without being `T`,
   and is `M` or inside it. These are the folders reached only because `T` is
   stored inside `M`.
3. The folders above `M` stay in the climb, in order.

"Inside" is decided by folder identity, with `_below`, as every other such
test in this module is, so a disk that ignores letter case behaves the same.

`search_4` needs no change of its own: it reads the same rounds (Goal 3). The
plan adds tests that it does.

Nothing else moves: `_search`, `_answer`, `_worktree_copy`, `read_as_written`
and the definition of a copy are unchanged. When no linked worktree outside
the active one is stored inside its own main checkout, nothing is left out,
and every round is what it is today.

## Abstraction litmus test

No new operation, and none changed. `search_rounds` is part of the
filesystem layer that resolves projects (deployment layer, `tcw/store/
project.py`). The git reads it adds (`git rev-parse`, through
`worktree_anchors`) are the kind `abstraction.md` places "in the code that
resolves projects, not in the model". A store that is not a folder of files
has no folders to climb and no search, so the question of whether a
non-filesystem store could implement it does not arise. Nothing a backend
owns is touched.

## Use cases

- **S-4 Copies of a checkout.** The case this fixes: a copy made of linked
  worktrees one inside another, kept inside the main checkout it was made
  from. That is what Claude Code's worktree tool does by default, at
  `.claude/worktrees/<name>`. After the change the copy finds its own
  projects and never the main checkout's copy on another branch. A plain
  worktree, a worktree kept elsewhere, and a copy kept outside the main
  checkout behave as before. S-4 does not yet describe a copy kept inside its
  own main checkout, so this change adds a requirement saying so.
- **UC-4 Many repositories and a planning workspace.** The layout is UC-4's:
  a workspace repository with a child repository cloned inside it. Its
  requirement that no project is located by git's ignore rules still holds:
  the change asks git only where a checkout and its main checkout are, never
  what it ignores. A child's worktree kept in the workspace's main
  checkout's `.worktrees/` folder still finds the workspace there (it
  encloses no linked worktree), and one kept in a linked worktree of the
  workspace that lies elsewhere still searches beside its main checkout on
  the second round.
- **S-9 Upgrades.** The 3.x refusal (case 2) names the main checkout today.
  After the change, a 3.x copy on the worktree's side is still the one
  reported, and a 3.x main checkout outside the copy is not read. `tcw
  migrate` run in the copy writes what it writes in the main checkout. No
  file format or key changes.
- **UC-1 A single project, UC-3 a monorepo.** Not affected. Their worktrees
  are inside one repository, so the folder holding the worktree is a checkout
  of the same repository, `read_as_written` is false (`:389`), and the round
  that changes is never used. They pay no extra `git` call.
- **UC-2, UC-5 to UC-8, S-1 to S-3, S-5 to S-8, S-10, S-11.** Not affected:
  nothing about stores, backends, Jira, harnesses, people, personal files or
  version control changes, only which folders one search climbs.

Checklist: (1) it locates projects, by the search only; UC-4 and the nested
layouts above are tested with real repositories. (2) It touches no object.
(3) It reads no further across projects than today, and less in the cases
fixed. (4) No backend. (5)-(7) Not applicable: no person, harness or
half-finished state is involved. (8) No cost to a single project: no extra
git call outside a worktree held in another repository's checkout. (9) No
file or key changes. (10) Every test uses real git repositories and linked
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
6. **A copy lacking the project does not find the original's.** The
   reported layout with `r`'s configuration removed from `w` (deleted from
   the working folder only): `project path r` exits non-zero and prints
   nothing to standard output.
7. **`tcw migrate`'s prediction agrees.** In the reported layout,
   `tcw.migrate.family.search_4(MAIN/.claude/worktrees/w/p, "r")` returns
   exactly `[MAIN/.claude/worktrees/w]`. With p on 3.x in both checkouts of
   Y, naming `r` as a parent at `..`, `tcw migrate --no-jira` run in
   `MAIN/.claude/worktrees/w/p` writes no `.tcw/tcw-manifest.yaml` entry for
   `r`, as the same run in `MAIN/p` writes none.
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
10. The whole suite passes as CI runs it (bare `pytest`).
11. `docs/guide/multi-repo.md` ("Git worktrees"), the capability's
    `description.md`, and `docs/use-cases.md` S-4 each say, in plain words,
    that the search from such a worktree does not climb into the main
    checkout a linked worktree holding it is stored in. A
    `docs/changelogs/upcoming/` and a `docs/release-notes/upcoming/` file,
    each named by this item's folder name, describe the fix.

Criteria 1, 2, 4, 5, 6 and the `tcw migrate` half of 7 were run on the tree
today as reproduction cases 1, 2, 4, 5 and 6 above, and fail. Criteria 3 and
9 were run and pass. The `search_4` half of 7 was run in case 1's layout and
returns `[MAIN/.claude/worktrees/w, MAIN]` today.

## Risks

- **Leaving out a folder someone relied on.** A project declared in the main
  checkout (or a folder between the linked worktree and it) that the copy
  does not have was found today, wrongly by the guide's own rule. After the
  change it is "not on this machine" from the copy, with the usual remedy
  (a manifest entry). This is the documented behaviour for copies, and case
  4's second round still reads beside Y's main checkout.
- **Cost.** One `git rev-parse` per further level of linked worktree, only
  from a worktree whose holding folder is in another repository's checkout;
  results are cached per command.
- **A main checkout above the copy that is reached by another route.** The
  folders above `M` are kept, so a project enclosing the main checkout, such
  as a workspace two levels up, is still found from the copy, as it would be
  from a copy kept elsewhere under the same folder.
- **Submodules.** `worktree_anchors` already answers for a submodule checked
  out in a superproject's linked worktree (`:234-238`). The new loop asks it
  the same question it already asks, so a submodule counts as its
  superproject's worktree here too. No test of submodules is added. That is
  an assumption, not a checked fact.

## Notes

- Ships in 4.0.1, together with TCW-119 (the request).
- Workaround until then: an entry for `r` in p's
  `.tcw/tcw-manifest.local.yaml`.
