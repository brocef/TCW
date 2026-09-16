# Plan — State the two rules for an overridable skill and mark every skill with its verdict

Two tasks, each test-first and each ending on a green suite, then one
documentation task. Task 1 lands the rules document and the half of the test
that needs only it; task 2 lands the key on all sixteen skills and the half of
the test that reads it.

## Before task 1

A worktree virtual environment, so the suite runs against this branch without
re-pointing the shared editable install:

```sh
python3 -m venv .venv && .venv/bin/pip install -e '.[dev]'
PATH="$PWD/.venv/bin:$PATH" .venv/bin/pytest -q     # baseline: record the summary line
```

## Tasks

### 1. The rules document and its completeness test

**Creates** `tests/test_dynamic_skill_marker.py`, `skills/README.md`.

1. Write the test module with these pieces and nothing more:
   - `RULES = REPO / "skills" / "README.md"`.
   - `verdict_rows()`: reads `RULES`, returns `(owner, pattern, verdict)` for
     every table row whose first two cells are backticked and whose third cell
     is one of the five verdicts. Base folder is `REPO / "agents"` when owner is
     `agents`, else `REPO / "skills" / owner`.
   - `shipped_documents()`: `skills/*/SKILL.md`, `skills/*/references/**/*.md`,
     `agents/*.md`.
   - `test_every_shipped_document_has_exactly_one_verdict` — each shipped file
     is matched by exactly one row's glob.
   - `test_every_verdict_row_names_a_shipped_document` — each row's glob matches
     at least one file.
   - `test_the_rules_are_stated` — `RULES` contains `Rule 1`, `Rule 2`, and the
     heading for why a project cannot add a procedure.
   Every assertion message names `skills/README.md`.
2. Run it; it fails because `skills/README.md` does not exist. Confirm that is
   the reason.
3. Write `skills/README.md` with the sections spec Design → "What the document
   says" lists, the verdict vocabulary, and one table, columns
   `Owner | Document | Verdict | Reason`, holding every verdict in spec Design →
   "Verdicts". Group rows by glob only where the spec groups them:
   `tcw-configure` `references/*.md`, `tcw-work` `references/procedures/*.md`,
   `tcw-work` `references/lifecycle/stage-*.md`; every other row names one file.
   Constraints from existing tests: never write `tcw-setup/references/` or
   `tcw-configure/references/` as one string
   (`tests/test_skill_path_pointers.py:18-26`), and never write the retired
   names in `tests/test_skill_lifecycle_parity.py:44-46` and `:545-554`.
4. Run the module; it passes. Mutation-check (spec criterion 2a and 2b): delete
   one `SKILL.md` row → red; `touch skills/tcw-work/references/scratch.md` → red.
   Read why each went red, then undo both.
5. Run the full suite, bare; it matches the baseline plus the new tests.
6. Commit: `skills: state the two rules for an overridable skill and classify every shipped document`.

Proves: spec acceptance criteria 1, 2a, 2b.

### 2. The `dynamic_skill` key on every skill

**Modifies** `tests/test_dynamic_skill_marker.py` and the frontmatter of all
sixteen `skills/*/SKILL.md`.

1. Add to the test module:
   - `test_every_skill_carries_dynamic_skill_matching_its_verdict`, parametrized
     over `skills/*/SKILL.md`: parse the frontmatter with `yaml.safe_load`,
     assert `dynamic_skill` is a `bool`, and equal to `True` exactly when the
     row's verdict is `overridable` or `composes already`.
   - `test_the_key_points_at_the_rules`, parametrized the same way: the raw
     frontmatter line starting `dynamic_skill:` contains `#` and `../README.md`.
2. Run; all sixteen fail on the missing key. Confirm that is the reason.
3. Add one line, as the last line before the closing `---`, to each file:
   `dynamic_skill: <value> # which skills a project may override, and why: ../README.md`,
   with the values in spec criterion 3. No other line in any `SKILL.md` changes.
4. Run the module; it passes. Mutation-check (criteria 2c, 2d, 2e): delete the
   key from one file, flip one value, strip one comment — each red for its own
   reason. Undo.
5. `git diff main -- 'skills/*/SKILL.md'` shows sixteen single-line additions
   inside frontmatter (criterion 4); `git diff --stat main -- agents
   'skills/*/references'` is empty (criterion 5).
6. `claude plugin validate --strict skills` passes (criterion 6).
7. Full suite, bare (criterion 7).
8. Commit: `skills: mark every skill with dynamic_skill`.

Proves: spec acceptance criteria 2c–2e, 3, 4, 5, 6, 7.

### 3. Documentation Sync

Evaluated against the finished diff, committed on its own.

- **`docs/changelogs/upcoming.md` — [Any-Code-Change]** — fires. Under `Added`:
  `skills/README.md` (the two rules and the verdict table), the
  `dynamic_skill` frontmatter key on every skill, and
  `tests/test_dynamic_skill_marker.py`.
- **`docs/release-notes/upcoming.md` — [Public-API]** — does not fire. No
  command, key a user writes, or skill behavior changes; the key is inert to
  both harnesses. The user-visible change arrives with children 2–6.
- **`README.md` — [Public-API]** — does not fire, for the same reason.
- **`skills/<component>/SKILL.md` — [Skill-Driven-Component]** — does not fire.
  No component's CLI, model or lifecycle changes; the frontmatter lines added in
  task 2 are this item's own change, not a response to one.
- **`skills/tcw-configure/references/<document>.md` — [Configuration-Key-Change]**
  — does not fire. `dynamic_skill` is a key in a skill file, not in
  `tcw-config.yaml` or any project configuration.
- **`docs/guide/jira.md` — [Tracker-Change]** — does not fire.

Commit: `docs: changelog entry for the skill override rules and marker`.

## Verification

What the suite cannot check:

- **Reachability for a person.** Open `skills/tcw-extras-autonomous-work/SKILL.md`
  cold, read the `dynamic_skill` line, follow `../README.md` from that folder,
  and confirm the document answers "what does this key mean and may I change
  what this skill says". Record the result in `outcome.md`.
- **Codex loads every skill with the key present.** The spec relies on Codex's
  parser source. If a `codex` binary is available, list skills from the worktree
  and confirm all sixteen load; otherwise say in `outcome.md` that it was not
  exercised.
- **The verdicts themselves.** Judgments, not computations. The requester
  reviews the table before children 3–6 start; `outcome.md` lists every verdict
  the requester did not give.

## Notes

- The `plan` gate refuses on status (the item is `active`, `plan` runs in
  `backlog`), as recorded in the spec's Notes. Its one `pre` check was run by
  hand: `TCW_SLUG=<slug> python3 scripts/require_artifact.py spec` exited 0.
- No blockers to record: the routing item this child was blocked by is
  completed (`4002ffb3`), and child 2 is not a dependency.
- Nothing here touches `tcw/`, so the lifecycle CLI stays usable for reads
  throughout.
