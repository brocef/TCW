# Outcome — Resolve relative connected-projects paths against the main worktree root

All seven plan tasks shipped, in order, one commit each. The suite is green and
every acceptance criterion is met. Two spec/plan claims were disproved by the
code and corrected in place.

## What shipped

| # | Commit | Subject |
| --- | --- | --- |
| 1 | `8edc17f` | `feat(project-registry): add a linked-worktree anchors probe` |
| 2 | `120a590` | `fix(project-registry): re-anchor an escaping relative locator to the main worktree` |
| 3 | `9fa72c4` | `fix(project-registry): collapse the worktree's own identity in the graph` |
| 4 | `08910e2` | `fix(work): refuse complete from inside the item's own worktree` |
| 5 | `efd923a` | `test: add the linked-worktree environment as the fourth hardness environment` |
| 6 | `0bffbc1` | `caps(run-from-a-git-worktree): declare Supported, bound two layout claims` |
| — | `afffe3b` | `tcw work: file follow-up for non-git write paths` |
| 7 | `39b73df` | `docs: sync README, changelog, release notes and the tcw-work skill` |

**Task 1 — the git probe.** `worktree_anchors(directory)` in
`tcw/store/project.py`, returning `(current worktree top, main worktree root)` in
a linked worktree and `None` otherwise, never raising. One
`git rev-parse --path-format=absolute --show-toplevel --git-common-dir` yields
both. Cached in an unbounded module-level dict keyed by resolved directory, with
a comment saying why it is not an LRU. It lives in `project.py`, not beside
`git_root` in `fs.py`, because `fs.py` imports `project.py`.

The bare-main-repo case is discriminated by **the common dir not being named
`.git`**. Measured on a real bare clone before the code was written:

```
=== normal-repo worktree ===   .../src-wt          .../src/.git
=== primary checkout ===       .../src             .../src/.git
=== bare-repo worktree ===     .../bare-wt         .../bare.git      ← not ".git"
=== non-git ===                fatal: not a git repository …   exit=128
```

A submodule's common dir (`<main>/.git/modules/<name>`) also fails that test, so
the probe returns `None` there too — no behavior change from HEAD, which is the
safe answer.

**Task 2 — Rule 1.** `_target_path` became an instance method (five call sites)
so the probe runs once per registry. A relative locator whose naive target
escapes the current worktree is re-resolved against
`main_root / source_dir.relative_to(current_toplevel)`; one that stays inside is
kept. As the plan predicted, this commit alone leaves the two-node worktree
fixture reporting `duplicate project id 'example-server'` plus a non-reciprocal
`child locator … does not point back` — the pre-existing suite was green (1138
passed) and task 3 closes it.

**Task 3 — Rule 2.** The current node's counterpart config under the main
worktree root is aliased onto the worktree's own config, so the graph holds one
node for the current project — the checked-out one. Exactly one pair, only under
a linked worktree.

**Task 4 — the `complete` refusal.** Detection reuses the task-1 probe and
compares the worktree top against *this item's* own worktree path
(`main / node_root.relative_to(top) / item.worktree`), so completing from an
unrelated worktree is untouched. Placed before every gate, so the refusal happens
before the Definition-of-Done checklist is printed.

**Task 5 — the fourth environment.** `tests/test_environment_hardness.py` gains
`two_node_graph` / `worktree_node` / `monorepo_worktree` factories and a
`TestWorktreeNode` class of ten tests, with the module docstring extended from
three environments to four. `tests/test_project_registry.py` gains five
`worktree_anchors` cases, including the bare main repo and a forced
`FileNotFoundError`.

**Task 6 — capabilities and taxonomy.** `cli/run-from-a-git-worktree`
(`cap-b47597`, `Feature: connected-project-registry`, `Subject: node`) declared
under `new:` in this item's new `capabilities.yaml` and flipped `Missing` →
`Supported`. `cli/host-multiple-projects-in-one-repo` and
`docs/taxonomy/node/description.md` had their "never scans git metadata" claims
bounded to what they were asserting — that the *graph* is not inferred from
layout. `work/complete-a-work-item` gained the refusal.
`state.yaml` effort `low` → `medium`, per the plan's Notes.

**Task 7 — documentation sync.** Below.

## Test result

```
$ python -m pytest -q
1149 passed in 159.21s (0:02:39)
```

The suite was run in full at four points, and was green at every one:

| After | Result |
| --- | --- |
| tasks 1-2 | `1138 passed in 154.95s (0:02:34)` |
| task 3 | `1138 passed in 170.17s (0:02:50)` |
| tasks 4-5 | `1148 passed in 164.24s (0:02:44)` |
| tasks 6-7 (final) | `1149 passed in 159.21s (0:02:39)` |

1133 before this item. `+5` are the `worktree_anchors` cases landed with task 1,
so they are already inside the 1138 baseline; `+10` are `TestWorktreeNode` at
task 5; `+1` is `tests/test_documented_cli_surface.py` picking up the new
`cli/run-from-a-git-worktree/description.md`, since its `DOC_FILES` is derived
from `git ls-files` rather than a hand-maintained list.

