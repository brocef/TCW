# Outcome — Report a leftover pre-2.5.0 store config file instead of silently dropping its extends

Implemented in the worktree on `work/2026-09-21-report-a-leftover-pre-2-5-0-store-config-file-instead-of-silently-dropping-its-extends`,
following `plan.md` task by task. The lifecycle was not driven with the `tcw` CLI
once `tcw/` was being edited; this file and `capabilities.yaml` were written by
hand.

## What shipped

| Task | Commit | What |
| --- | --- | --- |
| 1 | `43b3e0e1` | `FsTreeStore._legacy_config_problems` reports a `config.yaml` / `.config.yaml` at the store root (existence only, never opened); both `check()` methods add it when not scoped to one object. Comments that said the file is never reported corrected. `tests/test_legacy_store_config.py` created; the two leftover tests in `tests/test_taxonomy.py` rewritten and tightened. |
| 2 | `3f814984` | `validate()` reports the leftover directly for each tree store whose `check()` it did not run, or that store's open failure once; marked temporary. Tests for spec criteria 4, 7–10 (all of 9a–e), the repository-provisioned tree, and — per the decision appended to the plan — an unprovisioned repository-only declaration, which now fails `validate`. |
| 3 | `c07822ad` | `overrides → unknown alias '<alias>'` gains `(not declared in <path>/tcw-config.yaml: capabilities.extends)`. |
| 4 | `7183a84e` | Ledger: `capabilities/validate-capabilities`, `taxonomy/validate-the-taxonomy`, `cli/validate-a-node` descriptions; the item's `capabilities.yaml` (`changed:` those three). |
| 5 | `96efc563` | Documentation Sync (see below). |

## Tests

- Every new test was watched fail before its code existed, for the reason it
  names (no leftover line; no `capabilities.extends` in the alias text; the
  validate cases with an empty problem list or only the YAML error).
- Mutation checks, each confirmed red for the named reason and then restored:
  `is_file()` → `exists()` (the directory case failed); the root-only lookup
  replaced by a search at any depth (the folder-node case failed); the
  `identifier is None` guard removed (the scoped-check case failed); the node
  root compared in its unresolved `/var` spelling (the symlink case and 12
  others failed); the YAML pass made to skip `config.yaml` (the tightened
  malformed test failed with `0 == 1`); in `validate`, the "already checked"
  skip removed (three duplicate-count tests failed), the open-failure line
  dropped (the cannot-open and unprovisioned tests failed), the direct report
  run for target-scoped runs too (both one-object tests failed); the helper
  made to rewrite the file (the untouched-file test failed).
- Full suite, bare `pytest` with no git identity
  (`GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null pytest -q -p no:cacheprovider`),
  worktree source via a private venv: **`3923 passed in 1178.12s (0:19:38)`**, run after the last code and documentation commit (`96efc563`).
- Real run in a scratch node with both leftovers: `tcw taxonomy check` and
  `tcw capabilities check` each print one line and exit 1; `tcw validate` prints
  both, prefixed `taxonomy check:` / `capabilities check:`, and exits 1.
- `tcw capabilities check`, `tcw taxonomy check` and `tcw validate --no-recurse`
  on this repository from the worktree: all OK.

## What the plan or spec got wrong

1. **Spec criterion 10, second half, cannot be met without an out-of-scope
   change.** It says `tcw taxonomy check` on a store that fails to open "exits 1
   with the open failure". It exits 1 and does not mention the leftover, but the
   message it prints is `no tcw taxonomy node here — run tcw init`: `find_node`
   (`tcw/store/fs.py:192-226`) turns every open failure other than a
   provisioning one into "no node here". That misdirection predates this item
   and affects every taxonomy and capabilities command with a bad `extends`, not
   just `check`. The test asserts exit 1 and no leftover line, and says why.
   **Follow-up filed** as backlog item
   `2026-09-21-let-a-broken-extends-reach-the-user-instead-of-find-node-answering-no-node-here`:
   make `find_node` let a federation `ValueError` through, as it already does
   for `StoreNotProvisioned` and `StoreDeclarationError`.
2. **Plan Task 1 asked to resolve `node_root` before comparing paths**, because
   `self.root` is resolved and `node_root` "is kept as handed over". Not so on any
   path that reaches `check()`: `resolve_store` resolves `node_root` before
   building the store. The extra `resolve()` could not be made to matter by any
   test, so it was dropped; a symlinked-ancestor test pins the property instead
   and goes red if the two roots ever stop being compared in the same form.

