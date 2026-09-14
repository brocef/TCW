# Plan — Delete a capability with `tcw capabilities rm`

Implements `spec.md`. Every task writes its tests first, watches them fail for the
reason the task names, then writes the code. The full suite runs from the
repository root with `python -m pytest` before each commit.

## Before starting

- This item is worked in an isolated worktree whose branch is not `main`. The
  editable install points at the primary checkout, so tests run from the worktree
  root as `python -m pytest`, after `python -c "import tcw; print(tcw.__file__)"`
  prints the worktree's path.
- The item's status is not transitioned here (no `tcw work start`); the requester
  does that. While `tcw/` is being edited, the lifecycle is not driven through the
  `tcw` CLI (`CLAUDE.md`, "Exception").
- No blockers to record: nothing this item needs is open elsewhere.

## Tasks

### Task 1 — Declare a removal in `capabilities.yaml`

The gate and rollup change first: they are independent of the command and the
lowest-risk half.

**Files**

- `tests/test_capabilities_sidecar.py` — the four tests comparing the whole
  returned mapping (`test_canonical_new_and_changed`, `test_added_is_alias_for_new`,
  `test_none_and_empty`, `test_list_form_declares_nothing`) gain
  `"removed": []`; new tests `test_removed_is_read` (AC 12: `{"removed":
  ["a/b # gone"]}` → `removed == ["a/b"]`) and `test_removed_non_list_raises`
  (AC 12).
- `tests/test_work.py` — next to `test_complete_gate_unresolved_refuses`:
  - `test_complete_gate_removed_absent_passes` (AC 13): `_item_with_delta(root,
    "removed:\n- ghost/path\n")`, `complete` exits 0.
  - `test_complete_gate_removed_still_resolving_refuses` (AC 14): `auth/login`
    added, `_item_with_delta(root, "removed:\n- auth/login\n")`, `complete` exits
    1, stderr contains `declared (removed) but still resolves`, item still
    `active`. This is the test that proves the early return no longer skips a
    sidecar holding only `removed:`.
- `tests/test_recursion.py` — `test_reconcile_surfaces_removed_capability_deltas`
  (AC 15): `_child_task(a, epic.slug, caps="removed:\n  - a/b\n")`, the block
  contains `removed a/b` and not `skipped`.
- `tcw/store/base.py` — `declared_capabilities` (`:288-321`): a `removed` bucket
  read from `removed:`; docstring names it.
- `tcw/work/recursion.py`:
  - `capability_gate` (`:27-68`): the early return tests all three lists; a loop
    over `deltas["removed"]` reporting a resolving path as
    `<path>: declared (removed) but still resolves (delete it with \`tcw capabilities rm\`)`
    and an ambiguous one with the resolver's message; docstring updated.
  - `_capability_deltas` (`:92-128`): iterate `("new", "changed", "removed")`; the
    condition at `:116` tests all three; the skip message at `:127` reads
    `has no new:/changed:/removed: entries`.

**Proof:** the new tests fail before the code (the gate test fails with exit 0
instead of 1, because the sidecar is ignored); all pass after.

**Commit:** `feat(work): declare a deleted capability under removed: in capabilities.yaml`

### Task 2 — The store refuses a delete that would take more than its target

**Files**

- `tests/test_capabilities_rm.py` (new). Helpers copied from
  `tests/test_capabilities_reset.py` (`repo`, `write_cap`, `connect`, `store`,
  `tree_hash`), as each capabilities test module keeps its own. Store-level tests:
  - `test_remove_deletes_local_capability_and_stages_it` (AC 1, store half):
    `get` is `None` afterwards and `git status --porcelain` shows `D ` for its
    `meta.yaml`.
  - `test_remove_unknown_path_changes_nothing` (AC 2).
  - `test_remove_inherited_refuses_bare_and_qualified` (AC 3).
  - `test_remove_overridden_inherited_names_reset` (AC 4): message contains
    `tcw capabilities reset`; override folder still present.
  - `test_remove_ambiguous_bare_ref_raises` (AC 5).
  - `test_remove_refuses_nested_capability` (AC 6): message names `routes/login`;
    both still resolve.
  - `test_remove_refuses_nested_override_folder` (AC 6): a local `auth`
    capability with an override of an inherited `auth/login` materialized at
    `auth/login`; `remove("auth")` refuses naming `auth/login`.
  - `test_remove_refuses_referenced_target` parametrized over
    `Superseded by=<t>`, `Blocked by=<t>`, `Roles=[!roles/<t>]` and
    `When=conditions/<t>` (AC 7): message names referrer path and field; target
    still resolves. Each case asserts the tree hash is unchanged, through one
    helper `_assert_nothing_removed(root, before)`.
  - `test_remove_refuses_reference_held_by_override` (AC 7).
  - `test_remove_succeeds_after_referrer_repointed` (AC 8).
  - `test_remove_ignores_unresolvable_reference_tokens`: a referrer with a
    dangling `Blocked by` does not block an unrelated removal.
  - `test_remove_path_escaping_store_changes_nothing` (AC 9).
