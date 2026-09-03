Found by the repo-wide sibling sweep required at the `spec` stage of
2026-09-03-unreachable-connected-projects-degrade-instead-of-failing-every-command,
on 2026-09-03. Not reported by a user.

`_extended_component_roots` composes the extended node's store path rather than
resolving it (`tcw/store/fs.py:977`):

    target = Path(project.locator) / "docs" / component

A node that configures `taxonomy.path` or `capabilities.path` elsewhere — which
`tcw init --taxonomy-path` and `--capabilities-path` exist to do — therefore
cannot be extended from, and the error says it has no `docs/<component>/` when in
fact it has one somewhere else. The same composition also skips the
`repository` declaration ladder, so a sibling whose tree is declared but not
present here is reported as having no tree rather than as unprovisioned.

`resolve_store` (`tcw/store/fs.py:2742`) is the resolution this should be using,
and the store-path rule is already stated elsewhere in the project: never compose
a store path from the node root.

Same class of defect as the item that found it — a path composed instead of
resolved — but a different code path with a different fix, which is why it is
filed on its own rather than folded in.
