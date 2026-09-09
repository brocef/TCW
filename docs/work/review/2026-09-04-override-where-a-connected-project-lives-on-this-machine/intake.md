Raised in conversation, 2026-09-04, immediately after v1.3.0 shipped:

> We could potentially use environment variables to specify the path of a
> reference to repository if it already exists on disk.

**The case that prompted it, observed rather than imagined.** Verifying the
merged Proposit configs against published 1.3.0, `proposit-core` reported two
graph problems in a workspace laid out with the repositories as flat siblings:

```
…/stores/…-proposit-core-…/tcw-config.yaml: duplicate project id 'proposit-core'
    also used by /home/user/proposit-core/tcw-config.yaml
…/stores/…-proposit-orchestration-…/tcw-config.yaml: child locator for
    'proposit-core' does not point back to /home/user/proposit-core
```

`proposit-core` declares `parent.proposit-app: path: ..`, correct for the real
workspace where both repositories are nested inside `proposit-orchestration/`.
Where they are flat siblings the path resolves to nothing, the ladder falls
through to `repository`, and provisioning fetches a *second* copy of a project
already on disk — which then collides by id with the first. Rebuilding the real
nested shape produced `validate OK` in all five nodes with zero fetches, so this
is not a defect in what shipped: it is a machine whose arrangement disagrees with
what its configs declare, and TCW has no way to be told so.

**Two more cases the same mechanism covers**, neither currently expressible:

- pointing a checkout at a *local* clone of a dependency instead of a fetched
  one, the need `go mod replace` and `cargo patch` exist for;
- CI, where the runner checks repositories out to paths nobody wrote in a config.

**Why the config cannot answer it.** A locator is a fact about one machine —
that premise is the whole reason `repository` declarations exist. Adding
alternative paths to the shared config would put the machine fact back in the
file every checkout reads, which is the thing this feature was built to remove.
