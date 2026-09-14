# Outcome — Restructure TCW's skills: setup and configure skills, command and extras skills, and no slash commands

`<base>` (the commit that last touched `plan.md`): `fe735d94`. The branch started
from `e73b0a6c` (item A completed); the item was started at `8a548c8a`. The
tracker item `2026-09-12-configure-an-external-tracker-and-read-its-tickets` had
already completed, so task 6 moved its final text.

## What shipped, task by task

| Task | Commit | What |
| --- | --- | --- |
| start | `8a548c8a` | `tcw work start` |
| 1 | `35bd788e` | The five per-stage skills deleted; `tcw-work-stage`'s fallback says to use the stage and item named in the request in place of `$stage` and `$item`; A1–A4 and A8 invoke `tcw-work-stage`; the `request` exclusion moved into `PARTIAL["tcw-work-stage"]`; the capability paragraph reworded; the per-stage parity tests removed |
| 2 | `120841ad` | `tcw-extras-autonomous-work`, `tcw-extras-triage-issues`, `tcw-extras-report`, and every reference |
| 3 | `226f5ba0`, `4a867aed` | The four `tcw-commands-*` skills: a move-plus-frontmatter commit, then body edits and wiring |
| 4 | `4b0f0e38` | `setup.md` → `tcw-configure/references/docs-sync.md` (R100) with pointer updates |
| 5 | `f7c2935d` | `docs-sync.md` retitled, pointers name `documentation-sync`; that skill's description reworded, with a test |
| 6 | `54079182`, `ec98881b`, `e222b650`, `057592ea` | `work.md`, `tracker.md`, `stores.md`, `projects.md`, one commit each |
| 7 | `b63ac309` | `tcw-configure` router; router tests; `tests/test_skill_path_pointers.py`; B11 with grading tests; `Configuration-Key-Change` entry |
| 8 | `5965d329` | Both `init.md` → `tcw-setup/references/` (R100) with pointer updates |
| 9 | `cdbce915` | `taxonomy.md` inheritance step and `capabilities.md` pointer |
| 10 | `7947bc0e` | `tcw-setup` router, `install.md`, `project.md`; B12; B4 and B8 routing checks; `tcw-taxonomy` description; capability and `session_bootstrap.sh` comments |
| 11 | `9af531b1` | `tcw-plugin` and `commands/` removed; deleted-names and no-commands tests; `cut-version.md`; B5 retargeted |
| 12 | `cad2a907` | Notes on related open items |
| 13 | `b6804a4d` | README |
| 14 | `630a45c7` | Release notes |
| 15 | `ba2e4e73` | Changelog |
| review | `f6528984`, `15ecaf50`, `d8738f65` | Review fixes, changelog line, inbox note (see Review) |

Skill counts, confirmed by `tests/test_plugin_manifests.py` at each commit: 10
after task 1, 10 after task 2, 14 after task 3, 15 after task 7, 16 after task
10, 15 after task 11.

## Tests

- **Full bare `pytest` at `ba2e4e73`** (after the last code task and the
  documentation pass): **2850 passed** in 12 min 39 s.
- **Full bare `pytest` at `d8738f65`** (after the review fixes, the last code
  change): **2850 passed** in 14 min 29 s. Only `outcome.md` changed after it.
- **Every intermediate commit was checked with partial runs only**: the test
  files each task touches or could break (`test_skill_lifecycle_parity`,
  `test_plugin_manifests`, `test_eval_coverage`, `test_eval_grading`,
  `test_eval_runner`, `test_eval_fixture`, `test_documented_cli_surface`,
  `test_documentation_sync_wiring`, `test_documentation_config`,
  `test_repo_lifecycle`, `test_skill_path_pointers`, `test_skill_flow`), all
  green. Nothing under `tcw/` changed.
- `tcw validate` prints `validate OK`; `tcw capabilities check` prints
  `capabilities OK`.
- `python -m evals.run_evals --axis b --dry-run --out <scratchpad>` lists B11
  and B12 (B12 with `fixture: bare`). No paid run.

**Tests written first and watched fail**, each for the reason named:

- `test_the_manual_fallback_says_where_the_arguments_come_from`: the fallback
  had no such sentence.
- Manifest count and coverage tests went red after each rename or move, naming
  the unnamed or uncovered skills.
- `test_skill_files_exist`, `test_commands_route_into_the_skill`: the moved
  `docs-sync.md` did not exist yet.
- `test_the_description_is_a_usage_trigger_not_a_setup_one`: the description
  said "declares".
- The router tests for `tcw-configure` and `tcw-setup`: no such skill.
- `test_this_repos_documentation_entries_parse`: no `Configuration-Key-Change`
  entry.
