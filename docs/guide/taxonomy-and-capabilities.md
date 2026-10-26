# Taxonomy and Capabilities

Taxonomy holds the nouns: the things the project deals with. Capabilities hold
the user stories: what someone can do with those things. A capability points at
taxonomy entries; taxonomy never points back. Both are folders of files in the
repository, and both change in the same commit as the code they describe.

Every taxonomy entry and every capability is an **object** with a **full
identifier**: the ID of the project that owns it, the axis, and its path in
that project's store, such as `shop.taxonomy/invoice` or
`shop.capabilities/billing/invoices`. Commands print full identifiers, and
accept either one or a path in the active project (the project the command
runs in). [Linking and validation](linking-and-validation.md) explains full
identifiers and the forms commands accept.

Each group has a `--help` on every command, and `tcw validate` checks both
trees, with everything else in the project.

See also [The Work component](work.md),
[Linking and validation](linking-and-validation.md),
[Related projects](multi-repo.md) and [The command line](cli.md).

## `tcw taxonomy`: the nouns

Taxonomy entries form a tree of folders, and an entry's path is its identity:
`admin/permission` is a different entry from `billing/permission`. Entries have
two kinds: **Vocabulary** for the fundamental language of the project, and
**Feature** for the user- or application-facing features that operate on or
involve vocabulary.

```sh
echo "A bill issued to a customer." | tcw taxonomy add Invoice   # vocabulary by default
tcw taxonomy add Admin < admin.md
tcw taxonomy add Permission --parent admin                       # -> admin/permission
tcw taxonomy add Note --parent invoice --slug memo               # -> invoice/memo
tcw taxonomy add User < user.md
tcw taxonomy add "User Authentication" --kind feature --vocab user

tcw taxonomy list                  # this project's own entries, one per line
tcw taxonomy list --scope up       # and the entries it inherits
tcw taxonomy show admin/permission # read one entry
tcw taxonomy search invoice        # match names and descriptions
tcw taxonomy path                  # the taxonomy store's folder
```

An entry is a folder holding `tcw-taxonomy.yaml` (its name, kind and links)
and `description.md`. Its description is read from **standard input**, and may
be left empty. Without `--slug`, the last part of the path is made from the
name. A `--slug` you give must already be in that form: lowercase letters and
digits, in words joined by single hyphens, such as `memo` or `credit-note`.
Anything else, a space, a capital letter or a `/` included, is a usage error
(exit code 2) and nothing is created.

`--parent` names the term the new one belongs under, by its full identifier or
its path here, and records it in the new entry's `parent:` field. When the
parent is one of this project's own terms, the new folder is made inside the
parent's; when the parent is inherited, the new folder is made at the top of
this project's store, with `parent:` naming the inherited term.

Feature entries can carry repeatable `--vocab <ref>` links to the vocabulary
they involve. A ref is a full identifier, a path here (an inherited term's
included), or the last part of a path when only one term ends with it; it is
stored as a full identifier. `tcw taxonomy add` refuses a ref that does not
resolve, is ambiguous, or names a feature where a vocabulary entry is
expected, and writes nothing when it refuses; so register vocabulary before
the features that name it. `tcw validate` checks the same refs across the
whole tree. `tcw taxonomy rm` refuses to remove an entry that another entry
still names.

## Bootstrapping a taxonomy or a capabilities ledger

To **bootstrap** a taxonomy or capabilities ledger (the project's set of
capability records) on a project newly adopting TCW, ask for the `setup` skill:
the assistant studies your code, proposes a first draft, refines it with you,
and writes it.

## `tcw capabilities`: the user stories

A capability is a folder under `docs/capabilities/`, holding
`tcw-capability.yaml` (its name and metadata) and `description.md` (its body),
and a `resources/` folder when it has attached documents. Its path is its
identity: the folder's name is its ID, and no other identifier is stored in
its file. Its `tcw-capability.yaml` carries metadata fields from a fixed list:

- **`Status`**, one of `Supported`, `Partial`, `Missing`, `Blocked`, `Omitted`;
- **`Subject`**, a loose, **multi-valued** pointer to taxonomy entries;
- **`Feature`**, a strong pointer to one taxonomy feature;
- `Priority` (`P0` to `P3`), `Lifecycle` (`Experimental`, `Stable`,
  `Deprecated`), `Superseded by`, `Blocked by`, `Roles`, `When` and `Gaps`.

