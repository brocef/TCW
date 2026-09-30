As a user, I declare a project I read from under `connected-projects.upstream`
in my own `tcw-config.yaml`, and that project never has to name mine. A private
application can read a public library this way without the library's files
mentioning the application.

My project, and every project in its family — its parents, its children and
theirs — can then read the upstream: `extends` its taxonomy and capabilities,
show its work items as `<project-id>/<slug>`, and link to them with `tcw://`.
The entry takes the same `path` / `repository` forms as a child, so a checkout
holding only my repository obtains the upstream with `tcw provision`.

Nothing writes into it from here. Every command that would change one of its
items or run its project's scripts — `start`, `edit`, `drop`, `delegate`, the
stage and procedure commands, and every changing route of `tcw serve` — refuses
with the reason and tells me to run it in the upstream's own checkout. A project
is writable from here only when it is reached through parent and child links
alone.

Only the upstream's own config is read: its connections are not followed,
checked or provisioned, so a problem there never blocks me. It stays off my
family's board, recursive validation and epic rollups; `tcw work nodes` lists it
under `upstream (read-only):`.

To turn an existing child into an upstream, the parent moves its entry from
`children` to `upstream` first; until the former child drops its `parent`
entry, `tcw validate` shows a warning rather than a problem. See
[Validate a TCW node](tcw://C/cli/validate-a-node) and
[Inspect the node topology](tcw://C/work/inspect-the-node-topology).
