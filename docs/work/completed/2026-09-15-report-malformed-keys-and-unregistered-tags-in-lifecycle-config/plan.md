# Plan: report malformed keys and unregistered tags in lifecycle config

## Tasks

1. **Join sites** (criterion 7). Tests first in `tests/test_lifecycle_validation.py`:
   one parametrized test per site with an int key and a mixed key set. Fix the
   six sites in `tcw/store/base.py`.
2. **Conditions** (criteria 1-2). Tests first in `tests/test_lifecycle_validation.py`
   and `tests/test_lifecycle_policy.py`. Normalize in `_parse_condition`, refusing
   commas and empty results.
3. **Registration check** (criterion 3). Test first; add an adapter-side check
   in `FsWorkStore.lifecycle_problems` walking every binding's condition.
4. **Tag readers** (criteria 4-5). Tests first; `registered_tags`,
   `_declared_plan_stages`, `_validate_tags` in `tcw/store/fs.py`; report an
   unnormalizable registered entry from `check`.
5. **`list --tags`** (criterion 6). Test first; note in `tcw/work/cli.py`'s list.
6. **`skill:` shape** (criterion 8). Test first; in `_parse_binding` or
   `lifecycle_problems`.

## Documentation Sync

- Changelog, release notes: Fixed entries plus the stated behavior change.
- `skills/configure/references/` [Configuration-Key-Change]: the lifecycle
  document — tags in `when` are normalized and must be registered; a `skill:`
  value's existence is not checked.
- `docs/guide/` lifecycle guide [Guide-Topic-Change]: same, if it describes `when`.

## Verification

Hands-on: scratch node with `when: {tags: [CLI]}`, `[clii]`, a `1:` key and
`skill: "my skill"`; run `tcw validate` from the worktree's install and read the
report; `tcw work list --tags nope`.
