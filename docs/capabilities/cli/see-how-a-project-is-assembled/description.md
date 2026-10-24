As a user, I run `tcw project info` to see, in one place, how the current
project is put together: its ID and folder; its parents, with the axes each
passes down; its children, marking those only my personal configuration lists;
which of them are not on this machine; the order its ancestors are read in,
with a warning when no order keeps every project's own order of parents; each
setting with where its value comes from (the project, layer and file, as
[Show the effective
configuration](tcw://C/cli/show-the-effective-configuration) labels it, and
whether it is inherited); where each store is, or why it cannot be reached;
the records this project overrides from an ancestor, for taxonomy and
capabilities; and how many paths two unrelated projects both use.

It shows what is missing rather than refusing: a parent not on this machine,
a store not fetched, or a setting that depends on an absent ancestor is shown
with its reason, and the command still exits 0. It refuses only what `tcw
project list` refuses, a problem in the project graph or in the project's own
configuration, with the same message. It writes nothing.

`tcw project info --json` prints the same facts as one document, `{"schema": 2,
"project": {...}}`, for scripts. To learn where one other project is, [Find
where a project is on this
machine](tcw://C/cli/find-where-a-project-is-on-this-machine).
