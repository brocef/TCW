# Refined outcome

**Accepted.** `tcw work rename <slug> <new-slug>` gives an open item a new
slug, rewrites what names it on the board, and leaves the old slug resolving.

## Evidence

- **Full suite, bare `pytest` at `301ce93f`:** 5075 passed, 3 skipped, 0
  failed.
- **`tcw:verifier`:** criteria 1-3 and 5-8 met, each with a named test. Its
  own checks added:
  - `parent` rewriting;
  - the graveyard record with the completed folder removed;
  - `edit`, `submit` and `complete` refusing the old slug;
  - a claim in progress refused;
  - a cross-project `tcw://` link validating.
- **Hands-on, in a scratch repository with the branch's code:**
  - the rename made one commit and left a clean tree;
  - `show <old>` followed the rename with a note;
  - `start <old>` refused and named the new slug;
  - the blocker was rewritten;
  - `validate` passed.

## Found at verify, fixed

- **Criterion 4 named `tcw://<project>/<old>` as a blocker.** External
  blockers have never accepted that spelling, with or without a rename; the
  build tested `<project>/<old>`. The criterion was reworded to match.
  `tcw://` links in prose do follow the rename.
- **An initiative child on another board could have uncommitted edits.** The
  rename would have rewritten its `state.yaml` and committed those edits in
  that board's repository. It is now left as it is and named, with the value
  to set by hand (`301ce93f`, with a test).
- **Tests added for a child's `parent` and for a child nested in the renamed
  folder.**

## Deferred

- **Closing GitHub issue #70 waits for publication.** The order is: complete
  the batch → cut the version → push → answer and close, with the reply text
  approved first.
- **Follow-ups filed in the inbox:**
  - the web app's item routes, the tracker commands and the capability drift
    check following renames;
  - external blockers accepting `tcw://` spellings.
