# Outcome — Add a tcw-work-create skill that checks for overlap before creating a work item

`<base>` is `8b870e96`: the `tcw work start … (worktree)` commit on branch
`work/2026-09-15-add-a-tcw-work-create-skill-that-checks-for-overlap-before-creating-a-work-item`.

## What shipped, task by task

| Task | Commit | What |
| --- | --- | --- |
| 1 | `b1e50b54` | `skills/tcw-work-create/SKILL.md` and `references/find-overlap.md`; the Codex manifest now says sixteen skills and names the new skill; eval case B13; a B13 `CASE_ROUTING` row, with an optional text selector in `_case_routing_assertion` |
| 2 | `6a0ad902` | Pointers from `tcw-work`'s router, `tcw-commands-plan-work`, and `tcw-configure`'s `docs-sync.md` |
| 3 | `ce323acc`, `85407a57` | Taxonomy Feature `tcw-work-create-skill`, capability `skills/tcw-work-create` (`cap-43570a`), and this item's `capabilities.yaml` |
| 4 | `9ce322ac` | README (sixteen skills, a core-table row), `docs/changelogs/upcoming.md`, `docs/release-notes/upcoming.md` |
| 5 | `37037769`, `5df02e41` | The by-hand run found a defect in the step 3 table. Fixed in the skill, then in the spec |

## Tests

- **Baseline** at `<base>`, bare `pytest` from the worktree root: **3362 passed**
  (16m41s).
- **Task 1 commit** `b1e50b54`, bare `pytest` in a separate detached checkout, so
  later edits could not affect it: **3366 passed** (17m47s).
- **Final** `5df02e41`, bare `pytest` from the worktree root: **3368 passed**
  (18m20s).
- **Tasks 2–4** were each checked with the tests their plan task names, not a
  full run. See "What the plan got wrong".
- **Red first.** The B13 routing test failed with `StopIteration` before B13
  existed. `test_the_codex_description_counts_the_skills_it_ships` failed once
  the skill folder existed without the manifest edit.
- **Mutation checks**, each restored afterwards:
  1. B13's text and the row's selector both set to `tcw-work`: red, with
     "B13 tool_input_contains passed for a run that only opened
     /p/skills/tcw-work/SKILL.md".
  2. The row's selector removed: red, with
     "B13 has 2 tool_input_contains assertions".
  3. `find-overlap.md` removed: the AC 3 loop reports all 7 strings missing.

## Acceptance criteria

1. **Met.** The frontmatter parses; `description` plus `when_to_use` is 864
   characters; all four `when_to_use` strings are present.
2. **Met.** Every string, one `grep -F` each; nothing missing, rechecked after
   the `37037769` fix.
3. **Met.** All seven strings are present in `find-overlap.md`.
4. **Met.** `tcw-work/SKILL.md` names the skill. Body is 60/60 lines;
   `tests/test_skill_lifecycle_parity.py` passes.
5. **Met.** Both files name the skill; the `tcw work new "<deferred item>"` count
   is 0; `tests/test_skill_path_pointers.py` passes.
6. **Met.** README contains "Sixteen skills" and the skill; the Codex manifest
   contains "sixteen skills".
7. **Met.** B13 carries its four assertions. The eval and manifest tests pass.
8. **Partly met.**
   - `tcw taxonomy show` and `tcw capabilities show` resolve, and
     `Feature: tcw-work-create-skill` is set.
   - `tcw capabilities check` prints `capabilities OK`.
   - `git diff --stat <base> -- tcw/ agents/` is empty.
   - Bare `pytest` is green.
   - **`tcw validate` exits 1 in the worktree**, over a problem that has nothing
     to do with this change (see "What the plan got wrong", item 5). It exits 0
     in the primary checkout.
9. **Met, with (c) run on the eval fixture.** See the by-hand run below.
10. **Open, not verified**, as planned. Both checks belong to
    `2026-09-11-refine-the-plugin-skills-and-lifecycle-prompts-against-the-eval-findings`:
    - B13 passing with the skill and failing `files_changed_exactly` without it,
      once `2026-09-15-eval-runs-under-this-checkout-grade-and-behave-wrongly`
      lands;
    - the next backlog audit finding no duplicate pair created after release.

    **Whether agents invoke this skill on their own has not been tested.**

## By-hand run

Every run followed `skills/tcw-work-create/SKILL.md` from inside the worktree
and stopped before its first write.

