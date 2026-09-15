As a user, I run `tcw work show <slug>` to read an item's state and body
(including any recorded blockers), `tcw work path <slug>` to print its current
on-disk path, or `tcw work path` without a slug to print the absolute, resolved,
configuration-aware work-store folder.
For initiative-related work, `show` includes the item's `type` and `initiative` fields when present so an agent can choose the right lifecycle path.
An item bound to a tracker ticket gets one more line naming the ticket, the
provider, the part and the ticket's link, or saying that its binding file cannot be
read and why. That line reports what the binding records, not what the tracker
says now, and reading it needs no tracker configured. When the ticket did not follow
the item's last move, a `tracker sync:` line says whether that is pending or
conflicting, after which move, when, and why.

With `--json`, `show` prints the item as a machine-readable document instead of
the summary: an explicit `schema` version I can check before relying on the
shape, every field at a documented JSON type, and an `artifacts` map telling me
which lifecycle documents exist — so a script can ask whether the spec has been
written without reading the folder. Its `tracker` field is `null` for an item with
no binding, the ticket's key, id and URL with the provider, project, part and bound
date and a `sync` record (`null` while the ticket is in step) for a bound one, or
a `problem` for a binding that cannot be read. It is the same document `tcw serve`'s API
returns, so what I automate against and what the web app shows cannot drift.

Errors keep stdout empty and exit non-zero, so piping into `jq` fails cleanly
rather than on a fragment. A `capabilities` block holding a value JSON cannot
represent — a date, binary data, a set — is converted rather than stringified on
the way out; a block whose keys would collide once converted is refused by name,
because dropping one of them silently is worse than telling me.
