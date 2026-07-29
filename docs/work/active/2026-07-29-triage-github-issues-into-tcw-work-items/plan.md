# Plan: Triage GitHub issues into TCW work items

Five code/doc tasks and one dogfood run. Nothing here touches `tcw` itself, so
the suite is green at every boundary by construction — the ordering constraint
that matters instead is **the skill exists before anything points at it**, and
**the dogfood runs before the docs claim it works**.

Capability `plugin/triage-github-issues` (`cap-2c9a74`) is already declared
`Missing` with this item as its `Planning doc`, and `capabilities.yaml` lists it
under `new:`. The completion gate flips it.

## Task 1 — Write `skills/tcw-triage-issues/SKILL.md`

The whole deliverable. First because tasks 2-4 all reference it.

**Changes:** new file, single `SKILL.md`, no `references/`.

Frontmatter matching the sibling skills: `name`, `description`, `when_to_use`,
`allowed-tools`, `metadata.author`, `license`. The `description` must state the
*direction* — reads issues on **your own project's** repo — because `tcw-report`
files issues **upstream to TCW** and the two will otherwise collide on trigger.

Body covers spec §2-§7 in order: preconditions, sweep, already-tracked filter,
the four triage outcomes, the accept path, the reply path. It **defers** to
`skills/tcw-work/references/stage-inbox.md` for retitling, splitting one issue
into several items, and tag choice, rather than restating them (spec §1).

**`allowed-tools` is the known trap.** Commit `daef4da` in this repo fixed
exactly this bug in `tcw-plugin`: procedures instructing a command the grant did
not permit, so the frictionless path hit a permission prompt. Every verb the
body instructs goes in the grant — the `gh` **writes** (`issue comment`,
`issue close`) as much as the reads (`auth status`, `repo view`, `issue list`,
`issue view`), plus `tcw`, the `docs/work/` search, `git` for committing the
created item, and `Read`.

**Verified by:** acceptance criteria 1-6. Cross-read every command appearing in
the body against `allowed-tools` — the check is mechanical, do it explicitly
rather than by eye over the finished file. Then
`pytest tests/test_documented_cli_surface.py`, which scans `skills/**/*.md` and
fails on any documented `tcw` verb or flag that does not exist.

## Task 2 — Write `commands/tcw-triage-issues.md`

**Changes:** new file. Frontmatter `description`, a body that names the skill,
and `$ARGUMENTS`.

Follows `commands/tcw-post-mortem.md`: the command routes and states the Codex
fallback; it carries no instruction the skill lacks
(`skills/tcw-work/references/commands.md:45-50` — "Nothing is only available
through a command").

**Verified by:** criterion 1, and reading the command against the skill — every
sentence in the command must be either routing or a restatement of something the
skill already says.

## Task 3 — Point `stage-inbox.md` at the new skill

**Changes:** one or two lines in
`skills/tcw-work/references/stage-inbox.md` saying a GitHub issue is the same
shape from a different source, and naming `tcw-triage-issues`. This is what keeps
the pair connected rather than leaving two intake procedures that don't know
about each other.

**Sequencing note:** put it in `## Purpose`, not in `## Steps`.
`tests/test_skill_lifecycle_parity.py` asserts every stage document has its five
sections in order and that every line in `## Steps` carries a recognized marker
(`[judgment]` / `[gated]`); an unmarked sentence added to `Steps` fails the
suite.

**Verified by:** criterion 6, and `pytest tests/test_skill_lifecycle_parity.py`.

## Task 4 — Dogfood sweep against `brocef/TCW`

The risky task, isolated here: tasks 1-3 give it something to run, and it runs
before the docs describe it as working.

**Changes:** whatever the sweep decides — zero or more work items, zero or more
GitHub replies. No repo files change except the items created.

`brocef/TCW` currently has **three open issues** (#9, #8, #5), so criteria 7-8
are genuinely exercisable rather than vacuous:

- #9 — `tcw` fails inside a git worktree
- #8 — `tcw work reconcile` misreads a valid `capabilities.yaml`
- #5 — capability-first lifecycle proposal

**Verified by:** criteria 7-8. For each issue the sweep accepts, grep its URL in
the created item's `initial-request.md`. Then **re-run the sweep** and confirm it
reports the accepted ones as already tracked and creates nothing new — that
second run is the only thing that actually tests spec §4, and skipping it leaves
the filter unverified.

**Two limits to state honestly rather than paper over:**

1. All three issues are authored by the repo owner, so the sweep does **not**
   exercise "preserve a stranger's words as evidence". That behavior is checked
   by reading the skill text, not by this run.
2. The run posts real, public GitHub replies. Per spec §7 each one needs the
   user's approval of the exact text; do not batch the approvals to get through
   the task faster.

If the user declines every reply, the task still verifies the accept path and
the tracked-filter — say which criteria the run did and did not exercise.

## Documentation Sync

Evaluated against `CLAUDE.md`; all four entries fire. Scheduled as one block
after the code tasks, answered in a single pass over the finished diff.

### Task 5 — `README.md` [Public-API] — fires

New user-facing skill and command. Two places:

- The install section's inventory (`README.md:109-116`) — the skill list and the
  slash-command list.
- The skill descriptions (`README.md:844` neighborhood) — a new bullet whose
  wording states the direction that separates it from the `tcw-report` bullet
  directly above it.

**Verified by:** criterion 10; `pytest tests/test_documented_cli_surface.py`.

### Task 6 — `skills/tcw-plugin/SKILL.md` [Skill-Driven-Component] — fires

The skill map (`:26-31`) and the "Practical routing" list (`:37-47`) enumerate
every skill and when to reach for it. A new skill absent from both is a skill
the router will not route to.

### Task 7 — `.codex-plugin/plugin.json` — fires

`interface.longDescription` enumerates the skills by name and count ("ships
seven skills"). The count is load-bearing prose and goes stale silently.

### Task 8 — `docs/changelogs/upcoming.md` [Any-Code-Change] — fires

Technical, grouped. Added: the skill, the command, the capability. Changed: the
`stage-inbox.md` pointer.

### Task 9 — `docs/release-notes/upcoming.md` [Public-API] — fires

Plain language, no module names: you can point TCW at your project's GitHub
issues, triage them, and turn the worthwhile ones into work items.

## Verification

Beyond the suite:

- **The `allowed-tools` cross-read (task 1).** No test checks that a skill's
  grant covers the commands its own prose instructs. This repo has already
  shipped that bug once (`daef4da`); a manual list-against-list comparison is
  the only check there is.
- **The second dogfood sweep (task 4).** The already-tracked filter has no unit
  test and cannot get one without a fixture repo; running the sweep twice is the
  test.
- **Trigger separation from `tcw-report`.** Unfalsifiable here — whether the
  right skill fires on "check my GitHub issues" is only observable in use.
  Recorded as a known residual risk, not as a passed check.
- **Full suite.** `python -m pytest` (it exceeds two minutes; run it in the
  background rather than assuming the fast subset stands in for it).

## Notes

No blockers. This item touches no file that the active
`auto-install-the-tcw-cli-on-sessionstart-via-a-plugin-hook` item touches except
`README.md` and the two `upcoming.md` working files, all of which are
append-shaped — worth a rebase check at implementation time, not a `--blocked-by`.
