# Spec — Fold the taxonomy and capabilities store configs into the root tcw-config.yaml

## Capability changes

**Changed — 2.** No new capabilities, none removed.

- `taxonomy/federate-shared-vocabulary` — its description states that
  "`docs/taxonomy/config.yaml` stores `extends` as a list of project IDs". After
  this change the list lives at `taxonomy.extends` in `tcw-config.yaml`.
- `capabilities/federate` — its description states that "`.config.yaml` stores
  `extends` as a list of project IDs". Same correction, for
  `capabilities.extends`.

Both keep `Feature: connected-project-registry`; no taxonomy entry changes. The
two `*/configure-the-*-store-location` capabilities are untouched — `path` and
`repository` behave exactly as before.

## Problem

A TCW project can hold three configuration files. The node-root
`tcw-config.yaml` is one; each tree store may hold a second, private to itself:

- taxonomy — `FsTaxonomyStore.CONFIG_NAME = "config.yaml"`
  (`tcw/store/fs.py:1864`)
- capabilities — `FsCapabilitiesStore.CONFIG_NAME = ".config.yaml"`
  (`tcw/store/fs.py:2357`), a dotfile, so an ordinary `find -name config.yaml`
  does not even show it

Between them those files hold **exactly one key**: `extends`, a list of
registered project IDs this component inherits from. Nothing else is ever
written to them. The whole surface is five places:

| What | Where |
| --- | --- |
| Loaded into `self.config` | `tcw/store/fs.py:1575` |
| Parsed and validated | `_extends_ids`, `tcw/store/fs.py:1235` |
| Resolved into stores | `_extended_component_stores`, `tcw/store/fs.py:1306` |
| Written | `extends_add` / `extends_remove`, `tcw/store/fs.py:2076-2110` (taxonomy) and `2809-2838` (capabilities) |
| Parsed again, for `check()` | `tcw/store/fs.py:2169-2173` and `2863-2867` |

Three things are wrong with this.

**It contradicts the code's own account of where configuration lives.** The
comment on `FsTreeStore.__init__` already says `node_root` is "the *node*: whose
config this is, and what federation resolves `extends` against"
(`tcw/store/fs.py:1569-1570`) — and then the next lines load that config from
the *store* root instead (`tcw/store/fs.py:1575`). `tcw-config.yaml` already
carries a `taxonomy:` and a `capabilities:` section; the store-resolution ladder
reads them for `path` and `repository` (`tcw/store/fs.py:3274-3280`), and
`connected-projects` — the registry `extends` is validated against — lives there
too. `extends` is the one federation key that does not.

**It is hard to find.** The file is optional and usually absent — "its
`CONFIG_NAME` file is optional and commonly absent" (`tcw/store/fs.py:3187-3188`)
— so a project that never federated has no evidence the second config file
exists at all. One of the two is a dotfile.

**It puts inheritance in the wrong place when a store is shared.** A tree store
can live outside its project (`taxonomy.path`) or in another repository
(`taxonomy.repository`). Today `extends` travels with the store folder, so every
project reading that folder is forced into the same ancestors. The requester has
decided inheritance is a property of the *project*.

### Sweep

Repo-wide, for anything sibling to this. Four findings, all small:

1. `tcw taxonomy extends add` prints a hard-coded `docs/taxonomy/config.yaml`
   (`tcw/taxonomy/cli.py:157`). **That is already wrong today** — a project with
   `taxonomy.path` set is told to look in a folder its taxonomy is not in. This
   change removes the line, which fixes it.
2. `_TAX_RESERVED` (`tcw/store/fs.py:1841`) is dead: a repo-wide grep finds the
   definition and no reader.
3. The comment above `OWNED_YAML_NAMES` says "taxonomy and work write
   `config.yaml`" (`tcw/store/fs.py:1139`). `FsWorkStore` declares no
   `CONFIG_NAME` and sets `self.config = {}` outright
   (`tcw/store/fs.py:3673`) — the work store has never had one.
4. `docs/work/dod.yaml` (`tcw/store/fs.py:5235`) is the only remaining
   configuration TCW keeps outside `tcw-config.yaml`. Deliberately left alone —
   see Non-goals.

Outside `tcw/`, every reference to the two filenames is a test fixture: about 25
of them across roughly ten files under `tests/`, plus
`tests/fixtures/lifecycle_baseline/capture.py`. The web app carries none —
`tcw/serve/runtime.py` never mentions `extends`, and reaches inherited entries
through the store like every other reader. `evals/seed_fixture.py` touches only
`tcw-config.yaml`.

## Goals

1. One configuration file per TCW project. `extends` moves to
   `taxonomy.extends` and `capabilities.extends` in `tcw-config.yaml`; the two
   per-store config files stop existing as far as TCW is concerned.
