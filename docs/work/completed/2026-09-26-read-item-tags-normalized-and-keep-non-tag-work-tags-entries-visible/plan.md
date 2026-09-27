# Plan: Read item tags normalized and keep non-tag work.tags entries visible

Work in a worktree (`tcw work start <slug> --worktree`), with a private venv
pointing at it, so the shared editable install is untouched.

## Tasks

1. **Tests first** — `tests/test_item_tags_read.py` (new). One test per
   acceptance criterion 1-7, 9 and 10, reusing the `node()` helper from
   `tests/test_lifecycle_config_tags.py` (imported, not copied). Items are
   hand-edited by rewriting their `state.yaml`, as a person would. CLI checks go
   through `tcw.cli.main` with `monkeypatch.chdir`, as that file already does.
   Proof: the new tests fail on main for the reasons the spec states (raw `CLI`,
   dropped `7`, `TypeError` on a mapping entry, `cli-docs` accepted), and the
   criterion 7 tests pass.

2. **Reading rule** — `tcw/store/base.py`: add `read_tags(raw) -> list[str]`
   beside `normalize_tag`. `tcw/store/fs.py:4972`: build `WorkItem.tags` with it.
   Proof: tests for criteria 1-5 pass.

3. **Registry entries** — `tcw/store/fs.py`: `_registered_tag_entries` sets aside
   a string holding a comma as not a tag; `_write_tags` raises `ValueError`
   naming the first such entry (config path, entry, "fix or remove it by hand,
   then run this again") before reading `current` into a set. Proof: tests for
   criteria 6, 9 and 10 pass; criterion 7 still passes.

4. **Full suite** in the worktree. Existing tests that assert a raw tag read, or
   the old dropping behavior, are read before being changed: each one changed is
   named in `outcome.md` with the reason.

5. **Documentation Sync** (one pass over the finished diff):
   - `docs/changelogs/upcoming.md` [Any-Code-Change]: delete the clause "and an
     item whose tags were hand-edited into a non-canonical form (`CLI`) no longer
     matches a condition written the same way"; add a Fixed entry for
     `read_tags`, the comma rule, and the `_write_tags` refusal, naming the
     tracker bug type and the display change.
   - `docs/release-notes/upcoming.md` [Public-API]: one plain Fixes line.
   - `skills/work/references/tags.md` [Skill-Driven-Component]: a tag written by
     hand in any spelling is read in its canonical form; `tags add`/`rm` refuse
     while the registry holds an entry that is not a tag.
   - `docs/guide/work.md` "Tags" [Guide-Topic-Change]: the same two sentences.
   - `docs/capabilities/work/tag-a-work-item/description.md`: the capability
     changes in the spec, including replacing "matched as written … matches
     nothing" with the current rule. Then the `capabilities` sub-skill's
     reconciliation.
   - Not firing: `README.md` (its tag line stays true), `docs/guide/jira.md`
     (no tracker command changes), `skills/configure/references/*` (no key
     added or changed in meaning; `work.tags` already holds tags only).

## Verification

- Hands-on, in a scratch node with the worktree's `tcw`: hand-edit an item to
  `tags: [CLI]`, bind a `pre` command to `when: {tags: [CLI]}`, and see it run at
  that transition; `tcw work list --tag cli` shows the item; add `- 7` to
  `work.tags`, run `tcw work tags add docs`, and see the refusal and an unchanged
  file.
- `tcw validate` on this repository, from the merged tree.

## Notes

- Criterion 8 is a documentation check; task 5 covers it and verify reads it.
