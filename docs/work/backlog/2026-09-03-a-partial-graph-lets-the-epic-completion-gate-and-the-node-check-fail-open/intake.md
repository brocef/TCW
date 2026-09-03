Found by an adversarial review of the graph work, 2026-09-03.

1. **The epic completion gate fails open.** `initiative_children` walks
   `descendant_nodes`, which calls `require_valid()`. Before this work an
   unreachable child made that raise, so the gate errored loudly. Now it returns
   a shorter list and `complete` concludes there are no open children: an epic in
   node `a` whose open slices live in child `d` — whose repository is not in this
   checkout — completes, stranding them. `epic_completable` returns True from
   `backlog` for the same reason.

   The `start`-side epic lookup got `_incomplete_graph_note()` for exactly this
   hazard. The completion gate, which is the one with a destructive consequence,
   did not.

2. **A directory that is not a tcw node passes `require_valid()`.**
   `_read_config` records a missing config as an unreachable edge, and
   `_unreachable_edge` returns early when `project_id` is None — which is the
   case for the current node's own config, since `_load_graph` calls
   `_visit(..., declared_id=None)`. So nothing is recorded at all:
   `check()` is empty, `require_valid()` passes, and every helper built on it
   answers "no parent, no children, valid" for a directory that is not a node.
   Before this work the same call raised. The comment justifying the fail-open
   argues it for *targets*; the code applies it to the root too.
