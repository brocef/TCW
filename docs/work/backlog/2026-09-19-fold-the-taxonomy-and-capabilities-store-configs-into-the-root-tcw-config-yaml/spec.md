# Spec — Fold the taxonomy and capabilities store configs into the root tcw-config.yaml

> Second draft. An adversarial review of the first found three claims about
> current behavior that were wrong; each is corrected here and marked
> **[corrected]** where it sat. The review's findings were re-verified against
> the code before being accepted.

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
written to them — the only mutations of a tree store's `self.config` anywhere in
`tcw/` are `tcw/store/fs.py:2094`, `2106-2108`, `2822` and `2834-2836`, and all
four are `extends`.

The surface the change has to move:

| What | Where |
| --- | --- |
| Loaded into `self.config` | `tcw/store/fs.py:1575` |
| Parsed and validated | `_extends_ids`, `tcw/store/fs.py:1235-1247` |
| Resolved into stores | `_extended_component_stores`, `tcw/store/fs.py:1306-1327` |
| Path passed for error messages, at construction | `tcw/store/fs.py:1878` (taxonomy), `2371` (capabilities) |
| Written | `extends_add` / `extends_remove`, `tcw/store/fs.py:2076-2110` (taxonomy) and `2806-2839` (capabilities) |
| Parsed again, for `check()` | `tcw/store/fs.py:2169-2173` and `2863-2867` |
| Constructed **without** `resolve_store` | `tcw/validate.py:172-174`, a direct `_open_at` |

That last row matters for Design rule 2 and was missing from the first draft.
**[corrected]**

Three things are wrong with the current arrangement.

**It contradicts the code's own account of where configuration lives.** The
comment on `FsTreeStore.__init__` already says `node_root` is "the *node*: whose
config this is, and what federation resolves `extends` against"
(`tcw/store/fs.py:1569-1570`) — and the next lines load that config from the
*store* root instead (`tcw/store/fs.py:1575`). `tcw-config.yaml` already carries
a `taxonomy:` and a `capabilities:` section; the store-resolution ladder reads
`path` from them at `tcw/store/fs.py:3274-3281` and `repository` at
`3284-3285`, and `connected-projects` — the registry `extends` is validated
against — lives there too. `extends` is the one federation key that does not.

**It is hard to find.** The file is optional and usually absent — "its
`CONFIG_NAME` file is optional and commonly absent" (`tcw/store/fs.py:3187-3188`)
— so a project that never federated has no evidence a second config file exists
at all. One of the two is a dotfile.

**It puts inheritance in the wrong place when a store is shared.** A tree store
can live outside its project (`taxonomy.path`) or in another repository
(`taxonomy.repository`). Today `extends` travels with the store folder, so every
project reading that folder is forced into the same ancestors. The requester has
decided inheritance is a property of the *project*.

### Sweep

Repo-wide, for anything sibling to this. Five findings, all small:

1. `tcw taxonomy extends add` prints a hard-coded `docs/taxonomy/config.yaml`
   (`tcw/taxonomy/cli.py:157`). **That is already wrong today** — a project with
   `taxonomy.path` set is told to look in a folder its taxonomy is not in. This
   change removes the line, which fixes it.
2. `_TAX_RESERVED` (`tcw/store/fs.py:1841`) is dead: a repo-wide grep finds the
   definition and no reader.
3. The comment above `OWNED_YAML_NAMES` says "taxonomy and work write
   `config.yaml`" (`tcw/store/fs.py:1139`). `FsWorkStore` declares no
   `CONFIG_NAME` and sets `self.config = {}` outright (`tcw/store/fs.py:3673`) —
   the work store has never had one.
4. `FsWorkStore._write_tags`'s docstring claims "A node outside git stages
   nothing rather than failing" (`tcw/store/fs.py:5670-5671`). Its own
   `self._require_repository()` two lines later
   (`tcw/store/fs.py:5673`) makes that false for the default layout, and
   `tests/test_non_git_writes.py:166-167` pins the refusal. **This docstring
   misled the first draft of this spec into asserting a fallback that does not
   exist**, so it is fixed here rather than filed — it will mislead the next
   reader too.
