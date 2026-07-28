# Spec — Audit the work backlog with subagents, and make the workflow reachable from Codex

Planning is **compressed** at the user's request: this document carries the
design decisions *and* the task list. No separate `plan.md`.

## Capability changes

`changed: [work/audit-work-backlog]` (recorded in `capabilities.yaml`).

The entry is over-claiming today. Its body reads *"As a user, I run
`tcw work audit-work-backlog`"* — a CLI verb that does not exist. The workflow is
real but reached through `/tcw-audit-work-backlog` (Claude) and, after this item,
through the `tcw-work` skill (both harnesses).

**Status stays `Supported`, deliberately.** A case exists for `Partial` — a Codex
user cannot reach the workflow at all today — but this item closes that gap in
the same change, so flipping to `Partial` and back is churn that would leave the
ledger wrong for the duration rather than right. The body rewrite at closeout is
the actual correction.

No new capability. `plugin/work-lifecycle` was checked and does not describe the
audit workflow; it needs no edit. `tcw capabilities check` is clean.

## Problem

Two independent defects, coupled because they live in the same files.

**1. The audit does not scale.** The checklist is eight flat bullets executed
sequentially in one context. Cost grows linearly with backlog size, and the
majority of the checks only ever look at one item — embarrassingly parallel work
being run serially.

**2. The workflow is unreachable from Codex, and the docs paper over it with a
verb that does not exist.**

- `.codex-plugin/plugin.json` exposes `"skills": "./skills/"` and **no
  `commands` key** (unlike `.claude-plugin/plugin.json`). Codex never sees
  `commands/`.
- The entire checklist lives in `commands/tcw-audit-work-backlog.md`.
- The skill's only pointer is `skills/tcw-work/references/commands.md:25`,
  listing `tcw work audit-work-backlog`. That verb does not exist —
  `tcw work` accepts `init inbox nodes reconcile delegate escalate tags new list
  show path start submit rework lifecycle edit complete drop`. `README.md:582`
  and `README.md:713` document the same fiction.

Defect 2 is why defect 1's fix cannot simply be written into `commands/`:
delegation instructions placed there would be Claude-only content, which is
precisely what the CLAUDE.md harness-compatibility rule exists to prevent.

## Goals

- Per-item audit checks run one-subagent-per-item; set-wide checks run once with
  full-set context.
- The audit procedure lives where **both** harnesses read it.
- No document claims a `tcw` verb or flag that does not exist.

## Non-goals

- No `tcw` CLI surface change. In particular, **`tcw work audit-work-backlog`
  will not be built** — see the design decision below.
- No change to what the audit checks *for*, beyond the one added check named
  below. This item changes execution shape and location, not judgment.
- No migration of the `consolidate-plans` workflow (scope decision below).

## Design decisions

### D1 — Two lists, split by context required

| List | Checks |
| --- | --- |
| **Per-item** | already completed · outdated · wrong repository/node · unactionable or oversized · blocked without a next action · capability drift |
| **Inter-item** | duplicate or superseded · **missing relationship edges** (new) · tag hygiene (whole) |

The split axis is *what context a check needs*, not what it is about.
`wrong repository/node` and `capability drift` look set-wide but are not: they
compare one item against a **shared read** (the node registry, the capability
ledger) that any single agent can perform alone.

**User's rule: a check that does not split cleanly goes in the inter-item list.**
That rule decides tag hygiene. "Does this item carry the right tags" reads
per-item, but "does this reveal a broadly useful category missing from the
registry" is visible only across items — and splitting one bullet across two
agents costs more than running it once with full context.

**Missing relationship edges** is new, and comes from the seed run:
`2026-06-19-remote-extends-for-taxonomy` states in prose that
`2026-07-01-transitive-taxonomy-inheritance` "should land first", but `state.yaml`
carries no `blocked_by`, so `tcw work list` shows both as equally pickable.
Prose-stated dependencies that never became recorded edges are a recurring
backlog defect, and only the inter-item agent can see them.

### D2 — Pipeline, not parallel

