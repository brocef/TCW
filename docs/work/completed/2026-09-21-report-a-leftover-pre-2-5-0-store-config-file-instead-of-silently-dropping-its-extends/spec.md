# Spec: Report a leftover pre-2.5.0 store config file instead of silently dropping its extends

## Capability changes

Planned ledger deltas only; nothing is written to the ledger at this stage.

- **changed** `capabilities/validate-capabilities` (cap-eb9744): `tcw capabilities
  check` also reports a leftover pre-2.5.0 `.config.yaml` at the root of the
  capabilities store, naming `capabilities.extends` as where its contents belong;
  and an `overrides` pointer to an alias that is not declared says so.
- **changed** `taxonomy/validate-the-taxonomy` (cap-7a08af): `tcw taxonomy check`
  also reports a leftover pre-2.5.0 `config.yaml` at the root of the taxonomy
  store, naming `taxonomy.extends`.
- **changed** `cli/validate-a-node` (cap-2bd014): `tcw validate` reports each such
  leftover once per store, including a store moved by `<component>.path` and a
  run where the component checks were skipped.

No new capability, no Taxonomy change: the Vocabulary this touches (`store`,
`node`, `namespace`) and the Features (`taxonomy-feature-registry`,
`capability-feature-association`, `connected-project-registry`) already cover it.

## Problem

Version 2.5.0 moved `extends` (the list of projects whose taxonomy or capabilities
a project inherits) out of a file inside each store and into the node's
`tcw-config.yaml`, as `taxonomy.extends` and `capabilities.extends`. The old files
are `config.yaml` at the root of the taxonomy store and `.config.yaml` at the root
of the capabilities store. The v2.5.0 changelog records the decision to leave a
leftover copy entirely alone: "A leftover file is inert: not parsed, not reported
by the component `check()`, not deleted" (`docs/changelogs/v2.5.0.md:93-96`).

What the code does today, checked against the tree:

- Nothing reads either file. The names survive only as `LEGACY_CONFIG_NAME`
  (`tcw/store/fs.py:1580-1588`, set at `tcw/store/fs.py:2021` and
  `tcw/store/fs.py:2497`), used for one thing: keeping the filename out of a
  folder node's attachment list (`_node_reserved`, `tcw/store/fs.py:1928-1948`).
- `FsTaxonomyStore.check` (`tcw/store/fs.py:2313`) and
  `FsCapabilitiesStore.check` (`tcw/store/fs.py:2986`) never look for the file.
  `tests/test_taxonomy.py:973` (`test_a_leftover_store_config_is_inert_and_left_alone`)
  pins `check() == []` with a well-formed leftover present.
- `tcw validate`'s YAML pass (`tcw/validate.py:295-310`) reports the file only if
  it fails to parse (`tests/test_taxonomy.py:994`). A well-formed leftover — the
  case that actually loses inherited entries — produces nothing.
- An override pointing at an undeclared alias is reported as
  `overrides → unknown alias '<alias>'` (`tcw/store/fs.py:3104`). That describes
  the effect. On the store `check()` runs on, an alias missing from
  `self.extends` is always one that is not in `<component>.extends`: a declared
  alias that cannot be resolved raises when the store opens
  (`_extended_component_stores`, `tcw/store/fs.py:1345-1396`), and a federation
  cycle's back edge is recorded by the deepest store on the chain, never the top
  one (`_FederationCycles` docstring, `tcw/store/fs.py:1301-1308`), so
  `extends_cycles` is empty on the store a user checks.
- `tcw validate` over a whole node chooses whether to run a tree component's
  `check()` by whether `docs/<component>` exists (`_components_to_check`,
  `tcw/validate.py:102-114`), although the check itself then opens the
  *configured* store; its YAML and link passes only scan `docs/taxonomy` and
  `docs/capabilities` (`_scan_roots`, `tcw/validate.py:68-76`). So a store moved
  with `<component>.path` is checked by `validate` only if a `docs/<component>`
  directory happens to exist as well, and its files are never YAML- or
  link-scanned. A probe during this spec confirmed the common case: a relocated
  taxonomy with no `docs/taxonomy`, holding a term of kind `Nonsense`, gives one
  problem from `FsTaxonomyStore.check()` and none from `validate()`.

