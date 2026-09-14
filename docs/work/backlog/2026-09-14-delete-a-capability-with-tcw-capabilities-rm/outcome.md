# Outcome — Delete a capability with `tcw capabilities rm`

## What was built

- **`tcw capabilities rm <path>`** (`tcw/capabilities/cli.py`). Deletes one local
  capability, prints `Removed capability <path>`, and stages the deletion without
  committing it, like `tcw taxonomy rm`.
- **The store contract** (`CapabilitiesStore.remove` in `tcw/store/base.py`) now
  states when a delete is refused, and `FsCapabilitiesStore.remove`
  (`tcw/store/fs.py`) enforces it. It refuses, writing nothing:
  - a path that resolves to nothing, or any spelling other than the listed path
    (`routes/`, `./routes`, `routes/.`, `Routes` on a case-insensitive disk);
  - a bare path matching more than one inherited project (`AmbiguousRef`);
  - an inherited capability, overridden locally or not — the message names
    `tcw capabilities reset` for dropping an override;
  - a capability with any `meta.yaml` inside its folder (capabilities and override
    folders, including ones in dot-directories), naming them;
  - a capability that another local capability or override folder still
    references through `Superseded by`, `Blocked by`, `Roles` or `When`, naming
    each as `<folder> (<field>)`. Fields are read exactly as `check` reads them,
    and references are matched by folder identity, so `a/b/`, `x/../a/b` and a
    differently-cased spelling all count.
- **`git_rm` treats a path literally** (`--literal-pathspecs`). Before, deleting a
  folder named `a*` also deleted `abc`. The fix is in the shared helper, so
  `tcw taxonomy rm` and the work store's deletes are fixed too.
- **`removed:` in `capabilities.yaml`.** `declared_capabilities` reads it; the
  completion gate (`capability_gate`, `tcw/work/recursion.py`) refuses a
  `removed:` path while a **local** capability still exists there, and no longer
  skips a sidecar holding only `removed:`; the epic rollup prints
  `removed <path>` rows.

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
- **Inbox notes** (in `docs/work/inbox/`, undated like the others there — the
  plan's dated name was dropped to match):
  - `tcw-taxonomy-rm-deletes-nested-terms-without-a-word.md`
  - `the-capability-completion-gate-ignores-a-configured-capabilities-location.md`
  - `store-git-calls-read-a-path-as-a-glob-pattern.md`

## Found during implementation and review

Each was a real defect in this change's code, fixed with a test that fails without
the fix:

1. **Loose target spelling** (found by probing). `get` resolves `routes/` to the
   `routes` folder but echoes the spelling back as the path, so the nested check
   compared the wrong prefix and `git rm -rf` took `routes/login` too.
2. **Loose reference spelling** (found by probing). `Superseded by: a/b/` was
   accepted by `set` but missed by the referrer check.
3. **`..` and case in references; dot-directories in the nested check; the gate
   counting an inherited capability at a removed path** (review round 1).
4. **Glob characters in `git_rm`; a folder vanishing mid-scan** (review round 2).

Details and each reviewer's findings are in `refined-outcome.md`.

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
- The planned `test_cli_rm_is_not_rewritten_to_show` was not written separately;
  `test_cli_rm_removes_and_reports` fails the same way if `rm` is rewritten.

## Tests

- New: `tests/test_capabilities_rm.py` (42 test cases), plus
  `tests/test_capabilities_sidecar.py` (+2, four updated), `tests/test_work.py`
  (+2), `tests/test_recursion.py` (+1).
- Full-suite counts are recorded in `refined-outcome.md`, run after the last code
  change, with both `python -m pytest` and bare `pytest`.
- **Mutation checks:** 24 mutations, each breaking one piece of the new code. 23
  turned their covering tests red with a failure naming the broken behavior; the
  24th, disabling the command's `AmbiguousRef` branch, stayed green and the branch
  was removed (see above). The
  escaping-path test is also held green by the store's existing containment
  check, so it does not isolate the new spelling check; the spelling test does.

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
| `docs/changelogs/upcoming.md` [Any-Code-Change] | Updated: Added, Changed and Fixed entries. |
| `skills/<component>/SKILL.md` [Skill-Driven-Component] | `skills/tcw-capabilities/SKILL.md` updated (command list and reserved words, removed-capability planning step, `removed:` schema and gate rule, the stale "use `remove`", a quick-reference row). `skills/tcw-work` references `transitions.md` and `procedures/audit-backlog.md` updated for `removed:`. |

## Status

The implementation did not transition this item; see `refined-outcome.md` for
acceptance and completion.
