Alter an inherited (federated) capability locally without touching its source:
`tcw capabilities set <path> --status <S>` / `--field K=V` on the inherited path
writes a local override for you — a `meta.yaml` carrying `overrides: <alias>/<id>`
plus only the fields you changed. Metadata partial-merges over the upstream entry;
a body override composes as `prependedDocs` + (a local `description.md`, else the
upstream body) + `appendedDocs`. The upstream node is never modified.

A write that Git refuses — a lock another process holds, a hook that says no — removes the override folder it had just materialized, rather than leaving an empty one behind. An override that already existed keeps what the write put in it.
