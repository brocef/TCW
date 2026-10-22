# Spec — TCW 4.0: inheriting taxonomy and capabilities, and overrides by path

Child 7 of 13 of TCW-99. It carries out these sections of the TCW-99 design
(`docs/work/TCW-99-…/design.md`): "What is inherited" for taxonomy and
capabilities (design.md:448-481), the parts of "Multiple parents, and which
value wins" that decide an object (design.md:398-417), the part of "A related
project that is not on this machine" that concerns inherited taxonomy and
capabilities (design.md:380-396), "Overriding an inherited object is allowed"
(design.md:584-585), and the `overrides:` and `extends` lines of "Versions and
migration" that say what replaces them (design.md:724-732, :741-744).

**Order.** The children land on the `v4` branch in the order TCW-106,
TCW-107, TCW-110, TCW-108, TCW-111, TCW-109, then this item (the dispatching
session, 2026-10-22). So when this item starts:

- every project has `.tcw/tcw-config.yaml` and every file TCW writes carries
  `tcw-version` (TCW-106);
- a project's folder is found from its ID by TCW-107's lookup, through the
  command's one registry (TCW-107 Design 2.11-2.13, TCW-110 Design 6.1);
- every object has a full identifier `<project>.<namespace>/<id-path>`, and
  every record and command prints it (TCW-110 Design 1, 4);
- a project names its parents under `parents:`, each with what it passes
  down (`inherit`), and the registry answers `load_order()` and
  `sources(axis)`, raising `InheritedUnavailable` (exit 7) when a project
  that would pass the axis cannot be read (TCW-108 Design 3.2, 4, 5, 6.2);
- an object is a folder holding its namespace's state file
  (`tcw-taxonomy.yaml`, `tcw-capability.yaml`), with `resources/` for its other
  files and an optional `parent:` (TCW-111 Design 1-3);
- TCW-109 has made configuration inherit through the same links.

Between them, those items keep three interim rules that this item replaces:
`extends` held to the parent links (TCW-108 Design 3.6, 6.3), an inherited
object read and written through the active project's view (TCW-110 Design
3.1, 6.2), and the 3.x `overrides:` pointer and opaque capability `id`, kept as
they were inside the new state files (TCW-111 Design 1.3, 2.5).

File and line references to code are to commit `67c4c15a` on `v4`, where no
4.0 code item has landed in `tcw/` yet (its `tcw/` is identical to `05d42988`,
the commit the sibling specs cite, and to `9f43d5f6`, where this spec was
revised). TCW-108, TCW-110 and TCW-111 rewrite much
of what is cited, so the plan re-checks each reference against what they
land. "TCW-108 Design n", "TCW-110 Design n" and "TCW-111 Design n" refer to
the numbered rules of those items' specs.

Words used throughout:

- The **active project** is the project the command runs in (design.md:55-56).
- An **axis** is `taxonomy` or `capabilities` here (TCW-108's `AXES` also
  holds `config`, which TCW-109 handles).
- A project's **sources** for an axis are TCW-108 Design 5.2's
  `sources(axis)`: the projects that pass that axis to it, in load order,
  ending with the project itself.
- A project's **own objects** are the objects in its own store: the folders
  holding the state file there (TCW-111 Design 2.5). Its **own declaration** of
  an object is what that folder holds, read alone.
- A project's **view** of an axis is what it sees there: every id-path any of
  its sources has an object at, each combined from the sources as Design 2
  says.
- To **fold** a list of declarations is to start from the first and lay each
  later one over the result, so that a later value replaces an earlier one.
- An **override** is one of a project's own objects at an id-path where an
  earlier source also has an object (design.md:456-462). It is an ordinary
  object of that project: nothing in its files says it is an override.

Every project ID in the criteria is valid and lower case (TCW-106's rule).
The design's capital letters are written doubled (`B` is `bb`), as TCW-108
does.

## Capability changes

- **New** `taxonomy/override-an-inherited-term`: a project changes an
  inherited term by putting its own term at the same path, holding only what
  it changes; the two are combined field by field, and the listing's records
  and `show` name the term it overrides. `tcw taxonomy add` at an inherited
  path writes such a term, holding only what differs from the inherited one.
- **Changed** `taxonomy/federate-shared-vocabulary` and
  `capabilities/federate`: a project inherits taxonomy and capabilities from
  every parent whose `inherit` includes the axis, through every level;
  `taxonomy.extends`, `capabilities.extends` and `tcw taxonomy|capabilities
  extends add|rm` are gone.
- **Changed** `capabilities/override-inherited`: an override is the
  project's own capability at the same path, with no `overrides:` pointer; it
  holds only what it changes and is combined with the original field by field.
- **Changed** `capabilities/set-a-capabilitys-status`: on an inherited
  capability, `set` writes the project's own capability at the same path,
  holding only the fields given; `--parent` is accepted there too; a field
  cleared on any of the project's own capabilities is written as `null`.
- **Changed** `capabilities/reset-an-override`: drops the project's own
  object at an inherited path; accepts the overridden object's full
  identifier; refused while the project's own references name the override.
- **Changed** `capabilities/remove-a-capability` and
  `taxonomy/remove-a-local-term`: `rm` removes any of the project's own
  objects, an override included, and says what the path shows afterwards.
- **Changed** `capabilities/add-a-capability`: refused at a path the project
  already inherits an object at, naming `tcw capabilities set`; a new
  capability's state file holds no `id`.
- **Changed** `taxonomy/add-a-term`: at a path the project already inherits a
  term at, writes an override holding only what differs from that term, and
  says what it overrides.
- **Changed** `capabilities/read-a-capability`, `taxonomy/read-a-term`,
  `capabilities/browse-capabilities-by-status`,
  `taxonomy/browse-the-term-forest`, `capabilities/search-capabilities`,
  `taxonomy/search-terms`: one entry per id-path, combined from the sources;
  `overrides` in every record and in `show`; no capability `id`; listings warn
  where two unrelated projects have an object at one path; reading the
  project's own objects works when a parent is not on this machine, and each
  record read that way is marked `partial`.
- **Changed** `capabilities/validate-capabilities`,
  `taxonomy/validate-the-taxonomy`, `cli/validate-a-project`: an object that
  overrides nothing must be complete; two unrelated projects at one path are
  a warning, until a project that inherits from both has a complete object of
  its own there; inherited content that cannot be read is "could not check"; the
  federation checks and the `overrides:` pointer checks are gone.
- **Changed** `capabilities/detect-capability-drift`: "never ruled on here"
  means the project has no object of its own at that path that sets `Status`;
  it stops with exit 7 when inherited capabilities cannot be read.
- **Changed** `capabilities/configure-the-capabilities-store-location`,
  `cli/reference-a-tcw-object`, `cli/read-from-an-upstream-project` (whose
  description still says a project "`extends` its taxonomy and
  capabilities"; TCW-108 changes the record first, while `extends` exists),
  `work/declare-capability-changes-in-a-child-projects-ledger`: inheritance
  comes from parent links, and a full identifier names its owner's object as
  its owner sees it.
- **Changed** `web/editing`: a project's own override is editable in
  `tcw serve`, and the record says what it overrides; editing a
  capability's body changes only its own description, never the attached
  documents or an inherited description shown with it.
- **Taxonomy:** new `override`.

## Problem

1. **Inheritance has its own mechanism.** A store inherits only from the
   projects listed in `taxonomy.extends` or `capabilities.extends`
   (`_extends_ids`, `tcw/store/fs.py:904-933`), which `tcw taxonomy|capabilities
   extends add|rm` edits (`:1963-1988`, `:2718-2743`; the CLI groups at
   `tcw/taxonomy/cli.py:190-201` and `tcw/capabilities/cli.py:297-308`), and
   which the abstract stores declare (`tcw/store/base.py:396-402`,
   `:617-623`). TCW-99 principle 2 (design.md:104-105) has one kind of link,
   and "What is inherited" (design.md:453-455) says the parent link replaces
   `extends`. TCW-108 keeps `extends` until this item, held to the links
   (TCW-108 Design 3.6).
2. **Opening a store opens every store it extends.** The constructors build
   each extended store as they run (`FsTaxonomyStore.__init__`,
   `tcw/store/fs.py:1713-1727`; `FsCapabilitiesStore.__init__`, `:2237-2253`;
   `_extended_component_stores`, `:991-1077`), so a missing or broken extended
   project stops every command on the axis, even one that reads only the
   project's own entries (`docs/use-cases.md`, UC-6 "Known gaps"; TCW-108
   Design 6.3 carries this gap until this item). TCW-99 asks that commands
   needing only the project's own records keep working (design.md:386-388).
3. **A capability override is matched by an opaque id, and a term cannot be
   overridden at all.** A capability override is a folder whose `meta.yaml`
   holds `overrides: <alias>/<cap-id>` (`_write_target`,
   `tcw/store/fs.py:2655-2691`), matched by the upstream's opaque `id`
   (`_apply_override`, `:2344-2389`, the match at `:2352`), which `tcw
   capabilities add` mints (`_mint_cap_id`, `:2211-2213`, called at `:2488`).
   When the mirror path is taken, the override goes to `<alias>/<path>`
   instead (`:2676-2686`). A taxonomy entry with the same path as an inherited
   one is a separate entry that wins over the inherited one for a bare
   reference (`get`, `:1799-1817`, "bare-wins-local" at `:1804`), and both are
   listed (`list_all`, `:1785-1793`). TCW-99 makes an override an object at the
   same path, with no marker, in both axes (design.md:456-465), and drops the
   opaque id (the user's decision of 2026-10-22, recorded in TCW-111 Notes).
4. **Inheritance is not ordered.** Each extended store is kept by its alias
   and searched as a set: a path found in two of them is refused as ambiguous
   (`AmbiguousRef`, `tcw/store/fs.py:1815-1816`, `:2438-2439`), and taxonomy
   flattens several levels by "first route wins" (`_inherited_stores`,
   `:1771-1783`). TCW-99 orders them by the load order, last declaring
   project wins (design.md:401-417), and warns about two unrelated projects at
   one path instead of refusing (design.md:476-481).
5. **A 3.x override replaces its original's attached documents.** The body of
   an overridden capability is the override's `prependedDocs`, then the
   override's description or else the upstream's raw `description.md`, then
   the override's `appendedDocs` (`_apply_override`, `:2364-2378`;
   `_compose_body`, `:2311-2326`). An override that does not list
   `prependedDocs` therefore drops the upstream's, though it changed nothing
   about them: against "an override holds only what it changes"
   (design.md:463-465).
6. **A broken override is reported by its pointer, and a moved original is
   not detectable without one.** `tcw validate` checks the pointer
   (`_override_problem`, `tcw/store/fs.py:2912-2932`), requires an `id` on
   every capability and refuses duplicates (`:2815-2820`), and checks
   federation cycles and alias collisions (`:2044-2056`, `:2780-2786`). With
   overrides by path there is no pointer to check; TCW-99 catches a moved
   original by the override being incomplete (design.md:471-475).
7. **Nothing marks an override.** `show` prints `origin:` (`tcw/capabilities/cli.py:75`,
   `tcw/taxonomy/cli.py:82-83`), which TCW-110 replaces with `owner:`; no
   record says that an object replaces an inherited one. TCW-99 asks listings,
   `show` and `tcw project info` to mark each (design.md:467-470).

## Goals

1. Taxonomy and capabilities are inherited from each source of the axis,
   through every level, with no other mechanism; `extends` is gone.
2. An override is an object at the same path as an earlier source's object,
   holding only what it changes, combined field by field; the last project in
   the load order that has an object at a path decides it.
3. Every record says what it overrides, in JSON, in `show` and in the web
   app. A text listing stays one identifier per line (decided by the user,
   2026-10-22; Notes).
4. An object that overrides nothing must be complete, so an override whose
   original moved fails `tcw validate`.
5. Two unrelated projects with an object at one path: the load order decides,
   and `tcw validate` and the listings warn.
6. Commands that read only the project's own objects work when a parent is
   not on this machine; a command that needs inherited content stops with
   exit 7, and `tcw validate` reports "could not check".
7. The capability's opaque `id` is no longer written or used.
8. A single project (UC-1) needs no new configuration and opens no other
   project.

## Non-goals

- **Views across projects** (`--scope`, `--project`, mixed capability
  status, `tcw serve`'s read-only rule for objects it does not own): TCW-113.
  This item keeps today's coverage of `list` (the project's view, with
  `--local` for its own objects) and defines the view and the `overrides` mark
  that TCW-113's scopes show (Notes, handoffs).
- **`tcw project info`**: TCW-115. This item provides what `info` shows about
  overrides (Design 3.7) and hands it on.
- **Changing objects only in the owning project, and moving or renaming
  objects**: TCW-114. This item writes only the active project's own objects
  (an override is one, design.md:584-585) and refuses `rm` and `reset` of
  another project's object (Design 4.3, 4.4); TCW-114 generalises the rule to
  every command.
- **Converting 3.x projects**: `tcw migrate` (TCW-116) moves each 3.x
  override to its original's path, drops `overrides:` and `id: cap-…`, turns
  `extends` into parent links, and fills in what Design 6.1 requires. Notes
  lists what it must do.
- **A command to change a term's fields after it is made.** The taxonomy has
  no command that edits a term's fields (`tcw/taxonomy/cli.py:137-201`
  registers `list`, `add`, `show`, `path`, `rm`, `search` and `extends`;
  TCW-110 Design 3.1 says the same of `relatesTo`). `tcw taxonomy add` at an
  inherited path writes a term override (Design 4.1), and `tcw taxonomy rm`
  removes one (Design 4.4); a field `add` cannot give, or a later change to
  an override, is written into its state file by hand, as a term's `parent`
  is changed (TCW-111 Design 3.4).
- **Removing an inherited object.** As the design says (design.md:499-503), a
  taxonomy entry cannot be removed from below and a capability can only be
  given the status `Omitted`.
