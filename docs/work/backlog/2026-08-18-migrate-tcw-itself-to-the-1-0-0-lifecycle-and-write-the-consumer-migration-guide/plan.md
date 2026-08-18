# Plan — Migrate TCW itself to the 1.0.0 lifecycle and write the consumer migration guide

Ten tasks. Tasks 1–2 are the guide; 3–8 are the configuration migration, ordered
so `tcw validate` and the suite are green at every commit boundary; 9 is the
documentation block; 10 folds the migration's findings back into the guide.

The riskiest task is 7 (deleting prose from `AGENTS.md`), and it is placed after
the prompt files exist, after every reference has somewhere to point, and after
the guard test is written — so that nothing is ever deleted before its
replacement is proven present.

---

## Task 1 — Write the migration guide

**Creates:** `docs/migration-guide-0.21.X-to-1.0.0.md`

Written from `docs/release-notes/v1.0.0.md`, `docs/changelogs/v1.0.0.md`, and
the code, in the house style of `docs/migration-guide-0.15.X-to-0.16.0.md`
(prose, reader-ordered, break first). Five sections in the order the spec's
Design fixes: the one break; what changed under you (all six items); upgrade
ordering; new and optional; what you don't have to do.

**Proves it:** acceptance criteria 1, 2, and 3 — the `prompt: []` break with both
spellings and both replacements appears before any feature is described; the six
behavior changes are each present; the CLI/plugin upgrade-ordering hazard is
stated.

**Commit:** `docs: add the 0.21.x → 1.0.0 migration guide`

## Task 2 — Point v1.0.0's release notes at the guide

**Modifies:** `docs/release-notes/v1.0.0.md`

Add one line under the breaking-change section linking the new guide. Legitimate
because v1.0.0 is tagged but unpushed, so the notes have not reached anyone; a
migration guide nobody can find from the release it describes is the failure mode
this avoids.

**Proves it:** the link resolves to a file that exists (`test -f` on the target
of the link, done by eye at review — no test earns its place for one link).

**Commit:** `docs: link the migration guide from the v1.0.0 release notes`

## Task 3 — Extract the three prompt files

**Creates:** `docs/lifecycle/abstraction.md`, `docs/lifecycle/harness.md`,
`docs/lifecycle/implementation.md`

Content is moved verbatim from `AGENTS.md` — the litmus test and abstract spine
into `abstraction.md`, "Harness compatibility (Claude and Codex)" into
`harness.md`, "Implementation rules" plus the `tcw work start`-is-the-first-
implementation-commit rule into `implementation.md`. Each file opens with one
sentence naming which stages it is bound to, since it will be read as a
continuation of TCW's built-in prompt rather than as a document with a title.

`implementation.md` **points at** `AGENTS.md`'s `## Documentation Sync` section
rather than copying it, per the spec: the section stays where
`skills/documentation-sync/SKILL.md:8` looks for it.

Nothing is deleted from `AGENTS.md` in this task. The tree deliberately holds
both copies until Task 7, so no commit boundary exists at which a rule is
unreachable.

**Proves it:** every heading and paragraph of the three moved `AGENTS.md`
sections appears in exactly one of the new files — checked by diffing the moved
text against the source before Task 7 removes it.

**Commit:** `docs: extract the stage-scoped rules into docs/lifecycle/`

## Task 4 — Write the two artifact templates

**Creates:** `docs/lifecycle/templates/spec.md`,
`docs/lifecycle/templates/spec-bug.md`, `docs/lifecycle/templates/plan.md`

`spec.md` restates the seven sections from `tcw/work/templates.py`'s `_SPEC` and
adds this repo's own: a `## Abstraction litmus test` section naming the operation
under test and the verdict. `spec-bug.md` is `spec.md` plus `## Reproduction`.
`plan.md` restates `_PLAN`'s headings.

Restating rather than extending is forced, not chosen: `artifacts:` is
first-match-wins (spec, Design), so a bound template replaces the built-in.

**Proves it:** Task 5's test.

**Commit:** `docs: add this repo's spec and plan templates`

## Task 5 — Write the guard test

**Creates:** `tests/test_repo_lifecycle.py`

Four tests, all against the real repo tree rather than a `tmp_path` fixture,
because what is under test is this node's own configuration:

1. `test_the_repo_config_parses_with_no_problems` — `lifecycle_problems()` on
   this node returns `[]`.
2. `test_repo_templates_carry_every_builtin_heading` — every `## ` heading in
   `tcw.work.templates`' built-in `spec` and `plan` templates appears in the
   corresponding file under `docs/lifecycle/templates/`. This is the named guard
   against the silent drift the first-match-wins semantics create.
