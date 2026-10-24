As a user, I edit a project's TCW documents in the local web app, and create
TCW objects there, without leaving the browser.

For a work item I write each stage's document, add rounds and handoffs (a
round of a stage that judges carries its verdict, chosen from a fixed list),
and edit the item's declared ledger changes, `capabilities.yaml`, as six
lists. A declaration the parser cannot read opens as plain text with the
parser's message, so it can be fixed. In filesystem mode I also change the
item's properties, add `blocks` links one at a time, and add comments; a
comment is never edited. I create items, in this project or, with only a
title, request text and priority, in a connected one; the form marks a
project that is read-only from here, as the command line decides it, and one
that is not on this machine. In Jira mode I adopt
inbox tickets as items, which runs the request stage's `post` hooks as
`tcw work tickets adopt` does.

I create and edit taxonomy entries and capabilities. My project's own
override of an inherited one is editable like any other of its own, and the
page says what it overrides. An entry that belongs to another project has no
edit control: it is changed in the project that keeps it. Editing a
capability's body changes only the capability's own description: the editor
starts from that description, not from the body shown on the page, and says,
when they differ, that the body shown also holds attached documents or an
inherited description, which the edit leaves unchanged. Clearing the field
leaves the capability with an empty description of its own, so the page falls
back to the inherited one. When inherited content cannot be read, the request
is answered with `503 Service Unavailable`.

Every save carries the revision the page loaded, so a save over a change made
elsewhere is refused and the page offers to load the current version. A save
of a taxonomy entry or a capability that carries no revision at all is refused
too, so no save can skip that check. An item's files are only those inside its
folder: a file path that leads outside it, through a stage folder or a
`capabilities.yaml` that is a link to somewhere else, is refused as not one of
the item's files, and nothing outside is read or written. A value
that names nothing is refused before anything is written: with the command
line's own message where the operation refuses it, and with the viewer's
message, naming the field, where only the viewer does. A document saved with a link that does not resolve, or a
round with no verdict, is saved and comes back with a warning.

The web app never moves an item from one stage to another, and never changes
git state. Each item page names the command that moves it,
`tcw work advance <slug>`, and `tcw work discard` drops one.

The new item form offers to put a new child's folder inside its parent's folder, unticked by default.