## Manual verification

### 1. The spec's Problem-section reproduction, re-run after the fix

Fixture: workspace root `example-app`, child git repo `example-server` declaring
`parent: {example-app: ..}`, linked worktree at
`example-server/.worktrees/my-feature`. Run from inside the worktree:

```
$ tcw work list
2026-07-30-created-inside-the-worktree | backlog | R | - | Created inside the worktree
exit=0
$ tcw work nodes
node:   example-server
parent: example-app
children: (none — leaf)
exit=0
$ tcw capabilities list
exit=0
$ tcw taxonomy list
exit=0
$ tcw validate
validate OK
exit=0
```

All five exit 0 (criterion 1), `parent: example-app` (criterion 2). The item in
that listing was created from inside the worktree and landed in the worktree's
own `docs/work/backlog/`, not the primary checkout's (criterion 4):

```
$ tcw work new "Created inside the worktree"
→ created at docs/work/backlog/2026-07-30-created-inside-the-worktree
--- worktree docs/work/backlog:   2026-07-30-created-inside-the-worktree
--- primary docs/work/backlog:    (empty)
```

Registry introspection from the same directory (criteria 3 and 4):

```
check(): []
current.locator: …/example-server/.worktrees/my-feature
parent: example-app …/example-app
```

### 2. Multi-project-in-one-repo, unregressed (criterion 5)

`mono-root` at the repo top with `sub-a`/`sub-b` beneath, linked worktree at
`<repo>/.worktrees/f`, run from `<worktree>/sub-a`:

```
$ tcw work nodes
node:   sub-a
parent: mono-root
children: (none — leaf)
exit=0

check(): []
parent.locator: …/mono/.worktrees/f
is the WORKTREE's repo top: True
is the PRIMARY checkout:    False
```

This is the case the reported remediation regressed into
`duplicate project id 'sub-a'`. The parent resolves to the **worktree's** repo
top, which is what Rule 1's narrowness buys.

### 3. Non-git graph, byte-identical to HEAD (criterion 6)

HEAD's output was captured **before** any code was written, at `d795ac9`, on a
two-node graph with no `git init` anywhere. Re-run after the change and diffed:

```
$ diff -u nogit-HEAD.txt nogit-AFTER.txt
(no differences)

=== tcw work list ===
exit=0
=== tcw validate ===
validate OK
exit=0
=== tcw work nodes ===
node:   example-server
parent: example-app
children: (none — leaf)
exit=0
```

This is a measurement, not a claim.

### 4. The `complete` refusal and its positive control (criterion 9)

Before the fix, on a standalone node with an item started `--worktree`, run from
inside that worktree:

```
$ tcw work complete 2026-07-30-try-worktree-flow --resolution done --confirm
completed 2026-07-30-try-worktree-flow (done) → docs/work/completed/…
complete exit=0
--- primary log:  66912db tcw work: start 2026-07-30-try-worktree-flow (worktree)
--- worktrees:    …/fx-solo                             66912db [main]
                  …/fx-solo/.worktrees/2026-07-30-…     f803709 [work/2026-07-30-…]
```

Exit 0, nothing merged, worktree still standing. After:

```
$ tcw work complete 2026-07-30-try-worktree-flow --resolution done --confirm
tcw work complete: 2026-07-30-try-worktree-flow cannot be completed from inside
its own worktree — the merge-back and teardown act on the primary checkout.
Re-run from /…/fx-solo2.
exit=1
```

Positive control — same item, real work committed on the branch, run from the
primary checkout:

```
### primary before:  8919646 tcw work: start … (worktree)   [no feature.txt]
$ tcw work complete 2026-07-30-try-worktree-flow --resolution done --confirm
completed 2026-07-30-try-worktree-flow (done) → docs/work/completed/…
exit=0
### primary after:
65cd55f tcw work: 2026-07-30-try-worktree-flow → completed
7041f7c branch work                       ← merged back
8919646 tcw work: start … (worktree)
   …/fx-solo3/feature.txt                 ← present
### worktrees: …/fx-solo3  65cd55f [main]  ← worktree gone
### branches:  * main                      ← work branch deleted
```

## What the spec and plan got wrong

**1. "Absolute locators are unaffected" is true of the function and false of the
graph.** Spec Problem point 1 claimed absolute locators were untouched by the
bug. That is true of `_target_path` in isolation — it returns them as written —
but a two-node graph declared *entirely* with absolute locators is also broken
from inside a worktree at HEAD, by a different route: the parent's absolute child
locator names the primary checkout, so the registry loads that config alongside
the worktree's own. Measured at `d795ac9`:

```
HEAD check(): ["…/example-server/tcw-config.yaml: duplicate project id
  'example-server' also used by …/my-feature/tcw-config.yaml",
 "…/example-app/tcw-config.yaml: child locator for 'example-server' does not
  point back to …/my-feature"]
```

