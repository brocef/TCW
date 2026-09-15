# Spec — Add a tcw-work-create skill that checks for overlap before creating a work item

## Capability changes

Planned ledger and taxonomy changes only. Nothing is written at this stage.

**Order when writing:** the Feature first, then the capability that names it.
`tcw capabilities set` refuses a `Feature` that does not resolve.

### Taxonomy

**New Feature — `tcw-work-create-skill`** ("TCW Work Create Skill"), set with
`-s tcw-work-create-skill`. It follows the one-Feature-per-skill convention from
`2026-09-14-consolidate-the-setup-skills-into-a-single-tcw-setup-skill`, whose
Features look like `docs/taxonomy/tcw-work-stage-skill/meta.yaml:1-7`.

- `relatesTo`: `work-inbox`, `tcw-work-skill`.
- `vocabulary`: `skill`, `work-item`, `work-item/intake`. All three are already
  registered.
- Description: "The TCW plugin skill for turning an idea for a piece of work into
  a new work item, an amended existing one, or nothing, after checking what is
  already tracked."

No new Vocabulary.

### Capabilities

```yaml
new:
  - skills/tcw-work-create
```

**`skills/tcw-work-create`** — "Offer a skill dedicated to instructing agents how
to turn an idea into a work item without duplicating tracked work".
`Status: Supported`, `Feature: tcw-work-create-skill`, `Subject: [skill]`. Its
description is written in the ledger's "As a user or agent, I …" form (see
`docs/capabilities/skills/tcw-work-stage/description.md`) and says:

- what goes in: an idea;
- the five outcomes that can come out;
- that it runs unattended with defaults.

No existing capability changes. `work/open-a-work-item` describes the CLI verb,
and this item does not change the CLI.

## Problem

1. **Nothing tells an agent to check what is already tracked before it runs
   `tcw work new`.** The instruction closest to mid-task discovery says only
   `tcw work new "<deferred item>"` (`skills/tcw-configure/references/docs-sync.md:46-55`).
   `tcw-commands-plan-work` turns a chat request into an item with no overlap step
   at all (`skills/tcw-commands-plan-work/SKILL.md:3-4`). The result is duplicate
   items, and new information that never reaches the item it belongs to.
2. **The overlap judgment that does exist is written four times, and each copy
   covers a different set of places:**
   - the CLI's inbox prompt: "Already tracked… Record the overlap on the item that
     exists" (`tcw/work/prompts/inbox.md:44`);
   - the backlog audit's "Duplicate or superseded" check
     (`skills/tcw-work/references/procedures/audit-backlog.md:44-46`);
   - issue triage: "search **both** queues"
     (`skills/tcw-extras-triage-issues/SKILL.md:117-120`);
   - plan migration: "already represented by an existing TCW work item"
     (`skills/tcw-work/references/procedures/consolidate-plans.md:51`).

   None of the four looks in the work inbox. Inbox entries are not items, so
   `tcw work list` never shows them; only `tcw work inbox list` does.
3. **No step asks about blockers when an item is created.** The `request` stage
   asks for reference material (`tcw/work/prompts/request.md:21`) but not for
   blockers or origin. A dependency stated only in prose leaves the board showing
   the item as ready to pick up. The audit catches this only after the fact
   (`audit-backlog.md:47-49`).
4. **An agent in the middle of other work will not find the procedure unless it
   has its own trigger.** Reference documents under `tcw-work` are read only after
   `tcw-work` has loaded and routed to them (`skills/tcw-work/SKILL.md:58-65`). An
   agent deciding whether to load anything sees only skill names and
   descriptions.
5. **Searching the backlog costs context.** The agent that notices the idea is
   usually busy with something else.

## Goals

1. A new core skill, `tcw-work-create`, whose description makes agents reach for
   it on their own when they notice work that should be tracked. It turns one
   idea into exactly one reported outcome.
2. The procedure runs **unattended** with defined defaults as well as
   interactively, so a working agent can hand an idea to a subagent and get a
   result back: an idea goes in, and a work item may or may not come out.
3. **One shared, read-only overlap procedure.** The new skill, the inbox stage
   document, the backlog audit, issue triage and plan migration all use it, and
   each keeps its own rules for what to do with a match.
4. The overlap search covers **inbox entries** as well as open items.
5. Creation records blockers, reference material and origin on the item.
6. Works identically under Claude and Codex.

## Non-goals

- **External trackers (Jira).** The skill only has to behave sensibly when strict
  mode refuses `tcw work new` (D6).