- **Inherited configuration** (TCW-109). This item needs nothing from it: a
  tree store's location keys are the project's own and are never inherited
  (design.md:489-491) or set by personal files or variables (TCW-110 Notes,
  Questions for TCW-99, 1), so another project's store is opened from that
  project's committed configuration (`docs/use-cases.md` S-5).
- **Guides and `docs/use-cases.md`** beyond the passages that name a removed
  command (Design 8): TCW-117. Notes lists what they must change.

## Design

Design 1, 2, 3.1-3.6, 4.1-4.4, 5, 6 and 7 are the model: every store
implements them. Design 3.7, 4.5 and 8 are what the CLI, the web app and the
shipped text show. Where a rule names a folder or a file, it is the files
store's realisation, and says so.

### 1. Where inherited content comes from

1.1. **The sources of an axis.** A project's taxonomy view is built from
`sources("taxonomy")` and its capabilities view from
`sources("capabilities")` (TCW-108 Design 5.2), and from nothing else. From
each source other than the project itself, only that project's **own
objects** are read, never its view: each project's own declarations are
folded over the order, as TCW-108 Design 4.8 requires. A source is opened
from its own committed configuration (`taxonomy.path`, `capabilities.path`,
or the default), located through the command's one registry (TCW-110 Design
6.1). So `inherit` decides what is inherited (TCW-108 Design 5.1), several
levels are inherited without being listed (design.md:730-732), and nothing
needs to be declared per axis.

1.2. **A source with no store for the axis contributes nothing.** A source
whose store for the axis is neither present nor declared adds no objects and
is not an error. Today an extended project with no store is an error
(`tcw/store/fs.py:1070-1071`). Reason: `inherit: all` is the default
(TCW-108 Design 1.2), so most parents pass every axis, and a planning
workspace or a monorepo root often keeps no taxonomy; refusing would make
every such link spell out an `inherit` list, which the design names as a sign
the model is wrong (design.md:806-807).

1.3. **A source that cannot be read.** When `sources(axis)` raises
`InheritedUnavailable` (a project that passes the axis is not on this
machine, or its links cannot be read: TCW-108 Design 6.2, 6.6), the view
cannot be built. When a source is on this machine but its store for the axis
cannot be opened (declared but not provisioned, `StoreNotProvisioned`; or
wrongly declared, `StoreDeclarationError`, `tcw/store/base.py:72-110`), the
same exception is raised with a third message, added here to TCW-108 Design
6.2's two:

```
'<P>' inherits its <axis> from project '<M>', whose <axis> store cannot be read here: <the store's own message>
```

Reason: for the project inheriting, the effect is the same as a missing
parent (the content it needs is not available here), and the person's fix is
in `<M>` or in fetching it; exit 1, today's code for this
(`tcw/store/fs.py:1059-1069`), would say TCW itself failed.

**A source's object with a version problem** (its state file has one of
TCW-106 Design 3.4's rows, TCW-111 Design 1.5) is not a reason to stop the
whole view, but its id-path `X` cannot be combined. Which projects declare
`X` is still known (the object exists; only its contents are not read), so
the chain of Design 2.1 is still found. When a member of `X`'s chain has a
version problem, `X` is **unreadable** in the active project's view, and
every use of it says so rather than going on as if that member's object were
absent (which would wrongly make the active project's partial override look
like one that overrides nothing, and let `add` write a new object over it):

- `list` and `search` leave `X` out, print the message naming the file on
  standard error, and exit 1, as TCW-111 Design 1.5 does for the project's
  own objects. `list --local` prints the active project's own object at `X`,
  when it has one, as its own declaration alone, marked as 3.4 marks it, and
  also exits 1 with the message;
- `show`, `reset` and `add` at `X`, `set` of `X` when the active project has
  no object of its own there, and Design 2.7 for `X` exit 1 with the message
  and change nothing;
- `set` and `rm` of the active project's own object at `X` work, since they
  need no view (3.5, 4.2, 4.4);
- `tcw validate` makes one `unresolved` finding for `X`, at the active
  project's `.tcw/tcw-config.yaml`, `could not check <axis> <id-path>: <the
  message>`, and does not run, for `X`, the checks that need the combined
  object (6.1, 6.2's field checks, 6.3). The version error itself is reported
  by the owner's own `tcw validate`.

An unused declarer (2.5) with a version problem changes nothing but its
place in 2.5's warning, since its fields are never used.

1.4. **Inherited content is read only when it is needed.** Opening the active
project's store reads no other project and asks the registry nothing about
sources. The view is built the first time a command asks for something that
needs it (Design 3.5), once per command. This replaces the constructors that
open every extended store at once (Problem 2) and closes the UC-6 gap that
TCW-108 Design 6.3 carries.

1.5. **`extends` is gone.** `taxonomy.extends` and `capabilities.extends` are
not 4.0 keys. With them go `tcw taxonomy extends add|rm` and `tcw
capabilities extends add|rm`, the abstract stores' `extends_add` and
`extends_remove`, TCW-108 Design 3.6 (an `extends` ID must be an ancestor
passing the axis) and 6.3 (exit 7 for a missing `extends` project), and the
federation walk and its cycle check (`_FederationWalk`, `_FederationCycles`,
`_extended_component_stores`, `tcw/store/fs.py:935-1077`; `_persist_extends`
and `_extends_label`, `:1444-1487`). A loop among projects is TCW-108 Design
4.7's graph error, so no second cycle check is needed. **In the active
project's own `.tcw/tcw-config.yaml`**, either key is a configuration problem
at the file, with the message:

```
'<axis>.extends' was removed in TCW 4.0: a project inherits its <axis> from its parents; name each project it inherits from under 'parents:' with an 'inherit' that includes <axis>, and delete this key
```

It is raised where today's `extends` errors are, when the active project's
store for that axis is opened (`tcw/store/fs.py:1724-1727`, `:2248-2251`), so
every `tcw taxonomy` or `tcw capabilities` command exits 1 and `tcw validate`
reports it as an error. Both keys also leave TCW-109's table of the keys TCW
knows (TCW-109 Design 4.3), so an environment variable naming one names no
key. Reason: a key that is kept but ignored would make a
project silently lose content it expected, which is the failure the
pre-2.5.0 store file check exists to prevent (`_legacy_config_problems`,
`:1619-1640`). **In another project's file** the key is not read: what that
project passes down comes from its links alone, and its own `tcw validate`
reports the key.

### 2. Overrides by path: how an object is combined

2.1. **Declarers and the chain.** For a project `P`, an axis and an id-path
`X`, the **declarers** of `X` are the projects in `P`'s sources (in load
order) that have an object of their own at `X`. The **chain** of `X` in `P`
is found from the end:

1. Its first member is the last declarer (which is `P` when `P` has an
   object at `X`).
2. Each next member is the last declarer before the current member, in `P`'s
   load order, that passes the axis to the current member (TCW-108 Design
   5.1). Stop when there is none.

So each member of the chain overrides the next one, and an object never
overrides one in a project it does not inherit from. TCW-108 Design 4.2's
second shape (`bb` the parent of `cc` and `dd`, `ee: [cc, dd]`) gives, when
`bb` and `cc` have an object at `X` and `dd` does not, the chain `cc`, `bb` in
`ee`: `dd` only passes `bb`'s object along, so it does not put it back
(TCW-108 Design 4.8). Membership is decided in `P`'s load order, so one order
serves the command (TCW-108 Design 5.2).

2.2. **Combining the fields.** The object at `X` in `P`'s view is the chain
folded from its last member to its first: start with the declaration of the
member farthest down the chain, and lay each nearer member's own declaration
over it, key by key:

- a key with a value replaces the value below it;
- a key set to `null` removes the value below it (as a 3.x override's `null`
  does, `tcw/store/fs.py:2360-2361`);
- a key that is absent leaves the value below it;
- a list (`Subject`, `relatesTo`, `vocabulary`, `prependedDocs`,
  `appendedDocs`) is replaced whole, never merged entry by entry, as the
  design says of configuration lists (design.md:493-496).

`name`, `kind`, `parent` (TCW-111 Design 3.1) and every capability field in
the locked set combine this way. `tcw-version` and `id` belong to the file
and never combine. A `name` that no member sets falls back to the folder's
name, as today (`tcw/store/fs.py:1736`, `:2336`).

2.3. **Combining the body and the attached files** (the files store's
realisation of "only what it changes"):

- **The description.** In the model, an object's own declaration either
  **declares a description** (a text, possibly empty) or declares none; the
  files store keeps a declared description in `description.md`, an empty
  file being a declared empty description, and keeps "no description" as no
  file. Every store must keep "declared empty" and "not declared" apart,
  because Design 6.1 tells them apart. Combining: the description is the
  nearest member's declared description whose text is not empty (holds
  something other than white space); an empty one adds no text and so
  changes nothing here, exactly as one not declared. This keeps 3.x's rule
  for an override's description (`tcw/store/fs.py:2369-2373`, which tests
  `child_raw.strip()`). So an empty description has one meaning everywhere:
  a description is declared, and it has no text.
- **`prependedDocs` and `appendedDocs`** combine as lists (2.2). Each entry is
  read from the `resources/` folder of the member that declared the list
  (TCW-111 Design 2.2). So an override that does not mention them keeps its
  original's, and one that sets `prependedDocs: null` removes them. This
  changes 3.x, which used only the override's lists (Problem 5).
- **A term's attachments** (TCW-111 Design 2.2) are those of the nearest
  member whose `resources/` holds any file, as a list is replaced whole.
- **`modified`** is the latest of the members' (as 3.x takes the later of the
  two, `tcw/store/fs.py:2379-2388`).

2.4. **What the combined object is called.** Its full identifier and owner
are those of the chain's first member: an object always belongs to the
project that declares it (design.md:106-109), and the first member is the
nearest one that does. **`overrides`** is the full identifier of the chain's
second member, or none when the chain has one member. So in `app`, which
overrides `core`'s `cli/x`, the entry is `app.capabilities/cli/x` with
`overrides: core.capabilities/cli/x`; in `ee` of 2.1's example, the entry is
`cc.capabilities/X` with `overrides: bb.capabilities/X`.

2.5. **Two unrelated projects at one path.** A declarer that is not in the
chain is **unused**: it has an object at `X`, and the object `P` sees does
not include it. That happens exactly when two declarers are such that
neither passes the axis to the other (the design's "neither an ancestor of
the other", read per axis, so that a project behind an `inherit` that leaves
the axis out is unrelated for that axis). The load order picks: the chain
takes the later one, whole, with what it inherits; the earlier one's fields
are not used at all, so no object is made of two unrelated objects' fields
(decided by the user, 2026-10-22, with AC 11 as the example: when `cc` and
`dd` both override `bb`'s `X` and `dd` comes later, `ee` sees `dd`'s object
over `bb`'s, and `cc`'s `Status` is lost although `dd` never set `Status`;
the warning below names `cc` as the project whose object is not used).
One warning is made for each unused declarer `L`:

```
<axis> <id-path>: '<L>' and '<W>' each have an object at this path, and neither inherits it from the other; '<P>' uses the one from '<W>', which comes later in its load order, and nothing from '<L>''s; to choose for yourself, give '<P>' a complete object of its own at <id-path> (<what complete means>), holding every field you want
```

where `W` is the first chain member after `L` in `P`'s load order (the one
that took its place), and `<what complete means>` is `a name, a Status and a
description` for a capability and `a name and a description` for a term
(Design 6.1). Warnings are ordered by id-path, then by `L`'s place in the
load order. A project's own object at `X` is always an override (every other
declarer is one of its sources), so the active project itself is never named
as unused, and a descendant's object at an ancestor's path is never a warning
(design.md:480-481).

**When the warning stops.** No warning is made for `L` when a member of the
chain that comes before `W` (nearer to `P`; `P`'s own object included) is a
project to which `L` also passes the axis, and that member's own declaration
at `X` is complete: it holds `name`, (for a capability) `Status`, and
declares a description, possibly empty, the test of Design 6.1 applied to
the declaration alone. Such a member inherits from both `L` and `W`, so it
saw the clash, and by holding a complete object it has decided what `X` is;
the warning's advice is therefore what silences it. A member that `L` does
not pass the axis to never silences it, since it never saw `L`'s object.
Fields the deciding object does not set still come from `W`'s side of the
chain (Risks).

2.6. **The combination is one function, outside the files store.** Given each
source's own declaration at an id-path and the "passes the axis to"
relation, Design 2.1-2.5 computes the chain, the combined declaration, the
`overrides` identifier, the unused declarers and whether each is warned
about, without reading a file. It
lives beside TCW-108's load order function in `tcw/store/base.py`, so another
kind of store uses the same rule. Reading `description.md`,
`resources/` and the attached files is the files store's.

2.7. **What is inherited at a path** (the store operation TCW-114 Design 10.2
asks for). Each tree store answers, for the active project and an id-path,
the full identifier of the inherited object at that path, or none: the first
member of the path's chain that is not the active project, computed over the
active project's sources without its own object. So for the active project's
override it names the object overridden, and for a path the active project
has no object at it names the object it would override. It raises
`InheritedUnavailable` when the view cannot be built (Design 1.3), and the
version message (exit 1) when the path is unreadable (Design 1.3). `add`
calls it (4.1), and TCW-114's move and rename check calls it for an object's
own path and for each new path.

### 3. What commands read

3.1. **What an input names** (replacing TCW-110 Design 3.1's paragraph "An
inherited object, until TCW-112", and the first two sentences of its 6.2 for
taxonomy and capabilities):

| Input (TCW-110 Design 3.1) | Names |
| --- | --- |
| an id-path `X` (form d) | the object at `X` in the active project's view (Design 2): its full identifier is the chain's first member's |
| the active project's full identifier `P.<axis>/X` (form a) | the active project's own object at `X`, as the active project sees it; not found when the active project has no object of its own at `X` |
| another project's full identifier `Q.<axis>/X` (form a) | `Q`'s own object at `X`, as `Q` sees it: Design 2 applied over `sources(axis, Q)` (TCW-108 Design 3.2; 4.6 gives the load order of any project TCW-107's lookup can locate); not found when `Q` has no object of its own at `X` |

So every full identifier names one project's own object, as its owner sees
it, whether or not the active project inherits from that owner; and
`core.capabilities/cli/x` from `app` is `core`'s capability, never `app`'s
override of it (design.md:459-462: `--project shared-libs` returns only the
original).

**This differs from TCW-110 Design 6.2.** There, an owner the active project
does not inherit from is read "from that store's own objects", which is the
raw declaration. Here every owner's object is combined over the owner's own
sources, because an owner's own object may itself be a partial override, and
its raw declaration alone would be a capability with no name and no
description. What TCW-110 6.2 says and this keeps: only the owner's own
objects are found, so an object the owner merely inherits is not found under
the owner's identifier. Three consequences:

- Combining `Q.<axis>/X` needs `Q`'s sources. When a project that passes the
  axis to `Q` cannot be read, `sources(axis, Q)` raises
  `InheritedUnavailable` (exit 7), whose message names `Q` as the project
  inheriting. When `Q` itself is not on this machine, it is TCW-110 Design
  6.3's exit 5, unchanged. So 5 says the named project is absent, and 7 that
  something it inherits is absent.
- Whether `Q` has an object of its own at `X` needs only `Q`'s own store. A
  check that only asks whether a reference names an existing object (TCW-110
  Design 6.4 in `tcw validate`, and the referrer checks of `rm` and `reset`,
  4.3, 4.4) asks only that, so it is never "could not check" because an
  ancestor of `Q` is missing. The records gate (7.1) reads the combined
  `Status`, so it does combine.
- **The two views agree.** The object `P` sees at `X`, whose chain's first
  member is `W`, is exactly what `show W.<axis>/X` gives, wherever it is run.
  Every source of `W` is a source of `P`, since passing an axis carries
  through a chain of links (TCW-108 Design 5.1); and when `P`'s load order is
  TCW-108 Design 4.1's (C3), the merge keeps the order of each list it
  merges, so `P`'s order lists `W`'s ancestors in `W`'s own order, and the
  chain below `W` is the one `W` finds. An unused declarer (2.5) is never
  combined, so it changes nothing here. They can differ only when `P`'s order
  is TCW-108 Design 4.4's depth-first fallback, which may place two of `W`'s
  declarers that are unrelated to each other the other way round from `W`'s
  own order; that order carries TCW-108 Design 4.5's warning in `tcw
  validate`, which is what says so.

3.2. **Listings.** `tcw taxonomy list`, `tcw capabilities list` and both
`search` commands cover the active project's view: each id-path once, as the
combined object of Design 2.2, named by Design 2.4's full identifier, and
`search` matches the combined name and body. `--local` (both `list`
commands) keeps the objects whose owner is the active project, overrides
included; it needs no other project (3.4). Each warning of Design 2.5 for an
id-path in the result is printed on standard error, as `warning: <the
message>`, before the list; standard output keeps one full identifier per
line (`cli/rely-on-one-output-contract`). The design's "Listings … mark each
object that replaces an inherited one" (design.md:467-470) is read as the
listing's records: `list --json` and `search --json` carry `overrides`
(3.3), and the plain text listing carries no mark (decided by the user,
2026-10-22; TCW-117 amends that line of the design and the guides, Notes).

3.3. **Records.** Every taxonomy and capability record (in `list --json`,
`search --json`, `show --json` and the web API) gains `overrides`: the full
identifier of Design 2.4, or `null`. `show` prints `overrides: <full id>`
after `owner:` and TCW-111's `parent:` (TCW-110 Design 4.2, TCW-111 Design
3.1) when there is one. The capability record and `show` no longer carry
`id` (Design 5). The one other key is `partial`, present only on a record
read without its inherited content (3.4, 1.3). No other key changes, and the
JSON envelope keeps TCW-110's
`"schema": 2`: nothing is released between TCW-110 and this item, so every
change to the records reaches users at once.

3.4. **Reading the project's own objects never stops for inherited
content.** When building the view raises `InheritedUnavailable` (Design 1.3):

- `list --local` prints the active project's own objects; `--json` gives each
  as its own declaration alone (its fields, and a name from the folder when it
  sets none);
- `show` of an object the active project owns (by its id-path or its full
  identifier) prints its own declaration alone, the same way;
- each such JSON record has `"partial": true` and **no** `overrides` key,
  because whether the object overrides one is not known; the text `show`
  prints `partial: inherited content could not be read` in place of an
  `overrides:` line. A record read with its inherited content has no
  `partial` key, and always has `overrides` (a full identifier or `null`);
- both print, once, on standard error,
  `warning: <the InheritedUnavailable message>; showing only '<P>''s own declarations`,
  and exit 0.

