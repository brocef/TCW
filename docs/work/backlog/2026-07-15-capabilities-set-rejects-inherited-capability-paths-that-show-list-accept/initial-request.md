# capabilities set rejects inherited capability paths that show/list accept

Source: https://github.com/brocef/TCW/issues/3 (reported against v0.11.3, from a
5-node federation with a shared capability master).

## Product changes

In a node that federates another project via `tcw capabilities extends`, an
inherited capability with no local override can be printed by `show` and
enumerated by `list`, but `set` rejects the same path:

```
$ tcw capabilities set shared/moderation/report-content --status Supported
tcw capabilities set: no such capability: shared/moderation/report-content
```

`set` appears to resolve only local declarations while `show`/`list` resolve the
federated view. The only working way to flip an inherited entry is hand-authoring
`docs/capabilities/<ns>/<name>/meta.yaml` with `overrides:` + `Status:` — a shape
that isn't documented, and which our own guidance forbids ("never hand-edit
status"). `capabilities add` isn't an alternative: it has no `--overrides` flag
and scaffolds a fresh local declaration.

So at the work-lifecycle completion gate, the documented command hard-fails and
the only mechanism that works is the one the guidance forbids. The reporter found
two completed items whose `outcome.md` deferred the flips to completion and then
never flipped them — 8 capabilities shipped in code but still reading `Missing`.

Remediation:
- Make `set` resolve inherited paths and materialize the override file itself.
- Document the override file shape regardless.

## Technical changes

## Meta changes
