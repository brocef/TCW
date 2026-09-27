# Outcome: Read item tags normalized and keep non-tag work.tags entries visible

## What shipped

1. **Tests** (`4f5042dc`) — `tests/test_item_tags_read.py`, one test per
   acceptance criterion 1-7, 9 and 10. All failed on main for the reasons the
   spec gives (raw `CLI`, the int `7`, `['C', 'L', 'I']`, a dropped entry, a
   `TypeError` on a mapping entry, `"cli,docs"` registered as `cli-docs`),
   except criterion 7, which guards the unchanged path and passed.
2. **The fix** (`3860facd`) — `read_tags` in `tcw/store/base.py`, used by the
   filesystem item read (`tcw/store/fs.py`); `_registered_tag_entries` treats a
   comma entry as not a tag; `_write_tags` refuses, naming the entry, before
   anything is compared or written.
3. **Documentation** (`0b1cd9c7`) — changelog (the clause documenting the
   regression removed, a Fixed entry added), release notes, `docs/guide/work.md`,
   `skills/work/references/tags.md`, and capability `work/tag-a-work-item`
   (including the out-of-date "matched as written" sentence), declared in
   `capabilities.yaml`.
4. **Review fold-ins** (`b5fa3d01`) — `tags: 0` and `tags: false` are kept as
   text and reported, not dropped; `_validate_tags` refuses a tag holding a comma
   ("holds several tags") instead of normalizing it to one tag, which the web API
   allowed; the release note warns that a hand-typed `"cli,docs"` registry entry
   no longer registers `cli-docs`.

## Test result

Full suite in the worktree, at `b5fa3d01`: 4743 passed, 3 skipped (main before this item: 4727 passed).

Hands-on, in a scratch project with the worktree's `tcw`: an item hand-edited to
`tags: [CLI]` is listed by `tcw work list --tag cli` and shown as `tags: cli`, and
a `pre` command bound to `when: {tags: [CLI]}` runs at `tcw work start`. main's
`tcw work list --tag cli` lists nothing for the same item. With `- 7` added to
`work.tags`, `tcw work tags add web` exits 1 naming `7`, and the file's checksum
is unchanged; `tcw validate` reports the entry.

## What the plan or spec got wrong

- Spec criteria 2 and 3 were wrong as first written: the fixture registered only
  `cli`, so the item's `docs-only` tag made `check` report a problem and
  `--untag cli` refuse. The spec review caught it before any code was written.
- The spec said a falsy value gives `[]`; `0` and `false` are values, not
  absence, and would have been dropped without a report. Fixed at review.
- The spec left `_validate_tags` normalizing `"cli,docs"` into `cli-docs` while
  the new documentation said a comma is never part of a tag. Fixed at review
  rather than filed, being one line.

## Review

- Spec review: criteria 2 and 3 corrected; criterion 9 (mapping entry), the comma
  rule for the registry (criterion 10) and a changelog line on the tracker bug
  type added (see `spec.md` Notes).
- Code review (adversarial-code-reviewer): DONE, nothing blocking. Adopted: the
  falsy-scalar case, the comma refusal in `_validate_tags`, the release-note
  sentence. Not done here: an item holding a kept-as-text tag (`'cli,docs'`,
  `'!!!'`) cannot be removed with `--untag`, because the argument is split and
  normalized; it predates this change and is filed as
  `2026-09-27-let-untag-remove-a-tag-an-item-holds-that-is-not-a-valid-tag`.
