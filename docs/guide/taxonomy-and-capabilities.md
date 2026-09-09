# Taxonomy and Capabilities

Taxonomy holds the nouns — the things the project deals with. Capabilities hold
the user stories — what someone can do with those things. A capability points at
taxonomy entries; taxonomy never points back.

Both groups have a `--help` and a `check` that validates the tree, and both take
a bare-path shortcut (`tcw taxonomy <path>` is `tcw taxonomy show <path>`) —
except that `path` itself is reserved as the store-location command, so use an
explicit `show path` to read an object actually named `path`.

See also [The Work component](work.md) and
[Working across repositories](multi-repo.md).

## `tcw taxonomy` — the nouns

Taxonomy entries form a **forest, and the slug _is_ the path**:
`admin/permission` is a different entry from `billing/permission`, and addressing
is by that path. Entries have two kinds: **Vocabulary** for the fundamental
language of the project, and **Feature** for the user- or application-facing
manifestations that operate on or involve vocabulary.

```sh
tcw taxonomy add Invoice "A bill issued to a customer."     # vocabulary by default
tcw taxonomy add Permission -p admin                        # -> admin/permission
tcw taxonomy add Note -p invoice -s memo                    # custom leaf slug
tcw taxonomy add "User Authentication" --kind feature --vocab user

tcw taxonomy list                  # the forest, indented, flagged by origin
tcw taxonomy list --local          # local terms only (hide imported)
tcw taxonomy show admin/permission # read one term (or: tcw taxonomy admin/permission)
tcw taxonomy search invoice        # match names + descriptions
tcw taxonomy check                 # validate inheritance + references

tcw taxonomy extends add acme-shared   # inherit a registered project
tcw taxonomy extends rm acme-shared    # drop the import
```

A taxonomy entry's body comes from the argument or from **stdin** (`echo "..." | tcw
taxonomy add Foo`). Feature entries can carry repeatable `--vocab <ref>` links
to the vocabulary they involve. A ref is a term path (`admin/permission`), a
`<project-id>/<path>` into an inherited taxonomy, or a leaf slug that is unique
across your own terms — which is stored as its full path. `tcw taxonomy add`
refuses a ref that does not resolve, is ambiguous, or names a feature where a
vocabulary entry is expected, and writes nothing when it refuses; so register
vocabulary before the features that name it. `tcw taxonomy check` validates the
same refs across the whole tree.
Taxonomies can **federate**: `tcw taxonomy extends add <project-id>` writes the
registered source ID to the `extends` list in `config.yaml`. Each project ID is
its own namespace, including sources inherited transitively, and there is **no
silent merge** — a local `permission` and an imported `acme/permission` stay
distinct. Capabilities federate separately and additionally let a
consumer **override** an inherited entry per-project (see `tcw capabilities`
above).

To **bootstrap** a taxonomy or capabilities ledger on a project newly adopting
TCW, run `/tcw-taxonomy-init` or `/tcw-capabilities-init`: the assistant studies
your code, proposes a first draft, refines it with you, and writes it.

## `tcw capabilities` — the user stories

A capability is a **path-addressed folder** (`docs/capabilities/<path>/` holding
`meta.yaml` + `description.md`) with an opaque stable `id`. It carries metadata
fields — notably **`Subject:`** (a loose, **multi-valued** pointer to taxonomy
entries), **`Feature:`** (a strong pointer to a taxonomy feature), and
**`Planning doc:`** (the forward pointer to a work item).

```sh
tcw capabilities add billing/invoices "Download an invoice as PDF"   # mints a stable id
tcw capabilities add billing/invoices/bulk "Download many at once"    # nested path

tcw capabilities list                      # every capability, flagged by status + origin
tcw capabilities list --status Missing     # filter by status
tcw capabilities list --local-only         # hide inherited (federated) capabilities
tcw capabilities show billing/invoices     # read one capability by path
tcw capabilities search pdf
tcw capabilities check                     # paths, metadata vocab, Subject/Feature, federation
tcw capabilities drift                     # inherited-but-unreviewed + shipped-but-Missing (CI-usable)

tcw capabilities set billing/invoices --status Supported
tcw capabilities set billing/invoices --field "Subject=invoice,billing"   # multi-valued
tcw capabilities set billing/invoices --field "Planning doc=2026-06-19-pdf-export"
```

`set` updates a capability's status/fields in place (stage-only) — the mechanism
the work→capability lifecycle uses to flip `Missing → Supported` at completion.

Status is one of `Supported · Partial · Missing · Blocked · Omitted`. `check`
validates the metadata vocabulary, resolves each `Subject:` pointer against the
taxonomy store, and verifies that each `Feature:` pointer resolves to a taxonomy
feature. The tool never parses capability prose; it only follows pointers.

`set` resolves those pointers too, and refuses a write carrying one that does
not — with the same message `check` reports, from one shared renderer. Six
fields carry references: `Subject`, `Feature`, `Superseded by`, `Blocked by`,
`Roles` and `When`. All bad references in a write are named at once, and a
refused write changes nothing. So **register a taxonomy Feature before the
capability that names it**, and a `roles/…` capability before the one that
lists it.

**Federation.** Capabilities can `extends` another project's — so a web frontend
and a mobile app that drive the same server declare their shared user stories
once:

```sh
tcw capabilities extends web-frontend       # inherit a registered project
tcw capabilities extends web-frontend --rm  # drop it
```

Inherited capabilities surface flagged by origin (`web-frontend/<path>`) and are
read-only in structure — a project can't delete one, only **override** it. Set an
inherited capability exactly like a local one, by any path `show` accepts:

```sh
tcw capabilities set web-frontend/auth/login --status Omitted
```

The override is written for you. It is a local folder whose `meta.yaml` has
`overrides: <upstream-id>` plus the changes: metadata fields partial-merge (e.g.
`Status: Missing`, or `Status: Omitted` for "we deliberately don't have this"; a
YAML `null` clears a field), and the body composes as `prependedDocs` + (a local
`description.md`, if present, else the upstream body) + `appendedDocs` — e.g. a
mobile app appending "…or take a photo with the camera." That file shape is
worth knowing (you can hand-author one anywhere, and `set` will keep using it),
but `set` is the front door. Local sibling-repo paths only.

To undo an override and go back to the upstream value, `reset` it:

```sh
tcw capabilities reset shared/auth/login   # drop the local override, re-inherit upstream
```

`reset` removes only your local override folder (never the upstream node). It
refuses with a clear message when there's nothing to drop — a standalone local
capability (use `remove`) or a path that already inherits verbatim.
