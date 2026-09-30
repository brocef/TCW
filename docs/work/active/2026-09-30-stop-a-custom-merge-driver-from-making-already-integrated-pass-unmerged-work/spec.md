# Spec: Stop a custom merge driver from making --already-integrated pass unmerged work

_Compressed spec, agreed with the maintainer for a small fix._

## Capability changes

None.

## Problem

`branch_integration` (`tcw/store/fs.py:1123`) decides whether
`tcw work complete --already-integrated` may delete a work branch. Its second
test counts a branch as merged when `git merge-tree --write-tree HEAD <branch>`
produces `HEAD`'s own tree (`tcw/store/fs.py:1165-1167`), which is how a squash
or rebase merge is recognised.

**Confirmed at spec, git 2.54:** `merge-tree` runs a repository's custom merge
drivers. With `* merge=ours` in `.gitattributes` and
`merge.ours.driver=true` configured, a branch that changed a line `HEAD` also
changed produces `HEAD`'s tree exactly, exit 0 — the check passes, and the branch
and its unmerged edit are deleted. The same happens when the attribute comes from
`.git/info/attributes` instead, which nothing in the tree shows.

Ways of switching that off, tested at spec:

| Approach | Result |
|---|---|
| `git --attr-source=<empty tree>` | Ignores `.gitattributes` in the tree, but **still reads `.git/info/attributes` and `core.attributesFile`** — hole stays open. |
| `-c merge.<name>.driver=` (empty) | Git errors "cannot run" and records a conflict: closed, but noisy. |
| `-c merge.<name>.driver=false` | A conflict wherever the driver would have decided a file (exit 1): **closed, whatever file set the attribute.** |
| `-c merge.<name>.driver="git merge-file %A %O %B"` | Closes the hole, but also turned a genuine squash merge into a conflict that git's built-in merge resolves cleanly — no better than `false`, and less predictable. |

## Goals

1. A branch whose changes a custom merge driver would discard is never reported
   as integrated by the trial-merge test.
2. A branch merged by a merge commit or fast-forward still passes (the ancestor
   test, `tcw/store/fs.py:1161-1162`, which drivers cannot affect).
3. When the trial merge is refused and the repository defines custom merge
   drivers, the refusal says so, so the user knows why a branch they did squash
   might be refused and what to do (the existing way out: delete the branch
   yourself and re-run).

## Non-goals

- TCW's own merge-back (`merge_worktree`): that is a real merge, and honoring
  the repository's merge configuration there is what the user configured.
- Built-in drivers (`text`, `binary`, `union`) and `-merge`: `binary` and `-merge`
  already give a conflict (fail closed) and `union` keeps both sides' lines, so
  none can hide a branch's change.

## Design

Fail closed, as the function already does for every other doubt: run the trial
merge with **every configured custom merge driver replaced by `false`**, so any
file a custom driver would decide becomes a conflict and the test answers "not
shown to be merged".

- The driver names come from `git config --null --name-only --get-regexp
  '^merge\..+\.driver$'` in the node's repository, which covers repository,
  global, system and included configuration.
- The overrides are passed through git's `GIT_CONFIG_COUNT` /
  `GIT_CONFIG_KEY_<n>` / `GIT_CONFIG_VALUE_<n>` environment variables rather than
  `-c`, so a driver name holding `=` or spaces cannot be misparsed. These exist
  since git 2.31; the check already requires 2.38.
- `merge.default` needs nothing of its own: it names a driver, and a custom one
  is overridden like any other.
- The trade-off, stated in the refusal and the docstring: in a repository with
  custom drivers, a squash-merged branch that touched a file a custom driver
  governs, which the main line also changed, is refused and must be deleted by
  hand. Merge-commit and fast-forward merges are unaffected.

## Acceptance criteria

1. The reproduction above (in-tree `.gitattributes`): `branch_integration`
   returns a refusal, and `tcw work complete --already-integrated` exits 1 with
   the branch still present.
2. The same with the attribute only in `.git/info/attributes`.
3. A branch squash-merged into `HEAD` in a repository with **no** custom
   drivers still passes, as today.
4. A branch merged with a merge commit in a repository **with** a custom
   driver still passes.
5. The refusal in criterion 1 mentions that the repository defines custom merge
   drivers.

## Risks

- A repository whose custom driver is on every file (`* merge=foo`) can no
  longer have squash-merged branches confirmed by the trial merge. Accepted:
  that is exactly the configuration that can hide work, and the way out exists.
- `get-regexp` with no matches exits 1; that must read as "no drivers", not as
  an error.

## Notes

- Open question raised by the adversarial review of #72; answered yes at spec.

## Amended after spec review (2026-09-30)

An adversarial spec review ran before implementation. Accepted:

- **Environment variables lose to an inherited `GIT_CONFIG_PARAMETERS`.** Git
  exports that variable to anything run under `git -c …` (a hook, an alias), and
  its entries beat `GIT_CONFIG_COUNT` ones, re-opening the hole (checked: `-c` on
  the command line wins, exit 1). The overrides are therefore passed as `-c
  merge.<name>.driver=false`, last on the command line. A driver name containing
  `=` cannot be written with `-c`; if one exists the trial merge is not trusted
  at all (fail closed).
- **`get-regexp` exiting with anything other than 0 or 1** (a malformed config)
  fails closed too.
- **The refusal depends on the exit code, not the tree.** With `false` as the
  driver git keeps `HEAD`'s side, so the written tree still equals `HEAD`'s; only
  exit 1 refuses. The docstring says so, so a later "compare trees only" change
  does not silently re-open the hole.
- **The non-goal was wrong about built-in names.** A user can redefine them
  (`merge.union.driver=true`); the design already covers that, since every
  configured name is overridden. Only the reasoning in Non-goals was wrong.
- **Criterion 5 means any refusal** of the trial merge in a repository that
  defines custom drivers; git cannot cheaply say which file a driver governed.
