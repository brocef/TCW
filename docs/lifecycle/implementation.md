<!-- Bound to the `implement` stage of `tcw work`; see `tcw-config.yaml`.
     Read as a continuation of TCW's built-in stage instructions, not on its own. -->

# Implementation rules

_Applies at `implement`. The design rules that govern what you build are in
[`abstraction.md`](abstraction.md), bound at `spec` and `plan`._

- Each component depends on an abstract **store interface** (`TaxonomyStore`, `WorkStore`, …) that the CLI and any skills talk to. Ship the **filesystem adapters** (`FsTaxonomyStore`, `FsWorkStore`) only; keep remote adapters (e.g. `JiraWorkStore`) possible but unbuilt. Never add an interface method that only the FS adapter could honor (run the litmus test first).
- The three components are **one system**: taxonomy is the nouns, capabilities the user stories (what a user can do), work the changes (to capabilities, machinery, or the project itself). They link by loose, one-directional pointers (capability→term, work→capability/term) and never duplicate each other.
- Python with type hints; pytest over `tmp_path` git repos. Use the ABC + adapter pattern for stores; extract the shared tree-store core only once two components are real (don't pre-abstract).
- **Skill authoring (progressive disclosure):** a `skills/<name>/SKILL.md` is a **thin router** — keep always-relevant judgment inline (the core lifecycle, the gates) and push genuinely rare sub-procedures into `skills/<name>/references/*.md` read on demand, each reached by a clear gate condition in the router (the `tcw-plugin` and `tcw-work` skills are the pattern). Only split once a skill's conditional detail is large enough to earn the indirection — for ~50-line, mostly-always-relevant skills it's a no-op; leave them inline.

## A node's work store is often in a different git repository

`work.path` in a node's `tcw-config.yaml` may point at a store outside that
node's own repository, and in the orchestrator layout it normally does. The
reference shape, from `/Users/brian/Projects/proposit-orchestration/`:

```
proposit-orchestration/          git repo A — owns docs/ and every work store
├── docs/proposit-core/work/     the child's store
├── proposit-core/               git repo B, nested, and gitignored by A
│   └── tcw-config.yaml          work.path → ../docs/proposit-core/work
```

Planning consolidates in one repository; code lives in several. This is the
intended multi-repo layout, not an edge case, and it has two consequences that
have each shipped silent bugs.

- **The store root and the node root vary independently.** Any code that
  reconstructs a store location from the node root plus a literal `docs/work`,
  runs `git -C <node_root>` over a store path, or hardcodes a `docs/work` commit
  pathspec is broken here — usually with no error. Resolve through
  `FsWorkStore.open(node)` and use its `store_git_root` and `root`. Never treat
  the existence of a `docs/work` directory as a proxy for "this is a work node";
  ask the store and catch `ValueError`. Issues #15–#18 were four separate
  instances of exactly this.
- **"Gitignored, therefore not a node" is false.** The child nodes above are
  each their own repository, gitignored by the parent so it does not track
  sub-project files. Any gitignore-based pruning of the node walk
  (`descendant_nodes` in `tcw/store/fs.py`) must be evaluated per repository and
  must never prune at a nested repository boundary — cross it and re-evaluate
  against that repository's own ignore rules. A naive top-level `git ls-files -oi`
  prune drops every child node and makes `tcw work list --include-descendants`
  return empty.

A regression test for either needs **two real git repositories** in the fixture.
A single-repo `tmp_path` reproduces none of it, which is plausibly why all four
of those issues shipped.

## Beginning implementation

After planning concludes, and implementation is about to begin, use `tcw work start {work-item-slug}` to move it to the active status. This status transition should be the first implementation commit.

## Before reporting complete

Evaluate this project's documentation entries by invoking the
`documentation-sync` skill. The entries themselves come from `tcw work docs`;
they live in `tcw-config.yaml` under `work.documentation`, where `tcw validate`
checks them.

## Tests that cannot narrow a criterion

Two rules, both earned. A general acceptance criterion verified by a helper that
quietly fixes two of its axes is indistinguishable, at review, from a criterion
verified generally — which is how the store-provisioning epic shipped the same
defect shape four times.

- **A shared fixture may not default an axis the code branches on.** If a helper
  builds a node, every configuration key the resolution path tests is an explicit
  argument with no default. A fixture's default is always whichever value makes
  setup easiest, and that is why three of those four defects sat in cells no test
  could reach — `_tree_node` created the local tree unconditionally and every
  caller passed `path=`, so the uncovered cell was unreachable by construction.
- **When asserting a user-facing message, assert that the message it replaces
  is absent.** An assertion aimed at a string another program owns is not a test
  of this one. A divergence test asserted `"diverged" in err`, matched *git's*
  push-rejection hint, and stayed green while TCW's own message was still the
  unhelpful `Not possible to fast-forward, aborting` — deleting TCW's message
  would not have failed it. `test_the_board_no_longer_misdirects_to_tcw_init`
  already had the shape: it asserts the old misdirecting message is **not** in
  stderr, naming the thing being replaced, so it cannot pass by accident.
- **Watching a test go red is not enough — read *why* it is red.** Three tests
  in one batch passed before their fix existed, each for a different reason: a
  substring that matched a neighbouring guard's output, `rglob` not descending
  symlinked directories (making three criteria vacuously true), and a fixture
  that broke instead of exercising the guard. Confirm the failure message names
  the defect you are fixing.
- **When a batch fixes a class of bug, grep the other items for the same shape.**
  `Path.exists()` follows symlinks; one item fixed a dangling-symlink case in
  `tcw/store/fs.py`, and a sibling item reintroduced the identical bug in the
  same file days later.
- **One property, one assertion helper.** A family of tests for a single
  criterion calls one named assertion — `_assert_nothing_left_behind(target)` —
  so a sibling that skips it is visible in the diff rather than left to review.
  Three failure-path tests existed for "leaves nothing behind"; two asserted it
  and said so in their names, the third asserted only that it raised, and that is
  the one that was wrong.