The result, as reported from proposit-app: after upgrading, a consumer node's
`tcw capabilities list` dropped from about 128 rows to 32, `check` reported 128
problems (71 of them `unknown alias 'proposit-shared'`), and nothing pointed at the
five leftover files across three nodes that caused it. The migration guide admits
this gap in so many words ("Nothing warns you",
`docs/migration-guide-2.4.X-to-2.5.0.md`).

## Goals

1. Whenever the store opens, `tcw taxonomy check` and `tcw capabilities check`
   report a leftover legacy config file at the root of their store as a problem,
   wherever `<component>.path` or `<component>.repository` puts that store, and
   name the fix: move any needed `extends` into `tcw-config.yaml` as
   `<component>.extends`, then delete the file.
2. `tcw validate` reports the same leftover, once per store that opens, for the
   node and for every descendant project it recurses into — including a store
   moved by `<component>.path` and a run where the component checks were skipped
   because of a YAML problem. A store that does not open is reported once as an
   open failure instead (see Design §4).
3. The `overrides → unknown alias '<alias>'` message also says the alias is not
   declared in `<component>.extends`, naming the config file.

## Non-goals

- **Rewriting or deleting any file.** The requester chose "report only" on
  2026-09-21. No command — not `check`, not `validate`, not `tcw provision` —
  migrates, edits or removes the leftover. The user moves it by hand.
- **Parsing the leftover.** The report is about the file being there, not about
  what it says. Reading it to tailor the message (listing its ids, comparing them
  with `<component>.extends`) would add a parse step that can fail, for a message
  that is already actionable without it.
- **Warnings on other commands.** `tcw taxonomy list`, `tcw capabilities list`,
  `show`, `set` and `tcw provision` stay silent. The request names the two
  `check` commands and `validate`; a warning on every read command is a larger,
  separate decision.
- **Making `tcw validate` cover relocated stores in general.** Its YAML pass,
  link pass and component check all skip a store outside `docs/<component>`
  (see Problem). That is a real defect, found during this spec, but fixing it
  changes which problems every relocated-store project sees and deserves its own
  item, which the team lead is filing separately. This item only guarantees that
  the *leftover report* (and, for a store validate did not check, its open
  failure) reaches `validate`.
- **Cause hints on other reference problems.** An alias-qualified `Subject`,
  `Feature`, `Blocked by` or `relatesTo` ref that stops resolving is reported as a
  dangling ref. Unlike `overrides`, where a `/` always means `<alias>/<id>`
  (`tcw/store/fs.py:3100`), these refs cannot be told apart from a local nested
  path, so the code cannot know an alias was meant. The leftover report, printed
  in the same `check` output, is what points at the cause for those.
- **Other removed inputs from earlier migrations.** The sibling sweep looked for
  other inputs a past release stopped reading silently. The changelogs and
  migration guides record no other one; auditing every historical migration for
  a similar gap is out of scope for a v2.5.1 blocker.

## Design

The store knows where its own root is, so the store reports its own leftover.
This passes the abstraction litmus test in the only way it can: the leftover is a
file inside a filesystem store, with no analog in a non-filesystem store, so it is
a private detail of the filesystem adapter that shows up as one more string in the
problem list the abstract `check()` already returns. No operation is added to the
abstract store interface.

