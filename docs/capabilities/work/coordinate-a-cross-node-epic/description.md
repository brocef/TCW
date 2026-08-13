As a user, I coordinate work that spans several projects by creating an **epic**
in the coordinating project — `tcw work new "<title>" --epic` — and pointing the
individual slices at it from wherever they live. A slice declares its owner with
`tcw work new "<title>" --initiative <epic-slug>`, or later with
`tcw work edit <slug> --initiative <epic-slug>`; `--initiative ""` clears it. The
back-pointer is one-directional and loose: the epic holds no list of its children,
so a slice can be added, moved, or dropped without editing the epic.

Slices may live in child projects, and TCW finds them through the registered
graph rather than the filesystem — see
[Inspect the node topology](tcw://C/work/inspect-the-node-topology).

The relation is **gated**, not merely advisory:

- A slice refuses to start until its epic is active: *"Cannot start work item
  &lt;slug&gt; before epic &lt;epic&gt; is active."* Starting on a plan nobody has
  committed to is the mistake this prevents.
- An epic refuses to complete while any slice is still open, naming the offenders.

`--force` overrides both, for the case where the relationship cannot be resolved
or I am deliberately deviating.

A slice counts as closed when it is **resolved** — completed *or* discarded. A
slice nobody will ever do does not hold its epic open, which is what stops
abandoned work from pinning an initiative open forever.

Once every slice is resolved the epic is flagged `ready-to-close` on the board and
in its rollup, and it may be completed **directly from `backlog`** without ever
being started. A coordinator epic that only ever tracked other people's work does
not need a throwaway `start` to close it. The Definition-of-Done and capability
gates still apply on that route — the shortcut is to the status path, not past the
checks. An epic with *no* slices at all is never ready to close: nothing resolved
is not the same as everything resolved.

To refresh the epic's own summary of its slices, see
[Reconcile an epic rollup](tcw://C/work/reconcile-an-epic-rollup).
