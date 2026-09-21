# Plan — Report a leftover pre-2.5.0 store config file instead of silently dropping its extends

Implements `spec.md` (committed at `3935639b`). This item is the first of the five
v2.5.1 items to be implemented. It runs in a worktree
(`.worktrees/<slug>` on `work/<slug>`, via `tcw work start --worktree`), and every
"Proves it" step is bare `pytest`, run the way CI runs it (see Notes for how to make
bare `pytest` run the worktree's source).

The order puts the store-level report first (Task 1), because `tcw validate`'s
direct report (Task 2) calls the helper Task 1 adds. The alias wording (Task 3) is
independent and small. Each task leaves the suite green.

"Leftover" below always means the pre-2.5.0 file at the **root** of a tree store:
`config.yaml` for taxonomy, `.config.yaml` for capabilities (the names already held
in `LEGACY_CONFIG_NAME`, `tcw/store/fs.py:2021` and `tcw/store/fs.py:2497`).

## Task 1 — The store reports its own leftover

**Modifies:** `tcw/store/fs.py`, `tests/test_taxonomy.py`.
**Creates:** `tests/test_legacy_store_config.py`.

Code, all inside the filesystem adapter (the abstract `check()` contract, "return
a list of problem strings", does not change, so the abstraction litmus test is
met: a non-filesystem store simply has no such file and adds nothing):

1. On `FsTreeStore` (`tcw/store/fs.py:1570`), add one private method,
   `_legacy_config_problems(self) -> list[str]`:
   - `path = self.root / self.LEGACY_CONFIG_NAME`; return `[]` when
     `LEGACY_CONFIG_NAME` is `None` or `not path.is_file()` (a directory with that
     name is not reported — spec criterion 6). It never opens or parses the file.
   - Display path: `path` relative to `Path(self.node_root).resolve()` when it is
     inside it, otherwise the absolute path. Resolve `node_root` before comparing:
     `self.root` is already resolved by `_open_at` (`tcw/store/fs.py:1667`) while
     `node_root` is kept as handed over, and on macOS `tmp_path` sits behind the
     `/var` → `/private/var` symlink.
   - Return exactly one string:
     `f"{shown}: no longer read since TCW 2.5.0 — move any needed extends into "
     f"{self._extends_label()}, then delete the file; if already migrated, just "
     f"delete it"`.
     `_extends_label()` (`tcw/store/fs.py:1809`) already renders
     `<absolute>/tcw-config.yaml: taxonomy.extends`, so the component key and the
     config file are both named without a second spelling of either.
2. In `FsTaxonomyStore.check` (`tcw/store/fs.py:2313`), right after the
   cycle and collision loops and before the `identifier` branch, add
   `if identifier is None: problems += self._legacy_config_problems()`.
3. The same in `FsCapabilitiesStore.check` (`tcw/store/fs.py:2986`), after its
   cycle and collision loops, before `selected = ...`.
4. Correct the comments that now state something false:
   - the `LEGACY_CONFIG_NAME` class docstring and attribute comment
     (`tcw/store/fs.py:1578-1588`) — the name now has two uses:
     `_node_reserved` and the leftover report;
   - the `OWNED_YAML_NAMES` comment paragraph (`tcw/store/fs.py:1139-1145`) —
     a well-formed leftover is now reported by the component `check()`, still not
     held to the mapping contract;
   - the `_node_reserved` docstring only if it claims the file is otherwise
     unused (re-read it; `tcw/store/fs.py:1928-1943`).

Tests:

- `tests/test_taxonomy.py::test_a_leftover_store_config_is_inert_and_left_alone`
  (line 973): rename to `test_a_leftover_store_config_is_reported_and_left_alone`
  and rewrite. Keep `st.list_all() == []` (nothing is inherited from it) and the
  byte-identical file check; replace `st.check() == []` with: exactly one problem,
  containing `docs/taxonomy/config.yaml`, `no longer read`, `taxonomy.extends`,
  `tcw-config.yaml`, `then delete the file` and `if already migrated, just delete
  it`. Update the docstring: "nothing warns, by decision" is now wrong.
- `tests/test_taxonomy.py::test_a_malformed_leftover_store_config_is_still_reported`
  (line 994): tighten the assertion to the parse error itself. Replace
  `any("config.yaml" in p ...)` with: some problem starts with
  `docs/taxonomy/config.yaml: ` **and** does not contain `no longer read` (so it
  is the YAML pass's line, `tcw/validate.py:299-300`, not the new report). Also
  assert `"(component checks skipped: YAML problem above)" in problems`.
- New `tests/test_legacy_store_config.py`, reusing `node`, `write_term` and
  `connect_sources` from `tests/test_taxonomy.py` the way other modules import
  shared helpers, plus a small local helper that writes a minimal capability
  folder. One test per bullet:
  - taxonomy default location (spec 1) — also runs `main(["taxonomy", "check"])`
    with `monkeypatch.chdir(consumer)`, asserting return `1` and the line on
    stderr via `capsys`;
  - capabilities default location (spec 2) — same, with `.config.yaml`,
    `capabilities.extends` and `main(["capabilities", "check"])`;
  - relocated store (spec 3), parametrized over both components: move the tree to
    `tax` / `caps` with `set_component_key` from `tests/nodeconfig.py`, delete
    `docs/<component>`, reported path is exactly `tax/config.yaml` /
    `caps/.config.yaml`;
  - store at an absolute path outside the node (spec 4a, the `check()` half):
    `<component>.path` = an absolute sibling directory under `tmp_path`; the
    reported path is the absolute path of the file;
  - content does not matter (spec 5), parametrized over `""`, `"extends: []\n"`,
    `"extends: [shared]\n"` with `shared` also declared via `declare_extends`, and
    `"extends: [unclosed\n"` — `check()` does not raise and reports exactly one
    leftover line;
  - only the store root (spec 6): `config.yaml` and `.config.yaml` inside a
    folder node; a *directory* named `config.yaml` at the taxonomy root (it is
    also a term, so assert only that no leftover line appears); `config.yaml` at
    the capabilities root; `.config.yaml` at the taxonomy root — no leftover line
    in any;
  - scoped checks (spec 7, the `check()` half): with a leftover present,
    `check(identifier=<existing term>)` and
    `check(identifier=<existing capability>)` contain no leftover line;
  - following the message makes it clean (spec 11), both components: declare
    `extends: [shared]` with `declare_extends`, delete the file, reopen, assert
    `check() == []` and the `shared/...` entry is back in `list_all()`.

**Proves it:** the tests above pass, and the whole suite passes under bare
`pytest`. At this point `tcw validate` already carries the leftover for a
default-location store (through `_run_check`), which Task 2's tests pin.

## Task 2 — `tcw validate` reports the leftover once per store, even where it does not run `check()`

**Modifies:** `tcw/validate.py`, `tests/test_validate.py`,
`tests/test_store_provisioning.py`, `tests/test_legacy_store_config.py`.

Code, in `validate()` (`tcw/validate.py:220`):

1. Before the `(c)` block (`tcw/validate.py:321`), `checked: set[str] = set()`;
   inside the `for comp in components:` loop, `checked.add(comp)`.
2. After the `(c)` block, only for a whole-node run (`path is None and target is
   None`), for each of `("taxonomy", "capabilities")` not in `checked`:
   - `store = STORE_CLASSES[comp].open(node_root)` inside `try/except ValueError
     as e`, the same guard `_run_check` uses (`tcw/validate.py:198-201`). On
     failure append `f"{comp} check: {e}"` — the exact shape `_run_check` would
     have produced — and continue. (`StoreNotProvisioned`,
     `StoreDeclarationError` and `StoreLocationUnusable` are all `ValueError`
     subclasses; confirm by reading `tcw/store/base.py` while implementing, and
     widen the `except` only if one is not.)
   - Otherwise append
     `[f"{comp} check: {p}" for p in store._legacy_config_problems()]`, the same
     prefix `_run_check` gives the same line, so the output reads identically
     whichever path produced it.
3. A comment at that block saying it is temporary: it exists only because
   `validate` does not follow a store moved outside `docs/<component>` and skips
   component checks after a YAML problem; once the separate item that makes
   `validate` cover relocated stores lands, delete the block and the `checked`
   set, and leave the leftover to `check()` alone (spec Design §4).
4. Update the module docstring (`tcw/validate.py:1-14`), which lists the three
   passes: add one line for this direct report.
5. `tests/test_validate.py:586-592`: the comment inside
   `test_every_yaml_name_tcw_writes_is_owned_or_deliberately_not` says the
   literals "survive only as `LEGACY_CONFIG_NAME`, which keeps each store's former
   filename out of its own attachment listing" — add that they also name the file
   the leftover report looks for. The assertion itself is unchanged.

Tests, in `tests/test_legacy_store_config.py` unless noted (spec criterion 9's
letters in brackets):

- both leftovers at default locations: `validate(consumer)` has exactly two
  leftover lines, one prefixed `taxonomy check:`, one `capabilities check:` [9a];
- relocated taxonomy with no `docs/taxonomy`: exactly one leftover line [9b]; and
  a second case where `docs/taxonomy` also exists (empty), so `(c)` runs
  `check()` on the relocated store — still exactly one line (the duplicate the
  `checked` set prevents);
- unparseable leftover: the parse-error line, the leftover line and
  `(component checks skipped: YAML problem above)` all present, the leftover line
  exactly once [9c];
- parent project whose descendant holds the leftover, run through the CLI
  (`main(["validate"])` from the parent, `capsys`): the line appears prefixed
  `[<descendant-id>]` exactly once [9d] — the prefix is added in `tcw/cli.py:441-444`,
  so this must go through `main`, not `validate()`;
- well-formed leftover while a *different* file (a term's `meta.yaml`) has a YAML
  syntax error: components skipped, leftover line present exactly once [9e];
- absolute-path store outside the node: `validate(consumer)` has exactly one
  leftover line, carrying the absolute path [spec 4a, the `validate` half];
- open failure of a store validate did not check [spec 10]: relocated taxonomy
  with no `docs/taxonomy`, and `declare_extends(consumer, "taxonomy", ...)`
  naming a project id that is not in `connected-projects`. Assert `validate`
  reports exactly one `taxonomy check:` line carrying the open error — assert it
  contains the undeclared project id and `taxonomy.extends`, which every
  refusal from `_extended_component_stores` carries
  (`tcw/store/fs.py:1349-1358`), rather than pinning the rest of the wording —
  and no leftover line; and `main(["taxonomy", "check"])` returns `1` with the
  open error on stderr, not the leftover;
- scoped `validate` [spec 7, the `validate` half]:
  `validate(consumer, target=ValidationTarget("taxonomy", <term>))` and the
  capabilities equivalent contain no leftover line;
- nothing touches the file [spec 8]: after `main(["taxonomy", "check"])`,
  `main(["capabilities", "check"])` and `main(["validate"])`, both leftovers
  exist with byte-identical content.
- **In `tests/test_store_provisioning.py`** [spec 4b]: a taxonomy store
  provisioned from a `taxonomy.repository` declaration, built with the module's
  existing `_repo`, `_remote_with_tree` and `FsStoreProvisioner(...,
  "taxonomy", declaration).ensure_available()` (the pattern of
  `test_an_absent_local_store_falls_through_to_the_provisioned_one`, line 594,
  with the component switched to taxonomy). Commit a `config.yaml` into the
  remote's tree before provisioning. Assert `FsTaxonomyStore.open(code).check()`
  reports it with its absolute path, and `validate(code)` reports it exactly
  once. `conftest.py`'s `_cache_in_tmp` already keeps the clone inside
  `tmp_path`.

**Proves it:** the tests above pass; the whole suite passes under bare `pytest`.
If an **existing** test now fails because a node with a declared but
unprovisioned taxonomy or capabilities store (and no `docs/<component>`) gains a
new `validate` problem, stop and report it rather than editing the test to match:
see Notes, "A consequence of spec Design §4 to confirm".

## Task 3 — The `unknown alias` message names the cause

**Modifies:** `tcw/store/fs.py`, `tests/test_capabilities_federation.py`.

1. `FsCapabilitiesStore._override_problem` (`tcw/store/fs.py:3104`): change the
   return to
   `f"overrides → unknown alias '{alias}' (not declared in {self._extends_label()})"`.
   The opening is unchanged, so a search for the old text still finds it. No
   cycle special case (spec Design §5).
2. Test in `tests/test_capabilities_federation.py`, next to the existing
   `dangling id` / `ambiguous id` override tests (lines 159 and 181), reusing that
   module's fixtures: a child capability folder with `overrides: shared/auth`
   where `shared` is not in `capabilities.extends`. Assert a problem starts with
   `overrides → unknown alias 'shared'` and contains `capabilities.extends` and
   `tcw-config.yaml` [spec 12].

**Proves it:** that test passes; `grep -rn "unknown alias" tests` shows no other
test depending on the old full text (none did when the spec was written); bare
`pytest` passes.

## Task 4 — Reconcile the capability ledger

**Modifies:** `docs/capabilities/capabilities/validate-capabilities/description.md`,
`docs/capabilities/taxonomy/validate-the-taxonomy/description.md`,
`docs/capabilities/cli/validate-a-node/description.md`.
**Creates:** `capabilities.yaml` in the item folder, with

```yaml
changed:
    - capabilities/validate-capabilities
    - taxonomy/validate-the-taxonomy
    - cli/validate-a-node
```

Three changed records, as the spec's Capability changes section names them; no
status changes. Description edits, in the records' existing plain style:

- `capabilities/validate-capabilities` — add that `check` flags a leftover
  pre-2.5.0 `.config.yaml` at the ledger's root and says to move any needed
  `extends` into `capabilities.extends`, and that an override naming an
  undeclared project says it is not declared in `capabilities.extends`.
- `taxonomy/validate-the-taxonomy` — add the leftover `config.yaml` report.
- `cli/validate-a-node` — add that validation reports each leftover once per
  store, including a store kept outside `docs/<component>` and a run whose
  component checks were skipped.

Run this task with the `capabilities` skill rather than editing blind. The
records' metadata does not change, so `tcw capabilities set` is not needed; the
body is `description.md`, which `set` does not write.

**Proves it:** `tcw capabilities check` and `tcw validate` from the worktree
report nothing new; the three descriptions mention the leftover report.

## Task 5 — Documentation Sync block

**Modifies:** `docs/changelogs/upcoming.md`, `docs/release-notes/upcoming.md`,
`docs/migration-guide-2.4.X-to-2.5.0.md`, `docs/guide/linking-and-validation.md`,
`docs/guide/taxonomy-and-capabilities.md`, `skills/taxonomy/SKILL.md`,
`skills/capabilities/SKILL.md`, `skills/configure/references/projects.md`.

One pass over the finished diff of Tasks 1–4, answering every entry in the table
under **Documentation Sync** below. Invoke the `documentation-sync` skill for it,
as `CLAUDE.md` requires before reporting a code change complete.

**Proves it:** spec criterion 14, checked by reading plus these greps from the
worktree root, each returning nothing:
`grep -n "not reported\|Nothing warns\|nothing warns" docs/migration-guide-2.4.X-to-2.5.0.md skills/configure/references/projects.md`.
Bare `pytest` still passes (`tests/test_plugin_manifests.py` and the skill tests
read these files).

## Documentation Sync

Evaluated against this node's entries (`tcw work docs`), for Task 5:

| Entry | Trigger | Fires? |
| --- | --- | --- |
| `README.md` | **Public-API** | **No change needed — re-check at Task 5.** The two `check` rows (`README.md:302`, `README.md:363`) and the `validate` row (`README.md:234`) describe what is checked in one line each and stay true; no command, flag or output format a reader would look up there changes. Re-read those rows against the final wording before closing. |
| `docs/guide/jira.md` | **Tracker-Change** | No. No tracker command, ticket behavior or `work.tracker` key changes. |
| `docs/guide/<topic>.md` | **Guide-Topic-Change** | **Yes, two guides.** `docs/guide/linking-and-validation.md`: add a short subsection after "A record of the wrong shape" — "A leftover pre-2.5.0 store config", showing the message and the fix (move any needed `extends` into `tcw-config.yaml`, delete the file), and stating it fails `validate`. `docs/guide/taxonomy-and-capabilities.md`: one sentence in the federation paragraph (lines 50-56) that `check` flags an old `config.yaml` / `.config.yaml` left in the tree. `docs/guide/multi-repo.md`'s inheritance section (lines 167-183) names no old file and needs nothing. |
| `docs/release-notes/upcoming.md` | **Public-API** | **Yes.** Plain language: `tcw taxonomy check`, `tcw capabilities check` and `tcw validate` now point at a leftover `docs/taxonomy/config.yaml` or `docs/capabilities/.config.yaml` (or its equivalent wherever the tree lives) and say how to fix it; the override "unknown alias" message now says the project is not declared in `tcw-config.yaml`. **Must state that a retained old file now fails `check` and `validate` and can block `tcw work complete`**, and that the fix is to move any needed `extends` and delete the file (spec criterion 14). Place it beside the existing "Read those notes before upgrading if you use inheritance" paragraph. |
| `docs/changelogs/upcoming.md` | **Any-Code-Change** | **Yes.** **Changed:** `FsTaxonomyStore.check` / `FsCapabilitiesStore.check` report a leftover at the store root when unscoped, via `FsTreeStore._legacy_config_problems` (existence only, never parsed) — reverses v2.5.0's "not reported by the component `check()`"; `validate()` reports it directly for tree stores whose `check()` it did not run, and an open failure of such a store once (temporary, pending the relocated-stores item); `_override_problem`'s unknown-alias text names `<component>.extends`. **Internal:** the rewritten and tightened leftover tests. |
| `skills/<component>/SKILL.md` | **Skill-Driven-Component** | **Yes, two skills.** `skills/taxonomy/SKILL.md:85-87` ("Run `tcw taxonomy check` after edits — it validates …"): add the leftover config file to the list. `skills/capabilities/SKILL.md`: where `check` is described (line 55 or 59), add the same, and that an "unknown alias" override means the project is missing from `capabilities.extends`. |
| `skills/configure/references/<document>.md` | **Configuration-Key-Change** | **Yes — the meaning of an old file changes, not a key.** `skills/configure/references/projects.md:107-110` says "Those files are no longer read and nothing warns"; change to: they are no longer read, and `check` and `validate` report one until it is deleted. No key is added or removed. |

## Verification

What the suite cannot check, to be confirmed by hand at `verify`:

1. **The message reads well in a real run.** In a scratch node with both
   leftovers, run `tcw taxonomy check`, `tcw capabilities check` and
   `tcw validate` using the worktree's source, and read the output: one line per
   leftover, sensible path, no doubled prefix, the "if already migrated" clause
   present.
2. **This repository stays clean.** `tcw validate` from the worktree root
   reports nothing new — TCW binds `tcw validate` as a `pre` check on `complete`,
   so a false report here would block completing this very item. (This checkout
   has no leftover file; the check found none at planning time.)
3. **Wording of the docs** (Task 5) against the spec's plain-language rule, and
   the release-notes warning about `tcw work complete` being present and plain.
4. **Bare `pytest` from the worktree root**, with the worktree's source actually
   imported (see Notes). A green `python -m pytest` is not evidence about CI.
5. **Combined review with the other v2.5.1 items.** `tcw/validate.py` and
   `tcw/store/fs.py` are also changed by other items in the v2.5.1 batch. Besides
   this item's own review, review the combined difference of those two files
   once the batch has landed, since an interaction between two items is only
   visible then (spec Notes).

## Notes

**No blockers.** This item is implemented first of the five; nothing it depends
on is outstanding, so no `--blocked-by` is recorded. The later items that touch
`tcw/validate.py` or `tcw/store/fs.py` should rebase onto it.

**Do not drive the lifecycle with the `tcw` CLI once Task 1 begins.** Tasks 1–3
edit `tcw/`, which is the CLI that would be driving. Per this repo's agent guide,
from then on the work system is maintained by editing `docs/work/` directly, and
the gates, Definition of Done and tracker sync those commands would run are done
by hand. Reading verbs (`tcw work show`, `tcw work docs`) stay safe.

**Running the worktree's source.** The shared editable install is pinned to the
primary checkout, and bare `pytest` follows that pin, not the current directory.
With other sessions working in this repository, use a private virtual
environment rather than re-pointing the shared install:
`python -m venv --system-site-packages <scratch>/venv`,
`<scratch>/venv/bin/pip install -e <worktree> --no-deps`,
`<scratch>/venv/bin/pip install --ignore-installed pytest`, then run bare
`pytest` with `<scratch>/venv/bin` first on `PATH`, from the worktree root.
Leave the shared install at `pip install -e /Users/brian/Projects/TCW` when done.

**A consequence of spec Design §4 to confirm.** The direct report in Task 2 opens
every tree store whose `check()` `validate` did not run, and reports an open
failure once. That includes a taxonomy or capabilities store that is declared in
`<component>.repository` but not yet provisioned, on a node with no
`docs/<component>`: today `validate` says nothing about it (the component is not
selected, `tcw/validate.py:102-114`), and after this change it reports
"not provisioned; run `tcw provision`". That matches what the
`cli/validate-a-node` capability already claims for all three components, and it
is what `validate` already does for the work store — but it is a new failure a
cloud session without provisioned trees could hit through the `pre` check on
`complete`. The spec requires it (Goal 2, criterion 10). If it proves unwelcome,
the narrower alternative is to report open failures only for a store whose
`<component>.path` is set, and leave unprovisioned declarations to the
relocated-stores item — that would be a spec change, not an implementation
choice.

**Not planned, by the spec:** no migration or deletion of the file by any
command; no warnings on `list`, `show`, `set` or `provision`; no cause hints on
other dangling alias-qualified refs; no general fix for `validate` skipping
relocated stores (separate item).

## Decision taken on the plan (2026-09-21, autonomous run)

- **An unprovisioned `<component>.repository` store fails `validate`** (option a,
  as planned). Codex and Opus both chose (a). The work store already behaves this way
  (`_claims_work` and `_run_check` in `tcw/validate.py`), the `StoreNotProvisioned`
  message names `tcw provision`, and `cli/validate-a-node` claims it for all three
  components. Task 2 adds a test for a repository-only declaration with no local
  tree. The changelog and release notes call out that such a node can now be refused
  at `tcw work complete`.
