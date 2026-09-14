# Outcome — Delete a capability with `tcw capabilities rm`

## What was built

- **`tcw capabilities rm <path>`** (`tcw/capabilities/cli.py`). Deletes one local
  capability, prints `Removed capability <path>`, and stages the deletion without
  committing it, like `tcw taxonomy rm`.
- **The store contract** (`CapabilitiesStore.remove` in `tcw/store/base.py`) now
  states when a delete is refused, and `FsCapabilitiesStore.remove`
  (`tcw/store/fs.py`) enforces it. It refuses, writing nothing:
  - a path that resolves to nothing, or is spelled loosely (`routes/`,
    `./routes`, `routes/.`, `routes//`);
  - a bare path matching more than one inherited project (`AmbiguousRef`);
  - an inherited capability, overridden locally or not — the message names
    `tcw capabilities reset` for dropping an override;
  - a capability with another capability or override folder nested under its
    path, naming them;
  - a capability that another local capability or override folder still
    references through `Superseded by`, `Blocked by`, `Roles` or `When`, naming
    each as `<folder> (<field>)`.
- **`removed:` in `capabilities.yaml`.** `declared_capabilities` reads it; the
  completion gate (`capability_gate`, `tcw/work/recursion.py`) refuses a
  `removed:` path that still resolves or is ambiguous, and no longer skips a
  sidecar holding only `removed:`; the epic rollup prints `removed <path>` rows.

  ```yaml
  new:
      - skills/tcw-setup
  changed:
      - work/complete-a-work-item
  removed:
      - plugin/work-lifecycle
  ```

- **Ledger:** `capabilities/remove-a-capability` created `Supported` (with
  `Subject: capability` and `Planning doc` set to this item);
  `capabilities/reset-an-override` and `work/complete-a-work-item` bodies updated.
  The item's `capabilities.yaml` records all three.
- **Inbox note:** `docs/work/inbox/tcw-taxonomy-rm-deletes-nested-terms-without-a-word.md`
  — `tcw taxonomy rm` still deletes nested terms and only warns about relations.

## Found during implementation

Probing the finished store code showed that `get` resolves `routes/`, `./routes`,
`routes/.` and `routes//` to the `routes` folder but reports the spelling back as
the capability's path. The nested check compares path strings, so
`remove("routes/")` passed it and `git rm -rf` deleted `routes/login` too. `remove`
now refuses any identifier `_safe_store_id` rejects, with `no such capability`.
Test: `test_remove_refuses_non_canonical_path_spelling`. Acceptance criterion 9
was extended to cover it.

## Deviations from the plan

- Task 4 and the Documentation Sync tasks were committed together, after one full
  suite run, instead of as separate commits.
- The plan deferred creating `capabilities/remove-a-capability` to the requester.
  The requester later handed verification and completion to this session, and
  the completion gate needs the capability to exist, so it was created on the
  branch with this worktree's own CLI (`python -m tcw.cli capabilities add`).
- The command's separate `AmbiguousRef` branch was removed: a mutation check
  showed it changed nothing, because `AmbiguousRef` already carries the message
  `ambiguous ref '<path>' — qualify it with an alias prefix`.

## Tests

- `python -m pytest` from the worktree root before each commit; last run before
  this document: **2844 passed** (11 min 27 s).
- New tests: `tests/test_capabilities_rm.py` (26), plus
  `tests/test_capabilities_sidecar.py` (+2, four updated),
  `tests/test_work.py` (+2), `tests/test_recursion.py` (+1).
- **Mutation checks:** 15 mutations, each breaking one piece of the new code; every
  one turned at least one of its covering tests red, and the failing test named
  the broken behavior, except the command's `AmbiguousRef` branch (removed, see
  above). The escaping-path test is also held green by the store's existing
  containment check, so it does not isolate the new spelling check; the spelling
  test does.

## Verification by hand

1. **The command on a scratch node** (`python evals/seed_fixture.py
   /private/tmp/tcw-rm-verify`, driven with the worktree's CLI): `rm routes`
   refused naming `routes/login`; `rm routes/login` refused naming
   `other (Superseded by)`; after repointing, both removed in order; `rm nope` and
   `rm ../taxonomy` refused; `capabilities check` → `capabilities OK`;
   `git status` showed the four deletions staged; `--help` lists `rm`.
2. **Acceptance criterion 16:** `grep -rn 'use \`remove\`' skills docs/guide tcw docs/capabilities`
   prints nothing.
3. **The consolidation item's nine capabilities:** in a scratch copy of this
   repository's `docs/capabilities` and `docs/taxonomy`, all nine were removed by
   `tcw capabilities rm` without a refusal (18 files staged). None is nested-under
   or referenced.
4. `python -m tcw.cli capabilities check` → `capabilities OK`;
   `python -m tcw.cli validate` → `validate OK`.

## Documentation Sync

| Entry | Verdict |
| --- | --- |
| `README.md` [Public-API] | Evaluated, not changed: it shows a short walkthrough and lists no per-command reference (not even `tcw taxonomy rm`); the command reference is `docs/guide/taxonomy-and-capabilities.md`, which was updated. |
| `docs/release-notes/upcoming.md` [Public-API] | Updated: "Delete a capability with `tcw capabilities rm`". |
| `docs/changelogs/upcoming.md` [Any-Code-Change] | Updated: Added and Changed entries. |
| `skills/<component>/SKILL.md` [Skill-Driven-Component] | `skills/tcw-capabilities/SKILL.md` updated: command list and reserved words, removed-capability planning step, `removed:` schema and gate rule, the stale "use `remove`", a quick-reference row. |

## Status

This item's status was not transitioned by the implementation; see
`refined-outcome.md` for acceptance and completion.
