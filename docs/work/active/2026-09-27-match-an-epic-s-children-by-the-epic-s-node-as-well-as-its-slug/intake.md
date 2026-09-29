# Match an epic's children by the epic's node as well as its slug

Left by the review of
`2026-09-09-make-epic-completability-read-the-same-in-every-checkout`
(2026-09-27); it predates that change.

`FsWorkStore.initiative_children` and `resolved_initiative_children` match
`initiative == epic_slug` in every descendant node. Slugs are unique only
within one node, so a descendant can hold its own epic with the same slug (same
date and title); that epic's children — present, or known only from the
graveyard — then count toward the parent's epic, for its completion gate, its
ready-to-close hint and `reconcile`. The gate and the rollup agree with each
other, so nothing looks wrong; both are wrong together.

Fixing it means recording which node the epic lives in with the reference —
`initiative: <project-id>/<slug>` for a cross-node slice, or resolving a bare
`initiative` against the nearest node that holds that epic — which is a design
decision, and the graveyard record's `initiative` would need the same shape.
