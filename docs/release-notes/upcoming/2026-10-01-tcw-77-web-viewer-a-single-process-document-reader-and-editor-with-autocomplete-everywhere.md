## The web viewer, rebuilt: one process, no Node.js

`tcw serve` is now a single Python process. Node.js is no longer needed to
run it: the browser client comes prebuilt inside the package, as before, and
the server that hands it to the browser is part of TCW itself.

It serves the project it is started in, and it is built for TCW 3.0's work
model:

- **The work board** filters by stage, tag and assignee, hides finished and
  dropped items until you ask for them, and sorts by name, creation date or
  priority.
- **An item's page** has a tab for each stage that keeps files, showing that
  stage's document, or its rounds with their verdicts, and handoffs. You can
  write each of them in the browser, start a new round or handoff, and edit
  the item's declared ledger changes as a form.
- **Properties and comments** can be edited and added in a project whose work
  is kept in files, and new items can be created here or in a connected
  project.
- **Every field suggests what it can hold.** Tags come from the registry,
  references from the entries that exist, inherited ones included, and
  typing `tcw://` in a document offers every object to link to. A value that
  names nothing is refused before anything is written; another project's
  item can be named, with a warning that the page cannot check it.
- **In Jira mode** the request, comments, stage and properties are shown
  read-only with **Open in Jira**, while the item's files stay editable, even
  when Jira cannot be reached. A **Tickets** view adopts inbox tickets.

The viewer no longer moves items between stages. Each item's page names the
command that does: `tcw work advance <slug>`, or `tcw work discard` to drop
one. It never changes git state.

It no longer shows child projects' items on the same board; open each
project's own viewer instead. Every request is now checked to come from your
own machine, reads included.

Two more things that worked in 2.x no longer do:

- **Inherited taxonomy entries and capabilities cannot be edited in the
  viewer.** In 2.x, saving an inherited capability made a local override. Now
  run `tcw capabilities set <path> --field <name>=<value>`, which makes the
  same override; an inherited taxonomy entry is changed in the project that
  keeps it.
- **2.x links to a work item, `/<project>/work/<slug>`, no longer open it**;
  they open the board. An item's link is now `/work/<folder>`.