5. `docs/work/dod.yaml` (`tcw/store/fs.py:5235`) is the only remaining
   configuration TCW keeps outside `tcw-config.yaml`. Deliberately left alone —
   see Non-goals.

Outside `tcw/`, every reference to the two filenames is a test fixture: **19
write sites across six files**, plus one docstring
(`tests/test_capabilities_federation.py:443`) — `test_multiproject.py`,
`test_store_provisioning.py`, `test_environment_hardness.py`,
`test_capabilities_federation.py`, `test_taxonomy.py`, `test_serve.py`. A plain
grep for `config.yaml` over `tests/` overcounts: `test_lifecycle_baseline.py:49`,
`test_lifecycle_validation.py:324-328` and
`tests/fixtures/lifecycle_baseline/capture.py:93` all name a *lifecycle corpus*
file that happens to be called `<case>.config.yaml`, and
`test_store_editor.py:1595` is an `_atomic_write_all` test using an arbitrary
temp filename. None of the four is a store config. The web app carries none —
`tcw/serve/runtime.py` never mentions `extends`, and reaches inherited entries
through the store like every other reader. `evals/seed_fixture.py` touches only
`tcw-config.yaml`. `tcw init` scaffolds no per-store config
(`tcw/store/fs.py:921-1089`), and `tcw provision` goes through
`_is_store_layout`, which explicitly does not look for one
(`tcw/store/fs.py:3186-3189`).

## Goals

1. One configuration file per TCW project. `extends` moves to
   `taxonomy.extends` and `capabilities.extends` in `tcw-config.yaml`; the two
   per-store config files stop existing as far as TCW is concerned.
2. Inheritance becomes a property of the project. Two projects sharing one store
   folder may inherit differently, and a store folder carries no opinion about
   what reads it.
3. Nothing else about federation changes: same value shape, same validation,
   same transitivity, same cycle detection, same refusal of legacy maps — and
   the same refusal to write outside a git repository.
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
- **Relaxing the "writes need a repository" contract.** `extends_add` and
  `extends_remove` keep refusing outside git, exactly as today. **[corrected]** —
  the first draft asked for the opposite; see Design rule 3.
- **What inheritance does.** Resolution, transitivity, cycle detection, override
  materialization and `<project-id>/` addressing are all unchanged.
- **Remote or URL `extends` locators.** A separate, discarded idea.
- **`path` and `repository`.** Untouched.
- **Historical documents.** `docs/migration-guide-0.12.X-to-0.13.0.md`,
  `docs/plan/phase-2-taxonomy.md`, `docs/plan/phase-3-capabilities.md` and every
  shipped changelog and release note name the old files as a record of what was
  true then. They are not corrected.

## Design

Six rules. The numbering is what the Coverage table crosses.

**Rule 1 — the key and its home.** `extends` is read from and written to the
component's existing section of the node's `tcw-config.yaml`:

```yaml
id: my-project
taxonomy:
    path: ../shared-docs/taxonomy
    extends:
        - core
        - platform
capabilities:
    extends:
        - core
```

The value shape is unchanged — a list of registered project IDs — and
`_extends_ids` (`tcw/store/fs.py:1235-1247`) validates it exactly as today: a
mapping is refused as a legacy map, a non-list or non-string member is refused,
an invalid project ID is refused, and duplicates are refused. Absent section, or
absent key, means no inheritance.

