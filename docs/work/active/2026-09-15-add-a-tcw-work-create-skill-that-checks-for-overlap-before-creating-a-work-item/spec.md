# Spec — Add a tcw-work-create skill that checks for overlap before creating a work item

## Capability changes

Planned ledger and taxonomy changes only. Nothing is written at this stage.

**Order when writing:** the Feature first, then the capability that names it.
`tcw capabilities set` refuses a `Feature` that does not resolve.

### Taxonomy

**New Feature `tcw-work-create-skill`** ("TCW Work Create Skill"), set with
`-s tcw-work-create-skill`.

- It follows the one-Feature-per-skill convention from
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

**`skills/tcw-work-create`**: "Offer a skill dedicated to instructing agents how
to turn an idea into a work item without duplicating tracked work".

- `Status: Supported`, `Feature: tcw-work-create-skill`, `Subject: [skill]`.
- Its description uses the ledger's "As a user or agent, I …" form (see
  `docs/capabilities/skills/tcw-work-stage/description.md`). It says:
  - what goes in (an idea);
  - the D1 step 5 outcomes;
  - that the search covers the work inbox as well as open items;
  - that it runs unattended with defaults when told to work without asking.

No existing capability changes. `work/open-a-work-item` describes the CLI verb,
and this item does not change the CLI.

## Problem

1. **Nothing tells an agent to check what is already tracked before it runs
   `tcw work new`.**
   - The instruction closest to mid-task discovery says only
     `tcw work new "<deferred item>"`
     (`skills/tcw-configure/references/docs-sync.md:46-55`).
   - `tcw-commands-plan-work` turns a chat request into an item with no overlap
     step (`skills/tcw-commands-plan-work/SKILL.md:3-4`).
   - The expected result is duplicate items, and new information that never
     reaches the item it belongs to. **This is a prediction, not an observation.**
     None of the 170 closed items carries a `duplicate` resolution (158 `done`,
     8 `superseded`, 4 `wontfix`). Duplicates caught at inbox triage never become
     items, though, so that count cannot rule the problem out.
2. **No overlap check covers inbox entries against an idea arriving mid-task.**
   - Inbox entries are not items: `tcw work list` never shows them, only
     `tcw work inbox list` does.
   - The existing checks each serve their own entry point: the CLI inbox prompt's
     "Already tracked" exit (`tcw/work/prompts/inbox.md:44`), the audit
     (`skills/tcw-work/references/procedures/audit-backlog.md:44-46`), issue
     triage (`skills/tcw-extras-triage-issues/SKILL.md:117-120`), and plan
     migration (`consolidate-plans.md:51`).
   - None of them serves an agent that is in the middle of something else.
3. **No step asks about blockers when an item is created.** The `request` stage
   asks for reference material (`tcw/work/prompts/request.md:21`), but not for
   blockers or origin. A dependency stated only in prose leaves the board showing
   the item as ready to pick up. The audit catches this only after the fact
   (`audit-backlog.md:47-49`).
4. **An agent in the middle of other work will not find the procedure unless it
   has its own trigger.** Reference documents under `tcw-work` are read only
   after `tcw-work` has loaded and routed to them
   (`skills/tcw-work/SKILL.md:58-65`). An agent deciding whether to load anything
   sees only skill names and descriptions.
5. **Searching the backlog costs context.** The agent that notices the idea is
   usually busy with something else.

## Goals

1. **A new core skill, `tcw-work-create`.** Its description is meant to make
   agents reach for it on their own when they notice work that should be
   tracked. It turns one idea into exactly one reported outcome.
2. **It runs interactively, handed to a subagent, or unattended.**
   - A working agent can hand the idea to a subagent and get an outcome back.
   - A subagent never answers on the user's behalf. Where a user is present in
     the parent session, the subagent returns a decision request.
3. **The overlap search covers inbox entries as well as open items.**
4. **Creation records blockers, reference material and origin on the item.**
5. **Items land on the board every session sees**, even when the skill runs
   inside an implementation worktree.
6. **It works identically under Claude and Codex.**