3. `test_every_bound_prompt_file_exists` — every `file:` binding in the parsed
   policy resolves to a file that exists and is non-empty.
4. `test_the_moved_rules_are_reachable` — the litmus-test sentence
   ("Could a non-filesystem store implement this operation") appears in
   `docs/lifecycle/abstraction.md`. This is the test that makes Task 7's deletion
   safe to commit.

Written **before** the config block (Task 6) so tests 1 and 3 fail first for the
right reason — no `work.lifecycle` key yet — and pass on Task 6.

**Proves it:** acceptance criterion 11.

**Commit:** `test: guard this repo's lifecycle configuration against drift`

## Task 6 — Add the `work.lifecycle` block

**Modifies:** `tcw-config.yaml`
**Creates:** `scripts/require_artifact.py`

The block is exactly as the spec's Design gives it: `prompt:` on `spec`, `plan`,
`implement` each led by `builtin: true`; a `pre:` on the `plan` stage running
`python scripts/require_artifact.py spec`; `artifacts:` for `spec` (with the
`when: { tags: [bug] }` variant first) and `plan`; a `pre:` on the `complete`
transition running `tcw validate`.

`scripts/require_artifact.py` takes one argument — the artifact name — reads
`TCW_SLUG` from the environment, runs `tcw work show "$TCW_SLUG" --json`, and
exits 1 with a message on stderr when `artifacts[<name>]` is false or missing. It
composes no store path. It exits 1 rather than raising if `TCW_SLUG` is unset or
`tcw` is not on PATH, so the check fails closed.

**Proves it:** acceptance criteria 4, 5, 6, 7, 8, 9, and 11, each run as a
command at this task's end:

- `tcw validate` → exit 0 (criterion 4).
- `tcw work stage spec <this item>` → built-in text, then `abstraction.md`, then
  `harness.md` (criterion 5). Compared against the file contents, not eyeballed.
- `tcw work stage plan <a backlog item with no spec>` → exit non-zero, empty
  stdout; the same on this item, which has a spec → exit 0 (criterion 6).
- `tcw work scaffold spec <an item tagged bug>` → draft contains
  `## Reproduction`; on an untagged item → it does not (criterion 7). Both drafts
  are deleted afterward.
- `tcw work scaffold plan <item>` → draft carries every `_PLAN` heading
  (criterion 8).
- `tcw work lifecycle --json | python -m json.tool` → parses; `spec`, `plan`,
  `implement`, and the `complete` transition all report bindings (criterion 9).
- `python -m pytest -q tests/test_repo_lifecycle.py` → passes (criterion 11).

**Commit:** `feat: bind this repo's own rules to the work lifecycle`

## Task 7 — Remove the moved rules from `AGENTS.md`

**Modifies:** `AGENTS.md`

Delete "Prime directive: the abstraction litmus test", "Abstract spine,
filesystem leverage", "Implementation rules", and "Harness compatibility (Claude
and Codex)". Delete the stage-scoped part of "Work Planning and Implementation",
keeping the one line that says all work here is tracked by `tcw work`.

Add one line naming `docs/lifecycle/` and the command that resolves it —
`tcw work stage <id> <slug>` — so a reader landing on `AGENTS.md` can still find
the prime directive.

Keep, untouched: the header and live-status line, `## Generic instructions`,
`## Documentation Sync`, and `## Versioning`.

**Proves it:** acceptance criterion 10, run as
`grep -c 'abstraction litmus test\|Abstract spine\|Harness compatibility' AGENTS.md`
excluding the pointer line, plus `grep '## Documentation Sync' AGENTS.md` and
`grep '## Versioning' AGENTS.md` both matching. Task 5's test 4 already passing
is what makes the deletion safe.

**Commit:** `docs: move the stage-scoped rules out of AGENTS.md`

## Task 8 — Redirect the six stale references

**Modifies:** `README.md` (two sites), `tcw/store/base.py` (module docstring),
`tcw/store/fs.py` (module docstring), `docs/plan/phase-5-work.md`,
`docs/plan/phase-1-scaffold.md`

Each currently points at `AGENTS.md` for the litmus test or the
don't-pre-abstract rule; each is repointed at `docs/lifecycle/abstraction.md`.
The two Python edits are comment text only — no statement changes, so acceptance
criterion 13 ("no file under `tcw/` is modified") is amended by criterion 10a,
which explicitly permits these two docstrings and nothing else.

**Proves it:** acceptance criterion 10a —
`grep -rn 'AGENTS\.md' README.md tcw/ docs/plan/` returns only references that
are about `AGENTS.md` as a file (the Codex-subagents citation, the doc-sync
setup), never about the moved rules. Plus `python -m pytest -q` full run, since
this task touches `tcw/`.

