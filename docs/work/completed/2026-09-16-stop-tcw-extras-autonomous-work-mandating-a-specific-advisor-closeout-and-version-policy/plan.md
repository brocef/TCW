# Plan — Stop tcw-extras-autonomous-work mandating a specific advisor, closeout and version policy

Three tasks, each one commit, suite green after each. No Python under `tcw/`
changes; the only non-test code is a skill file and a procedure default.

## Tasks

### 1. Convert the skill and its default, with their tests

Written test-first: the tests are added and run red against today's skill
before either document changes, then everything lands in one commit so the
suite is never red at a commit boundary (the drift test and the conversion must
change together, as `tests/test_shipped_procedures.py:15-19` requires).

**Files**

- `tests/test_unattended_work_skill.py` (new). Four tests, each reading the
  skill file:
  1. the body after the frontmatter matches none of
     `codex|opus|sonnet|haiku|sendmessage|adversarial-code-reviewer` (word
     boundaries, case-insensitive), and contains none of `majority of two`,
     `git push`, `upcoming.md` (spec criterion 1);
  2. the body has a heading for what an advisor must be, says two are wanted, and
     says an answer is weighed, never counted (criterion 2);
  3. a line reading exactly `` !`tcw work procedure prompt unattended-work || true` ``
     exists, `allowed-tools:` contains `Bash(tcw *)`, `Bash(codex *)`, `Agent`
     and `SendMessage`, and `compatibility:` exists and mentions
     `work.procedures.unattended-work` (criteria 3 and 4);
  4. the last `## ` heading is `## Document command summary` and its section
     names `tcw work procedure prompt unattended-work` (criterion 5).
- `tests/test_shipped_procedures.py` — `test_each_default_is_todays_text`
  recognizes a converted source (its body contains
  `tcw work procedure prompt <pid>`) and for it asserts that no paragraph of the
  default (a blank-line-separated block of at least 40 characters) appears in the
  source body; unconverted sources keep the verbatim comparison. The
  `SOURCES` row for `unattended-work` keeps its path; its comment block is
  updated to describe the converted case.
- `tcw/work/procedures/unattended-work.md` — keeps `## The advisors` and
  `## Checkpoint map` word for word; loses the title, the opening paragraph,
  "Ask once", `## Hard blockers` and `## Leave the audit trail`.
- `skills/tcw-extras-autonomous-work/SKILL.md` — frontmatter gains
  `allowed-tools:` and `compatibility:`, `description:` says "by default";
  `dynamic_skill` line untouched. Body, in order: title; opening paragraph
  ("the advisors"); "Ask once"; `## What an advisor must be`; `## This project's
  procedure` with the tension sentence, the `--no-exec` re-read sentence and the
  injection line; `## Hard blockers — stop, report, wait` ("all of them");
  `## Leave the audit trail`; `## Document command summary`.

**Proof**

- The four new tests and the modified drift test fail against today's files
  for the stated reason (recorded in `outcome.md`), then pass.
- Mutation check on the drift test: paste one default paragraph back into the
  skill body, see the converted-case assertion go red, remove it, confirm with
  `git diff`.
- `pytest tests/test_unattended_work_skill.py tests/test_shipped_procedures.py
  tests/test_dynamic_skill_marker.py tests/test_plugin_manifests.py
  tests/test_skill_lifecycle_parity.py` green.
- The "nothing configured = today's text" diff (spec criterion 7): replace the
  injection line in the new body with `tcw work procedure prompt
  unattended-work` output and diff against
  `git show main:skills/tcw-extras-autonomous-work/SKILL.md`; every hunk
  explained in `outcome.md`.

### 2. Ledger

**Files**

- `docs/work/active/<slug>/capabilities.yaml` — `changed: [skills/tcw-extras-autonomous-work]`.
- `docs/capabilities/skills/tcw-extras-autonomous-work/description.md` — says
  the two advisors, the never-cut-a-version and never-push behaviour are TCW's
  default, which a project replaces under `work.procedures.unattended-work`.
  Status untouched.

**Proof** `tcw capabilities check` exits 0 (spec criterion 9).

### 3. Documentation Sync

Evaluated against the finished diff:

- `README.md` — **[Public-API]** — fires weakly: the skills table row says
  "asking two read-only advisors", still true by default. Update to say the
  advisors are a default the project can replace.
- `docs/guide/jira.md` — **[Tracker-Change]** — does not fire; no tracker
  command, lifecycle effect on a ticket, or `work.tracker` key changes.
- `docs/release-notes/upcoming.md` — **[Public-API]** — fires: a user-visible
  fact that a project can now replace the unattended skill's advisors, review,
  closeout and version policy. One bullet at the end of the relevant section.
- `docs/changelogs/upcoming.md` — **[Any-Code-Change]** — fires: one bullet at
  the end of `Changed`.
- `skills/<component>/SKILL.md` — **[Skill-Driven-Component]** — does not fire:
  no component's CLI, model, lifecycle or guardrails change; the skill edited is
  the item itself.
- `skills/tcw-configure/references/<document>.md` —
  **[Configuration-Key-Change]** — does not fire: `work.procedures` exists
  already and no key changes meaning. `work.md`'s example already uses
  `unattended-work`.

**Proof** `git diff main -- README.md docs/` shows only those entries; sibling
bullets untouched.

## Verification

What the suite cannot check:

- **An agent reading the injected text runs the default the way it did.**
  Deferred to verify: an unattended run against a real backlog item.
- **A Codex reader finds and follows the fallback block.** Deferred to verify.
- **Claude Code accepts the frontmatter** (`allowed-tools` pre-approving the
  injected command so the skill does not render empty). Only a live session
  shows this; deferred to verify. The test asserts the declaration exists.
- **The full suite, bare**, once, on the final code commit.

## Notes

- **Gate refusal.** `tcw work stage gate plan <slug>` refused: "'plan' is not
  legal for an item in 'active'; it runs in backlog". The bound pre-check
  `TCW_SLUG=<slug> python scripts/require_artifact.py spec` was run by hand and
  exited 0.
- The plan prompt's closing instruction to run `tcw work start` is not followed:
  the item is already active in its worktree, and transitions are forbidden in
  this run.
- No blockers to record: children 1 and 2 are merged.