Reason: the design keeps "reading its own taxonomy and capabilities" working
when a related project is missing (design.md:386-388). The record may be
partial, because the object may override one in the missing project, so its
fields and its name may not be what the view would give, and a script must
be able to tell that from the record itself, not only from standard error:
`overrides: null` would claim "overrides nothing", which is not known. A
script that needs certainty runs `tcw validate`, which reports what it could
not check (6.5).

3.5. **Which commands need inherited content.** These build the view, and
stop with `InheritedUnavailable` (exit 7, TCW-108 Design 6.2, and Design 1.3's
third message) when it cannot be built:

| Command | Needs the view because |
| --- | --- |
| `list` (no `--local`), `search` | it lists the view |
| `show` of an id-path the active project has no object at, or of another project's full identifier | the object comes from another project |
| `add` | it must know whether the path is inherited: `tcw capabilities add` is refused there, and `tcw taxonomy add` writes an override holding only what differs (4.1) |
| `set` of an id-path or full identifier the active project has no object at | it must know the inherited object exists (4.2) |
| `reset` | it must know the object overrides one (4.3) |
| `tcw capabilities drift` | its first half reads the view (7.2) |
| `tcw validate` | catches the exception and reports "could not check" (6.5) |
| the records gate of `tcw work advance` | treats it as "could not check" for that entry (7.1) |

`list --local`, `show` of an object the project owns (3.4), `set` of an
object the project owns (4.2: it writes the same thing whether or not the
object overrides one), and `rm` (4.4) do not stop. A source behind an
`inherit` that leaves the axis out never stops anything (TCW-108 Design
6.2). In a project with no parents, `sources(axis)` is the project alone, so
no command of this item opens another project (UC-1).

3.6. **No path is ambiguous any more.** The load order decides every id-path
(Design 2.5), so `get` never raises `AmbiguousRef` for a path
(`tcw/store/fs.py:1815-1816`, `:2438-2439`). The callers that catch it for
this (`:1928`, `:1955`, `:2003`, `:2954`, and the `AmbiguousRef` rows in the
abstract stores' docstrings, `tcw/store/base.py:349-358`, `:516-526`) lose
that case; the plan says which of them still catch it for another reason.

3.7. **What `tcw project info` will show** (TCW-115). For each axis, the
active project's own objects whose `overrides` is set, each with what it
overrides, and the count of Design 2.5's warnings. Both are read from the
records of `list --local` and from the warnings of 2.5, so `info` adds no
rule of its own. Whichever of TCW-115 and this item lands second puts them
into `tcw project info` (Notes).

### 4. What commands write

Every write changes only the active project's own objects (design.md:581-585).

4.1. **`add`.** Both commands first ask Design 2.7 whether the path they
would create has an inherited object. Where it has none, they write a new,
complete object as today; a new capability's state file holds no `id`
(Design 5). Where it has one:

- **`tcw capabilities add` is refused** (`Refused`, exit 3, nothing
  written):

  ```
  cannot add '<id-path>': '<P>' already inherits <full id> there; to change it, override it with tcw capabilities set <id-path> --field <name>=<value>
  ```

  `add` would write a name, a `Status` and a description, so its object
  would be a full-copy override, the one case nothing reports if the
  original later moves (design.md:473-475); `set` writes only the fields
  given (4.2), so the CLI still carries the operation (`docs/use-cases.md`
  S-2).
- **`tcw taxonomy add` writes an override**, since the taxonomy has no `set`
  and this is its one command that makes a term at a path. The term's state
  file holds `tcw-version` and only what differs from the inherited term as
  the active project sees it: `name` when the name given differs from its
  name; `kind` only when `--kind` is given and differs from its kind
  (`--kind`'s default, `vocabulary`, `tcw/taxonomy/cli.py:158-159`, applies
  only to a new term, so an inherited Feature is not turned into a
  Vocabulary term by leaving it out); `vocabulary` when
  `--vocab` is given; and a `description.md` only when the description read
  from standard input is not empty. It never writes `relatesTo` (today's
  `add` writes `relatesTo: []`, `tcw/store/fs.py:1861`, which as an override
  would clear the inherited list, Design 2.2). Standard error adds
  `<new full id> overrides <inherited full id>`. When nothing differs, it is
  refused (exit 3, nothing written):
  `cannot add '<id-path>': '<P>' already inherits <full id> there, and nothing given differs from it; give a description on standard input, --vocab, or a different name or kind`.
  When `--parent` names a path that the view has an object at but the
  active project's store has no folder for, the folders between are created
  as organising folders (TCW-111 Design 2.3), as `set` does for a nested
  capability override (4.2).

Reason: without a marker, an object added at an inherited path would
otherwise become an override silently, and a full copy at that; refusing
`tcw capabilities add` there, and making `tcw taxonomy add` write only what
differs and say so, are the two ways TCW can prevent both at the one moment
it can see them. The checks of the combined term (a Feature's vocabulary,
6.2) run before anything is written, as `add`'s checks do today
(`:1859-1860`).

4.2. **`set`** (`tcw capabilities set`, and `update_capability` for the web
app):

- on an object the active project owns, override or not: changes that
  object's state file in place. **A cleared field** (the store's clear value,
  `None`, which the web app's `PATCH` sends as JSON `null`) is written as an
  explicit `null` on every own object. Today `_merge_meta`
  (`tcw/store/fs.py:2693-2705`) writes `null` on an override and deletes the
  key on a standalone object, so it must know which it is, and only the view
  can tell that now that nothing in the files marks an override. With one
  rule `set` needs no view (3.5). For an object that overrides nothing,
  `null` and an absent key mean the same (Design 2.2: `null` removes the
  value below, and there is none), so the combined object, `show` and every
  check are unchanged; and if a parent later gains an object at the path,
  the field stays cleared, which is what clearing it said. `add`, which only
  ever makes an object that overrides nothing (4.1), keeps deleting the key
  (`:2494-2498`);
- on an id-path the active project inherits, or on the full identifier of an
  object in the chain of that id-path in the active project: writes the
  active project's own object **at the same id-path**, holding `tcw-version`
  and only the fields given (no `name`, no `id`, no pointer), and no
  `description.md` unless a body is given. A key given as `null` writes an
  explicit `null`, which removes the inherited value (Design 2.2), as 3.x does
  (`_merge_meta`, `tcw/store/fs.py:2693-2705`). The folder `<alias>/<path>` is
  never used (`:2676-2686` goes);
- on another project's full identifier whose object is not in that chain: refused
  (`Refused`, exit 3, nothing written):
  `<full id> belongs to project '<Q>', and '<P>' does not inherit it, so it cannot be overridden here; change it in '<Q>'`.
  TCW-114 Design 1.3 later keeps the reason and replaces the tail
  `; change it in '<Q>'` with one that says where `<Q>` is.

In every case the object `set` writes, and so the object TCW-114's ownership
check is given, is the active project's own object at the id-path, never the
object named by the full identifier.

`tcw capabilities set --parent` on an inherited capability is no longer
refused (TCW-111 Design 3.4's interim refusal): `parent` is a field of the
override like any other (Design 2.2), so it is written into the active
project's object at that path. A write that fails partway removes the folder
it created, as today (`_write_meta`, `tcw/store/fs.py:2639-2653`). When the
id-path's folder already exists in the active project's store without a
state file (an organising folder, TCW-111 Design 2.3), the state file is
written into it, which makes it an object; `tcw validate` then reports any
loose file in it (TCW-111 Design 2.6 a).

4.3. **`reset`** (`tcw capabilities reset`) removes the active project's own
object at an id-path when it is an override, so the id-path shows the
inherited object again. It accepts the id-path, the active project's full
identifier, or the full identifier of any object in that id-path's chain (so
`reset core.capabilities/cli/x` means "stop overriding this"). It is refused
(exit 3, nothing removed):

- when the active project's object at the id-path overrides nothing (today's
  message, naming `tcw capabilities rm`, `tcw/store/fs.py:2578-2580`);
- when the active project has no object there (today's "inherits verbatim"
  message, `:2588-2590`);
