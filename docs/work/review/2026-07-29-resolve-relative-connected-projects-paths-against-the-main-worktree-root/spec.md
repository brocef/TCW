# Spec: Resolve relative connected-projects paths against the main worktree root

## Capability changes

Planned ledger deltas only — nothing is written to `docs/capabilities/` at this
stage.

**New**

- `cli/run-from-a-git-worktree` — "Run TCW from inside a git worktree."
  Seeded `Status: Missing` with `Planning doc` pointing at this item; flipped to
  `Supported` at completion. `Feature: connected-project-registry`
  (`docs/taxonomy/connected-project-registry/`), `Subject: node`.
  Nothing in the ledger describes running from a linked worktree today —
  `tcw capabilities search worktree` returns only `work/complete-a-work-item`,
  and that hit is about `--already-integrated`
  (`docs/capabilities/work/complete-a-work-item/description.md:10`).

**Changed**

- `cli/host-multiple-projects-in-one-repo` — its `description.md` closes with
  "TCW derives deeper ancestry from the registered graph **without scanning
  directories or git metadata**." After this change the filesystem adapter reads
  git metadata to re-anchor a relative locator. The claim needs bounding to what
  it was actually asserting (the *graph* is not inferred from layout) so it does
  not read as false.
- `work/complete-a-work-item` — gains the refusal described in Goal 3.

**Adjacent, not a delta here:** `docs/taxonomy/node/description.md` says node
relations come "only from reciprocal registered locators, independent of
filesystem nesting or git layout". Same bounding problem as above; it is a
taxonomy-axis edit, listed here so the plan schedules it.

No new Vocabulary term is proposed. A git worktree is a property of the host
checkout, not a TCW noun; locator resolution is already covered by the
registered Feature `connected-project-registry`.

`tcw capabilities check` is clean at HEAD (`capabilities OK`), so there is no
pre-existing structural problem to resolve first.

## Problem

`FsProjectRegistry._target_path` (`tcw/store/project.py:256-261`) resolves a
relative `connected-projects` locator against `source_config.parent` — the
directory of the config file that declares it. Inside a linked git worktree that
directory is the worktree, not the checkout the locator was authored against, so
every relative locator is off by the worktree's nesting depth.

`_visit` follows both `children` and `parent` locators through that function
(`tcw/store/project.py:179-182`), and a target with no sentinel is a hard problem
(`tcw/store/project.py:187-189`). `find_node` calls `require_valid()` before it
returns anything (`tcw/store/fs.py:130`), so *every* command fails — including
read-only ones.

Reproduced at HEAD (`bfc4b14`, `tcw 0.17.3`) on a throwaway graph: workspace root
`example-app`, child repo `example-server` whose config declares
`parent: {example-app: ..}`, with a linked worktree at
`example-server/.worktrees/my-feature`.

```
=== primary checkout: tcw work list ===
exit=0
=== worktree: tcw work list ===
tcw: .../example-server/.worktrees/tcw-config.yaml: registered target has no tcw-config.yaml
exit=1
=== worktree: tcw validate ===
.../example-server/.worktrees/tcw-config.yaml: registered target has no tcw-config.yaml
1 project graph problem(s).
exit=1
=== worktree: tcw capabilities list ===
tcw: .../example-server/.worktrees/tcw-config.yaml: registered target has no tcw-config.yaml
exit=1
=== worktree: tcw taxonomy list ===
tcw: .../example-server/.worktrees/tcw-config.yaml: registered target has no tcw-config.yaml
exit=1
```

Two facts the report does not state, both established by experiment and both
load-bearing for the design:

