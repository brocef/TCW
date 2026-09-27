# Outcome: store names are names, never patterns

## What shipped

- **Code** — `928af577`: `_literal(path)` in `tcw/store/fs.py` passes each
  pathspec argument of the store's git calls as `:(literal)<path>` — `add`,
  `rm`, `rm --cached`, `status`, `commit --`, `ls-files`, `ls-tree`, the
  graveyard `status`, and `tcw work complete`'s `diff --cached` — replacing
  `git_rm`'s `--literal-pathspecs`. `git mv` and `check-ignore` take plain paths
  and reject the prefix; unchanged. `_claiming_dirs` returns no claims for a
  slug that is not one plain path segment.
- **Review fold-in** — `ac69c07c`: the prefix is left off when
  `GIT_LITERAL_PATHSPECS` is already on (git then reads the prefix as part of
  the name, and every write failed); `cli.py` uses the helper. Spec corrected
  (`60214dc4`); `isdecimal` for the setting's digits.
- **Docs**: changelog and release notes.

## Tests

- `tests/test_literal_store_names.py` (10). On the code before the fix:
  `/etc/passwd`, the web `%2F`, capability `a*` staging `abc`, and stage+commit
  of `x[b]`/`q?` failed; the inherited-setting tests failed with the check
  removed. `""`, `a/b`, `..` and the move test guard behaviour that already
  held (git takes an existing folder's exact name literally).
- Full suite on `ac69c07c`: 4592 passed, 3 skipped. Later commits change a
  spec and one comparison; its file passed.
- Hands-on with the worktree's `tcw`: `capabilities set 'a*' --field
  Status=Partial` with an unsaved edit in `abc` staged only `a*`;
  `GET /api/work/%2Fetc%2Fpasswd` against `tcw serve` → 404.

## What the plan or spec got wrong

- The spec named `git log` calls; there are none.
- Criterion 3 ("through a transition commit") could not be met as written: work
  slugs cannot hold `[` or `?`. Tested through the helpers a transition calls.
- The spec's reasoning about hooks missed the reverse case — an inherited
  `GIT_LITERAL_PATHSPECS` makes git read `:(literal)` literally. Fixed.
- The intake's belief that `tcw serve` could not reach the crash was wrong: a
  percent-encoded `/` reached the store.

## Documentation Sync

| Entry | Fired? | Done |
| --- | --- | --- |
| `README.md` | Checked, no | No naming rules there. |
| `docs/guide/jira.md` | No | — |
| `docs/guide/<topic>.md` | Checked, no | `capabilities.md`, `work.md` state no naming rules for these characters. |
| `docs/release-notes/upcoming.md` | Yes | One line. |
| `docs/changelogs/upcoming.md` | Yes | Two Fixed entries. |
| `skills/<component>/SKILL.md` | Checked, no | — |
| `skills/configure/references/` | No | — |

## Autonomous decisions

Run unattended on 2026-09-26 (`extras-autonomous-work`).

- **Refuse glob characters in names, or make git read them literally?** Both
  advisors: literal; refusing changes which names `add` accepts. Chose literal.
- **How: `GIT_LITERAL_PATHSPECS` in `_git` (Codex) or per call (Opus)?** Opus
  showed the variable — and git's own `--literal-pathspecs`, which sets it —
  reaches the hooks `commit`, `merge` and `worktree add` run, where a user hook
  filtering on `'*.py'` would silently match nothing. Chose per path with
  `:(literal)`, which reaches no hook. Codex's points taken: the two calls that
  bypassed `_git`, the empty slug, a serve test.
- **Where to catch a path-shaped slug?** Both: `_claiming_dirs`, the one
  caller-interpolated glob, so every caller is covered.
- **Code review round 1**: NOT DONE — the inherited-setting failure, the inline
  prefix in `cli.py`, spec drift. All fixed. Round 2: DONE; took its `isdecimal`
  note, left `0x1`/`-1` (git reads them as on; nobody sets them).
  Not filed: `start --worktree` on a hand-made glob-named folder (git refuses
  the branch name); work slugs cannot hold these characters.
