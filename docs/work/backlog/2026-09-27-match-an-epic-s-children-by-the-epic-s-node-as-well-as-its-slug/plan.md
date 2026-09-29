# Plan — Match an epic's children by the epic's node as well as its slug

## Tasks

1. **Write the tests first.** Create `tests/test_initiative_node_qualified.py`,
   with one test per acceptance criterion from 1 to 6. Run them against the
   current code, and confirm that criteria 1, 2, 3, 5 and 6 fail. Criterion 4
   guards backward compatibility, so it passes both before and after the
   change.
2. **Store.**
   - In `tcw/store/base.py`, add `qualify_initiative`.
   - In `tcw/store/fs.py`:
     - add `_initiative_holder`, `qualify_initiative` and the matching helper;
     - rebuild `initiative_epic`, `initiative_slices`, `_graveyard_initiative`
       and `resolved_initiative_children` on those;
     - qualify the value in `create_work`, in `update_work` (including its
       resolved-item check), and in inbox accept.
3. **Writers outside the store.**
   - `delegate`: always qualified, refusing a slug it cannot resolve.
   - `escalate`: qualified by the parent's store.
   - The `tracker import` re-run check.
   - The indentation in `_render_descendant_boards`.
4. **Mutation checks.** Remove each piece in turn and confirm its test goes
   red: the holder rule in the slice walk, the graveyard resolution,
   delegate's qualification, and qualification at `create`.
5. **Full suite**, run in the item's own venv.

## Documentation Sync

- `docs/changelogs/upcoming/<slug>.md`: Fixed and Changed.
- `docs/release-notes/upcoming/<slug>.md`: the new stored form, and the fix.
- `docs/guide/work.md`: update the cross-node epic section (about lines
  577–640) to cover both forms and when each is written.
- `skills/work/references/cross-node-deltas.md` and `commands.md`: say that
  `--initiative` accepts `<project-id>/<slug>`, and that `delegate` records
  it.
- README and `configure`: not triggered, because no command or configuration
  key changes.

## Verification

- Every acceptance criterion is covered by a test.
- A hands-on run on a scratch two-node graph drives the real CLI through
  `delegate`, `inbox accept`, `list` and `complete`.