1. **The report.** `FsTreeStore` gains one small private helper that returns the
   leftover problem when `self.root / self.LEGACY_CONFIG_NAME` is a file, and
   nothing otherwise. It only tests for the file; it never opens it. Because
   `self.root` is the resolved store root, a store moved by `<component>.path` or
   provisioned from `<component>.repository` is covered for free. Only the store
   root is examined: a `config.yaml` inside a folder node is an ordinary file
   (`tests/test_capabilities.py:721` pins that case) and stays unreported.

   The report is unconditional — the file's content does not matter — and it is
   a *problem*, not a warning: `check` and `validate` exit 1 while the file
   exists. That was settled with the reviewers. A file that only restates what
   is already in `<component>.extends` still misleads the next reader into
   thinking it is read, and the fix is one `rm`; making the report depend on
   content would need a parse step for a message that is actionable without it.
   Consequence, stated plainly: **a retained leftover now fails `check` and
   `validate`, and so blocks `tcw work complete` in any project that binds
   `tcw validate` as a `pre` check on `complete`** (TCW itself does).

   **A store that fails to open reports no leftover.** Opening a tree store
   resolves its federation first (`FsTreeStore.__init__` →
   `_extended_component_stores`), so a bad `<component>.extends` raises before
   `check()` runs. Then the open failure is what the user sees, from the check
   commands and from `validate`; the leftover is reported on the next run, once
   the open failure is fixed. Adding a second path that finds the leftover
   without opening the store is not worth it: the leftover never causes an open
   failure, because nothing reads it.
2. **Where it appears.** Both components' `check()` add it when called without an
   `identifier`. A scoped `check(identifier=...)` leaves it out: that call is how
   `tcw serve` validates the one object just written
   (`tcw/serve/__init__.py:167-172` → `tcw/validate.py:201-205`), and a
   store-level file would otherwise be attached as a warning to every edit.
3. **The wording.** One line per leftover, carrying: the file's path (relative to
   the node root when it sits inside it, otherwise absolute); that it is no
   longer read since TCW 2.5.0; the destination, as the existing
   `_extends_label()` spells it (`<path>/tcw-config.yaml: taxonomy.extends`,
   `tcw/store/fs.py:1809-1816`); that the file should then be deleted; and that
   if it is already migrated it should just be deleted. For example:
   `docs/capabilities/.config.yaml: no longer read since TCW 2.5.0 — move any
   needed extends into /…/tcw-config.yaml: capabilities.extends, then delete the
   file; if already migrated, just delete it`. The exact text is the plan's to
   settle within those elements.
4. **`tcw validate`.** A whole-node run (no `path`, no `target`) must report each
   tree store's leftover exactly once. Today the component check, which would
   carry it, does not run for a relocated store and is skipped after a YAML
   problem (`tcw/validate.py:321-336`). So `validate` reports the leftover
   directly for any tree store whose `check()` it did not run, following the
   precedent of the retention and tracker problems it already reads straight from
   the work store rather than through `check()` (`tcw/validate.py:258-283`).

   Opening the store for this direct report is guarded the same way `_run_check`
   guards it (`tcw/validate.py:185-206`). If it fails, that failure is reported
   **once**, in `_run_check`'s `<component> check: <error>` shape, instead of the
   leftover. It cannot be assumed to be reported elsewhere: the component check
   and the configured-path check both live inside the block that is skipped after
   a YAML problem (`tcw/validate.py:321-336`), and neither runs for a relocated
   store with no `docs/<component>`. A store whose `check()` validate did run
   gets nothing from this step, so nothing is reported twice.

   A path- or target-scoped run adds nothing beyond what its component check
   produces.

   **This direct report is temporary.** The "which stores did `check()` not
   cover" bookkeeping exists only because `validate` does not follow a relocated
   store. Once the separate item that makes `validate` cover relocated stores
   lands, that bookkeeping should be removed and the leftover left to `check()`
   alone; the plan should leave a comment at the code saying so.
5. **The alias message.** `_override_problem` keeps the existing opening,
   `overrides → unknown alias '<alias>'`, so anyone searching for it still finds
   it, and appends that `<alias>` is not declared in `_extends_label()`. No special
   case for federation cycles: on the store `check()` runs on, an alias absent
   from `self.extends` is always undeclared (see Problem).
6. **Documentation.** The migration guide's "Nothing warns you" section becomes a
   description of the new report; `skills/configure/references/projects.md:107-110`
   ("nothing warns") is corrected; `docs/changelogs/upcoming.md` and
   `docs/release-notes/upcoming.md` get entries, the changelog noting that this
   reverses the v2.5.0 "not reported" decision. The code comments that state the
   file is never reported go stale and are corrected: the `LEGACY_CONFIG_NAME`
   docstring (`tcw/store/fs.py:1580-1588`), the `OWNED_YAML_NAMES` comment
   (`tcw/store/fs.py:1139-1145`) and the comment in
   `tests/test_validate.py:586-592`.

