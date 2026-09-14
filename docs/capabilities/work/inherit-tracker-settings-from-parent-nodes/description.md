As a developer in a workspace of connected TCW nodes that all read one Jira site,
I can write the tracker settings that describe the site once, in a parent node,
and have each child node write only what is its own, usually just the query that
selects its tickets. A child's `work.tracker` takes every key it leaves out from
its ancestors, all the way up, with the nearest file winning each key and nested
settings merging key by key.

It is opt-in: a node that writes no `tracker` block has no tracker, so adding
shared settings to a parent never gives a node a tracker it did not ask for. A node
that sets its own `base-url` must also set its own `credentials`, so a token is
never sent to a site chosen in a different file.

When something is wrong, `tcw validate` reports it in every node that inherits it
and names the file the bad value came from, so I know which file to fix. If a
parent is not checked out on this machine and the settings come out incomplete, it
says which one is missing.