- when anything is nested under the folder (`:2594-2599`, with TCW-111 Design
  2.5's search);
- when another of the active project's own objects references the override
  by its full identifier (`Superseded by`, `Blocked by`, `Roles`, `When`,
  `Subject`, `Feature`, `relatesTo`, `vocabulary`, `parent`): the message
  names each one and the field, and says to repoint it at the overridden
  object's full identifier. Reason: references are full identifiers
  (TCW-110 Design 3.3), and the override's identifier stops existing when it
  is removed.

What `reset` removes is always the active project's own object at the
id-path, whichever input names it, and that is the object TCW-114's
ownership check is given; so `reset core.capabilities/cli/x` is a write to
`app`'s object, not to `core`'s, and is not one of TCW-114 Design 1.5's
refused writes.

4.4. **`rm`** (`tcw taxonomy rm`, `tcw capabilities rm`) removes any of the
active project's own objects, an override included. It keeps today's
refusals for nested objects and for references to the object's full
identifier (`tcw/store/fs.py:1888-1895`, `:2518-2525`), and drops the refusal
of an inherited object (`:1876-1878`, `:2512-2515`), since every object it
can name by an id-path that the project owns is the project's own. Another
project's full identifier, and an id-path the active project has no object
at but its view shows as another project's, are refused as `cannot remove
<full id>: it belongs to project '<Q>'; change it in '<Q>'` (exit 3), a
message TCW-114 Design 1.3 replaces with its one shape. An
id-path nothing has an object at is not found (exit 4), as today; so is one
the active project has no object at when the view cannot be built, since `rm`
only ever removes the active project's own objects. When the removed object was an override, standard
error adds `<id-path> now shows <full id of the next chain member>`; when the
view cannot be built, that line is left out and the removal still happens
(3.5). Reason: an override is an ordinary object of the project
(design.md:459-460), so the command that removes the project's objects
removes it, and taxonomy, which has no `reset`, needs it.

4.5. **The web app** (`tcw serve`) shows what the CLI decides (TCW-99
principle 4): each record carries `overrides` (3.3) and the entry view shows
"overrides `<full id>`". A taxonomy entry or capability whose owner is the
served project, an override included, is editable; one owned by another
project keeps today's refusal (`tcw/serve/records.py:117-119`, `:193-196`):
`read_only`, answered `403 Forbidden` with `{"code": "read-only"}`
(`tcw/serve/server.py:61-62`), with "owner" for "origin". Not `409`: 403 is
what that refusal answers today, and TCW-114 Design 1.4 keeps 403 for every
refused write, so changing it here would be undone there. An `InheritedUnavailable` raised by an API
request is answered with `503 Service Unavailable` and `{"code":
"inherited-unavailable"}`, beside the existing mapping of `Unreachable`
(`tcw/serve/server.py:88-89`). Reason: it is the first time a served read
can raise it, and without a row it falls to the generic `500` (`:90-91`).

**What a web edit of a capability's body writes.** A capability's body, as
records give it, is the combined body of Design 2.3: the declared
description of the nearest member that has one with text, with the
attached documents of `prependedDocs` and `appendedDocs` around it. A web
edit of the body writes only the active project's **declared description**
(the files store's `description.md`), never the combined body. So the detail
answer of `GET /api/capabilities/<key>`, and the answers of the `POST` and
`PATCH` that return the same shape, carry `declaredDescription` beside
`capability` and `coreRevision`: the declared description of the object's
owner (the chain's first member), its text with leading and trailing white
space removed (as the combined body uses it), possibly empty, or `null` when
the owner declares none. The web editor's body field starts from
`declaredDescription` (empty when it is `null`), not from the record's
`body`; a save that leaves the field unchanged sends no `body`, and one that
changes it sends the field's text, which `update_capability` writes as the
declared description. When the record's `body` differs from the declared
description, the editor says, beside the field, that the body shown on the
page also holds attached documents or an inherited description, which the
edit leaves unchanged. Clearing the field writes an empty declared
description, which adds no text (Design 2.3), so the body shown falls back
to the next member's description. Reason: the editor sends back what it was
given, and the body it is given today is the combined one
(`web/client/src/ui/app.tsx:636-639`, saved at `:737-738`), so a save writes
the attached documents' text into `description.md` and the next read shows
it twice. This already happens in 3.x to a capability with its own
`prependedDocs` or `appendedDocs`, and Design 2.3 would extend it to every
override whose original has attached documents, since an override now keeps
its original's lists; this item fixes both. A term is not affected: its
description is never composed with attached text, so the combined
description is one declared description, and editing it writes the edited
text as the override's own, which replaces the inherited one rather than
repeating it.

### 5. The capability's opaque `id`

5.1. **It is no longer written** by `tcw capabilities add` (`_mint_cap_id`,
`tcw/store/fs.py:2211-2213`, called at `:2488`, goes) or by an override that
`set` creates (4.2).

5.2. **It is no longer an identity.** `Capability.id`
(`tcw/store/base.py:481-494`) and `get_by_id` (`tcw/store/fs.py:2401-2407`) go;
`tcw validate` no longer requires an `id` or refuses duplicates
(`:2815-2820`); `show` and the JSON record no longer print it
(`tcw/capabilities/cli.py:42-43`, `:76-77`).

5.3. **TCW-111 Design 2.6 row k applies to capabilities**, as TCW-111 Design
1.3 said it would: a capability state file may hold `id`, which must equal
its folder's name, or `tcw validate` reports TCW-111's error. So a
`tcw-capability.yaml` still holding `id: cap-…` fails until it is removed;
`tcw migrate` removes it (TCW-116).

### 6. What `tcw validate` reports

6.1. **An object that overrides nothing must be complete.** Each of the
active project's own objects whose chain has one member must, in its own
declaration, hold a value (not `null`) for `name` and, for a capability,
`Status`, and must declare a description, possibly empty (Design 2.3). In the
files store, that is `name` and `Status` in the state file and a
`description.md` in the folder, which may be empty. These are what a new
term from `tcw taxonomy add` and `tcw capabilities add` always holds
(`tcw/store/fs.py:1861-1864`, `:2488-2499`). An id-path that is unreadable
(Design 1.3) is not checked here: whether its chain has one member is known,
but the message would blame the wrong object, so 1.3's "could not check"
finding covers it. Otherwise it is an error at the object's state file:

```
<full id> is incomplete: it overrides nothing, and has no <name | Status | description.md>; if it overrode an object that moved or was removed, complete it or remove it
```

naming each missing part. "missing Status" (`:2829`) becomes this message
for such an object. A partial override whose original moved is caught this
way (design.md:471-473); a full copy whose original moved is the accepted
case nothing reports (design.md:473-475).

6.2. **Each own object is checked as the project sees it.** Today's field
checks (unknown or retired field, invalid `Status`, `Priority` or
`Lifecycle`, "Partial requires Gaps", "Blocked requires Blocked by", a
Feature's vocabulary, `tcw/store/fs.py:2070-2084`, `:2821-2840`) run on the
combined object of each of the active project's own objects, so an override
that sets `Status: Partial` over an original with no `Gaps` is reported in
the project that made it so. The reference checks run on the references the
active project's own objects declare, never on inherited values it does not
set: those are checked in their owner. For an override this is what 3.x
checked through `_override_fields` (`:2279-2294`, `:2865-2882`); the two
lists of own objects and override folders become one.

6.3. **Two unrelated projects at one path** (Design 2.5): each of Design
2.5's warnings for the active project's view is a `warning` finding, at the active project's
`.tcw/tcw-config.yaml` (whose `parents:` decide the order), with Design 2.5's
message. It never fails the run.

6.4. **Keys that are no longer read.** An `overrides` key in a state file is
an error at that file:
`'overrides' was removed in TCW 4.0: an override is an object at the same path as the object it overrides; run 'tcw migrate' in this project, or move this folder to that path and delete the key`.
The folder is otherwise read as an ordinary object of the project (at the
mirror path it is therefore an override already; at `<alias>/<path>` it is a
standalone object, and 6.1 also reports it when it is partial). TCW-111
Design 2.5's paragraph "3.x override folders" and its exceptions to rows k
to n go. The `extends` keys are reported by Design 1.5.

6.5. **Inherited content that cannot be read.** When `sources(axis)` raises
for an axis the project has a store for, `tcw validate` records TCW-108
Design 6.5 row (c) for the project at which it stopped, whose suffix becomes
`; could not check the <axis> inherited from it` (row (c) was "a project at
which an `extends` check stopped"; it is now "a project from which inherited
taxonomy or capabilities could not be read"). For Design 1.3's third message
the finding is `unresolved`, at the active project's `.tcw/tcw-config.yaml`,
`could not check the <axis> inherited from '<M>': <the store's message>`.
Then, for that axis, the checks that need the combined object (6.1, the
field-presence checks of 6.2, and 6.3) are not run, and are covered by that
one finding; the checks of what the project's own objects declare (6.2's
reference checks, unknown and retired fields, invalid values present in the
file, where `null` is never an invalid value since it only clears, 6.4, and
TCW-111's rows) still run. So `tcw validate` in CI on a fresh
clone without a parent exits 0 for this reason (UC-6, S-4).

6.6. **Checks that go.** The federation cycle check
(`tcw/store/fs.py:2047-2049`, `:2780-2782`; TCW-108's
`test_check_federation_cycle`, which TCW-108 points at its Design 3.6
refusal, goes with that refusal), the collision of a project ID with a
top-level entry (`:2050-2053`, `:2783-2786`: an inherited object is no longer
named by an alias prefix), the `overrides:` pointer problems
(`_override_problem`, `:2912-2932`), and the `id` checks (5.2).

6.7. **An override nested in an override** (TCW-111 Design 2.6 row m, 3.2).
An object whose combined `parent` names an object at the same id-path as its
folder parent, owned by a project that passes the axis to the active
project, agrees with its folder: the folder parent is that object's override,
or that object as the active project sees it. Without this rule, every
nested override would be warned about: `app`'s `cli/x/y` would sit in `app`'s
`cli/x` while its inherited `parent` names `core.capabilities/cli/x`.

6.8. **The pre-2.5.0 store file** (`_legacy_config_problems`,
`tcw/store/fs.py:1619-1640`) keeps its check; its message no longer names
`extends`: `no longer read since TCW 2.5.0; a project inherits taxonomy and capabilities from its parents (parents: in .tcw/tcw-config.yaml); delete this file`.

### 7. Other readers

7.1. **The records gate** (`capabilities.yaml`, `tcw/work/gates.py`), which
TCW-110 makes read full identifiers. Each entry is checked against its
owner's object as its owner sees it (3.1), replacing TCW-110 Design 6.2's
interim "checked against `app`'s view of it". So:

- `new` and `changed` find the owner's object (`Present` with its combined
  `Status`), or `ABSENT` when the owner has no object of its own at the
  id-path, even when the owner inherits one there: `app.capabilities/cli/x`
  is `app`'s own object, which `tcw capabilities set` creates (4.2);
- `removed` is `REMOVED` when the owner has no object of its own at the
  id-path, and `STILL_LOCAL` when it has; the `INHERITED` outcome
  (`tcw/work/gates.py:421-424`) goes, since a full identifier never names an
  inherited copy;
- rule 1 of `route_capability_path` (`head in own.extends`,
  `tcw/work/gates.py:354-355`, the rule TCW-110 Design 6.2 keeps until this
  item) goes with it: no store has `extends` (AC 15), and an entry is routed
  by its full identifier's owner alone. These two are the gate's only uses of
  `extends` (`:354`, `:423`);
- an `InheritedUnavailable` raised while reading an entry is
  `Unchecked(<its message>)`, like the read errors the gate already catches
  (`_READ_ERRORS`, `:383`).

7.2. **Drift** (`tcw capabilities drift`). An inherited capability is
"never ruled on here" when the active project has no object of its own at
its id-path, or has one that does not set `Status`
(`unreviewed_inherited`, `tcw/store/fs.py:2461-2463`; `_status_is_local`,
`:2449-2459`, which matched the override by the opaque id, goes). The
command builds the view before printing anything, so it exits 7 with nothing
on standard output when the view cannot be built.

7.3. **Removing a term** checks the capabilities that name it
(`_capability_referrers`, `tcw/store/fs.py:1899-1935`) over the active
project's own capabilities and the references they declare. The separate
list of override folders goes: overrides are own capabilities (6.2).

### 8. Shipped text

8.1. **Every shipped or owned passage that names a removed command is
changed here.** `tcw taxonomy extends add|rm` and `tcw capabilities extends
add|rm` are named in skills (`skills/taxonomy/SKILL.md:111-112`, `:132`;
`skills/capabilities/SKILL.md:122-123`, `:175`;
`skills/configure/references/stores.md:110-114`;
`skills/configure/references/projects.md:55`, `:360-371`;
`skills/setup/references/taxonomy.md:18`) and in guides
(`docs/guide/taxonomy-and-capabilities.md:37-38`, `:57-64`, `:212-213`;
`docs/guide/cli.md:14`; `docs/guide/multi-repo.md:269`), in `README.md`
(`:360`, `:371`, `:421`, `:432`, a table row and an example for each axis),
and in the two capability descriptions that 8.2 rewrites
(`docs/capabilities/capabilities/federate/description.md`,
`docs/capabilities/taxonomy/federate-shared-vocabulary/description.md`).
Three scans check that every named command exists, and each would fail:
`test_every_command_named_in_shipped_text_exists`
(`tests/test_shipped_text.py:313-323`); the owned-document command check of
`tests/test_docs_describe_3_0.py`, which reuses it; and
`test_documented_verbs_and_flags_exist`
(`tests/test_documented_cli_surface.py:238-247`), which reads every
Markdown file git knows of, tracked or new, apart from its `ARCHIVAL`
prefixes (`:38-51`, `_doc_files`, `:54-72`), so `README.md` and the
capability descriptions are in it. Each passage is changed to say that a
project inherits taxonomy and capabilities from the parents whose `inherit`
includes the axis, configured under `parents:` (the `configure` skill's
projects reference), and that an override is an object at the same path. The
sweep reads the same files as that third scan:

```sh
git ls-files --cached --others --exclude-standard -- '*.md' \
  | grep -v -e '^docs/work/' -e '^docs/plan/' -e '^docs/superpowers/' \
            -e '^docs/changelogs/' -e '^docs/release-notes/' \
            -e '^docs/migration-guide-' -e '^docs/tcw-3.0-migration-log.md' \
  | xargs grep -n 'extends'
```

