# The local web viewer

`tcw serve` starts a local web app for reading and editing the project it is
run in: its work items and their documents, its taxonomy and its capabilities.

```sh
tcw serve                    # http://127.0.0.1:8765/ and open a browser
tcw serve --no-open          # start the server without opening a browser
tcw serve --port 9000        # choose a different loopback port
```

It is one Python process. The browser client is built ahead of time and
shipped inside the installed package, so nothing else needs to be installed
to run it and it works offline. The URL is the only thing printed on standard
output, as soon as the server is listening; Ctrl-C stops it.

The app serves one project, the one it was started in. A link to another
project's item is shown as a labelled name that says which project holds it;
open that project's own viewer to follow it.

## What you can read

The app has a tab for each axis the project keeps (Work, Taxonomy,
Capabilities), and its URL follows what is shown (`/work/<folder>`,
`/taxonomy/<slug>`, `/capabilities/<path>`), so any view can be linked to and
Back and Forward work. Each list is a tree, filtered by the text box above it.

- **The work board** lists the project's items, each row coloured by the kind
  of stage it is at. It filters by stage, tag and assignee; finished and
  dropped items are hidden until their stage is ticked. It sorts by name,
  creation date or priority, in either direction. Each row can copy its slug.
- **An item's page** shows its stage, its properties, what it asks for, its
  comments, and one tab per stage that keeps files: that stage's document, or
  its rounds with their verdicts, and any handoffs.
- **Taxonomy and capabilities** list inherited entries beside local ones, each
  marked with the project it comes from.

Any `tcw://` link in a document renders as a link inside the app. One that
does not resolve stays plain text with the reason.

The gear after the tabs chooses **Light**, **Dark** or **System** appearance;
the choice is kept in the browser, not in the project.

## What you can edit and create

- **An item's files**: each stage's document, new rounds (a round of a stage
  that judges has a verdict, chosen from a fixed list) and handoffs.
- **The item's declared ledger changes**, `capabilities.yaml`, as six lists:
  capabilities and taxonomy entries the work adds, changes and removes. The
  form does not keep comments written in the file. A file it cannot read as
  lists opens as plain text with the reason, to be fixed by hand.
- **An item's properties** (title, priority, effort, complexity, tags,
  assignee, parent, blocked-by), `blocks` links added one at a time, and
  comments, which are added and never edited.
- **New items**, in this project or in a connected one. An item made in
  another project takes only a title, what it asks for, and a priority.
- **Taxonomy entries and capabilities**, created and edited. An inherited
  entry has no edit control: it is changed in the project that keeps it.

Every save sends the version the page loaded. If the file or record changed
since, the save is refused and the page offers to load the current version,
keeping your draft until you choose. After a save TCW checks what was saved,
offline, and shows anything wrong (a link that does not resolve, a round with
no verdict, a declaration that names nothing) as a notice; the save stands.

### No lifecycle moves

The app never moves an item from one stage to another, and it never changes
git state. Each item's page names the command that moves it:

```sh
tcw work advance <slug>                    # move an item to its next stage
tcw work discard --reason "<why>" <slug>   # drop an item
```

## When the work is kept in Jira

In a project whose work backend is Jira, Jira keeps each item's record. The
request, comments, stage and properties are shown read-only, each with
**Open in Jira** to edit it there. The item's files are on disk and stay
editable. The board is read with one search. The new-item form shows the
fields Jira's create screen has, and a **Tickets** view lists inbox tickets
with **Adopt**, which makes one an item and opens it.

When Jira cannot be reached, or its credentials are not set, the server still
starts. The board lists the item folders found on disk under a banner that
gives the reason and offers **Retry**; files can still be read and saved.

## Suggestions as you type

Every field either suggests values as you type or is a fixed choice. Use Up,
Down and Enter, or click, to pick a suggestion.

- **Fixed choices**: priority, effort and complexity; a taxonomy entry's kind;
  a capability's status, priority and lifecycle. All come from the project's
  own scales.
- **Tags** are chips from the project's tag registry; an unregistered tag is
  not kept.
- **Parent, blocked-by and blocks** suggest this project's items (a parent
  never offers the item itself or anything under it) and the items of
  connected projects on this machine whose work is kept in files. Another
  project's full slug, `<project>/<folder>`, is kept with a warning, because
  this page cannot check it. In Jira mode only this project's items are
  allowed.
- **Assignee** suggests the names already on items and you; in Jira mode it
  offers the people Jira lets the item be assigned to, and nothing else.
- **Taxonomy and capability references** (a parent, related entries, a
  feature's vocabulary, a capability's feature, subject, roles, conditions,
  blocked-by and superseded-by) suggest the entries that fit, inherited ones
  included, and keep nothing else. Roles and conditions keep a leading `!`,
  which negates them.
- **A new capability's path** is suggested one segment at a time; a new
  segment is allowed.
- **The declaration lists** suggest existing entries; an entry under "new"
  may be a name not in the ledger yet, while "changed" and "removed" must name
  one that exists.
- **Typing `tcw://`** in any document offers the objects of all three axes and
  inserts the link; a work item is inserted as `tcw://W/<folder>`.

The server applies the same rules, so a value a form would not keep is refused
when sent by hand too.

## Security

- The server listens on `127.0.0.1` only.
- Every request must name a loopback host in `Host`, and in `Origin` when it
  sends one. This blocks other web pages and DNS rebinding, where a hostile
  name is pointed at your machine.
- A request that changes something must be JSON and at most 1 MiB.
- Every answer carries a content security policy that lets the page load only
  its own files.
- Errors carry the operation's message and never a Python traceback.

If `tcw serve` reports that its packaged web assets are missing, reinstall TCW.
If the port is taken, choose another with `--port`.

## Building the client (contributors)

The client's source is in `web/client/`; the built files are committed under
`tcw/serve/dist/client/` and shipped in the package. Rebuilding needs Node.js
22.12 or newer and pnpm; running `tcw serve` needs neither.

```sh
pnpm install
pnpm build          # rebuild tcw/serve/dist/client from web/client
pnpm check:build    # confirm the committed build matches the source
pnpm test           # client unit tests
pnpm lint
pnpm prettify       # format source and documentation
```

Commit the rebuilt files with the source change that produced them;
`check:build` fails otherwise.