**Commit:** `docs: repoint the prime-directive references at docs/lifecycle/`

## Task 9 — Documentation Sync

Evaluated against `AGENTS.md`'s four entries. Two fire, two do not:

| Entry                                   | Trigger                  | Fires? | Why                                                                                                                                                                        |
| --------------------------------------- | ------------------------ | ------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `README.md`                             | Public-API               | **No** | No CLI surface or user-facing behavior changes. Task 8 edits `README.md`, but for a reference redirect, which is not this trigger.                                          |
| `docs/release-notes/upcoming.md`        | Public-API               | **No** | Nothing user-facing ships. The guide belongs to v1.0.0, which is why Task 2 links it from `v1.0.0.md` rather than opening an `upcoming.md` entry for a release that is done. |
| `docs/changelogs/upcoming.md`           | Any-Code-Change          | **Yes** | `scripts/require_artifact.py` and `tests/test_repo_lifecycle.py` are new code. One `Internal` entry.                                                                        |
| `skills/<component>/SKILL.md`           | Skill-Driven-Component   | **Yes** | `skills/tcw-work/SKILL.md` describes how an agent drives the work lifecycle. This repo now configures that lifecycle, and the skill is the place a reader learns the CLI is not the only source of stage text. One sentence, no restructuring. |

**Modifies:** `docs/changelogs/upcoming.md`, `skills/tcw-work/SKILL.md`

Run the `documentation-sync` skill over the finished diff before this task is
considered done, per `AGENTS.md`. If it finds a trigger this table missed, the
table was wrong and the finding is recorded in `outcome.md`.

**Proves it:** the skill reports no unfired trigger; `python -m pytest -q` still
passes (`tests/test_documentation_sync_wiring.py` and the skill line-ceiling
tests both read `skills/tcw-work/SKILL.md`).

**Commit:** `docs: changelog and skill note for the lifecycle adoption`

## Task 10 — Fold the migration's findings back into the guide

**Modifies:** `docs/migration-guide-0.21.X-to-1.0.0.md`

The guide was written first, from the release notes. Doing the migration produces
things the release notes do not say, and by this point they are known rather than
predicted. At minimum, the two the spec already names:

- A rule another skill reads out of `CLAUDE.md` by name cannot move into a stage
  prompt. Name `documentation-sync` as the concrete case.
- A rule that source code cites needs a citable location, so `file:` bindings
  beat `blob:` for anything referenced from outside the config.

Plus whatever else Tasks 3–8 actually turned up, including any CLI defect filed
as its own backlog item.

**Proves it:** the guide contains a section on both findings; any backlog item
filed during the work is linked from `outcome.md`.

**Commit:** `docs: add the dogfooding findings to the migration guide`

---

## Verification

What the suite cannot check, and must be confirmed by hand or by the user:

1. **That the guide is useful to someone who has not read the release notes.**
   No test covers prose quality or ordering. This is the user's call at the
   `verify` stage, and it is the primary thing to put in front of them.
2. **That `AGENTS.md` is still sufficient for an agent that never runs
   `tcw work stage`.** This is the spec's named accepted risk. The check is to
   read the post-Task-7 `AGENTS.md` cold and ask whether an agent starting work
   from it alone would go wrong. It cannot be automated; if the answer is no, the
   finding is more valuable than the prose was and belongs in the guide.
3. **That the Codex path works.** `tcw work stage` is harness-neutral by
   construction — it is the CLI — but nothing in this repo proves a Codex agent
   reaches the moved rules. Confirm by reasoning about the command, and record
   that it was reasoning rather than an executed test.
4. **Baseline comparison.** `python -m pytest -q` must report ≥ 1581 passed and
   0 failed (spec `## Notes`). Run once at the end over the whole change, not per
   task — it takes 417 seconds.

## Notes

- Task ordering rule applied: the three files exist (3), the templates exist (4),
  the guard test exists and passes (5), the config binds them (6), and only then
  is anything deleted (7) or repointed (8). At no commit boundary is a rule
  absent from both `AGENTS.md` and `docs/lifecycle/`.
- No blockers to record with `tcw work edit --blocked-by`: every dependency here
  is between tasks inside this one item, not between items.
- Self-review against the spec: criteria 1–3 → Task 1; 4–9 → Task 6; 10 → Task 7;
  10a → Task 8; 11 → Tasks 5 and 6; 12 → Verification 4; 13 → Task 8, which
  amends it and says so. Every task traces back: 1→c1-3, 2→discoverability of
  the Task 1 artifact, 3→c5/c10, 4→c7/c8, 5→c11, 6→c4-9, 7→c10, 8→c10a/c13,
  9→Documentation Sync gate, 10→the spec's Goal 5.
