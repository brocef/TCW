# Spec — Rewrite stage prompts, procedures and skills for the new lifecycle

## Capability changes

This slice changes what the plugin offers and what `tcw work stage prompt` and
`tcw work procedure` print, so it changes records. The planned declaration, in the
shape TCW-69 defines for `<item>/capabilities.yaml` (TCW-69 spec, Design 7):

```yaml
removed:
  - skills/commands-verify-work   # built on the 2.x verify stage; review and qa replace it
  - skills/work-stage             # duplicates `tcw work stage prompt`
  - skills/post-mortem            # the postmortem stage prompt becomes the one source
changed:
  - skills/work
  - skills/capabilities           # the reversal: records change during implement
  - skills/configure
  - skills/setup                  # gains the Jira workflow walkthrough
  - skills/commands-process-inbox
  - skills/commands-plan-work
  - skills/commands-drive-work-to-completion
  - skills/commands-pause-work    # handoff in the stage folder; no commit or push
  - skills/work-create
  - skills/extras-autonomous-work
  - skills/extras-triage-issues
  - work/run-a-lifecycle-stage    # eight built-in prompts, backend passages, new header and footer
  - work/run-a-procedure          # the procedure set changes
  - work/configure-procedures     # names the procedure ids
taxonomy:
  removed:
    - commands-verify-work-skill
    - work-stage-skill
    - post-mortem-skill
```

Each `changed` record above was chosen by reading its `description.md` for
behavior this slice changes: for example
`docs/capabilities/skills/commands-pause-work/description.md` promises the agent
"commits and pushes anyway" when the user does not answer, and
`docs/capabilities/skills/capabilities/description.md` promises "setting each
capability's status as the work completes". Records for the `extras-report`,
`taxonomy` and `documentation-sync` skills describe nothing this slice changes and
stay as they are.

Records for the 2.x work commands (`work/start-a-work-item`,
`work/submit-a-work-item-for-review`, the `tracker` records and the rest of the 46
records under `docs/capabilities/work/`) belong to the slices that remove those
commands (TCW-70, TCW-71, TCW-73). `work/run-a-lifecycle-stage` also describes
`stage gate` and `stage validate`, which TCW-73 removes; because this slice lands
after TCW-73 (Design 13), it rewrites that record whole.

## Problem

Every piece of text TCW gives an agent describes the 2.x lifecycle, and much of
it exists in two places. Five problems follow.

1. **The built-in prompts describe a lifecycle 3.0 deletes.** The packaged
   prompts are one file per 2.x stage id:
   `STAGE_IDS = ("inbox", "request", "spec", "plan", "implement", "verify", "postmortem")`
   (`tcw/store/base.py:1136`), loaded by `load_builtins`
   (`tcw/work/resolve.py:71`). They name verbs 3.0 removes:
   - `tcw work start <slug>` before the first code edit
     (`tcw/work/prompts/implement.md:17`);
   - `submit`, `rework` and `complete` (`tcw/work/prompts/verify.md:19`,
     `:29`, `:30`);
   - `tcw work inbox accept` and `intake.md` (`tcw/work/prompts/inbox.md:13`,
     `:27`).

   They name 2.x artifacts (`outcome.md`, `refined-outcome.md`, `rework.md`,
   `post-mortem.md`) instead of TCW-69's stage folders and rounds, and nothing
   in them mentions rounds, verdicts, `judges`, handoffs, comments or the QA
   plan. The generated footer sends the reader to removed verbs too:
   `STAGE_NEXT_STEPS` (`tcw/store/base.py:2325-2345`) says to run
   `tcw work stage gate`, `tcw work start` and `tcw work complete`.
2. **Every built-in prompt tells the agent to commit.** All seven do: for
   example `request.md:32` ("Commit `initial-request.md` on its own"),
   `spec.md:33`, `plan.md:33`, `implement.md:19` ("committing each"),
   `verify.md:26`, `postmortem.md:34`, and `inbox.md:37-38`, which relies on
   `work.auto-commit-transitions`. Outside the prompts, 41 shipped files under
   `skills/`, `agents/`, `tcw/work/prompts/` and `tcw/work/procedures/`
   (excluding the `documentation-sync` skill and procedure) contain the words
   git, commit, push, pull, worktree, trunk or branch. The heaviest are
   `skills/work/references/transitions.md` (53 lines),
   `skills/work/references/commands.md` (36),
   `skills/commands-pause-work/SKILL.md` (17, including "Ask whether to commit
   and push", `:25`) and `tcw/work/procedures/create-work.md` (13, including
   `git worktree list --porcelain`, `:28`). Nine skills grant `Bash(git *)` in
   their frontmatter, for example `skills/work/SKILL.md:5`.
3. **Stage text exists twice.** Each stage has a prompt and a second document,
   `skills/work/references/lifecycle/stage-<id>.md`, which the `work-stage` skill
   prints beside it (`skills/work-stage/SKILL.md:28`). The two are written to
   different shapes and checked by different tests
   (`tests/test_shipped_prompts.py`, `tests/test_skill_lifecycle_parity.py`).
4. **Each procedure is split across two files.** Five procedures have a second
   file under `skills/work/references/procedures/` holding the rules a project
   cannot replace, and five skills inject the replaceable half with
   `` !`tcw work procedure prompt <id>` `` (`tests/test_shipped_procedures.py:30-41`
   maps every id to its second home). The ticket calls these "duplicates that have
   already diverged"; reading them, they are not copies but a deliberate split
   (`skills/work/references/procedures/decompose.md:3-7`), and
   `test_each_default_is_todays_text` (`tests/test_shipped_procedures.py:72`)
   fails if a paragraph appears in both. The split is still two places to read and
   keep in step, and the fixed halves already describe 2.x behavior: the
   `decompose` half says a child "starts in `backlog`" and `tcw work complete`
   refuses an open parent (`skills/work/references/procedures/decompose.md:11-20`).
5. **The capabilities skill plans records.** It tells the agent to create a
   `Missing` capability at planning, to point it at the work item with a
   `Planning doc` field, and to flip it to `Supported` at completion
   (`skills/capabilities/SKILL.md:37`, `:45`, `:82-86`). TCW-69's records gate
   rejects a `new` capability whose status is `Missing` (TCW-69 spec, Design 7),
   so following the skill would now fail the gate.

The plugin also ships agents and skills whose job disappears. `agents/verifier.md`
assesses the `verify` stage; `skills/commands-verify-work/SKILL.md` drives it;
`agents/post-mortem.md:3` reads "the item's commit history".
`skills/work/references/epic-deltas.md` and `cross-node-deltas.md` describe
`type: epic`, `--initiative`, `delegate` and `escalate`, all removed. The eval
harness in `evals/` seeds a 2.x board and grades 2.x artifacts: case B3 asserts
that "the ledger was flipped Missing → Supported" at closeout (`evals/evals.json`),
the exact practice this slice reverses.

## Goals

1. **Eight built-in prompts**, one per stage whose `prompt` column is yes in
   TCW-69's stage table, each describing TCW-69's layout exactly: stage folders,
   `round-N.md` with `verdict` and `judges`, handoffs, comments,
   `<item>/capabilities.yaml`, `advance` and `path`.
2. **One file per stage, both backends.** Backend-specific passages are marked,
   and `stage prompt` and `procedure` print only the passages for the project's
   backend, for built-in text and for a project's own bindings alike.
