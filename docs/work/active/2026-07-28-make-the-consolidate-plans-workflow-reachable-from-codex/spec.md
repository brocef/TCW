# Spec — Make the consolidate-plans workflow reachable from Codex

## Capability changes

| Capability | Current | Planned | Delta |
|---|---|---|---|
| `work/consolidate-plans` (`cap-b5e1fa`) | Supported | Supported | **Body rewrite only.** Drop the trailing `Not yet reachable from Codex.` line; state that it works under either harness, as `work/audit-work-backlog` already does. |

No status change: the capability is already `Supported`
(`docs/capabilities/work/consolidate-plans/meta.yaml`), and harness reach is a
claim in its body, not a lifecycle state.

No taxonomy delta. `tcw taxonomy list` holds no term for harnesses, plugins, or
slash commands, and this item introduces no new noun — it moves prose between
files.

The existing body already promises a safety property the procedure does not
deliver, and this item makes it true rather than removing it — see **Problem**,
point 3.

## Problem

**1. Codex cannot run the workflow at all.**
`.codex-plugin/plugin.json:18` exposes `"skills": "./skills/"` and carries no
`commands` key; `.claude-plugin/plugin.json:16-17` carries both. Codex therefore
never loads `commands/`, and the entire procedure lives in
`commands/tcw-consolidate-plans.md:6-37`. That violates `CLAUDE.md`'s harness rule
— *a task a Claude user can accomplish, a Codex user must also be able to
accomplish*.

**2. The docs contradict themselves about it.**
`skills/tcw-work/references/commands.md:33` states the workflow is "Claude only,
not yet reachable from Codex", and `commands.md:50` — seventeen lines later —
states "Nothing is only available through a command." One of those is false.
`README.md:768-769` states the gap honestly.

**3. The confirmation the capability promises is not in the procedure.**
`docs/capabilities/work/consolidate-plans/description.md` (final paragraph) reads
*"Because that step destroys files, it always confirms with me first."* The
procedure it describes says no such thing. `commands/tcw-consolidate-plans.md:33-34`
gates deletion on artifacts being *"written and verified"* — a completeness
check, not a user approval — and names no approval step anywhere. Today the only
thing standing between a Claude session and unprompted bulk deletion is
`disable-model-invocation: true`, and once a user types `/tcw-consolidate-plans`
that guard is spent: the procedure then deletes without asking again.

**4. Moving the procedure as-is would carry that gap into a second harness.**
`commands/tcw-consolidate-plans.md:3` carries `disable-model-invocation: true`;
`commands/tcw-audit-work-backlog.md` does not. Skill references have no equivalent
frontmatter. Migrating verbatim, the way the audit workflow was migrated
(`docs/work/completed/2026-07-28-audit-the-work-backlog-…/outcome.md:11-13`), would
publish a delete-files procedure into a model-invocable skill with no approval
rule in it.

### What the flag actually guards — the correction that resolves the tension

The request treats `disable-model-invocation: true` as the guard on the
destructive act. It is not. Three checks:

- **It gates discovery of one file, not the capability.** The destructive act is
  `git rm` / `rm` through Bash, available in every session regardless. The flag
  removes this command from the set the model may auto-select; it does not remove
  the model's ability to delete files. `skills/tcw-work/SKILL.md:5` already
  declares `allowed-tools: Bash(tcw *), Bash(git *), Read, Edit, Write` — `git rm`
  is inside the `tcw-work` skill's declared tool surface today, before this change.
- **It is inert in the harness the parity gap is about.** Codex never reads
  `commands/` (point 1), so under Codex the flag protects nothing. Codex's current
  safety property is *"the workflow does not exist"*, not *"the workflow is
  guarded"* — and that is precisely the property this item is chartered to remove.
- **It stops covering anything after the user invokes the command.** Per point 3,
  the procedure body has no approval step. The flag is a barrier at the door with
  an unguarded room behind it.

So the honest framing is not *"a hard flag versus prose"*. It is *"a
discovery-time flag that ends at the door, versus a rule that governs the act
itself"* — and the design below keeps the flag **and** adds the rule, so neither
harness ends up worse than it is now.

