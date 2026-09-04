Found by two adversarial reviews, 2026-09-04. Both reproduced.

1. **Three commands report a declared-but-unreachable project as never
   declared.** `registered_parent` and `registered_children` read
   `registry.parent()` / `registry.children()`, both filtered through `_by_id`,
   from which unreachable projects are absent by construction. So in a checkout
   missing its parent's repository:

   ```
   $ tcw work nodes
   node:   child-proj
   parent: (none — root)
   children: (none — leaf)
   $ tcw work escalate "Test"
   tcw work escalate: no parent node to escalate to (this is the root)
   $ tcw validate
   … connected project 'parent-proj' is declared but not reachable in this
     checkout (…/parent)
   ```

   This contradicts three things written by the same work: the comment above
   `child_nodes` (*"What none of them may do is imply the absent node was never
   declared"*), the comment in `escalate` (*"telling a user the node is the root
   when it plainly has a parent sends them to fix the wrong thing"* — its added
   branch handles only the storeless case), and `README.md` (*"A command that
   does need the absent project says which one and where it was declared, rather
   than reporting that it was never registered"*). `delegate` has the same hole.

2. **A mistyped reciprocal locator is now reported by nothing at all.**
   `_points_elsewhere` returns False when the reciprocal target is absent ("an
   absent target cannot answer the question"), and `unreachable()` drops any
   entry whose id is in `_by_id`. A locator typo pointing at a path that does not
   exist satisfies both: reciprocity abstains, and the unreachable record is
   filtered out because the project is present via the other route.

   `a` declares `children: {b-project: ../b}`; `b` declares
   `parent: {a-project: ../TYPO-a}`. From `a`: no problems, nothing unreachable
   (on `main`: two problems, including the non-reciprocal locator). From `b`:
   no problems and `parent()` answers None, so `tcw work escalate` reports no
   ancestor while the config plainly names one.

   `_cmd_validate`'s comment claims unreachable entries "are also how a genuine
   typo in a locator now surfaces". For this shape they are not.