1. **The *reported* bug needs a relative locator.** A standalone node with no
   `connected-projects` runs fine from inside its own `--worktree` checkout
   (`work list`, `work show`, `work submit` all exit 0). Absolute locators are
   unaffected *by this code path* — `_target_path` returns them untouched
   (`tcw/store/project.py:258-260`).

   **Corrected during implementation.** "Absolute locators are unaffected" is
   true of the function and **false of the graph**. A two-node graph declared
   entirely with absolute locators is *also* broken from inside a worktree at
   HEAD, by a different route: the parent's absolute child locator names the
   primary checkout, so the registry loads that config alongside the worktree's
   own and reports the same `duplicate project id` + `does not point back` pair
   the relative case produces after Rule 1. Measured at `d795ac9` on the
   absolute-locator fixture:

    ```
    HEAD check(): [".../example-server/tcw-config.yaml: duplicate project id
        'example-server' also used by .../my-feature/tcw-config.yaml",
     ".../example-app/tcw-config.yaml: child locator for 'example-server' does
        not point back to .../my-feature"]
    ```

   Consequence for the design: **Rule 2 must apply to absolute locators too.**
   Scoping it to the relative branch leaves criterion 8 failing. Rule 1 remains
   relative-only.
2. **The report's remediation, applied literally, does not fix it.** Resolving
   *every* relative locator against the main worktree root was prototyped against
   the fixture above. It clears the reported error and produces two new ones:

    ```
    .../example-server/tcw-config.yaml: duplicate project id 'example-server'
        also used by .../example-server/.worktrees/my-feature/tcw-config.yaml
    .../example-app/tcw-config.yaml: child locator for 'example-server' does not
        point back to .../example-server/.worktrees/my-feature
    ```

    The parent's own `example-server` locator still resolves to the primary
    checkout, so the graph acquires two configs carrying one ID
    (`tcw/store/project.py:171-176`) and fails reciprocity
    (`tcw/store/project.py:276-280`). `require_valid()` raises on either, so
    `tcw work list` still exits 1 — with a different message.

3. **It also regresses a layout that works today.** Multiple nodes in one repo
   (`docs/capabilities/cli/host-multiple-projects-in-one-repo/`, `Supported`) is
   fine inside a worktree at HEAD, because every relative target stays inside the
   worktree. Under always-re-anchor the same fixture reports
   `duplicate project id 'sub-a'` and a non-reciprocal `mono-root`, i.e. the
   proposed fix breaks a working case.

## Goals

1. From inside a linked git worktree, every `tcw` command resolves the same
   project graph it resolves from the primary checkout, for relative and absolute
   locators alike.
2. The node the commands operate on stays the **worktree** — its `docs/work/**`,
   `docs/capabilities/**` and `docs/taxonomy/**` are the checked-out ones, not the
   primary checkout's. Only graph *topology* is resolved via the primary checkout.
3. `tcw work complete` run from inside the item's own worktree stops silently
   doing nothing (see the sweep below) — it either performs the merge-back and
   teardown against the primary checkout or refuses with a message naming where
   to run it.
4. Nothing changes outside a linked worktree, and nothing changes for a node that
   is not in a git repository at all.

## Non-goals

- **Making TCW usable without git.** Reads already work without git
  (`tcw work list`, `tcw validate`, `tcw work nodes` all exit 0 in a repo-less
  tree) but writes do not: `tcw work new` dies with an unhandled
  `CalledProcessError` from `git_stage` (`tcw/store/fs.py:640` → `:262`), and
  `tcw init` refuses outright (`tcw/cli.py:30`). That is a real, separate defect
  found by this sweep; it gets its own item. This item must not make the git
  requirement *worse*, which is Goal 4.
- **`tcw work start --worktree` from inside a worktree.** Nested worktrees are a
  layout nobody asked for; out of scope.
- **Changing the locator format.** No `${TCW_NODE_ROOT}` token, no config
  migration, no deprecation of relative locators.
- **Making a sibling node inside the same repo resolve to its worktree copy.**
  See Risks.
- **Worktrees TCW did not create.** The fix keys on git's own notion of a linked
  worktree, so a hand-made `git worktree add` anywhere is covered; but no new
  bookkeeping is added to track them.

## Design

Two rules inside `FsProjectRegistry`, both filesystem-adapter private.