- **Another agent changing the matching item while the search runs.** No re-check
  before amending.
- **Messaging, or finding, the agent that is working an active item.**
- **Any change under `tcw/`**, including the CLI's own stage prompts
  (`tcw/work/prompts/*.md`). The CLI's one-line "Already tracked" exit stays as it
  is; the skill-side stage document points to the shared procedure. This also
  keeps the CLI usable while this item is implemented (see the `AGENTS.md`
  exception).
- **A new agent definition.** See D5.
- **Running the eval harness.** A case is added but not run, because runs are
  blocked on `2026-09-15-eval-runs-under-this-checkout-grade-and-behave-wrongly`.
- **Searching connected projects** (`tcw work list -i`). Deciding which node an
  item belongs in is the audit's job, and fanning the audit out across nodes is
  `2026-09-01-fan-the-backlog-audit-out-across-every-connected-work-root`.
- **Deliberate structural creation:**
  - children with `--parent` (`procedures/decompose.md`);
  - epic tasks with `--initiative` (`epic-deltas.md`, `cross-node-deltas.md`);
  - splitting one inbox entry into several items.

  The caller already knows these are new pieces of known work.
- **Changing the audit's pipeline shape**: per-item agents, two-line summaries,
  batches of 8.
- **A CLI verb for writing or amending an inbox entry.** See Risks.

## Design

### D1 — The skill: `skills/tcw-work-create/SKILL.md`

**Name.** `tcw-work-create` is a plain `tcw-*` name, which the restructure
reserved for core skills. The other groups are `tcw-commands-*` for workflow
entry points and `tcw-extras-*` for optional skills
(`docs/work/completed/2026-09-14-restructure-…/spec.md:139-142`). A skill agents
invoke on their own, mid-task, is core, and `tcw-work-stage` is the precedent for
the `tcw-work-` prefix. `tcw-work-create` is not in `DELETED_NAMES`
(`tests/test_skill_lifecycle_parity.py:503-512`).

**Frontmatter.**
- The house keys: `name`, `description`, `when_to_use`, `allowed-tools`
  (`Bash(tcw *)`, `Bash(git *)`, `Read`, `Edit`, `Write`), `metadata.author`,
  `license: Apache-2.0`.
- `description` leads with what the skill does.
- `when_to_use` carries the trigger phrases. Two kinds of trigger:
  - **Noticed in passing:** a bug found while doing something else; a follow-up
    or deferred cleanup a task or review leaves behind; "we should also…"; work
    outside the current task's scope that should outlive the session.
  - **Asked for:** "file / track / open / log a work item", "add this to the
    backlog".
- It ends with the house "not for …" clause:
  - children of a known item → `tcw work new --parent`;
  - GitHub issues → `tcw-extras-triage-issues`;
  - inbox triage → `tcw-work`;
  - a bug in TCW itself → `tcw-extras-report` (eval case B6 expects no item);
  - asking which stage should have caught a problem → `tcw-post-mortem` (B9
    expects no item).

  These keep the existing routes that also involve a problem someone noticed.
  `evals/evals.json` pins B6 and B9 to `new_item_count: 0`.
- `description` plus `when_to_use` stays within the 1,536-character combined cap
  from `docs/work/completed/2026-07-02-bring-plugin-skills-into-full-agentskills-claude-spec-compliance/spec.md:118-120`.

**Body: the procedure.** Tables for the branching and checklists for the
questions. Each question says when it is skipped and where its answer is
recorded.

**1. Is the idea understandable?** It needs no detail beyond one sentence saying
what should change and why.

- **User present:** ask.
- **Unattended:** write it as a raw entry into the folder `tcw work inbox path`
  prints, and report `deferred to inbox`. Stop there.

**2. Find overlap** with the shared procedure (D2).

- **Delegate the search** to a read-only subagent by default; the D2 return
  contract is what comes back.
- **Search inline** where subagents are unavailable.

**3. Act on the strongest match:**

| Match | User present | Unattended |
| --- | --- | --- |
| Inbox entry covers it | Append the new information to the entry | Same |
| Open item, no `spec.md` yet (board shows `i` or `R` only) | Append to its body: `initial-request.md` if present, else `intake.md` | Same |
| Backlog item with `spec.md` or `plan.md` | Ask: revise, or leave as is | Revise |
| Item `active` or in `review` | Tell the user the item and the new information; change nothing; move on | Report it the same way |
| Only partly covered, and the new part is separable | Create an item for the new part (step 4), naming the existing item under References | Same |
| Nothing covers it | Create (step 4) | Same |

