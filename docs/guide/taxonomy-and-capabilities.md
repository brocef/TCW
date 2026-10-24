# Taxonomy and Capabilities

Taxonomy holds the nouns: the things the project deals with. Capabilities hold
the user stories: what someone can do with those things. A capability points at
taxonomy entries; taxonomy never points back. Both are folders of files in the
repository, and both change in the same commit as the code they describe.

Each group has a `--help` on every command, and `tcw validate` checks both
trees, with everything else in the project.

See also [The Work component](work.md),
[Linking and validation](linking-and-validation.md) and
[Working across repositories](multi-repo.md).

## `tcw taxonomy`: the nouns

Taxonomy entries form a **forest, and the slug _is_ the path**:
`admin/permission` is a different entry from `billing/permission`, and addressing
is by that path. Entries have two kinds: **Vocabulary** for the fundamental
language of the project, and **Feature** for the user- or application-facing
features that operate on or involve vocabulary.

```sh
echo "A bill issued to a customer." | tcw taxonomy add Invoice   # vocabulary by default
tcw taxonomy add Admin < admin.md
tcw taxonomy add Permission --parent admin                       # -> admin/permission
tcw taxonomy add Note --parent invoice --slug memo               # custom leaf slug
tcw taxonomy add User < user.md
tcw taxonomy add "User Authentication" --kind feature --vocab user

tcw taxonomy list                  # every entry's path, one per line
tcw taxonomy list --local          # local entries only, none inherited
tcw taxonomy show admin/permission # read one entry
tcw taxonomy search invoice        # match names and descriptions
tcw taxonomy path                  # the taxonomy store's folder
```

An entry's description is read from **standard input**, and may be left empty.
Without `--slug` the leaf slug is made from the name. A `--slug` you give must
already be in that form: lowercase letters and digits, in words joined by
single hyphens, such as `memo` or `credit-note`. Anything else, a space, a
capital letter or a `/` included, is a usage error (exit code 2) and nothing
is created; nesting an entry under another is what `--parent` is for.
Feature entries can carry repeatable `--vocab <ref>` links to the vocabulary
they involve. A ref is a term path (`admin/permission`), a
`<project-id>/<path>` into an inherited taxonomy, or a leaf slug that is unique
across your own terms, which is stored as its full path. `tcw taxonomy add`
refuses a ref that does not resolve, is ambiguous, or names a feature where a
vocabulary entry is expected, and writes nothing when it refuses; so register
vocabulary before the features that name it. `tcw validate` checks the same
refs across the whole tree. `tcw taxonomy rm` refuses to remove an entry that
another entry still names.

A project **inherits** the taxonomy of every parent whose `inherit` includes
`taxonomy`, through every level, as configured under `parents:` in
`.tcw/tcw-config.yaml` (the `configure` skill's
[projects reference](../../skills/configure/references/projects.md) explains
it). An inherited entry is read by its path like one of your own, and its full
identifier (`acme-shared.taxonomy/permission`) names the project it belongs to.
To change an inherited entry, put your own entry at the same path, holding only
what you change: an **override**. `tcw taxonomy add` at an inherited path
writes one, holding only what differs from the inherited entry, and says on
standard error what it overrides; `tcw taxonomy rm` removes it. Capabilities
are inherited and overridden the same way (see below).

## Bootstrapping a taxonomy or a capabilities ledger

To **bootstrap** a taxonomy or capabilities ledger on a project newly adopting
TCW, ask for the `setup` skill: the assistant studies your code, proposes a
first draft, refines it with you, and writes it.

## `tcw capabilities`: the user stories

A capability is a **path-addressed folder** (`docs/capabilities/<path>/` holding
`meta.yaml` and `description.md`); its path is its identity, and it has no
separate `id`. Its `meta.yaml` carries metadata fields from a fixed list:

- **`Status`**, one of `Supported`, `Partial`, `Missing`, `Blocked`, `Omitted`;
- **`Subject`**, a loose, **multi-valued** pointer to taxonomy entries;
- **`Feature`**, a strong pointer to one taxonomy feature;
- `Priority` (`P0` to `P3`), `Lifecycle` (`Experimental`, `Stable`,
  `Deprecated`), `Superseded by`, `Blocked by`, `Roles`, `When` and `Gaps`.