**5. Repo-wide sweep for the sibling defect.** All 13 files in `commands/` were
checked for the defect class *"a command file that is the sole home of a
procedure"*. Every one except `tcw-consolidate-plans.md` links into `skills/`, and
every link target exists (`skills/documentation-sync/references/cut-version.md`,
`…/setup.md`, `skills/tcw-capabilities/references/init.md`,
`skills/tcw-plugin/references/doctor.md`, `skills/tcw-post-mortem`,
`skills/tcw-taxonomy/references/init.md`, `skills/tcw-triage-issues`,
`skills/tcw-work`, `…/references/audit-backlog.md`, `…/stage-inbox.md`,
`…/stage-postmortem.md`, `…/stage-verify.md`). `tcw-consolidate-plans.md` is the
only command file containing zero `references/` links. **This item closes the last
instance in the repo.**

## Goals

1. A Codex agent can run plan consolidation end to end from the `tcw-work` skill,
   with no `commands/` access.
2. `/tcw-consolidate-plans` keeps working for Claude users.
3. The workflow gains a written approval gate on deletion, closing the gap in
   Problem 3 — under both harnesses.
4. Deleting a source document becomes **recoverable**, not merely approved.
5. The three self-contradicting or now-stale doc sites are corrected.

## Non-goals

- **No `commands` key in `.codex-plugin/plugin.json`.** Codex has no slash
  commands (`README.md:126`); the key would be inert.
- **No `tcw` CLI verb.** Rejected with reasoning in Design, D4.
- **No subagent fan-out.** Decided against in Design, D6.
- **No change to what the procedure does** — same discovery heuristics, same
  document classification, same artifact mapping. This item relocates and gates
  it; it does not redesign it.
- **`tcw work drop` has no `--confirm` gate** (`tcw work drop --help` shows only
  `slug`), unlike `complete`. That is an adjacent destructive-operation
  observation, deliberately out of scope, and belongs to no item.
- No version bump decision; that is a closeout call.

## Design

**D1 — The procedure moves to `skills/tcw-work/references/consolidate-plans.md`.**
Same content as `commands/tcw-consolidate-plans.md:6-37`, plus D2 and D3. Opens
the way `audit-backlog.md:3-6` does: states it is an AI-driven workflow with no
`tcw` verb, names the Claude slash command, and states this document is the
procedure under any harness.

**D2 — The reference carries a destructive-workflow gate, at the top, not the
bottom.** Two rules, modeled on the approval rule already in
`audit-backlog.md:125-138`:

- **Start only when asked.** Do not begin a consolidation run on your own
  initiative — not while doing adjacent work in `docs/`, not as a tidy-up. This is
  the property `disable-model-invocation: true` supplies to Claude; written here,
  Codex gets it too.
- **Never delete without a grouped, itemized approval.** Present every source
  document proposed for deletion by path, with its destination slug, as one ask.
  Not per file (unusable) and not a blanket yes (the audit's reasoning,
  `audit-backlog.md:129-134`).

**D3 — Deletion is restricted to what git can give back.** Delete only files git
has already committed, and only with `git rm`. A source that is untracked, or
tracked with uncommitted modifications, is **reported and left in place** — its
content exists nowhere else, so removing it is unrecoverable. The current text
(`commands/tcw-consolidate-plans.md:34`) says "use `git rm` for tracked files",
which implies plain deletion for untracked ones; that is the irreversible case
and this closes it. Checkable by a third party with `git ls-files
--error-unmatch <path>` and `git status --porcelain <path>`.

This is where the real guarantee lands. The property worth guaranteeing is
*recoverability*, and git already provides it for committed content — no new
mechanism, and it behaves identically under both harnesses because it is git, not
harness configuration.

**D4 — Why not a `tcw` CLI verb.** `CLAUDE.md` says anything that must be
guaranteed belongs in the CLI, and the option was taken seriously. It is rejected:
a verb would accept arbitrary paths outside the store, and there is nothing it
could enforce that `git rm` on committed content does not already enforce — it
would add CLI surface, a second deletion path to keep correct, and no new
guarantee. The judgment the workflow needs (is this a plan? how does its content
map onto lifecycle artifacts?) cannot move into a CLI at all, which is why the
capability body already says so. The guarantee moves to git (D3) instead of to
new code.