- **Appending.** New information goes under a dated `## Added <YYYY-MM-DD>`
  heading that says where it came from. Never rewrite what is already there.
  Commit the change on its own.
- **Revising.** Append to the request first; that is the durable record. Then
  re-run `spec`, and `plan` if one exists, as delegated stages under
  `procedures/delegation.md`. Each artifact is committed separately.
- **Closed items.** Completed and discarded items are never "covering" matches.
  A close one is named under References. For a discarded one, tell the user why
  it was discarded, then carry on.

**4. Create.** Ask only what the conversation has not already answered:

| Question | Accepted answers | Unattended default | Recorded as |
| --- | --- | --- | --- |
| Known blockers? | slugs · "no" · a description (search, then confirm) · "determine automatically" (search, no confirmation) | determine automatically | `--blocked-by` per blocker, plus one line per blocker saying why |
| Reference material? | anything given; material already in the conversation counts | take it from context; if none, "no user to ask; none in context" | `## References`, one line of *why it matters* each |
| A bug, or a follow-up to another item? | yes, with the item or symptom · no | infer from context: the item being worked when the idea came up is its origin | `## Origin`, plus the `bug` tag for a bug |

- **"Determine automatically" records a blocker only when the idea cannot proceed
  until the other item lands.** Sharing a topic, touching the same files, or a
  preferred order does not count; those go under References.
- **The body is piped into `tcw work new`**, which stores it as `intake.md`, as
  issue triage already does (`skills/tcw-extras-triage-issues/SKILL.md:128-134`).
  The body carries the `## Origin`, `## References` and blocker lines. Writing
  `initial-request.md` stays the `request` stage's job, so this skill does not
  pull a mid-task agent into a stage.
- Tags come from `tcw work tags list`.
- Commit the new item's folder narrowly (`git commit -- <paths>`), so a working
  agent's own staged changes are not swept in.

**5. Report one outcome**, with its reference and a one-line reason:
`created <slug>` · `amended <ref>` · `revised <slug>` ·
`already in progress <slug>` · `deferred to inbox <entry>`. When the user is
present, the slug is said to them.

**When the run is unattended.** It is unattended when the session was told to
work without asking (for example `tcw-extras-autonomous-work`), or when the skill
runs inside a subagent, which cannot ask. So a working agent that wants the
function shape — an idea goes in, a work item may come out — dispatches a
subagent to run this skill, and gets step 5's outcome back.

### D2 — The shared procedure: `skills/tcw-work/references/procedures/find-overlap.md`

Read-only. It is the home of the "what counts as a match" judgment the four
places in Problem 2 each hold a copy of.

- **Input:** a description of one piece of work.
- **Candidates:**
  - `tcw work list`, which shows open statuses and is `review`-inclusive;
  - `tcw work inbox list`, with `tcw work inbox show` for plausible entries;
  - `tcw work list --all` for closed items, which can only be references.
- **Narrowing:** it narrows and reads bodies by pointing at `search.md` steps 1-2,
  not restating them.
- **Relations.** Each plausible candidate is judged as exactly one of:

  | Relation | Meaning |
  | --- | --- |
  | `covers` | Doing that item would deliver the idea |
  | `partly covers` | It delivers some of the idea; the rest is separable |
  | `blocks` | The idea cannot proceed until that item lands (the D1 rule) |
  | `related` | Shared subject or files, but neither delivers nor blocks the other |

- **Returns:** one line per candidate — `<ref> | <relation> | <status and stage
  letters from the board> | <evidence>`. A final line names the set searched.
  "No overlap" is stated with that set, never left as silence.
- **Consumers keep their own actions** and point here for the judgment:
  - `stage-inbox.md`: a step before accepting;
  - `audit-backlog.md`: the "Duplicate or superseded" check uses these relation
    definitions, and keeps its pipeline;
  - `tcw-extras-triage-issues` §4: the "search both queues" paragraph is replaced
    by a pointer, and the GitHub-specific URL join in §3 stays;
  - `consolidate-plans.md` step 2.

### D3 — Wiring into existing skills

- **`skills/tcw-work/SKILL.md`:** names `tcw-work-create` and `find-overlap.md`.
  Its body is 59 lines against a 60-line budget
  (`tests/test_skill_lifecycle_parity.py:50`, `:277-285`), so both go into
  existing lines.
- **`skills/tcw-commands-plan-work/SKILL.md`:** a chat request with no existing
  item goes through `tcw-work-create`, run with the user present, before the
  `request` stage. An `amended` or `already in progress` outcome stops the
  planning run and reports it.