plus `grep -rn extends skills/ agents/` for any shipped file that is not
Markdown (none holds the word at `9f43d5f6`). The plan names every passage it finds, including the ones that
name the key without the command (`skills/configure/SKILL.md:4`, the
`when_to_use` line's "taxonomy and capabilities extends";
`skills/configure/references/personal.md:145-148`;
`skills/capabilities/SKILL.md:26`, `:89`, `:138`;
`docs/guide/linking-and-validation.md:139`). The guides' fuller rewrite, and
`docs/use-cases.md`, stay TCW-117's.

8.2. **The capability records** named under "Capability changes" are
rewritten in this item's implementation, in this repository's 3.x layout
(TCW-111 Non-goals: this repository's records keep `meta.yaml` until TCW-116),
so the CLI that drives this repository's lifecycle still reads them.

## Abstraction litmus test

| Operation | Layer | Verdict |
| --- | --- | --- |
| A store's view of an axis is built from `sources(axis)` and each source's own objects (Design 1.1) | model | Passes: a tracker or database store can list one project's own objects by path and ask the registry for the sources; nothing assumes folders. |
| A source with no store contributes nothing; one that cannot be read raises `InheritedUnavailable` (Design 1.2, 1.3) | model | Passes: "this project keeps nothing on this axis" and "it cannot be read here" are states any store reaches. |
| The view is built only when needed (Design 1.4) | model | Passes: it is an order of operations, not a storage trick. |
| `extends_add` and `extends_remove` removed from `TaxonomyStore` and `CapabilitiesStore` (Design 1.5) | model | Removes two operations; nothing replaces them, since the parent link is the registry's (TCW-108). |
| The chain, the field-by-field combination, `overrides`, unused declarers (Design 2.1, 2.2, 2.4, 2.5) | model | Passes: written once in `tcw/store/base.py` over declarations and a relation (Design 2.6); another store gives it the same inputs. |
| The body and attached files of a combined object (Design 2.3) | files store, private | `description.md`, `resources/` and `prependedDocs` are how the files store keeps a body; another store keeps a body its own way and combines it by the same "nearest non-empty" rule. The model's part is that a declaration declares a description (possibly empty) or none: a database keeps that as an empty text against no row or a null column, so "declared empty" and "not declared" stay apart in any store. |
| What is inherited at a path (Design 2.7) | model | Passes: a question about paths and the sources, answered by the same function. |
| `get` of an id-path or a full identifier (Design 3.1) | model | Passes: by path and owner, both store-neutral (TCW-110 Design 1). |
| Reading own objects without the view (Design 3.4) | model | Passes. |
| `tcw capabilities add` refused, and `tcw taxonomy add` writing an override, at an inherited path; `set` writes the active project's object at the same path, a cleared field as `null`; `reset`; `rm` (Design 4.1-4.4) | model | Passes: each creates, changes or deletes one object of the active project, keyed by its path, and none needs to know whether an object it changes in place is an override. Where the files store puts the folder (the same path in its own store root) is its own detail. |
| The opaque `id` removed (Design 5) | model | Passes: removes an identity that only the files store's 3.x override pointer needed. |
| `tcw validate`'s findings (Design 6) | model | Passes: each is a question about declarations and paths, and 6.1's "declares a description" is the model's, not a file's (Design 2.3); 6.4's `overrides` key and 6.8's file are about files the files store wrote. |
| The web API's `503` for `InheritedUnavailable` (Design 4.5) | CLI and web | Not a store operation. |
| A capability's declared description read apart from its combined body, and a body edit writing only it (Design 4.5) | model | Passes: "declares a description, or none" is already the model's (Design 2.3), so any store answers it for one object of one project; only the files store keeps it as `description.md`. |

No operation of the work backend interface (`tcw/work/backend.py`) changes.

## Use cases

- **UC-1 (a single project).** No parents, so `sources(axis)` is the project
  alone (TCW-108 Design 5.2): every view is its own objects, no other
  project's store is opened (3.5), and listings print what they print today
  apart from the identifiers TCW-110 changed. `extends` is gone, so its
  configuration shrinks if anything. **One cost:** Design 6.1 makes `name` and
  a description required on every object, where today a missing `name`
  falls back to the folder's (`tcw/store/fs.py:1736`, `:2336`) and a missing
  description passes (`Status` is already required, `:2828-2829`). `add` has
  always written both (`:1861-1864`, `:2488-2499`), every object in this
  repository has both (49 terms and 91 capabilities, checked by listing
  them), and `tcw migrate` fills them in (Notes), so only an object written
  by hand without them is affected. This is settled by the design, not a
  choice of this spec: a partial override whose original is gone must fail
  as incomplete (design.md:471-473), and without a marker such an orphan
  cannot be told apart from an incomplete object of a single project, so the
  rule reaches both (Notes, decided 2026-10-22). **A smaller change:** `tcw
  capabilities set` writes a cleared field as `null` instead of deleting the
  key (4.2); the object reads the same.
- **UC-2 and UC-7 (a library others read; a public library).** The reader
  names the library as a parent passing the axes it wants (TCW-108); nothing
  is written into the library (4.2 writes only the reader's own objects; a
  full identifier of the library's object can only be overridden, never
  changed, 4.2, 4.4). The reader's status decisions are overrides at the same
  paths, holding only `Status`, so they keep following the library's names
  and descriptions (design.md:463-465). A library that moves an entry leaves
  the reader's partial override incomplete, and the reader's `tcw validate`
  fails naming it (6.1); the library cannot see it, which UC-2's requirement
  already accepts ("only the readers' `tcw validate` notices"). A library that
  later adds an entry at a path a reader already uses makes the reader's
  object an override, marked in `show`, JSON and the web app (3.3), which is
  how an unintended clash is seen (design.md:467-470). A reader that wants
  its own term where the library has one runs `tcw taxonomy add` there and
  gets an override holding only what it gave (4.1).
- **UC-3 (a monorepo).** Several levels and per-axis inheritance come from
  `inherit` on each parent link (TCW-108 Design 5.1): `server` taking taxonomy
  from `shared` and `core`, and capabilities only from `shared`, is
  `parents: [{id: shared}]` with `shared`'s own link to `core` passing
  taxonomy only, or a second parent link to `core` with `inherit:
  [taxonomy]`. Each inherited object is read from exactly one project however
  many routes reach it, since each source is read once and an object is
  combined along one chain (2.1). UC-3's requirement that "a bare reference
  to a name defined in two inherited projects is refused as ambiguous" and
  "a local term with the same name wins without a warning" changes: the load
  order decides and warns (2.5, 3.6), and a local object at an inherited path
  is an override, marked (3.3). That wording is TCW-117's to change (Notes).
- **UC-4 (a planning workspace).** A workspace parent with `inherit: none`
  passes nothing, so a code repository's CI need not clone it (3.5, TCW-108
  Design 6.2). One with `inherit: all` and no taxonomy or capabilities store
  contributes nothing and is not an error (1.2). A source whose store lives in
  another repository is opened from its own configuration through the
  command's registry (1.1, TCW-110 Design 6.1, 7), and one not provisioned
  here is exit 7 with Design 1.3's third message, not exit 1.
- **UC-5 (one Jira project for several TCW projects).** Not touched: this
  item reads no work item and no Jira ticket. The records gate's change (7.1)
  reads capability ledgers only.
- **UC-6 (a related project not on this machine).** The known gap that a
  missing `extends` project stops reading the project's own entries, with
  exit 1, is closed: own reads work with a warning (3.4), and only commands
  that need the view stop, with exit 7 (3.5); `tcw validate` reports "could
  not check" (6.5). The other gap there (references into a missing project
  reported as errors) is TCW-110's (Design 6.3).
- **UC-8 (several families on one machine).** Not touched beyond TCW-107's
  and TCW-108's rules: a source is located through the command's one
  registry, never by a second walk from another project (1.1).
- **S-2 (harness).** Everything is in the CLI: a capability override is
  written by `tcw capabilities set`, and a term override by `tcw taxonomy add`
  at the inherited path (4.1, 4.2); only a later change to a term override's
  other fields is written by hand, as any term field is today (Non-goals).
  The skill passages that name removed commands are changed here (8.1).
- **S-3 (backend).** Taxonomy and capabilities are files in both work
  modes; no work backend operation changes (litmus table).
- **S-4 (copies of a checkout, CI).** A fresh clone without its parents can
  read and validate its own objects (3.4, 6.5); TCW-108's worktree and
  manifest rules locate the sources.
- **S-5 (personal configuration).** Another project's store is opened from
  its committed configuration only (1.1, Non-goals); `extends` was never
  personal (`skills/configure/references/personal.md:145-148`).
- **S-6 (unattended runs).** Exit 7 is one meaning (inherited content not
  available) for every taxonomy and capabilities command; exit 0 with a
  `warning:` line where only the project's own declaration is shown (3.4) is
  stated, and each such record says `"partial": true`, so a script can tell
  from the record itself.
- **S-8 (stopping halfway).** Each write is one object's files, staged and
  rolled back as today (`_write_files`, `tcw/store/fs.py:1505-1534`); `reset`
  and `rm` delete one folder. Nothing has more than one step.
- **S-9 (versions).** A 4.0 configuration holding `extends` is refused with a
  message naming `parents:` (1.5); a state file holding `overrides:` or
  `id: cap-…` is reported naming `tcw migrate` (5.3, 6.4); a 3.x file is
  TCW-111's (Design 2.6 f). Old code reading new files is not a constraint.
- **S-10 (things TCW does not own).** Sources are found only through
  declared parent links (TCW-108), never by looking inside a project.
- **S-11 (version control).** Nothing reads or changes git.

The checklist: (1) it locates sources through the registry and opens their
stores from their own configuration, in another repository or not (UC-4),
and reports one that is not here (UC-6); (2) it writes only the active
project's own objects (4); (3) it reads across projects along parent links,
several levels, each source once (UC-3), with exit 7 or "could not check"
for a missing one (UC-6), and no Jira (UC-5); (4) it passes the litmus test
and is the same in both work modes; (5) nobody's decision is assumed; (6) the
CLI carries everything; (7) every write is one step; (8) a single project
pays nothing but the completeness rule of 6.1; (9) `extends`, `overrides:`
and `id: cap-…` are refused or reported with a message; (10) the criteria
use projects in separate folders, one of them in a second repository (AC
19), and a parent absent from the machine (AC 16-18).

## Acceptance criteria

Every fixture is a TCW 4.0 project with a valid lower-case ID, its stores at
the defaults (`docs/taxonomy`, `docs/capabilities`), and its parents located
by a manifest entry. "`app` inherits from `core`" means `app` has `parents:
[core]` (so `inherit: all`). An object "with" fields means a folder holding
its state file with `tcw-version` and those fields, and a `description.md`
when a description is named. "Shows" means `tcw <axis> show <input> --json`
run in the named project, and "lists" means the identifiers on standard
output of `tcw <axis> list`. Unless a criterion says otherwise, a command
exits 0.

1. **Inherited through the parent link.** `core` has a term `invoice`
   (`name: Invoice`, `kind: Vocabulary`) and a capability `cli/x` (`name: X`,
   `Status: Missing`); `app` inherits from `core` and has neither. In `app`,
   `tcw taxonomy list` lists `core.taxonomy/invoice` and `tcw capabilities
   list` lists `core.capabilities/cli/x`; `show invoice` has `full-id`
   `core.taxonomy/invoice`, `owner` `core` and `overrides` `null`.
2. **Per-parent `inherit`.** With `parents: [{id: core, inherit: [taxonomy]}]`,
   `app` lists `core.taxonomy/invoice` and not `core.capabilities/cli/x`; with
   `inherit: none`, neither; with `inherit: [capabilities]`, only the
   capability.