- **(a) Step 0.** `git rev-parse --git-dir` printed
  `/Users/brian/Projects/TCW/.git/worktrees/2026-09-15-add-…`;
  `--git-common-dir` printed `/Users/brian/Projects/TCW/.git`. They differ, so
  this is a linked worktree. The first `worktree` line of
  `git worktree list --porcelain` is `/Users/brian/Projects/TCW`, and every
  `tcw` command below ran there.
- **(b)** Idea: "Fan the backlog audit out across every connected project's
  work root."
  ```
  2026-09-01-fan-the-backlog-audit-out-across-every-connected-work-root | covers | backlog i | intake heading "Fan the backlog audit out across every connected work root"
  searched: tcw work list · tcw work inbox list · tcw work list --all
  ```
  It is a backlog item with no spec, and the idea adds nothing. Outcome:
  `already tracked 2026-09-01-fan-the-backlog-audit-out-across-every-connected-work-root`.
- **(c) Not runnable on this board.** `tcw work inbox list` in the primary
  checkout printed nothing, because another session had triaged all 23 entries
  since planning. It was run instead on an eval fixture seeded outside the
  checkout (`python evals/seed_fixture.py <scratch>`), using B13's idea: slow
  sign-in for accounts with many invoices, starting after Tuesday's invoice
  import.
  ```
  slow-login.md | covers | inbox | "Signing in takes about eight seconds for accounts with a lot of invoices"
  searched: tcw work list · tcw work inbox list · tcw work list --all
  ```
  The entry does not mention the import, so there is new information. Outcome:
  `amended slow-login.md`. Nothing was appended, and the fixture's
  `git status` was unchanged.
- **(d)** Idea: "Rewrite the README to a new outline."
  `2026-09-15-rewrite-the-readme-to-a-new-outline` is `active`.
  ```
  2026-09-15-rewrite-the-readme-to-a-new-outline | covers | active iRSP | request heading "Rewrite the README to a new outline"
  ```
  **The first pass gave `already tracked`, which is wrong.** The table checked
  "adds nothing" before status, so active work with nothing new never reached the
  `already in progress` row. The user decided that active work is always
  reported as in progress, so the rows were reordered (`37037769`, spec
  `5df02e41`). On re-run the outcome is
  `already in progress 2026-09-15-rewrite-the-readme-to-a-new-outline`.
- **(e)** Idea: "Add a dark-mode colour theme to `tcw serve`'s web viewer."
  `tcw work list --all | grep -i dark` found nothing. A body grep found only this
  item's own `plan.md`, which quotes the idea as an example; that is a passing
  mention, not a match. Result: `no overlap`, then
  `searched: tcw work list · tcw work inbox list · tcw work list --all`.
  Outcome: `created`, but nothing was created.
- **(f)** The same idea as (b), Delegated, with a brief holding only the idea.
  Step 1 understood it; the step 2 line is the same as (b). No question applies,
  since nothing is created or revised. Outcome: `already tracked …`, with no
  `needs decision`.
- **Status snapshots.**
  - The worktree was clean before and after, apart from the `37037769` fix,
    which was committed.
  - The primary checkout's `git status --porcelain` did change during the run.
    The changes are new untracked `initial-request.md` files for other backlog
    items, written by the session triaging the inbox. Every command run there
    was a read: `tcw work list`, `inbox list`, `path`, `show`, `grep`, `head`.

## What the plan or spec got wrong

1. **The step 3 table put "adds nothing" above the active/review row** (spec D1
   and the skill). Found by by-hand run (d); fixed in the skill and the spec.
2. **Mutation check 1 was wrong as written.** Changing only B13's text makes
   the new selector find no assertion, which fails for a different reason.
   Checking the wrong-route property needs the row's selector changed too.
3. **The skill body is 156 lines (168 after the rework)**, over the plan's "under 150". Nothing enforces
   it. The rest is the seven-row, four-mode table and the body template; cutting
   either would remove content an agent needs.
4. **The plan described the routing row as a 4-tuple with a fourth field that
   defaults to None.** The existing rows stay 4-tuples and the B13 row carries a
   fifth element (the selector text), padded with `(*row, None)[:5]` in the
   parametrize call, and the parametrize ids are unchanged.
