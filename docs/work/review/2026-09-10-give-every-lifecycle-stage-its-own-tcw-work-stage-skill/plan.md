# Plan: give every lifecycle stage its own `tcw-work-stage-<stage>` skill

Ordered so the suite is green at every commit boundary. The tests that describe
the new skills land **before** the skills themselves, red on purpose, then go
green as each file appears. The manifest fix (Task 1) has to precede the fifth
skill or an unrelated test starts failing on a `KeyError` for reasons that have
nothing to do with the file being added.

## Task 1 — make the skill-count test survive fourteen prefixed skills

**Modifies:** `tests/test_plugin_manifests.py`

Two independent breakages in `test_the_codex_description_counts_the_skills_it_ships`,
both caused by this item and neither by the other.

**a. The count.** `NUMBER_WORDS` stops at 12 (`tests/test_plugin_manifests.py:65`).
The count goes 9 → 14, so the test raises `KeyError: 14` before reaching its
assertion. Extend the mapping through 20.

**b. The enumeration.** The test asks `n not in blob` for each shipped directory
name — a substring test. `tcw-work-stage` is a substring of every
`tcw-work-stage-<stage>` name, so once the five ship, the generic skill could be
deleted from the description entirely and the test would still pass. Match each
name as a whole token instead: `re.search(re.escape(n) + r"(?![-\w])", blob)`.
The negative lookahead is the whole fix — a trailing `-` or word character means
this is a longer name, not the one being checked.

Acceptance criterion 8 is this half. Criterion 7 is the other.

Nothing else changes in this file yet — the description itself is Task 7.

**Proves it:** `NUMBER_WORDS[14]` is `fourteen`. `pytest
tests/test_plugin_manifests.py` still green — the description still says "nine
skills", nine still ship, and each of the nine names is a whole token in it.
Then a scratch check of the lookahead: with a blob containing only
`tcw-work-stage-spec`, the name `tcw-work-stage` reports as missing. Run that as
a throwaway `python3 -c`, not as a committed test.

## Task 2 — widen the composing-skill tests to a set, still passing on one

**Modifies:** `tests/test_skill_lifecycle_parity.py`

Replace the single `STAGE_SKILL` constant with a derived set:

- `PER_STAGE_SKILLS = tuple(s for s in STAGE_IDS if s not in {"inbox", "postmortem"})`
  — derived from `STAGE_IDS`, per acceptance criterion 1, so the exclusion is
  the only hand-written part and it is one literal set with a comment saying
  why each is excluded.
- `COMPOSING_SKILLS` = the generic skill plus
  `skills/tcw-work-stage-<stage>/SKILL.md` for each of those five.

Parametrize the four existing `STAGE_SKILL` tests over `COMPOSING_SKILLS`:

| Existing test | What changes |
| --- | --- |
| `test_the_composing_skill_reads_a_router_that_exists_for_every_stage` | The generic skill's `cat` template holds `$stage` and is resolved against every stage id; a per-stage skill's holds the literal stage and is checked once. Split accordingly rather than forcing one assertion to cover both. |
| `test_the_composing_skill_names_the_gate_in_its_own_prose` | Strip fenced blocks first, as it already does, then assert the file's own gate literal — `tcw work stage gate $stage $item` for the generic one, `tcw work stage gate <stage> $item` for each per-stage one. |
| `test_every_injected_command_survives_its_own_failure` | Unchanged logic, run per file. |
| `test_the_composing_skill_declares_the_commands_it_injects` | Unchanged logic, run per file. |

Add one new test asserting the per-stage skill **set** is exactly
`PER_STAGE_SKILLS` — no missing file, and no `skills/tcw-work-stage-*/SKILL.md`
that is not in the set. The glob now discriminates on its own: every per-stage
skill carries the `tcw-work-stage-` prefix and the generic skill does not match
it. This is what catches a sixth skill appearing for `postmortem` later without
the decision being revisited.

Add one new test asserting each per-stage skill declares `arguments: [item]` and
no stage argument (criterion 2).

**Proves it:** the five per-stage skills do not exist yet, so
`pytest tests/test_skill_lifecycle_parity.py` fails with exactly the five
missing-file failures and the parametrized cases for `tcw-work-stage` all pass.
Record the failure list — anything failing that is *not* a missing per-stage
file is a mistake in this task, not the next one.

## Task 3 — `tcw-work-stage-spec`

**Creates:** `skills/tcw-work-stage-spec/SKILL.md`

Written first because `spec` is the stage most often reached for, so it is the
one whose description wording gets the most scrutiny before the other four copy
its shape. Structure per the spec's Design section:

- frontmatter: `name`, `description`, `when_to_use`, `arguments: [item]`,
  `allowed-tools: Bash(tcw *), Bash(cat *)`, `metadata.author`, `license`
- `when_to_use` says what this skill is **not**: it does not drive the stage
  range the way `/tcw-plan-work` does, and it does not gate
- body: the two injected blocks with `spec` literal and `$item` interpolated,
  each ending `|| true`; the gate warning naming
  `tcw work stage gate spec $item` outside any fence; the manual-fallback fence

**Proves it:** the `tcw-work-stage-spec` parametrized cases in
`tests/test_skill_lifecycle_parity.py` go green; the other four stay red.

## Task 4 — the remaining four per-stage skills

**Creates:** `skills/tcw-work-stage-request/SKILL.md`,
`skills/tcw-work-stage-plan/SKILL.md`,
`skills/tcw-work-stage-implement/SKILL.md`,
`skills/tcw-work-stage-verify/SKILL.md`

Same shape as Task 3, each with its own `description` and `when_to_use`.
Specifically:

