As a user, I run `tcw work show <slug>` to read an item's state and body
(including any recorded blockers), `tcw work path <slug>` to print its current
on-disk path, or `tcw work path` without a slug to print the absolute, resolved,
configuration-aware work-store folder.
For initiative-related work, `show` includes the item's `type` and `initiative` fields when present so an agent can choose the right lifecycle path.

With `--json`, `show` prints the item as a machine-readable document instead of
the summary: an explicit `schema` version I can check before relying on the
shape, every field at a documented JSON type, and an `artifacts` map telling me
which lifecycle documents exist — so a script can ask whether the spec has been
written without reading the folder. It is the same document `tcw serve`'s API
returns, so what I automate against and what the web app shows cannot drift.

Errors keep stdout empty and exit non-zero, so piping into `jq` fails cleanly
rather than on a fragment. A `capabilities` block holding a value JSON cannot
represent — a date, binary data, a set — is converted rather than stringified on
the way out; a block whose keys would collide once converted is refused by name,
because dropping one of them silently is worse than telling me.