## Non-goals

- **External trackers (Jira).** The skill only has to behave sensibly when
  strict mode refuses `tcw work new` (D6).
- **Another agent changing the matching item while the search runs.** No
  re-check before amending.
- **Messaging, or finding, the agent that is working an active item.**
- **Consolidating the existing overlap checks.**
  - The audit, issue triage, plan migration, the inbox stage document and the
    CLI inbox prompt stay exactly as they are.
  - Their rules differ on purpose. For example, the audit counts completed work
    as a duplicate (`audit-backlog.md:44-46`).
  - `2026-09-01-fan-the-backlog-audit-out-across-every-connected-work-root` owns
    any change to the audit's check.
- **Any change under `tcw/` or `agents/`.** This includes the CLI's stage prompts
  (`tcw/work/prompts/*.md`). Keeping `tcw/` untouched also keeps the CLI usable
  while this item is being implemented (the `AGENTS.md` exception).
- **A new agent definition.** See D5.
- **Running the eval harness.** A case is added but not run, because runs are
  blocked on `2026-09-15-eval-runs-under-this-checkout-grade-and-behave-wrongly`.
- **Searching connected projects** (`tcw work list -i`). Deciding which node an
  item belongs in is the audit's job.
- **Deliberate structural creation.** The caller already knows these are new
  pieces of known work:
  - children with `--parent` (`procedures/decompose.md`);
  - epic tasks with `--initiative` (`epic-deltas.md`, `cross-node-deltas.md`);
  - splitting one inbox entry into several items.
- **Forcing one run per finding.** A set of related leftovers, such as one
  review's findings, may still be filed as one inbox entry or one item.
- **A CLI verb for writing or amending an inbox entry.** See Risks.

## Design

### D1 — The skill: `skills/tcw-work-create/SKILL.md`

**Name.** `tcw-work-create` is a plain `tcw-*` name, which the restructure
reserved for core skills
(`docs/work/completed/2026-09-14-restructure-…/spec.md:139-142`).

- The other groups are `tcw-commands-*` for workflow entry points and
  `tcw-extras-*` for optional skills.
- A skill agents invoke on their own, mid-task, is core, and `tcw-work-stage` is
  the precedent for the `tcw-work-` prefix.
- `tcw-work-create` is not in `DELETED_NAMES`
  (`tests/test_skill_lifecycle_parity.py:503-512`).

**Frontmatter.**

- **The house keys:** `name`, `description`, `when_to_use`, `allowed-tools`
  (`Bash(tcw *)`, `Bash(git *)`, `Read`, `Edit`, `Write`), `metadata.author` and
  `license: Apache-2.0`. Long values are double-quoted, because a plain YAML
  scalar containing `": "` fails to parse
  (`tests/test_plugin_manifests.py:139-144`).
- **`description`** leads with what the skill does.
- **`when_to_use`** carries the trigger phrases, of two kinds:
  - *Noticed in passing:* a bug found while doing something else; a follow-up or
    deferred cleanup that a task or review leaves behind; "we should also…";
    work outside the current task's scope that should outlive the session.
  - *Asked for:* "file / track / open / log a work item", "add this to the
    backlog".
- **It ends with a "do not use it for …" clause:**
  - children of a known item → `tcw work new --parent`;
  - GitHub issues → `tcw-extras-triage-issues`;
  - triaging the work inbox → `tcw-work`;
  - a bug in TCW itself → `tcw-extras-report` (eval case B6 expects no item);
  - asking which stage should have caught a problem → `tcw-post-mortem` (B9
    expects no item).
- **Length:** `description` plus `when_to_use` stays within the
  1,536-character combined cap from
  `docs/work/completed/2026-07-02-bring-plugin-skills-into-full-agentskills-claude-spec-compliance/spec.md:118-120`.

**How it runs.** Every run has exactly one mode, decided before step 1:

| Mode | When | Questions |
| --- | --- | --- |
| **Interactive** | The session holding the user runs the skill | Asked of the user |
| **Delegated** | A subagent runs it on a brief from a session that has a user | Answered from the brief; anything left returns `needs decision` |
| **Unattended** | The session was told to work without asking | Answered by the defaults below |

