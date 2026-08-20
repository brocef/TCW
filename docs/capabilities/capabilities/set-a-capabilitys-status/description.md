Update a capability's status or any field in the locked vocabulary in place, by
path — `tcw capabilities set <path> --status Supported`, `--field K=V` — or
through the web editor. The route the work lifecycle's ledger flip runs on.
Addresses local and inherited (federated) capabilities alike; for an inherited
one the local override is written for you.

A reference-bearing field must resolve, and a write carrying one that does not
is refused with the same problem `tcw capabilities check` would report — the
message comes from one shared renderer, so the two cannot drift apart. Six
fields carry references: `Subject`, `Feature`, `Superseded by`, `Blocked by`,
`Roles` and `When`. Every bad reference in the write is named at once, not one
per attempt, and a refused write changes nothing on disk. `Subject` and
`Feature` resolve against the project's taxonomy, so on a project with no
taxonomy component there is nothing to resolve against and they pass; the other
four resolve against the capability ledger itself and are always checked.

Only the references a write supplies are checked, never the capability's
existing ones — so a capability that already stores a bad reference can still
be repaired with `--status Omitted`, which is the route completing a work item
recommends.
