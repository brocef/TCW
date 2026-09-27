# Plan: let a broken extends reach the user instead of find_node answering no node here

## Tasks

1. **Tests first** in `tests/test_store_provisioning.py` (which already holds
   the find_node "no node here" tests near line 1383): criteria 1-3, each
   message assertion paired with an assertion that "no tcw … node here" is
   absent. Tighten `tests/test_legacy_store_config.py:311-317` (criterion 4).
   Proof: criteria 1, 2, 4 red on the current tree; criterion 3 green.
2. **Fix** `find_node` in `tcw/store/fs.py`. Proof: task 1 green; full suite.
3. **File the follow-up item**: `init` does not honour a configured tree-store
   path, so "run `tcw init`" is wrong advice for a configured-but-missing
   `taxonomy.path` / `capabilities.path`.

## Documentation Sync

- `docs/changelogs/upcoming.md` [Any-Code-Change], `docs/release-notes/upcoming.md`
  [Public-API]: one Fixed entry each.
- Guides/skills/README/configure: expected not to fire; re-checked on the diff.

## Verification

Hands-on: scratch node with `taxonomy.extends: [ghost]`; run `tcw taxonomy list`
from the worktree's install and read the message.
