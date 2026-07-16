Alter an inherited (federated) capability locally without touching its source:
`tcw capabilities set <path> --status <S>` / `--field K=V` on the inherited path
writes a local override for you — a `meta.yaml` carrying `overrides: <alias>/<id>`
plus only the fields you changed. Metadata partial-merges over the upstream entry;
a body override composes as `prependedDocs` + (a local `description.md`, else the
upstream body) + `appendedDocs`. The upstream node is never modified.
