# Plan: Refuse instead of crashing when a slug is held by two folders

_Compressed plan, agreed with the maintainer for a small fix._

## Tasks

1. **Tests first** — create `tests/test_duplicate_slug_refusals.py`: a project
   with an item's folder copied from `backlog/` to `active/`; `tcw work list`
   exits 0 with other rows intact and the duplicated rows marked "held by 2
   folders" (criterion 1); `start` and `submit` exit 1 with no `Traceback` (2);
   `show` names both folders and `tcw validate` (3); `edit <other> --blocked-by
   <slug>` exits 1, no traceback, mentions `tcw validate` (4); `tcw validate`
   still prints the "held by 2 folders" problem (5). Red before tasks 2-3.
2. **Store and entry point** — `tcw/store/fs.py` `_find`: message names each
   folder via `_shown_path` and points at `tcw validate`, re-walk unchanged.
   `tcw/cli.py` `main`: catch `MultipleMatch` like `ValueError`.
   `tcw/store/base.py` (~4342): the remedy for `_HELD_TWICE` points at
   `tcw validate`. Update tests pinning `slug resolves to` wording
   (`grep -rn "resolves to" tests/`).
3. **Board** — `tcw/work/cli.py` `_render_board_item`: catch `MultipleMatch`
   around the artifact read; print `!` for stages and a trailing
   ` | held by N folders — see tcw validate` segment. Then re-run the sweep by
   hand over every `tcw work` verb that takes a slug, and over `tcw serve`'s item
   route if it can be reached quickly; anything still crashing outside the CLI
   is reported in `outcome.md`, not fixed here.

## Documentation Sync

- `docs/changelogs/upcoming/<slug>.md` [Any-Code-Change] — `## Fixed`.
- `docs/release-notes/upcoming/<slug>.md` [Public-API].
- Guides: `grep -rn "held by\|resolves to" docs/guide skills` — update any text
  quoting the old message; otherwise no trigger fires.

## Verification

- The scratch-project reproduction by hand, all verbs, before and after.
