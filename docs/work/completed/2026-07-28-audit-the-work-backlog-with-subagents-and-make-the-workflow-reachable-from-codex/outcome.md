# Outcome — Audit the work backlog with subagents, and make the workflow reachable from Codex

Commit range `5e7d130..3633c30` (the `start` transition through doc sync).
Full suite: **1010 passed**. `tcw validate`: **OK**.

## What shipped, task by task

| # | Task | Commit | Notes |
|---|---|---|---|
| 7 | Guard test for documented CLI surface | `6e63405` | Written first, committed red — failed on exactly the three phantoms |
| 1 | `references/audit-backlog.md` | `a5bc076` | Both checklists, pipeline, cap, prompt contract, report format, approval rule |
| 2 | Gate line in `tcw-work` SKILL.md | `a5bc076` | "Read on demand" list |
| 3 | `commands/tcw-audit-work-backlog.md` reduced | `a5bc076` | Frontmatter + pointer; slash command preserved |
| 6 | `agents/tcw-backlog-auditor.md` | `a5bc076` | Read-only tool set, mirrors `tcw-verifier` |
| 4 | Repoint the docs | `dbb2340` | `commands.md` "Not CLI subcommands" table; two README sites |
| 5 | Delete phantom `--pr` row | `dbb2340` | |
| 8 | Codex manifest: six skills → seven | `dbb2340` | `tcw-post-mortem` was the missing one |
| 9 | Correct the Codex-subagent claim | `dbb2340` | Three sites, not the two the spec predicted — see below |
| 10 | File the follow-up | `7ab49ae` | `2026-07-28-make-the-consolidate-plans-workflow-reachable-from-codex` |
| 11 | Verify | — | 1010 passed; `tcw validate` OK |
| — | Documentation sync | `3633c30` | README + SKILL.md answered in-task; changelog + release notes here |

Task 12 (the `work/audit-work-backlog` capability body rewrite) is a **closeout**
step and is deliberately not done yet — it belongs immediately before
`tcw work complete`.

## Where the spec was wrong

**1. The guard test was far harder than "a grep".**

Two separate corrections, and it matters which came from where. The first
acceptance criterion originally read "verified by grep" with the test itself
"recommended, not required" in Risks — that was caught by the **local review
round, before any code**, and the spec was amended then.

What **implementation** disproved is the remaining assumption underneath: that
this is a cheap check at all. A grep cannot distinguish a real verb from a
phantom without knowing the real surface, so the test walks `tcw --help`
recursively — and that walk hit two traps neither the spec nor either reviewer
anticipated:

- **argparse spells flag choices and subcommand choices identically.**
  `--status {backlog,active,…}` looks exactly like `{init,inbox,nodes,…}`. The
  first fix stripped bracketed groups, which handles optional flags.
- **That was not enough, because `tcw work complete` takes a *required*
  `--resolution {done,duplicate,superseded,wontfix}`**, which argparse renders
  **unbracketed**. Worse, `tcw work complete done --help` returns `complete`'s
  own help rather than failing — so the walk recursed until the stack gave out.
  Fixed by stripping `--flag {…}` pairs before looking for the positional slot,
  plus a depth cap as a backstop.

Recorded in the spec's Risks section, because it is a live maintenance hazard:
the walk depends on argparse's usage-line formatting, and the failure mode is an
infinite recursion rather than a clean error.

**2. The spec said the stale Codex claim lived in two places. It lived in three.**

`AGENTS.md`/`CLAUDE.md` was known. Reading `delegation.md` to check the existing
subagent doctrine turned up two more assertions — *"A harness without subagents —
Codex has none"* and *"Codex has no custom agents"* — in the very file the new
reference delegates to. Task 9 was widened before implementation; the spec text
already reflects it.

**3. The first guard test had a coverage hole the spec did not predict.**

It initially scanned only backtick spans, which missed `README.md:582-584` — the
fenced command-reference block, where two of the three phantoms lived. A guard
that misses the primary format is worse than none, because it reads as proof. Now
scans fenced blocks too.

## What reading `delegation.md` changed

The spec's D2 and D3 were improved by house doctrine already in the repo rather
than by invention:

- Its rule *"`Produce` is the return contract… check `Produce`, then re-dispatch
  or escalate"* is exactly the missing-summary degradation path the local review
  asked for. Inherited rather than re-invented.
- Its custom-agent test — *"earns its place only when it needs a different tool
  set"* — is what justified `tcw-backlog-auditor`, and made read-only
  **enforced** rather than requested. Both existing agents pass the same test.

`delegation.md` gained a line stating that a read-only tool set is the strongest
reason to define an agent, since that reasoning was implicit before.

## Scope held

The sweep found the identical defect in the `consolidate-plans` workflow. Per the
spec's D6 line, its **documentation lies were fixed** (they sat two rows from
lines being corrected in the same table) but its **procedure was not migrated** —
that is a second body of content, and it is now item
`2026-07-28-make-the-consolidate-plans-workflow-reachable-from-codex`. README now
states plainly that consolidating plans is Claude Code only.

## Notes

- The audit's real verification is the next audit run, not the test suite. No
  test can tell whether ten subagents verify against the tree or merely summarize
  prose, and that distinction is the whole value. This session's sequential audit
  of the 10-item backlog is the baseline to compare against.
- `docs/work/blocked/.gitkeep` is still tracked and still dead (`blocked` is not
  in `WORK_STATUSES`). Noted during the audit, out of scope here, belongs to no
  item — a one-line cleanup for whoever wants it.