3. **The product chain in the text**: the request asks what changes for users;
   the spec declares it in `capabilities.yaml` and posts a QA plan comment;
   implement changes the records with the code; review checks the records; qa
   checks the product against the request and the QA plan.
4. **One source for each text**: no stage document beside a prompt, one file per
   procedure, no artifact templates.
5. **No git in built-in text**, enforced by a test.
6. **Every skill, reference, agent and procedure has a verdict**, recorded in
   `skills/README.md` and carried out.
7. **Every `tcw` command the shipped text names exists** in the 3.0 command
   parser, enforced by a test.
8. **The eval harness measures 3.0**: it seeds a 3.0 project and its cases name
   3.0 stages and artifacts.

## Non-goals

- **The model.** Stages, layout, `judges`, `advance`, gates and the
  `capabilities.yaml` schema are TCW-69's. Where this slice needs the model or a
  sibling's command surface to change, Notes lists it as a cross-slice finding
  rather than diverging.
- **Command names and output.** The command surface and the stdout/stderr
  contract are TCW-73's, including removing `stage gate`, `stage validate` and
  `scaffold`. Git-related strings in the Python code are TCW-73's.
- **User documentation** (README, `docs/guide/`, `docs/lifecycle/abstraction.md`,
  `implementation.md`, `harness.md`): TCW-75.
- **This repository's own bindings, procedure files and opt-in git example**
  (`tcw-config.yaml`, `docs/lifecycle/*.md`, `docs/procedures/create-work.md`,
  `scripts/require_artifact.py`): TCW-76. Nothing found in this spec moves them
  here: they are this project's configuration, which the migration guide reviews.
- **The `documentation-sync` release flow.** `skills/documentation-sync/` and
  `tcw/work/procedures/documentation-sync.md` keep their commit and tag steps.
  Only their 2.x work-axis wording changes (Design 7).
- **Porting the resolver onto the 3.0 model.** `tcw/work/resolve.py` takes 2.x
  types (`WorkItem`, `LifecyclePolicy`, `tcw/work/resolve.py:20-24`). Whichever
  slice wires `stage prompt` and `procedure` onto TCW-69's model (TCW-70 or
  TCW-73; see Notes) does that. This slice changes only the text-processing steps
  inside it (Design 3 and 4).

## Design

### 1. The prompt set

1. The built-in prompts are `tcw/work/prompts/<name>.md` for every stage whose
   `prompt` column is yes, as TCW-69 fixes (TCW-69 spec, Design 3.2): inbox,
   request, spec, plan, implement, review, qa and postmortem. `verify.md` is
   deleted. Completed and discarded have no file.
2. The loader derives that set from the stage table's `prompt` column, not from
   `STAGE_IDS`. A stage with `prompt: yes` and no file, and a file for a stage
   with `prompt: no` or no row, are both load errors naming the file, as
   `_load_texts` does today for a missing file (`tcw/work/resolve.py:77-94`).
3. Every prompt keeps today's shape: **Purpose**, **Inputs**, **Produce**,
   `## Steps`, `## Exit badly`. The judgment worth keeping carries over: ask the
   user at request; ground claims in the code at spec; no placeholders and a
   self-review at plan; the failing test first, falsifying a test that passes on
   its first run, and finding the root cause at implement; "nobody could have
   known" against "nobody checked" at postmortem.
4. **[Decision] Ceiling.** Each prompt, after backend filtering for either
   backend, is at most **60** lines. Today's ceiling is 50
   (`tests/test_shipped_prompts.py:57`); the request template and the backend
   passages need room, and the merged postmortem text (Design 5) needs more than
   50.
5. **Paths come from `path`, never composed.** Every prompt names its files
   through `tcw work path <slug> <stage>` (the document or folder),
   `tcw work path <slug> <stage> --next` (the next round) and the handoff form
   of `path` (TCW-69 spec, Design 4.10). The item folder is
   `tcw work path <slug>`.
6. **Resuming.** Every prompt for a stage that has a folder opens with the same
   rule: read the newest `handoff-*.md` in this stage's folder first, as a
   description of the work at the time it was written, and check the folder for
   anything newer (a later round, a revised document) before trusting it.
   **[Decision]** Handoffs are never deleted (2.x deleted them on resume,
   `skills/work/SKILL.md:45`): TCW never deletes item files, and the newest one
   wins by name. A stage with no folder (inbox; request and qa in Jira mode,
   which TCW-69 makes external) has no handoff.

### 2. What each prompt says

The text is written at implement. These are the requirements each prompt must
meet; acceptance criterion 3 checks the mechanical ones.

- **inbox.** Decide whether each arrival becomes work. No `inbox accept`, no
  `intake.md`.
  - Filesystem passage: `tcw work list --stage inbox`; read each one's request
    through `tcw work path <slug> request`; accept with `tcw work advance <slug>`;
    turn away with `tcw work discard <slug> --reason …`; split one arrival into
    several with `tcw work new` for each extra piece.
  - Jira passage: `tcw work tickets list`, then `tcw work tickets adopt <KEY>`,
    which creates the item and moves it to request (TCW-71).
  - Both: choose tags from `tcw work tags list`; do not ask the filer for more;
    an arrival already tracked is recorded on the existing item, not accepted
    twice.
- **request.** What to build at a product level, written for any reader, light
  on code references unless the work is technical by nature. The template lives
  in this prompt (the request template at `tcw/work/templates.py:20-33` goes,
  Design 4), with these sections:
  - **What and why.**
  - **Product changes**: what users will be able to do differently, and what the
    change adds, changes or removes. "None" is a valid answer and is written as
    such.
  - **Out of scope.**
  - **Constraints.**
  - **References**, each with one line on why it matters.

  It keeps today's steps: ask the user what is unclear, ask for reference
  material and record "asked; none provided" when there is none
  (`tcw/work/prompts/request.md:21-28`). Backend passages:
  - Filesystem: write `request/request.md` through `tcw work path <slug> request`.
  - Jira: the request is the ticket's description, which Jira owns. **[Decision]**
    The agent never rewrites it. It reads it with `tcw work show <slug>`, and when
    a template section is missing or unclear it posts a comment with
    `tcw work comment <slug>` listing what is missing and proposing wording, for
    the requester to adopt. This keeps "Jira owns the request" (TCW-71) true.
- **spec.** What to build technically. Keeps the seven required sections and the
  product-first, grounding, checkable-criteria and repo-wide-sweep steps
  (`tcw/work/prompts/spec.md:13-33`). It writes:
  - `spec/spec.md`, through `tcw work path <slug> spec`;
  - `<item>/capabilities.yaml`, whose path is the item folder plus that name,
    with the schema TCW-69 defines, and no records written;
  - **the QA plan**, posted with `tcw work comment <slug>` (text on stdin). The
    comment is the plan's only home. Its first line is the heading `QA plan`
    **[Decision]**, so later stages can find it. A revised spec posts a new one,
    whose second line says which earlier QA plan it replaces; the newest wins.
    Minimum contents:
    - one scenario per product change in the request;
    - the expected behavior for each;
    - the environment or accounts needed;
    - what is not tested.

    **[Decision]** When the request says "Product changes: none", the spec still
    posts a QA plan, saying so and naming what qa should confirm did not change,
    so qa always has a plan to read.
