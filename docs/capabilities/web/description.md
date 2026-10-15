As a user, I read a project's Work, Taxonomy and Capabilities in the local
web app that `tcw serve` runs, with deep links and browser history. It is one
Python process: the client comes prebuilt inside the installed package, and
nothing else needs to be installed, Node.js included. It serves one project,
the one it was started in, on the loopback address only.

The Work board lists that project's items, coloured by the kind of stage each
is at. It filters by stage (finished and dropped items are hidden until their
stage is ticked), by tag and by assignee, and sorts by name, creation date or
priority in either direction. An item's page shows its stage and properties,
its request and comments, and one tab per stage that keeps files, with each
stage's document or rounds and their verdicts. The Taxonomy and Capabilities
trees list inherited entries beside local ones, each marked with the project
it comes from.

A link to another project's item is shown as a labelled name, not followed:
this page serves one project. An unresolved link stays inert and says why.
See [Edit TCW content in a local web app](tcw://C/web/editing).
