# Plan: Name the item and file when editing an item whose state.yaml cannot be read

_Compressed plan, agreed with the maintainer for a small fix._

## Tasks

1. **Tests first** — create `tests/test_damaged_state_on_edit.py`: a project with
   an item whose `state.yaml` is `key: [unclosed`; `tcw work edit` with `--tag`,
   `--title`, `--priority`, `--blocked-by` each exit 1 with the slug, the
   `docs/work/backlog/<slug>/state.yaml` path and `tcw validate` in stderr, and the
   file unchanged (criteria 1-2); `start` refuses with path and pointer (3);
   `tcw validate` names the file (4); a broken `tcw-config.yaml` read through
   `load_yaml` reports its path, not `<unicode string>` (5). Red before task 2.
2. **Code** — `tcw/store/fs.py`:
   - `load_yaml`: parse a `io.StringIO` of the file's text whose `name` is the
     path, so PyYAML's position lines name the file.
   - `_require_readable_state`: instance method; message
     `<slug>: <shown path> cannot be read (<reason>); fix or replace it before
     changing the item — \`tcw validate\` lists every item it cannot read`.
   - `_set_fields_at` and `update_work`: call it before the strict read.
   Fix any existing test that pinned the old wording (`grep -rn "cannot be read"
   tests/`, `grep -rn "unicode string" tests/`). Proof: task 1 green, full suite
   green under bare `pytest`.

## Documentation Sync

- `docs/changelogs/upcoming/<slug>.md` [Any-Code-Change] — `## Fixed`.
- `docs/release-notes/upcoming/<slug>.md` [Public-API] — user-visible message change.
- README, guides, skills, configure references: no trigger fires (no command,
  key or documented behavior changes); confirm by grep for the old message.

## Verification

- By hand in a scratch project: the reproduction from the request, before/after.