**D5 — `commands/tcw-consolidate-plans.md` is reduced to frontmatter plus a
pointer, and *keeps* `disable-model-invocation: true`.** Same shape as
`commands/tcw-audit-work-backlog.md:1-11`. Nothing about Codex parity requires
dropping the flag; retaining it costs nothing and leaves Claude's auto-invocation
surface strictly unchanged. Net effect per harness:

| | Today | After |
|---|---|---|
| Claude | flag; no approval rule; untracked sources deletable | flag **kept**; approval rule; only recoverable deletions |
| Codex | workflow unreachable | workflow reachable, arriving with approval rule + recoverability rule |

Neither harness loses a property. Claude gains two.

**D6 — No per-item subagent fan-out.** The audit's fan-out won because its
per-item work is *verification against the working tree* — independent, read-only,
and its whole value is not summarizing prose (`audit-backlog.md:91-95`); it beat
the sequential baseline empirically (`…/refined-outcome.md:60-64`). Consolidation
is a different shape: each document's work is read-then-**write** (`tcw work new`
plus artifacts), i.e. sequential state mutation in `docs/work/`, and the audit
procedure explicitly withholds mutation authority from its agents
(`audit-backlog.md:84-86`). Fanning out would dispatch exactly the authority the
sibling design was careful to keep in the session holding the user relationship —
to parallelize the reading of what is typically a handful of documents. Skipped;
revisit if a run routinely exceeds ~20 sources and reading dominates.

**D7 — Documentation sites, all four:**

- `skills/tcw-work/SKILL.md:66` area — add a gate line to "Read on demand" for
  `consolidate-plans.md`.
- `skills/tcw-work/references/commands.md:27-33` — the "Not CLI subcommands" table
  says "**Two** workflows"; the row for this one becomes
  `[consolidate-plans.md](consolidate-plans.md) — any harness ·
  /tcw-consolidate-plans in Claude`, matching the audit row (line 32).
- `skills/tcw-work/references/commands.md:50` — "Nothing is only available through
  a command" becomes true on completion; no edit needed, but it is the assertion
  this item is validating and it must be re-read at verify.
- `README.md:765-769` — drop "(This one is not yet reachable from Codex.)" and say
  the procedure lives in the `tcw-work` skill so it works under either harness,
  mirroring `README.md:762-763`. `README.md:114` lists `/tcw-consolidate-plans`
  among the shipped commands and stays correct as-is.
- `docs/capabilities/work/consolidate-plans/description.md` — per **Capability
  changes**.

**D8 — Phantom-verb guard: already covered, nothing to add.**
`docs/capabilities/work/consolidate-plans/description.md` was already rewritten by
the sibling item and names no `tcw work consolidate-plans` verb; it now says
`/tcw-consolidate-plans` in Claude Code.
`tests/test_documented_cli_surface.py:44-65` derives its file set by *exclusion*
from `git ls-files --cached --others`, so every non-archival Markdown file —
capability bodies and the new reference alike — is in scope the moment it exists,
with no edit to the test. Per the request's own closing note, no new test is
expected, and none is proposed.

## Acceptance criteria

1. `skills/tcw-work/references/consolidate-plans.md` exists and contains the whole
   procedure: discovery scope and exclusions, the three-way document
   classification, item creation, artifact mapping, and the source→slug report.
   Nothing needed to run the workflow is reachable only from `commands/`.
2. **Safety, start:** that reference states, before any procedural step, that the
   workflow is run only on explicit user request and never on the agent's own
   initiative.
3. **Safety, deletion:** that reference states that no source document is deleted
   without a grouped approval naming every file by path, and that deletion is
   limited to files git has committed, removed with `git rm`; untracked or
   uncommitted sources are reported and left in place. A reader can point at the
   two rules; they are not implied by surrounding prose.