3. **Several levels.** `lib` inherits from `core`, `app` from `lib`; `lib`
   has a term `money`. `app` lists `core.taxonomy/invoice` and
   `lib.taxonomy/money`. With `lib`'s link to `core` set to `inherit:
   [config]`, `app` does not list `core.taxonomy/invoice` (TCW-108 Design 5.1).
4. **A parent with no store.** `app` has `parents: [ws, core]`, where `ws`
   has no taxonomy or capabilities store and declares none. Both `list`
   commands in `app` exit 0 and list `core`'s objects.
5. **A partial override.** `core`'s `cli/x` has `Status: Missing`,
   `Priority: P1`, and the description `Core body`. `app` has its own `cli/x`
   holding only `Status: Supported` (no `description.md`). In `app`, `show
   cli/x` has `full-id` `app.capabilities/cli/x`, `owner` `app`, `name` `X`,
   `fields.Status` `Supported`, `fields.Priority` `P1`, body `Core body`, and
   `overrides` `core.capabilities/cli/x`; the text `show` has the line
   `overrides: core.capabilities/cli/x`; `list` prints
   `app.capabilities/cli/x` once and never `core.capabilities/cli/x`; the
   `list --json` record for it has the same `overrides` and no `partial` key;
   `tcw capabilities search "Core body"` in `app` lists
   `app.capabilities/cli/x`.
6. **Fields combine key by key.** In AC 5, `app`'s `cli/x` also holding
   `Priority: null` makes `show cli/x` have no `Priority` field; holding
   `Subject: [app.taxonomy/money]` over `core`'s
   `Subject: [core.taxonomy/invoice, core.taxonomy/payment]` gives exactly
   `[app.taxonomy/money]`.
7. **The body and attached documents.** `core`'s `cli/x` has
   `prependedDocs: [resources/a.md]` (with that file). `app`'s override with
   no `prependedDocs` gives a body starting with `a.md`'s text; with
   `prependedDocs: null`, a body without it; with `prependedDocs:
   [resources/b.md]` and `b.md` in `app`'s `cli/x/resources/`, a body starting
   with `b.md`'s text and not `a.md`'s. An `app` `description.md` holding
   `App body` gives the middle `App body`; an empty one gives `Core body`.
8. **A term override.** `core`'s `invoice` has the description `Core text`
   and `resources/d.png`. `app` has its own `invoice` holding only
   `relatesTo: [app.taxonomy/money]`, and its own term `money`. In `app`, `show
   invoice` has `full-id` `app.taxonomy/invoice`, `name` `Invoice`, `kind`
   `Vocabulary`, description `Core text`, `relatesTo`
   `["app.taxonomy/money"]`, attachments `["resources/d.png"]`, and
   `overrides` `core.taxonomy/invoice`.
9. **Only a declaring project replaces** (TCW-108 AC 11's shape). `bb` has
   `X` with `Status: Missing`; `cc` and `dd` inherit from `bb`; `cc` has its
   own `X` holding `Status: Supported`; `dd` has none; `ee` has `parents: [cc,
   dd]`. In `ee`, `show X` has `fields.Status` `Supported`, `full-id`
   `cc.capabilities/X` and `overrides` `bb.capabilities/X`; `tcw validate` in
   `ee` reports no warning containing `X`.
10. **Two unrelated projects at one path.** `cc` and `dd` have no parents in
    common; `ee` has `parents: [cc, dd]`; `cc`'s `X` has `name: C`, `Status:
    Supported`, `Priority: P1`; `dd`'s `X` has `name: D`, `Status: Missing`.
    In `ee`, `show X` has `name` `D`, `full-id` `dd.capabilities/X`, no
    `Priority` field, and `overrides` `null`. `tcw validate` in `ee` exits 0
    with exactly one warning about `X`, whose `where` is
    `.tcw/tcw-config.yaml` and whose message contains `'cc' and 'dd'` and
    `uses the one from 'dd'`; `tcw capabilities list` in `ee` prints the same
    message on standard error after `warning: ` and lists `dd.capabilities/X`
    once. With `parents: [dd, cc]` the warning says `uses the one from 'cc'`
    and `show X` has `name` `C`. The same two projects each holding a term
    `t` (`cc`'s `name: C`, `dd`'s `name: D`): `tcw taxonomy show t` in `ee`
    exits 0 with `full-id` `dd.taxonomy/t` and `name` `D`.
11. **Siblings both overriding a common parent** (the user's example,
    2026-10-22). In AC 9's family, `dd` also has its own `X` holding
    `Priority: P2`. In `ee`, `show X` has `fields.Status` `Missing` (`bb`'s:
    `cc`'s `Status: Supported` is not used, although `dd` never set
    `Status`), `fields.Priority` `P2`, `full-id` `dd.capabilities/X` and
    `overrides` `bb.capabilities/X`; `tcw validate` warns once, naming
    `'cc' and 'dd'`, `uses the one from 'dd'` and `nothing from 'cc''s`.
12. **An override is never a warning.** In AC 5, `tcw validate` in `app`
    reports no warning about `cli/x`.
13. **An orphaned partial override is incomplete.** `app` has its own
    `cli/x` holding only `Status: Supported`, and no source has `cli/x`.
    `tcw validate` in `app` exits 1 with an error at
    `docs/capabilities/cli/x/tcw-capability.yaml` whose message contains
    `app.capabilities/cli/x is incomplete`, `name` and `description.md`. A
    term `invoice` holding only `relatesTo` in `app`, with no source having
    `invoice`, gives the same error with `name` and `description.md`. A
    capability with `name`, `Status` and an empty `description.md`, and a
    term with `name` and an empty `description.md`, give no such error.
14. **A full copy whose original moved stands.** `app`'s `cli/x` has `name`,
    `Status` and a `description.md`; `core` has no `cli/x`. `tcw validate` in
    `app` reports nothing about `cli/x`.
15. **`extends` is gone.** `tcw taxonomy extends add core` and `tcw
    capabilities extends rm core` exit 2 (no such command). `taxonomy:
    {extends: [core]}` in `app`'s `.tcw/tcw-config.yaml` makes `tcw taxonomy
    list` exit 1 with a message containing `'taxonomy.extends' was removed in
    TCW 4.0` and `parents:`, and `tcw validate` report an error at
    `.tcw/tcw-config.yaml`; the same with `capabilities`. The same key in
    `core`'s file, `core` being `app`'s parent, leaves `tcw taxonomy list` in
    `app` exiting 0. `TaxonomyStore` and `CapabilitiesStore` have no
    `extends_add` or `extends_remove`, and `FsTaxonomyStore` and
    `FsCapabilitiesStore` have no `extends` attribute. With the variable
    `TCW_TAXONOMY_EXTENDS__APP=core` set, `tcw work list` in `app` exits 1
    with TCW-109 Design 4.3's message, containing `no configuration key is
    written`, and not its message for a shared key (`is a shared key`); the
    same with `TCW_CAPABILITIES_EXTENDS__APP`.
16. **A parent not on this machine.** `app` inherits from `core`, whose
    manifest entry names a folder that does not exist; `app` has its own
    term `money` and its own capability `cli/y` (complete), and an override
    `cli/x` holding only `Status: Supported`. In `app`:
    - `tcw taxonomy list --local` prints `app.taxonomy/money`, and `tcw
      capabilities list --local` prints `app.capabilities/cli/x` and
      `app.capabilities/cli/y`;
    - `tcw taxonomy show money` and `tcw taxonomy show app.taxonomy/money`
      exit 0 with a standard error line containing `showing only 'app''s own
      declarations`; `tcw capabilities show cli/x --json` exits 0 and its
      record has `"partial": true` and no `overrides` key, and the text `show
      cli/x` has a `partial:` line and no `overrides:` line; each record of
      `tcw capabilities list --local --json` has `"partial": true`;
    - `tcw taxonomy list`, `tcw taxonomy search a`, `tcw taxonomy show invoice`
      and `tcw taxonomy add Invoice` exit 7 with a message containing `'app'
      inherits its taxonomy from project 'core', which is not on this
      machine`;
    - `tcw capabilities set cli/y --status Supported` and `tcw capabilities rm
      cli/y` exit 0; `tcw capabilities set cli/z --status Supported` (an id-path
      `app` has no object at), `tcw capabilities reset cli/x` and `tcw
      capabilities drift` exit 7; `tcw capabilities rm cli/z` exits 4;
    - `tcw validate` exits 0, with one `unresolved` finding for `core` whose
      message contains `could not check the taxonomy inherited from it` and
      `could not check the capabilities inherited from it`, and no
      `incomplete` error for `cli/x`; with `app`'s `cli/y` also holding the
      unknown field `Foo: 1`, it exits 1 with that field's error at
      `cli/y`'s state file, since the checks of what `app` declares still
      run.
17. **A view-only parent not on this machine.** `app` has `parents: [{id:
    ws, inherit: none}, core]` and `ws` is not on this machine. Both `list`
    commands in `app` exit 0 and list `core`'s objects.
18. **A parent whose store cannot be read.** A test makes opening `core`'s
    taxonomy store raise `StoreNotProvisioned`. In `app`, `tcw taxonomy list`
    exits 7 with a message containing `whose taxonomy store cannot be read
    here`; `tcw taxonomy list --local` exits 0; `tcw validate` exits 0 with an
    `unresolved` finding at `.tcw/tcw-config.yaml` containing `could not check
    the taxonomy inherited from 'core'`.
19. **A source in another repository.** `core` is its own git repository
    beside `app`'s, and `core`'s capabilities store is at `capabilities.path:
    ledger`. In `app`, `tcw capabilities list` lists `core`'s capabilities from
    `core/ledger`.
20. **Writing an override.** In AC 5's family before `app` has `cli/x`, `tcw
    capabilities set cli/x --status Supported` in `app` writes
    `docs/capabilities/cli/x/tcw-capability.yaml`, named on standard error,
    whose keys are exactly `tcw-version` and `Status`, and no other file;
    `tcw capabilities set core.capabilities/cli/x --field Priority=P2` then
    adds `Priority: P2` to the same file and writes nothing else. No folder
    named `core` is created in `app`'s store. When `app`'s store already has
    a folder `cli/x` with no state file (an organising folder holding `app`'s
    own object `cli/x/z`), the first `set` writes the state file into that
    folder, and `cli/x/z` is unchanged and still listed.
21. **Setting a project not inherited from.** `app` has `parents: [{id:
    core, inherit: [taxonomy]}]`. `tcw capabilities set core.capabilities/cli/x
    --status Supported` exits 3 with a message containing `'app' does not
    inherit it`, and writes nothing.
22. **`--parent` on an inherited capability.** In AC 5's family before
    `app` has `cli/x`, `tcw capabilities set cli/x --parent
    core.capabilities/cli` exits 0 and `app`'s new `cli/x` state file holds
    `parent: core.capabilities/cli` (and no `Status`).
23. **`add` at an inherited path.** In AC 1's family, with `core`'s
    `invoice` having the description `Core text`:
    - `tcw capabilities add cli/x` in `app` exits 3 with a message
      containing `core.capabilities/cli/x` and `tcw capabilities set`, and
      writes nothing;
    - `tcw taxonomy add Invoice` with nothing on standard input exits 3 with
      a message containing `core.taxonomy/invoice` and `nothing given
      differs`, and writes nothing;
    - `printf 'App text' | tcw taxonomy add Invoice` exits 0, writes
      `app`'s `docs/taxonomy/invoice/tcw-taxonomy.yaml` whose keys are
      exactly `tcw-version`, and `description.md` holding `App text`, and
      standard error has `app.taxonomy/invoice overrides
      core.taxonomy/invoice`; `show invoice` then has `name` `Invoice`,
      `kind` `Vocabulary`, description `App text` and `overrides`
      `core.taxonomy/invoice`;
    - with `core`'s `invoice` holding `relatesTo: [core.taxonomy/money]`,
      `tcw taxonomy add 'Bill' --slug invoice` writes a state file whose
      keys are exactly `tcw-version` and `name` (`Bill`), and `show invoice`
      keeps `relatesTo` `["core.taxonomy/money"]`;
    - `tcw capabilities add cli/new` writes a state file with no `id` key.
24. **`reset`.** After AC 20, `tcw capabilities reset cli/x` in `app` removes
    `app`'s `docs/capabilities/cli/x` and `show cli/x` then has `full-id`
    `core.capabilities/cli/x`; the same with `reset core.capabilities/cli/x`.
    `reset cli/y` of a standalone `cli/y` exits 3 with a message containing
    `tcw capabilities rm`; `reset cli/x` with no `app` object exits 3. With
    `app`'s `cli/y` holding `Blocked by: app.capabilities/cli/x`, `reset
    cli/x` exits 3 with a message naming `app.capabilities/cli/y` and
    `Blocked by`, and removes nothing.
25. **`rm` of an override.** `tcw capabilities rm cli/x` of `app`'s override
    exits 0, removes the folder, and standard error has `cli/x now shows
    core.capabilities/cli/x`; `tcw taxonomy rm invoice` of AC 8's override
    likewise names `core.taxonomy/invoice`. `tcw capabilities rm
    core.capabilities/cli/x` in `app` exits 3 with a message containing
    `belongs to project 'core'`, and removes nothing.
26. **A full identifier names its owner's object.** In AC 5, `show
    core.capabilities/cli/x` in `app` has `fields.Status` `Missing`, `full-id`
    `core.capabilities/cli/x` and `overrides` `null`. In AC 9's `ee`, `show
    bb.capabilities/X` has `fields.Status` `Missing`, and `show
    cc.capabilities/X` has the same `name`, `fields` and body as `show X`.
    `show app.capabilities/cli/z` for an id-path `app` only inherits exits 4.
    With `bb`'s folder removed (its manifest entry kept), `show
    cc.capabilities/X` in `ee` exits 7 with a message containing `'cc'
    inherits its capabilities from project 'bb'`; with `cc`'s folder removed
    instead, it exits 5. A project `zz` with no parents, whose manifest
    locates `cc`, has its own capability `q` holding `Blocked by:
    cc.capabilities/X`: with `bb`'s folder removed, `tcw validate` in `zz`
    reports no finding that names `cc.capabilities/X`.
27. **`--local`.** In AC 5, `tcw capabilities list --local` in `app` prints
    `app.capabilities/cli/x` and not `core.capabilities/cli/x`.
28. **No opaque id.** `show --json` of any capability has no `id` key and the
    text `show` no `id:` line. A `tcw-capability.yaml` in folder `cli/x`
    holding `id: cap-1a2b3c` makes `tcw validate` report TCW-111's row k
    error at that file; `id: x` gives none; a capability with no `id` gives no
    `missing id` finding.
29. **The `overrides:` key.** `app`'s `cli/x` holding `overrides:
    core/cap-1a2b3c` and `Status: Supported` makes `tcw validate` report an
    error at that file containing `'overrides' was removed in TCW 4.0`, and
    `show cli/x` in `app` still combines it with `core`'s `cli/x` (AC 5's
    result).
30. **Checks that go.** `app` inherits from `core` and has a top-level term
    folder named `core`: `tcw validate` reports no finding containing
    `collides with local top-level`. `grep -rn "cycle in taxonomy
    federation\|cycle in capability federation\|collides with local
    top-level" tcw/` finds nothing.