A subagent is *delegated*, never *unattended*, unless its brief says the parent
session was itself told to work without asking.

**The brief** a working agent passes to a subagent:

- the idea, in a sentence or more;
- where it came from: the item being worked, and the review or task that
  surfaced it;
- reference material already in the conversation;
- any answer the user has already given (blockers, and whether to revise);
- the mode: *delegated*, or *unattended* when the parent was told not to ask.

**Step 0 — Use the primary checkout's board.**

- Check whether this is a linked worktree: `git rev-parse --git-dir` differs from
  `git rev-parse --git-common-dir`.
- If it is, run every `tcw` command in steps 2–4 with the working directory set
  to the primary checkout. That is the first `worktree` path printed by
  `git worktree list --porcelain`.
- This follows the precedent that `tcw work complete` runs from the primary
  checkout (`skills/tcw-work/references/transitions.md:103-108`). A search there
  sees items created on `main` since the branch point. An item filed there is
  visible to every session and survives the work branch being discarded.

**Step 1 — Is the idea understandable?** It needs no more detail than one
sentence saying what should change and why. **If it is not understandable:**

- **Interactive:** ask.
- **Delegated:** return `needs decision: clarify`, with the question to ask.
- **Unattended:** write a raw entry (a `# <title>` heading, the idea, and where it
  came from) into the folder `tcw work inbox path` prints. Report
  `deferred to inbox <entry>` and stop.

**Step 2 — Find overlap** with `references/find-overlap.md` (D2).

- In an interactive run, delegate the search to a read-only subagent where one
  can be dispatched, and act on the lines it returns.
- In a delegated or unattended run, or wherever dispatch is unavailable, run it
  inline.

**Step 3 — Act on the result.**

**Picking the governing match** when there are several: `covers` beats
`partly covers`. Among `covers` matches, the one furthest along wins, in this
order: active or review, then backlog with a spec or plan, then
backlog without one, then an inbox entry. Name every other `covers` match in the
report, because two items covering the same work is itself worth telling the
user.

| Governing match | Interactive | Delegated | Unattended | Outcome |
| --- | --- | --- | --- | --- |
| `covers`, and the idea adds nothing the match does not already say | Tell the user | Return it | Report it | `already tracked <ref>` |
| `covers` an item that is `active` or in `review`, with new information | Tell the user the item and the new information; change nothing | Same, returned | Same, reported | `already in progress <ref>` |
| `covers` an inbox entry, or a `backlog` item with no `spec.md`, with new information | Append (rule below) | Append | Append | `amended <ref>` |
| `covers` a `backlog` item that has `spec.md` or `plan.md`, with new information | Ask: revise, or leave as is (leaving still appends to the request) | Append, then return `needs decision: revise <slug>` unless the brief answers it | Append, then revise | `revised <slug>`, or `amended <slug>` |
| `partly covers`, and the rest can be separated | Create an item for the rest (step 4), naming the match under References | Same | Same | `created <slug>` |
| `partly covers`, and the rest cannot be separated | Treat it as `covers` with new information | Same | Same | as that row |
| No match | Create (step 4) | Create | Create | `created <slug>` |