- `tcw/store/base.py` — `CapabilitiesStore.remove` (`:565-567`) gains the
  contract docstring from the spec's table; `reset`'s docstring (`:570-575`)
  says `tcw capabilities rm`.
- `tcw/store/fs.py`:
  - `FsCapabilitiesStore.remove` (`:2481-2488`): after the inherited check, a
    nested check and a referrer check (below), then `_rm`. The inherited refusal
    keeps its `cannot remove inherited capability` prefix
    (`tests/test_capabilities_federation.py:143`, `:392` match it) and appends the
    `reset` hint.
  - A private `_referrers(self, cap) -> list[str]` returning `"<path> (<field>)"`
    for every `_all_meta_dirs()` folder other than the target whose
    `Superseded by`, `Blocked by`, `Roles` or `When` token resolves, via `get`, to
    a local capability at the target's path. Tokens for `Roles`/`When` are read
    as `_check_globals` reads them (`:2833-2844`): list or comma string, `!`
    stripped. `AmbiguousRef` from `get` counts as no match.
  - `reset`'s refusal (`:2493-2494`) reads `(use \`tcw capabilities rm\` to delete it)`.
    `tests/test_capabilities_reset.py:117` matches `local capability`, which stays.

**Proof:** nested, reference and reset-hint tests fail before the code (the
nested test fails because `routes/login` no longer resolves after the call); all
pass after. `tests/test_non_git_writes.py:265` (AC 10) stays green.

**Commit:** `feat(capabilities): refuse a delete that would remove a nested or referenced capability`

### Task 3 — The `tcw capabilities rm` command

**Files**

- `tests/test_capabilities_rm.py` — CLI tests through `tcw.cli.main` with
  `monkeypatch.chdir`:
  - `test_cli_rm_removes_and_reports` (AC 1): exit 0, stdout
    `Removed capability x`, then `main(["capabilities", "show", "x"]) == 1`.
  - `test_cli_rm_is_not_rewritten_to_show`: a capability named `rm` does not
    exist, so `main(["capabilities", "rm", "x"])` must reach `_rm` rather than
    `show rm` — asserted by the `Removed capability` output.
  - `test_cli_rm_unknown_path` (AC 2): exit 1, stderr
    `tcw capabilities rm: no such capability: nope`, stdout empty.
  - `test_cli_rm_ambiguous` (AC 5): exit 1, stderr contains
    `ambiguous ref 'auth/login'`.
  - `test_cli_rm_refusal_reports_referrer` (AC 7, CLI half): exit 1 and stderr
    names the referrer.
  - `test_cli_help_lists_rm` (AC 11): `capsys` output of
    `main(["capabilities", "--help"])` (catching `SystemExit`) contains `rm`
    followed by its help text `remove a local capability`.
- `tcw/capabilities/cli.py`: `"rm"` in `SUBCOMMANDS` (`:12`); `_rm` handler;
  parser registration after `reset` (`:293-295`).

**Proof:** CLI tests fail before (argparse rejects `rm`, exit 2); pass after.

**Commit:** `feat(capabilities): add tcw capabilities rm`

### Task 4 — Ledger bodies and this item's capability delta

**Files**

- `docs/capabilities/capabilities/reset-an-override/description.md` — "tells me
  to use `remove` instead" → "tells me to delete it with `tcw capabilities rm`
  instead". Plain text, not a `tcw://C/` link: the linked capability is not
  created on this branch (see Deferred), and `tcw validate` would report the link
  as dangling.
- `docs/capabilities/work/complete-a-work-item/description.md` — one paragraph
  after the epic paragraph: a capability the item deleted is listed under
  `removed:` in `capabilities.yaml`, and completion is refused while that path
  still resolves.
- `docs/work/backlog/2026-09-14-delete-a-capability-with-tcw-capabilities-rm/capabilities.yaml`
  — the spec's delta (`new: capabilities/remove-a-capability`, `changed:` the two
  above).

**Deferred to the requester:** creating `capabilities/remove-a-capability`. The
session that builds this item was told not to run a writing `tcw` command against
this repository's ledger, and hand-writing a capability folder (minting its id)
is the shortcut the skill refuses. `outcome.md` gives the exact commands.

