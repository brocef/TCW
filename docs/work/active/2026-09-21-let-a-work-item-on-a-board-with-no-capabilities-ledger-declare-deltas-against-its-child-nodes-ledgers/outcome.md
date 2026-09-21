# Outcome: Let a work item on a board with no capabilities ledger declare deltas against its child nodes' ledgers

Implemented on branch `work/<slug>` in the item's worktree, following `plan.md`
task by task. Criterion numbers ("C1"…"C21") are the spec's acceptance criteria.
New tests are in `tests/test_capability_gate_children.py` (32 tests after the verify fold-ins).

## What shipped, task by task

| Task | Commit | What it did | Criteria |
|---|---|---|---|
| Setup + 1 | `61a298b9` | `capability_gate` reads `capabilities.yaml` first; new `_open_ledger` finds a ledger through the resolved store (absorbs part 1 of `2026-09-15-make-the-capability-gate-honor-a-configured-ledger`); every store or registry failure becomes a problem line. Also the item's own bookkeeping: new capability seeded `Missing`, the item's `capabilities.yaml`. | C11, C12 (store half), C13 (own ledger) |
| 2 | `41174f32` | `route_capability_path` and `Route`: rule 1 (an `extends` alias wins), rule 2 (declared child → child's ledger), rule 3 (own ledger, or refused on a node with none). Child problems name the child. `test_complete_gate_work_only_node_unaffected` becomes `…_refuses_an_unqualified_path`. | C1 (minus remedy), C3-C6, C9, C10, C12 (child half), C13 (child), C15, C16, C18 |
| 3 | `fbde63ef` | Ambiguity: a child id that is also a namespace in the node's resolved view (`list_all(namespace=…)`, inherited entries included) is refused, covering the redirection case. | C17 |
| 4 | `34be6162` | `removed:` stays local-only: a path qualified by an `extends` alias of the routed ledger is refused, for the child and for the node itself. | C7, C8 |
| 5 | `b5e09659` | `tcw work complete`'s remedy line and discard hint say to reconcile a child-qualified path inside the child (`_CHILD_PATH_HINT` in `tcw/work/cli.py`). | C1 (remedy), C12 (hint) |
| 6 | `748e3dcb` | Tests only: a child in its own git repository; a child ledger declared by `capabilities.repository`, provisioned and not. No code change needed. | C14 |
| 7 | `4236ca00` | Tests only: a child flip on the `--worktree` branch counts after merge-back; `reconcile --complete-when-ready` refuses on a still-Missing child path. No code change needed. | C2, C19 |
| 8 | `6ab2b1d0` | Documentation Sync and ledger records (below). | C21 |

C20: the existing gate tests pass throughout (see Test result).

### Documentation Sync (Task 8)

- Updated: `docs/guide/work.md`, `docs/guide/taxonomy-and-capabilities.md`,
  `docs/guide/multi-repo.md`, `skills/capabilities/SKILL.md`,
  `skills/work/references/cross-node-deltas.md`,
  `docs/release-notes/upcoming.md` (including the completions that may now be
  refused), `docs/changelogs/upcoming.md`.
- Checked, no change: `README.md` and `skills/work/SKILL.md` (neither describes the
  gate's rules).
- Not fired: `docs/guide/jira.md`, `skills/configure/references/*` (no
  configuration key added or changed).
- Ledger: `work/declare-capability-changes-in-a-child-nodes-ledger` flipped to
  `Supported`; the bodies of `work/complete-a-work-item` and
  `skills/capabilities` mention the child-qualified form. `tcw capabilities
  check` and `tcw validate` both clean. `capability_gate` on this item returns no
  problems.

## Mutation checks

Every new assertion was broken on purpose and seen to fail for the named reason,
then restored (`git diff` clean against the committed code after each):

- Task 1: literal `docs/capabilities` test (configured-path test red); store
  failure re-raised (refusal, discard, and bad-registry tests red); store opened
  before the sidecar is read (the four "nothing declared / store broken" tests
  red).
- Task 2: child rule placed before the inheritance rule (C15, C16 red); no
  refusal for an unqualified path on a ledgerless node (C10, C12, the updated
  `test_work.py` test red); child name dropped from messages (six tests red); a
  child with no ledger treated as having one (C9 red); own-store failure passing
  (C18 and others red).
- Task 3: namespace check limited to local capabilities (redirection case red);
  no ambiguity check (both C17 tests red).
- Task 4: `removed:` using the resolved view instead of `get_local` (C7 red); no
  inherited-removal refusal (both C8 tests red).
- Task 5: discard hint without the child sentence (red); old remedy sentence kept
  alongside the new one (red, via the absent-assertion).
- Task 6: literal `docs/capabilities` (provisioned-repository test red); store
  failure read as "no ledger" (unprovisioned test red); child ledger opened at the
  item's node (all three red).
- Task 7: gate run before merge-back (C2 red); child routes skipped (C19 red).

## Verification against the real layout

Run read-only against `/Users/brian/Projects/proposit-orchestration/proposit-app`
(root node `proposit-app-repo`, no ledger, children `proposit-shared`,
`proposit-server`, `proposit-mobile` — the spec's assumption holds). Because that
node's board lives in the orchestration repository, a scratch item would have
written there, so the gate was called directly on an existing item with an
in-memory `capabilities` value instead of running `tcw work complete`. Result:
`changed:` on a real `proposit-shared/…` path and on a `proposit-server/…` path the
server inherits both passed; `new:` on a `proposit-shared/…` path still reading
`Missing` was refused naming `proposit-shared`; an unqualified path and an unknown
prefix were refused listing the three children. Nothing was written in either
repository.

## Test result

Full suite, run without a git identity as CI does
(`GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null pytest -q -p no:cacheprovider`
from the worktree, through the private venv), at commit `6ab2b1d0`:

```
3918 passed in 1196.78s (0:19:56)
```

## Folded in at verify

Findings from the verifier and the adversarial review, each fixed in the
worktree as a `tcw work(verify):` commit:

| Commit | Finding | Fix | Proof |
|---|---|---|---|
| `c59bdbac` | A malformed `meta.yaml` anywhere in a ledger a path reads (for example one the ambiguity check lists) raised `yaml.YAMLError` out of the gate, blocking even a discard. | Each path's check catches `ValueError` and `yaml.YAMLError` as that path's problem; `_open_ledger` treats `yaml.YAMLError` as an opening failure. | `test_a_malformed_meta_yaml_is_a_problem_line_not_a_crash`: done refuses with a problem line, wontfix warns and discards. Mutation: catching only `ValueError` turns it red. |
| `fc1cfb5f` | The remedy line did not name the owning child (C1), and the child sentence printed even when no path was child-qualified. | New `child_path_owners` names each child a declared path is qualified by, with where it is (`kid (packages/kid)`, or `not in this checkout`); the CLI's hint is empty when there are none. | C1's test asserts the named hint; `test_the_child_hint_is_printed_only_for_child_qualified_paths`. Mutations: hint always printed, owners not named, unreachable label changed — each red. |
| `fc1cfb5f` | The discard test's docstring called its `ghost/` path a C9 case; it is a C10 (unqualified) case. | Docstring corrected, and a real C9 discard test added (a child with no ledger, then one not in the checkout: both warn only). | `test_a_discard_only_warns_about_a_child_that_cannot_be_checked`. |
| `15f5d8a1` | Release notes missed two completions that may now be refused. | Added: a ledger at `capabilities.path` / `capabilities.repository` is now checked; a node whose own ledger is declared but not provisioned refuses every declared path. | Read in `docs/release-notes/upcoming.md`. |

After the fold-ins, the gate tests plus `tests/test_work.py` (with
`test_capabilities_rm.py`, `test_capabilities_sidecar.py`,
`test_epic_completable.py` and `test_recursion.py`), run with no git identity:

```
369 passed in 124.60s (0:02:04)
```

The full-suite result above predates the fold-ins; the full suite was not rerun
after them.

## What the plan or spec got wrong

- **Plan, Task 1, C12:** it said a declared path on a node with a broken
  `capabilities.path` "raises out of the gate" today. It did not: the old gate saw
  no `docs/capabilities` and passed silently. An exception escaped only when the
  node did have `docs/capabilities` and its `connected-projects` was invalid. The
  tests cover both; the claim in the plan was wrong.
- **Plan, C11 (invalid `connected-projects`):** the CLI refuses to run at all on
  such a node, before the gate, so that case is tested by calling
  `capability_gate` directly rather than through `tcw work complete`.
- **Plan, Task 5:** it asked to assert the old discard hint absent, but the hint
  was extended, not replaced, so its old text is still a prefix of the new one.
  The test asserts the old line *ending* there is absent instead.
- **Plan, fixtures:** the `_graph(kid_ledger="repository")` axis was not added to
  the shared fixture; the repository declaration needs a remote built in
  `tmp_path`, so Task 6 declares it with its own helper
  (`_declare_kid_ledger_repository`, reusing `_remote_with_tree` from
  `tests/test_store_provisioning.py`).
- **Plan, Task 7 (C2):** the flip on the work branch is made by editing the
  worktree copy's `meta.yaml` directly rather than through `FsCapabilitiesStore`
  opened on the worktree copy of the child, to keep the test about the gate's
  ordering rather than about opening a child node inside a linked worktree.
- **Plan, Verification 1:** it expected to run `tcw work complete` on a scratch
  item and `tcw work drop` it. That would have written into the orchestration
  repository, so it was done as a direct, read-only gate call (above).
- **Some tests passed on first run** (C7, C16, C18, and the Task 6 and 7 tests),
  because the behavior was already true after an earlier task or before this
  change. Each was mutation-checked as listed above instead.

## Notes

- **Release notes conflict likely.** `docs/release-notes/upcoming.md` said
  "Nothing else changed" about v2.5.1; this item changed that sentence to "together
  with the changes below". Sibling v2.5.1 items will probably touch the same lines,
  so the batch merge needs one reconciled intro.
- **Combined review still owed** for `tcw/work/recursion.py` and
  `tcw/work/cli.py` with the other v2.5.1 items. This item did not edit
  `tcw/store/fs.py` or `tcw/validate.py`.
- **Follow-ups not done here (from the spec's non-goals):** `tcw capabilities
  show/set` accepting child-qualified paths at a node with no ledger; reaching
  grandchildren through a routing node (#30); the early sidecar check (#27), which
  should call `route_capability_path`.
- The CLAUDE.md rule against driving the lifecycle with `tcw` while `tcw/` is
  being edited was respected: the only `tcw` commands run from the worktree after
  editing began were `tcw capabilities set`, `check` and `validate`, not lifecycle
  transitions; the lead runs those.
