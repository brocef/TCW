# Outcome: make tcw validate check taxonomy and capabilities stores moved by their path setting

## What shipped

- **Tasks 1-2** — `d4af7506`: `tree_store_present` and `FsCapabilitiesStore._taxonomy`
  in `tcw/store/fs.py`; `_tree_roots`, reworked `_scan_roots` /
  `_components_to_check`, guarded `check()` in `_run_check`, and block (d) cut to
  the YAML-problem case in `tcw/validate.py`. Tests: new
  `tests/test_validate_moved_stores.py`.
- **Documentation** — `3a7e9b71`: `docs/guide/linking-and-validation.md`,
  changelog, release notes.
- **Review round 1** — `8e98347e`: tree stores are opened the way `find_node`
  opens them, so a broken `extends` with no local tree is reported again; the
  capabilities check keeps running past an unopenable taxonomy; path mode matches
  a store that will not open. Docstring, target-mode and test tightening.
- **Review round 2** — `d48eb4de`: "Subject and Feature not checked" is said once,
  and only when a checked capability names a Subject or Feature; `939517f1`: path
  mode also matches an unopenable store at its configured path.

## Tests

- Every new test went red on the code before it for the stated reason (round 1:
  4 of 14 on the previous commit; round 2's path-mode test on the previous
  commit).
- Related files (validate, validate target, legacy config, capabilities, serve
  writes): 266 passed; validate files after the last fold-in: 96 passed.
- Full suite: see `refined-outcome.md` (run on the final code).
- Hands-on: scratch node with `taxonomy.path: tax` holding a dangling
  `relatesTo`. Installed build: "validate OK"; worktree build: `taxonomy check:
  payment: dangling relatesTo ref 'invoice'`. With `taxonomy.path: nowhere` the
  installed build stopped at the first error; the worktree build lists it.

## What the plan or spec got wrong

- **Spec criterion 6 and "as today" for `extends`-only nodes were wrong**: the
  old stopgap block reported a broken `extends` in a node with no local tree.
  The first implementation lost that; review found it; restored by opening every
  tree store as `find_node` does. `tree_store_present` stays only for
  `_taxonomy`, where an inherited-only taxonomy must not fail capability checks.
- **The first design let an unopenable taxonomy stop the whole capabilities
  check** (a declared-but-unprovisioned taxonomy is a normal checkout state).
  Fixed in round 1, narrowed in round 2.
- Criterion-4 tests landed in `tests/test_validate_moved_stores.py`, not
  `tests/test_capabilities.py` as planned: one file for the property.

## Documentation Sync

| Entry | Fired? | Done |
| --- | --- | --- |
| `README.md` | No | — |
| `docs/guide/jira.md` | No | — |
| `docs/guide/<topic>.md` | Yes | `linking-and-validation.md`: trees are checked wherever they live. |
| `docs/release-notes/upcoming.md` | Yes | Two lines, incl. the capability-write refusal. |
| `docs/changelogs/upcoming.md` | Yes | Four Fixed entries. |
| `skills/<component>/SKILL.md` | Checked, no | The skills already say `validate` checks every tree. |
| `skills/configure/references/` | No | No key changed. |

## Autonomous decisions

Run unattended on 2026-09-26 (`extras-autonomous-work`).

- **Spec: resolve through `open()`; selection rule; keep or delete the stopgap
  block?** Codex: plan with changes — fix `_taxonomy`'s default-folder gate, add
  shared-store recursion coverage, keep the YAML-skip half. Opus: plan with
  changes — the same three, plus resolve once. Chose all of them.
- **Code review round 1** (adversarial-code-reviewer): NOT DONE — three
  regressions (unopenable taxonomy aborting capability checks; broken `extends`
  without a tree going silent; path mode silent on an unopenable store). All
  fixed with tests that went red first.
- **Round 2**: DONE. Decision A — report "Subject and Feature not checked" on
  every capability check, or only when relevant? Chose only when a checked
  capability names one, so a capability save in a checkout without the
  taxonomy does not always carry a warning about nothing. Folded in finding C
  (path mode, configured path) though the reviewer placed it in a separate
  change: two lines in code this item wrote. Not changed: stores reopened
  several times per run (cost only).