- **Appending** happens only when the idea adds something the match does not
  already say.
  - The addition goes under a dated `## Added <YYYY-MM-DD>` heading that names
    where it came from. Nothing already there is rewritten.
  - An item's body is `initial-request.md` if present, else `intake.md`.
  - An inbox entry that is a folder (`tcw work inbox list` reports its kind) gets
    the addition in its main Markdown file.
  - Commit it on its own (step 4's commit rule).
- **Revising** re-runs `spec`, and `plan` if one exists, after the append.
  - Each stage is gated with `tcw work stage gate`, and each artifact is
    committed separately.
  - Dispatch them as delegated stages under `procedures/delegation.md` where the
    current agent can dispatch. Otherwise run them inline. Report `revised` only
    once both artifacts exist.
  - In an unattended run inside an autonomous-work session, the advisors that
    `tcw-extras-autonomous-work` consults stand in for "ask". The unattended
    default applies only where that skill gives no rule of its own.
- **Closed items** are never governing matches. A close one is named under
  References. For a discarded one, its resolution is reported, and the run
  carries on.

**Step 4 — Create.** Ask only what the brief or conversation has not already
answered, and ask everything that remains in **one** message:

| Question | Accepted answers | Delegated | Unattended default | Recorded as |
| --- | --- | --- | --- | --- |
| Known blockers? | slugs · "no" · a description (search, then confirm) · "determine automatically" (search, no confirmation) | From the brief. If the brief does not say, determine automatically and list what was recorded in the report | Determine automatically | `--blocked-by` per blocker, plus one line per blocker saying why |
| Reference material? | Anything given; material already in the conversation or brief counts, and a request made in chat counts as its own source | From the brief | From context; if there is none, note "no user to ask; none in context" | `## References`, one line of *why it matters* each |
| A bug, or a follow-up to another item? | yes, with the item or symptom · no | From the brief's origin | The item being worked when the idea came up is its origin | `## Origin`, plus the `bug` tag for a bug |

- **A blocker is recorded only when the idea cannot proceed until that item
  lands.** Sharing a topic, touching the same files, or a preferred order does
  not count; those go under References. "Determine automatically" uses step 2's
  `blocks` lines and does not search a second time.
- **The body is piped into `tcw work new`**, which stores it as `intake.md`, as
  issue triage already does (`skills/tcw-extras-triage-issues/SKILL.md:128-134`).
  - It carries a `# <title>` heading, the idea, `## Origin`, `## References`, and
    the blocker lines.
  - Writing `initial-request.md` stays the `request` stage's job, which reads
    intake as its input (`tcw/work/prompts/request.md:6-15`).
- **Tags** come from `tcw work tags list`.
- **Commit** narrowly, in the repository that holds the store:
  `git -C <path that tcw work path prints> commit -- <changed paths>`. A store can
  live in a different Git repository from the code
  (`skills/tcw-work/references/commands.md:338-341`), and a narrow commit keeps
  the working agent's own staged changes out.
- **A batch of related leftovers** may be one item or one inbox entry. The run
  treats the batch as one idea.

**Step 5 — Report exactly one outcome**, with its reference and a one-line
reason:

- `created <slug>`
- `amended <ref>`
- `revised <slug>`
- `already tracked <ref>`
- `already in progress <ref>`
- `deferred to inbox <entry>`
- `needs decision: <clarify | revise <slug> | blockers>`, together with the
  step 2 lines, so the parent can act without searching again.

In an interactive run, the reference is said to the user.

### D2 — The overlap procedure: `skills/tcw-work-create/references/find-overlap.md`

Read-only, and used only by this skill. It lives inside the skill so it adds
nothing to `tcw-work`'s reference set, which a router test requires `tcw-work`
to link in full (`tests/test_skill_lifecycle_parity.py:294-304`).

- **Input:** a description of one piece of work.
- **Candidates:**
  - `tcw work list`, which shows `backlog`, `active` and `review`;
  - `tcw work inbox list`, then `tcw work inbox show <entry>` for any entry
    whose title is plausible;
  - `tcw work list --all`, for closed items, which can only be references.
- **Narrowing:** grep before reading. `tcw work path` with no slug prints the
  store folder, and `tcw work path <slug>` gives one item's folder. Read the body
  (`initial-request.md` or `intake.md`), plus `spec.md` where the body is not
  enough.
- **Relations.** Each plausible candidate is judged as exactly one of:

  | Relation | Meaning |
  | --- | --- |
  | `covers` | Doing that item would deliver the idea |
  | `partly covers` | It delivers some of the idea, not all |
  | `blocks` | The idea cannot proceed until that item lands |
  | `related` | Shared subject or files, but neither delivers nor blocks the other |

- **Returns:**
  - one line per candidate:
    `<ref> | <relation> | <status and stage letters from the board> | <evidence>`,
    with the status and stage letters copied from `tcw work list`, never
    recomputed;
  - for `partly covers`, a note on whether the rest can be separated;
  - a closing `searched:` line naming the sets read.

  When nothing matches, the answer is "no overlap" plus the `searched:` line,
  never silence.

### D3 — Pointers from existing skills

- **`skills/tcw-work/SKILL.md`:** one bullet under `## Read on demand` naming the
  `tcw-work-create` skill. The body is 59 lines against a 60-line budget
  (`tests/test_skill_lifecycle_parity.py:50`, `:277-285`), so it becomes
  exactly 60.
- **`skills/tcw-commands-plan-work/SKILL.md`:** a chat request with no existing
  item goes through `tcw-work-create` in interactive mode before `request`.
  - The chat request itself answers the references and origin questions.
  - If it reports `already tracked`, `amended` or `already in progress`, stop and
    report that.
  - If it reports `revised`, resume from the first missing artifact.
- **`skills/tcw-configure/references/docs-sync.md:46-55`:** the
  `tcw work new "<deferred item>"` block becomes a one-line pointer to the
  `tcw-work-create` skill.

Skill documents name other skills in words, not by paths into another skill's
`references/`, following `tests/test_skill_path_pointers.py` and house style.

### D4 — Registration

- **`.codex-plugin/plugin.json:24`:** "sixteen skills", plus a clause naming
  `tcw-work-create` (`tests/test_plugin_manifests.py:93-112`).
- **`README.md:584-630`:** the skill count, the core-skill table, and the
  grouping sentence.
- **`evals/evals.json`:** a new axis B case, B13, with `invokes: tcw-work-create`
  (this satisfies `tests/test_eval_coverage.py:23-29`).
  - **Prompt:** a user partway through the fixture's active item mentions, in
    passing, that sign-in has become slow for accounts with many invoices. The
    user adds one fact the fixture's inbox entry does not contain: it started
    right after the Tuesday invoice import. The user tells the agent not to work
    on the active item in this turn. The entry is at
    `evals/seed_fixture.py:105-108` and is seeded at `:474-477`.
  - **Assertions:**
    - `tool_input_contains` `tcw-work-create`: the skill was invoked or its file
      opened;
    - `tool_input_contains` `inbox`: the inbox was read;
    - `files_changed_exactly` `["docs/work/inbox/slow-login.md"]`: the new fact
      reached the existing entry, and nothing else changed;
    - `new_item_count` 0.
  - **What this tells apart.** An agent that ignores the remark changes no file
    and fails `files_changed_exactly`. One that creates an item fails both that
    and `new_item_count`. One that writes a second inbox entry fails
    `files_changed_exactly`.
  - **Known limit:** `tool_input_contains` is also satisfied by a Bash command
    naming the skill folder (`evals/grade.py:108-124`). `files_changed_exactly`
    is the check that measures behavior.
  - A `CASE_ROUTING` row in `tests/test_eval_grading.py` pins the routing
    assertion: a run that opened only `tcw-work/SKILL.md` fails it.
- **Ledger:** the Feature and capability from Capability changes, listed under
  `new:` in this item's `capabilities.yaml`.
- **Release documents:** `docs/changelogs/upcoming.md` and
  `docs/release-notes/upcoming.md`.

### D5 — No new agent definition

`procedures/delegation.md:55-59` allows a custom agent only when it needs a
different tool set or model. Neither delegated shape needs one:

- **The delegated run writes**, so it needs the default tool set, and the skill
  is its brief.
- **The read-only search** is the one place an agent could narrow tools. But its
  limits would repeat `find-overlap.md`, and `agents/` is Claude-only packaging
  that must stay an accelerator (`docs/lifecycle/harness.md:14`).

### D6 — Strict tracker mode

Under `work.tracker.strict: true`, `tcw work new` is refused and points to
`tcw work tracker import` (`skills/tcw-work/references/commands.md:202`).

- **Interactive:** relay the refusal.
- **Delegated:** return it.
- **Unattended:** write a raw inbox entry instead and report `deferred to inbox`.
  Strict mode refuses `inbox accept`, not writing an entry, so the entry waits
  for a triage that has a ticket.

### Abstraction and harness checks

- **No store operation is added or changed.**
  - Writing or appending an inbox entry goes through the path
    `tcw work inbox path` resolves, which is the supported way to find the inbox
    (`commands.md:338-341`). A non-filesystem store could implement
    "add a raw inbox entry"; the missing verb is noted under Risks.
  - Step 0's worktree check is a detail of the filesystem adapter, which
    `docs/lifecycle/abstraction.md` lists as such. Against a store with no
    branches it does nothing.
- **Harness:** every instruction is plain prose plus `tcw` and `git` commands.
  - Every delegation has an inline fallback, whether the current agent can
    dispatch or not.
  - No `` !`cmd` `` injection, no hooks, no arguments.

## Acceptance criteria

Structural checks (1–8) prove the work is **finished**. Criterion 9 checks
behavior by hand. Criterion 10 names how **worth doing** is judged later.

1. `skills/tcw-work-create/SKILL.md` exists. Its frontmatter parses with
   `yaml.safe_load` and carries `name: tcw-work-create`, `description`,
   `when_to_use`, `allowed-tools`, `metadata.author` and `license`.
   `len(description) + len(when_to_use) <= 1536`. Each of the following strings
   appears in `when_to_use`, checked one `grep -F` per string: `in passing`,
   `work item`, `tcw-extras-report`, `tcw-post-mortem`.
2. Each of these appears in the skill body, one `grep -F` per string:
   - the mode names `Interactive`, `Delegated`, `Unattended`;
   - `git rev-parse --git-common-dir` and `git worktree list --porcelain`;
   - `find-overlap.md`, `## Added`, `## Origin`, `## References`,
     `determine automatically`, `tcw work inbox path`, `tcw work tracker import`;
   - the seven outcome names: `created`, `amended`, `revised`, `already tracked`,
     `already in progress`, `deferred to inbox`, `needs decision`.

   These prove the parts are present, not that they are right; criterion 9
   checks the behavior.
3. `skills/tcw-work-create/references/find-overlap.md` exists. One `grep -F` per
   string finds each of: `tcw work inbox list`, `covers`, `partly covers`,
   `blocks`, `related`, `searched:`, `read-only`.
4. `skills/tcw-work/SKILL.md` contains `tcw-work-create`, and
   `pytest tests/test_skill_lifecycle_parity.py` passes (the body budget and the
   router's reference check).
5. `skills/tcw-commands-plan-work/SKILL.md` and
   `skills/tcw-configure/references/docs-sync.md` each contain `tcw-work-create`.
   `grep -cF 'tcw work new "<deferred item>"' skills/tcw-configure/references/docs-sync.md`
   is 0.
6. `.codex-plugin/plugin.json` contains "sixteen skills" and `tcw-work-create`.
   `README.md` contains `tcw-work-create` and "Sixteen skills".
7. `evals/evals.json` case B13 carries the four D4 assertions.
   `pytest tests/test_eval_coverage.py tests/test_eval_grading.py tests/test_plugin_manifests.py`
   passes.
8. `tcw taxonomy show tcw-work-create-skill` and
   `tcw capabilities show skills/tcw-work-create` resolve, and the capability's
   `Feature` is `tcw-work-create-skill`. `tcw capabilities check` and
   `tcw validate` exit 0. `git diff --stat <base> -- tcw/ agents/` is empty,
   where `<base>` is the commit implementation started from. Bare `pytest` is
   green.
9. **A by-hand run of the skill against this repository's board, from inside
   the implementation worktree**, recorded in `outcome.md`. Each run stops before
   it would write anything, and after every run `git status --porcelain` in both
   checkouts is unchanged.
   - (a) Step 0 selects the primary checkout.
   - (b) An idea restating
     `2026-09-01-fan-the-backlog-audit-out-across-every-connected-work-root`
     governs as `covers` on that item, and the outcome would be
     `already tracked`.
   - (c) An idea restating one entry from `tcw work inbox list`, plus one
     invented new fact, governs as `covers` on that entry, and the outcome would
     be `amended`.
   - (d) An idea for an active item, if the board has one at the time, would be
     `already in progress`. If none is active, the record says so.
   - (e) An idea matching nothing yields "no overlap" with its `searched:` line,
     and would be `created`.
   - (f) The same idea as (b), run delegated with no answer in the brief, would
     return `already tracked` rather than any `needs decision`.
10. **Worth doing, checked later rather than here:**
    - Once `2026-09-15-eval-runs-under-this-checkout-grade-and-behave-wrongly`
      completes, B13 passes in its `with-skill` arm and fails
      `files_changed_exactly` in its `no-skill` arm. If `with-skill` does not
      invoke the skill, the premise is wrong.
    - The next backlog audit after release finds no duplicate pair where both
      items were created after this ships.
    - Both checks belong to
      `2026-09-11-refine-the-plugin-skills-and-lifecycle-prompts-against-the-eval-findings`,
      and `outcome.md` names them as open.

## Risks

- **The premise is untested.** That a separate skill gets invoked mid-task more
  often than a trigger added to `tcw-work`'s description is an assumption. The
  requester asked for it to be tested, and it cannot be until eval runs work
  (criterion 10). If B13's with-skill arm does not invoke the skill, the
  alternative is folding the trigger into `tcw-work`'s `when_to_use`.
- **The new trigger can pull existing eval cases off their route.**
  - B6 and B9 are covered by the "do not use it for" clause.
  - B1 ("Can you build that?") runs headless and expects `plan.md` and `start`.
    D3 lets the chat request answer references and origin, and D1 asks
    everything else in one message. An agent that still stops to ask about
    blockers fails B1.
  - None of this can be confirmed until the harness runs.
- **Too much triggering adds noise to the backlog.** An agent may file every
  passing thought. The trigger is limited to work that "should outlive the
  session", step 1's understandability bar applies, and batching stays allowed.
- **An unattended revision rewrites a spec or plan without review.** The
  requester chose this for sessions told to work without asking. Each revision
  is a separate commit on an item that has not started.
- **Filing from the primary checkout while another session uses it.** A
  concurrent `git commit` there can hit `index.lock`. Narrow path commits keep
  the contents apart; the fallback is to retry the commit.
- **No CLI verb adds or amends an inbox entry**, so the skill writes files under
  the resolved inbox path. A non-filesystem store would need
  `tcw work inbox add`. That follow-up is filed as an inbox entry when this item
  completes.
- **Overlap with other items:**
  - `2026-09-15-rewrite-the-readme-to-a-new-outline` rebuilds the README's
    skills section. Whichever lands second adds the row.
  - `2026-09-01-fan-the-backlog-audit-out-across-every-connected-work-root` is no
    longer touched, now that consolidation is a non-goal.

## Notes

- **Multi review, 2026-09-15.** The adversarial spec reviewer and Codex both
  reviewed; `bllm` was disabled for maintenance. Changes accepted from that
  round:
  - the modes table;
  - step 0 (worktrees);
  - the `already tracked` and `needs decision` outcomes;
  - the governing-match rule;
  - D2 moved inside the skill, and consolidation dropped;
  - B13's assertions;
  - structural criteria split into one grep per string;
  - criteria 9 and 10.

  The requester decided four points: delegated runs are not unattended, items
  land on the primary checkout's board, consolidation is deferred, and batching
  stays allowed.
- **Rejected: a row for status `blocked`.** `blocked` is not a status: `tcw work list --status` accepts backlog, active, review, completed and discarded, and `docs/work/blocked/` is an empty leftover folder. A backlog item with blockers is still `backlog`.
- **The two reviewers disagreed on whether a subagent can dispatch its own
  subagents** under Claude Code. The design does not depend on the answer:
  every delegation has an inline fallback.
- **Naming:** the subagent that mapped touch points called `tcw-work-create` a
  naming violation. I narrowed that finding in D1, because plain `tcw-*` names
  are the core group.