5. **`tcw validate` fails in any checkout without the primary's untracked
   files, and the plan assumed it would exit 0.**
   - The failing link is in
     `docs/work/backlog/2026-09-09-distinguish-a-blank-artifact-from-an-absent-one-in-the-web-ui/initial-request.md`,
     pointing at
     `tcw://W/2026-08-18-reconcile-read-artifact-with-the-canonical-presence-rule`.
   - That item lives in `docs/work/completed/`, which `.gitignore:29` keeps out
     of git, and it has no tombstone in `docs/work/graveyard.yaml`. It therefore
     resolves only in the primary checkout.
   - It fails the same way at `b1e50b54`, and it predates this item.
   - **It is not fixed here.** It is a candidate follow-up, and the new skill's
     first real use.
6. **"Every commit leaves bare pytest green"** was checked with full runs at
   `<base>`, `b1e50b54` and `5df02e41`, not after every commit. A full run takes
   about 18 minutes. Tasks 2–4 changed only skill prose, ledger entries and
   documents, and the tests that read those files were run for each.
7. **(c) could not use this board's inbox**, which emptied during
   implementation. The eval fixture has the same entry shape B13 uses.
8. **The plan did not name the capability's `Planning doc` field.** It was set to
   this item's slug, matching the other skill capabilities.

## Notes

- Documentation Sync was evaluated with the `documentation-sync` skill over
  `git diff <base>`. The README, release-notes and changelog entries fired and
  were updated in `9ce322ac`. The `[Skill-Driven-Component]` and
  `[Configuration-Key-Change]` entries did not fire.
- **Follow-ups to file at closeout**, with the new skill, from the primary
  checkout:
  - no CLI verb adds or amends a work inbox entry (spec Risks);
  - `tcw validate` fails outside the primary checkout on a link to a gitignored
    completed item that has no tombstone (item 5 above).
- `bllm` was unavailable (disabled for maintenance) during the spec review. Not
  reported to the llama inbox, because it was a deliberate maintenance state,
  not a fault.

## Rework pass (after `rework.md`, 2026-09-15)

The first pass was rejected at verify. `rework.md` lists six findings, A–F. All
six are fixed in `ec821671` (the skill and the release note), and spec D1 now
matches (`ab6e4c3b`).

- **A — staged commits.**
  - Step 4's commit is now `git -C <store folder> add -- <absolute paths>`,
    then `git -C <store folder> commit -m "…" -- <absolute paths>`.
  - The old command also had no `-m`, which would have opened an editor. The
    verifier did not name that gap; the fix covers it.
  - Step 1's inbox entry now commits too.
- **B — step 0's reach.** Every `tcw` and `git` command in steps 1–4 runs from
  the primary checkout. That now names step 1's inbox entry and the strict-mode
  fallback.
- **C — delegated blockers.** A delegated run whose brief is silent, or
  describes a blocker that would need confirming, creates nothing. It returns
  `needs decision: blockers`, with step 2's `blocks` lines as candidates. The
  brief gained a blockers field.
- **D — smaller gaps.**
  - Delegated references and origin fall back to "none given in the brief".
  - `revised` is reported once every revised artifact exists, which may be the
    spec alone.
  - A discarded match's resolution goes in the reason part of the outcome line.
  - A folder entry's file is the one `tcw work inbox show` prints as its body.
- **E — permissions.** `Bash(grep *)` added to `allowed-tools`, and no
  `$(...)` substitution remains in the skill (`grep -c '\$('` prints 0).
- **F — release note.** It now says that when someone is already working on
  the matching item, the skill tells you and changes nothing.

### Write-path check (the rework's new by-hand run)

This ran in a freshly seeded eval fixture outside the checkout
(`python evals/seed_fixture.py <scratch>/fixture2`), with the store at
`<fixture>/docs/work`. It followed the fixed step 4 commit text exactly.
`git status --porcelain` printed nothing after each step.

- **(g) Created item.** `tcw work new "Paginate the invoice list" --tag cli`,
  with the body piped in, then the two-line add/commit on `tcw work path <slug>`.
  Committed as `ac06366`.
- **(h) Raw inbox entry.** `export-times-out.md` was written under
  `tcw work inbox path`, then add/commit. Committed as `db0947f`. This is the
  case that failed before the fix.
- **(i) Append to a tracked entry.** A `## Added 2026-09-15` section was
  appended to `slow-login.md`, then add/commit. Committed as `6653818`.
  `tcw work inbox show slow-login` prints the added section.

### Re-checked

- **AC 1:** the Python check prints `AC1 ok`.
- **AC 2:** no string missing.
- **Targeted tests:** 192 passed.
- **`tcw capabilities check`:** `capabilities OK`.
- **Bare `pytest` at `ab6e4c3b`:** **3368 passed** (12m37s).