31. **The records gate.** In `app` with AC 5's override, an item whose
    `capabilities.yaml` has `changed: [app.capabilities/cli/x]` passes the gate
    for that entry; `new: [core.capabilities/cli/x]` is reported as still
    `Missing` (core's own); after `reset cli/x`, `removed:
    [app.capabilities/cli/x]` passes, though `core.capabilities/cli/x` exists.
    With `core` not on this machine, `changed: [core.capabilities/cli/x]` is
    reported as not checked, never as absent.
32. **Drift.** `app` inherits `cli/x` and `cli/y` from `core`; `app`'s own
    `cli/x` sets `Status`, and its own `cli/y` sets only `Priority`. `tcw
    capabilities drift` prints an `unreviewed:` line for `cli/y` and none for
    `cli/x`.
33. **The web app.** `tcw serve` in `app` with AC 5's override:
    `GET /api/capabilities/cli%2Fx` has `overrides` `core.capabilities/cli/x`;
    a `PATCH` of it with a fresh revision answers 200 and changes `app`'s
    `cli/x` state file; a `PATCH` of an inherited capability `app` does not
    override answers 403 with `code` `read-only`, as today
    (`tcw/serve/server.py:61-62`), and writes nothing. With `core` not on
    this machine, `GET /api/taxonomy` answers 503 with `code`
    `inherited-unavailable`.
34. **A nested override is not a misplaced folder.** `core` has `cli/x` and
    `cli/x/y` (whose `parent` is `core.capabilities/cli/x`); `app` overrides
    both, holding only `Status` in each. `tcw validate` in `app` gives no
    TCW-111 Design 3.2 warning for `cli/x/y`.
35. **A single project opens no other.** In a project with no parents, a
    test that records every tree store opened, and every call of
    `project_folder`, while each of `tcw taxonomy list`, `tcw capabilities
    list` and `tcw validate` runs, sees for each command only stores whose
    root is inside that project's own folder (its `docs/taxonomy` and
    `docs/capabilities`; `tcw taxonomy list` opens no capabilities store),
    and no call of `project_folder` with an ID other than the project's own.
36. **The pre-2.5.0 store file.** A `config.yaml` at `app`'s taxonomy root
    gives the error whose message contains `parents:` and does not contain
    `extends`.
37. **Shipped text.** `test_every_command_named_in_shipped_text_exists`, the
    owned-document command check of `tests/test_docs_describe_3_0.py`, and
    `test_documented_verbs_and_flags_exist` for `README.md` and every other
    file it reads pass; and Design 8.1's sweep, with `grep -n 'extends'`
    narrowed to `grep -n 'extends add\|extends rm\|\(taxonomy\|capabilities\)
    extends'`, finds nothing, `README.md` and the two `federate`
    capability descriptions included.
38. **The suite passes as CI runs it** (bare `pytest`).
39. **A source object with a version problem.** `core`'s `cli/x` state file
    has `tcw-version: 99.0.0` (newer than the running TCW); `core` also has
    `cli/w`. In `app`, `tcw capabilities list` exits 1, lists
    `core.capabilities/cli/w` and not `cli/x` in any form, and prints a
    message naming `core`'s `cli/x/tcw-capability.yaml` on standard error.
    With `app` also holding its own `cli/x` with only `Status: Supported`:
    `tcw validate` in `app` reports no `incomplete` error for `cli/x` and
    one `unresolved` finding containing `could not check capabilities
    cli/x`; `tcw capabilities show cli/x` and `tcw capabilities reset cli/x`
    exit 1 with the version message and change nothing; `tcw capabilities
    set cli/x --field Priority=P2` exits 0 and changes `app`'s file. With
    `app` having no `cli/x`, `tcw capabilities add cli/x` exits 1 with the
    version message and writes nothing.
40. **A term named only by an override.** `app`'s term `money` is named only
    in the `Subject` of `app`'s override `cli/x` (which `core`'s `cli/x` does
    not name). `tcw taxonomy rm money` in `app` exits 3 with a message naming
    `cli/x` and `Subject`, and removes nothing.