A capability never points at a work item. Work items point at capabilities,
through each item's `capabilities.yaml` (see
[From a request to the records](#from-a-request-to-the-records)).

```sh
tcw capabilities add billing/invoices "Download an invoice as PDF" < invoices.md
tcw capabilities add billing/invoices/bulk "Download many at once"    # nested path

tcw capabilities list                      # every capability's path
tcw capabilities list --status Missing     # filter by status
tcw capabilities list --local              # hide inherited capabilities
tcw capabilities show billing/invoices     # read one capability by path
tcw capabilities search pdf
tcw capabilities drift                     # see "Drift" below

tcw capabilities set billing/invoices --status Supported
tcw capabilities set billing/invoices --field "Subject=invoice,user"   # multi-valued

tcw capabilities rm billing/invoices/bulk  # delete a local capability
```

A new capability's body is read from standard input, and its status is
`Missing` unless `--status` says otherwise. `set` changes a capability's status
or fields in place. The records change during the `implement` stage, in the
same change as the code they describe. **`Missing` means a gap the team has
acknowledged**: something users cannot do yet, recorded so that it is visible.
It is never a plan.

`rm` deletes one local capability and nothing else. It refuses, deleting
nothing, an inherited capability, one with capabilities nested under it (so
`rm billing/invoices` is refused while `billing/invoices/bulk` exists), and one
another capability still points at through `Superseded by`, `Blocked by`,
`Roles` or `When`.

`tcw validate` checks the metadata, resolves each `Subject` pointer against the
taxonomy, and checks that each `Feature` pointer names a taxonomy feature. The
tool never parses capability prose; it only follows pointers.

`set` resolves those pointers too, and refuses a write carrying one that does
not resolve, with the same message `tcw validate` reports. Six fields carry
references: `Subject`, `Feature`, `Superseded by`, `Blocked by`, `Roles` and
`When`. All bad references in a write are named at once, and a refused write
changes nothing. So **register a taxonomy Feature before the capability that
names it**, and a `roles/…` capability before the one that lists it.

## From a request to the records

A change to the product is described at each stage, each time more precisely,
until the records themselves change:

1. **Request.** The request says in plain prose what users will be able to do
   differently, in its "Product changes" section. "None" is a valid answer.
2. **Spec.** The spec declares the changes formally, in `capabilities.yaml` at
   the root of the item's folder:

   ```yaml
   new: [billing/refund-a-payment]
   changed: [billing/view-a-payment]
   removed: [billing/legacy-export]
   taxonomy:
       new: [refund]
       changed: []
       removed: []
   ```

   Each key is optional. `new`, `changed` and `removed` list capability paths;
   `taxonomy` lists term paths the same way.
3. **Implement.** The records are changed with `tcw capabilities add`, `set`
   and `rm` (and `tcw taxonomy add` and `rm`), in the same change as the code.
4. **The records gate**, on any move into the stage after `implement`, checks
   that the records match the declaration: everything `new` or `changed` exists, a `new`
   capability's status is not still `Missing`, and everything `removed` is gone.
   A `removed` path naming an inherited capability is refused outright, since
   `rm` could never delete it.
5. **QA** checks the product's behavior against the request.

While the item is still being worked, `tcw validate` reports only what cannot
be right at any point: a `capabilities.yaml` that cannot be read, an unknown
key, a path that cannot be checked, and the removal of an inherited capability.
A change not made yet is not reported until the gate.

### A project with no ledger of its own

A work item in a project that keeps no capabilities ledger, such as a planning
project, can declare changes in a child project's ledger by starting the path
with the child's project ID:

```yaml
new:
    - shared-app/authoring/add-a-claim   # checked in shared-app's ledger
```

The records gate checks the rest of the path in that child's ledger, so the
child's record is changed in the child project.

## Drift

`tcw capabilities drift` compares what finished work said with what the records
say today, and also lists inherited capabilities nobody here has ruled on. It
prints one finding per line, `<kind>: <path>: <message>`, nothing when there is
none, and exits with code 1 when it found anything, so a continuous-integration
job can run it. The kinds are:

- **`unreviewed`**: an inherited capability whose status is still the upstream
  default, never ruled on in this project;
- **`drift`**: a completed item declared a change that today's records do not
  show. For each path, the **newest declaration wins**, by the item's creation
  date, so a later item that declares a path differently supersedes an earlier
  one;
- **`ambiguous`**: the newest declarations of one path disagree, because items
  created on the same day declare it both kept and removed;
- **`unchecked`**: a declaration that could not be checked, such as a
  `capabilities.yaml` that cannot be read.

In Jira mode, drift asks Jira which items are completed, so it needs the
network.

## Inheriting and overriding a capability

**Inheritance.** A project inherits the capabilities of every parent whose
`inherit` includes `capabilities`, configured under `parents:` as for the
taxonomy, so a web frontend and a mobile app that drive the same server
declare their shared user stories once, in a parent both name.

Inherited capabilities are listed by their path, and each one's full
identifier names the project it belongs to
(`web-frontend.capabilities/auth/login`). A project cannot delete one, only
**override** it. Set an inherited capability exactly like a local one:

```sh
tcw capabilities set auth/login --status Omitted
```

The override is written for you: it is your project's own capability at the
same path, holding only the fields you gave, and nothing in it points at the
original (there is no `overrides:` key). The two are combined field by field
(for example `Status: Missing`, or `Status: Omitted` for "we deliberately do
not have this"; a YAML `null` clears a field; a list such as `Subject` or
`appendedDocs` is replaced whole), and the body is composed as
`prependedDocs`, then your `description.md` if it has text or else the
inherited description, then `appendedDocs`, for example a mobile app appending
"…or take a photo with the camera." An override that does not list
`prependedDocs` or `appendedDocs` keeps the original's. `tcw capabilities add`
at an inherited path is refused and points at `set`, since it would write a
full copy. A capability that overrides nothing must be complete (a name, a
`Status` and a `description.md`, which may be empty), so `tcw validate`
reports an override whose original was moved or removed.

To undo an override and go back to the inherited capability, `reset` it:

```sh
tcw capabilities reset auth/login   # drop the local override, inherit again
```

`reset` removes only your project's own capability at that path, never the
inherited one, and also accepts the overridden capability's full identifier.
It refuses with a clear message when there is nothing to drop: a capability
that overrides nothing (delete that with `tcw capabilities rm`) or a path your
project has nothing of its own at. It also refuses while another of your
project's own capabilities or terms names the override by its full
identifier; repoint it at the overridden capability's full identifier first.
It also refuses, with exit code 3, when a capability sits in a folder under
the override's, since removing the override folder would delete it too; the
message names each one. Delete a local one with `tcw capabilities rm` and drop
a nested override with `tcw capabilities reset` first, then reset again.
`tcw capabilities rm` also removes an override, and says what the path shows
afterwards.