The per-item agents run first; the inter-item agent consumes their output.

The duplicate and superseded checks need to know what each item is *about* —
which means reading every item folder, exactly the work the per-item agents just
did. Running both lists in parallel from zero pays for that reading twice. Each
per-item agent therefore returns a fixed shape: its findings **plus** a two-line
"what this item is about". The inter-item agent gets those summaries instead of
ten folders, and starts better-informed than a cold read would leave it.

It additionally reads the raw one-line output of `tcw work list --status active`
and `--status completed` (the duplicate check names all three statuses), opening
a folder only when a summary makes a candidate look real.

**Concurrency cap: 8, as a sliding window** — a new item dispatches as each slot
frees, not in fixed sequential batches of eight. Borrowed from Codex's own
`max_concurrent_threads_per_session` default rather than invented. A 60-item
backlog must not spawn 60 agents.

**The fixed shape is a return contract, and the coordinator checks it.**
`references/delegation.md` already states the rule this inherits: *"`Produce` is
the return contract, and must be specific enough to check"*, and a subagent that
fails to produce is a `[judgment]` failure for the coordinating session to catch —
*"check `Produce`, then re-dispatch or escalate."* Applied here: if a per-item
agent returns no summary or a malformed one, the coordinator re-dispatches that
item, or reads that one folder itself and continues. One bad return degrades to
the old sequential cost for a single item; it must never silently drop the item
from the inter-item agent's input.

### D3 — Read-only is enforced by tooling, not just by prompt

Two instructions currently live in the command file's closing paragraph and would
not otherwise reach a subagent's context. They are handled differently, because
only one of them *can* be enforced:

- **Read-only.** Never mutate, transition, or tag. The parent asks the user for
  approval; a subagent has no standing to act. **Enforced by dispatching the
  per-item audit to a custom agent** (`agents/tcw-backlog-auditor.md`) that holds
  no file-editing tools, rather than by asking nicely in a prompt. **Corrected at
  verify:** this narrows the blast radius, it does not make the agent read-only —
  the audit needs `Bash` for `tcw work show` and `git log`, and `Bash` can write.
  Withholding `Write`/`Edit` is real; the remainder rests on the agent's hard
  limits. Do not describe it as enforcement. This passes the exact test
  `references/delegation.md` sets for custom agents — *"a custom agent earns its
  place only when it needs a different tool set or model than the default"* — and
  it is the same test `tcw-verifier` and `tcw-post-mortem` already pass, both
  read-only. Per that document's own rule the agent is an **accelerator only**:
  the reference must stand alone without it, and where custom agents are
  unavailable the instruction degrades to prompt-level.
