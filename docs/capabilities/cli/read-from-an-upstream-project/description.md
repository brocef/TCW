As a user, I declare a project I read from under `projects.upstream` in my own
`.tcw/tcw-config.yaml`, by its ID, and that project never has to name mine. A private
application can read a public library this way without the library's files
mentioning the application.

My project, and every project in its family — its parents, its children and
theirs — can then read the upstream: `extends` its taxonomy and capabilities,
show its work items as `<project-id>/<folder>`, and link to them with `tcw://`.
Where it is on this machine is said the same way as for a child: by a manifest
entry, by `TCW_PROJECT_<ID>`, or found from the ID. When it is not here, TCW
names the repository its manifest entry gives and the command that fetches it,
`tcw project provision <id>`; `tcw provision` does not fetch it.

Nothing writes into it from here. Every command that would change one of its
items — `tcw work edit`, `advance`, `discard`, `comment` and `rename` —
refuses (exit 3) with the reason and tells me to run it in the upstream's own
checkout. The two commands that do write into another project, `tcw work new
--project` and `tcw work edit --blocks`, refuse an upstream one, and so do the
web app's create form and `blocks` field, which run them; a project is written
from here only when it is reached through parent and child links alone.

Only the upstream's own config is read: its connections are not followed or
checked, and its manifests are not read, so a problem there never blocks me. It stays off my
family's board and out of `tcw validate`'s checks; `tcw projects list` lists it
after this project's parent and children.

To turn an existing child into an upstream, the parent moves its entry from
`children` to `upstream` first; until the former child drops its `parent`
entry, `tcw validate` shows a warning rather than an error. See
[Validate a TCW project](tcw://C/cli/validate-a-project) and
[List connected projects](tcw://C/cli/list-connected-projects).