**Proof:** `python -m tcw.cli capabilities check` and `python -m tcw.cli validate`
from the worktree root both pass (reading only).

**Commit:** `docs(capabilities): describe capability deletion in the ledger`

### Task 5 — Inbox note: `tcw taxonomy rm` deletes nested terms

**Files:** `docs/work/inbox/2026-09-14-tcw-taxonomy-rm-deletes-nested-terms-without-a-word.md`
— plain Markdown (the CLI is not driven while `tcw/` changes): `FsTaxonomyStore.remove`
(`tcw/store/fs.py:1941-1948`) runs `git rm -rf` on the term's folder, so a parent
term's children go with it; `tcw taxonomy rm` only warns about `relatesTo`.
Reference to this item's decisions 3 and 4.

**Proof:** file exists; no code.

**Commit:** with Task 6's documentation commit.

## Documentation Sync

One pass over the finished diff, after Task 5.

### Task 6 — `skills/tcw-capabilities/SKILL.md` [Skill-Driven-Component] — fires

The command set and the `capabilities.yaml` schema change.

- `:13` — the command list names `rm` (delete), and the reserved-word sentence
  covers `rm` as well as `path`.
- `:33-34` — "Changed / removed existing capability" split: changed goes under
  `changed:`; a removed one is deleted with `tcw capabilities rm <path>` and
  listed under `removed:`, copying the path from `tcw capabilities list` first.
- `:38-47` — schema paragraph and example gain `removed:`; the gate sentence
  says a `removed:` path must no longer resolve.
- `:107` — "use `remove`" → "use `tcw capabilities rm`".
- Quick reference — a row: `delete a local capability` →
  `tcw capabilities rm <path>` (refuses inherited, nested, or referenced).

### Task 7 — `docs/release-notes/upcoming.md` [Public-API] — fires

A "New" entry in plain language: `tcw capabilities rm`, what it refuses, and
`removed:` in a work item's `capabilities.yaml`.

### Task 8 — `docs/changelogs/upcoming.md` [Any-Code-Change] — fires

`Added`: `tcw capabilities rm`; `removed:` read by `declared_capabilities`, the
completion gate and the rollup. `Changed`: `FsCapabilitiesStore.remove` refuses
nested and referenced targets; `CapabilitiesStore.remove` contract documented;
`reset` refusal wording.

### `README.md` [Public-API] — expected not to fire

The README shows a short walkthrough and lists no per-command reference (it does
not list `tcw taxonomy rm` either). Evaluate against the final diff; the command
reference lives in `docs/guide/taxonomy-and-capabilities.md`.

### Also updated (not a declared entry)

- `docs/guide/taxonomy-and-capabilities.md` — `:139` "(use `remove`)" names
  `tcw capabilities rm`; a `tcw capabilities rm` line in the command block at
  `:71-84`. Part of Task 6's commit.

**Commit:** `docs: tcw capabilities rm in the skill, guide, release notes and changelog`

## Verification

The suite cannot check these; each is run by hand and its result recorded in
`outcome.md`.

1. **The command on a real node.** Build `/private/tmp/tcw-rm-verify` with
   `python evals/seed_fixture.py`, then from the worktree root run the worktree's
   CLI against it (`python -c "... main([...])"` with the node as working
   directory): add `routes`, `routes/login`, `other` with
   `Superseded by=routes/login`; `rm routes` (refused, nested), `rm routes/login`
   (refused, referenced), repoint `other`, `rm routes/login` (succeeds),
   `rm routes` (succeeds), `capabilities check` passes, `git status --short`
   shows staged deletions.
2. **AC 16.** `grep -rn 'use \`remove\`' skills docs/guide tcw docs/capabilities`
   prints nothing.
3. **The consolidation item's nine paths.** From the worktree root,
   `python -m tcw.cli capabilities show <path>` resolves each (reading only), and
   a store-level dry check in a scratch copy of `docs/capabilities` confirms none
   of the nine is refused as nested or referenced.
4. **Bare `pytest` matches `python -m pytest`.** Both from the worktree root;
   the counts are recorded. CI runs bare `pytest`.

## Notes

- AC coverage: 1 (T2, T3, V1), 2 (T2, T3), 3 (T2), 4 (T2), 5 (T2, T3), 6 (T2),
  7 (T2, T3), 8 (T2), 9 (T2), 10 (existing test), 11 (T3), 12–14 (T1), 15 (T1),
  16 (T6, V2), 17 (T6), 18 (every commit, V4).
