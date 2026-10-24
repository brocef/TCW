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

## The project served, and the others it can show

The app edits one project, the one it was started in (the served project). It
can also show the objects of that project's relatives, its parents and their
parents (its ancestors) and its children and theirs (its descendants), but it
never changes them.

### The scope control and the project filter

A project with parents or children has two choices after the tabs, which
match the command line's `--scope` and `--project` options (see
[the CLI guide](cli.md)):

- **The scope control** chooses which projects every list covers:
  `own: This project` (the default), `up: With its ancestors`,
  `down: With its descendants`, or `all: Ancestors and descendants`.
- **The project filter** keeps one of the projects that scope covers, or
  **All of them**. With one project chosen, a list holds only the objects
  that project owns itself, as `--project` does.

A project with no parents and no children shows neither. The choice is kept
in the page's address (`?scope=down&project=app`, say), so a link reproduces
the view, and Back and Forward step through it. A scope that does not cover
the project the filter holds drops it, back to **All of them**. Changing
either choice while a form or editor holds unsaved changes asks first:
"You have unsaved changes. Leave without saving?"

Under the default scope the lists hold the served project's own objects only;
an inherited taxonomy entry or capability is listed under `up` or `all`. How
inheritance and overrides work is in
[Taxonomy and capabilities](taxonomy-and-capabilities.md).

### What the app shows of a capability across projects

Under `down` and `all`, with **All of them** in the filter, each capability's
row shows how many projects hold each status, such as `Missing(1), Supported(1)`,
and its page has a **Status by project** section that lists the projects
under each status. A project that only inherits the capability is marked
"(inherited)"; each project that has an object of its own at that path is a
link to that object's page; a project that could not be read is listed as
unavailable. With one project chosen in the filter, the records carry no
status by project, so the row shows that project's own status and the page
has no **Status by project** section.

### Another project's objects are read-only

Every object of another project carries an **owned by `<id>`** badge, on its
row and on its page, and its page has no edit control. Another project's
work item page has no **Edit**, no comment box, no controls to edit or add
files, and its declared ledger changes (its `capabilities.yaml`) are shown
without an edit control. Its stage line names the command that moves it, run
in its own project with `-C`, which runs `tcw` as if it had been started in
the folder named (here the folder of the project with ID `<owner>`):

```sh
tcw -C tcw://<owner>.path/ work advance <full id>
```

A full identifier is the name that says which project owns an object, such as
`core.work/<folder>` for a work item of the project `core`; the
[guide on linking](linking-and-validation.md) explains them. To change an
inherited capability, the project makes an override of its own with
`tcw capabilities set`, as the taxonomy and capabilities guide says; the
server's refusal of such an edit names that command.

### Following links between projects

A `tcw://` link in a document, and an item named as a parent, a blocker, a
child or a blocked item, opens its object's page inside the app when that
object's project is on this machine, whichever project owns it. The page
opened is read-only as above. A link to a project that is not on this machine
is shown as its name with a badge naming the project, described as "In
project `<id>`; open it there", and does not navigate. A link that does not
resolve stays plain text with the reason.

### When another project cannot be read

A project the scope covers that cannot be read is named above the list, with
the reason: "Project `<id>` could not be read, so its objects are not listed".
On the work board, while the project filter keeps a different project, the
unreadable project is read only to count the kept items' children and blocks,
so the notice says instead "so its items are not counted in children and
blocks".

### The records are the command line's

Each object in a list carries the keys the matching `--json` record of
`tcw <axis> list` carries for the same scope (`full-id`, `owner`,
`overrides`, `statuses` and the rest), with the server's other fields of that
object beside them, so what the page shows can be checked against the command
line.

## What you can read

The app has a tab for each axis the project keeps (Work, Taxonomy,
Capabilities), and its URL follows what is shown (`/work/<folder>`,
`/taxonomy/<path>`, `/capabilities/<path>`, or another project's full
identifier in place of the folder or path), so any view can be linked to and
Back and Forward work. Each list is a tree, filtered by the text box above it.

- **The work board** lists the items the scope covers, each row coloured by
  the kind of stage it is at. It filters by stage, tag and assignee; finished
  and dropped items are hidden until their stage is ticked. It sorts by name,
  creation date or priority, in either direction. Each row can copy its full
  identifier.
- **An item's page** shows its stage, its properties, what it asks for, its
  comments, and one tab per stage that keeps files: that stage's document, or
  its rounds with their verdicts, and any handoffs.
- **Taxonomy and capabilities** list the entries the scope covers, each one
  owned by another project marked with that project.

Any `tcw://` link in a document renders as a link inside the app, as
described above.