- **Verify against the working tree; do not summarize the item's prose.** This
  cannot be enforced by tooling — it is a judgment instruction and stays in the
  prompt. It is also where the value is: the seed run's strongest findings — stale
  line citations in a plan, and an item whose stated goal ("fix the README command
  drift") had already been fixed by another item — came only from checking the
  tree. Ten agents summarizing prose would cost more than the sequential run and
  find less.

### D4 — Home: a skill reference, with the command reduced to a pointer

`skills/tcw-work/references/audit-backlog.md` becomes the single source of the
procedure, reached by a gate line in the `tcw-work` router's "Read on demand"
list. This matches the skill-authoring rule in CLAUDE.md — a rare sub-procedure
behind a clear gate, not inlined into a thin router.

`commands/tcw-audit-work-backlog.md` is **reduced, not deleted**: deleting it
would remove the `/tcw-audit-work-backlog` slash command and regress the Claude
UX for no gain. It keeps its frontmatter and becomes a pointer to the reference.

### D5 — Do **not** build `tcw work audit-work-backlog`

CLAUDE.md says "anything that must be guaranteed belongs in the `tcw` CLI", which
argues for building the verb. Rejected: the CLI cannot host an AI-driven review.
The most it could do is *print* the procedure — which would create a second copy
of the checklist that drifts from the skill reference, trading a documentation
lie for a duplication bug. The guarantee is satisfied instead by putting the
procedure in `skills/`, which **both** harnesses load. The three documentation
sites are repointed at the skill, not at a new verb.

### D6 — Scope line on `consolidate-plans`

The sweep of `skills/tcw-work/references/commands.md` found the same defect
twice more:

| Documented | Reality | Sites |
| --- | --- | --- |
| `tcw work consolidate-plans [--apply] [--delete]` | no such verb | `README.md:583-584`, `README.md:720`, `commands.md:26` |
| `tcw work edit --pr <url>` | no such flag | `commands.md:17` |

`consolidate-plans` is the identical pattern: an AI-driven workflow existing only
as a Claude slash command, documented as a CLI verb.

**Decision: fix all three documentation lies here; migrate only the audit
workflow.** Leaving a known-false line two rows below one being corrected in the
same table is indefensible. But migrating a second workflow's checklist is a
second body of content and belongs in its own item. After this change, README
will describe `/tcw-consolidate-plans` as a Claude slash command — honest about
the Codex gap rather than inventing a verb to hide it. **A follow-up item is
filed for closing that gap** (task 8).

## Acceptance criteria

1. `skills/tcw-work/references/audit-backlog.md` exists and holds the full
   procedure: both checklists, the pipeline, the concurrency cap, the per-item
   prompt contract (D3), the report format, and the existing approval rule.
2. `skills/tcw-work/SKILL.md` reaches it from the "Read on demand" list with a
   gate condition.
3. `commands/tcw-audit-work-backlog.md` still exists, still carries its
   `description` frontmatter, and contains no copy of the checklist — only a
   pointer.
4. No file in the repo documents `tcw work audit-work-backlog`,
   `tcw work consolidate-plans`, `--apply`/`--delete` on it, or
   `tcw work edit --pr`.
5. **A test guards criterion 4 going forward**: every `tcw <group> <verb>` and
   flag documented in `README.md` and `skills/**/*.md` exists in the real CLI
   surface. This is the criterion with the most evidence behind it — the same
   defect shipped three times undetected, and both local reviewers independently
   asked for it.
6. `agents/tcw-backlog-auditor.md` exists, is read-only, and the reference works
   without it.
7. `.codex-plugin/plugin.json`'s `longDescription` says seven skills, not six.
8. `pytest` green; `tcw validate` exits 0.
9. A follow-up backlog item exists for the `consolidate-plans` Codex gap.

## Tasks

1. **Write** `skills/tcw-work/references/audit-backlog.md` — port the checklist
   from `commands/tcw-audit-work-backlog.md`, split per D1, add the D2 pipeline
   and cap, the D3 prompt contract, and the new missing-relationship-edges check.
   Keep the existing report format and the "do not silently mutate / ask for
   approval" rule verbatim.
2. **Gate it** from `skills/tcw-work/SKILL.md`'s "Read on demand" list.
3. **Reduce** `commands/tcw-audit-work-backlog.md` to frontmatter + a pointer.
4. **Repoint the docs** — `skills/tcw-work/references/commands.md:25-26`,
   `README.md:582-584`, `README.md:713`, `README.md:720`. Describe both
   workflows by how they are actually reached.
5. **Delete** the phantom `--pr` row at `skills/tcw-work/references/commands.md:17`.
6. **Add** `agents/tcw-backlog-auditor.md` — read-only tool set, mirroring
   `agents/tcw-verifier.md`. Carries the D3 verify-don't-summarize instruction
   and the fixed return shape from D2.
7. **Add the guard test** (acceptance criterion 5) beside
   `tests/test_plugin_manifests.py` — parse `tcw <group> --help` for the real
   verb and flag surface, grep `README.md` and `skills/**/*.md` for documented
   `tcw` invocations, assert every one resolves. Must fail on all three of
   today's bugs before the doc fixes land.
8. **Fix** `.codex-plugin/plugin.json` `longDescription`: six skills → seven.
9. **Correct** the stale "Codex has no subagents" claim in **three** places:
   `AGENTS.md` / `CLAUDE.md` (harness-compatibility section, which lists custom
   subagents as Claude-only), and `skills/tcw-work/references/delegation.md`,
   which asserts it twice — *"A harness without subagents — Codex has none"* and
   *"Codex has no custom agents"*. Codex has both (`.codex/agents/*.toml`,
   model-driven, parallel, `[agents] max_concurrent_threads_per_session`) and
   "respects applicable `AGENTS.md` or skill instructions that request
   delegation" — <https://learn.chatgpt.com/docs/agent-configuration/subagents>.
   This claim nearly forced a pointless sequential fallback into this design.
   **Note:** `delegation.md`'s surrounding doctrine — delegation is an
   optimization, never load-bearing; every stage document stands alone — is
   *correct* and must survive the edit. Only the factual claim changes.
10. **File** the follow-up: `tcw work new "Make the consolidate-plans workflow
    reachable from Codex"`.
11. **Verify**: `pytest` (incl. the new guard), `tcw validate`.
12. **Closeout**: flip the `work/audit-work-backlog` body (see Capability
    changes) before `complete`.

## Documentation Sync (triggers expected to fire)

- `skills/tcw-work/SKILL.md` **[Skill-Driven-Component]** — **fires** (tasks 1-2,
  4-5). The skill gains a reference and loses three false command rows.
- `README.md` **[Public-API]** — **fires** (task 4). It documents two verbs that
  do not exist.
- `docs/release-notes/upcoming.md` **[Public-API]** — **fires.** Codex users gain
  access to the backlog audit; the audit gets faster on large backlogs.
- `docs/changelogs/upcoming.md` **[Any-Code-Change]** — **fires.** Changed:
  audit procedure relocated and parallelized. Fixed: three documented commands
  that did not exist. Include the commit hash range.

## Risks

- **The fan-out finds less than the sequential run.** Ten agents summarizing item
  prose is cheaper and worse than one agent verifying against the tree. D3 is the
  mitigation and it is prompt-level, i.e. not enforceable by a test. Treat the
  next real audit run as the verification, and compare against this session's
  findings as the baseline.
- **Two sources of truth during the change.** Between tasks 1 and 3 the checklist
  exists in two files; task 3 must not be deferred past the same commit.
- **No test covers skill prose.** Criteria 4-8 are mechanically checkable;
  1-3 and 6's "works without it" are review-only. Accepted — the guard test
  (criterion 5) covers the class of defect that actually shipped three times;
  prose quality is not testable and the next real audit run is its check.
- **The guard test's surface walk is coupled to argparse's usage formatting.**
  *(Recorded during implementation — this was not anticipated at spec time.)*
  Subcommand choices and flag choices are both rendered `{a,b,c}`; the walk tells
  them apart by position, stripping `[optional groups]` **and** bare
  `--flag {…}` pairs — the latter because a *required* flag renders unbracketed
  (`tcw work complete --resolution {done,…}`). If that formatting changes, the
  failure mode is an infinite recursion, not a clean error, because
  `tcw work complete done --help` returns `complete`'s own help instead of
  failing. A depth cap of 4 is the backstop.
- **The guard test can only check what it can parse.** It resolves
  `tcw <group> <verb>` and `--flag` tokens from fenced blocks and backticks;
  prose that describes a command without writing it out will slip past. That is
  acceptable — all three of today's bugs are in parseable form — but the test
  must not be read as proving the docs are correct, only that they name no
  nonexistent verb.

## Dismissed review feedback (recorded, not applied)

- *"This is not a code diff; there is no implementation to review"* and *"doc-sync
  triggers are listed but the doc changes are absent"* (qwen25, both blocking) —
  the reviewer read the spec as a diff. This is a pre-implementation artifact by
  definition of the `spec` stage.
- *"Does the subagent harness provide `tcw` as a tool for the inter-item agent?"*
  (gemma4) — yes; both harnesses give subagents shell access by default, and the
  existing `tcw-verifier` / `tcw-post-mortem` agents already run `tcw` this way.
