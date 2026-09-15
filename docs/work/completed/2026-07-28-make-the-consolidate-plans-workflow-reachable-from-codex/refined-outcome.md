# Refined outcome — Make the consolidate-plans workflow reachable from Codex

**Verdict: accepted**, by the user on 2026-07-30.

Assessment delegated to the read-only `tcw-verifier`, which tested the safety
rules empirically rather than reading them, and was asked specifically not to
rubber-stamp the item's two judgment calls. The coordinating session re-ran the
suite, verified the gate retention and the `drop` behavior itself, and fixed two
defects the verifier found before acceptance.

## Evidence

All 10 acceptance criteria **met**, plus task 4's four.

| # | Criterion | Evidence |
| --- | --- | --- |
| 1 | procedure moved intact | 63-line reference; diffed against `25a06e5:commands/tcw-consolidate-plans.md`, steps 1-6 carry over, only step 7 changed (to add the gates). Command file retains zero procedure |
| 2 | "start only when asked" at the top | First prose in the body (`:9`), ahead of `## Scope` (`:37`) and `## Process` (`:44`) |
| 3 | grouped approval + recoverability | Second rule at `:16`; dedicated `## Deletion is limited to what git can give back` at `:22` with a two-row check table |
| 4 | flag retained, file is a pointer | Frontmatter *parsed*, not grepped: `disable-model-invocation: true` present; 12 lines; link target resolves |
| 5 | router gate | **met in substance, not literally** — see below |
| 6 | `commands.md` row + standing assertion | Row matches the audit row's shape; all 13 files in `commands/` link into `skills/`, so "Nothing is only available through a command" is **now true** |
| 7 | README | Codex caveat gone; closing sentence mirrors the audit paragraph |
| 8 | capability body | "works the same under either harness"; the confirmation sentence extended to name the grouped approval and the git-committed-only limit, so criterion 3 now backs it |
| 9 | no phantom verb | `.codex-plugin/plugin.json` untouched; `--confirm` is a flag on an existing verb |
| 10 | suite + validate | `1162 passed`; `validate OK`; `capabilities OK` |

## The two judgment calls, pressed rather than waved through

**The merged gate line (correction 3).** The router's 60-line budget forbade the
dedicated "Read on demand" entry both the spec and plan assumed, so the gate
landed by merging bullets. The verifier argued the merge came out **better**, on
two grounds worth recording:

- A dedicated entry would have followed the list's existing shape — filename
  first, gate condition trailing. The merged form puts **"Only when the user asks
  for it"** in bold at the *head* of the bullet, read before either target. For a
  gate, leading is the right position.
- The haystack is a six-item routing list in a 60-line router, which an agent
  reads in full because that is the list's entire function. Missing a bolded
  phrase there is a different risk from missing a line in a long document.

It also noted the merge was not purely a cost: `audit-backlog.md` previously
carried **no** gate and now inherits an accurate one. The real cost is a ~250
character line that wraps badly as raw text — a formatting nit. Criterion 5 is
recorded as satisfied in substance rather than literally, which is what
`outcome.md` claimed rather than papering over.

**The unguarded HTTP DELETE.** `DELETE /api/work/<slug>` → `work.drop(slug)` has
no confirmation parameter. The verifier confirmed both cited mitigations exist
(`web/client/src/ui/app.tsx:963-975` AlertDialog; `web/e2e/parity.spec.ts:579`
drives it) and agreed no item is warranted — standing on the architectural
reason rather than the network one:

> Confirmation is a CLI/UI concern, not a store operation. Pushing it into
> `WorkStore` would fail the abstraction litmus test — a Jira adapter's drop has
> no business demanding a flag. The gate belongs at each user-facing surface, and
> both user-facing surfaces have one.

The store-level `drop()` being unguarded is therefore correct, not merely
tolerated.

## The recoverability rule was tested, not read

Across four git states in a throwaway repo:

