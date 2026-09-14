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