- **`skills/tcw-configure/references/docs-sync.md:46-55`:** deferred follow-up
  work goes through `tcw-work-create`, not a bare `tcw work new`.
- **Skill documents name one another in words** ("the `tcw-work` skill's
  `find-overlap.md`"), not by path into another skill's `references/`, as
  `tests/test_skill_path_pointers.py` requires for two skills and house style
  does throughout.

### D4 — Registration

- `.codex-plugin/plugin.json:24`: "sixteen skills", plus a clause naming
  `tcw-work-create` (`tests/test_plugin_manifests.py:93-112`).
- `README.md:584-630`: the skill count, the core-skill table, and the grouping
  sentence.
- `evals/evals.json`: a new axis B case, B13, with `invokes: tcw-work-create`.
  This satisfies `tests/test_eval_coverage.py:23-29`.
  - **Prompt:** a user in the middle of the fixture's active item mentions, in
    passing, that sign-in has become slow for accounts with many invoices. The
    fixture's inbox already holds that report
    (`evals/seed_fixture.py:105-108`, `:474-477`).
  - **Assertions:**
    - `tool_input_contains` `tcw-work-create`: the skill was invoked or opened;
    - `new_item_count` 0: the inbox entry covers it, so nothing is created.
  - A `CASE_ROUTING` row in `tests/test_eval_grading.py` pins the routing
    assertion: a run that opened only `tcw-work/SKILL.md` fails it.
  - It is a case, not an `EXCLUSIONS` entry, because automatic invocation is the
    skill's reason to exist and this is the instrument that can measure it.
- The Feature and capability from Capability changes, listed under `new:` in this
  item's `capabilities.yaml`.
- `docs/changelogs/upcoming.md` and `docs/release-notes/upcoming.md`.

### D5 — No new agent definition

`procedures/delegation.md:55-59` allows a custom agent only when it needs a
different tool set or model. Neither delegated shape in D1 meets that:

- **The unattended run writes**, so it needs the default tool set, and the skill
  is already its brief.
- **The read-only search** is the one place an agent could narrow tools. But its
  hard limits would repeat `find-overlap.md`, and `agents/` is Claude-only
  packaging that must stay an accelerator (`docs/lifecycle/harness.md:14`).

It can be added later without changing any document here.

### D6 — Strict tracker mode

Under `work.tracker.strict: true`, `tcw work new` is refused and points to
`tcw work tracker import` (`skills/tcw-work/references/commands.md:202`).

- **User present:** relay the refusal.
- **Unattended:** fall back to a raw inbox entry and report `deferred to inbox`.

Nothing else about trackers is in scope.

### Abstraction and harness checks

- **No store operation is added or changed.**
  - Writing or appending an inbox entry goes through the path
    `tcw work inbox path` resolves. That is the one supported way to find the
    inbox (`commands.md:338-341`), and the same practice `AGENTS.md` prescribes.
  - A non-filesystem store could implement "add a raw inbox entry". The missing
    verb is noted under Risks, not built here.
- **Harness:** every instruction is plain prose plus `tcw` and `git` commands.
  - Delegation is allowed under both harnesses (`harness.md:14`), and every
    delegated step has an inline fallback.
  - No `` !`cmd` `` injection, no hooks, no arguments.

## Acceptance criteria

1. `skills/tcw-work-create/SKILL.md` exists. Its frontmatter parses and carries
   `name: tcw-work-create`, `description`, `when_to_use`, `allowed-tools`,
   `metadata.author` and `license`. `len(description) + len(when_to_use) <= 1536`.
   `when_to_use` contains both trigger kinds from D1: noticed in passing, and
   asked for.
2. The skill body contains:
   - the understandability check with its unattended inbox default;
   - a pointer to `find-overlap.md`;
   - the D1 step 3 table, with rows for an inbox entry, an item without a spec, an
     item with a spec or plan, `active`/`review`, partial coverage, and no match;
   - the D1 step 4 table, with all four blocker answer forms and the
     cannot-proceed rule;
   - `## Origin` and `## References` as the recording headings;
   - the five outcome names from step 5, spelled exactly;
   - the strict-mode fallback.
3. `skills/tcw-work/references/procedures/find-overlap.md` exists. It:
   - names `tcw work inbox list`;
   - defines the four relations `covers`, `partly covers`, `blocks`, `related`;
   - states the return line format;
   - says a search with no match names the set searched;
   - says it is read-only.
4. The following each name `find-overlap.md`:
   - `skills/tcw-work/references/lifecycle/stage-inbox.md`;
   - `skills/tcw-work/references/procedures/audit-backlog.md`;
   - `skills/tcw-work/references/procedures/consolidate-plans.md`;
   - `skills/tcw-extras-triage-issues/SKILL.md`.

   The triage skill no longer contains "search **both** queues".
5. `skills/tcw-work/SKILL.md` names `tcw-work-create` and `find-overlap.md`, and
   `test_the_router_stays_within_its_line_budget` passes.
6. Both `skills/tcw-commands-plan-work/SKILL.md` and
   `skills/tcw-configure/references/docs-sync.md` name `tcw-work-create`.
   `docs-sync.md` no longer contains `tcw work new "<deferred item>"`.
7. `.codex-plugin/plugin.json` says "sixteen skills" and names `tcw-work-create`.
   `README.md` names it in the skills section, and its count says sixteen.
8. `evals/evals.json` has a case whose `invokes` is `tcw-work-create`, and
   `pytest tests/test_eval_coverage.py tests/test_eval_grading.py` passes.
9. `tcw taxonomy show tcw-work-create-skill` and
   `tcw capabilities show skills/tcw-work-create` both resolve. The capability's
   `Feature` is `tcw-work-create-skill`. `tcw capabilities check` and
   `tcw validate` exit 0.
10. `git diff --stat <base> -- tcw/ agents/` is empty, where `<base>` is the commit the implementation started from.
11. Bare `pytest` from the repository root is green.
12. **A dry run of the procedure against this repository's own board**, made by
    following the new skill by hand and recorded in `outcome.md`:
    - An idea restating
      `2026-09-01-fan-the-backlog-audit-out-across-every-connected-work-root`
      yields `covers` for that item.
    - An idea matching an entry in `tcw work inbox list` finds that entry.
    - An idea matching nothing yields "no overlap" with the searched set named.

    Nothing is created, amended or committed during the dry run.

## Risks

- **Automatic invocation is unproven until the eval harness runs**, and that is
  blocked (Non-goals). The description is a best guess until B13 is run.
- **The new trigger can pull existing eval cases off their route**: B1
  (`tcw-work`), B6 and B9. The "not for" clause covers B6 and B9, and B1 creating
  its item through `tcw-work-create` is a correct route. None of this can be
  confirmed until the harness runs.
- **Too much triggering adds noise to the backlog.** An agent may file every
  passing thought. The trigger wording is limited to "should outlive the
  session", and step 1's understandability bar applies. `2026-09-11-refine-the-plugin-skills-and-lifecycle-prompts-against-the-eval-findings`
  is where this gets tuned.
- **An unattended revision rewrites a spec or plan without anyone reviewing it.**
  The requester chose this. Each revision is a separate commit on an item that
  has not started, so it is visible and reversible.
- **A delegated run commits while the working agent is also using git.** A
  concurrent `git commit` can hit `index.lock`. Narrow path commits keep the
  contents apart but do not stop the lock collision. The fallback is to retry
  the commit.
- **No CLI verb adds or amends an inbox entry**, so the skill writes files under
  the resolved inbox path. That path is correct for a filesystem store. A
  non-filesystem store would need `tcw work inbox add`, which is a candidate
  follow-up item, not part of this one.
- **The `tcw-work` body budget is nearly full** (59/60). The pointer has to fit
  into existing lines, or something else has to be extracted.
- **The CLI's inbox prompt keeps its own one-line overlap rule**
  (`tcw/work/prompts/inbox.md:44`). A Codex user reading only
  `tcw work stage prompt inbox` does not see `find-overlap.md`. The stage
  document does carry the pointer, and both harnesses read it.
- **Overlap with other items:**
  - `2026-09-01-fan-the-backlog-audit-out-across-every-connected-work-root` edits
    `audit-backlog.md`.
  - `2026-09-15-rewrite-the-readme-to-a-new-outline` rewrites the README's skills
    section.

  Whichever lands second has to merge the other's text.

## Notes

- **The subagent that mapped touch points called `tcw-work-create` a naming
  violation. I narrowed that finding:** the documented rule reserves plain
  `tcw-*` names for core skills, and `tcw-work-stage` already uses the prefix
  (D1).
- **Codex, consulted during the brainstorm, recommended against a separate
  skill.** It preferred a shared overlap procedure and stronger stages. This spec
  keeps both of those (D2, D3) and adds the skill for the requester's
  automatic-invocation reason.
