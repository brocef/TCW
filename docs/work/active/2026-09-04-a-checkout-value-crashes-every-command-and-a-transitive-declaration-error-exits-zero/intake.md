Found by an adversarial review of the provisioning work, 2026-09-04. Both
reproduced.

1. **A `checkout` containing `~unknownuser` crashes every command in the node
   with an uncaught `RuntimeError`.** `_target_path` calls `provisioned_root` on
   every `connected-projects` entry that declares a repository — during
   `_load_graph`, so on every command. `Path.expanduser()` raises `RuntimeError`
   (not `ValueError`, not `OSError`) for a `~name` it cannot resolve, and nothing
   on the path catches it. A node whose only defect is
   `checkout: "~nosuchuser/b"` produces a raw traceback out of `tcw validate`,
   `tcw work list` and `FsProjectRegistry.open`, from a value the parser
   accepted.

   Two secondary effects, both from `except Exception: pass` swallowing it:
   `_declared_nodes_in_graph` silently drops that node's declarations, and
   `_provision_nodes`' `starting_registry` falls to None — which disables
   `resolved_outside` entirely, so every project is re-cloned including ones the
   checkout already has.

2. **`tcw provision` exits 0 after printing declaration errors found on a
   transitively obtained node.** `run_provision` returns 1 for a malformed
   `connected-projects` declaration on the starting graph, with the comment *"a
   declaration that is present and wrong refuses, rather than reading as
   'nothing declared' and reporting success"*. `enqueue` prints the identical
   problems to stderr and never sets `failed`. The same malformed entry exits 1
   on the starting node and 0 on an obtained one, so a CI step gated on
   `tcw provision` treats the second as success.