Beside them it may hold `parent:` (the capability this one belongs under),
and `prependedDocs` and `appendedDocs` (attached documents, described under
[Inheriting and overriding](#inheriting-and-overriding)).

A capability never points at a work item. Work items point at capabilities,
through each item's `capabilities.yaml` (see
[From a request to the records](#from-a-request-to-the-records)).

```sh
tcw capabilities add billing/invoices "Download an invoice as PDF" --status Supported < invoices.md
tcw capabilities add billing/invoices/bulk "Download many at once" --status Missing --parent billing/invoices

tcw capabilities list                      # this project's own capabilities
tcw capabilities list --status Missing     # filter by status
tcw capabilities list --scope up           # and the capabilities it inherits
tcw capabilities show billing/invoices     # read one capability by path
tcw capabilities search pdf
tcw capabilities drift                     # see "Drift" below

tcw capabilities set billing/invoices --status Supported
tcw capabilities set billing/invoices --field "Subject=invoice,user"   # multi-valued
tcw capabilities set billing/invoices --field "Gaps="                  # clear a field

tcw capabilities rm billing/invoices/bulk  # delete a local capability
```

A new capability's body is read from standard input. Give its status with
`--status`; without it the status is `Missing`. `set` changes a capability's
status or fields in place; an empty value clears a field. The records change
during the `implement` stage, in the same change as the code they describe.
**`Missing` means a gap the team has acknowledged**: something users cannot do
yet, recorded so that it is visible. It is never a plan.

`--parent`, on `add` and on `set`, records the capability this one belongs
under, by its full identifier or its path here; `set --parent ""` clears it.
On capabilities it records the field only and never moves a folder, so a
nested capability is made at its nested path and given `--parent` as well. One
made inside another capability's folder without `--parent` is created with a
warning that `parent:` is not set.

`rm` deletes one local capability, and each folder above it that the removal
leaves empty, and nothing else. It refuses, deleting nothing, an inherited
capability (it names the project the capability belongs to), one with
capabilities nested under it (so `rm billing/invoices` is refused while
`billing/invoices/bulk` exists), and one another capability
still points at through `Superseded by`, `Blocked by`, `Roles`, `When` or
`parent`.

`tcw validate` checks the metadata, resolves each `Subject` pointer against the
taxonomy, and checks that each `Feature` pointer names a taxonomy feature. The
tool never parses capability prose; it only follows pointers.

`set` resolves those pointers too, and refuses a write carrying one that does
not resolve (exit code 2). Six fields carry references: `Subject`, `Feature`,
`Superseded by`, `Blocked by`, `Roles` and `When`. Every reference in a write
that does not resolve is named at once, and a refused write changes nothing.
So **register a taxonomy Feature before the capability that names it**, and a
`roles/…` capability before the one that lists it.

## Renaming and moving

`rename` changes the last part of a local object's path, and `move` puts its
folder inside another folder (`--into`) or at the top of the store (`--top`).
Both work on the two axes, carry the objects nested in it along, and rewrite
every reference to them in this project's records and documents:

```sh
tcw taxonomy rename invoice bill
tcw capabilities move billing/invoices --into payments
```

Each prints one `<old full id> -> <new full id>` line per identifier it
changed. References in other projects are not rewritten; `tcw validate` in
those projects reports them, so pass the printed identifiers on. An override
(see below) is never renamed or moved, since its path is the inherited
object's: `rename` and `move` refuse it with exit code 3.

## Inheriting and overriding

**Inheritance.** A project inherits the taxonomy and the capabilities of every
parent whose `inherit` includes that axis, configured under `parents:` in
`.tcw/tcw-config.yaml`, and through every level: a parent's own parents pass
down too, as far as each link's `inherit` allows.
[Related projects](multi-repo.md) explains parent links and `inherit`. So a web
frontend and a mobile app that drive the same server declare their shared
vocabulary and user stories once, in a parent both name.

An inherited object keeps the full identifier of the project it belongs to.
Plain `list` and `show` cover the active project's own objects;
`--scope up` adds what it inherits, and
[the command line guide](cli.md) explains `--scope` and `--project`. A project
cannot delete an inherited object, only **override** it.

**An override** is the project's own object at the same path as the inherited
one, holding only what it changes. Nothing in it points at the original: being
at the same path is what makes it an override. Write one exactly as you would
change a local object:

- `tcw capabilities set auth/login --status Omitted` at an inherited path
  writes this project's own `tcw-capability.yaml` there, holding only the
  fields given;
- `tcw taxonomy add` at an inherited path writes an override holding what
  differs from the inherited entry, and says on standard error what it
  overrides, such as `app.taxonomy/user overrides top.taxonomy/user`. It
  refuses, with exit code 3, when nothing given differs.

Adding a capability (`tcw capabilities add <path> --status <status>`) at an
inherited path is refused with exit code 3 and points at `set`, since it would
write a full copy.

`show` names the object an override replaces on its `overrides:` line. This is
an override in project `mobile` of a capability it inherits from `top`, after
`tcw capabilities set auth/login --status Partial`:

```text
full-id: mobile.capabilities/auth/login
owner: mobile
overrides: top.capabilities/auth/login
name: Sign in
Status: Partial

body:
  Sign in with a password.
```

**How the two combine.** The override and the original are combined field by
field: each field the override holds replaces the original's, a field it
leaves out keeps the original's value, a YAML `null` clears the field, and a
list such as `Subject` or `appendedDocs` is replaced whole. The description is
the override's `description.md` when it has text, and the inherited one
otherwise. A capability's body is composed as the documents `prependedDocs`
lists, then that description, then the documents `appendedDocs` lists, each
read from the `resources/` folder of the project that declared the list, for
example a mobile app appending "…or take a photo with the camera." An override
that does not list `prependedDocs` or `appendedDocs` keeps the original's.

**Undoing an override.** `reset` drops the override and inherits again:

```sh
tcw capabilities reset auth/login   # drop the local override, inherit again
```

`reset` removes only your project's own capability at that path, never the
inherited one, and also accepts the overridden capability's full identifier.
It refuses with exit code 3 when there is nothing to drop: a path that
inherits the original unchanged, or a capability that overrides nothing
(delete that with `tcw capabilities rm`). It also refuses while another of
your project's own capabilities or terms names the override by its full
identifier; repoint it at the overridden capability's full identifier first.
And it refuses when a capability sits in a folder under the override's, since
removing the override folder would delete it too; the message names each one.
Delete a local one with `tcw capabilities rm` and drop a nested override with
`tcw capabilities reset` first, then reset again.

`tcw capabilities rm` and `tcw taxonomy rm` also remove an override, and each
says what the path shows afterwards, such as
`auth/login now shows top.capabilities/auth/login`.

**An override whose original moved.** An object that overrides nothing must be
complete on its own: a name, for a capability a `Status`, and a
`description.md`, which may be empty. When the original is moved or removed in
its own project, the override is left overriding nothing, and `tcw validate`
reports it as incomplete:

```text
error: docs/capabilities/billing/invoices/tcw-capability.yaml: app.capabilities/billing/invoices is incomplete: it overrides nothing, and has no name, Status or description.md; if it overrode an object that moved or was removed, complete it or remove it
```

**Two unrelated parents at one path.** When two projects the active project
inherits from each have an object at the same path, and neither inherits it
from the other, the active project uses the one that comes later in its load
order (the order its sources are read in, which
[Related projects](multi-repo.md) explains), and warns when it lists the
path (`tcw capabilities list --scope up`, for example) and in `tcw validate`:

```text
warning: capabilities web/search: 'left' and 'right' each have an object at this path, and neither inherits it from the other; 'both' uses the one from 'right', which comes later in its load order, and nothing from 'left''s; to choose for yourself, give 'both' a complete object of its own at web/search (a name, a Status and a description), holding every field you want
```

**A parent not on this machine.** Finding a parent's folder is about this
machine only; parent links, inheritance and overrides are what every store
keeps. When a parent that passes an axis cannot be found here, a listing of
this project's own objects warns and shows only its own declarations, an
override shows `partial: inherited content could not be read`, and a command
that needs the inherited content (`--scope up`, `set` at an inherited path,
`reset`, `drift`) exits with code 7. [Related projects](multi-repo.md) says how
TCW finds a project's folder.

## How records mark overrides

A plain `list` prints one full identifier per line, an override's included,
with no mark: the identifier names the active project, and nothing more is
printed. The records carry the marks:

- `--json` gives each object `overrides`: the full identifier of the object it
  overrides, or `null`. An override whose inherited content could not be read
  carries `partial: true` in its place.
- Under `--scope down` and `all`, each record also carries `overridden-by`:
  the full identifiers of the objects in the covered projects that override
  it. `show` prints the same as an `overridden by:` line.
- The web app (`tcw serve`, described in [The web app](web-viewer.md)) reads
  the same records, and an override's page shows the line `overrides` and the
  full identifier under its heading.

## Mixed status across a family

A capability inherited by several projects can have a different status in
each, when some of them override its `Status`. Under `--scope down` (the
active project and its descendants) and `--scope all` (its ancestors as well),
the records say each project's status. The plain listing stays one identifier
per line and shows none of it:

```sh
tcw capabilities list --scope down
tcw capabilities list --scope down --json   # each record's "statuses"
tcw capabilities show auth/login --scope down
```

Read mixed status from `--json` or from `show`, never from a plain listing. In
`--json`, each capability record carries `statuses`, one entry per covered
project: its `project`, its `status`, whether it is `inherited` unchanged, and
the `full-id` of the object that project sees there. `show` groups the same by
status. Here project `top` declares `auth/login`, `shared` inherits it
unchanged, and its children `app` and `mobile` override its status:

```text
full-id: top.capabilities/auth/login
owner: top
overridden by: app.capabilities/auth/login, mobile.capabilities/auth/login
name: Sign in
Status: Supported
status by project:
  Supported: top, shared (inherited)
  Omitted: app
  Partial: mobile

body:
  Sign in with a password.
```

Taxonomy entries have no status, so their records under `down` and `all` carry
`overridden-by` and no `statuses`.

## From a request to the records

A change to the product is described at each stage, each time more precisely,
until the records themselves change:

1. **Request.** The request says in plain prose what users will be able to do
   differently, in its "Product changes" section. "None" is a valid answer.
2. **Spec.** The spec declares the changes formally, in `capabilities.yaml` at
   the root of the item's folder, naming each capability and term by its full
   identifier:

    ```yaml
    new: [shop.capabilities/billing/refund-a-payment]
    changed: [shop.capabilities/billing/view-a-payment]
    removed: [shop.capabilities/billing/legacy-export]
    taxonomy:
        new: [shop.taxonomy/refund]
        changed: []
        removed: []
    ```

    Each key is optional. `new`, `changed` and `removed` list capabilities;
    `taxonomy` lists terms the same way. A 3.x `capabilities.yaml` lists bare
    paths; `tcw migrate` rewrites them as full identifiers.

3. **Implement.** The records are changed with
   `tcw capabilities add <path> --status <status>`, `set` and `rm` (and
   `tcw taxonomy add` and `rm`), in the same change as the code.
4. **The records gate**, on any move into the stage after `implement`, checks
   each entry in the store of the project its full identifier names, against
   that project's own object at the path: everything `new` or `changed`
   exists, a `new` capability's status is not still `Missing`, and everything
   `removed` is gone. An entry is satisfied only by an object of the named
   project's own, so a project that changes an inherited capability declares
   its override under its own ID. A path removed from a project that still
   shows an inherited object there counts as removed.
5. **QA** checks the product's behavior against the request.

While the item is still being worked, `tcw validate` reports only what cannot
be right at any point: a `capabilities.yaml` that cannot be read, an unknown
key, and an entry that cannot be checked, such as one in the 3.x form or one
naming a project that keeps no store for that axis. A change not made yet is
not reported until the gate.

### A project with no ledger of its own

A project that keeps no capabilities ledger, such as a planning project made
with `tcw project new work --id planning`, declares changes in another
project's ledger by naming that project in each entry:

```yaml
new:
    - shared-app.capabilities/authoring/add-a-claim # checked in shared-app's ledger
```

The records gate checks the entry in `shared-app`'s ledger, so the record is
changed in that project, with `tcw capabilities add <path> --status <status>`
run there. Any project
TCW can find on this machine can be named this way, whether or not either
project inherits from the other. An entry naming the planning project itself
cannot be checked; `tcw validate` reports it as an error, and the records gate
names it:

```text
planning.capabilities/authoring/local-thing: could not be checked: this project ('planning') keeps no capabilities ledger; name the ledger's project in the entry (<project>.capabilities/authoring/local-thing)
```

`tcw capabilities list` and `drift` in such a project exit with code 1 and say
there is no capabilities store here.

## Drift

`tcw capabilities drift` compares what finished work said with what the records
say today, and also lists inherited capabilities nobody here has ruled on. It
prints one finding per line, `<kind>: <path>: <message>`, where the second part
is the capability's full identifier (or, for an unreadable declaration, the
work item), prints nothing when there is none, and exits with code 1 when it
found anything, so a continuous-integration job can run it. The kinds are:

- **`unreviewed`**: an inherited capability this project has never overridden,
  so its status is still the one it inherits, such as
  `unreviewed: shared.capabilities/payments/invoices: inherited, and its status is still the one it inherits; never ruled on here`;
- **`drift`**: a completed item declared a change that today's records do not
  show. For each capability or term, the **newest declaration wins**, by the
  item's creation date, so a later item that declares it differently
  supersedes an earlier one;
- **`ambiguous`**: the newest declarations of one capability disagree, because
  items created on the same day declare it both kept and removed;
- **`unchecked`**: a declaration that could not be checked, such as a
  `capabilities.yaml` that cannot be read.

In Jira mode, drift asks Jira which items are completed, so it needs the
network. When the project's Jira settings come from a parent that is not on
this machine, drift exits with code 7 before contacting Jira, naming the
missing project and the setting (`work.jira`) it would supply.