2. Inheritance becomes a property of the project. Two projects sharing one store
   folder may inherit differently, and a store folder carries no opinion about
   what reads it.
3. Nothing else about federation changes: same value shape, same validation,
   same transitivity, same cycle detection, same refusal of legacy maps.
4. A project that upgrades with an old file on disk can find out what to do, from
   a migration guide.

## Non-goals

- **`docs/work/dod.yaml`.** It is the Definition of Done, read from the work
  store root (`tcw/store/fs.py:5235`), and the requester named only the taxonomy
  and capabilities configs. It is also a different kind of thing: a list of
  completion criteria that belongs to a *board*, so a shared board sharing one
  Definition of Done is arguably correct. Anyone wanting literally one file per
  project should file it separately.
- **Reading old files.** No compatibility shim, no deprecation warning, no
  automatic migration. Decided by the requester and recorded in
  `initial-request.md`; do not reopen it.
- **Deleting old files.** TCW does not remove a file it no longer reads.
- **What inheritance does.** Resolution, transitivity, cycle detection, override
  materialization and `<project-id>/` addressing are all unchanged.
- **Remote or URL `extends` locators.** A separate, discarded idea.
- **`path` and `repository`.** Untouched.

## Design

Six rules. The numbering is what the Coverage table crosses.

**Rule 1 — the key and its home.** `extends` is read from and written to the
component's existing section of the node's `tcw-config.yaml`:

```yaml
id: my-project
taxonomy:
    path: ../shared-docs/taxonomy # unchanged
    extends: [core, platform]
capabilities:
    extends: [core]
```

The value shape is unchanged — a list of registered project IDs — and
`_extends_ids` (`tcw/store/fs.py:1235`) validates it exactly as today: a mapping
is refused as a legacy map, a non-list or non-string member is refused, and
duplicates are refused. Absent section, or absent key, means no inheritance.

**Rule 2 — reading.** `FsTreeStore` stops loading `self.config` from
`root / CONFIG_NAME` (`tcw/store/fs.py:1575`). A tree store's `self.config`
becomes the component's section of `node_root / SENTINEL`. `CONFIG_NAME` is
removed from both tree stores. Whether the section is threaded down from
`resolve_store`, which already loads that file (`tcw/store/fs.py:3274-3280`), or
re-read in the constructor, is the plan's choice; both must tolerate an absent
config (`load_yaml` already returns `{}`) and must not introduce a failure mode
`resolve_store` does not already have for a malformed one.

**Rule 3 — writing.** `extends_add` and `extends_remove` read-modify-write the
component's section of the node config, preserving every other key, and stage
the file **in the node's repository**. This is not new machinery:
`_write_staged` already takes `stage_root` "for the one write that is not a
store file: the node's own `tcw-config.yaml`" (`tcw/store/fs.py:1735-1738`), and
`FsWorkStore._write_tags` (`tcw/store/fs.py:5657-5686`) is the working example,
including its fallback — a node outside git gets a plain atomic write rather
than a failure. The accessors that example uses, `_config_path` and `_config`
(`tcw/store/fs.py:5246-5252`), currently sit on `FsWorkStore` and need to be
reachable from the tree stores.

The store root and the node root are different repositories in the orchestrator
layout, which is why this rule is stated separately: staging a node-config write
against the store's repository is what made `tcw work tags add` unusable there
(`tcw/store/fs.py:5660-5666`), and this change would reproduce that bug exactly
if it staged against the store.

**Rule 4 — what the messages say.** Every message that names a per-store config
file names the key and `tcw-config.yaml` instead. That covers `_extends_ids`'s
three refusals, which take a `config_path` argument for the purpose, and the
success line of `tcw taxonomy extends add` (`tcw/taxonomy/cli.py:157`), whose
hard-coded path is deleted rather than re-pointed — sweep finding 1.

**Rule 5 — the old files become nothing.** TCW does not read, write, create or
delete them.

- Both names leave `OWNED_YAML_NAMES` (`tcw/store/fs.py:1154`), and the stale
  half of its comment goes with them — sweep finding 3.
- Each tree store's `check()` stops parsing its config file
  (`tcw/store/fs.py:2169-2173`, `2863-2867`).
- `_TAX_RESERVED` is deleted — sweep finding 2.
- **`_node_reserved` (`tcw/store/fs.py:1785-1790`) keeps both names**, as
  literals rather than via `CONFIG_NAME`. It lists the filenames in a node
  folder that are not attachments; dropping `config.yaml` from it would make a
  `config.yaml` sitting inside a *term* folder newly appear as that term's
  attachment. Nothing about this item is meant to change the attachment surface,
  and keeping two strings is a smaller change than reasoning about who that
  would affect. (`.config.yaml` is excluded anyway as a dotfile, and is kept only
  so the two read alike.)

