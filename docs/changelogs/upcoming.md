# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category, with commit hash ranges so entries trace back to source.

## Added

<changes starting-hash="64d0746" ending-hash="10fe40f">

- Added optional `effort` and `complexity` fields to work items
  (`WORK_LEVELS = low|medium|high|very-high`): two `WorkItem` fields persisted
  through the generic `state.yaml`/`set_field` path (no store-signature change),
  `--effort`/`--complexity` flags on `tcw work new` and `tcw work edit`
  (argparse `choices=`), and display in `tcw work show`. The `tcw work list`
  output is unchanged. FS reads use `state.get(k) or ""` so a hand-edited null
  key degrades to `""`.

</changes>
