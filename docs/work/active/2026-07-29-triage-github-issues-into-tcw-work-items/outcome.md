# Outcome: Triage GitHub issues into TCW work items

All five plan tasks shipped. `python -m pytest` → **1094 passed** (146s);
`tcw validate` → OK; `tcw capabilities check` → OK.

The plan's two named manual checks both paid: the `allowed-tools` cross-read
caught a real defect before commit, and the dogfood run disproved the skill
twice. Neither was found by reading.

## What shipped

### Task 1 — `skills/tcw-triage-issues/SKILL.md` — `4527460`

Single `SKILL.md`, no `references/`. Seven sections: preconditions, sweep,
already-triaged filter, the four triage outcomes, accept, reply, report. Defers
to `stage-inbox.md` for retitling, splitting, and tag choice rather than forking
a second copy.

**The `allowed-tools` cross-read found two gaps** — the check the plan called out
because no test performs it. The body instructs `grep -r docs/work/` and
instructs writing `initial-request.md`; the grant had neither `Bash(grep *)` nor
`Write`/`Edit`. Same class as `daef4da`, caught before commit this time.

**Spec assumption confirmed:** `gh issue list --json comments` does return the
thread with author logins (verified against `brocef/TCW`). So "I already asked
and the reporter has not answered" is answerable from the sweep itself — the
fallback the spec worried about is not needed.

### Task 2 — `commands/tcw-triage-issues.md` — `7483b60`

Routes to the skill, states the Codex fallback, names the direction that
separates it from `tcw-report`. No instruction the skill lacks.

### Task 3 — `stage-inbox.md` pointer — `7483b60`

In `## Purpose`, as the plan required: `test_skill_lifecycle_parity` asserts
every `## Steps` line carries a `[judgment]`/`[gated]` marker, so an unmarked
sentence there would have failed the suite.

### Task 4 — dogfood, **dry run** — `8c9f0dc`, `05d1d13`

Run at the user's direction as a dry run: **no work items created, nothing posted
to GitHub.** What the sweep decided against `brocef/TCW`'s three open issues:

| Issue | Filter result | Triage |
| --- | --- | --- |
| #9 — `tcw` fails inside a git worktree | not tracked | **Worth doing.** Concrete repro, no duplicate in `docs/work/`. Would be `cli`+`bug`. |
| #8 — `reconcile` misreads a valid `capabilities.yaml` | not tracked | **Worth doing.** Concrete repro with the cause named. Would be `cli`+`work`+`bug`. |
| #5 — capability-first lifecycle | **hit** in `docs/work/discarded/` | **Already decided against** — see below. |

### Tasks 5-9 — documentation — `ed1c71c`

All four Documentation Sync entries fired. Three counts were load-bearing prose
that would have gone stale silently: the Codex manifest's "seven skills",
README's "six skills in `skills/`", and README's "five axis/plugin skills".

## What the plan and spec got wrong

Both corrections came from running the procedure on real input.

### 1. "Already tracked" conflated three different states — `8c9f0dc`

Spec §4 and the skill's §3 said a grep hit in `docs/work/` means the issue is
already a work item: report it and move on.

Issue #5 hit `docs/work/discarded/…-capability-first-lifecycle…` — resolution
`superseded`. The project **considered that issue and rejected it**, and the
reporter was never told: the issue is still open on GitHub, still unanswered.
Under the original rule the sweep would have skipped it silently, forever, as
"tracked".

§3 now resolves the slug with `tcw work show` and branches on status —
`backlog`/`active`/`review` is genuinely tracked; `completed` means it already
shipped and the reply says so; `discarded` **is** the "not worth doing" outcome
with the reason already on record. The status is read through the CLI rather than
off the folder name, so the check does not depend on the store's layout.

This is the more valuable of the two findings: the wrong version was silent, and
silent-wrong on an outcome the whole skill exists to produce.

### 2. The spec invented a heading the repo already had — `05d1d13`

Spec §6 prescribed a `**Source:**` line. `docs/work/` has recorded provenance
under **`## Origin`** at the top of `initial-request.md` for months — including
on the item that came from issue #5, which reads "GitHub issue [#5](…), filed
2026-07-18". Items the skill created would have been gratuitously distinguishable
from hand-made ones. Now `## Origin`, with an explicit instruction to follow the
project's own convention where one exists, since this skill ships beyond TCW.

## What is **not** verified

Stated plainly because the plan predicted these and the run confirmed the
prediction rather than the behavior:

- **Acceptance criteria 7 and 8 are unverified.** The dry run exercised the
  preconditions, the sweep, and the already-triaged filter, but created no work
  item — so "every created item's `initial-request.md` contains its issue URL"
  and "a second sweep creates no duplicate" were not executed. The filter's
  read-side is the half that ran; its write-side (§5 writing the URL that §3
  later finds) is checked by reading only.
- **The reply path never ran.** No comment or closure was posted. Criterion 5 —
  nothing posted without per-message approval — is checked by reading the skill.
- **"Preserve a stranger's words" is unexercised**, as the plan said it would be:
  all three issues are authored by the repo owner.
- **Trigger separation from `tcw-report`** remains unfalsifiable here. Whether
  the right skill fires on "check my GitHub issues" is only observable in use.

## Notes

Issues #9 and #8 are real, un-triaged TCW bugs that this run identified as worth
doing but did not convert. They stay open and untracked until a live sweep runs.

`plugin/triage-github-issues` (`cap-2c9a74`) is still `Missing`; the completion
gate flips it.