```
committed.md     tracked      status=[]                 -> DELETABLE
modified.md      tracked      status=[ M …]             -> skip
untracked.md     UNTRACKED    status=[?? …]             -> skip
staged-only.md   tracked      status=[A  …]             -> skip
```

`staged-only.md` is the trap: `git add` without a commit makes a file *tracked
but unrecoverable*. The rule states the conjunction correctly and catches it.
The old text's single clause ("use `git rm` for tracked files") licensed plain
deletion for untracked files by omission; that is now explicit.

## Defects found in verification, and fixed before acceptance

Both were in code this item introduced, so they were fixed rather than filed
(`9bead09`):

1. **The `drop` gate short-circuited before the existence check**, so
   `tcw work drop no-such-item` printed `Would delete …` and advised `--confirm`
   — and taking that advice produced a second, different error. Existence now
   resolves first: `tcw work drop: no such work item: <slug>`.
2. **The refusal split across stdout and stderr**, so a terminal could interleave
   it backwards. Both lines are now on stderr — nothing succeeded, so nothing
   belongs on stdout. `test_drop_refuses_without_confirm` updated accordingly and
   a new `test_drop_of_a_missing_item_does_not_advise_confirm` pins the first fix.

**Not fixed, on the verifier's recommendation:** two archival documents still show
flagless `tcw work drop` (`docs/migration-guide-0.14.X-to-0.15.0.md:67`,
`docs/plan/phase-5-work.md:206`). The migration guide's claim was true *for
0.15.0*; editing a version-pinned document to describe later releases makes it
less accurate, not more.

## Codex reachability, concretely

`.codex-plugin/plugin.json` exposes `"skills": "./skills/"` and no `commands`
key. A Codex agent loads the `tcw-work` skill → reads the six-line "Read on
demand" list → line 66 names `consolidate-plans.md` behind the bolded gate →
follows a plain relative Markdown link → gets the full procedure with both safety
rules first. **Nothing on that path passes through `commands/`.**

The reference has no frontmatter at all, and no `$ARGUMENTS`, `` !`cmd` `` or
`{{` templating — nothing for Codex to choke on.

## Test changes

Two in `tests/test_work.py`, both legitimate for a breaking interface change:
`--confirm` added to the existing caller (original assertions intact), and a new
refusal test. Coverage went **up**. `tests/test_environment_hardness.py:341` was
correctly *not* modified — it calls `st.drop()` at the store level, which this
change deliberately does not touch.

## Closeout choices

- **Route:** committed directly on `main`; no worktree, no PR. Commits `eb340ea`,
  `fbc206b`, `5ec2558`, `ad7d2ef`, `ea965f0`, `6b53b82`, `08c26a2`, `6c77669`,
  plus the verification fix `9bead09`.
- **Version:** none cut at closeout; folded into the **minor** bump
  (0.17.3 → 0.18.0), confirmed by the user on 2026-07-30. This item contributes
  the release's other breaking change — `tcw work drop` now requires `--confirm`,
  committed as `feat(work)!`. Any script calling `drop` will start failing, and
  the release notes lead with it.
- **Definition of Done:** all six satisfied. The GitHub-issue entry **does not
  apply** — this item was split out of
  `2026-07-28-audit-the-work-backlog-with-subagents-and-make-the-workflow-reachable-from-codex`,
  not filed from an issue.

## Notes

The request's central premise was wrong and the spec corrected it:
`disable-model-invocation: true` is not the guard on the destructive act. It
gates discovery of one command file, while the act is `git rm`/`rm` through Bash
— already inside the `tcw-work` skill's declared tool surface
(`skills/tcw-work/SKILL.md:5`). It is inert under Codex, which never reads
`commands/`, and it stops covering anything once the user invokes the command,
because the old procedure body had no approval step.

So the design kept the flag **and** added the rules, and neither harness lost a
property while Claude gained two. That reframing — from "a hard flag versus prose"
to "a discovery-time flag that ends at the door, versus a rule governing the act
itself" — is the reusable part of this item.

Correction not acted on: the plan header says "Four tasks" and there are five.
Cosmetic; the task bodies are unambiguous.