- **plan.** How to build it, as ordered, checkable steps, each naming the files
  it creates or changes and what proves it, plus the Documentation Sync block and
  a Verification section (`tcw/work/prompts/plan.md:9-12`). Dependencies between
  items are blockers, recorded with `tcw work edit <slug> --blocked-by`.
  **[Decision]** Two conditional steps cover a disabled spec stage, matching
  TCW-69's rule that the first enabled stage among spec, plan and implement
  writes the declaration (TCW-69 spec, Design 4.4):
  - if `<item>/capabilities.yaml` does not exist and the request names product
    changes, write it;
  - if the item has no `QA plan` comment, post one.

  Too-large work is decomposed here with `tcw work new "<title>" --parent <slug>`.
  This absorbs the `decompose` procedure (Design 5).
- **implement.** Builds it and writes `implement/round-N.md` through
  `tcw work path <slug> implement --next`, with no verdict. The round records:
  - what was done, step by step;
  - the test result, from a command run just now;
  - what the plan or spec got wrong;
  - which records changed.

  It changes the taxonomy and capability records **in the same change as the
  code**, so that `capabilities.yaml` is true by the time review starts and the
  records gate passes (TCW-69 spec, Design 7). It writes `capabilities.yaml`
  first if no earlier stage did. A later round reads the latest rejection first.
  **[Decision]** The latest rejection is every review or qa round whose verdict
  is `rejected` and whose `judges` equals the number of the newest implement
  round. In Jira mode it is also the newest comment recorded when the item left
  qa for implement, because TCW-71 requires a rejection to carry a comment.
  "Return to plan" is `tcw work advance <slug> --to plan` (a backward move, no
  force).
- **review.** Code verification against the spec and plan, including that the
  records changed alongside the code and say what the code does (the records
  gate only checks they exist). The reviewer reads the change through what the
  implement round says changed, and the code itself; how a project shows "the
  change" (a diff, a pull request) is the project's own binding. It writes
  `review/round-N.md` through `tcw work path <slug> review --next`, starting
  with the front matter TCW-69 defines:

  ```yaml
  ---
  verdict: accepted        # or rejected
  judges: 3                # the newest implement round
  ---
  ```

  **[Decision]** `judges` is the highest `N` among the `round-N.md` files in
  `tcw work path <slug> implement`, or 0 when there are none. The round lists
  each acceptance criterion as met, not met, or not checkable, with evidence. An
  agent may write a review verdict itself.
- **qa.** Product behavior against the request and the newest `QA plan` comment.
  With no QA plan, test against the request's Product changes and say so in the
  round.
  - Filesystem passage: writes `qa/round-N.md` with the same front matter.
    **[Decision]** The verdict is a person's (QA, product or the requester): the
    agent runs the scenarios, presents the evidence, and stops for the decision,
    as today's verify does (`tcw/work/prompts/verify.md:23-24`). With nobody to
    decide, the item stays at qa. A project that works unattended replaces this
    through its own `unattended-work` procedure.
  - Jira passage: QA happens on the ticket. A person accepts with
    `tcw work advance <slug> --to completed --reason …` or by moving the ticket,
    and a rejection is `tcw work advance <slug> --to implement --reason …`, whose
    reason becomes the required comment (TCW-69 spec, Design 6.4). The agent may
    run the scenarios and post its findings as a comment. **[Decision]** It never
    records the verdict for a person.
- **postmortem.** Writes `postmortem/postmortem.md` through
  `tcw work path <slug> postmortem`. It reads the item backwards:
  - qa rounds, then review rounds, then implement rounds;
  - plan, spec and the request;
  - the item's comments.

  `## Notes` across them is the primary trail. It is a side stage: it never
  moves the item, and it applies to any item that is not discarded. The
  investigation text from the `post-mortem` procedure
  (`tcw/work/procedures/post-mortem.md:1-41`) moves into this prompt, minus its
  `git log` step (`:13-14`).

  **[Decision] The optional request-level comment** is not posted by the
  built-in text. The prompt defines its form: what the request missed, written
  in the request's language, posted with `tcw work comment`. It is posted only
  when the project's own `prompt` bindings for postmortem ask for it. That is how
  "off by default" is expressed without a new configuration key, since TCW-69's
  config gives a side stage only `enabled` and `prompt` (TCW-69 spec, Design 8,
  check 3).

**Comments are read with `tcw work show <slug>`.** **[Decision]** Implement, qa
and postmortem read comments, and in Jira mode request reads the ticket
description, through `tcw work show <slug>`, in both backends. TCW-69's backend
interface writes comments but has no operation that reads them (TCW-69 spec,
Design 5), and TCW-73's `show` prints "the item's record" without saying it
includes comments or the request text. Both are listed as cross-slice findings
in Notes.

### 3. Backend passages

1. **Syntax.** A passage opens with a line holding exactly
   `<!-- backend: <name> -->` and closes with a line holding exactly
   `<!-- /backend -->`. **[Decision]** The ticket names only the opening markers.
   An explicit closing marker is what lets a passage sit in the middle of a list
   or a section. `<name>` is a value `work.backend` accepts (`filesystem` or
   `jira`, TCW-69 spec, Design 8).
2. **Filtering.** For the project's backend, the marker lines are removed and
   the passage kept; for any other backend, the marker lines and the passage are
   removed. Text outside any passage is kept for every backend.
3. **Errors.**
   - An unknown name, a passage inside another passage, an unterminated passage
     and a stray closing marker are all errors.
   - In built-in text, a test finds them before release (criterion 4).
   - In a project's text, `stage prompt` and `procedure` exit 1 and name the
     binding.
4. **Where it applies.** Filtering applies to each resolved binding's text before
   composition: built-in, `file`, `blob` and `generate` output, for stage prompts
   and procedures alike. That is how "project and personal prompt files get the
   same filtering" holds, whatever layer a binding comes from (TCW-72).
5. **Order.** Backend filtering runs first, then `{{tcw:documentation}}`
   substitution (`tcw/work/resolve.py:231-305`), so a documentation span may sit
   inside a passage.

### 4. Generated text around a prompt

1. **The header and footer.** `bookend` (`tcw/work/resolve.py:399-439`) and
   `STAGE_NEXT_STEPS` (`tcw/store/base.py:2325-2345`) are replaced.
   **[Decision]** This slice owns that generated text, because it is part of what
   an agent reads with every prompt and must agree with the prompts. The text is
   derived from the stage table's columns and contains no stage name:
   - **header** (every stage): this text ran no checks; gates run when an item
     moves, and `tcw work advance <slug> --dry-run` reports whether the next move
     would pass;
   - **footer**, for a side stage: nothing follows, because this stage never
     moves the item;
   - **footer**, for a stage whose artifact is `none` (inbox): none, because how
     an arrival becomes an item differs by backend and the prompt's own passages
     say it;
   - **footer**, for any other stage: when this stage's output is written, run
     `tcw work advance <slug>`; for a stage whose rounds carry a verdict, the
     verdict decides where the item goes.
2. **`<slug>`.** With a work item reference, `stage prompt` replaces every
   literal `<slug>` in the composed text, header and footer with the item's full
   slug. Today only the footer is substituted (`tcw/work/resolve.py:435`).
   Without a reference, `<slug>` stays literal.
3. **`{{tcw:body}}` goes.** It resolved "the item's body artifact" from
   `BODY_ORDER = ("initial-request", "intake")` (`tcw/store/base.py:3109`). In
   3.0 the request's place is fixed per backend and stated in the prompts'
   backend passages. `substitute_body` and `resolved_body`
   (`tcw/work/resolve.py:307-384`) are deleted.
