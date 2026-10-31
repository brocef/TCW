As a user, I read a project's Work, Taxonomy and Capabilities in the local
web app that `tcw serve` runs, with deep links and browser history. It is one
Python process: the client comes prebuilt inside the installed package, and
nothing else needs to be installed, Node.js included. It serves one project,
the one it was started in, on the loopback address only.

A scope control and a project filter in the header match `--scope` and
`--project`: the page lists the project's own objects by default, and adds the
projects above it, below it, or both, or keeps one of them. The choice is kept
in the page's address, so a link reproduces the view. The control is shown only
for a project that has parents or children. A project the scope covers that
cannot be read is named in a notice above the list, with its reason.

The Work board lists the items of the projects the scope covers, coloured by the kind of stage each
is at. It filters by stage (finished and dropped items are hidden until their
stage is ticked), by tag and by assignee, and sorts by name, creation date or
priority in either direction. An item's page shows its stage and properties,
its request and comments, and one tab per stage that keeps files, with each
stage's document or rounds and their verdicts. The Taxonomy and Capabilities
trees list the scope's entries, each one another project owns marked with that
project. Under a scope that reaches the projects below, each capability shows
how many of them give each status, as `Missing(1), Supported(1)`, and its page
lists each status with its projects.

Any object of another project TCW can locate opens in the app, read-only
([Edit TCW content in a local web app](tcw://C/web/editing)), and a link to
one on this machine is followed. A link to a project that is not on this
machine is shown as a labelled name. An unresolved link stays inert and says why.
See [Edit TCW content in a local web app](tcw://C/web/editing).
