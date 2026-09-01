# Re-anchor a relative work.path at the node's counterpart inside the main worktree

A tcw node that is **nested inside its repository** cannot express its
`work.path` relatively if anyone ever works in a linked git worktree. Standing
in the worktree, the store resolves to the wrong directory and `tcw work`
reports `no tcw work node here — run tcw init in the project folder`. The same
config works from the primary checkout.

The requester's case is a monorepo whose packages are each a tcw node with a
work store kept outside the repository. What is wanted is for that path to be
expressible relatively, so a checked-in `tcw-config.yaml` does not have to
carry a machine-specific absolute path. Today the only workaround is to write
the absolute path, which is what prompted the report.

## Scope

The ask is that a **nested node resolve its relative `work.path` to the same
store from a linked worktree as from the primary checkout**. Confirmed by
reproduction to affect two shapes, both in scope:

1. A relative path that escapes the checkout (`../../../docs/x/work`) — the
   shape reported.
2. A relative path that stays inside it (`docs/work`) — not reported, same
   cause, and arguably worse because it resolves to a plausible-looking
   directory rather than failing outright.

A node **at** the repository root is unaffected in both shapes and must stay
that way.

## Out of scope

A separate divergence surfaced while reproducing this, and the requester chose
to leave it alone: for a node at the repository root, an *explicit* relative
`work.path: docs/work` re-anchors to the primary checkout, while the
*identical* default (no `work.path` at all) does not, giving each worktree its
own store. Whether an explicit relative path should re-anchor at all is a real
question, but it is not this item's, and answering it would change behaviour
for users who are not hitting this bug. Record it; do not fix it here.

## Notes

Reference material: asked; none provided beyond what the report and this
repository already contain — the requester confirmed the material collected on
`intake.md` is sufficient.

The requester is also the reporter of the originating GitHub issue, so the
request and the report are one voice here; that is not the usual case for an
issue-derived item.

The report proposes a specific patch and a specific pair of edit sites. Both
are recorded on `intake.md` as the reporter's words, and one of the two sites
does not exist in this tree. Treat the proposal as evidence for `spec`, not as
a decision `spec` must accept.

## References

- GitHub issue [#26](https://github.com/brocef/TCW/issues/26) — the originating
  report, with the reporter's reproduction and proposed patch.
- `tcw/store/fs.py:2778` — `FsWorkStore._local_root`, the only re-anchoring site
  in this tree and where the behaviour is decided.
- `tcw/store/project.py:56` — `worktree_anchors`, which already returns the
  current worktree top alongside the main root; the sub-path this needs is
  available and currently discarded.
- `tests/test_environment_hardness.py` — the worktree fixtures. `monorepo_worktree`
  there is documented as the layout a naive "always re-anchor" fix breaks, so it
  is the guard any change has to survive. No test currently sets a relative
  `work.path` at all.