**A git probe.** One helper, private to `tcw/store/project.py`, returning
`(current_toplevel, main_worktree_root)` when the registry's `node_root` sits in a
*linked* worktree and `None` otherwise. `None` on: git absent, not a repository,
the primary checkout, a bare main repo, or any non-zero exit. The single
invocation `git -C <dir> rev-parse --path-format=absolute --show-toplevel
--git-common-dir` yields both values (verified: inside the worktree it prints the
worktree top, then `<main>/.git`); `git worktree list --porcelain`'s first record
is the documented alternative and is what distinguishes a bare main repo. Either
is acceptable; the plan picks one and handles the bare case.

The helper lives in `project.py`, not next to `git_root` in `fs.py`: `fs.py`
imports `project.py` (`tcw/store/fs.py:39`), so the reverse import is circular.

**Rule 1 — re-anchor only on escape.** When resolving a relative locator whose
source config is inside the current worktree, compute the naive target first. If
it still lies inside the worktree, keep it. If it escapes, re-resolve it against
the source directory's counterpart under the main worktree root
(`main_root / source_dir.relative_to(current_toplevel)`).

This is deliberately narrower than the report's proposal. A target that stays
inside the worktree is a sibling node on the same branch and belongs to the
worktree; only a target that leaves the checkout was authored against the primary
checkout's position on disk. This is what keeps the multi-project-in-one-repo
layout working.

**Rule 2 — collapse the worktree's own identity.** The current node has two
config paths on disk: `<worktree>/tcw-config.yaml` and its counterpart
`<main>/<rel>/tcw-config.yaml`. Once the parent is reachable, the parent's own
locator points at the second one, and the registry would register both as one ID.
`_target_path` therefore maps that one main-worktree path onto the worktree path,
so the graph holds exactly one node for the current project — the worktree copy,
satisfying Goal 2.

**Rule 2 applies to absolute locators as well as relative ones** (corrected
during implementation — see Problem, point 1). Unlike Rule 1, it does not
re-anchor anything: it aliases one already-resolved path onto another, and the
parent may name the current node by absolute path just as readily as by relative
one. Restricting it to the relative branch leaves the absolute-locator graph
failing inside a worktree, which is criterion 8.

Rule 2 also keeps `_validate_reciprocity` (`tcw/store/project.py:263-306`)
consistent, because it compares `_target_path` outputs against `cfg.path` and both
sides now agree, and it keeps `registered_project_id(node, node)`
(`tcw/store/fs.py:164-172`) resolving, since `current.locator` remains the
worktree.

`_target_path` is a `@staticmethod` today with five call sites
(`tcw/store/project.py:180, 182, 266, 276, 297`); it becomes an instance method
(or takes the anchor) so the probe result is computed once per registry rather
than per locator.

**Prototype evidence.** Both rules were prototyped by monkeypatching
`_target_path` and opening the registry against four fixtures:

```
[mono/.worktrees/f/sub-a]  problems=(none) current=sub-a       parent=mono-root
[mono/sub-a (primary)]     problems=(none) current=sub-a       parent=mono-root
[repro2 worktree]          problems=(none) current=my-feature  parent=example-app
[repro2 primary]           problems=(none) current=example-server parent=example-app
```

**Everything else routes through this one function.** Sweep results below.

### Scope sweep (repo-wide)

Checked, no separate fix needed:

- `_extended_component_roots` (`tcw/store/fs.py:520-538`) — taxonomy/capabilities
  federation resolves `extends` IDs through `FsProjectRegistry`, so it inherits
  the fix. Its self-extend guard (`:535`) compares against `node_root` and still
  holds under Rule 2.
- `child_nodes` / `parent_node` / `descendant_nodes` (`tcw/store/fs.py:134-161`),
  `registered_project_id` (`:164-172`), `resolve_qualified_work_ref` (`:175-233`),
  `qualified_work_ref_problem` (`:236-258`) — all open the registry; no
  independent path arithmetic.
- `tcw/validate.py:117-124` and `tcw/refs.py:105-125` — registry / store
  delegation only.
