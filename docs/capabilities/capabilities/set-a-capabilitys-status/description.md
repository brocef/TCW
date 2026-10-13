Update a capability's status or any field in the locked set in place, by path —
`tcw capabilities set <path> --status Supported`, `--field K=V` — or through the
web editor. Each `--field` sets one field; repeat it for more fields, and a list
field such as `Subject` takes its values separated by commas
(`--field Subject=invoice,payment`). Naming the same field twice, or a `--field`
without `=`, is a usage error (exit 2). Addresses local and inherited (federated)
capabilities alike; for an inherited one the local override is written for you.

The fields I can set are `Status`, `Priority`, `Lifecycle`, `Superseded by`,
`Subject`, `Feature`, `Roles`, `When`, `Gaps` and `Blocked by`. Any other field
name is a usage error (exit 2) — including `Planning doc` and `Tracker`, which
3.0 retired. A record that still carries one of them can be read, and a write of
other fields leaves it in place, but `tcw validate` reports it as an error until
it is removed.

A reference-bearing field must resolve, and a write carrying one that does not
is refused (exit 2) with the same problem `tcw validate` would report — the
message comes from one shared renderer, so the two cannot drift apart. Six
fields carry references: `Subject`, `Feature`, `Superseded by`, `Blocked by`,
`Roles` and `When`. Every bad reference in the write is named at once, not one
per attempt, and a refused write changes nothing on disk. `Subject` and
`Feature` resolve against the project's taxonomy, so on a project with no
taxonomy store there is nothing to resolve against and they pass; the other
four resolve against the capability ledger itself and are always checked.

Only the references a write supplies are checked, never the capability's
existing ones — so a capability that already stores a bad reference can still
be repaired with `--status Omitted`.

A successful write prints nothing on standard output and names the file it wrote
on standard error. It stages and commits nothing. A write that fails part-way
removes the override folder it had just made, rather than leaving an empty one
behind; an override that already existed keeps what the write put in it.
