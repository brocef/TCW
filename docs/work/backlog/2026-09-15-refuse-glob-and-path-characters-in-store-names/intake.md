## Inbox manifest

- `2026-09-11-an-absolute-slug-crashes-the-claim-lookup.md`

## Inbox body

# A slug beginning with `/` crashes the claim lookup instead of being refused

## Desired outcome

A store operation handed a path-shaped identifier refuses it with a message,
rather than raising an exception from inside `pathlib`.

## Context

Found by the adversarial review of
`2026-09-09-validate-a-slug-before-the-claiming-lookup-globs-with-it`, which
escaped the slug in `FsWorkStore._claiming_dirs` so it is matched as a name
rather than a glob pattern.

Escaping is not validating. A slug beginning with `/` is still handed to
`Path.glob`, which rejects a non-relative pattern:

```
>>> st.start("/etc/passwd", owner="x")
NotImplementedError: Non-relative patterns are unsupported
```

Both the ordinary and the `--take-over` branches reach it. This is a crash, not
a refusal: the caller gets an exception from `pathlib` naming a concept it never
mentioned, rather than "no such work item".

**It predates that item** — an unescaped absolute pattern fails the same way —
and the escape neither caused nor fixed it.

**Not reachable from the CLI**, which resolves the slug first and prints
`no such work item: /etc/passwd`. It needs the store API. `tcw serve` routes
`POST /api/work/<slug>/actions/start` through `_resolve_work` first and answers
404 when that returns nothing, so it is probably unreachable there too — but the
path parameter is percent-decoded before resolution, and whether a decoded `/`
can survive to the store is not established. Establishing that is part of the
work.

## Constraints

- **`_safe_store_id` is the right mechanism for *this*, and the wrong one for
  what the escaping item fixed.** It rejects a leading `/`, `..`, empty segments
  and NUL — exactly this defect. It does **not** reject `*`, `?` or `[`, which is
  why the escaping item explicitly refused to use it and said so. Do not read
  this item as reversing that finding: the two questions are different, and the
  earlier item's spec records why.
- **Decide whether validation belongs in `_claiming_dirs` or in `start`.** The
  lookup is called from two branches of one function; validating in the caller
  keeps the lookup a lookup, but leaves the next caller to remember.
- **Check the other store entry points for the same shape** before fixing one.
  This was found in the claim path because that is where someone was looking, not
  because it is the only place.

## Supporting resources

- `tcw://work/2026-09-09-validate-a-slug-before-the-claiming-lookup-globs-with-it`
  — its spec's Problem section explains why `_safe_store_id` does not address
  pattern syntax, with the inputs that pass through it unchanged. Read that
  before proposing it here, so the reasoning is inherited rather than re-argued.

## Triage (2026-09-15)

Merged at triage because both entries are about a store identifier (a slug or a
component path) being handed to something that reads it as more than a name —
`Path.glob` in the claim lookup, and git pathspecs in the store's git helpers — and
both name `_safe_store_id` in `tcw/store/fs.py` as one possible place to settle it.
The maintainer asked for items touching the same feature to be combined.

## Folded in: inbox entry `store-git-calls-read-a-path-as-a-glob-pattern.md`

## Store git calls read a path as a glob pattern

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
