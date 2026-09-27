# Refined outcome: Read item tags normalized and keep non-tag work.tags entries visible

## Decision

Accepted by the user on 2026-09-27, after the verify assessment.

## Evidence

- Verifier (tcw:verifier): all ten acceptance criteria met, each by a named
  passing test; documentation sync done as planned; `outcome.md` matches the
  commits. Its one open point — a follow-up the outcome said was filed but was
  not yet — was fixed by filing it (below).
- Full suite in the worktree at `b5fa3d01`: 4743 passed, 3 skipped.
- After merging main (`583d1a8e`, which brought only work-item documents):
  `tests/test_item_tags_read.py` and `tests/test_work_tags.py` 57 passed;
  `tcw validate` OK.
- Hands-on in a scratch project: a hand-typed `CLI` tag is listed by
  `list --tag cli`, shown as `cli`, and triggers a `pre` command bound to
  `when: {tags: [CLI]}`; main's `tcw` lists nothing for the same item. A `7` in
  `work.tags` makes `tags add` refuse with the file unchanged.

## Capability ledger

`work/tag-a-work-item` changed as the spec said: its description now says a tag
written by hand is read in canonical form, a comma is reported in a condition
or `work.tags`, and `tags add`/`rm` refuse over a non-tag entry. The out-of-date
"matched as written" sentence is gone. Status stays Supported.

## Deferred

- `2026-09-27-let-untag-remove-a-tag-an-item-holds-that-is-not-a-valid-tag` — an
  item holding a tag that is not valid (`'!!!'`, `'cli,docs'`) cannot be cleaned
  up with `--untag`. Predates this change.

## Closeout

Complete, then merge the branch into main locally. No push and no version cut:
the changelog and release-note entries wait in `upcoming.md` for the next
bugfix release. No GitHub issue is attached to this item.
