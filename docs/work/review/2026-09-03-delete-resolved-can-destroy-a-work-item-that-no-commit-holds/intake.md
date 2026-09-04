Found by an adversarial review of the retention work, 2026-09-03. Every case
below was reproduced by running the code.

1. **The gitignore interlock never fires on the `tcw work delete` path.**
   `_require_deletable` is called only from `_effect_transition_locked`.
   `delete_resolved` — which `_delete` and `_auto_delete` reach directly — does
   not call it. On a default node with the shipped `docs/work/completed/*`
   rules: complete an item, add `work.retain.completed: false`, run
   `tcw work delete <slug>` → exit 0, folder removed, message names a commit
   that does not contain the item. Gone from disk and from history. There is no
   `--confirm` on that verb.

2. **Nothing checks the item was committed before the removal.** With
   `work.auto-commit-transitions: false`, the *automatic* path destroys it:
   `tcw work complete --resolution done --confirm` exits 0, prints "its
   documents remain in commit …", and `git log --all --name-only` never
   mentions the slug. A narrower variant reaches the same end with auto-commit
   on, when the item's own files are individually gitignored and
   `git_commit_result` legitimately reports nothing to commit.

3. **The graveyard read-modify-write happens outside `_graveyard_lock`.**
   `_effect_transition` takes that lock precisely to serialize this window.
   Interleaving a second store's `complete("beta")` between
   `delete_resolved("alpha")`'s read and write leaves `beta` in `completed/`
   with no tombstone — the state `_write_tombstone`'s own docstring calls out,
   and the one `_unique_slug` cannot protect against.

4. **`_require_writable_graveyard` is skipped too.** A list-shaped graveyard is
   reset to a single entry, destroying every other record. An unparseable one
   raises `yaml.ParserError`, which is not in `_ERRORS`, so the command exits
   with a traceback — after the `rmtree` has already run.

5. **A hook that moves the item away leaves the removal uncommitted.**
   `_get_now` returns None, so `status` is "", so the item's path is left out of
   the second commit's pathspec. The commit carries only `graveyard.yaml`, the
   working tree keeps an unstaged deletion, and `_publish_after_transition`
   pushes a remote that still holds the item the store deleted — which the
   comment three lines above says publication exists to prevent.
   `test_a_binding_that_moves_the_item_away_is_not_an_error` asserts no error
   and never checks the commit.