The gear after the tabs chooses **Light**, **Dark** or **System** appearance;
the choice is kept in the browser, not in the project.

## What you can edit and create

Everything below applies to the served project's own objects only.

- **An item's files**: each stage's document, new rounds (a round of a stage
  that judges has a verdict, chosen from a fixed list) and handoffs.
- **The item's declared ledger changes**, `capabilities.yaml`, as six lists:
  capabilities and taxonomy entries the work adds, changes and removes. The
  form does not keep comments written in the file. A file it cannot read as
  lists opens as plain text with the reason, to be fixed by hand.
- **An item's properties** (title, priority, effort, complexity, tags,
  assignee, parent, blocked-by), and comments, which are added and never
  edited. To say that this item blocks another, set **Blocked by** on the
  other item.
- **New items**, always in the served project: the form has no choice of
  project. An item of another project is made in that project, with
  `tcw -C tcw://<id>.path/ work new "<title>"`. With a parent given, **Put its
  folder inside the parent's folder** makes the new item's folder inside its
  parent's, as `tcw work new --nest` does; the box cannot be ticked while the
  parent is empty.
- **Taxonomy entries and capabilities**, created and edited. A capability's
  body edit changes only the capability's own description. Where the body the
  page shows also holds attached documents or an inherited description, the
  editor says "The body shown on the page also holds attached documents or an
  inherited description, which this edit leaves unchanged."

Every save sends the version the page loaded. If the file or record changed
since, the save is refused and the page offers to load the current version,
keeping your draft until you choose. After a save TCW checks what was saved,
offline, and shows anything wrong (a link that does not resolve, a round with
no verdict, a declaration that names nothing) as a notice; the save stands.

### No lifecycle moves

The app never moves an item from one stage to another, and it never changes
git state. Each item's page names the command that moves it:

```sh
tcw work advance <full id>                    # move an item to its next stage
tcw work discard --reason "<why>" <full id>   # drop an item
```

## When the work is kept in Jira

In a project whose work backend is Jira, Jira keeps each item's record. The
request, comments, stage and properties are shown read-only, each with
**Open in Jira** to edit it there. The item's files are on disk and stay
editable. Under the default scope the board is read with one search, or two
while a tag filter is ticked: one for the tagged items and one for every
item, which an item's `blocks` and `children` are worked out from;
[the Jira guide](jira.md) says how a wider scope is read. The new-item form
shows the fields Jira's create screen has, and a **Tickets** view lists inbox
tickets with **Adopt**, which makes one an item and opens it. Adopting runs
the request stage's `post` hooks, as `tcw work tickets adopt` does; if one
fails, the item is still made, and the page shows what failed.

The new-item form accepts a parent or a blocker in another project. One that
is a ticket of another project on the same Jira site becomes a Jira link;
any other is recorded in the new item's `tcw-work-item.yaml` file, and Jira
shows no link for it.

When Jira cannot be reached, or its credentials are not set, the server still
starts. The board lists the item folders found on disk under a banner that
gives the reason and offers **Retry**; files can still be read and saved.

## Suggestions as you type

Every field either suggests values as you type or is a fixed choice. Use Up
or Down and then Enter, or click, to pick a suggestion; Enter on its own keeps
exactly what you typed, when the field allows it. Text a field will not keep
stays in the field with the reason, and the form will not save until it is
changed or cleared.

The fields that name other objects offer what the served project can
reference, whatever the scope control shows: its own work items, and its view
of taxonomy and capabilities, which is its own entries and those it inherits.

- **Fixed choices**: priority, effort and complexity; a taxonomy entry's kind;
  a capability's status, priority and lifecycle. All come from the project's
  own scales.
- **Tags** are chips from the project's tag registry; an unregistered tag is
  not kept.
- **Parent and blocked-by** suggest the served project's items (a parent
  never offers the item itself or anything under it). In a project whose
  work is kept in files, they also search, as you type, the items of its
  parents and children on this machine whose work is kept in files. Another
  project's item, named by its full identifier, is kept with the warning
  "`<full id>` is in project `<id>`, which this page does not check; make sure
  it exists". In Jira mode such a parent or blocker is placed as the section
  on Jira above says.
- **Assignee** suggests the names already on items and you. In Jira mode it
  offers the people Jira lets the item be assigned to, shown by name, and
  keeps nothing else: the server checks the account against Jira's assignable
  users before creating the item.
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
- **Typing `tcw://`** in any document offers work items, taxonomy entries and
  capabilities, and inserts the chosen object's address, `tcw://` followed by
  its full identifier (`tcw://<id>.work/<folder>` for a work item).

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