- `find_node_root` (`tcw/store/fs.py:110-120`) — walks for the sentinel and finds
  the worktree's own copy. Correct as-is; that is what makes Goal 2 free.
- `git_root` (`tcw/store/fs.py:68-82`) — used only by `tcw init`
  (`tcw/cli.py:30`) and the capabilities CLI. Returns the worktree top inside a
  worktree, which is the right answer for both.
- Empirically, `work`, `capabilities`, `taxonomy` and `validate` all fail with the
  identical message from the identical path (Problem section), confirming a single
  resolution site rather than four.

**Sibling defect found — in scope (Goal 3).** `tcw work complete` run from inside
the item's own worktree reports success and does nothing. `st.node_root` is the
worktree, so `merge_worktree(st.node_root, branch)` (`tcw/work/cli.py:837` →
`tcw/store/fs.py:411-429`) merges the work branch into itself, and
`remove_worktree(st.node_root, bare, branch)` (`tcw/work/cli.py:887` →
`tcw/store/fs.py:432-448`) looks for `<worktree>/.worktrees/<slug>`, misses, and
swallows the miss as "already absent" (`tcw/store/fs.py:441`). Observed on a
standalone node:

```
$ cd .worktrees/2026-07-30-try-worktree-flow
$ tcw work complete 2026-07-30-try-worktree-flow --resolution done --confirm
completed 2026-07-30-try-worktree-flow (done) → docs/work/completed/...
complete exit=0
$ git -C <primary> log --oneline -1
538a404 tcw work: start 2026-07-30-try-worktree-flow (worktree)   # nothing merged
$ git -C <primary> worktree list
.../solo                                          538a404 [main]
.../solo/.worktrees/2026-07-30-try-worktree-flow  72e6a90 [work/...]   # still there
```

No work is lost today — the branch survives and the miss is tolerated — but the
command claims a completion that did not happen. Refusing is the smaller fix and
loses nothing: `git worktree remove` on the worktree you are standing in deletes
your own cwd (verified), so completing from inside is not a flow worth
engineering.

**Sibling defect found — out of scope.** Non-git write paths, above under
Non-goals.

## Acceptance criteria

Fixtures are throwaway git repos; "worktree" means one created with
`git worktree add`.

1. In a two-node graph (`example-app` workspace root; `example-server` a git repo
   inside it declaring `connected-projects.parent: {example-app: ..}`), from
   inside `example-server/.worktrees/<name>`: `tcw work list`,
   `tcw work nodes`, `tcw capabilities list`, `tcw taxonomy list` and
   `tcw validate` each exit 0, and `tcw validate` prints `validate OK`.
2. In that same worktree, `tcw work nodes` prints `parent: example-app`.
3. In that same worktree, `FsProjectRegistry.open(<worktree>).check()` returns an
   empty list — specifically no `duplicate project id` and no
   `does not point back` problem.
4. In that same worktree, `FsProjectRegistry.open(<worktree>).current.locator`
   resolves to the **worktree** path, not the primary checkout, and a work item
   created there lands under the worktree's `docs/work/`.
5. Multi-project-in-one-repo is unregressed: in a repo with `mono-root` at the top
   and `sub-a`/`sub-b` beneath it, each declaring `parent: {mono-root: ..}`, from
   inside `<repo>/.worktrees/<name>/sub-a` the registry reports no problems,
   `parent: mono-root`, and the parent's locator is the **worktree's** repo top,
   not the primary checkout's.
6. Non-git nodes are unregressed: in a graph with the same two-node shape and no
   `git init` anywhere, `tcw work list`, `tcw validate` and `tcw work nodes` exit
   0 exactly as they do at HEAD.
7. Primary-checkout behavior is byte-identical: the full `python -m pytest -q`
   suite passes with no test modified to accommodate the change.
