## Fixed

- **The search for a project no manifest entry places no longer climbs from
  a copy into the main checkout it was made from (TCW-120).** `search_rounds`
  (`tcw/store/project.py`) now leaves out of every climb made from where a
  folder is the main checkout of each linked worktree enclosing that folder
  that is stored inside its own main checkout, and the folders between the
  two that are in the main checkout's repository (same git common folder);
  the folders above that main checkout, and a separate repository between
  the two, are still climbed. New helpers `_under_a_linked_worktree`,
  `_left_out_of_the_climb` and `_climb`. The walk outward goes through every
  enclosing checkout, main or linked, so it is not stopped by a plain clone
  in between, and it starts at the folder searched from, so the active
  worktree's own main checkout is left out too when a separate repository
  lies between the two. It applies to the round read as written, to a
  related project's search made outside the active worktree, and to an
  active project in no worktree, wherever the command runs.
  `_checkout_of` (cached in `_CHECKOUT_CACHE`) is now the one place that
  asks git where a folder's checkout, main checkout and git common folder
  are, reading a submodule's main checkout from `core.worktree`;
  `worktree_anchors` and `_same_place_in_two_checkouts` are built on it, so
  each folder is asked once per process, and a submodule's own linked
  worktree kept inside the submodule's checkout is handled as any other.
  A copy made of nested worktrees at `.claude/worktrees/<name>`, as Claude
  Code makes, no longer fails with "declared by more than one folder:
  …/.claude/worktrees/w and …/MAIN", no longer reports a 3.x main checkout
  as needing `tcw migrate`, and no longer reads the main checkout's project
  when the copy lacks it. `tcw migrate`'s prediction (`search_4`) follows,
  so migrating in such a copy no longer writes a manifest entry the main
  checkout's run does not. Cost: no git process unless a `.git` file lies
  above the folder searched from, or the active worktree's folder is in
  another repository's checkout.
