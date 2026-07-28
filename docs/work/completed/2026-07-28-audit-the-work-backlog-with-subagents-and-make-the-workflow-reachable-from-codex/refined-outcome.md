# Refined outcome — Audit the work backlog with subagents, and make the workflow reachable from Codex

**Accepted** by the user on 2026-07-28, after two verification rounds and an
empirical trial of the shipped procedure.

Commit range `5e7d130..1123888`. Final state: **1062 passed**, `tcw validate` OK,
`tcw capabilities check` OK.

## The acceptance decision

All nine acceptance criteria met — but only after verification failed once and
was fixed. That sequence is the substance of this artifact, so it is recorded
rather than smoothed over.

| AC | Evidence |
|---|---|
| 1 | `skills/tcw-work/references/audit-backlog.md` — both checklists, dispatch rules, report format, approval rule |
| 2 | Gate line in `SKILL.md`'s "Read on demand" |
| 3 | `commands/tcw-audit-work-backlog.md` — 10 lines, frontmatter + pointer, no checklist copy |
| 4 | **Failed first pass**, then fixed — see below |
| 5 | `tests/test_documented_cli_surface.py`, 99 cases; reproduced the AC4 miss red before fixing it green |
| 6 | `tcw-backlog-auditor` holds no file-editing tools; the overstated "read-only" claim corrected in four places |
| 7 | `.codex-plugin/plugin.json` → "ships seven skills" |
| 8 | 1062 passed; `tcw validate` OK |
| 9 | `2026-07-28-make-the-consolidate-plans-workflow-reachable-from-codex` filed |

## Two defects found *after* implementation reported done

**1. AC6 was overstated (found at verify, round one).** The spec claimed the
custom agent "enforces" read-only "rather than requesting it". Its tool set is
`Read, Glob, Grep, Bash` — and `Bash` can write. Withholding `Write`/`Edit` is
real and narrows the blast radius; the rest is a prohibition honored, not a wall.
Corrected in `tcw-backlog-auditor`, `delegation.md`, `audit-backlog.md`, the
spec's D3, and the **pre-existing identical claim** in `agents/tcw-verifier.md`.

**2. AC4 was not met (found by the trial run, round two).**
`docs/capabilities/work/consolidate-plans/description.md:1` still read *"As a
user, I run `tcw work consolidate-plans [PATH ...]`"* — the phantom verb this
item exists to eliminate, surviving in the capability ledger. Both the manual
grep and the guard test scanned `README`, `skills/`, `commands/`, `agents/` and
stopped there. The root cause was the guard's scan roots, not the missed file, so
the fix was to widen them: capability bodies are user-facing documentation and
name commands like any other doc. That change alone added 52 test cases.

I had reported "all nine acceptance criteria met" before this was found. That
report was wrong, and the guard test I wrote could not have caught it.

## The trial run

The user asked for the shipped procedure to be exercised by an agent given only
the natural request — "audit my work backlog" — with no pointer to the new
reference. Five criteria were pre-registered before results arrived.

| Criterion | Result |
|---|---|
| Discoverability | Found the reference and gate line unprompted |
| Delegation | 12 subagents: 11 per-item + 1 inter-item |
| Pipeline | Inter-item agent consumed the summaries; opened folders only to check candidates |
| Verified vs. prose | Probed all 15 of item 10's line citations individually; labeled its inferences |
| **Beat the baseline** | **Yes** — found everything the sequential run did, plus material on five other items |

**The design question is answered empirically: the fan-out beat the sequential
baseline, and not marginally.** It also found the AC4 defect, which had already
passed verification and would have shipped.

Its own critiques of the procedure were mostly right and are fixed: `--status
review` missing from the inter-item pass (the likeliest near-duplicate, and this
very item was sitting in `review` at the time); "sliding window" prescribing a
mechanism no harness offers; no fallback when `tcw-backlog-auditor` is absent
from a session's roster; no severity scale; no rendering for a healthy item; no
approval granularity; no read-only self-check.

Two of its claims were **wrong** and were not carried forward. It diagnosed the
`commands/` file as a "lossy copy" of the reference — it had actually read the
installed plugin cache at v0.15.4, which predates this work; the working-tree
file is the 10-line pointer. And it recommended dropping `new` from item 10's
scope as "already shipped" — `tcw work new` prints the *file* to edit, not the
item's folder, a distinction that item's spec draws explicitly. Both were caught
by re-checking rather than relaying, which the trial agent itself flagged as the
gap in its process: it never re-verified its own subagents' citations.

## Closeout choices

- **Version: no bump.** Changelog and release notes are updated in place;
  `docs/{changelogs,release-notes}/upcoming.md` carry the entries with the range
  `24f4bc6..0886943`.
- **Merge route:** committed directly to `main`; no worktree or PR was used.
- **Post-mortem: requested by the user**, and run after this item completes.

## Deferred, with homes

- **`consolidate-plans` migration** →
  `2026-07-28-make-the-consolidate-plans-workflow-reachable-from-codex`. Now
  carries a **safety blocker** the trial found: that command holds
  `disable-model-invocation: true` because it deletes files, and skill references
  have no equivalent flag — so migrating it verbatim would remove the guard
  keeping a model from invoking a destructive workflow unprompted.
- **The trial's findings on five other backlog items** — a fourth transactional
  write site (`FsWorkStore.create`, `fs.py:2288-2295`, plain `write_text`), an
  existing fix precedent (`accept_inbox`, `fs.py:2246-2269`), the documented YAGNI
  decision on typed relations (`phase-2-taxonomy.md:157`), and a falsified premise
  in the concurrency item (`node_root = root.parent.parent`, `fs.py:578-585`).
  **Not yet folded into their item folders** — deliberately left out of this item
  rather than widening it. They currently exist only in this session.
- **`docs/work/blocked/.gitkeep`** — tracked, dead (`blocked` is not in
  `WORK_STATUSES`), belongs to no item.

## Notes

The fan-out's real check remains the *next* audit, not this one. A single trial
on an 11-item backlog says the procedure works; it does not say it holds at 60
items, where the batch-of-8 limit starts to bite.
