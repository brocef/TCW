# Plan — Replace private project names

_Written after the work, as the spec says._

1. Find every mention with `git grep`; classify each as a name to replace or
   the kept Jira site address.
2. Replace names in docs (historical ones: names only), the docstring, and
   the tests; recompute derived test values from the code.
3. Mutation-check each changed test.
4. Full suite in the worktree's own virtual environment.
5. Apply the commit to `main`; rerun the affected test files there.