4. `commands/tcw-consolidate-plans.md` is frontmatter plus a pointer to that
   reference, contains no copy of the procedure, and its frontmatter still carries
   `disable-model-invocation: true`.
5. `skills/tcw-work/SKILL.md`'s "Read on demand" list carries a line for
   `consolidate-plans.md` with a gate condition.
6. `skills/tcw-work/references/commands.md` no longer describes the workflow as
   Claude-only; its row points at the reference in the audit row's format; and
   line 50's "Nothing is only available through a command" is true when re-read
   against `commands/` — every command file links into `skills/`.
7. `README.md` no longer states the workflow is unreachable from Codex, and says
   the procedure lives in the `tcw-work` skill.
8. `docs/capabilities/work/consolidate-plans/description.md` drops the "Not yet
   reachable from Codex" line and states it works under either harness; the
   sentence promising confirmation before destruction survives and is now backed
   by AC3. `tcw capabilities check` passes.
9. No `commands` key is added to `.codex-plugin/plugin.json`; no new `tcw` verb
   appears in `tcw --help` or its subcommand tree.
10. Full suite green (baseline 1062 at the sibling item's close), `tcw validate`
    OK.

## Risks

- **Prose is not a flag.** AC2 and AC3 are instructions an agent can ignore, where
  `disable-model-invocation: true` is enforced by the harness for Claude. Accepted
  because the flag never covered the destructive act (Problem, "What the flag
  actually guards") and is retained regardless (D5) — and because D3 makes the
  residual failure mode *recoverable* rather than *silent*. The unmitigated case is
  an agent that both ignores the approval rule and deletes an uncommitted file.
- **Deletion via `git rm` is only as recoverable as the commit is reachable.** A
  deletion committed and then rewritten away (rebase, amend, force-push) loses the
  content. Out of scope; the same is true of every file in the repo.
- **Making the workflow model-invocable in Codex is a genuine widening.** Codex has
  no `disable-model-invocation` equivalent, so AC2 is the only barrier there. The
  alternative — accepting the Codex gap permanently — was considered and rejected
  because it contradicts a standing `CLAUDE.md` directive; if the user prefers the
  gap, this item should be discarded rather than narrowed, since a half-migration
  is worse than either end state.
- **The reference is the third procedure document in `tcw-work`'s router**
  (`audit-backlog.md`, the seven stage docs, now this). Router bloat is a known
  cost of the pattern; `CLAUDE.md`'s skill-authoring rule anticipates it, and one
  gated line is the price.
- **`commands.md:50` becomes an assertion nobody re-checks.** It was false for
  weeks. Its truth now depends on every future command file linking into
  `skills/` — a convention, not a test. Noted, not fixed here.

## Notes

- **Where the request is wrong.** It states the flag is carried by "three command
  files — this one, `tcw-doctor`, and `tcw-init`". There is no
  `commands/tcw-init.md`; the flag appears in exactly **two** files,
  `commands/tcw-consolidate-plans.md:3` and `commands/tcw-doctor.md:4`.
  `docs/changelogs/v0.9.0.md:15-18` added it to four (`tcw-init`, `tcw-doctor`,
  `tcw-drive-work-to-completion`, `tcw-consolidate-plans`); two of those have since
  lost the flag or the file. This does not change the argument — it weakens the
  "rare and deliberate" framing slightly and is recorded for accuracy.
- The request also asks whether the capability body "claims a
  `tcw work consolidate-plans` CLI verb that never existed". It did; the sibling
  item already fixed it (`…/refined-outcome.md:36-43`) and the body now names only
  the slash command. Nothing to fix — see D8.
- **Assumption, not grounded:** whether a skill's `allowed-tools` in
  `skills/tcw-work/SKILL.md:5` *pre-approves* `Bash(git *)` at the permission
  prompt, or merely bounds what the skill may reach for, is harness behavior I did
  not verify. The argument in Problem does not rest on it — it rests on `git rm`
  being reachable from any session with Bash, which needs no frontmatter at all.
- Litmus test: not applicable. Nothing here touches a store interface; this is
  plugin packaging and skill prose.