- `test_a_case_routing_assertion_fails_the_wrong_route[...]` for B11, B12, B4,
  B8: no such case or assertion.
- `test_the_taxonomy_skill_does_not_advertise_setup_or_federation`: it said
  seeding, bootstrapping and federating.
- `test_no_live_route_names_a_removed_skill_or_command` and
  `test_the_plugin_ships_no_slash_commands`: 15 red before the deletions, each
  listing the files still naming the removed name.

## Mutation checks

Each broke what the test claims to observe, was watched go red for that reason,
and was restored byte for byte.

| Broken | Red test | Why |
| --- | --- | --- |
| a `tcw-configure/references/` path appended to `tcw-work`'s `hooks.md` | `test_only_the_owning_skill_names_its_reference_paths[tcw-configure]` | names `hooks.md` |
| 40 blank lines in each router | `test_a_routing_skill_stays_within_the_line_budget` | "body is 70 / 72 lines" |
| a link target renamed | `test_a_routing_skill_links_every_reference_and_every_link_resolves` | lists the missing file |
| the only link to `tracker.md` made plain text | same test | "never links: tracker.md" |
| `$ARGUMENTS`, then an injected `` !` `` command, added | `test_a_routing_skill_depends_on_no_claude_only_mechanism` | shows the string |
| "the `tcw-setup` skill" / "the `tcw-configure` skill" unnamed (and, before the fix, the first router's line wrap split it) | `test_a_routing_skill_names_the_other_one` | "never names" |
| B11 contains text → `references/`; B11 absent text → `tcw-configure/references/` | `test_a_case_routing_assertion_fails_the_wrong_route[B11-*]` | "passed for a run that only opened …tcw-setup/references/project.md" |
| B12 contains → `references/`; B12 absent → `tcw-setup/references/` | `[B12-*]` | "passed for a run that only opened …docs-sync.md" |
| B4 and B8 absent text → `tcw-taxonomy/` | `[B4-*]`, `[B8-*]` | "passed for a run that only opened …project.md" |
| "seeding a new taxonomy" added to `tcw-taxonomy`'s `when_to_use` | `test_the_taxonomy_skill_does_not_advertise_setup_or_federation` | `['seed']` |
| `/tcw-plan-work` added to `commands.md`; `autonomous-work` put back in README | `test_no_live_route_names_a_removed_skill_or_command[...]` | names the file |
| `commands` key added to the Claude manifest; a `commands/x.md` created | `test_the_plugin_ships_no_slash_commands` | "still has a commands key" / "commands/ still exists" |

Deleting the `install.md` table row in `tcw-setup` does **not** turn the link
test red, correctly: the first-time order list links it too.

## Acceptance criteria

Checked by hand on the tree at `ba2e4e73`, and ACs 6–10, 12–14 and 16–18 again
after the review fixes:

1. **AC 1–3.** `ls skills` lists exactly the fifteen names; `commands/`,
   `skills/tcw-plugin/`, both axis `references/` folders and
   `documentation-sync/references/setup.md` do not exist; no `commands` key.
2. **AC 4, AC 5.** Both `git grep` commands, exactly as the spec writes them,
   print nothing.
3. **AC 6.** Bodies are 32 (`tcw-setup`) and 31 (`tcw-configure`) lines; links
   resolve; no `$ARGUMENTS` or `` !` ``; each names the other. Enforced by tests.
4. **AC 7.** All six redirect rows name "the `tcw-configure` skill".
5. **AC 8, AC 9.** Every required word present; no forbidden word. AC 9 is also
   enforced by tests.
6. **AC 10.** All pointers present; no `## Bootstrap` heading.
7. **AC 11, renames.** R100 for all three moves, in `4b0f0e38` and `5965d329`.
8. **AC 11, partial moves.** The substring check against `fe735d94` passes for
   `hooks.md` → `work.md`, and for `commands.md` 93–100 → `tracker.md` and
   156–162 → `stores.md`. The lines it reports missing are listed below.
9. **AC 12, AC 13.** All strings present; `hooks.md` opens "# How lifecycle
   bindings run"; the default lifecycle README names `tcw-configure`.
10. **AC 14.** Enforced by `tests/test_skill_path_pointers.py`.
11. **AC 15.** `tcw capabilities show` prints neither `tcw-plugin` nor a
    per-stage name; `capabilities OK`.
12. **AC 16.** All four checks hold.
13. **AC 17.** Every bullet holds, with the grading-test bullet narrowed (see
    departures).
14. **AC 18.** `tcw work docs` lists `skills/tcw-configure/references/<document>.md`.
15. **AC 19.** Bare `pytest` passes; `tcw validate` exits 0.

### Moved lines changed

