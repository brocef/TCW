# Outcome — Drop the `tcw-` prefix from the plugin's skill and agent names

15 skills and 3 agents renamed, with their 15 taxonomy Features and 15 capability
entries, and three guards added so the prefix cannot return by accident. Every
plan task landed; task 12 was verification only and changed nothing.

## What shipped

| Task | Commit    | What                                                                               |
| ---- | --------- | ---------------------------------------------------------------------------------- |
| —    | `824c4b0` | Spec and plan re-measured against the sixteenth shipped skill (see below)          |
| 1    | `2e90431` | Guard 8b: a skill's and an agent's declared `name` equals its path                 |
| 2    | `ea0cd59` | `tcw-work` → `work`, and 75 live references                                        |
| 3    | `16d029e` | `tcw-work-stage` → `work-stage`, `tcw-work-create` → `work-create`                 |
| 4    | `1b6cb3a` | `tcw-capabilities` → `capabilities`, `tcw-taxonomy` → `taxonomy`                   |
| 5    | `dbbb50b` | `tcw-setup` → `setup`, `tcw-configure` → `configure`, and `tcw-config.yaml:41`     |
| 6    | `194e0c0` | `tcw-post-mortem` → `post-mortem` (the skill; the agent file left for task 9)      |
| 7    | `7085743` | The four `tcw-commands-*` skills                                                   |
| 8    | `bcdae38` | The three `tcw-extras-*` skills                                                    |
| 9    | `f9c334c` | The three agents; after this no `tcw:tcw-…` address exists                         |
| 10   | `4b1e14e` | 15 taxonomy Features and 15 capability entries, through the CLI in three passes    |
| 11   | `ba0832e` | Guards 8a (17 names, widened `LIVE_ROUTES`) and 8c (no name repeats the plugin id) |
| 12   | —         | Verification only: exclusion counts and untouched history                          |
| 13   | `fb2ca5b` | Documentation Sync across the six entries                                          |

## Test result

**3404 passed, 2 skipped, 0 failed** (`python -m pytest`, full suite, on the
finished tree). The pre-change baseline was **3367 passed, 2 skipped**; the 37 new
cases are exactly the guards: 19 for 8b (16 skills + 3 agents), 1 for 8c, and 17
new `DELETED_NAMES` parametrisations for 8a.

`tcw taxonomy check`, `tcw capabilities check` and `tcw validate` each exit 0.
`python -m evals.run_evals --axis a --dry-run` resolves all 13 arms with no
unresolved skill name and spawns nothing.

**Mutation checks — five arms, each reverted, each red for the right reason.**

| Guard | Broke                                                  | It said                                                                                                                                                 |
| ----- | ------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 8b    | `documentation-sync`'s `name` → `documentation_sync`   | `…/documentation-sync/SKILL.md declares name='documentation_sync' but sits in 'documentation-sync'` — 1 failure                                         |
| 8b    | `agents/tcw-verifier.md`'s `name` → `verifier`         | `…/agents/tcw-verifier.md declares name='verifier' but is filed as 'tcw-verifier'` — 1 failure                                                          |
| 8a    | `tcw-work` re-added to `README.md`                     | `'tcw-work' was removed but is still named by: ['README.md']`                                                                                           |
| 8a    | the old path re-added to `tcw-config.yaml`             | `'tcw-configure' was removed but is still named by: ['tcw-config.yaml']` — and the _old_ `LIVE_ROUTES` reports nothing, so the widening is load-bearing |
| 8c    | `skills/work` → `skills/tcw-work`, frontmatter with it | `these repeat the plugin id 'tcw', which the namespace already supplies: ['tcw-work']`                                                                  |

## What the plan or spec got wrong

1. **There are sixteen shipped skills, not fifteen.** `skills/tcw-work-create`
   landed after this item was planned, so it is 15 renames rather than 14 and 18
   names rather than 17 (17 of them distinct — `tcw-post-mortem` names both a
   skill and an agent). It also joins `tcw-work-stage` in the collision class the
   whole-name rule exists for. Both artifacts corrected in `824c4b0`; it rides in
   task 3, and task 10 grew a pass-C ordering note because it is the only Feature
   whose `relatesTo` names another renamed Feature.

2. **The intermediate staleness does _not_ stay green.** The plan said rewriting a
   skill name in a capability body before task 10 moves the folder is safe because
   "`tcw capabilities check` validates refs rather than prose". `tcw validate`
   resolves `tcw://` refs embedded in a body, so rewriting the name inside
   `tcw://C/skills/tcw-extras-triage-issues` pointed it at a capability that did
   not exist yet and turned validate **red on task 8**. A ref is a capability
   _path_, which is task 10's to change, so the substitution now leaves every
   `tcw://` target alone. Corrected in the plan in `bcdae38`.

3. **Rule 6's "whole word" is a looser test than the substitution rule, and the
   spec uses one phrase for both.** The counts were taken with a regex word
   boundary, where `-` is a boundary — so `tcw-ref` counts inside `data-tcw-ref`,
   `tcw-sidecar-token` inside `X-TCW-Sidecar-Token`, and `tcw-storage-folders`
   inside `cli/locate-tcw-storage-folders`. Under the strict
   `(?<![-\w])…(?![-\w])` form the substitution uses, those three and `tcw-serve`
   count zero. Stated here because reading one phrase as the other makes four rows
   of that table look wrong.

