---
name: capabilities
description: Drives `tcw capabilities` — the Capabilities axis of TCW (what a user can do). Use when a tcw work item has a product (user-facing) delta, or when coordinating capability wording across repos. The taxonomy axis is the `taxonomy` skill, the work axis the `work` skill.
when_to_use: Use when specifying or implementing a tcw work item that has a product (user-facing) delta, or when coordinating capability wording across repos — declaring the capabilities a change adds, changes or removes, changing the records alongside the code, linking them to taxonomy Features, checking a change against the standing ledger, or asking another project for canonical product-layer wording.
allowed-tools: Bash(tcw *), Read, Grep, Glob
metadata:
    author: Brian Cefali
license: Apache-2.0
dynamic_skill: false # which skills a project may override, and why: ../README.md
---
**Version check.** Under Claude Code, skip this: the session-start hook already ran it. Under any other harness, once per session before your first `tcw` command, run `bash "<plugin>/scripts/check_versions.sh"`, where `<plugin>` is two folders above the folder holding this `SKILL.md`, and pass on anything it prints to the user.

# The capabilities process

The standing ledger describes _what a user can currently do_. It is the third layer in the TCW chain: `Vocabulary -> Features -> Capabilities -> Work`. This skill keeps it true as work lands. Drive `tcw capabilities`: read with `list`/`show`/`search`, create with `add`, write status and fields with `set`, rename or move one of the project's own capabilities with `rename` and `move`, delete with `rm`, drop an override with `reset`, and locate the absolute resolved store with `path`; `tcw validate` checks the ledger with the rest of the project. Never hand-edit capability metadata when `set` applies, and never delete a capability folder by hand. Because `path` and `rm` are reserved as commands, read a capability literally named either with explicit `tcw capabilities show <name>`.

`Capability.modified` is read-only, adapter-provided presentation metadata for
viewers; it is not an editable capability field.

**The ledger is not necessarily `docs/capabilities/`.** `capabilities.path` in
`.tcw/tcw-config.yaml` can put it elsewhere and a `capabilities.repository`
block can put it in another repository, fetched here by `tcw project provision`
— so never compose a store path from the project root; ask
`tcw capabilities path`. A command needing a declared but missing ledger fails
(exit 1), names the repository it lives in, and tells you to run
`tcw project provision --component capabilities`; running `tcw project new`
instead would create a second, empty ledger beside the real one. Inheritance is
unaffected: it comes from your project's parent links, not from wherever the
tree sits.

Each capability is a **path-addressed folder** (`<path>/` = `tcw-capability.yaml` + `description.md`). Its path inside the store (e.g. `auth/login`) and its **full identifier**, `<project-id>.capabilities/<path>` (e.g. `shop.capabilities/auth/login`), which names the project it belongs to, are its only names; it carries no separate `id`. Every command that takes a capability accepts its full identifier, its `tcw://` address (`tcw://shop.capabilities/auth/login`), or its path in the active project, the project whose folder the command runs in; never a `#heading`. Capabilities may carry `Subject` (a **multi-valued** loose taxonomy pointer — a list of terms) and `Feature` (a strong pointer to a taxonomy feature); each term given is stored as its full identifier. `--parent` on `add` and `set` records the capability it belongs under, by its full identifier, in `parent:`; an empty `--parent` clears it. The taxonomy axis is **REQUIRED SUB-SKILL: Use the `taxonomy` skill** when a relevant Feature is missing or unclear. The work axis is **REQUIRED SUB-SKILL: Use the `work` skill**.

> **Web editing:** Capabilities can also be created and edited through the local `tcw serve` web app; check failures are surfaced in the UI.

## Declaring a change (at spec)