- `tcw-work-stage-request` — say it is the stage that asks the user questions,
  so a session that cannot reach the user should not start here.
- `tcw-work-stage-plan` — say explicitly that it is not `/tcw-plan-work`, which
  drives `request` through `plan`; this one composes the `plan` stage's
  instructions only.
- `tcw-work-stage-implement` — say it composes the instructions; it does not run
  `tcw work start` and does not write code.
- `tcw-work-stage-verify` — say explicitly that it is not `/tcw-verify-work`,
  which runs the whole verification and records the decision.

**Proves it:** `pytest tests/test_skill_lifecycle_parity.py` fully green.
`ls skills/*/SKILL.md | wc -l` prints 14.

## Task 5 — confirm `tcw-work-stage` is untouched

**Modifies:** nothing.

Criterion 6. `git diff <first commit of this item>..HEAD --
skills/tcw-work-stage/SKILL.md` is empty. If it is not, the change was made in
the wrong file and Tasks 3–4 need revisiting before going further.

**Proves it:** the diff command produces no output.

## Task 6 — the manual invocation check

**Modifies:** nothing; produces evidence for `outcome.md`.

Criterion 11, and the only criterion no test can carry. In a Claude session with
the plugin loaded from this checkout:

1. `/tcw:tcw-work-stage-spec` with no argument — both blocks render, and the
   prompt half shows `<slug>` where an item reference would go.
2. `/tcw:tcw-work-stage-spec 2026-09-10-give-every-lifecycle-stage-its-own-tcw-work-stage-skill`
   — both blocks render with the reference substituted in the gate warning, the
   prompt header, and the fallback fence.

Record both observations verbatim in `outcome.md`. If the plugin cache is stale,
the skill invoked will be the published 2.0.0 one and neither observation is
worth anything — confirm the loaded copy is this checkout before reading
anything into the result.

## Task 7 — documentation

Scheduled as one block at the end, per the plan-stage instruction: the finished
diff is what these describe. All four of the project's documentation entries
fire.

**Modifies:**

- `.codex-plugin/plugin.json` — `longDescription` says "fourteen skills" and
  names all five new directories literally. The test checks each name
  individually, so a grouped phrase like "`tcw-work-stage-request` through
  `tcw-work-stage-verify`" will not satisfy it. Task 1b also means the sentence
  must still name `tcw-work-stage` on its own, not only as the head of the five
  longer names.
- `README.md` — the Skills section at line 270 says "Seven skills" over a table
  that already omits `tcw-work-stage` and `tcw-post-mortem`. Correct the count
  to match `skills/*/SKILL.md` and add the composing skills to the table as one
  row for `tcw-work-stage` plus one row covering the five stage-specific ones.
  Nothing tests this, which is why it is named as its own file here.
- `skills/tcw-work/references/commands.md` — the "read a stage as one document"
  row at line 31 names only `tcw-work-stage <id> <item>`. Add the per-stage
  form. `[Skill-Driven-Component]` fires: this is the driving skill for the
  component whose surface changed.
- `docs/capabilities/work/run-a-lifecycle-stage/description.md` — the paragraph
  at line 95. Describe both routes; keep the statement that the composed read
  runs no gate, since that is the sentence the whole capability turns on.
- `docs/release-notes/upcoming.md` — plain language: you can now ask for a
  lifecycle stage by name.
- `docs/changelogs/upcoming.md` — Added: five skills, the widened parity tests.
  Changed: the Codex description, the README count, the commands table.
  Internal: `NUMBER_WORDS` extended.

**Proves it:** `pytest` fully green — in particular
`test_the_codex_description_counts_the_skills_it_ships`, which after Task 1
checks the count word and every name as a whole token. `tcw capabilities check` and `tcw validate` exit zero.

## Documentation Sync

| Entry | Trigger | Fires | Task |
| --- | --- | --- | --- |
| `README.md` | `Public-API` | Yes — what the plugin ships is user-facing surface | 7 |
| `docs/release-notes/upcoming.md` | `Public-API` | Yes | 7 |
| `docs/changelogs/upcoming.md` | `Any-Code-Change` | Yes | 7 |
| `skills/<component>/SKILL.md` | `Skill-Driven-Component` | Yes — `tcw-work`'s `references/commands.md` documents the composed read | 7 |

## Verification

What the suite cannot check:

- **The skill invocation itself** (Task 6). No test can drive a Claude skill
  invocation, and the two facts the whole design rests on — that `$item`
  interpolates, and that an omitted argument becomes the empty string rather
  than a literal — are harness behavior observed in one session, not repository
  behavior. This is the check that would catch a harness change.
- **Whether the five descriptions discriminate.** A description that matches too
  broadly pulls a TCW skill into an unrelated conversation, and no assertion can
  measure that. Read all six descriptions side by side at the end and ask
  whether a prompt about writing a spec for something that is not a TCW work
  item would match any of them.
- **Whether the README table still reads well.** Six composing skills in a table
  that was written for seven single-purpose ones may want restructuring rather
  than five more rows. A judgment call at Task 7, not a test.

## Notes

Task order is load-bearing in one place only: Task 1 before the fifth skill
lands. Everything else could be reordered, but Tasks 3 and 4 are split so the
first skill's wording is settled before four copies of it exist.

The `tcw-work-stage-` prefix replaced an earlier `tcw-work-` one, which put
`tcw-work-plan` next to the `/tcw-plan-work` command and `tcw-work-verify` next
to `/tcw-verify-work`. The rename cost one thing and it is Task 1b: the shared
prefix makes the existing substring-based enumeration check unable to see the
generic skill's name at all.

No blockers. Nothing else in the backlog touches `skills/tcw-work-stage/` or the
parity tests.