A leftover file at a store root is therefore inert: the store root is not a
node, so nothing reads it, and a project that upgrades without acting simply has
no inheritance.

**Rule 6 — migration is a document.** A `docs/migration-guide-<from>-to-<to>.md`
in the shape of the existing six, naming both old filenames, both new keys, and
the shared-store consequence from Goal 2. Plus the usual `upcoming.md` release
note and changelog entries. No code path reads an old file and nothing warns at
runtime — that is the whole of the migration, by the requester's decision.

## Abstraction litmus test

> Could a non-filesystem store implement this operation, even if less elegantly?

**No operation is added or removed.** `extends_add` and `extends_remove` already
exist on the abstract `TaxonomyStore` and `CapabilitiesStore`
(`tcw/store/base.py:553-557`, `804-808`) and keep their signatures. What changes
is which file the filesystem adapter puts the answer in — an adapter-private
detail, correctly located below the interface.

The change moves the litmus in the right direction. A store is a place entries
live; "a config file inside the store folder" is a filesystem affordance a Jira
or graph-DB adapter has no analog for, whereas node-level configuration is
something every adapter already needs, because that is where `path`,
`repository`, `connected-projects` and the tracker block already live. Reading a
component's settings from the node rather than from inside the store is the
abstract spine asserting itself over a filesystem trick.

**Harness compatibility.** Nothing here is carried by a skill, a hook or
injected context. The behavior is entirely in the `tcw` CLI and the store
adapter, which behave identically under Claude and Codex. The only agent-facing
change is documentation — `skills/configure/references/projects.md` — which both
harnesses read the same way.

## Acceptance criteria

1. With `taxonomy: {extends: [base]}` in `tcw-config.yaml` and no
   `docs/taxonomy/config.yaml` anywhere, `tcw taxonomy list` shows `base/`
   terms under that project ID.
2. With `capabilities: {extends: [base]}` and no `docs/capabilities/.config.yaml`,
   `tcw capabilities list` shows `base/` capabilities.
3. `tcw taxonomy extends add base` writes `taxonomy.extends: [base]` into
   `tcw-config.yaml`, creates no file under the taxonomy store, and leaves every
   other key in that config — `id`, `work.tags`, `taxonomy.path` — byte-identical
   in value. `tcw taxonomy extends rm base` removes the key. The same holds for
   `tcw capabilities extends base` and `--rm` against `capabilities.extends`.
4. With `taxonomy.path` pointing into a **second git repository**,
   `tcw taxonomy extends add base` exits 0, and `git status` in the node's
   repository shows `tcw-config.yaml` staged while `git status` in the store's
   repository shows nothing.
5. In a node that is not a git repository at all, `tcw taxonomy extends add base`
   exits 0 and the key is on disk.
6. A pre-existing `docs/taxonomy/config.yaml` containing `extends:\n  - base`
   has no effect whatever: `tcw taxonomy list` shows no inherited terms,
   `tcw taxonomy check` and `tcw validate` report nothing about the file, and the
   file is still on disk unmodified afterwards. Same for
   `docs/capabilities/.config.yaml`.
7. `taxonomy.extends` holding a mapping (the legacy alias→path form) is refused
   with the `legacy extends map is unsupported` message, and the message names
   `tcw-config.yaml`, not a store path. A non-list, a non-string member, and a
   duplicate ID are each refused as they are today.
8. No output of any `tcw` command mentions `docs/taxonomy/config.yaml` or
   `.config.yaml`. In particular `tcw taxonomy extends add` names
   `tcw-config.yaml`, and does so correctly when `taxonomy.path` is set.
9. Transitivity survives: with A extending B and B extending C, each declaring
   `taxonomy.extends` in its own `tcw-config.yaml`, `tcw taxonomy list` in A
   resolves both `B/` and `C/` terms. A cycle is still reported by
   `tcw taxonomy check`.
10. Two projects whose `taxonomy.path` points at the *same* folder, declaring
    different `taxonomy.extends`, each resolve their own ancestors — the shared
    folder imposes nothing.
11. `grep -rn 'config\.yaml' tcw/ --include=*.py | grep -v 'tcw-config'` returns
    nothing except the two literals in `_node_reserved`, and `_TAX_RESERVED` is
    gone.
12. A `config.yaml` placed inside a term folder is still not listed among that
    term's attachments.
13. A migration guide exists under `docs/`, named like its six siblings, naming
    both old filenames, both new keys, and the shared-store consequence.
    `docs/release-notes/upcoming.md` and `docs/changelogs/upcoming.md` both
    carry an entry.
14. `skills/configure/references/projects.md` no longer says the two lists do
    not live in `tcw-config.yaml`, and both federation capability descriptions
    name the new keys.