41. **Field checks on the combined object.** `app`'s override `cli/x` holding
    only `Status: Partial`, over `core`'s `cli/x` with no `Gaps`, makes `tcw
    validate` in `app` report `Partial requires Gaps` at `app`'s
    `cli/x`; `core`'s `cli/x` holding `Gaps: something` makes it pass.
    `core`'s `cli/x` holding `Blocked by: core.capabilities/gone` (no such
    object) gives `app`'s `tcw validate` no finding naming
    `core.capabilities/gone`, since `app` does not declare that reference.
42. **Clearing a field writes `null`.** `app` has no parents and its own
    complete `cli/y` holding `Priority: P1`. `tcw serve` in `app`: a `PATCH
    /api/capabilities/cli%2Fy` with `"fields": {"Priority": null}` and a
    fresh revision answers 200, the state file then holds `Priority: null`,
    `show cli/y` has no `Priority` field, and `tcw validate` reports nothing
    about `cli/y` (6.2's value checks read the combined object, where `null`
    leaves no field; today's `Priority` check, `tcw/store/fs.py:2832`, read
    on the raw file, would report `null`). In AC 5's family, the same
    `PATCH` of `app`'s override `cli/x` leaves `Priority: null` in `app`'s
    file, and `show cli/x` has no `Priority` field although `core`'s `cli/x`
    has `Priority: P1`.
43. **A clash stops warning once it is decided.** In AC 10's family, `ee`
    gets its own `X` with `name: E`, `Status: Supported` and a
    `description.md`: `tcw validate` and `tcw capabilities list` in `ee` give
    no warning about `X`, and `show X` has `full-id` `ee.capabilities/X` and
    `overrides` `dd.capabilities/X`. With `ee`'s `X` holding only `Status:
    Supported`, the warning is still given, and contains `a complete object
    of its own`. In AC 11's family, `dd`'s own `X` being complete does not
    stop the warning in `ee`, since `cc` does not pass the axis to `dd`.
44. **A web body edit writes the declared description only.** In AC 7's
    family, `core`'s `cli/x` also has a `description.md` holding `Core
    body`, and `app`'s override `cli/x` holds only `Status: Supported`, with
    no `description.md`. `tcw serve` in `app`: `GET
    /api/capabilities/cli%2Fx` has a `capability.body` starting with
    `a.md`'s text and holding `Core body`, and `declaredDescription`
    `null`; a `PATCH` with `"body": "App body"` and a fresh revision answers
    200, `app`'s `docs/capabilities/cli/x/description.md` then holds exactly
    `App body`, and `show cli/x` has a body holding `a.md`'s text exactly
    once, followed by `App body`. In a project `solo` with no parents, its
    own `cli/y` with `prependedDocs: [resources/p.md]` and a
    `description.md` holding `Y body`: `GET` has `declaredDescription` `Y
    body`, and a `PATCH` with `"body": "Y edited"` leaves `description.md`
    holding exactly `Y edited` and a body holding `p.md`'s text exactly
    once. In the web client's tests, the editor opened on a capability whose
    detail has `declaredDescription` `Own` and a different `body` holds
    `Own` in its body field and shows the note that the page's body also
    holds text the edit leaves unchanged; saving after changing only a
    field sends no `body`.

### Coverage

| Design rule | Criteria |
| --- | --- |
| 1.1 sources per axis, own objects only, several levels, opened from the source's configuration | 1, 2, 3, 19 |
| 1.2 a source with no store contributes nothing | 4 |
| 1.3 `InheritedUnavailable`: missing, unreadable links, unreadable store (third message); an unreadable id-path from a source object's version problem, in `list`, `show`, `set`, `reset`, `add` and `tcw validate` | 16, 18, 39 |
| 1.4 the view built only when needed | 16 (own reads work), 35 |
| 1.5 `extends` gone: commands, store methods, key refused in the active project, ignored in another, out of TCW-109's table of keys | 15, 30 |
| 2.1 declarers and the chain | 9, 10, 11 |
| 2.2 fields combine key by key; `null`; lists whole; name fallback | 5, 6, 8 |
| 2.3 body (a declared empty description adds no text), `prependedDocs`/`appendedDocs` from the declaring member, attachments, `modified` | 7, 8, 23 (`add` writes only a description); 13 (a declared empty description counts as declared); `modified`: n/a, it is shown only by `tcw serve` and decides no outcome a command reports (`Term.modified`, `Capability.modified`, `tcw/store/base.py:338`, `:499`), and the rule is today's (`tcw/store/fs.py:2379-2388`) |
| 2.4 full identifier and owner of the chain's first member; `overrides` | 5, 8, 9, 11 |
| 2.5 unused declarers, whole-object choice, the warning, never for an override, silenced by a complete object in a project that inherits from both | 10, 11, 12, 43 |
| 2.6 one store-neutral function | 9, 10, 11 (each reaches it through the store) |
| 2.7 what is inherited at a path | 23 (through `add`), 16 (`add` exits 7), 39 (`add` exits 1 at an unreadable path) |
| 3.1 what an input names; exit 7 against 5 for another owner; existence checks need only the owner's own store; the two views agree | 1, 5, 26 |
| 3.2 listings: each id-path once, `--local`, `search` over the combined body, warnings on standard error, no mark in text | 5, 10, 27 |
| 3.3 `overrides` in every record and in `show`; no `id`; `partial` only on a record read without inherited content | 5, 16, 27, 28, 33 |
| 3.4 own reads never stop; by id-path and by full identifier; `partial` and no `overrides` | 16, 18 |
| 3.5 which commands need the view; exit 7 | 16, 17 |
| 3.6 no `AmbiguousRef` for a path | 10 (two sources at one path give an answer and exit 0, for a capability and for a term) |
| 3.7 what `tcw project info` shows | n/a here: no `tcw project` group exists on `v4` (`tcw/cli.py:560-610` registers `projects`), and it is TCW-115's (Non-goals); its inputs, 3.2's records and 2.5's warnings, are covered by 27 and 10 |
| 4.1 `tcw capabilities add` refused at an inherited path; `tcw taxonomy add` writes an override of what differs, never `relatesTo`, refused when nothing differs; no `id` | 16 (exit 7 when unknown), 23, 39 |
| 4.2 `set` writes the active project's object at the same path; a cleared field written as `null` on every own object; an organising folder becomes an object; refused for a project not inherited; `--parent` | 20, 21, 22, 42 |
| 4.3 `reset` | 24 |
| 4.4 `rm` of any own object; another project's refused; not found (exit 4) when the view cannot be built | 16, 25 |
| 4.5 the web app; a body edit writes the declared description only | 33, 44 |
| 5.1 `id` not written | 20, 23 |
| 5.2 `id` not an identity | 28 |
| 5.3 TCW-111 row k for capabilities | 28 |
| 6.1 an object that overrides nothing must be complete, stated on the declaration; not checked at an unreadable path | 13, 14, 39 |
| 6.2 each own object checked as combined; references only where declared | 13 (an override's missing fields are not reported, by contrast with 6.1), 29, 41 (combined field checks; an inherited reference not checked), 42 (`null` leaves no field) |
| 6.3 the unrelated-path warning in `tcw validate` | 10, 11, 43 |
| 6.4 `overrides` key | 29 |
| 6.5 "could not check" for inherited content; the checks of the project's own declarations still run | 16, 18 |
| 6.6 checks that go | 28, 30 |
| 6.7 a nested override agrees with its folder | 34 |
| 6.8 the pre-2.5.0 file's message | 36 |
| 7.1 the records gate; both uses of `extends` gone | 15 (no `extends` attribute), 31 |
| 7.2 drift | 16, 32 |
| 7.3 a term's capability referrers over own capabilities | 40 |
| 8.1 shipped passages, `README.md` and the capability descriptions included | 37 |
| 8.2 capability records rewritten in the 3.x layout | n/a as a criterion: the records gate checks them against this item's `capabilities.yaml` when the item leaves implementation (`route_capability_path` and `_LedgerReader`, `tcw/work/gates.py:331-437`) |

## Risks

- **Every federation fixture is written with `extends`.** The taxonomy and
  capabilities federation suites (`tests/test_capabilities_federation.py`,
  `tests/test_taxonomy.py`, `tests/test_override_references.py`,
  `tests/test_capabilities_reset.py`, and about thirty other files that
  mention `extends`, `grep -rln extends tests/`) connect projects through it,
  after TCW-108 has converted their relations to parent links passing the
  axis (TCW-108 Design 3.5, 3.6). Each must lose its `extends` line and
  rely on the link, and each 3.x override fixture (an `overrides:` pointer,
  often at `<alias>/<path>`) must move to the same path. A test that checked
  ambiguity (`AmbiguousRef`) now checks the load order and the warning. The
  plan reads each failure rather than editing its assertion.
- **Overrides become far more common, and each is visible.** In 3.x a reader
  rules on an inherited capability's status by writing an override; it still
  does. A reader of a large library may hold hundreds of status-only
  overrides, each listed as the reader's own object with `overrides` set. That
  is the design's intent (an override is the reader's object), but it means
  `--local` lists them all, and TCW-113's `--scope own` will too.
- **A decided clash still takes unset fields from one side** (Design 2.5).
  A complete object in a project that inherits from both declarers silences
  the warning, but "complete" means a name, a `Status` and a description,
  not every field: a `Priority` or `Gaps` it does not set still comes from
  the later declarer's side. The person who wrote it saw that object in
  `show`, so this is a visible choice, not a silent one. And a project whose
  complete object at the path predates the clash is never warned when an
  unrelated parent later adds one there: its object already decided the
  path, as a descendant's object at an ancestor's path does
  (design.md:480-481).
- **The completeness rule reaches every project** (UC-1). A hand-written
  object with no `name` or no `description.md` now fails `tcw validate`
  (Design 6.1). `tcw migrate` fills both in, and the message says what is
  missing.
- **An object read through a full identifier and through an id-path can
  differ only under the fallback load order** (Design 3.1): with TCW-108
  Design 4.4's depth-first order, two of `W`'s unrelated declarers may be
  ordered differently in `P` and in `W`. TCW-108 Design 4.5's warning is the
  signal; the plan tests the agreement (AC 26), not a difference.
- **Reading another project's object now reads that project's ancestry**
  (Design 3.1): `show Q.<axis>/X` exits 7 when an ancestor of `Q` is
  missing, where TCW-110's raw read would have succeeded. Reference checks
  are not affected, since they ask only whether `Q` has its own object.
- **The body rule changes for existing 3.x overrides** (Design 2.3): an
  override that listed no `prependedDocs` used to drop its original's, and now
  keeps them. `tcw migrate` must report each 3.x override whose original has
  `prependedDocs` or `appendedDocs` and that lists none, since its body will
  change (Notes).
- **Exit 7 for `add`** (Design 3.5) stops a person in a clone without a
  parent from adding a term or a capability, since `add` cannot tell whether
  the path is inherited, and so whether to refuse, to write a new object, or
  (for a term) to write only what differs. The message names `tcw project
  provision` (TCW-108 Design 6.2), and stopping is the only way not to write
  a full-copy override without knowing it.
- **`tcw taxonomy add` means two things** (Design 4.1): a new term where
  nothing is inherited, and an override of only what differs where
  something is. Standard error says which (`… overrides …`), and the refusal
  when nothing differs keeps a mistyped repeat of an inherited name from
  writing an empty override.

## Notes

### Decisions the design left to this spec

1. **The chain, and "the load order picks one", as a whole object** (Design
   2.1, 2.5): an object overrides only one in a project it inherits from, and
   of two unrelated declarers the later one is used whole. Reason: it is the
   design's "picks one"; folding unrelated objects field by field would make
   one capability out of two unrelated ones (the name of one and the `Gaps` of
   the other). It keeps TCW-108 Design 4.8's rule that only a declaring
   project replaces (AC 9). Confirmed by the user (Decided on 2026-10-22,
   Question 2).
2. **Lists replace whole; `null` removes** (Design 2.2), as for
   configuration (design.md:493-499), so objects and settings combine by one
   rule.
3. **`prependedDocs` and `appendedDocs` are fields like any other** (Design
   2.3), read from the declaring member's `resources/`; TCW-111 left their
   rework to this item. An override no longer drops its original's documents
   by not naming them.
4. **Complete means `name`, `Status` for a capability, and a declared
   description, possibly empty** (Design 6.1; in the files store a
   `description.md`): the design's "a name, a description", plus the field
   3.x already required, and exactly what `add` writes for a new object.
5. **The unrelated-path warning is at the active project's
   `.tcw/tcw-config.yaml`** (Design 6.3), as TCW-108 places the load-order
   warning, since its `parents:` decide the order.
6. **A source with no store contributes nothing** (Design 1.2).
7. **A source's unreadable store is exit 7, with a third message** (Design
   1.3), added to TCW-108's `InheritedUnavailable`.
8. **Reading own objects shows the own declaration with a warning** (Design
   3.4) rather than stopping.
9. **At an inherited path, `tcw capabilities add` refuses and `tcw taxonomy
   add` writes an override of only what differs** (Design 4.1), and both
   exit 7 when they cannot tell. Revised after the spec review: refusing both
   left no command that makes a term override, against `docs/use-cases.md`
   S-2; the capabilities axis keeps the refusal because `set` already makes
   its overrides.
10. **`set` accepts the full identifier of an object in the chain; `reset`
    too; `rm` only the active project's own** (Design 4.2-4.4).
11. **`rm` removes an override** (Design 4.4), and `reset` and `rm` both
    refuse while the active project references the override by its full
    identifier.
12. **A full identifier names the owner's object as its owner sees it**
    (Design 3.1).
13. **`extends` in the active project's file is refused, and ignored in
    another's** (Design 1.5).
14. **Text listings stay one identifier per line**; the `overrides` mark is
    in every record, in `show` and in the web app, and the unrelated-path
    warning is on standard error (Design 3.2, 3.3). Decided by the user
    (Decided on 2026-10-22, Question 1).
15. **The web app answers `InheritedUnavailable` with 503** (Design 4.5).
16. **`"schema": 2` is not bumped again** (Design 3.3): nothing ships between
    TCW-110 and this item.
17. **Documentation entries** (`tcw work docs`). The release note and the
    changelog get this item's `upcoming/` files. `skills/<component>/SKILL.md`,
    `skills/configure/references/<document>.md` and `docs/guide/<topic>.md`
    fire, and get the passages of Design 8.1 here; their fuller rewrite, and
    `docs/use-cases.md` (`Project-Setup-Change`), are TCW-117's, as the
    dispatching session decided for TCW-108 on 2026-10-22: nothing ships
    between the 4.0 children, and TCW-117 lands before TCW-118 cuts the
    release.

### Decided on 2026-10-22

1. **How a text listing marks an override (the user, Question 1).** Plain
   `list` output stays one identifier per line
   (`cli/rely-on-one-output-contract`). The override mark goes in the
   `--json` records, in `show`, in `tcw project info` (TCW-115, Design 3.7)
   and in the web app. This is a reading of the design's "Listings, `show`
   and `tcw project info` mark each object that replaces an inherited one"
   (design.md:467-470): "listings" means the listing's records, not its
   plain text. TCW-117 amends that line of the design and the guides to say
   so (Handoffs).
2. **A clash between unrelated declarers resolves to the whole object (the
   user, Question 2).** The later declarer's object wins entirely, and the
   clash warning names what was lost (Design 2.5). AC 11 is the example the
   user decided on: `cc` and `dd` both override `bb`'s `X`, `cc` sets
   `Status` and `dd` sets only `Priority`; `ee`, whose parents are `[cc,
   dd]`, sees `dd`'s object over `bb`'s, so `cc`'s `Status` is lost, and the
   warning names `cc` as the project whose object is not used.
3. **The completeness rule on a single project (the dispatching session,
   Question 3).** Settled by the design, not a question: a partial override
   with no original must fail as incomplete (design.md:471-473), and
   without a marker it cannot be told apart from an incomplete object of a
   single project. Kept as a note in Use cases (UC-1). The cost in this
   repository is nothing: its 49 terms and 91 capabilities all have a name
   and a description, and `Status` is already required
   (`tcw/store/fs.py:2828-2829`).

### Revised after the spec review

- `README.md`, the two `federate` capability descriptions, and
  `test_documented_verbs_and_flags_exist` joined Design 8.1 and AC 37; the
  sweep reads the same files as that test.
- AC 33 expects 403 `read-only` for a `PATCH` of an inherited capability, as
  today and as TCW-114 Design 1.4 keeps (Design 4.5).
- `set` writes a cleared field as `null` on every own object, so it never
  needs to know whether an object is an override (Design 4.2, AC 42).
- A source object with a version problem makes its id-path unreadable
  rather than absent (Design 1.3, AC 39).
- Design 3.1 states where it departs from TCW-110 Design 6.2, the exit 7
  against 5 split, and that existence checks need only the owner's own
  store; the claim that a clash makes the two views differ was wrong and is
  replaced (AC 26).
- The clash warning stops once a project that inherits from both has a
  complete object of its own at the path, which is what its advice says to
  do (Design 2.5, AC 43).
- An empty description has one meaning, stated in the model (Design 2.3,
  6.1).
- A record read without its inherited content says `"partial": true` and
  has no `overrides` (Design 3.4).
- `tcw taxonomy add` at an inherited path writes an override (Design 4.1).
- Both uses of `extends` in the records gate are named (Design 7.1).
- The messages TCW-114 replaces, and the object `set` and `reset` hand to
  its ownership check, are stated (Design 4.2-4.4, Handoffs).
- AC 30 and AC 35 were reworded to be checkable; two citations one line off
  were corrected; the coverage gaps the review listed each gained a line in
  an existing criterion.

### Revised after the plan review

- A web edit of a capability's body writes only the declared description,
  and the detail answer carries `declaredDescription` apart from the
  combined body (Design 4.5, AC 44; decided by the dispatching session,
  2026-10-22, on the plan review's D1). Without it, Design 2.3's inherited
  attached documents would be written into an override's `description.md`
  by every web save of its body and shown twice; the same doubling already
  happens in 3.x to a capability with its own `prependedDocs` or
  `appendedDocs`, and is fixed by the same rule.
- `declaredDescription` is the declared text with leading and trailing white
  space removed, the form the combined body uses (Design 4.5; the plan
  re-check's I6), so that a `description.md` ending in a newline does not
  make the editor's note appear for a capability whose body is only that
  text.

### Handoffs

Recorded on each ticket by the dispatching session when this spec is
accepted.

- **TCW-108** (landed): this item adds a third `InheritedUnavailable` message
  (Design 1.3) and rewords Design 6.5 row (c) (Design 6.5). Design 3.6 and 6.3
  and `test_check_federation_cycle` are removed here. This item also lists
  `cli/read-from-an-upstream-project`, which TCW-108's ledger changes first,
  to take out its remaining "`extends` its taxonomy and capabilities".
- **TCW-109:** `taxonomy.extends` and `capabilities.extends` are not 4.0 keys
  (Design 1.5): this item removes them from TCW-109's table of known keys (its
  Design 4.3), as TCW-109's handoff asks. Nothing else is needed from TCW-109.
- **TCW-110** (landed): its Design 3.1 paragraph "An inherited object, until
  TCW-112", and for taxonomy and capabilities the first two sentences of its
  6.2, are replaced by Design 3.1 here: every owner's object, not only an
  inherited owner's, is read combined over that owner's own sources, so
  reading `Q.<axis>/X` loads `Q`'s ancestry and exits 7 when an ancestor of
  `Q` is missing (exit 5 stays for `Q` itself not on this machine); the
  existence check of a reference (its 6.4) needs only `Q`'s own store. Rule 1
  of `route_capability_path` (`tcw/work/gates.py:354-355`), which its 6.2
  keeps, goes with `extends`; the records gate reads each entry in its
  owner's view (7.1).
- **TCW-111** (landed): `set --parent` on an inherited capability is allowed
  (4.2); `id: cap-…` is no longer written, and row k applies to capabilities
  (5); the paragraph "3.x override folders" of its Design 2.5 and its row
  exceptions go (6.4); a nested override agrees with its folder (6.7).
- **TCW-113:** the view of Design 2 is what `--scope up` lists for taxonomy
  and capabilities; `--scope own` lists the active project's own objects as
  `--local` does here, each combined; with `--project <id>` an override and
  its original are separate objects (Design 3.1: `--project core` returns
  `core`'s). Mixed status reads each project's own object at an id-path as
  that project sees it (`load_order(id)`, TCW-108 Design 4.6, and Design 3.1
  here). The web app's read-only rule replaces Design 4.5's "owner is the
  served project". The capability detail answer's `declaredDescription`
  (Design 4.5) is what the editor edits in every scope, so a view that
  shows another project's capability gives that owner's declared
  description.
- **TCW-114:** the operation its Design 10.2 asks for is Design 2.7 (which,
  besides exit 7, stops with the version message, exit 1, at an id-path a
  source's version problem makes unreadable, Design 1.3), and
  `tcw capabilities set` on an inherited capability writes an object of the
  active project at the same path (Design 4.2), as its Design 1.5 relies on.
  `rm` and `reset` already refuse another project's object
  (Design 4.3, 4.4), and `set` writes only the active project's (4.2).
  TCW-114 Design 1.3 replaces this item's two refusals of another project's
  object: `set`'s (4.2) keeps its reason, `, and '<P>' does not inherit it,
  so it cannot be overridden here`, and takes 1.3's tail in place of `;
  change it in '<Q>'`; `rm`'s (4.4) becomes 1.3's message with no reason;
  this item's tests of them (AC 21, AC 25) check only the parts 1.3 keeps
  (`'app' does not inherit it`, `belongs to project 'core'`). The object
  passed to TCW-114's ownership check by `set core.capabilities/cli/x` and
  `reset core.capabilities/cli/x` run in `app` is the object the command
  writes or removes, `app`'s own `cli/x`, never `core`'s; so neither is one
  of the writes its Design 1.5 refuses. The same holds for `tcw taxonomy add`
  writing an override (4.1). The web app's refusal stays 403 (Design 4.5,
  its 1.4). A move
  or rename of an object that others override leaves their overrides
  incomplete in their projects (Design 6.1), which is the design's "nothing
  breaks silently" (design.md:676-681); moving an override away from its
  original's path, or moving an object onto an inherited path, is refused
  by TCW-114 Design 5.4 g; any other move of an override is a move of an
  ordinary object. TCW-114 Design 1.3 rewords this item's `set` refusal
  (a capability that is not inherited) and `rm` refusal (another project's
  object) into its ownership check's one shape, so this item's tests of
  those two messages change when TCW-114 lands.
- **TCW-115:** `tcw project info` shows, per axis, the active project's own
  objects that override one, each with its `overrides`, and the count of
  Design 2.5's warnings (Design 3.7). If TCW-115 lands first, this item adds
  them; otherwise TCW-115 does.
- **TCW-116:** `tcw migrate` moves each 3.x override to its original's path
  (design.md:741-744), dropping `overrides:`; drops `id: cap-…` from every
  capability (Design 5.3); turns `taxonomy.extends` and
  `capabilities.extends` into parent links (design.md:724-732) and deletes
  the keys; writes `name:` from the folder (today's fallback) and an empty
  `description.md` into each 3.x object that lacks them and overrides
  nothing (Design 6.1), reporting each; reports each 3.x override that lists
  no `prependedDocs` or `appendedDocs` while its original does, since its body
  changes (Risks).
- **TCW-117:** the guides (`docs/guide/taxonomy-and-capabilities.md`,
  `docs/guide/multi-repo.md`, `docs/guide/linking-and-validation.md`) and the
  skills' fuller explanation of inheritance and overrides, beyond the passages
  changed here (Design 8.1); `docs/use-cases.md`: UC-2 and UC-3 (`extends`
  examples become parent links; "a bare reference … refused as ambiguous"
  and "a local term … wins without a warning" become "the load order decides
  and warns" and "an override, marked"; Design 2.5, 3.3), UC-6 and S-4 (the
  `extends` known gap is closed, Design 3.4, 6.5), S-6 (exit 7 for taxonomy
  and capabilities), and the "Inheritance (`extends`)" dimension row. Also
  the TCW-99 design's line "Listings, `show` and `tcw project info` mark each
  object that replaces an inherited one" (design.md:467-470), and the guides
  that repeat it: amend it to say that a listing marks overrides in its
  records (`--json`, the web app) and that plain `list` output stays one
  identifier per line, as the user decided on 2026-10-22 (Notes, Decided on
  2026-10-22, 1).