**A write re-renders the file.** `extends_add` goes through
`yaml.safe_dump(config, sort_keys=False, allow_unicode=True)`, so keys and
values and their order survive but comments and formatting do not — the same
trade `work.tags` already makes ("`dump_yaml` rewrites the sentinel wholesale,
dropping its stub comments — accepted per plan", `tcw/store/fs.py:5658-5660`).
That was already true of `tcw work tags add`; this change makes two more verbs
do it, so it belongs in the migration guide as a user-visible consequence, not
only in a test's wording. **[corrected]**

**Rule 2 — reading.** `FsTreeStore` stops loading `self.config` from
`root / CONFIG_NAME` (`tcw/store/fs.py:1575`). A tree store's `self.config`
becomes the component's section of `node_root / SENTINEL`, read **in the
constructor**, not threaded down from `resolve_store`. **[corrected]** — the
first draft left this to the plan; it is not a free choice, for three reasons
each verified in the code:

1. `tcw/validate.py:172-174` constructs a store by calling `_open_at` directly,
   bypassing `resolve_store` entirely. A threaded section would arrive empty
   there and that store would silently resolve no inheritance.
2. `resolve_store` normalizes a section that is present but not a mapping to
   `{}` (`tcw/store/fs.py:3276-3278`). The constructor read must do the same, or
   `taxonomy: docs/tax` — a string where a mapping belongs — becomes an
   `AttributeError` instead of "no configuration", which is a failure mode
   `resolve_store` does not have.
3. `resolve_store` reads through `load_config` (`tcw/store/fs.py:3274`), which
   raises a worded `ValueError` naming the file; `load_yaml` does not. The
   constructor read must use `load_config` so both routes say the same thing
   about the same broken file.

`CONFIG_NAME` is removed from both tree stores as a *config* mechanism. The
constructor's `node_root` default of `root.parent.parent`
(`tcw/store/fs.py:1573`) is wrong for any external store, so this is only safe
because every real caller passes `node_root` — `resolve_store` and
`_open_at` both do.

**Rule 3 — writing.** `extends_add` and `extends_remove` read-modify-write the
component's section of the node config, preserving every other key, and stage
the file **in the node's repository** rather than the store's. `_write_staged`
already takes `stage_root` "for the one write that is not a store file: the
node's own `tcw-config.yaml`" (`tcw/store/fs.py:1735-1738`), and
`FsWorkStore._write_tags` (`tcw/store/fs.py:5657-5686`) is the working example.

The store root and the node root are different repositories in the orchestrator
layout, which is why this is a rule of its own: staging a node-config write
against the store's repository is what made `tcw work tags add` unusable there
(`tcw/store/fs.py:5660-5666`), and this change reproduces that bug exactly if it
stages against the store.

**Writes still require a repository, and that does not change. [corrected]**
The first draft claimed `_write_tags` falls back to a plain write in a node
outside git. It does not: it opens with `self._require_repository()`
(`tcw/store/fs.py:5673`), which resolves through `store_git_root`, and
`tests/test_non_git_writes.py:166-167` pins `register_tags` and
`unregister_tags` as refusals. That file's whole purpose is the contract "reads
work anywhere and **writes** need a repository"
(`tests/test_non_git_writes.py:1-12`), and it already lists
`["taxonomy", "extends", "add", …]`, `["taxonomy", "extends", "rm", …]`,
`["capabilities", "extends", …]` and `["capabilities", "extends", …, "--rm"]`
among the commands that must exit 1 changing nothing
(`tests/test_non_git_writes.py:424-431`). `extends_add` already begins with
`self._require_repository()` (`tcw/store/fs.py:2077`, `2807`) and keeps it. The
`git_root(...) is None` branch inside `_write_tags` is reachable only when the
*store* is in a repository and the *node* is not, and it is carried across
unchanged rather than relied upon.

The accessors `_config_path` and `_config` (`tcw/store/fs.py:5246-5254`)
currently sit on `FsWorkStore`. `FsWorkStore` already inherits `FsTreeStore`
(`tcw/store/fs.py:3644`) and overrides only `__init__`, so making them reachable
from the tree stores is a **hoist of those nine lines**, not a new mixin. One
caveat: `FsTreeStore.__init__` stores `node_root` unresolved
(`tcw/store/fs.py:1573`) where `FsWorkStore` resolves it
(`tcw/store/fs.py:3671`), so the hoisted `_config_path` must not assume a
resolved path.

**Rule 4 — what the messages say.** Every message that names a per-store config
file names the key instead, spelled `tcw-config.yaml: taxonomy.extends`, not
just the filename — a user with both `taxonomy.extends` and
`capabilities.extends` in one file needs to know which one is wrong. That covers:

- the three refusals in `_extends_ids` that interpolate the `config_path` they
  are handed (`tcw/store/fs.py:1238-1246`);
- the fourth refusal, `validate_project_id(v)` (`tcw/store/fs.py:1244`), which
  raises naming no path at all — it is wrapped so it names the key like the
  others. **[corrected]**, the first draft said there were three;
- the success line of `tcw taxonomy extends add` (`tcw/taxonomy/cli.py:157`),
  whose hard-coded path is deleted rather than re-pointed — sweep finding 1.

**Rule 5 — the old files become nothing.** TCW does not read, write, create or
delete them.

- Both names leave `OWNED_YAML_NAMES` (`tcw/store/fs.py:1154`), and the stale
  half of its comment goes with them — sweep finding 3.
- Each tree store's `check()` stops parsing its config file
  (`tcw/store/fs.py:2169-2173`, `2863-2867`).
- `_TAX_RESERVED` is deleted — sweep finding 2.
- **`_node_reserved` (`tcw/store/fs.py:1785-1790`) stays per-store.
  [corrected]** It lists the filenames in a node folder that are not
  attachments, and it is per-store today: taxonomy reserves `config.yaml`,
  capabilities reserves `.config.yaml`. The first draft proposed giving both
  stores both literals "so the attachment surface does not change", which does
  the opposite — a `config.yaml` inside a *capability* folder is an attachment
  today (it is neither reserved there nor a dotfile) and would silently stop
  being one. Each store therefore keeps reserving its own former filename,
  as a literal rather than through `CONFIG_NAME`, with a comment saying it is
  kept to hold the attachment surface still now that nothing writes the file.

**A malformed leftover is still reported, and that is correct.**
`tcw validate`'s YAML pass walks every `*.yaml` under the store roots and
reports a syntax error or duplicate key from any of them
(`tcw/validate.py:296-301`), independently of `OWNED_YAML_NAMES`; only the
*mapping-shape* check at `tcw/validate.py:304` is gated on that set. `rglob`
matches dotfiles, so `.config.yaml` is included. So a **well-formed** leftover
is entirely silent, and a **corrupt** one is still named — which is right: the
file being unread is no reason to stop reporting that it is unparseable.
**[corrected]**

A leftover file at a store root is otherwise inert: the store root is not a
node, so nothing reads it, and a project that upgrades without acting simply has
no inheritance.

**Rule 6 — migration is a document.** A `docs/migration-guide-2.X-to-3.0.0.md`
in the shape of the existing six, naming both old filenames, both new keys, the
re-rendering consequence from Rule 1, and the shared-store consequence below.
Plus the usual `upcoming.md` release note and changelog entries. No code path
reads an old file and nothing warns at runtime — that is the whole of the
migration, by the requester's decision.

### Two consequences of per-project inheritance

The decision is settled; these are things it causes that the first draft did not
state. **[corrected]**

**A shared folder can now be composed with itself.** Today, if projects A and B
point `taxonomy.path` at one folder and A declares `extends: [B]`, that
declaration is in the shared file, so it is B's declaration too — building B's
store reaches the self-extend guard (`tcw/store/fs.py:1339`) and the whole read
errors out. Afterwards A and B have separate declarations, the error is gone,
and A resolves the shared folder's terms **twice**: once as its own local terms
and once under `B/`. That state is newly reachable. It is not a bug — each
namespace is honest about where it came from, and `tcw taxonomy check` still
reports a genuine cycle — but it is new, and the migration guide should say so.

**Inside a linked git worktree, `extends` can differ by branch.** `extends` now
comes from the worktree's own checked-out `tcw-config.yaml` rather than from
wherever the store folder sits. This only bites when `<component>.path` is a
relative path that *escapes* the worktree, because `anchor_configured_path`
re-anchors only on escape (`tcw/store/fs.py:1517-1520`); a path that stays
inside the worktree already belonged to the branch. Narrow, but
`tcw work start --worktree` is a first-class workflow here, so it earns a line.

## Abstraction litmus test

> Could a non-filesystem store implement this operation, even if less elegantly?

**No operation is added or removed.** `extends_add` and `extends_remove` already
exist on the abstract `TaxonomyStore` and `CapabilitiesStore`
(`tcw/store/base.py:552-557`, `803-808`) and keep their signatures. What changes
is which file the filesystem adapter puts the answer in — an adapter-private
detail, correctly located below the interface.

The change moves the litmus in the right direction. A store is a place entries
live; "a config file inside the store folder" is a filesystem affordance a Jira
or graph-DB adapter has no analog for, whereas node-level configuration is
something every adapter already needs, because that is where `path`,
`repository`, `connected-projects` and the tracker block already live. Reading a
component's settings from the node rather than from inside the store is the
abstract spine asserting itself over a filesystem trick.

**The cost, stated plainly.** It makes an abstract store operation mutate
something the store does not own: `TaxonomyStore.extends_add`
(`tcw/store/base.py:553`) now writes a file outside the store, in possibly a
different repository. `FsWorkStore.register_tags` already does exactly this, so
there is precedent rather than a new pattern — but the precedent is what a
reviewer of the next such change will cite, so it should be named here rather
than discovered later. The reason it is acceptable: the operation's *meaning* is
"this project inherits from that one", which is a statement about the project,
and the adapter is free to store a project-level fact wherever that adapter
keeps project-level facts. An adapter with no node config would keep it
somewhere else entirely, and the interface would not notice.

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
   other key in that config — `id`, `work.tags`, `taxonomy.path` — equal in
   parsed value. (Not byte-identical: the file is re-rendered and comments are
   lost, per Rule 1.) `tcw taxonomy extends rm base` removes the key. The same
   holds for `tcw capabilities extends base` and `--rm` against
   `capabilities.extends`.
4. With `taxonomy.path` pointing into a **second git repository**,
   `tcw taxonomy extends add base` exits 0, and `git status` in the node's
   repository shows `tcw-config.yaml` staged while `git status --porcelain` in
   the store's repository is empty.
5. In a node that is not a git repository, `tcw taxonomy extends add base`,
   `tcw taxonomy extends rm base`, `tcw capabilities extends base` and
   `tcw capabilities extends base --rm` each **exit 1**, print a single-line
   refusal, and leave the tree byte-for-byte unchanged — i.e.
   `tests/test_non_git_writes.py` passes with its four `extends` rows
   (`tests/test_non_git_writes.py:424-431`) untouched. **[corrected]** — the
   first draft asked for exit 0 here, which that file forbids.
6. A pre-existing, **well-formed** `docs/taxonomy/config.yaml` containing
   `extends:\n  - base` has no effect: `tcw taxonomy list` shows no inherited
   terms, `tcw taxonomy check` and `tcw validate` report nothing at all about
   the file, and it is still on disk unmodified. Same for
   `docs/capabilities/.config.yaml`. A **malformed** one — a syntax error or a
   duplicate key — is still reported by `tcw validate`
   (`tcw/validate.py:296-301`). **[corrected]**
7. `taxonomy.extends` holding a mapping is refused with
   `legacy extends map is unsupported`, and the message names
   `tcw-config.yaml: taxonomy.extends`. A non-list, a non-string member, an
   invalid project ID and a duplicate ID are each refused, each naming the same
   key path.
8. `tcw taxonomy extends add base` prints a line containing `tcw-config.yaml`
   and containing neither `docs/taxonomy/config.yaml` nor `.config.yaml`, and it
   prints the same line correctly when `taxonomy.path` points elsewhere.
   **[corrected]** — the first draft said "no output of any `tcw` command",
   which nobody can enumerate; the general form is criterion 11's grep.
9. Transitivity survives: with A extending B and B extending C, each declaring
   `taxonomy.extends` in its own `tcw-config.yaml`, `tcw taxonomy list` in A
   resolves both `B/` and `C/` terms. A cycle is still reported by
   `tcw taxonomy check`.
10. Two projects whose `taxonomy.path` points at the *same* folder, declaring
    different `taxonomy.extends`, each resolve their own ancestors.
11. `grep -rn 'config\.yaml' tcw/ --include=*.py | grep -v 'tcw-config'` returns
    **exactly two** lines: the `config.yaml` literal in `FsTaxonomyStore`'s
    `_node_reserved` contribution and the `.config.yaml` literal in
    `FsCapabilitiesStore`'s, plus whatever single comment line justifies them if
    it names a filename. `_TAX_RESERVED` is gone. The count is stated so a new
    stray reference cannot hide in a "nothing except" wording. **[corrected]**
12. The attachment surface is unchanged **on both sides**: a `config.yaml`
    inside a *term* folder is still **not** among that term's attachments, and a
    `config.yaml` inside a *capability* folder still **is** among that
    capability's attachments. **[corrected]** — the first draft tested only the
    side that does not change.
13. A migration guide exists at `docs/migration-guide-2.X-to-3.0.0.md`, covering
    the old filenames, the new keys, that nothing warns, the file re-rendering,
    and both consequences under "Two consequences of per-project inheritance".
    `docs/release-notes/upcoming.md` and `docs/changelogs/upcoming.md` both carry
    an entry.
14. No live document still describes the old location. Specifically
    `skills/configure/references/projects.md:88-97`,
    `docs/guide/taxonomy-and-capabilities.md:51`,
    `docs/guide/multi-repo.md:172` and
    `docs/guide/linking-and-validation.md:57` — the last of which becomes
    factually false the moment `config.yaml` leaves `OWNED_YAML_NAMES` — are
    each corrected, and both federation capability descriptions name the new
    keys. Historical documents (Non-goals) are untouched. **[corrected]** — the
    first draft named only the first of these.
15. `pytest` passes, and `tcw validate` on this repository exits 0.

### Coverage

Each criterion against the six design rules. A cell is a test name or `n/a`;
where an `n/a` rests on a fact about the code rather than on the criterion's own
wording, it carries the `file:line` that settles it. **[corrected]** — the first
draft's preamble promised a line in every `n/a` cell and delivered one, which
made the table disprove its own convention.

| # | R1 key/home | R2 reading | R3 writing | R4 messages | R5 old files inert | R6 migration doc |
| - | ----------- | ---------- | ---------- | ----------- | ------------------ | ---------------- |
| 1 | ✓ | ✓ | n/a — read-only | n/a — `_list` prints only term rows (`tcw/taxonomy/cli.py:44-62`) | ✓ the old file's absence is the premise | n/a |
| 2 | ✓ | ✓ | n/a — read-only | n/a — as 1 | ✓ | n/a |
| 3 | ✓ incl. re-render | n/a — re-read is criteria 1–2 | ✓ | n/a — covered by 8 | ✓ "creates no file under the store" | n/a |
| 4 | n/a — same key | n/a | ✓ the `stage_root` half | n/a | n/a | n/a |
| 5 | n/a | n/a | ✓ the `_require_repository` half | ✓ asserts a one-line refusal | ✓ "tree unchanged" | n/a |
| 6 | n/a — asserts the key's absence | ✓ nothing loads the old path | n/a — no write runs | n/a | ✓ both halves, well-formed and malformed | n/a |
| 7 | ✓ validation unchanged | ✓ refusal raised on load | n/a — refusal precedes any write | ✓ the key path in all four refusals | n/a | n/a |
| 8 | n/a | n/a | n/a | ✓ | n/a | n/a |
| 9 | ✓ per-project declaration | ✓ each node read separately | n/a — fixtures declare the key directly | n/a | n/a | n/a |
| 10 | ✓ Goal 2 as a check | ✓ | n/a | n/a | ✓ shared folder holds no config | n/a |
| 11 | n/a | n/a | n/a | n/a | ✓ and sweep finding 2 | n/a |
| 12 | n/a | n/a | n/a | n/a | ✓ the `_node_reserved` half of R5 | n/a |
| 13 | ✓ re-render is named in the guide | n/a | n/a | n/a | n/a | ✓ |
| 14 | ✓ names the keys | n/a | n/a | n/a | ✓ `linking-and-validation.md` tracks `OWNED_YAML_NAMES` | ✓ same pass |
| 15 | ✓ | ✓ | ✓ | ✓ | ✓ | n/a — `tcw validate` does not read prose |

Three rules are load-bearing and easy to leave untested, so each has a criterion
of its own rather than riding on a general one: R3's `stage_root` (criterion 4)
reproduces a bug that has already shipped once (`tcw/store/fs.py:5660-5666`);
R3's `_require_repository` (criterion 5) is an invariant a whole test file
exists to defend; and R5's `_node_reserved` (criterion 12) is a behavior change
that happens by *omission* if nobody writes it down.

## Risks

- **The external-store write is the likely defect.** Staging `tcw-config.yaml`
  against the store's repository fails only when the two are different
  repositories, which no default-layout test exercises. `tcw work tags add`
  shipped exactly this bug. Criterion 4 exists for it and needs a
  two-repository fixture, not a same-repo one.
- **Silent loss of inheritance for anyone already federating.** By decision, an
  old file is ignored with no message. A project that upgrades and does nothing
  loses its inherited entries, and the only warning is the migration guide. The
  requester was asked twice and confirmed. The blast is bounded by how rare
  `extends` is — the file is "optional and commonly absent"
  (`tcw/store/fs.py:3187-3188`) — but it is real.
- **Test churn hides a regression.** Nineteen fixture sites move from writing a
  file to writing a config key. A fixture rewritten slightly wrong is a test that
  passes while testing nothing, and
  `tests/test_capabilities_federation.py:441-452` deliberately writes
  `.config.yaml` *without* going through `extends_add`, so it is testing the read
  path specifically — that intent has to survive the rewrite.
- **`self.config` changes meaning for tree stores.** It stops being "the store's
  file" and becomes "this component's slice of the node config". Any reader
  assuming the former is now wrong; criterion 11's grep is the check.
- **A wrong claim about current behavior can survive review.** Three did, in the
  first draft, and all three came from trusting a comment or docstring instead of
  the code under it — including one docstring that is itself wrong (sweep
  finding 4). The lesson applies to `implement`: read the assertion, not the
  sentence above it.

## Notes

- The requester supplied no reference material; everything cited here was found
  in the repository, and every `file:line` was re-read at the time of writing.
  The first draft's three citation drifts (`2809-2838` for a block starting at
  `2806`, `3274-3280` for a range that excluded where `repository` is read, and
  `5246-5252` for one that cut off the `return`) are corrected above.
- Sweep finding 5 (`docs/work/dod.yaml`) is the one place this item knowingly
  leaves the "one config per project" goal incomplete. It is named in Non-goals
  rather than silently dropped.
- Sweep finding 4 (`_write_tags`'s wrong docstring) is folded in rather than
  filed, under this project's practice for small follow-ups, because it is the
  direct cause of one of this spec's corrections.