4. **`{{tcw:documentation}}` stays**, in plan and implement, unchanged.
5. **Artifact templates go.** `tcw/work/templates.py` is deleted, as are
   `resolve_artifact` (`tcw/work/resolve.py:514-541`) and
   `Builtins.artifact_templates`. TCW-73 removes the `scaffold` verb, which was
   their only reader, and TCW-69 makes `work.lifecycle.artifacts` a config error.
   A per-tag template becomes a conditional `file` binding in a stage's `prompt`
   list (TCW-69 spec, Design 8).

### 5. Procedures

1. **[Decision] The procedure set** becomes:

   | Id | Verdict | Reason |
   | --- | --- | --- |
   | `documentation-sync` | keep | Outside the no-git rule; wording updated (Design 7) |
   | `create-work` | rewrite | Filing an idea; loses worktree checkout, inbox verbs, commits and strict tracker mode (`tcw/work/procedures/create-work.md:22-30`, `:122-143`) |
   | `audit-backlog` | rewrite | Reviewing unfinished items; reads 3.0 stages and folders, loses `state.yaml` and `git status` (`tcw/work/procedures/audit-backlog.md:8-11`, `:123`) |
   | `search` | rewrite | `--status` becomes `--stage`; reads stage folders |
   | `triage-issues` | rewrite | Creates items with `tcw work new`; loses its commit step (`tcw/work/procedures/triage-issues.md:136`) |
   | `unattended-work` | rewrite | The checkpoint map names `submit`, `tcw work complete`, the verifier, and a local merge (`tcw/work/procedures/unattended-work.md:33-38`); it maps review and qa instead, with no git |
   | `pause-work` | **new** | See item 3 |
   | `post-mortem` | delete | Merged into the postmortem stage prompt (Design 2) |
   | `consolidate-plans` | delete | Its safety rules are git checks (`skills/work/references/procedures/consolidate-plans.md:22-35`); without git there is no safe deletion rule, and moving outside plans into items is ordinary `tcw work new` |
   | `decompose` | delete | Folded into the plan prompt; 3.0 has no parent-completion rule for it to explain |
   | `delegation` | delete | Its one rule (Design 7, the work skill) moves into the work skill. **[Decision]** The word "delegation" is kept for TCW-69's meaning, `tcw work new --project` |

2. **[Decision] One file per procedure.** Each procedure's text is
   `tcw/work/procedures/<id>.md` and nothing else. The rules a project must not
   be able to switch off move into the skill that invokes the procedure, stated
   once there:
   - "ask before changing the board, grouped by kind" moves from
     `skills/work/references/procedures/audit-backlog.md:9-22` to the work skill;
   - "search is read-only" moves from
     `skills/work/references/procedures/search.md:9-10` to the work skill;
   - "search the board before filing" stays in
     `skills/work-create/references/find-overlap.md`.

   The `skills/work/references/procedures/` folder is deleted.
3. **[Decision] `pause-work` is a new procedure id.** Pausing is where 2.x
   committed and pushed (`skills/commands-pause-work/SKILL.md:25-33`, `:65-71`).
   With that text gone, a project that wants a commit on pause needs somewhere to
   say so; a procedure is the existing place for replaceable conduct, and today's
   `skills/README.md:95` already records that "no procedure id backs this skill".
   The built-in text says how to reach a resting point and what a handoff holds.
   The skill keeps the fixed parts: the handoff's location and name, and stopping
   afterwards.
4. The id set lives wherever TCW-69's configuration parser validates
   `work.procedures` ids. Today it is `PROCEDURE_IDS` (`tcw/store/base.py:1143-1145`).

### 6. No git in shipped text