From `skills/tcw-plugin/SKILL.md` (62–115) → `tcw-setup/references/install.md`:

- `**A \`tcw\` that runs is not this skill's problem.** …` → "is not an install
  problem". `tcw-setup` does handle provisioning (in `project.md`), so "not this
  skill's problem" would now be false.
- `the user's own repository rather than anything this skill does. The README's`
  and `_Install → In a cloud environment_ carries the script and the rules it must
  obey.` → the rule is kept in its own words and the README pointer is dropped, as
  spec D3 requires: reference documents never send the agent to the README.

From `skills/tcw-work/references/commands.md` (173–191) →
`tcw-configure/references/projects.md`:

- `**A connected project declares the same way.** An entry under` → "declares a
  repository the way a store does". In `commands.md` "the same way" pointed at
  the store-repository paragraph just above; in `projects.md` nothing precedes it.
- `the same ladder — the project at \`path\` wins when it is here — so a checkout that`
  → "the ladder a store uses", for the same reason.
- `machine. It reaches component stores too, through the rung above: a store whose`
  → "through the rung above" dropped. That rung (another checkout on this disk)
  stayed in `commands.md`.

## What the plan or spec got wrong, and departures

1. **`connected-projects.children` is a mapping, not a list.** Plan task 6 says
   "`children` a list". `tcw/store/project.py` `_relation` requires a mapping from
   project id to entry for both keys; `projects.md` documents that. The spec (D3)
   was already right.
2. **`README.md`'s "In **Codex** (skills only, no slash commands):" also
   changed**, to "In **Codex**:". The spec's line list missed it, and AC 16 forbids
   "slash command" in the README.
3. **Three tracker items have no body document**
   (`2026-09-12-synchronize-…`, `-refuse-local-work-…`, `-surface-an-item-s-…`:
   `state.yaml` only). Writing an `intake.md` or `initial-request.md` by hand would
   change their stage or pretend to be raw input, so their note went on the parent
   epic `2026-08-04-supplement-filesystem-tcw-work-with-an-external-tracker-bridge`.
   The completed tracker item is gitignored and was not edited. A note was also
   added to `2026-09-14-inherit-work-tracker-from-parent-nodes-key-by-key`, which
   adds tracker configuration but postdates the plan.
4. **AC 17's grading-test bullet is narrowed.** B11 and B12 each have grading
   tests for both routing assertions, read from `evals/evals.json`. Their
   `files_changed_exactly` and `validate_exit_zero` assertions are fixture
   predicates, already tested in general by `tests/test_eval_files_changed.py` and
   `tests/test_eval_fixture.py`; no hand-built transcript can fail them, and no
   per-case test was added.
5. **Task 3 is two commits** (move plus frontmatter, then body edits), because
   the plan calls step 1 a "rename commit" and the task also has body edits.
6. **Tests beyond the plan.** The fallback-sentence test (AC 16), the
   `documentation-sync` and `tcw-taxonomy` description tests (AC 9), and a check
   that the Claude manifest has no `commands` key sit beside the planned tests,
   because the plan counts those ACs as covered by the suite.
7. **`tcw-configure` covers `work.lifecycle.artifacts`**, which spec D3's table
   left out although Goal 2 says every key. Added after review.
8. **Where the two `## Bootstrap` sections were**, the pointer lines have their
   own headings ("Starting a taxonomy", "Starting a capabilities ledger") rather
   than sitting under the previous section.
9. **`project.md` uses a project name the user already gave as the ID**, and asks
   only otherwise. Found in review: the non-interactive B12 run would otherwise
   stop to ask.
10. The B11 case was appended one indentation level short and re-indented in
    `7947bc0e`.
11. The spec's `documentation-sync` `SKILL.md` table row for `cut-version.md` is
    reworded in place (task 11), matching the spec.

## Documentation sync

From `tcw work docs` (source: config).

- `README.md` [Public-API] — **fired.** Skill counts and groups, rows for
  `tcw-setup` and `tcw-configure`, the extras table, the command-skills
  paragraph, install and bootstrapping text (tasks 2, 11, 13).
- `docs/release-notes/upcoming.md` [Public-API] — **fired.** A section for
  users of the old names.
- `docs/changelogs/upcoming.md` [Any-Code-Change] — **fired.** Added, Changed and
  Removed entries.
- `skills/<component>/SKILL.md` [Skill-Driven-Component] — **did not fire.** No
  component's CLI surface, model, lifecycle or guardrails changed; the skills are
  this item's subject rather than something that drifted from a changed
  component.
- `skills/tcw-configure/references/<document>.md` [Configuration-Key-Change] —
  **did not fire.** No configuration key was added, removed or changed meaning;
  tasks 5–7 wrote these documents.

