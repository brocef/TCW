# Plan — Compose documentation-sync and tcw-work-create from project bindings

Implements `spec.md`. Every task ends green on the targeted modules and is its
own commit. Run everything from the worktree root with
`PATH="$PWD/.venv/bin:$PATH"`.

## Tasks

### 1. Convert `tcw-work-create`

Files: `tests/test_shipped_procedures.py`, `skills/tcw-work-create/SKILL.md`,
`tcw/work/procedures/create-work.md`.

1. In the test file, move the `create-work` row out of `SOURCES` into a new
   `CONVERTED = {"create-work": "skills/tcw-work-create/SKILL.md"}` map, change
   `test_the_source_map_covers_exactly_the_ids` to compare
   `set(SOURCES) | set(CONVERTED)`, and add
   `test_a_converted_skill_reads_its_procedure(pid)` parametrized over
   `CONVERTED`, asserting the skill body (a) contains
   `` !`tcw work procedure prompt <pid> ``, (b) names
   `tcw work procedure prompt <pid>` inside a fenced block after a
   `## Document command summary` heading, and (c) does not contain the first
   non-heading, non-blank line of the default.
2. Run `pytest -q tests/test_shipped_procedures.py`; it must fail on (a) for
   `create-work` because the skill has no injection yet.
3. Rewrite the skill: frontmatter unchanged; title and opening paragraph;
   `## 2. Find overlap` verbatim; `` !`tcw work procedure prompt create-work || true` ``;
   a `## Document command summary` block naming the command, with the line
   telling a reader whose harness ran nothing to run it and read its output in
   place of the line above.
4. Remove the title, opening paragraph and step 2 section from
   `tcw/work/procedures/create-work.md`, nothing else.
5. Green: `tests/test_shipped_procedures.py`, `tests/test_dynamic_skill_marker.py`,
   `tests/test_plugin_manifests.py`, `tests/test_skill_lifecycle_parity.py`,
   `tests/test_eval_grading.py`.

Proves spec criteria 2, 3, 4, 7 (find-overlap untouched).

### 2. Convert `documentation-sync`

Files: `tests/test_shipped_procedures.py`, `skills/documentation-sync/SKILL.md`,
`tcw/work/procedures/documentation-sync.md`.

1. Move the `documentation-sync` row into `CONVERTED`; run the test module and
   watch the new test fail on (a) for `documentation-sync`.
2. Rewrite the skill: frontmatter plus
   `allowed-tools: Bash(tcw *), Bash(cat *)`; today's lines 7-51 verbatim;
   the injection
   `` !`tcw work procedure prompt documentation-sync 2>/dev/null || cat "${CLAUDE_PLUGIN_ROOT}/tcw/work/procedures/documentation-sync.md" || true` ``;
   the command summary naming both commands, saying the `cat` is for a project
   that is not a TCW node or has no CLI.
3. Cut `tcw/work/procedures/documentation-sync.md` down to `## Evaluating
   Triggers` onward.
4. Green: the modules of task 1 plus `tests/test_documentation_sync_wiring.py`,
   `tests/test_documentation_config.py`, `tests/test_shipped_prompts.py`,
   `tests/test_unpushed_version_script.py`.
5. Check spec criterion 6 by hand: from the scratchpad's empty directory, run
   the injection command with `CLAUDE_PLUGIN_ROOT` set to the worktree; expect
   the default and exit 0.

Proves spec criteria 2, 3, 5, 6, 7.

### 3. Capability ledger

Files: `docs/work/active/<slug>/capabilities.yaml` (new),
`docs/capabilities/skills/documentation-sync/description.md`,
`docs/capabilities/skills/tcw-work-create/description.md`.

`changed:` both skills. Append one sentence to each description saying the
procedure text comes from `tcw work procedure prompt <id>` and a project may
replace it under `work.procedures.<id>`, while the stated fixed part cannot be.
`tcw capabilities check` exits 0. Proves criterion 9.

### 4. The "nothing configured" proof

No files committed. Rebuild the reader's text for each skill (body after
frontmatter, injection line replaced by the command's output) and diff it
against `git show main:<path>` after frontmatter; diff the frontmatter too.
Record both diffs and an explanation of every hunk in `outcome.md`. Run the
criterion 8 grep. Proves criteria 1 and 2.

## Documentation Sync

One pass after task 4, one commit.

- **`docs/changelogs/upcoming.md` [Any-Code-Change]** — fires: the shipped
  defaults and two skills change. New bullet at the end of the relevant
  existing section.
- **`docs/release-notes/upcoming.md` [Public-API]** — fires: a project can now
  replace what the two skills tell an agent. New bullet at the end of the
  relevant existing section.
- **`README.md` [Public-API]** — expected not to fire: no verb or key is new,
  and the skill table's descriptions (`README.md:677`) stay true. Re-check.
- **`skills/<component>/SKILL.md` [Skill-Driven-Component]** — expected not to
  fire: no component's CLI, model or lifecycle changes; the converted skills
  are the change itself.
- **`skills/tcw-configure/references/<document>.md` [Configuration-Key-Change]**
  — does not fire: `work.procedures` exists already and its meaning is unchanged.
- **`docs/guide/jira.md` [Tracker-Change]** — does not fire.

## Final run

After the docs commit, bare `pytest -q -p no:cacheprovider` once, in the
background; record its summary line. Then write and commit `outcome.md`.

## Verification

What the suite cannot check, deferred to verify:

- That Claude Code runs both injections, including the permission grant added
  to documentation-sync, and the reader sees one continuous document.
- That a Codex session reading either skill follows the command summary and
  gets the same text.
- That documentation-sync in a project that is not a TCW node still evaluates
  triggers (the `cat` fallback in a live session, not only by hand).
- That a `work.procedures.create-work` override actually replaces what an agent
  does, while step 2 still runs.

## Notes

- `tcw work stage gate plan` refused ("'plan' is not legal for an item in
  'active'; it runs in backlog"), as the requester expected. The bound pre-check
  `TCW_SLUG=<slug> python scripts/require_artifact.py spec` exited 0.
- No blockers to record: the two blockers in `state.yaml` are merged.
