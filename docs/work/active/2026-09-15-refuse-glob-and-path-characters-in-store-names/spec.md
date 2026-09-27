# Spec: store names are names, never patterns

## Capability changes

None to the ledger.

## Problem

- `FsWorkStore._claiming_dirs` (`tcw/store/fs.py`) escapes the slug before
  `Path.glob`, but a slug starting with `/` is still a non-relative pattern:
  `get`, `start` and `submit("/etc/passwd")` raise `NotImplementedError`.
  `tcw serve` reaches it: `_decode_path_param("%2Fetc%2Fpasswd")` is
  `/etc/passwd`, and with descendants off `_resolve_work` does not check
  existence first.
- The store's git calls pass paths as pathspecs. Only `git_rm` and one
  `ls-files` use `--literal-pathspecs`. `git add` (`git_stage`, `git_mv`),
  `git rm --cached`, `git status`, `git commit -- <paths>`, `git ls-files`,
  `git log` / `git ls-tree` / `git diff` over an item's path — each matches other
  folders when a name holds `*`, `?` or `[`. Reproduced: `tcw capabilities set
  'a*' …` staged `abc/meta.yaml`. Two calls bypass `_git`: the graveyard
  `git status` in `fs.py` and `git diff --cached` in `tcw/work/cli.py`.

## Goals

1. `_claiming_dirs` returns `[]` for a slug that is not one plain path segment
   (empty, absolute, holding `/` or `\`, `.`, `..`, or NUL): no item can have
   that name, so `get` answers `None` and `start`/`submit` "no such work item".
   The glob escaping stays.
2. Every store git argument that git reads as a pathspec is passed as
   `:(literal)<path>`, per path, through one helper. `git mv`, which reads plain
   paths and rejects the prefix, is unchanged. Nothing is set in the
   environment, so no git hook TCW's commits run sees a changed setting.
3. The two direct git calls get the same treatment.
4. Names with `*`, `?`, `[` stay legal (no model change).

## Non-goals

- Refusing glob characters in names: a change to which names `add` accepts,
  and existing folders would become unreachable.
- Git calls outside the store (`tcw/tracker`, worktree set-up), which take no
  store names.

## Acceptance criteria

1. `get("/etc/passwd")` → `None`; `start`/`submit` → "no such work item";
   `GET /api/work/%2Fetc%2Fpasswd` → 404, not 500. Same for `""` and `a/b`.
2. With capabilities `a*` and `abc`, and an uncommitted edit in `abc`: writing
   `a*` stages and commits only `a*`; `abc`'s edit stays unstaged.
3. The same for a work item slug holding `[` and `?` through a transition commit.
4. A taxonomy or capabilities move (`git_mv`) of a glob-named folder moves only
   it.
5. Existing tests pass; full suite passes.

## Notes

- Advisors (2026-09-26). Both: fix (A) in `_claiming_dirs`; no store call relies
  on pathspec globs; add a serve test. Split on (B): Codex — set
  `GIT_LITERAL_PATHSPECS` inside `_git`; Opus — per call, because the variable
  (and git's own `--literal-pathspecs`, which sets it) reaches the hooks `commit`,
  `merge` and `worktree add` run, where a user hook filtering on `'*.py'` would
  silently match nothing. Chose per path with `:(literal)`, which reaches no
  hook; see `outcome.md`.