8. A fixture declaring the connection with absolute paths resolves the same
   graph inside and outside a worktree. (Restated during implementation: the
   original wording, "absolute locators are untouched", was built on the false
   premise corrected in Problem point 1. Absolute locators are untouched *by
   Rule 1*; Rule 2 does apply to them, and must, or this criterion fails.)
9. `tcw work complete <slug> --resolution done --confirm`, run from inside the
   worktree of an item started with `--worktree`, does not exit 0 while leaving
   the primary checkout unmerged and the worktree present. Either the primary
   checkout's branch advances and the worktree is gone, or the command exits
   non-zero with a message naming the primary checkout as where to run it.
10. `tests/test_environment_hardness.py` gains a fourth environment — a node
    inside a linked worktree — alongside the three its module docstring already
    describes (`tests/test_environment_hardness.py:1-20`), covering criteria 1-5.
11. `tcw capabilities check` and `tcw validate` are clean in this repo after the
    capability and taxonomy wording edits land.

## Risks

- **Cost.** The git probe is one subprocess at ~8 ms (measured). `tcw work list`
  opens the registry once; `tcw work list -i` on a three-node graph opens it six
  times (measured), so an uncached probe adds ~50 ms to recursive commands. Cache
  the probe per resolved directory at module level; a single CLI invocation never
  outlives the process.
- **A sibling node inside the same repo keeps resolving to the worktree copy.**
  Under Rule 1 that is deliberate and matches today's behavior, but it means a
  cross-node reference from a worktree reads the sibling on the *worktree's*
  branch. That is the defensible reading (same repo, same branch), and it is what
  the multi-project layout already does; recorded so nobody treats it as an
  oversight.
- **Git metadata enters graph resolution.** The registry has been advertised as
  layout-independent (`docs/taxonomy/node/description.md`,
  `docs/capabilities/cli/host-multiple-projects-in-one-repo/description.md`).
  Mitigated by scope: git is consulted only to *re-anchor a relative locator*,
  never to discover a node or infer a relation, and never on a path that is
  already correct. The abstraction litmus test is satisfied — `ProjectRegistry`
  (`tcw/store/base.py:64-94`) exposes no path-resolution operation and `Project`
  keeps `locator` opaque (`:53-61`), so worktree-awareness stays entirely inside
  `FsProjectRegistry`. A Jira-backed registry addresses projects by key and has no
  relative path to re-anchor; there is nothing here for it to implement.
- **Rule 2 changes what "same node" means.** Two distinct config paths now map to
  one node. It applies to exactly one pair (the current node's worktree and its
  main-worktree counterpart) and only while the probe reports a linked worktree.
  A wider alias would risk masking a genuine duplicate-ID error, which is a real
  validation the registry performs (`tcw/store/project.py:171-176`).
- **Bare or unusual main repos.** `--git-common-dir` in a bare repo has no
  worktree above it. The probe must return `None` there rather than re-anchoring
  against a nonsense parent directory; criterion 6 does not cover this, so the
  plan should add a targeted test.

## Notes

- The reporter's diagnosis of the *cause* is exactly right and the reproduction
  is faithful. Only the proposed remediation is wrong, in two independent ways
  (Problem, points 2 and 3); the item's own `## Notes` was right to flag it as a
  proposal.
- The item's `## Notes` asks whether resolving against the git common dir is
  right for a node that is not a git repository. Answer: the question is real and
  the constraint is that git must not become a hard requirement for reads, because
  it is not one today — `tcw work list`, `tcw validate` and `tcw work nodes` all
  exit 0 in a repo-less tree at HEAD. Goal 4 and criterion 6 encode that. The
  probe returning `None` on any git failure is what makes it hold.
- `docs/capabilities/work/start-a-work-item/description.md` does not mention
  `--worktree` at all, so the flag is undocumented at the capability layer. Not
  fixed here; noted because the new `cli/run-from-a-git-worktree` capability sits
  next to that gap.
- Effort in `state.yaml` is `low`. Rules 1 and 2 plus the `complete` refusal and
  the test environment read closer to `medium`; worth revisiting at planning.