1. **The rule.** No built-in prompt, procedure, skill or agent tells an agent to
   run a git command, commit, pull, push, branch, use a worktree or tag, or
   assumes the project's work is in git. The `documentation-sync` skill and
   procedure are exempt (the ticket's exception). Python strings are TCW-73's.
2. **The check.** A test scans every `.md` file under `skills/`, `agents/`,
   `tcw/work/prompts/` and `tcw/work/procedures/`, except the exempt ones, for
   these whole words, case-insensitively:
   - `git`;
   - `commit`, `commits`, `committed`, `committing`;
   - `push…` and `pull…`;
   - `worktree`, `worktrees`;
   - `trunk`;
   - `branch…`.
3. **[Decision] A short allowlist** of exact phrases, each with its reason in the
   test, covers configuration facts that are not instructions:
   - a store's `repository: {url: …}` example and "another repository" in the
     configure skill's store and project references, since TCW-69 keeps
     `work.repository` and TCW-70 keeps `provision`;
   - the `taxonomy rm` refusal on files git does not track
     (`skills/taxonomy/SKILL.md:122`), which describes TCW reading git, which is
     allowed.

   Anything else needs a new entry with its reason, so a reviewer sees every
   exception.
4. **`allowed-tools: Bash(git *)`** is removed from every skill's frontmatter.
   Nine skills carry it today (the list is in Notes); `extras-autonomous-work`
   carries `Bash(git merge *)` (`skills/extras-autonomous-work/SKILL.md:4`).

### 7. Disposition of every skill, reference, agent and procedure

Counts are lines in today's file, matched by two regular expressions given in
Notes:
- **git** counts lines naming git, commit, push, pull, worktree, trunk or branch;
- **2.x** counts lines naming a removed verb, artifact, status or concept (start,
  submit, rework, complete, drop, tracker, inbox accept, stage gate, Definition
  of Done, graveyard, scaffold, tombstone, claim, `intake.md`, `outcome.md`,
  `refined-outcome.md`, `rework.md`, `state.yaml`, verify, backlog, `type: epic`,
  `Planning doc`, `work-stage`, node).

The default verdict is delete; a kept file says why.

| File | Lines | git | 2.x | Verdict | Becomes |
| --- | --- | --- | --- | --- | --- |
| `skills/README.md` | 142 | 3 | 15 | rewrite | The verdict table for what remains; the `commands-pause-work` row names `pause-work` |
| `skills/work/SKILL.md` | 70 | 5 | 17 | rewrite | The work axis in 3.0: `stage prompt`, `advance`, `path`, rounds and `judges`, handoffs, comments, `capabilities.yaml`, epics as parents, `new --project`, the backend differences, and the fixed rules moved from procedures |
| `skills/work/references/commands.md` | 528 | 36 | 199 | rewrite | The 3.0 command reference, from TCW-73's surface; the tracker, claim and strict-mode sections go |
| `skills/work/references/transitions.md` | 248 | 53 | 68 | delete | `advance` is described in the work skill |
| `skills/work/references/hooks.md` | 76 | 2 | 4 | delete | Bindings are documented once, in the configure skill's `work.md` |
| `skills/work/references/tags.md` | 55 | 0 | 1 | keep | The tag registry is unchanged; "node" becomes "project" |
| `skills/work/references/epic-deltas.md` | 76 | 0 | 22 | delete | No epic type; a parent is an epic (TCW-69); one paragraph in the work skill |
| `skills/work/references/cross-node-deltas.md` | 84 | 1 | 31 | delete | `delegate` and `escalate` go; `new --project` is one paragraph in the work skill |
| `skills/work/references/lifecycle/stage-inbox.md` | 37 | 0 | 4 | delete | The prompt is the one source |
| `skills/work/references/lifecycle/stage-request.md` | 26 | 1 | 3 | delete | Same |
| `skills/work/references/lifecycle/stage-spec.md` | 30 | 0 | 3 | delete | Same |
| `skills/work/references/lifecycle/stage-plan.md` | 33 | 0 | 4 | delete | Same |
| `skills/work/references/lifecycle/stage-implement.md` | 31 | 1 | 5 | delete | Same |
| `skills/work/references/lifecycle/stage-verify.md` | 31 | 0 | 7 | delete | Same; verify is gone |
| `skills/work/references/lifecycle/stage-postmortem.md` | 24 | 0 | 4 | delete | Same |
| `skills/work/references/procedures/audit-backlog.md` | 22 | 0 | 2 | delete | Rule moves to the work skill (Design 5.2) |
| `skills/work/references/procedures/consolidate-plans.md` | 35 | 5 | 0 | delete | Procedure deleted |
| `skills/work/references/procedures/decompose.md` | 35 | 0 | 10 | delete | Procedure deleted |
| `skills/work/references/procedures/delegation.md` | 51 | 0 | 8 | delete | Procedure deleted; its rule moves to the work skill |
| `skills/work/references/procedures/search.md` | 10 | 0 | 0 | delete | Rule moves to the work skill |
| `skills/work-stage/SKILL.md` | 63 | 0 | 8 | delete | Duplicates `tcw work stage prompt`; its stage contract (`:28`) is deleted, and `stage validate` (`:18`) goes in TCW-73 |
| `skills/commands-process-inbox/SKILL.md` | 35 | 3 | 14 | rewrite | Runs the inbox prompt over every arrival (filesystem: inbox-stage items; Jira: `tickets list`), then request for each accepted item |
| `skills/commands-plan-work/SKILL.md` | 39 | 4 | 6 | rewrite | Runs request, spec and plan through `stage prompt`, advancing between them, and stops at plan |
| `skills/commands-drive-work-to-completion/SKILL.md` | 38 | 5 | 8 | rewrite | Runs the current stage onwards through review and qa; stops at qa for the person's verdict; no "bounded stage documents" (a 2.x plan-stage concept, `:22-24`) |
| `skills/commands-verify-work/SKILL.md` | 33 | 1 | 9 | delete | Verify is gone; review and qa are stage prompts the work skill and `commands-drive-work-to-completion` reach |
| `skills/commands-pause-work/SKILL.md` | 91 | 17 | 2 | rewrite | Resting point, handoff through the handoff form of `path` in the current stage's folder, report, stop; conduct from the `pause-work` procedure; no commit or push |
| `skills/work-create/SKILL.md` | 41 | 1 | 1 | rewrite | Same outcomes; an unclear idea goes to an inbox-stage item (filesystem) or is returned (Jira, where the inbox is tickets) |
| `skills/work-create/references/find-overlap.md` | 69 | 0 | 4 | rewrite | Searches unfinished items, including inbox-stage ones, by stage instead of status |
| `skills/capabilities/SKILL.md` | 145 | 1 | 14 | rewrite | The reversal (Design 8) |
| `skills/taxonomy/SKILL.md` | 122 | 2 | 5 | rewrite | Taxonomy terms change during implement in the same change as the code; "node" becomes "project"; `:33` reworded without git |
| `skills/configure/SKILL.md` | 42 | 3 | 6 | rewrite | Routing for 3.0 keys: `work.stages`, `work.hooks`, `work.procedures`, `work.backend`, `work.jira`; no DoD, `artifacts`, `trunk-branch` or commit rows |
| `skills/configure/references/work.md` | 186 | 11 | 14 | rewrite | `work.stages.<stage>.{enabled, prompt, pre, post}`, `work.hooks`, `work.procedures`, backend passages; DoD, `artifacts` and commit sections (`:39`, `:119`, `:144`) go |
| `skills/configure/references/tracker.md` | 303 | 1 | 96 | delete | Replaced by `references/jira.md`: `work.backend: jira`, `work.jira.*`, per-stage `status` |
| `skills/configure/references/projects.md` | 169 | 3 | 6 | rewrite | "project" throughout; `connected-projects` keys as TCW-73 renames them |
| `skills/configure/references/stores.md` | 103 | 7 | 0 | rewrite | Store locations; "pushes each transition back" (`:70`) goes |
| `skills/configure/references/docs-sync.md` | 60 | 0 | 3 | keep | Documentation entries are unchanged; wording only |
| `skills/setup/SKILL.md` | 44 | 0 | 4 | rewrite | Routes the Jira walkthrough; drops DoD and tracker rows |
| `skills/setup/references/install.md` | 74 | 0 | 1 | keep | Installing the CLI is unchanged |
| `skills/setup/references/project.md` | 77 | 4 | 1 | rewrite | `tcw init` without git requirements (`:26`, `:36`, `:44-45`) |
| `skills/setup/references/taxonomy.md` | 56 | 0 | 0 | keep | Unchanged |
| `skills/setup/references/capabilities.md` | 32 | 0 | 0 | keep | Seeding a ledger records what exists, so `Missing` there is an acknowledged gap, which 3.0 keeps |
| `skills/setup/references/jira.md` | — | — | — | **new** | Design 9 |
| `skills/extras-autonomous-work/SKILL.md` | 97 | 4 | 3 | rewrite | Advisors stand in for people at spec, plan and the qa verdict; the audit trail goes in the newest implement round, not `outcome.md` (`:75`); no `git merge` |
| `skills/extras-triage-issues/SKILL.md` | 71 | 1 | 7 | rewrite | GitHub triage into `tcw work new` items; `Bash(git *)` goes |
| `skills/extras-report/SKILL.md` | 123 | 1 | 5 | keep | Reporting upstream is unchanged; the removed-verb examples and "tracker" wording are updated |
| `skills/post-mortem/SKILL.md` | 55 | 0 | 7 | delete | The postmortem prompt is the one source; the work skill routes "which stage could have caught this" to it |
| `skills/documentation-sync/SKILL.md` | 77 | 1 | 7 | keep | Exempt from the no-git rule; 2.x work words (`outcome.md`, "node") updated, and `upcoming/` files named by folder name (TCW-75) |
| `skills/documentation-sync/references/cut-version.md` | 189 | 27 | 1 | keep | Release flow, exempt |
| `skills/documentation-sync/references/release-notes-and-changelogs.md` | 128 | 6 | 0 | keep | Exempt |
| `agents/verifier.md` | 52 | 0 | 8 | rewrite, renamed `agents/reviewer.md` | Read-only assessment for the review stage: criterion by criterion, records against code, suite result; recommends a verdict and the dispatching session writes the round. It is kept because a reviewer that did not write the code, and cannot edit it, is worth a separate context |
| `agents/backlog-auditor.md` | 59 | 2 | 12 | rewrite | Per-item fan-out for `audit-backlog`, reading `tcw work procedure audit-backlog`; no `git log`, `state.yaml` or removed verbs |
| `agents/post-mortem.md` | 47 | 3 | 6 | delete | Needs no tool set or independence the coordinating session lacks, and its output is a document that session writes anyway; it also restates the prompt |
| `tcw/work/prompts/*.md` (7 files) | 307 | 14 | 48 | rewrite | Design 1-2; `verify.md` deleted, `review.md` and `qa.md` new |
| `tcw/work/procedures/*.md` (10 files) | 832 | 20 | 60 | per Design 5 | 6 kept or rewritten, 1 new, 4 deleted |

**Plugin manifests.** `.codex-plugin/plugin.json`'s `longDescription` lists the
skills by name and says "seventeen skills". It is rewritten for the fourteen that
remain.

**`dynamic_skill`.** Each remaining skill's marker follows its row in the rewritten
`skills/README.md`, as `tests/test_dynamic_skill_marker.py` already enforces.

**What the work skill carries.** Beyond the routing table row above, the work
skill states these, each once:
- how to find your place: the item's stage from `tcw work show`, then the newest
  handoff, then `tcw work stage prompt <stage> <slug>`;
- `advance` is never handed to a subagent, and request and qa are not dispatched
  because they need a person (from
  `skills/work/references/procedures/delegation.md:9-24`);
- the backlog-audit approval rule and the search read-only rule (Design 5.2).

### 8. The capabilities skill reversal

The rewritten `skills/capabilities/SKILL.md` states, explicitly:

- **No `Missing` records at planning.** The spec declares new, changed and
  removed paths in `<item>/capabilities.yaml` and writes no records.
- **No planning-document pointers.** No `Planning doc` field is written.
- **No flipping at completion.** Implement adds, edits or removes the records in
  the same change as the code. The records gate on the stage after implement
  checks they are there, and review checks they are right.
- **`Missing` means a known gap the team has acknowledged**, not a plan.
- **Drift** is `tcw capabilities drift`, which reads completed items'
  declarations (TCW-69 spec, Design 7).
- **Product-layer wording** across projects is asked for with
  `tcw work new "<title>" --project <parent>` instead of `tcw work escalate`
  (`skills/capabilities/SKILL.md:119`).

The ledger-flip section (`:82-90`, "The ledger flip (at `tcw work complete`)") and the quick-reference rows for planning
pointers and flipping (`:131-134`) are deleted.

### 9. The setup skill's Jira walkthrough

`skills/setup/references/jira.md` walks a user from a Jira project to a working
`backend: jira` configuration. It is an agent conversation, not an automatic
change:

1. Choose the stages to enable, and one distinct Jira status for each (TCW-71).
2. Write `work.backend: jira`, `work.jira.*` and each stage's `status`.
3. Run `tcw validate --remote`. It reports missing statuses, transitions
   `advance` needs, and missing custom fields (TCW-71).
4. For each problem, explain what TCW needs and why, and work with the user to
   change the Jira workflow in Jira's own settings. TCW changes nothing in Jira's
   configuration.
5. Re-run until clean.

The configure skill's `references/jira.md` documents the keys; the setup
reference links to it rather than repeating them.

### 10. Commands named in shipped text exist

**[Decision]** A test extracts every `tcw …` command named in backticks or code
blocks in the shipped text: prompts, procedures, skills and agents, excluding the
`documentation-sync` skill's own release scripts. It checks each command's
words, up to the first argument or flag, against the 3.0 `argparse` tree. It also
checks every `--flag` named directly after such a command against that
subcommand. This replaces lists of removed verbs: anything removed, misspelled or
renamed fails it.

### 11. The eval harness

`evals/` answers whether lifecycle instructions reach an agent and what the
skills add. **[Decision]** It is rewritten, not retired, because that question
stays open in 3.0.

- **Seeding.** `evals/seed_fixture.py` seeds a 3.0 project:
  - items created with `tcw work new` and moved with `tcw work advance`;
  - artifacts written to the paths `tcw work path` prints;
  - the customized variant's nonces bound under `work.stages.<stage>.prompt`
    instead of `work.lifecycle.stages` (`evals/seed_fixture.py:298`);
  - the fixture still a git repository, because the harness grades by diffing
    it. That is test tooling, not shipped text.
- **Axis A** (do bound instructions reach the agent):
  - cases A1-A3 and A5 (spec, plan, implement, postmortem) keep their nonces;
  - A4 (verify) becomes a review case asserting a `review/round-N.md` with valid
    front matter;
  - a new qa case asserts a filesystem-mode qa round is not written without a
    verdict from a person, since there is none in the run;
  - **[Decision]** with `work-stage` deleted there is no injection, so the
    injected / fallback provenance (`evals/grade.py:19-66`) and cases A6-A8,
    which read it, are removed. The question becomes whether the agent ran
    `tcw work stage prompt` and its artifact carries the nonce, under both
    harnesses.
- **Axis B** (what a skill adds):
  - B2 (an inbox file) becomes an inbox-stage item accepted with `advance`;
  - B3 (closeout flips Missing → Supported) is rewritten so the records change
    during implement and the item advances into review with the records gate
    passing, without `--force`;
  - B6's quoted command becomes `tcw work advance`;
  - B13's overlap target becomes an inbox-stage item.
- **Coverage.** `evals/coverage.py`'s exclusion and partial tables are updated
  for the deleted skills.

The harness depends on the 3.0 CLI, so it is rewritten after TCW-70 and TCW-73
land (Design 13).

### 12. Tests this slice rewrites or removes

| Test file | Fate |
| --- | --- |
| `tests/test_shipped_prompts.py` | Rewritten against the stage table (criteria 1-3) |
| `tests/test_shipped_procedures.py` | Rewritten: one file per id, no source map |
| `tests/test_skill_lifecycle_parity.py` | Deleted: `LIFECYCLE_STEPS` and the stage documents it checks are gone; criteria 3, 6 and 9 replace it |
| `tests/test_body_prompt.py` | Deleted with `{{tcw:body}}` |
| `tests/test_prompt_fallback.py` and its fixture | Re-captured from the 3.0 output, in its own commit before any later text change, as the file's own docstring requires |
| `tests/test_falsification_rule.py`, `tests/test_documentation_prompt.py` | Kept, pointed at the new implement and plan text |
| `tests/test_unattended_work_skill.py`, `tests/test_dynamic_skill_marker.py`, `tests/test_skill_path_pointers.py` | Kept, updated |
| `tests/test_skill_flow.py` | Rewritten as the 3.0 product-first flow the skills prescribe: new, through implement with records added, into review with the records gate passing |
| `tests/test_eval_*.py` | Updated with the harness |
| `tests/test_resolve.py`, `tests/test_resolve_procedure.py`, `tests/test_procedure_config.py`, `tests/test_procedure_verb.py` | Updated for the id set, backend filtering and the removed body token |

### 13. Sequencing

**[Decision]** This slice lands after TCW-70 (the filesystem backend wired into the
CLI) and TCW-73 (the command surface), because its text names their commands and
criterion 9 checks them against the real parser. It lands before TCW-76, whose
migration of this repository reviews project text against these prompts. It can
land in parallel with TCW-75.

## Abstraction litmus test

| Operation or text | Verdict |
| --- | --- |
| Backend passages | **Model-level text processing.** Keyed on the configured backend's name, not on how a backend stores anything. A third backend gets its own passages; text outside passages applies to every backend. |
| Prompts reading paths through `path` | **Shared layout** (TCW-69): the technical record is files in both modes. |
| Reading comments and the request through `tcw work show` | **Backend interface.** Jira can list a ticket's comments and description; the filesystem backend reads its comment files. This needs the interface change listed in Notes, not a filesystem shortcut such as globbing `comments/`. |
| The QA plan as a comment | **Backend interface** (`comment`), the same in both modes. |
| Header and footer | **Derived from stage table columns.** No stage name and no backend assumption. |
| `judges` from the implement folder | **Shared layout.** Implement is never an external stage, so its folder exists in both modes. |

No text instructs an agent to glob a store folder or to compose a store path.

## Harness compatibility

- **Every entry point is a skill**, and every requirement is carried by a `tcw`
  command both harnesses run: `stage prompt`, `procedure`, `advance`, `path`,
  `comment`, `show`.
- **Deleting `work-stage` removes this plugin's main use of Claude-only context
  injection** (`skills/work-stage/SKILL.md:18`, `:28`, `:32`). The skills that
  keep an injected `procedure` command (`work-create`, `extras-autonomous-work`,
  `commands-pause-work`) keep the manual fallback section they have today, and
  criterion 7 checks it.
- **Agents** (`reviewer`, `backlog-auditor`) are Claude packaging and
  accelerators only. The review prompt and the `audit-backlog` procedure stand
  alone, and say so.
- **`arguments:` frontmatter** is Claude-only. A skill that keeps it also says, in
  its text, where the values come from when nothing fills them.

## Acceptance criteria

All are pytest tests unless marked otherwise. "Filtered for a backend" means the
composed output of `tcw work stage prompt <stage> <slug>` on a project with
`work.backend` set to that backend and no bindings of its own.

1. **The prompt set.**
   - The loaded built-in prompts are exactly the stages whose `prompt` column is
     yes.
   - `tcw/work/prompts/verify.md` does not exist.
   - Deleting any one prompt file, or adding `tcw/work/prompts/completed.md`,
     makes loading fail with a message naming the file.
   - The built wheel contains exactly those prompt files.
2. **Ceiling.** Every prompt, filtered for each backend, is at most 60 lines.
3. **Content, mechanically checked.** Filtered for each backend:
   - no prompt contains `intake.md`, `initial-request.md`, `outcome.md`,
     `refined-outcome.md`, `rework.md`, `post-mortem.md` or `state.yaml`;
   - every prompt for a stage with a folder contains `handoff`;
   - spec contains `QA plan`, `tcw work comment` and `capabilities.yaml`;
   - plan contains `capabilities.yaml` and `QA plan`;
   - implement contains `tcw work path <slug> implement --next` (with `<slug>`
     substituted when a reference is given), and names all four things an
     implement round records (Design 2): what was done, the test result, what
     the plan or spec got wrong, and which records changed;
   - review and qa (filesystem) contain the front-matter keys `verdict:` and
     `judges:`;
   - review contains `tcw work path <slug> review --next`;
   - request contains the five template section names, including
     `Product changes`;
   - the jira-filtered request contains `tcw work comment` and no
     `tcw work path <slug> request`;
   - the jira-filtered inbox contains `tcw work tickets adopt` and no
     `--stage inbox`;
   - the filesystem-filtered inbox contains `tcw work advance` and no `tickets`;
   - qa contains no instruction to `advance` on a person's behalf. This is
     checked by reading: the jira-filtered qa names `--reason` only in text
     addressed to the person deciding.
4. **Backend passages.** Through the filter function:
   - a `jira` passage is removed for `filesystem` and kept, without its markers,
     for `jira`;
   - an unknown backend name, a nested passage, an unterminated passage and a
     stray close are each an error;
   - every built-in prompt and procedure passes the filter for both backends
     without error;
   - a project `file` binding containing a `jira` passage, resolved on a
     filesystem project, omits it;
   - one with an unterminated passage makes `tcw work stage prompt` exit 1 and
     name the binding.
5. **Header, footer and `<slug>`.**
   - `stage prompt postmortem <slug>` ends with the side-stage sentence.
   - `stage prompt inbox` has no footer.
   - Every other stage's footer contains `tcw work advance <slug>` with the slug
     substituted.
   - With a reference, no literal `<slug>` remains anywhere in the output.
   - A test scans the header and footer source for any stage name from the table
     and finds none.
   - `{{tcw:body}}` appears in no shipped file, and `tcw/work/templates.py` does
     not exist.
6. **Procedures.**
   - The loaded procedures are exactly `documentation-sync`, `create-work`,
     `audit-backlog`, `search`, `triage-issues`, `unattended-work` and
     `pause-work`, each one file.
   - `skills/work/references/procedures/` does not exist.
   - `work.procedures.delegation` is a config error naming the known ids.
7. **Skills, references and agents match the disposition table.**
   - The set of files under `skills/` and `agents/` is exactly the table's kept,
     rewritten and new files.
   - `skills/README.md` has a row for each, and `test_dynamic_skill_marker.py`
     passes.
   - Every skill that contains a `` !` `` injection has a `## Document command
     summary` naming the same command.
   - `.codex-plugin/plugin.json` names no deleted skill, and the number of skills
     it states equals the number of `skills/*/SKILL.md` files.
8. **No git** (Design 6).
   - The scan finds no match outside the exempt files and the allowlist.
   - No skill's `allowed-tools` contains `git`.
   - Mutation check, run once at implement and recorded in the round: adding the
     word "commit" to `tcw/work/prompts/plan.md` makes the test fail and name the
     file and line.
9. **Commands exist** (Design 10).
   - The extractor finds every `tcw` command in the shipped text, and each
     resolves in the 3.0 parser.
   - Mutation check, recorded the same way: adding `tcw work start <slug>` to the
     work skill makes it fail and name the file.
10. **The capabilities skill reversal.** `skills/capabilities/SKILL.md` contains
    none of `--status Missing`, `Planning doc` or `flip`, and contains
    `same change as the code`.
11. **Records.** `tcw validate` passes, and the records named in Capability
    changes are in the declared state: the three removed skills' capability
    records and taxonomy Features are gone, and each changed record's
    description no longer names a removed verb.
12. **Evals.**
    - `python evals/seed_fixture.py --customized <dir>` and `--bare` succeed
      against the 3.0 CLI.
    - `python evals/coverage.py` reports no uncovered skill.
    - `python -m evals.run_evals --axis a --dry-run` lists the rewritten cases.
    - `tests/test_eval_*.py` pass.
    - No case asserts a status flip from `Missing`.
13. **The 3.0 product flow** (`tests/test_skill_flow.py`). `new`, then
    `advance` through spec, plan and implement, with `capabilities.yaml`
    declaring a new path and `tcw capabilities add` made during implement, then
    a bare `advance` into review exits 0, with no `--force`. The same flow with
    the record still `Missing` is refused (exit 3).
14. **The full suite passes.**

### Coverage

| Design rule | Criteria |
| --- | --- |
| 1 Prompt set | 1, 2 |
| 2 Prompt contents | 3, 13 |
| 3 Backend passages | 4 |
| 4 Generated text | 5 |
| 5 Procedures | 6 |
| 6 No git | 8 |
| 7 Disposition | 7, 11 |
| 8 Capabilities reversal | 10, 13 |
| 9 Setup Jira walkthrough | 7 (file exists), 9 (`tcw validate --remote` resolves) |
| 10 Commands exist | 9 |
| 11 Evals | 12 |
| 12 Tests | 14 |

## Risks

- **Prompts depend on commands siblings have not specified.** Reading comments
  and the Jira request through `tcw work show`, the handoff form of `path`, and
  `tickets list` showing enough to triage are not in TCW-69's or TCW-73's specs
  yet (Notes). Mitigation: criterion 9 fails if a named command or flag does not
  exist, so a gap is found at implement, not by a user.
- **The qa verdict needs a person.** A filesystem project with nobody to decide
  leaves items at qa. That is the intended direction, the same as 2.x verify.
  Unattended projects replace it through `unattended-work`.
- **Deleting `work-stage` changes how Claude users reach a stage.** One injected
  read becomes an explicit `tcw work stage prompt` call. The evals (Design 11)
  measure whether agents still make that call.
- **`judges` computed by an agent can be wrong.** A wrong number makes the
  verdict `stale`, which blocks rather than lets work through (TCW-69 spec,
  Risks). The prompt states the rule in one sentence and names the folder to
  read.
- **Breadth.** This slice touches about 70 shipped files and a dozen test files.
  Mitigation: the plan orders the work by mechanism (loader and filter, then
  prompts, then procedures, then skills, then evals), each step with its own
  green suite.
- **A project that relied on 2.x commit instructions loses them silently.** This
  repository, for one, never committed by hand on several of these paths, because
  the built-in text did it. TCW-75's opt-in git example and TCW-76's migration
  of this repository restore it as project text; the migration guide says so.

## Notes

- **Decisions made in this spec, for the owner to confirm.** Each is marked
  **[Decision]** above:
  - the prompt ceiling is 60 lines after filtering;
  - handoffs are never deleted; the newest wins and is read as of its time;
    stages with no folder have none;
  - the Jira request prompt never rewrites the ticket description and proposes
    changes as a comment;
  - the QA plan comment's first line is `QA plan`; a revised spec posts a new
    one; it is posted even when there are no product changes;
  - plan writes `capabilities.yaml` and posts a QA plan when no earlier stage
    did;
  - implement's "latest rejection" is every rejected review or qa round judging
    the newest implement round, plus the Jira qa rejection comment;
  - `judges` is the highest implement round number in the folder, or 0;
  - an agent may write a review verdict, but never a qa verdict for a person,
    in either backend;
  - the postmortem request-level comment is turned on by a project prompt
    binding, not a config key;
  - comments and the Jira request are read through `tcw work show <slug>`;
  - backend passages use an explicit closing marker, apply to every binding
    kind, and run before documentation substitution;
  - this slice owns the generated header and footer, which are derived from
    table columns; `<slug>` is substituted through the whole output;
  - `{{tcw:body}}`, `tcw/work/templates.py` and `resolve_artifact` are deleted;
  - procedures: keep or rewrite six, add `pause-work`, delete `post-mortem`,
    `consolidate-plans`, `decompose` and `delegation`; one file each, with the
    fixed rules moved into the invoking skill; "delegation" means
    `new --project` only;
  - the no-git test has a short, reasoned allowlist for configuration facts;
  - a test checks every named `tcw` command against the parser;
  - skill verdicts as in Design 7: `work-stage`, `commands-verify-work` and
    `post-mortem` deleted; `verifier` renamed `reviewer`; the `post-mortem`
    agent deleted; `backlog-auditor` kept;
  - this slice owns every file under `skills/`, including the configure
    references;
  - the eval harness is rewritten; injection provenance and cases A6-A8 go;
  - sequencing: after TCW-70 and TCW-73, before TCW-76.
- **Cross-slice findings** (nothing has been posted to those tickets):
  - **TCW-69 / TCW-73: reading comments.** The backend interface has `comment`
    (write) but no read (TCW-69 spec, Design 5). Implement (Jira qa rejection),
    qa (the QA plan) and postmortem must read comments in both backends. This
    needs either `read` to return comments or a ninth operation, and TCW-73's
    `show` to print them.
  - **TCW-73 / TCW-71: the Jira request text.** `show` must print the ticket
    description in Jira mode, or the request and spec prompts have no way to read
    the request.
  - **TCW-73 / TCW-71: triaging tickets.** `tickets list` must show enough of each
    ticket (at least its description, or offer a `--json` that includes it) for
    the inbox prompt to decide without adopting first.
  - **TCW-73: `path --handoff`.** TCW-69 defines a handoff form of `path`
    (Design 4.10), but TCW-73's surface lists only
    `path <slug> [<stage> [--next]]`.
  - **TCW-73: who ports `stage prompt` and `procedure`.** The resolver takes 2.x
    types (`tcw/work/resolve.py:20-24`). The port onto TCW-69's model is assigned
    to no slice. This spec assumes TCW-73 does it, since it owns those commands.
  - **TCW-73: generated header and footer.** TCW-74's ticket says "strings in the
    Python code belong to TCW-73"; this spec takes the prompt header and footer
    (Design 4.1) because they are prompt text. TCW-73 should not also rewrite them.
  - **TCW-70: tests that break when the 2.x CLI goes.** `tests/test_skill_flow.py`,
    `tests/test_prompt_fallback.py` and `tests/test_eval_*.py` drive the 2.x CLI.
    TCW-70 removes it before this slice can rewrite them. TCW-70 should delete or
    skip them, with a reason naming TCW-74, so CI does not stay red in between.
  - **TCW-75: the configure skill's references.** TCW-75's ticket makes
    `skills/configure/references/` "the canonical home of each key's
    documentation" and rewrites `tracker.md` and `projects.md`. TCW-74's ticket
    rewrites the configure skill. This spec gives every file under `skills/` to
    TCW-74, because the no-git and command checks cover the whole plugin, and
    leaves TCW-75 to link to them. The shared/overridable table is TCW-72's
    content placed there.
  - **TCW-74's own ticket** says spec writes `spec/capabilities.yaml`. TCW-69's
    confirmed decision puts it at `<item>/capabilities.yaml`, which this spec
    follows. The ticket has no "Update from TCW-69's spec" section and needs one.
  - **TCW-69's Capability changes** calls `work/archive-a-resolved-item-before-it-is-deleted`
    "the ledger's one `work/` capability today". The ledger has 46 records under
    `docs/capabilities/work/`, all `Supported`, many describing commands 3.0
    removes (`start-a-work-item`, `submit-a-work-item-for-review`,
    `drop-a-work-item`, the tracker records). TCW-70, TCW-71 and TCW-73 need to
    own them explicitly.
  - **TCW-76 against the design record.** The record maps `refined-outcome.md`
    and `rework.md` to `review/round-N.md`; TCW-76's ticket maps them to
    `qa/round-N.md`, which is newer and consistent with "old verify was the
    user's acceptance". TCW-76's artifact table also still says
    `spec/capabilities.yaml`, corrected only in its update section.
- **Questions only the owner can answer:**
  1. Should a filesystem-mode qa verdict really require a person, or may an agent
     record it when the project has not said otherwise? This spec says a person.
  2. Is deleting `work-stage` acceptable, given it is the one skill that hands a
     Claude user the stage text without a tool call?
  3. Keep `extras-triage-issues` and `extras-autonomous-work` in the plugin, or
     move them out as this repository's own skills? This spec keeps both.
  4. Should `consolidate-plans` survive without its git-based safety rules?
     This spec deletes it.
  5. Confirm the boundary with TCW-75 over `skills/configure/references/`.
- **Inventory method.** Counts in Design 7 and Problem come from two regular
  expressions over each file, run on 2026-10-01 against this branch:
  - git: `\b(git|commit\w*|push\w*|pull\w*|worktrees?|trunk|branch\w*)\b`,
    case-insensitive;
  - 2.x: an alternation of the removed verbs, artifacts and concepts listed in
    Design 7.

  The 2.x count over-matches words like "complete" in ordinary prose and is a
  measure of how much rewriting a file needs, not a defect count. The 41-file
  git figure matches the ticket's "about 41 files".
- **Skills granting `Bash(git *)` today:** `work`, `work-create`, `configure`,
  `commands-drive-work-to-completion`, `commands-pause-work`,
  `commands-plan-work`, `commands-process-inbox`, `commands-verify-work`,
  `extras-triage-issues`; and `extras-autonomous-work` grants `Bash(git merge *)`.
- **Driving this item.** Implementation edits `tcw/work/resolve.py` and the
  procedure id set, so from implement onwards this repository's board is driven
  by editing files, as `CLAUDE.md` requires.
