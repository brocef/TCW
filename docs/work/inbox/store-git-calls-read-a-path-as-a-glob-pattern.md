# Store git calls read a path as a glob pattern

Git treats every path it is given as a pattern (a "pathspec"), even after `--`.
`--` only stops a path being read as an option. So a store folder whose name
holds `*`, `?` or `[` matches other folders too.

Nothing stops such a name: `_safe_store_id` (`tcw/store/fs.py`) rejects `..`,
`.`, empty segments, backslashes and NUL, but not glob characters, so
`tcw capabilities add 'a*'` creates a folder named `a*`.

`2026-09-14-delete-a-capability-with-tcw-capabilities-rm` found this in `git_rm`:
removing the capability `a*` also deleted the capability `abc`. It fixed `git_rm`
by passing `--literal-pathspecs`, which also fixes `tcw taxonomy rm` and the work
store's deletes, since they share it.

The other store git calls that take paths were left as they are:

- `git add -- <paths>` in the staging helper and in `git_mv`: a glob-named path
  would stage more than the write touched.
- `git mv -- <src> <dst>` in `git_mv`.
- `git ls-files --error-unmatch -- <source>` in the intake move.

None of these deletes anything, which is why they were not changed with the delete
fix. The likely fix is the same flag on each, or refusing glob characters in
`_safe_store_id`; the second changes which names `add` accepts, so it is a decision
about the model, not only the adapter.