## Acceptance criteria

Fixtures below are built the way `tests/test_taxonomy.py` builds them (`node`,
`connect_sources`): a consumer node connected to a source node `shared`, with
`extends` declared nowhere except in the leftover file.

1. **Taxonomy, default location.** With `docs/taxonomy/config.yaml` containing
   `extends: [shared]`, `FsTaxonomyStore.open(consumer).check()` contains exactly
   one entry that includes the string `config.yaml`, the phrase `no longer read`,
   and `taxonomy.extends`. `tcw taxonomy check` run in the consumer prints that
   entry and exits 1.
2. **Capabilities, default location.** Same as 1 with
   `docs/capabilities/.config.yaml` and `capabilities.extends`, via
   `FsCapabilitiesStore.open(consumer).check()` and `tcw capabilities check`.
3. **Relocated store.** With `taxonomy: {path: tax}` in the consumer's
   `tcw-config.yaml`, no `docs/taxonomy` directory, and the leftover at
   `tax/config.yaml`, `check()` reports it and the reported path is
   `tax/config.yaml`. Same for capabilities with `capabilities: {path: caps}` and
   `caps/.config.yaml`.
4. **Store outside the node root.** (a) With `taxonomy.path` set to an absolute
   path outside the consumer (for example a sibling directory under `tmp_path`)
   and the leftover at its root, `check()` reports it with the file's **absolute**
   path, and whole-node `validate(consumer)` contains exactly one leftover
   problem for it. (b) The same holds for a store provisioned from a
   `<component>.repository` declaration, using the fixtures the existing
   provisioned-store tests use: absolute path in the message, exactly one report
   from `validate`.
5. **Content does not matter, and nothing is parsed.** The report appears, and
   `check()` does not raise, for each of: an empty file; `extends: []`; an
   `extends` list whose ids are already in `<component>.extends`; and an
   unparseable file (`extends: [unclosed`). The message contains both the "move
   any needed extends … then delete the file" instruction and the "if already
   migrated, just delete it" clause.
