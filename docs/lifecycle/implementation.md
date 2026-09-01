<!-- Bound to the `implement` stage of `tcw work`; see `tcw-config.yaml`.
     Read as a continuation of TCW's built-in stage instructions, not on its own. -->

# Implementation rules

_Applies at `implement`. The design rules that govern what you build are in
[`abstraction.md`](abstraction.md), bound at `spec` and `plan`._

- Each component depends on an abstract **store interface** (`TaxonomyStore`, `WorkStore`, …) that the CLI and any skills talk to. Ship the **filesystem adapters** (`FsTaxonomyStore`, `FsWorkStore`) only; keep remote adapters (e.g. `JiraWorkStore`) possible but unbuilt. Never add an interface method that only the FS adapter could honor (run the litmus test first).
- The three components are **one system**: taxonomy is the nouns, capabilities the user stories (what a user can do), work the changes (to capabilities, machinery, or the project itself). They link by loose, one-directional pointers (capability→term, work→capability/term) and never duplicate each other.
- Python with type hints; pytest over `tmp_path` git repos. Use the ABC + adapter pattern for stores; extract the shared tree-store core only once two components are real (don't pre-abstract).
- **Skill authoring (progressive disclosure):** a `skills/<name>/SKILL.md` is a **thin router** — keep always-relevant judgment inline (the core lifecycle, the gates) and push genuinely rare sub-procedures into `skills/<name>/references/*.md` read on demand, each reached by a clear gate condition in the router (the `tcw-plugin` and `tcw-work` skills are the pattern). Only split once a skill's conditional detail is large enough to earn the indirection — for ~50-line, mostly-always-relevant skills it's a no-op; leave them inline.

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
- **One property, one assertion helper.** A family of tests for a single
  criterion calls one named assertion — `_assert_nothing_left_behind(target)` —
  so a sibling that skips it is visible in the diff rather than left to review.
  Three failure-path tests existed for "leaves nothing behind"; two asserted it
  and said so in their names, the third asserted only that it raised, and that is
  the one that was wrong.