15. `pytest` passes, and `tcw validate` on this repository exits 0.

### Coverage

Each criterion against the six design rules. `n/a` carries the line that makes
it so.

| # | R1 key/home | R2 reading | R3 writing | R4 messages | R5 old files inert | R6 migration doc |
| - | ----------- | ---------- | ---------- | ----------- | ------------------ | ---------------- |
| 1 | ✓ | ✓ | n/a — read-only path; writes covered by 3 | n/a — `_list` prints only term rows (`tcw/taxonomy/cli.py:44-62`) | ✓ absence of the old file is the premise | n/a — doc, not behavior |
| 2 | ✓ | ✓ | n/a — as 1 | n/a — as 1 | ✓ | n/a |
| 3 | ✓ | n/a — asserts the write, then re-reads via 1/2 | ✓ | n/a — covered by 8 | ✓ "creates no file under the store" | n/a |
| 4 | n/a — same key, different repo layout | n/a — write-path criterion | ✓ the `stage_root` half | n/a | n/a — no old file involved | n/a |
| 5 | n/a — as 4 | n/a | ✓ the outside-git fallback | n/a | n/a | n/a |
| 6 | n/a — asserts the key's *absence* | ✓ nothing loads the old path | ✓ the file is unmodified after | n/a — asserts silence | ✓ | n/a — the doc is what tells the user; 13 covers it |
| 7 | ✓ validation unchanged | ✓ refusal is raised on load | n/a — refusal precedes any write | ✓ the path in the message | n/a | n/a |
| 8 | n/a | n/a | n/a | ✓ | n/a | n/a |
| 9 | ✓ per-project declaration | ✓ each node read separately | n/a — fixtures declare the key directly | n/a | n/a | n/a |
| 10 | ✓ this is Goal 2 stated as a check | ✓ | n/a | n/a | ✓ shared folder holds no config | n/a |
| 11 | n/a | n/a | n/a | n/a | ✓ and sweep finding 2 | n/a |
| 12 | n/a | n/a | n/a | n/a | ✓ the `_node_reserved` half of R5 | n/a |
| 13 | n/a | n/a | n/a | n/a | n/a | ✓ |
| 14 | ✓ names the keys | n/a | n/a | n/a | n/a | ✓ same documentation pass |
| 15 | ✓ | ✓ | ✓ | ✓ | ✓ | n/a — `tcw validate` does not read `docs/` prose |

Two rules are load-bearing and easy to leave untested, which is why they each
have a criterion of their own rather than riding on a general one: R3's
`stage_root` (criterion 4) reproduces a bug that has already shipped once
(`tcw/store/fs.py:5660-5666`), and R5's `_node_reserved` (criterion 12) is a
behavior change that happens by *omission* if nobody writes it down.

## Risks

- **The external-store write is the likely defect.** Staging `tcw-config.yaml`
  against the store's repository fails only when the two are different
  repositories, which no default-layout test exercises. `tcw work tags add`
  shipped exactly this bug. Criterion 4 exists for it and needs a two-repository
  fixture, not a same-repo one.
- **Silent loss of inheritance for anyone already federating.** By decision, an
  old file is ignored with no message. A project that upgrades and does nothing
  loses its inherited terms, and the only warning is the migration guide. The
  requester was asked twice and confirmed. The blast is bounded by how rare
  `extends` is — the file is "optional and commonly absent"
  (`tcw/store/fs.py:3187-3188`) — but it is real.
- **Test churn hides a regression.** About 25 fixture sites move from writing a
  file to writing a config key. A fixture rewritten slightly wrong is a test that
  passes while testing nothing, and
  `tests/test_capabilities_federation.py:443-451` deliberately writes
  `.config.yaml` *without* going through `extends_add`, so it is testing the read
  path specifically — that intent has to survive the rewrite.
- **`self.config` changes meaning for tree stores.** It stops being "the store's
  file" and becomes "this component's slice of the node config". Any reader
  assuming the former is now wrong; the grep in criterion 11 is the check.

## Notes

- The requester supplied no reference material; everything cited here was found
  in the repository during the `request` and `spec` stages, and every
  `file:line` was re-read at the time of writing.
- Sweep finding 4 (`docs/work/dod.yaml`) is the one place this item knowingly
  leaves the "one config per project" goal incomplete. It is named in Non-goals
  rather than silently dropped.
- Whether the node config section is threaded down from `resolve_store` or
  re-read in the tree store's constructor is left to the plan. `resolve_store`
  already loads the file and already extracts the same section for `path` and
  `repository` (`tcw/store/fs.py:3274-3280`), so threading it avoids a second
  read — but the constructor is also reachable directly from tests, which is the
  case that argues the other way.