When a work item changes what users can do, its spec names each new, changed
and removed capability in `capabilities.yaml`, in the item's folder
(`tcw work path <item>` prints the folder, given the item's full identifier,
its folder's path in the work store, or its tracker key). **No `Missing`
records at planning:** the spec declares and writes no records. The declaration
is the link from the work to the capabilities; nothing points back from a
record to the item.

```yaml
new:
    - shop.capabilities/auth/login # added during implement, with its real status
changed:
    - shop.capabilities/billing/refund
removed:
    - shop.capabilities/billing/legacy-export # deleted with tcw capabilities rm during implement
taxonomy:
    new:
        - shop.taxonomy/login-session
```

Each list holds full identifiers (`<project-id>.capabilities/<path>`, no `#`),
and the entry's project is the ledger that answers for it. `taxonomy:` declares
vocabulary terms and Features the same way, as `<project-id>.taxonomy/<path>`.
For a removal, copy the exact identifier from `tcw capabilities list`: a deleted
capability and a mistyped one look the same to the check. `tcw validate`
reports what is wrong with the file at any point: an entry that is not a full
identifier, one naming a project TCW does not know, and one it could not check
because that project is not on this machine.

## Changing the records (at implement)

**Implement adds, edits or removes the records in the same change as the code**,
so the ledger describes the product the moment the code does:

- **New capability:** `tcw capabilities add <namespace/path> "<Capability name>" --status Supported`, with its description on stdin. `--parent <capability>` records the capability it belongs under and makes the folder inside the parent's: the path is then read inside the parent's folder (`--parent billing/invoices` with `bulk` makes `billing/invoices/bulk`), unless it already starts with the parent's path; read inside the parent's folder it must be one part, so `extra/bulk` is refused (exit 2). `--flat` reads the path as without a parent; under an inherited parent or another project's the path is read as given, and a `not nested:` line says so. **Every `tcw capabilities add` names its status**, because `add` without `--status` writes a `Missing` record, which the records check refuses for a declared `new` path. Use the status the capability really has: `Supported`, or `Partial` with the gap described in its `Gaps` field (`--field Gaps=<text>`), which `tcw validate` requires of a `Partial` one.
- **Changed capability:** edit its description and fields (`tcw capabilities set <path> --field K=V`, `--status <S>`).
- **Removed capability:** `tcw capabilities rm <path>`. `rm` deletes one of the project's own capabilities, an override included (it then says what the path shows), and refuses — deleting nothing — an inherited one, one with capabilities nested under it, and one another capability still references through `Superseded by`, `Blocked by`, `Roles`, `When` or `parent`; the message names what to repoint or remove first. A behavior folded into another capability is removed, not marked `Omitted` (that means "we deliberately don't have this").
- **Renamed or moved capability:** `tcw capabilities rename <path> <name>` changes the last part of its path, and `tcw capabilities move <path> --into <id-path>` (or `--top`) moves its folder; the capabilities nested in it go with it, and every reference to it in the project's own records and documents is rewritten. Each prints one `<old full id> -> <new full id>` line per identifier changed; references in other projects are not rewritten, so pass those lines on. Only the project's own capabilities can be renamed or moved, and never an override (exit 3), which must stay at the path of what it overrides.

**No flipping at completion.** Nothing changes the records later. The move out
of implement checks the declaration against the ledger — every `new` and
`changed` capability present, no `new` one still `Missing`, every `removed` one
gone — and refuses the move until it holds. Review then checks that the records
say what the code does.

**`Missing` means a known gap the team has acknowledged**, not a plan: a
capability users should have and do not, written down so it is not forgotten.

**Changes in another project's ledger.** An entry is checked in the ledger of
the project its full identifier names, against that project's own capability
there, never against an override of it in this project, and never against a
capability that project only inherits. So when the item's project keeps no
ledger of its own (a repository root grouping packages, for example), each
entry names the child project whose ledger holds the capability —
`shared.capabilities/authoring/add-a-claim`; an entry naming the item's own
project is then unchecked, and the message asks for the ledger's project. A
capability in another project is created and changed **in that project**, with
the path inside its store: `tcw -C <folder> capabilities add <path> "<Name>" --status Supported`, or
`set` and `rm` the same way, where `tcw project path <id>` prints the
project's folder. Run from here, those commands are refused with exit 3, and
the message names the folder to run them in. An entry naming a project not on
this machine cannot be checked, and `tcw validate` reports it.

## Contradiction-detection (at the moment of change)

Before recording or altering a capability, check it against the standing ledger: `tcw capabilities search <term>` / `tcw capabilities show <path>` for an existing capability the change would contradict (a new capability that conflicts with a `Supported` one; a status that disagrees with reality). Add `--scope up` to include the capabilities the project inherits. Run `tcw validate` (non-zero ⇒ structural problems to fix first). A capability reported as incomplete because it "overrides nothing" usually overrode one that was moved or removed. Whether two capabilities _semantically_ contradict is judgment — surface candidates to the human; never silently overwrite.

When a capability describes behavior around a registered taxonomy feature, set
`Feature=<feature-ref>` in addition to any useful `Subject=<taxonomy-ref>`.
`tcw validate` checks that `Feature` resolves to a taxonomy entry whose kind is
`Feature`, and **`set` checks it too** — a write carrying a reference that does
not resolve is refused, in the same words, and writes nothing. That covers all
six reference-bearing fields (`Subject`, `Feature`, `Superseded by`,
`Blocked by`, `Roles`, `When`), so **order matters**: register the taxonomy
Feature before the capability naming it, and a `roles/…` capability before the
capability listing it. Only the references a write supplies are checked, so a
capability already holding a bad one is still repairable with
`--status Omitted`.

If no suitable Feature exists, do not invent an unregistered string in the
capability. Use `taxonomy` to add or clarify the Feature first, then link it
from the capability.

A capability's `description.md` body may also cross-reference other objects in
prose by their addresses, `[text](tcw://<project-id>.capabilities/<path>)` (or
`.taxonomy` and `.work` in place of `.capabilities`), in this project or in any
other project TCW can find — additive to the structured `Subject`/`Feature`
pointers, not a replacement. `tcw validate` resolves these links and the
`tcw serve` viewer makes them clickable.

## Inheritance (capabilities from parent projects)

A project inherits the capabilities of every parent whose `inherit` includes
`capabilities`, through every level: a parent's own parents are inherited too,
without being listed. The parent links are configured under `parents:` in
`.tcw/tcw-config.yaml`, which the configure skill's reference on projects
explains; there is no capabilities command for it. An inherited capability
keeps the full identifier of the project it belongs to
(`<parent-id>.capabilities/<path>`).

**Which projects a command reads.** `list` and `search` read only the project's
own capabilities by default (`--scope own`); a plain `list` prints one full
identifier per line. `--scope up` adds the capabilities it inherits from its
parents; `--scope down` adds those its children and their children declare, and
`--scope all` both. `show` of an inherited capability by its path needs
`--scope up`, or its full identifier. `--project <id>` keeps only one covered
project's own capabilities.

**Status across a family.** A capability a child inherits or overrides can have
a different status in each project. Read that mixed status from the parent's
project with `--scope down` (or `all`): `show` prints an `overridden by:` line
and a `status by project:` block, and each `--json` record carries `statuses`
(one entry per project: `project`, `status`, `inherited`, and the `full-id` its
status comes from) and `overridden-by`. A plain listing never shows it, and a
`--json` listing with `--project` carries no `statuses` and no `overridden-by`,
since it holds one project's own capabilities only.

**Capabilities stay inside their own store.** A path is joined onto the store
root, so a symlink planted inside the store would otherwise carry the write out
of it. Every lookup, listing, write target and validation resolves first and
refuses a path landing outside — including the files inside a capability
folder, so one whose `tcw-capability.yaml`, `description.md` or a listed
attachment is a symlink out is not read. Such a capability does not resolve,
does not appear in `list`, and cannot be written to. Inheriting from a parent
project is the supported way to reference another project's capabilities.

**Changing another project's capability.** `rm`, `rename` and `move` of a
capability that belongs to another project, a parent included, are refused
with exit 3, and so is `set` of one the project does not inherit; the message
names that project and the folder to run the command in, as
`tcw -C <folder> capabilities rm <path>` and the like. `set` of an inherited
capability overrides it instead (below), and `reset` drops only the project's
own override.

**Overriding an inherited capability.** An override is the project's own
capability at the same path as the inherited one, holding only the fields it
changes. Nothing in its files points at the original: there is no `overrides:`
key (`tcw validate` reports one as an error). The two are combined field by
field:

- **override metadata** — `tcw capabilities set <path> --status <S>` (or
  `--field K=V`, or `--parent`) on an inherited capability writes the project's
  own capability at that path, holding only the fields given; the inherited
  capability's full identifier is accepted in place of the path. A YAML null
  clears an inherited field; `--field K=` with an empty value writes one. A list field (`Subject`, `prependedDocs`,
  `appendedDocs`, …) is replaced whole, and an override that does not mention
  one keeps its original's;
- **compose the body** — a `description.md` in the override replaces the inherited description; `prependedDocs`/`appendedDocs` (bounded lists in `tcw-capability.yaml`) wrap it (e.g. a mobile app appending "…or take a photo with the camera"), and an override that does not list them keeps the original's. The override body is a _delta_: an empty one adds no text, so **clearing an override's body re-inherits the inherited description** rather than blanking it (that fallback is what makes append-only overrides work). To say "we deliberately don't have this", use `Status: Omitted`, not an empty body;
- **not with `add`** — `add` at a path the project already inherits is refused (exit 3), naming `tcw capabilities set`, since it would write a full copy.

The JSON records carry `overrides` (the full identifier of the capability
overridden, or `null`), and `show` prints an `overrides:` line.

To **drop an override** and re-inherit the original, `tcw capabilities reset <path>` (or the overridden capability's full identifier) — it removes only the project's own capability at that path (never the parent's), and refuses clearly when there is no override (a capability that overrides nothing → delete it with `tcw capabilities rm`; a path the project has nothing of its own at → nothing to drop), when a capability is nested in the override's folder (exit 3, naming each: `rm` the local ones and `reset` the nested overrides first), and while another of the project's own objects names the override by its full identifier (repoint it at the overridden capability's full identifier first). Whole-override only; to revert a single inherited field, `set <path> --field K=<value>` instead. `tcw capabilities rm <path>` also removes an override, and says what the path shows afterwards.

`tcw validate` reports a capability that overrides nothing and is incomplete (it needs a name, a `Status` and a `description.md`, which may be empty), which is how an override whose original was moved or removed is caught; an `overrides` key; and, as a warning, two parents that do not inherit from each other with a capability at one path (the one that comes later in the project's load order, the order in which TCW reads its parents, is used whole, until the project gives that path a complete capability of its own). It checks the references an override sets (`Subject`, `Feature`, `Blocked by`, `Superseded by`, `Roles`, `When` — checked as a local capability's are) and attachment lists.

**When a parent is not on this machine.** `tcw capabilities list` under the default `--scope own`, and `show` of one of the project's own capabilities, still work, with a warning naming the missing parent: each JSON record read that way has `"partial": true` and no `overrides` key, since what it overrides is not known. The commands that need inherited capabilities (`list` and `search` with `--scope up`, `add`, `set` of an inherited capability, `reset`, `drift`) stop with exit code 7, and the message says where TCW looked and how to make the parent known. Report which project is missing and pass on the message; do not retry.

## Product-layer wording from another project

An agent working one project does **not** read another project's ledger to
decide product-layer wording. To ask for it, file an item in the project that
owns the wording. When that project is on this machine, file it there:
`tcw -C tcw://<id>.path/ work new "capability wording: <name>"`, where `<id>`
is that project's ID, or `tcw -C <folder> work new "capability wording: <name>"`
with the folder `tcw project path <id>` prints. When it is not on this machine,
those commands exit 5 if a manifest here places it (the message says where TCW
looked), and exit 1, with a message ending `check the spelling`, if nothing
here knows its ID; either way, ask through that project's own issue tracker
instead.
That project answers through its own work.

Never wait on the answer. If canonical wording is not available when needed,
use the evidence in this repository and mark the entry `TODO: confirm wording`.

## Starting a capabilities ledger

To seed a new capabilities ledger from an existing codebase, use the `setup` skill.

## Quick reference

| Goal                            | Command                                                                                                                                                                               |
| ------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| declare a change (spec)         | `capabilities.yaml` in the folder `tcw work path <item>` prints: `new:`, `changed:`, `removed:`, `taxonomy:`, each entry a full identifier                                            |
| add a capability (implement)    | `tcw capabilities add <ns/path> "<Name>" --status Supported [--parent <capability> [--flat]]`, description on stdin; with `--parent` the path is read inside the parent's folder                                                                            |
| change status or fields         | `tcw capabilities set <path> --status <S>` · `--field K=V` · `--parent <capability>` (local or inherited)                                                                             |
| change an inherited entry       | `tcw capabilities set <path> --status <S>` — writes the project's own capability at that path, holding only the fields given                                                          |
| rename or move a capability     | `tcw capabilities rename <path> <name>` · `tcw capabilities move <path> --into <id-path>` (or `--top`) — the project's own only; prints each changed identifier                       |
| delete a local capability       | `tcw capabilities rm <path>` — an override included; refuses another project's, nested-under, or still-referenced; list it under `removed:` in the item's `capabilities.yaml`         |
| drop an override                | `tcw capabilities reset <path>` (or the overridden capability's full identifier) — re-inherit the original (refuses if none, or while the project's own references name the override) |
| associate a feature             | `tcw capabilities set <path> --field "Feature=<feature-ref>"`                                                                                                                         |
| link taxonomy (multi-valued)    | `tcw capabilities set <path> --field "Subject=term-a,term-b"`                                                                                                                         |
| inherit another project         | name it under `parents:` with an `inherit` that includes `capabilities` (the configure skill's projects reference); no capabilities command                                           |
| read without a parent present   | `tcw capabilities list` · `show <own path>` — records marked `"partial": true`; commands needing inherited capabilities exit 7                                                        |
| choose which projects to read   | `tcw capabilities list` reads the project's own (`--scope own`, the default); `--scope up` adds inherited ones, `--scope down` descendants', `--scope all` both                       |
| status in each project          | `tcw capabilities show <path> --scope down` · `tcw capabilities list --scope down --json` (`statuses`, `overridden-by`); never from a plain listing                                   |
| check the ledger                | `tcw validate` (the whole project: YAML, `tcw://` links, every axis's checks)                                                                                                         |
| find drift                      | `tcw capabilities drift` — inherited capabilities never ruled on, and what completed items declared that the records do not show                                                      |
| find / read                     | `tcw capabilities search <term>` · `tcw capabilities show <path>`                                                                                                                     |
| locate the store                | `tcw capabilities path` — prints only the absolute, resolved store folder                                                                                                             |
| ask another project for wording | `tcw -C tcw://<id>.path/ work new "capability wording: <name>"` when it is on this machine; otherwise its own issue tracker                                                           |
