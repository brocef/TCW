# Outcome: Re-anchor a relative work.path at the node's counterpart inside the main worktree

Shipped. The reporter's command now returns the same store from a linked
worktree as from the primary checkout, and the fix reaches all three components
rather than only `work`.

## What shipped, task by task

| Task | Commit | What landed |
| --- | --- | --- |
| 1 — fixture + regression guards | `2a7bdb7` | `nested_node_worktree` and `TestWorktreeWorkPathUnchanged` (4 tests), passing on the unmodified tree |
| 2 — the anchoring change | `c37ef67` | `FsWorkStore._local_root` gated on escape and anchored at the node's counterpart, plus `TestWorktreeWorkPathReAnchoring` (4 tests) |
| 2b — the tree stores | `c9aa44e` | `anchor_configured_path` extracted; both `_local_root` hooks route through it; `TestWorktreeTreeStorePathReAnchoring` (4 tests, parametrized over taxonomy and capabilities) |
| — | `19e3caf` | Spec sweep corrected, plan non-goal withdrawn (see below) |
| 3 — capability ledger | `19e3caf` | `cli/run-from-a-git-worktree` and `work/configure-the-work-store-location` amended |
| 4 — documentation sync | `08358fb` | README (2 passages), changelog, release notes |

## Test result

`pytest -q -p no:randomly`: **2175 passed, 5 failed.**

All five fail identically on the rebase base with this branch's changes stashed,
and all five are artifacts of this container rather than defects: three assert a
`PermissionError` that never raises because the suite runs as root
(`test_an_unwritable_target_reports_and_prints_no_path`,
`test_atomic_write_preserves_prior_on_failure`,
`test_atomic_write_temp_cleanup_on_failure`), one reads a wheel that was never
built (`test_the_prompts_are_in_the_built_wheel`), and one is
`test_invalid_utf8_is_replaced_rather_than_fatal`. A sixth,
`test_generate_hook.py::test_a_grandchild_does_not_survive_the_timeout`, failed
once under full-suite load and passed on every isolated re-run and on the final
full run; it is a subprocess-timing flake in a path this change does not touch.

Every new test was watched fail before the code that makes it pass. The four
work-store tests were falsified by stashing `tcw/store/fs.py`; the four
tree-store tests by restoring the previous `FsTreeStore._local_root` body.

### Acceptance criteria

| # | Criterion | Covered by |
| --- | --- | --- |
| 1 | nested node, escaping path, same store from both checkouts | `test_nested_node_escaping_path_resolves_to_the_same_store` |
| 2 | nested node, inside path, resolves to the worktree's own store | `test_nested_node_inside_path_stays_with_the_worktree` |
| 3 | root node, inside path, matches the default | `test_root_node_inside_path_matches_the_default` |
| 4 | root node, escaping path, unchanged | `test_escaping_path_on_a_root_node_already_agreed` |
| 5 | absolute and default paths unchanged everywhere | `test_absolute_work_path_is_never_re_anchored`, `test_default_store_stays_with_its_own_checkout`, `…_at_repo_root` |
| 6 | `monorepo_worktree` still passes | full run of `tests/test_environment_hardness.py` (81 passed) |
| 7 | full suite | above |

### Manual verification (plan's Verification section)

Built the reporter's shape exactly — `proposit-app/apps/server` as a nested
node, store at `docs/proposit-server/work` outside the repository, a linked
worktree at `worktrees/auth-screens` — and ran his command rather than the
function:

- primary checkout and linked worktree both print
  `…/repro/docs/proposit-server/work`;
- `tcw work new` from inside the worktree creates the item in that external
  store, and `tcw work list` from the primary checkout sees it;
- with `anchor_configured_path` reverted to `return anchors[1]`, the same
  fixture reproduces his error verbatim — `tcw work: no tcw work node here — run
  tcw init in the project folder.`, exit 1.

The `grep -n "_local_root" tcw/` check the plan asked for is what found the
second copy; see below.

## What the plan and spec got wrong

**The spec's sweep was wrong, and the reporter was right.** It concluded there
was one `_local_root` and that "the tree store has no configured path to
resolve." That held for v1.1.0, the tree I swept. The reporter filed against
1.2.0, which had already generalized store resolution into a shared
`resolve_store` ladder — so `FsTreeStore._local_root` exists, serves taxonomy
and capabilities, and carried a character-identical copy of both defects. It
arrived here when the branch rebased onto `main` mid-implementation. Fixing only
the work store would have left the other two components broken in exactly the
way the work store had just been repaired. The spec's Sweep now records the
correction rather than the original claim.

**The plan's non-goal was withdrawn.** It said not to extract the shared
counterpart expression, "if a fifth appears, that is the moment." A second
identical copy of the whole rule appeared, so the moment arrived: extracting
`anchor_configured_path` became the fix rather than a tidy-up beside it. Two
copies where only one gets fixed is the drift `resolve_store` exists to prevent.

**The fixture needed something the plan did not anticipate.** An external store
must live in a git repository — `_open_at` refuses one that is not, because it
has to know which repository owns the store's commits. The first end-to-end test
failed on that, not on the path computation. `nested_node_worktree` now git-inits
the external store's own repo.

**A deviation from Task 3, decided against the plan.** The plan said to set each
amended capability's Planning doc to this item's slug. I set it and then put it
back. Both entries stay Supported and neither is introduced by this item — it
corrects the code to match what they already promised — so repointing the field
would erase the record of the items that did introduce them, and would read as
though this item delivered worktree support. The originating slugs stand.

## Notes

**The public record was corrected.** My first comment on issue #26 told the
reporter there was only one `_local_root`, which was true of the tree I checked
and false of the one he filed against. A correction is posted on the issue
naming the mistake and describing the wider fix, rather than leaving the earlier
comment standing.

**A behaviour change rides along with the bug fix.** A relative
`<component>.path` that stays inside the checkout used to resolve to the primary
checkout's store from inside a worktree; it now belongs to the worktree, like
the default always has. That is the second half of the same defect — it
contradicted `cli/run-from-a-git-worktree`, which documented the opposite — but
it is a change someone could notice, and the release notes say so in plain
language.

**`tcw validate` reports 4 pre-existing problems** on this tree, identical with
the branch stashed: dangling `tcw://W/` references to two items that no longer
exist under those slugs. Untouched here, and a live instance of what issue #25
reports.