4. **Two of rule 6's counts had drifted, and measuring `work/` as a directory name
   corrupts the comparison.** `tcw-config` was 443 and `tcw-cli` 100 before this
   item — the v2.3.0 release notes added them. Separately, excluding "every `work/`
   board directory" by matching _any_ path component named `work` silently drops
   `skills/work/**` once task 2 creates it, which made three counts appear to fall.
   Re-measured against a worktree of the pre-change commit with only `docs/work/`
   excluded: **13 of 14 unchanged**, and `tcw-config` up by 2 — both occurrences
   added deliberately by task 11's new `LIVE_ROUTES` entry and its comment. No
   occurrence of any excluded token was destroyed, which is what criterion 10 is
   for.

5. **Criterion 9's grep must exclude `tests/` and `evals/`, not only the
   `DELETED_NAMES` tuple.** Guard 8c's own docstring quotes `/tcw:tcw-work` to
   explain what it forbids — a guard has to be able to name the thing it refuses.
   The plan already reasoned this way when it kept both directories out of
   `LIVE_ROUTES`; only the criterion's wording was narrower. With `tests/` and
   `evals/` excluded the grep returns nothing, and `evals/` turns out to carry no
   old name at all.

6. **`docs/work/` is excluded from the substitution whole**, not "outside this
   item's own folder" as plan step 4 has it. This item's spec and plan are a rename
   spec: their mapping tables must keep quoting the old names on the left, and a
   substitution would destroy exactly the document that records what was renamed.
   The artifacts were edited by hand only.

7. **The 8c mutation check fires two guards, not one.** The plan expected that
   moving `skills/work` back to `skills/tcw-work` with its frontmatter would leave
   "only 8c" speaking. `test_the_codex_description_counts_the_skills_it_ships`
   also fails, correctly — the Codex description no longer names the renamed
   directory. Both signals are right; the prediction was just narrower.

8. **Three consequences of the rename that no task anticipated.**
    - `test_a_shared_name_prefix_cannot_stand_in_for_the_shorter_name` demonstrated
      its discrimination against `tcw-work-stage-spec`, a retired skill. After the
      rename `work-stage` sits inside that name as an _infix_, so both docstrings
      said "prefix" about something that no longer was one. Re-pointed at the live
      pair — `work` is a prefix of `work-stage` and `work-create` — which is the
      same collision class on names that still ship.
    - The cross-axis descriptions in `capabilities` and `taxonomy` became
      tautologies: "The taxonomy axis is taxonomy, the work axis is work." They name
      the skills explicitly now. These are frontmatter `description` values, so they
      are what a user reads in a skill listing.
    - README's four skill tables no longer aligned once the names shortened. That is
      prettier's output, not something to align by hand: 290 files were already
      prettier-dirty before this item (its own backlog item covers that), and this
      change added exactly one — `README.md`, which was clean before. Formatted with
      prettier, and the result is only separator-row widths.

9. **Minor.** The spec says "all five" documentation entries fire; there are six,
   and five fire — `docs/guide/jira.md` correctly does not. The suite baseline is
   3367, not the 3360 the spec recorded.

## Notes

- **The host resolution the plan called unverifiable was verified.** A headless
  `claude -p --plugin-dir /home/user/TCW` session reports in its own `init` event
  that it loaded `tcw` from the working tree (`source: tcw@inline`, version 2.3.0)
  and resolved exactly sixteen skills, every one unprefixed: `tcw:work`,
  `tcw:work-stage`, `tcw:work-create`, `tcw:capabilities`, `tcw:taxonomy`,
  `tcw:setup`, `tcw:configure`, `tcw:post-mortem`, the four `tcw:commands-*`, the
  three `tcw:extras-*`, and `tcw:documentation-sync`. No `tcw:tcw-…` address
  appears. **Codex is still unverified** — nothing here runs it — but it reads the
  same frontmatter and the same directory names, both of which this proves are
  consistent.
- **Driving the lifecycle with the CLI was safe here**, despite `AGENTS.md`'s
  exception. That exception is scoped to editing `tcw/`; this item changed one
  docstring there and nothing else, and no lifecycle binding in `tcw-config.yaml`
  is a `skill:` ref — they are all `builtin:` and `file:` — so renaming `skills/`
  never put the CLI's behaviour in flux.
- **Pre-existing environment flake, not TCW:** the container signs commits through
  a signing server that intermittently returns 502. That failed
  `test_a_hook_exceeding_the_timeout_is_a_failure` on the first baseline run — the
  test makes a real commit — and it passed on retry with no change.
- **Follow-up to file at completion**, per the spec's Notes: `tcw capabilities mv` /
  `tcw taxonomy mv`. Task 10 was the second rename done as `add` + `rm`, it is the
  only task here with no test coverage, and it regenerated every capability and
  Feature id for no reason other than the missing verb. A rename verb passes the
  abstraction litmus test, so it belongs in the model; it changes the CLI surface
  and needs its own spec.
- **Version cut deferred to closeout**, as the plan says: the `upcoming.md` entries
  are written, and whether to cut and at what size is the user's call.