The design consequence is real: **Rule 2 must apply to absolute locators too.**
The first implementation returned absolute locators early — before Rule 1, and
therefore before Rule 2 as well — and criterion 8 failed with exactly the pair
above. Rule 2 is not a re-anchoring rule; it aliases one already-resolved path
onto another, and a parent may spell the current node absolutely just as readily
as relatively. `_target_path` now resolves the locator first, applies Rule 1 to
the relative case only, then applies Rule 2 to whatever came out. Rule 1 remains
relative-only, exactly as specified.

Corrected in place: spec Problem point 1, spec Design (Rule 2), spec criterion 8,
plan task 2, plan task 3.

**2. Criterion 8's wording rested on that false premise.** "Absolute locators are
untouched" was restated as "a fixture declaring the connection with absolute
paths resolves the same graph inside and outside a worktree" — the property that
was actually wanted, and one the original wording would have forbidden.

**3. Effort was `low`; it is `medium`.** Flagged in both the spec's Notes and the
plan's Notes, and now fixed in `state.yaml` rather than left as an estimate
nobody corrected.

Everything else in the spec held. The prototype's monkeypatched predictions —
`problems=(none)` on all four fixtures, `current=sub-a parent=mono-root` inside
the monorepo worktree — reproduced exactly against the real integration, and the
sweep's claim that all four components fail through one resolution site was borne
out: one function changed and `work`, `capabilities`, `taxonomy` and `validate`
all came right together.

## Documentation Sync

| Entry | Trigger | Fired | What changed |
| --- | --- | --- | --- |
| `README.md` | `Public-API` | **yes** | The Connected projects section said relative locators "resolve from the declaring config" and that TCW derives ancestry "never by scanning directories or git metadata" — the first is now conditionally false and the second false in the letter. Both bounded, with a new paragraph on worktree re-anchoring. The `--worktree` section gained the run-`complete`-from-the-primary-checkout rule. |
| `docs/changelogs/upcoming.md` | `Any-Code-Change` | **yes** | `worktree_anchors` under **Added**; both resolution rules and the `complete` refusal under **Fixed**, recording that the reported remediation was insufficient and why; the fourth test environment under **Internal**. |
| `docs/release-notes/upcoming.md` | `Public-API` | **yes** | Two entries in plain language: TCW works from inside a git worktree, and `complete` from inside a worktree now refuses instead of silently doing nothing. |
| `skills/tcw-work/references/transitions.md` | `Skill-Driven-Component` | **yes** | `complete`'s gate list gained the primary-checkout condition. |
| `skills/tcw-work/references/commands.md` | `Skill-Driven-Component` | no | Lists the command form only (`start <slug> [--worktree]`); no gate or lifecycle text to drift. |

No version was cut.

## Follow-up filed

`2026-07-30-fix-non-git-write-paths-work-new-and-init-fail-outside-a-git-repository`
(backlog, tags `cli`/`bug`). Reads work without git; writes do not — `tcw work
new` dies with an unhandled `CalledProcessError` from `git_stage` and `tcw init`
refuses outright. Its `initial-request.md` carries the measurements and names the
contract question (is git a precondition or an enhancement?) rather than
presupposing a fix.

## Notes

- **Criterion 7 held precisely.** The only deletions anywhere under `tests/` are
  **four** lines: the module docstring's "Three environments are scaffolded", two
  section-header comments renumbered 4→5 and 5→6, and one single-line
  `from tcw.store.project import …` reformatted into a parenthesized three-line
  import to add `worktree_anchors`. No test body, assertion, or fixture was
  touched. `git diff -U0 -- tests/ | grep '^-'` is the check — note it also
  matches `--- a/…` diff headers, which must be netted out.

  *(Corrected during verification: this originally said "three lines" and omitted
  the reformatted import. The substance of criterion 7 was unaffected; the count
  was wrong because the header lines were netted out by hand.)*
- **The `.git`-name discriminator for bare repos is a heuristic with one known
  hole**: a bare repository literally named `.git`. Returning `None` in the wrong
  direction there means "behave as HEAD does", which is the failure mode you
  want; the opposite discriminator would re-anchor against a nonsense parent.
- **A sibling node in the same repo still resolves to the worktree copy.** The
  spec recorded this as deliberate under Rule 1, and criterion 5 now pins it as a
  test rather than a paragraph. It means a cross-node reference from a worktree
  reads the sibling on the *worktree's* branch.
- **The probe cache is per-process and per-resolved-directory.** Tests get unique
  `tmp_path` directories, so there is no cross-test pollution and no reset hook is
  needed. If a future test ever needs to change a directory's worktree status
  mid-process, it will have to clear `_ANCHOR_CACHE` — nothing does today.
- **`tcw work complete` from inside an *unrelated* worktree is still allowed**
  and still merges against `st.node_root`, which in that situation is the
  unrelated worktree. That is out of this item's scope (it is not the reported
  defect and no fixture exercises it), but it is the same class of confusion and
  someone should decide whether it deserves the same refusal.
- GitHub issue #9 is **not** closed at completion — deferred until the containing
  minor version is cut and pushed, per the user's 2026-07-30 decision.
