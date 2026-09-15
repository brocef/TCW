## Inbox manifest

- `the-capability-completion-gate-ignores-a-configured-capabilities-location.md`

## Inbox body

# The capability completion gate ignores a configured capabilities location

`capability_gate` in `tcw/work/recursion.py` decides whether a node has a
capabilities ledger by looking for `<node root>/docs/capabilities`:

```python
caps_root = st.node_root / "docs" / "capabilities"
if not caps_root.is_dir():
    return []
```

A node can put its ledger elsewhere with `capabilities.path`, or in another
repository with a `capabilities.repository` block. On such a node the directory
test fails and the gate returns "no problems" without reading `capabilities.yaml`
at all, so every declaration passes: a `new:` capability still `Missing`, a
`changed:` path that no longer resolves, and (since
`2026-09-14-delete-a-capability-with-tcw-capabilities-rm`) a `removed:` path that
still exists.

`skills/tcw-capabilities/SKILL.md` already says never to compose a store path from
the node root, and `docs/lifecycle/implementation.md` describes the same mistake
for the work store (issues #15 to #18).

Found by the Codex review of
`2026-09-14-delete-a-capability-with-tcw-capabilities-rm`, which left it alone as
a defect that predates that change.

Likely direction: ask the store whether the node has a capabilities component
(open it and treat "no capabilities component" as the pass case) instead of
testing a hard-coded directory. A regression test needs a node whose
`capabilities.path` points outside `docs/capabilities`.

## Triage (2026-09-15)

Merged at triage because both parts concern how an item's capability declarations
reach the Definition-of-Done gate: the gate's test for a ledger
(`capability_gate` in `tcw/work/recursion.py`), and the read of an item's
`capabilities.yaml` whose parse-error sentinel feeds that gate
(`FsWorkStore._read_item`). The maintainer asked for items touching the same feature
to be combined.

## Folded in: inbox entry `2026-09-14-an-unreadable-capabilities-yaml-breaks-the-whole-board.md`

## An unreadable `capabilities.yaml` breaks the whole board

Found by the adversarial review of
`2026-09-12-surface-an-item-s-tracker-binding-in-the-board-the-projection-and-the-web-app`.
Not fixed there, because that item changed how `tracker.yaml` is read and this is
an older problem in the code beside it.

### What happens

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

### Also worth checking

`_json_safe` in `tcw/work/projection.py` walks a `capabilities` value for
`show --json`. A chain of YAML anchors expands exponentially when walked, so a
small hand-written `capabilities.yaml` may make `show --json` and `tcw serve` hang.
Not reproduced.
