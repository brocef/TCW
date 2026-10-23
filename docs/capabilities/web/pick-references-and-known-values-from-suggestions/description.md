As a user, every field I fill in the local web app either suggests what it
can hold as I type or is a fixed choice, so I seldom have to remember an
exact name.

Status, priority, lifecycle, effort, complexity and a taxonomy entry's kind
are fixed choices from the project's own scales. Tags are chips from the
project's tag registry. A taxonomy or capability reference (feature, subject,
roles, conditions, parent, vocabulary, related entries) suggests the entries
that fit, inherited ones included, and will not keep a name that is not one
of them; roles and conditions keep a leading `!` that negates them. A new
capability's path is suggested one segment at a time, and a new segment is
allowed. A work item's parent, blocked-by and blocks fields suggest this
project's items and those of connected projects found on this machine; in
filesystem mode another project's full slug is kept with a warning, since
the page cannot check it. In Jira mode the assignee is chosen from the people
Jira lets the item be assigned to.

Typing `tcw://` in a document offers the objects of all three axes and inserts
the reference; a work item is inserted as `tcw://W/<folder>`.

The suggestions insert full identifiers for references and
`tcw://<project>.<namespace>/<id-path>` addresses for links, and a reference
typed as an id-path is stored as the full identifier of this project's own
entry.
