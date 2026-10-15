As a user, I edit a project's TCW documents in the local web app, and create
TCW objects there, without leaving the browser.

For a work item I write each stage's document, add rounds and handoffs (a
round of a stage that judges carries its verdict, chosen from a fixed list),
and edit the item's declared ledger changes, `capabilities.yaml`, as six
lists. A declaration the parser cannot read opens as plain text with the
parser's message, so it can be fixed. In filesystem mode I also change the
item's properties, add `blocks` links one at a time, and add comments; a
comment is never edited. I create items, in this project or, with only a
title, request text and priority, in a connected one. In Jira mode I adopt
inbox tickets as items, which runs the request stage's `post` hooks as
`tcw work tickets adopt` does.

I create and edit taxonomy entries and capabilities. An inherited entry has no
edit control: it is changed in the project that keeps it.

Every save carries the revision the page loaded, so a save over a change made
elsewhere is refused and the page offers to load the current version. A value
that names nothing is refused before anything is written: with the command
line's own message where the operation refuses it, and with the viewer's
message, naming the field, where only the viewer does. A document saved with a link that does not resolve, or a
round with no verdict, is saved and comes back with a warning.

The web app never moves an item from one stage to another, and never changes
git state. Each item page names the command that moves it,
`tcw work advance <slug>`, and `tcw work discard` drops one.
