Found by an adversarial review of the provisioning work, 2026-09-03.
Reproduced.

1. **Transitivity only works in the state where nothing is present.** The skip
   that stops `tcw provision` re-fetching a project the checkout already has
   also stops the walk reading that project's own declarations: only the two
   branches that touched the checkout call `enqueue()`. And
   `_declared_nodes_in_graph` enumerates `root + ancestors + descendants`, not
   the whole graph, so a present project that is neither is never read either.

   Orchestrator `o` with children `a` and `b`; `o` declares `b` with a
   repository; `b` is present and declares child `c` with a repository. From
   `a`: `b: already available`, exit 0, and `c` is never mentioned. Delete `b/`
   and `c` *is* discovered. **Having a repository already makes a downstream
   repository disappear from provisioning** — the steady state, and the one the
   Proposit workspace is in.

   `_declared_nodes_in_graph`'s own docstring claims it reads "every node
   reachable from it here" and calls out a sibling package specifically, which
   is precisely what `ancestors + descendants` omits.

2. **`--dry-run` can report "already available" for a project it only
   planned.** `have.add(project_id)` runs before the `if dry_run` return, so a
   second declaration of the same id — routine when a parent and a grandparent
   both name it — prints `already available` in a run where nothing was fetched
   and the project is not on disk. Dry-run output is what a user reads to decide
   whether to run for real.