6. **Only the store root.** No leftover problem is reported for a `config.yaml` or
   `.config.yaml` inside a folder node (for example
   `docs/capabilities/billing/refund/config.yaml`), nor for a directory with the
   legacy name at the store root, nor for capabilities' store holding a
   `config.yaml` (taxonomy's name) or taxonomy's holding a `.config.yaml`.
7. **Scoped checks stay quiet.** With a leftover present,
   `check(identifier=<an existing object>)` on either store contains no leftover
   problem, and `validate(consumer, target=ValidationTarget(axis, ref))` contains
   none.
8. **Nothing touches the file.** After running both `check` commands and
   `tcw validate`, the leftover still exists with byte-identical content.
9. **`tcw validate`, whole node.** Each of the following yields exactly one
   leftover problem per store that has one, and no duplicates:
   (a) both leftovers at default locations — two problems, one per component;
   (b) a relocated store as in criterion 3 — one problem, even though
   `validate` checks nothing else in that store;
   (c) an unparseable leftover — the YAML parse error *and* the leftover problem
   both appear, alongside `(component checks skipped: YAML problem above)`;
   (d) run from a parent project whose descendant holds the leftover — the
   problem appears prefixed with `[<descendant-id>]`;
   (e) a well-formed leftover while a **different** file under the store roots
   (for example a term's `meta.yaml`) has a YAML syntax error — the component
   checks are skipped (`tcw/validate.py:321-336`) and the leftover is still
   reported exactly once.
10. **Open failure of a store validate did not check.** A relocated store (no
    `docs/<component>`) whose `<component>.extends` names a project that is not
    reachable: whole-node `validate(consumer)` reports that open failure exactly
    once, as `<component> check: <error>`, and no leftover problem for that
    store. `tcw taxonomy check` / `tcw capabilities check` on the same fixture
    exit 1 with the open failure, not the leftover (Design §1).
11. **Following the message makes it clean.** In fixture 1 (and 2), moving
    `extends: [shared]` into `tcw-config.yaml` under `taxonomy:` (`capabilities:`)
    and deleting the file makes `check()` return `[]` and the inherited entries
    reappear in `list_all()`.
12. **Alias message.** A capability folder with `overrides: shared/auth`, where
    `shared` is not in `capabilities.extends`, yields a problem that starts with
    `overrides → unknown alias 'shared'` and also contains `capabilities.extends`
    and `tcw-config.yaml`.
13. **Tests.** `tests/test_taxonomy.py::test_a_leftover_store_config_is_inert_and_left_alone`
    is rewritten to the new behavior (still asserting the file is untouched and
    that nothing is inherited from it).
    `tests/test_taxonomy.py::test_a_malformed_leftover_store_config_is_still_reported`
    (`tests/test_taxonomy.py:994`) is tightened to assert the YAML parse error
    itself — a problem naming `docs/taxonomy/config.yaml` that is the parser's
    error, not the new leftover line — because its current
    `any("config.yaml" in p ...)` would pass on the leftover report alone. Bare
    `pytest` passes.
14. **Docs.** `docs/migration-guide-2.4.X-to-2.5.0.md` no longer says an old file
    is "not reported" or that nothing warns, and names `tcw taxonomy check`,
    `tcw capabilities check` and `tcw validate` as where it is reported;
    `skills/configure/references/projects.md` no longer says "nothing warns";
    both `upcoming.md` files have an entry. The release-notes entry states that
    **a retained leftover file now fails `check` and `validate` and can block
    `tcw work complete`**, and that the fix is to move any needed `extends` and
    delete the file.

## Risks

- **New failures on upgrade.** A project that migrated its `extends` but never
  deleted the old file will now see `check` and `validate` fail. TCW's own
  `tcw-config.yaml` binds `tcw validate` as a `pre` check on `complete`, and other
  projects may do the same, so `tcw work complete` can start refusing. This is the
  intended effect, settled with the reviewers (Design §1), and the release notes
  say so (criterion 14).
- **A leftover in a repository this project does not control.** A store reached
  through an absolute `<component>.path` or a `<component>.repository`
  declaration can live in another repository. Its leftover still fails this
  project's `check` and `validate`, and still blocks `tcw work complete` here, but
  deleting it may need a commit in that other repository — possibly by someone
  else. Accepted: the file misleads every project reading that store, and
  printing the absolute path (criterion 4) tells the reader where to go.
- **Wording drift.** The alias message and the leftover message are new strings
  that tests will pin. Keeping the `overrides → unknown alias '<alias>'` opening
  avoids breaking anyone searching for it; no test pins the old full text today.
- **Duplicate reports in `validate`.** The direct report and the component check
  can both carry the same line if the "already checked" bookkeeping is wrong.
  Criteria 4 and 9 exist to catch exactly that.
- **Shared store folders.** Two projects whose `<component>.path` points at the
  same folder both report the same leftover. That is correct — the file misleads
  both — and harmless.

## Notes

- **Decisions settled after review** (Codex and Opus, 2026-09-21; both said
  proceed with changes):
  - The leftover is reported whenever the file exists, as a problem, whatever it
    contains (Design §1).
  - The general "`tcw validate` ignores relocated stores" gap is a separate item,
    filed by the team lead. This item keeps only the leftover's direct report in
    `validate`, to be removed once that fix lands (Design §4).
  - Single-object checks (`check(identifier=...)`, and so `tcw serve`'s
    after-write validation) omit the leftover (Design §2), even though
    store-level cycle and collision problems are reported on those calls today
    (`tcw/store/fs.py:2313-2322`, `2993-3003`): a store-level file is noise on
    every single-object edit.
- **For the plan:** `tcw/validate.py` and `tcw/store/fs.py` are also being
  changed by other v2.5.1 items. Besides this item's own review, review the
  combined difference of those two files across all v2.5.1 items together,
  since an interaction between two items can only be seen once both have landed.
- The stage instructions say to commit `spec.md` on its own. That was not done
  here: the agent running this stage was told to write the file only, because
  other items are being worked in the same checkout at the same time.
- Line numbers were read at commit `61ebb4db`.
