Alter an inherited (federated) capability locally without touching its source:
`tcw capabilities set <path> --status <S>` / `--field K=V` on the inherited path
writes a local override for you — a `meta.yaml` carrying `overrides: <alias>/<id>`
plus only the fields you changed. Metadata partial-merges over the upstream entry;
a body override composes as `prependedDocs` + (a local `description.md`, else the
upstream body) + `appendedDocs`. The project the capability is inherited from is
never modified.

The override is files and nothing else: each file written is named on standard
error, and nothing is staged or committed. A write that fails part-way removes
the override folder it had just made, rather than leaving an empty one behind;
an override that already existed keeps what the write put in it.
