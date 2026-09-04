Found while verifying the cloud-environment work against the real Proposit
repositories, 2026-09-04. Reproduced.

`proposit-app-repo` is the repository-root node of the `proposit-app` monorepo.
It deliberately keeps **no** work store — the boards belong to the three package
nodes — and exists so those packages have a route to each other that never leaves
their own repository. Every other command already understands that:
`tcw work nodes` prints `parent: proposit-app-repo  (no work store)`.

`tcw validate` does not:

```
$ cd proposit-app && tcw validate
[proposit-app-repo] work check: …/tcw-config.yaml: work.path is not a directory:
    …/proposit-app/docs/work
1 problem(s).
```

`_components_to_check` (`tcw/validate.py`) appends `"work"` when the store fails
to open and *either* `docs/work` exists *or* `tcw-config.yaml` exists. The second
disjunct is true of every node, so a node that declares no work component and has
no `docs/work` is checked anyway and reports the default path as missing.

The intent of that fallback is right and must be kept: a node that *claims* a
work store and cannot open it has to say why rather than silently skipping the
check — a declared-but-unprovisioned board, a `work.path` typo. What is wrong is
the test for "claims one". A bare `tcw-config.yaml` with no `work:` section and no
`docs/work` claims nothing.

Pre-existing on `main`, and harmless there: before this work there was no reason
to register a node that keeps no board. The routing node is what makes it a
defect, so it belongs with that work rather than after it.