## Documentation Sync

| Entry | Fired? | Done |
| --- | --- | --- |
| `README.md` [Public-API] | No change needed | Re-read the `validate` and both `check` rows; each still describes what is checked in one line. |
| `docs/guide/jira.md` [Tracker-Change] | No | — |
| `docs/guide/<topic>.md` [Guide-Topic-Change] | Yes | `linking-and-validation.md`: new subsection on the leftover; `taxonomy-and-capabilities.md`: one sentence in the federation paragraph. Also `docs/migration-guide-2.4.X-to-2.5.0.md` ("How you find out" replaces "Nothing warns you"). |
| `docs/release-notes/upcoming.md` [Public-API] | Yes | New section; states that a kept file fails `check`/`validate` and can block `tcw work complete`, and that an unprovisioned declared tree now fails `validate`. "Nothing else changed" removed. |
| `docs/changelogs/upcoming.md` [Any-Code-Change] | Yes | **Changed** (three entries) and **Fixed** (the test tightening). |
| `skills/<component>/SKILL.md` [Skill-Driven-Component] | Yes | `skills/taxonomy/SKILL.md`, `skills/capabilities/SKILL.md`. |
| `skills/configure/references/<document>.md` [Configuration-Key-Change] | Yes (meaning of an old file) | `projects.md` no longer says "nothing warns". |

## Notes

- `tcw/validate.py` and `tcw/store/fs.py` are also changed by other v2.5.1
  items; the combined difference should be reviewed once the batch lands (plan
  Verification 5).
- The `validate` direct report (block `(d)`) is to be removed when the separate
  "validate ignores relocated stores" item lands; the code comment says so.
- **Folded in at verify:** a review finding that the `validate` direct report
  opens every tree store it did not check, so *any* open failure of a tree
  with no `docs/<component>` is now a `validate` problem — not only an
  unprovisioned `<component>.repository`, but also a `<component>.path` that is
  missing on this machine and an `extends` naming an unreachable project. The
  changelog, release notes and `cli/validate-a-node` now say so, and that each
  can refuse `tcw work complete` where `tcw validate` is a `pre` check. A
  separate crash the reviewer found in `validate` is being filed by the team
  lead as its own item.
- The release notes' opening "Nothing else changed" sentence, which Task 5 had
  reworded, was restored at verify on request; it is reconciled at merge.

## Autonomous decisions

Taken in an autonomous run; each consulted Codex (read-only) and an Opus subagent.

- **Report the file whenever it exists, even when its extends is already migrated?** Codex: always a problem, and the message covers "already migrated → just delete it". Opus: always a problem, noting stores that live in another repository. Chose always a problem.
- **`tcw validate` ignores stores relocated by `<component>.path` in general.** Codex: a separate item. Opus: a separate item. Chose a separate item, filed as `2026-09-21-make-tcw-validate-check-taxonomy-and-capabilities-stores-moved-by-their-path-setting`.
- **Must the alias hint cover a cycle?** Codex: require the cycle hint. Opus: that branch can't be reached on the top store. Split. Reading tcw/store/fs.py (the docstring at ~1304-1306) settled it: cycles are recorded on the deepest store, never on the top one that `check()` runs on. Took Opus's answer and dropped the branch.
- **(Plan) A store declared only by `<component>.repository` and not provisioned: fail validate?** Codex: yes (option a). Opus: yes (option a). Chose yes, consistent with the work store; the message names `tcw provision`.
- **Code review** (adversarial-code-reviewer): DONE on the condition that the documents also name the other open failures validate now reports (a missing `<component>.path`, an unreachable `extends`). Fixed in adef4912. Its pre-existing crash finding (a missing `taxonomy.path` inside the capabilities check) was filed as `2026-09-21-report-a-missing-taxonomy-path-as-a-validate-problem-instead-of-crashing-inside-the-capabilities-check`. Nothing rejected.
- **Verify** (tcw:verifier): accept. Criteria 1–9 and 11–14 are met. Criterion 10 is met for `validate`, and for the check commands only as far as "exit 1, no leftover line". Accepted with that gap, because the cause is `find_node`, which predates this item and is filed as `2026-09-21-let-a-broken-extends-reach-the-user-instead-of-find-node-answering-no-node-here`.
- **Hands-on QA** by the coordinating session: in a scratch node with both leftover files, each check command printed its one line and exited 1, and `validate --no-recurse` printed both and exited 1. After the files were deleted, `validate` was OK.
