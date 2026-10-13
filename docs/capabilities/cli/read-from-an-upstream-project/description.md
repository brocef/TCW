As a user, I declare a project I read from under `projects.upstream` in my own
`tcw-config.yaml`, and that project never has to name mine. A private
application can read a public library this way without the library's files
mentioning the application.

My project, and every project in its family — its parents, its children and
theirs — can then read the upstream: `extends` its taxonomy and capabilities,
show its work items as `<project-id>/<folder>`, and link to them with `tcw://`.
The entry takes the same `path` / `repository` forms as a child, so a checkout
holding only my repository obtains the upstream with `tcw provision`.

Nothing writes into it from here. Every command that would change one of its
items — `tcw work edit`, `advance`, `discard`, `comment`, `rename`, and every
changing route of `tcw serve` — refuses (exit 3) with the reason and tells me to
run it in the upstream's own checkout. The two commands that do write into
another project, `tcw work new --project` and `tcw work edit --blocks`, refuse
an upstream one, so a project is written from here only when it is reached
through parent and child links alone.

Only the upstream's own config is read: its connections are not followed,
checked or provisioned, so a problem there never blocks me. It stays off my
family's board and out of `tcw validate`'s checks; `tcw projects list` lists it
after this project's parent and children.

To turn an existing child into an upstream, the parent moves its entry from
`children` to `upstream` first; until the former child drops its `parent`
entry, `tcw validate` shows a warning rather than an error. See
[Validate a TCW project](tcw://C/cli/validate-a-project) and
[List connected projects](tcw://C/cli/list-connected-projects).
