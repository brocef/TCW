Raw request, from a working session on 2026-09-03.

Found while designing a repository-root node for the `proposit-app` monorepo. The
three package nodes there route to each other only through their shared parent in
another repository, so a checkout that cloned only the code has no route between
siblings sitting in the same tree. The fix on the consumer side is a node at the
repository root whose children are the three packages — an intermediate node that
holds no work store of its own, since the boards stay where they are.

TCW does not currently tolerate that. `parent_node` returns a parent only if it
has a usable work store:

    def parent_node(root: Path) -> Path | None:
        """Direct registered parent that contains a work store."""
        ...
        return path if _has_work_store(path) else None

`reconcile` walks ancestors through it to find the node owning an item's
initiative epic:

    candidate_root = parent_node(candidate_root)

so a work-less node anywhere in the chain ends the walk early and the epic is
never found — silently, and on the author's machine as much as in a cloud
session. An epic rollup that quietly stops listing its slices is the failure
mode.

The walk wants the nearest work-bearing *ancestor*, not the direct parent when it
happens to have a store.