## Review

`adversarial-code-reviewer` on `e73b0a6c..ba2e4e73`, with the spec and plan. It
checked nearly every new configuration claim against the CLI source. Verdict:
NOT DONE. Each finding was checked against the repository before acting.

**Belongs to this change**

1. **BLOCKING — no `outcome.md`, so AC 11's changed lines were unrecorded.
   Accepted.** This document; the check found exactly the lines listed above
   (the review counted four; the fix to `projects.md` changed a second line of the
   same paragraph, so there are five).
2. **SIGNIFICANT — `work.md` implied `work.lifecycle.artifacts` is reported as
   unknown. Accepted.** Verified at `tcw/store/base.py:1830`. Fixed in `f6528984`.
3. **SIGNIFICANT — `artifacts` had no `tcw-configure` coverage. Accepted.** A
   routing row and a short section in `work.md` (`f6528984`).
4. **SIGNIFICANT (suspected) — "cross-project operations use only connections
   both sides declare" is unsupported. Accepted, narrowed.** `children()` and
   `parent()` do not filter; `_validate_reciprocity` reports the problem, and
   `require_valid()` (used by `extends_add`, among others in `fs.py`) refuses an
   invalid graph. The sentence now says exactly that.
5. **SIGNIFICANT — "declares the same way … the same ladder" refers to nothing
   in `projects.md`. Accepted.** Reworded and recorded above.
6. **SIGNIFICANT (suspected) — B11 and B12 documents ask the user questions,
   which the coverage note says is why other routes are unmeasured. Accepted,
   narrowed.** `project.md` now takes the ID from a name the user gave. Both
   cases' `note` says an agent that routes correctly and then stops to ask fails
   `files_changed_exactly` or `validate_exit_zero`, so the routing checks must be
   read separately. The documents still ask when the request does not answer.
7. **NOTE — `commands.md` "described below" pointed at moved text. Accepted.**
   Fixed.
8. **NOTE — seed pointer lines under unrelated sections. Accepted.** Headings
   added.
9. **NOTE — `hooks.md` names "a bare stage list" whose meaning moved.
   Accepted.** Pointer added.
10. **NOTE — `project.md`'s "prints `validate OK`" bullet overlaps a declared but
    unprovisioned connected project. Rejected.** The bullet naming "declared but
    not here" comes first, and `tcw validate` also prints a hint in that case; no
    change.
11. **NOTE — `transitions.md` and `commands.md` still say how to set `dod.yaml` and
    `work.publish-transitions`. Rejected.** Spec D4 kept these as behavior text
    with no pointer.
12. **NOTE — `tests/test_documented_cli_surface.py:7` says "workflows that live as
    slash commands". Rejected.** It is a historical explanation of why that test
    exists, not a route.
13. **NOTE — `install.md` omits the PATH-repair rule of the README's cloud
    hook.** Narrowed: recorded here; the paragraph keeps the rule the moved text
    carried, and D3 forbids pointing at the README.
14. **DUPLICATION — "never run `tcw init` to get past a declared store" in three
    places. Rejected.** It is a warning at each point an agent could make the
    mistake, not declaring text, so Goal 6 holds.
15. **QUESTION — `tcw-work`'s `when_to_use` overlaps the `tcw-commands-*`
    skills.** No change. Both reach the same stage documents; the spec kept
    `tcw-work`'s triggers, and routing is measured only by a paid run.
16. **QUESTION — a pointer names "the `tcw-configure` skill's `docs-sync.md`" in
    words, with no path.** No change: that is spec D3's rule, so that routing
    checks see only files an agent actually opened. Whether agents follow it is
    what B11 measures.

**Needs a separate change**, recorded in
`docs/work/inbox/2026-09-14-guards-and-gaps-the-skill-restructure-review-left.md`:
the removed-names test covers only the folders the spec named; nothing checks
that `EXCLUSIONS`/`PARTIAL` keys still ship; `install.md` does not say how to run
the bootstrap script under Codex; `tcw-work-stage`'s `<plugin>` placeholder has
no Codex instruction; small duplication in test helpers.

**Merge note from the review.** On `main`,
`2026-09-12-claim-…` and `2026-09-14-inherit-work-tracker-…` have moved from
`active/` to `review/`. This branch appends a note to each under `active/`; the
merge should follow the rename, but the combined result needs a look.

## Not verified here

- Whether agents route correctly between `tcw-setup`, `tcw-configure` and the
  usage skills. That needs the paid eval run
  (`2026-09-11-run-the-eval-harness-and-act-on-what-it-finds`).
- The skills in a real Codex session.
- Codex and `bllm` were not asked to review; this was a single adversarial review.
