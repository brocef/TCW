# Refined outcome: gitignore resolved work folders at init by default

Accepted on evidence, under the user's standing instruction to finish the item
and cut a patch release. No separate acceptance conversation was held.

## Acceptance criteria

1. **Rules written on a fresh node** — `test_init_ignores_resolved_work_folders`
   asserts the four rules, `check-ignore` on an item folder, and `check-ignore`
   *not* matching `.gitkeep`. Green.
2. **Idempotent** — same test runs init twice and asserts each rule appears once.
   Green.
3. **`taxonomy`-only init writes no `.gitignore`** —
   `test_init_without_work_writes_no_gitignore`. Green.
4. **Pre-existing `.gitignore` content survives** — same test seeds
   `__pycache__/` and asserts it is still the first line. Green.
5. **Completion still untracks rather than moves** — the earlier item's coverage
   passes unchanged, and the whole test corpus now runs against nodes that ignore
   their resolved folders by default, which is what exposed the two defects
   recorded in `outcome.md`.
6. **This repo** — `git ls-files docs/work/{completed,discarded}` lists exactly
   the two `.gitkeep` files; `check-ignore` matches `completed/foo` and does not
   match `completed/.gitkeep`.
7. **Suite and validate** — `pytest`: 1171 passed, 1 failed; the one failure was
   the pre-existing `tcw-work` router line-budget breach from `69eeb0a`, since
   fixed in `044624d`, and the parity file is green. `tcw validate` exits 0;
   `tcw capabilities check` is OK.
8. **Capabilities** — `cli/scaffold-the-doc-trees` and
   `work/keep-resolved-work-out-of-git` reworded, both `Supported`.

## Notes for later

No opt-out flag was added, by design: the `.gitignore` lines are the knob. If
users turn out to re-run `tcw work init` on nodes that deliberately track their
resolved work, the rules will come back silently — that is the one failure mode
worth watching.
