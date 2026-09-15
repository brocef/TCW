# An unreadable `capabilities.yaml` breaks the whole board

Found by the adversarial review of
`2026-09-12-surface-an-item-s-tracker-binding-in-the-board-the-projection-and-the-web-app`.
Not fixed there, because that item changed how `tracker.yaml` is read and this is
an older problem in the code beside it.

## What happens

`FsWorkStore._read_item` (`tcw/store/fs.py`) reads every item's
`capabilities.yaml` when it exists and catches only `yaml.YAMLError`. The reviewer
confirmed that a `capabilities.yaml` which is not valid UTF-8 makes `tcw work list`
exit 1 with "'utf-8' codec can't decode" and print no rows at all — one item's
file takes down the board for every item. A directory with that name, a file with
no read permission, or nesting deep enough to raise `RecursionError` in the parser
should behave the same way, by the same reasoning, though only the UTF-8 case was
reproduced.

The tracker item fixed the identical shape for `tracker.yaml` by turning each read
failure into a value reported on that item (`unreadable_binding` in
`tcw/store/base.py`). `capabilities.yaml` already has a sentinel for a parse error,
`{"_tcw_parse_error": ...}`, which `declared_capabilities` turns into a
`SidecarError` so the Definition-of-Done gate fails closed; widening the caught
exceptions to feed that same sentinel looks like the whole fix.

## Also worth checking

`_json_safe` in `tcw/work/projection.py` walks a `capabilities` value for
`show --json`. A chain of YAML anchors expands exponentially when walked, so a
small hand-written `capabilities.yaml` may make `show --json` and `tcw serve` hang.
Not reproduced.
