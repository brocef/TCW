# Linking and validation

How one TCW object references another, and the single command that checks a
whole project.

## `tcw://` links: reference a TCW object

Any object's body prose can point at another TCW object with a `tcw://` link:

```
tcw://[<project-id>/]<axis>/<ref>
```

- `<axis>` is `T` (Taxonomy), `C` (Capabilities), or `W` (Work).
- `<project-id>` (optional) locates the object in another project: for `W`, a
  project this one is connected to; for `T` and `C`, a project listed by that
  axis's `extends`. Absent means this project.
- `<ref>` is the identifier within that axis: a taxonomy path, a capability
  path, or a work item's folder name.

```markdown
See [Read a capability](tcw://C/capabilities/read-a-capability) and the
[reference](tcw://T/reference) term, or work item [tcw://W/2026-01-01-x](tcw://W/2026-01-01-x).
```

These are ordinary inline Markdown links, so any Markdown viewer shows them as
links, and [the local web viewer](web-viewer.md) follows them inside the app.
They are additional to the structured pointers (a capability's `Subject` and
`Feature`, a work item's `parent` and `blocked-by`), not a replacement for
them. TCW never rewrites stored Markdown.

## `tcw validate`: one check of the whole project

`tcw validate` checks the project it is run in: its configuration, its
connections to other projects, its taxonomy, capabilities and work stores
wherever each lives (moved with `<component>.path`, or kept in another
repository with `<component>.repository`), and its work items.

```sh
tcw validate            # everything, without contacting anything
tcw validate --remote   # also check a Jira-mode project against Jira
```

**`tcw validate` never needs the network.** In Jira mode it checks the item
folders and their files, and nothing Jira holds, so the work-item checks that
need an item's properties wait for `--remote` (see
[Work items](#what-it-checks) below). `tcw validate --remote` also reads Jira,
changing nothing there, as [the Jira guide](jira.md#checking-the-workflow)
describes.

### What it prints

It prints one **finding** per line on standard output,
`<severity>: <where>: <message>`, and nothing when the project is clean. Each
finding has one of three severities:

- **`error`**: something is wrong and must be fixed;
- **`warning`**: something is probably wrong, or will become a problem;
- **`unresolved`**: TCW cannot tell, because what it would need to look at
  cannot be reached from here, such as a connected project that is declared
  but not on this machine. It is neither a warning nor an error.

A count of each closes the run, on standard error. A check that was skipped is
not a finding: standard error says what was skipped and why. `tcw validate`
exits with code 1 when there is any error, and 0 otherwise; with `--remote`, 5
when Jira could not be reached. The other codes are in
[the command-line guide](cli.md#exit-codes).

### What it checks

- **Configuration.** Every problem in `tcw-config.yaml` and in personal
  configuration, each named by its key. A `tcw-config.local.yaml` (your
  personal configuration file for this project) that git tracks is a
  **warning**: it is meant to stay out of version control.
- **Connected projects.** A connection declared on one side only; a declared
  project that is not on this machine (**unresolved**); `TCW_PROJECT_<ID>`
  variables in effect, listed on standard error.
- **YAML files** in the stores load cleanly, duplicate keys included.
- **Records of the wrong shape**: see below.
- **`tcw://` links** in every Markdown file of the stores resolve. Links inside
  code spans and fenced code are ignored, so documents that teach the scheme do
  not fail themselves.
- **Taxonomy and capabilities**: metadata, pointers between records, and
  inheritance (including inheritance cycles).
- **Work items.** With the filesystem backend, plain `tcw validate` runs every
  check below. In a Jira-mode project the stage, parent and blocking items are
  kept in Jira, so plain `tcw validate` checks only each item folder's name and
  its `item.yaml`, a ticket key used by two folders, a record folder for a
  stage Jira keeps, and the latest `review` round. The `parent` and
  `blocked-by`, stage-ahead and `capabilities.yaml` checks run only under
  `tcw validate --remote`, which reads each item's properties from Jira.
  - an `item.yaml` that cannot be read is an **error**;
  - a `parent` or `blocked-by` naming an item that does not exist is a
    **warning**;
  - an item whose stage is ahead of its documents, such as an item at
    `implement` with nothing from `spec`, is a **warning** until the item is
    finished;
  - a reference into a project that cannot be reached from here is
    **unresolved**;
  - the latest `review` or `qa` round with no usable `verdict` and `judges` is a
    **warning**, because `tcw work advance` refuses past that stage until it
    has them.
- **Each unfinished item's `capabilities.yaml`**, the records it declares it
  changes. While the item is being worked, only what cannot be right at any
  point is reported: a file that cannot be read or is malformed, an unknown
  key, a path that cannot be checked, and the removal of a capability the
  project inherits, which `rm` could never delete. A change not made yet is not
  reported; the records gate checks those when the item moves into the
  stage after `implement`.

### A record of the wrong shape

A YAML file TCW writes as a record, `item.yaml` or `meta.yaml`, has to be a
mapping (a set of `key: value` lines). One that is not is reported by name:

```
error: docs/capabilities/billing/invoices/meta.yaml: expected a mapping, found list
```

A work item's `item.yaml` that is not a mapping is reported as unreadable, and
standard error says that the references in it were not checked.

Any _other_ YAML under the scanned trees may be any shape at all: a work item's
`capabilities.yaml`, or an attachment kept beside an item, is not held to this
rule.

### A leftover inheritance file from before 2.5.0

Before 2.5.0 a project listed the projects it inherits from in a file inside
the tree: `config.yaml` at the root of the taxonomy, `.config.yaml` at the root
of the capabilities ledger. That list lives in `tcw-config.yaml` from 2.5.0 on,
and TCW does not read the old file. `tcw validate` reports one wherever the
tree lives, once per tree, and names the key in `tcw-config.yaml` to move its
list to.

The fix is to copy any `extends` you still need into `tcw-config.yaml` and
delete the file. The report stays until the file is gone, even if you already
copied the list. TCW never edits or deletes it.
