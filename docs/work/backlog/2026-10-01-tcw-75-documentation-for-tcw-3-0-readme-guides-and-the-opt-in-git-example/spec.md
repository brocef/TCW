# Spec — Documentation for TCW 3.0: README, guides and the opt-in git example

## Capability changes

```yaml
# <item>/capabilities.yaml
changed: [skills/configure]
```

- **`skills/configure` (cap-97192e), changed.** Under Design 1.2 this item owns
  the whole `configure` skill. The record says the skill points to a document
  for, among other things, "the Definition of Done, whether transitions commit
  and publish themselves, the trunk branch, deleting resolved items"
  (`docs/capabilities/skills/configure/description.md:1`). 3.0 removes all of
  those settings (TCW-69 Design 8.4). It also adds settings the record does not
  list: stages and hooks, the Jira backend, and personal configuration. The
  description is rewritten to list the areas in Design 6. Its status stays
  `Supported`. Its `Planning doc` field is handled however TCW-76 decides for
  every record (see Notes, owner question 2).
- **No other capability record changes.** Documentation does not change what a
  user can do with TCW. Each behavior is recorded by the item that ships it:
  TCW-69 to TCW-73 and TCW-77, as the ticket says, plus TCW-74 for the skills
  it deletes or rewrites (see Notes, cross-slice finding 3).
- **No taxonomy changes.** The `configure-skill` taxonomy entry names the terms
  `node` and `work-item/definition-of-done`
  (`docs/taxonomy/configure-skill/meta.yaml`). Those terms are renamed or
  removed by TCW-73 and TCW-70. `tcw taxonomy rm` refuses to remove an entry
  that another entry still names (`README.md:307`), so the item that removes a
  term has to update the entries that name it. This item does not.

## Problem

Every user-facing document describes TCW 2.8. Once the 3.0 code lands, a reader
who follows them runs commands that no longer exist and sets keys that 3.0
treats as errors. Seven problems follow.

1. **The README describes the 2.x model throughout.**
   - It says an item's status is the folder it sits in and that every move
     commits itself (`README.md:226-230`, `README.md:390-393`).
   - It describes a Definition of Done checklist and `start --worktree`
     (`README.md:406-411`).
   - It presents five transitions and their checks (`README.md:482-492`).
   - It presents Jira as an add-on to the folder model ("None of the stages
     change: Jira attaches to how an item is created and to the transitions",
     `README.md:510-513`), with tracker commands, claiming and strict mode
     (`README.md:508-642`).
   - Its web app section says the app needs Node.js and can start, complete and
     drop items (`README.md:779`, `README.md:789-793`, and again at
     `README.md:110`).
   - It has no section explaining why taxonomy and capabilities live in the
     repository, which the owner asked for in TCW-67.
   - Its documentation index omits the existing 2.4 to 2.5 migration guide
     (`README.md:820`).
2. **The guides describe the 2.x model.**
   - `docs/guide/work.md` opens with "Status is the folder an item lives in, and
     a transition is a `git mv`" (`docs/guide/work.md:3-5`). It has sections on
     resolved-work retention, transitions and commits, the Definition of Done,
     claims and worktrees (`docs/guide/work.md:105`, `:184`, `:221`, `:701`,
     `:776`).
   - `docs/guide/jira.md` (1,107 lines) is built around the `tcw work tracker`
     commands, claiming, linking and strict mode (`docs/guide/jira.md:8-15`,
     `:203`, `:418`, `:660`, `:1013`).
   - `docs/guide/taxonomy-and-capabilities.md` says `set` is "the mechanism the
     work→capability lifecycle uses to flip `Missing → Supported` at
     completion" (`docs/guide/taxonomy-and-capabilities.md:99-100`), and it
     describes `Planning doc` as "the forward pointer to a work item" (`:78`).
   - `docs/guide/linking-and-validation.md` says a new capability "is added, as
     `Missing`, when the item is planned" (`:45-51`). It lists `state.yaml`,
     `graveyard.yaml` and `tracker.yaml` as record files (`:67-68`), and names
     `dod.yaml` (`:80`).
   - `docs/guide/configuration.md` documents `work.lifecycle` and
     `transitions` (`:17-26`) and `when: {type: …}` (`:68-73`). It lists the
     hook variables `TCW_STATUS`, `TCW_TRANSITION` and `TCW_NODE_ROOT`
     (`:185-193`).
   - `docs/guide/multi-repo.md` is written in terms of "node" and
     `tcw work nodes` (`:94`, `:125`, `:175`, `:186`).
3. **The abstraction rules rest on a premise 3.0 removes.**
   `docs/lifecycle/abstraction.md` says the filesystem is the default store and
   an external tracker would replace it (`:12`). It names "node relation" in
   the model's vocabulary (`:21`) and lists "atomic `mv` as transition" as a
   benefit to use freely (`:23`). In 3.0 the model reads item folders in both
   backends, a folder never moves, and "node" is replaced by "project". TCW-69's
   spec hands this rewrite to this item (TCW-69 `spec.md:687-691`).
   `docs/lifecycle/implementation.md` says to keep remote adapters "possible but
   unbuilt" (`:9`), but 3.0 builds a Jira backend. It also tells the agent to
   run `tcw work start` (`:52-54`).
4. **Configuration is documented in two places and describes removed keys.**
   - `skills/configure/references/work.md` documents `work.lifecycle`
     (`:3-14`), `artifacts` templates (`:39`), `dod.yaml` (`:119`) and the
     commit and retention keys (`:144-186`). 3.0 removes all of them (TCW-69
     Design 8.4).
   - The rules for which binding kinds each position allows live in a second
     place, the `work` skill's `hooks.md`, which the configure reference
     defers to (`skills/configure/references/work.md:26-28`).
   - No document says which keys a person may override in their personal
     configuration, a distinction TCW-72 introduces.
5. **The output contract is documented only in pieces.** "What the commands
   print" exists only for `tcw work`, inside the work guide
   (`docs/guide/work.md:414`). TCW-73 sets one contract for stdout, stderr and
   exit codes across every command, and no document describes it.
6. **Projects lose their git automation with no documented replacement.** 2.x
   commits each move by itself and can pull and push a separate work store
   (`skills/configure/references/work.md:144-175`). 3.0 never changes git state
   (TCW-69 Design 10). A project that relied on that behavior needs a pattern
   to rebuild it with its own prompts and hooks, and none is written down.
7. **Tests that guard the documentation will fail while the code changes.**
   `tests/test_documented_cli_surface.py` checks that every `tcw` command and
   flag named in any live Markdown file exists
   (`tests/test_documented_cli_surface.py:1-21`, scope at `:36-46`).
   `tests/test_configuration_text_home.py` asserts sentences in `tracker.md`
   (`:22-55`). `tests/test_repo_lifecycle.py` asserts two phrases in
   `abstraction.md` (`:76-84`). When TCW-70, TCW-71 and TCW-73 remove commands
   and keys, the documents still name them, and those tests fail before this
   item runs.

## Goals

1. **The README describes 3.0 as it is.** It has the new section "Why
   taxonomy and capabilities live in the repository" right after the Overview.
   It has a rewritten Work overview, the two backends side by side, and a web
   app section that matches TCW-77. Its documentation index is correct and
   links the 3.0 migration guide.
2. **Every live guide and lifecycle document has a recorded outcome**
   (rewritten, edited, kept, deleted or created; Design 3), and the outcome is
   carried out.
3. **Each configuration key is documented once**, in
   `skills/configure/references/`. Each key says whether it is shared or can be
   overridden, and one table lists them all.
4. **The abstraction rules hold in 3.0.** The litmus test keeps its question
   (the one-line test "could a non-filesystem store implement this operation,
   even if less elegantly?", which module docstrings cite). It is restated for a
   model with two backends and files in git in both modes.
5. **One documented, tested git example** keeps git in step with each stage
   change using only prompt text and a `post` hook.
6. **One user-facing description of the output contract**: stdout, stderr,
   slug input and exit codes.
7. **Release notes and changelog entries** for 3.0.0's documentation, including
   the introduction that opens the 3.0.0 release notes.
8. **The documentation stays checked.** Tests catch a document that names a
   removed command, key, file or term, a broken link, and an exit-code table or
   override table that disagrees with the code.

## Non-goals

- **Sibling items' documents.**
  - `docs/guide/web-viewer.md`: TCW-77.
  - Built-in prompts (`tcw/work/prompts/`), procedures, agents, and every skill
    except `configure`: TCW-74. This includes the request template's text,
    which lives in the request prompt.
  - The migration guide, TCW's own `tcw-config.yaml`, `docs/procedures/`,
    `docs/lifecycle/templates/`, and every part of `AGENTS.md` except its
    worktree section: TCW-76.
  - Python help and message strings: TCW-73.
- **Capability and taxonomy records** other than `skills/configure` (see
  Capability changes).
- **Historical documents** stay as written: `docs/plan/`, `docs/superpowers/`,
  `docs/changelogs/v*.md`, `docs/release-notes/v*.md`, the 2.x and older
  migration guides, and finished work items. They are the archives
  `tests/test_documented_cli_surface.py:36-46` already excludes.
- **`docs/releasing.md`** stays as it is. Its `git push` is the release flow,
  which the "TCW never changes git state" rule excludes (design record, Git).
- **`tests/cli/scenarios/`** are contributor test scripts, not user
  documentation. Several of them describe 2.x behavior
  (`09-worktree-isolation-and-merge-back.md`, `11-scaffold-and-artifact-templates.md`).
  No ticket owns them; see Notes, cross-slice finding 8.
- **Generating documentation from the records.** The README mentions it as a
  possibility only.

## Design

### 1. Boundaries and ordering

1. **Ordering.** **[Decision]** This item is implemented after TCW-69 to TCW-74
   and TCW-77 have landed on the epic branch, and before TCW-76. The documents
   describe commands, keys and skills that those items fix. TCW-76 then links
   to and adopts what this item writes (the git example's script path, the
   README index row for its guide).
2. **Who edits which file.** **[Decision]**

   | Files | Owner |
   | --- | --- |
   | `README.md` (all of it) | this item |
   | `docs/guide/*.md` except `web-viewer.md` | this item |
   | `docs/guide/web-viewer.md` | TCW-77 |
   | `docs/lifecycle/{abstraction,implementation,harness}.md` | this item |
   | `docs/work-inbox-template.md` | this item (deleted) |
   | `skills/configure/` (its `SKILL.md` and `references/`) | this item |
   | every other skill, `agents/`, `tcw/work/prompts/`, procedures | TCW-74 |
   | `AGENTS.md`, worktree section only (`AGENTS.md:80-101`) | this item |
   | `AGENTS.md`, everything else; `tcw-config.yaml`; `docs/procedures/`; `docs/lifecycle/templates/` | TCW-76 |
   | `docs/migration-guide-2.8-to-3.0.0.md` | TCW-76 |
   | `docs/{changelogs,release-notes}/upcoming/README.md` | this item |
   | this item's own `upcoming/` entry files | this item |

   The `configure` skill moves here from TCW-74's list ("the work,
   capabilities, taxonomy, configure and setup skills are rewritten"). The
   skill is a router table plus the reference documents it routes to. If two
   items each wrote one half, the table and the files could disagree, and
   `tests/test_configuration_text_home.py:58-62` already checks the two
   against each other. This needs TCW-74's ticket to drop `configure` (see
   Notes).
3. **The boundary with TCW-74.** Built-in prompts and skills tell an agent what
   to do at a stage. This item's documents tell a reader how TCW works and how to
   configure it. Where a skill needs a configuration fact, it links to the
   configure reference and does not restate it. Where a guide needs stage
   instructions, it names `tcw work stage prompt <stage>` and does not copy
   them.
4. **The boundary with TCW-76.** These documents describe 3.0 only. Anything
   phrased as a difference from 2.x ("no longer", "replaces", "since 3.0")
   belongs in the migration guide or the release notes. The README and the
   documentation index link to the migration guide; nothing else refers to 2.x.
5. **Keeping the suite passing in the meantime.** **[Decision]** Each code item
   that removes a command, flag or key keeps `tests/test_documented_cli_surface.py`
   and `tests/test_configuration_text_home.py` passing by the smallest edit
   that does so: it deletes the line naming the removed thing, or the sentence
   around it. This item does the full rewrite. This needs agreement from
   TCW-70, TCW-71 and TCW-73 (see Notes). The other choices were worse:
   marking the tests as expected failures hides real problems for the length of
   the epic, and writing all the documentation first describes code that does
   not exist yet.

### 2. Writing rules for every document this item writes

1. Plain language, as `CLAUDE.md` requires. A technical term is defined in the
   sentence where it first appears in each document.
2. **No 2.x vocabulary.** The terms in the table under Acceptance criterion 2
   appear in no document this item owns, except as that criterion allows.
3. **The two backends side by side.** Wherever behavior differs by backend, both
   are described at the same level of detail, with the filesystem backend
   first. "Filesystem" is the name used throughout, not "vanilla".
4. **"Project", never "node".** Slugs are written `project/folder`.
5. **Git is the project's choice.** A document mentions git only to say that TCW
   does not run it, or to show the opt-in example (Design 8).
6. **Configuration keys are documented in the configure references only.** A
   guide shows a short example and links to the reference for the full rules.

### 3. Inventory and outcome of each document

| Document | Outcome | What changes |
| --- | --- | --- |
| `README.md` | rewrite in part | Design 4 |
| `docs/guide/work.md` | rewrite | Design 5.1 |
| `docs/guide/jira.md` | rewrite | Design 5.2 |
| `docs/guide/configuration.md` | rewrite | Design 5.3, and the git example (Design 8) |
| `docs/guide/multi-repo.md` | rewrite | Design 5.4 |
| `docs/guide/taxonomy-and-capabilities.md` | edit | Design 5.5 |
| `docs/guide/linking-and-validation.md` | edit | Design 5.6 |
| `docs/guide/cli.md` | **new** | Design 9 |
| `docs/guide/examples/commit-item-after-move.sh` | **new** | Design 8 |
| `docs/guide/web-viewer.md` | not touched | TCW-77 |
| `docs/lifecycle/abstraction.md` | rewrite | Design 7.1 |
| `docs/lifecycle/implementation.md` | edit | Design 7.2 |
| `docs/lifecycle/harness.md` | edit | Design 7.3 |
| `docs/work-inbox-template.md` | **delete** | Design 5.7 |
| `skills/configure/SKILL.md` | rewrite | Design 6 |
| `skills/configure/references/work.md` | rewrite | Design 6 |
| `skills/configure/references/tracker.md` | **replaced by** `jira.md` | Design 6 |
| `skills/configure/references/projects.md` | rewrite | Design 6 |
| `skills/configure/references/stores.md` | edit | Design 6 |
| `skills/configure/references/docs-sync.md` | edit | Design 6 |
| `skills/configure/references/personal.md` | **new** | Design 6 |
| `AGENTS.md` worktree section (`:80-101`) | rewrite | Design 7.4 |
| `docs/{changelogs,release-notes}/upcoming/README.md` | edit | Design 10 |
| `docs/releasing.md` | keep | release flow; see Non-goals |

### 4. The README

The `##` sections, in order:

1. **Title and summary** (`README.md:1-12`): kept. The summary says "keep all
   three in step with the code" and stays true.
2. **Contents**: regenerated to match the headings below.
3. **Problem Statement** (`README.md:45-58`): kept.
4. **Installation** (`README.md:60-216`): kept, except that the CLI
   requirements line drops Node.js for `tcw serve` (`README.md:110`),
   following TCW-77.
5. **Overview** (`README.md:217-268`): edited.
   - The paragraph on how items are stored (`:226-230`) says that an item is a
     folder that never moves, that its stage is a property (a recorded value,
     not a location), and that its slug is `project/folder`.
   - The command table follows TCW-73's top-level surface
     (`init`, `provision`, `validate [--remote]`, `projects list`,
     `config show`, `serve`, and the three axes).
   - The "CLI enforces the rules; the plugin supplies judgment" paragraph
     (`:255-259`) stays, with "legal status changes" reworded to "which stage
     moves are allowed".
   - The "Many repositories" paragraph (`:261-268`) uses TCW-73's names for
     connected projects.
6. **Why taxonomy and capabilities live in the repository** (**new**, the
   `##` section right after Overview). It makes exactly these four points, in
   plain prose, in this order:
   1. The product's description (its vocabulary, features and capabilities)
      changes in the same commit as the code that changes it, so a reviewer sees
      both together. The implement stage is where it changes.
   2. Any commit shows the product as it was at that moment, readable by anyone,
      with no tool beyond a file viewer.
   3. Documentation could be generated from the records, for example a knowledge
      base that updates with every change and lets a reader pick any point in
      time. This is stated as a possibility, not a feature.
   4. Tickets describe changes and are short-lived; the records describe the
      product and last. The records are never stored in Jira, whichever backend
      a project uses.
7. **Taxonomy** and **Capabilities** (`README.md:270-381`): edited.
   - The CLI tables follow TCW-73: no `taxonomy init`, `capabilities init`,
     `taxonomy check` or `capabilities check` (they fold into `tcw init <axis>`
     and `tcw validate`).
   - The capabilities overview sentence "completing a work item is how a
     capability moves from `Missing` to `Supported`" (`:330-332`) becomes:
     the implement stage changes the record in the same change as the code, and
     `Missing` means a gap the team has acknowledged.
   - The `drift` row (`:371`) describes 3.0 drift (Design 5.5).
   - The capabilities skill row (`:354`) follows TCW-74's rewritten skill
     description.
8. **Work** (`README.md:383-718`): rewritten.
   - **Overview.** A work item is a folder that never moves. It holds one
     folder per stage that produces something. It has one set of properties
     (title, stage, priority, effort, complexity, tags, assignee, parent,
     blocked-by). An item with children is an epic. TCW never runs git.
   - **Two backends, one model.** One sub-section for each backend, at the same
     heading level, filesystem first:
     - **Filesystem**: everything is in the repository, in `item.yaml`, the
       request file, comment files and stage folders.
     - **Jira**: Jira owns everything a non-engineer reads or changes (the
       request, status, assignee, estimates, tags, links), and the repository
       owns the technical record.

     A short table names who owns each fact in each backend. Both link to their
     guides.
   - **Relationship to Capabilities and Taxonomy.** The chain: the request
     states product changes in prose; the item's `capabilities.yaml` declares
     them formally; implement changes the records; the records gate checks them
     on the move out of implement; qa checks the product's behavior.
   - **Stages.** A diagram and the stage table: name, purpose, what it writes,
     whether a project can turn it off. The data comes from TCW-69 Design 3.
     Postmortem is shown off to the side, since an item never moves into it.
   - **Moving an item.** `advance`, `--to`, `--force --reason`, `--dry-run`,
     `discard`, gates and `post` hooks, in a short form that links to the work
     guide.
   - **Usage.** Skills and CLI tables taken from TCW-73's surface and TCW-74's
     disposition table, plus one example session for each backend.
9. **Skills and Agents** (`README.md:720-766`): the tables follow TCW-74's
   keep, rewrite or delete table.
10. **TCW Local Web App** (`README.md:768-805`): rewritten to match TCW-77.
    It runs as one Python process with no Node.js. It reads, edits and creates
    documents. It runs no lifecycle actions and shows the stage without
    letting you change it. In Jira mode, what Jira owns is read-only, with an
    "Open in Jira" link. It serves one project. It keeps the same local-only
    protections.
11. **Documentation** (`README.md:807-823`): the index.
    - One row for each guide in Design 3.
    - A new row for `docs/guide/cli.md`.
    - A row for the configure references: "every configuration key, and which
      ones a person may override".
    - No row for the deleted inbox template.
    - The migration-guide row lists every existing guide, including the
      missing 2.4 to 2.5 one (`docs/migration-guide-2.4.X-to-2.5.0.md`) and
      `docs/migration-guide-2.8-to-3.0.0.md`, which TCW-76 writes.
12. **Development** (`README.md:825-908`): the worktree paragraph
    (`:845-848`) is replaced to match Design 7.4. "How work is tracked here"
    (`:867-879`) names the lifecycle files by stage without naming the 2.x
    `implement` binding mechanism. The Releasing paragraph (`:889-898`) says
    entry files are named after the item's folder name.
13. **Further Reading** (`README.md:910-916`): kept.

### 5. Guides

1. **`docs/guide/work.md`, the main lifecycle guide.** Rewritten in this order:
   1. What a work item is: a folder that never moves and is never deleted by
      TCW; its slug; its properties and their scales; `item.yaml` in
      filesystem mode, and the ticket in Jira mode.
   2. The stage table, with every column explained in words (TCW-69 Design
      3): which stages can be turned off, side stages, terminal stages.
   3. The item folder: stage folders, `<stage>/<stage>.md`,
      `<stage>/round-N.md`, verdicts and `judges`, what `stale` means and how it
      arises, handoffs, comments, `capabilities.yaml`, and `tcw work path`.
   4. Moving an item:
      - a bare `advance` and how its target is chosen;
      - `--to`, and what counts as a skip;
      - `--force` with `--reason`, and the trace comment it leaves;
      - `--dry-run`, which answers only for TCW's own checks, so in Jira mode it
        can say yes to a move the Jira workflow does not offer (TCW-69 Design
        6.6);
      - `discard`; reopening a finished item;
      - the built-in gates (the records gate on the move out of implement, the
        completion gate);
      - `post` hooks and exit 6.
   5. Inbox items (filesystem mode); tickets without an item (Jira mode, with a
      link to the Jira guide).
   6. Creating and editing: `new`, `edit`, `list`, `show`, tags, `blocked-by`
      and `blocks`, `parent` and epics, `rename`, `comment`.
   7. References and what `tcw validate` warns about: a missing item, a
      reference to a project not on this machine, a stage ahead of its
      documents.
   8. Stage instructions and procedures: `stage prompt`, `lifecycle`,
      `procedure`, `docs`.
   9. "TCW does not run git": one paragraph that links to the example in the
      configuration guide.
   10. A short command table that links to `docs/guide/cli.md` and `--help`
       for the full options, rather than copying each command's flags.
2. **`docs/guide/jira.md`, the Jira-first guide.** Rewritten from scratch, in
   this order:
   1. **Who owns what**: Jira owns the request, status, assignee, estimates,
      labels, parent and blocking links; the repository owns specs, plans,
      rounds, handoffs, taxonomy and capabilities. Nothing is copied between
      them.
   2. **For people outside engineering**: writing a ticket in plain language;
      the request template's sections, including "Product changes" ("none" is
      a valid answer); following progress (the ticket's status is the stage);
      where the QA plan appears (a comment posted at spec); how QA accepts or
      rejects on the ticket (a rejection needs a comment saying why); the
      optional postmortem comment.
   3. **Setting up**: a minimal `work.jira` and `work.stages.<stage>.status`
      example that links to the configure reference; the TCW Project and TCW
      Item fields; credentials named by environment variable.
   4. **Stages and statuses**: one status per enabled stage; a move uses the
      one transition Jira offers to the target status, and is refused when
      there is none or several; a ticket in a status with no stage; a ticket
      moved by hand in Jira counts as a forced move with no reason recorded.
   5. **Checking the workflow**: `tcw validate --remote` and what it reports;
      the `setup` skill walks through fixing the workflow with the user; TCW
      changes nothing in Jira's workflow itself.
   6. **Adopting tickets**: the default inbox query, `inbox-query`,
      `tcw work tickets list`, `tcw work tickets adopt`.
   7. **QA on the ticket**: `advance --to completed --reason …` and
      `advance --to implement --reason …`; why a bare `advance` from qa is
      refused.
   8. **Delegating** with `tcw work new --project`: what stdout prints (a slug,
      or a ticket key when the item could not be created).
   9. **What needs the network**, and what `tcw validate` without `--remote`
      checks offline.
   10. **Limits**: Jira Cloud only; two people adopting the same ticket at the
       same moment; the answers TCW-71's spec gives to team-managed projects
       and to transition screens with required fields.

   The request template's section names are those of TCW-74's request
   prompt. The guide lists them with one line each and says that
   `tcw work stage prompt request` prints the full template.
3. **`docs/guide/configuration.md`.** Rewritten:
   - what `tcw-config.yaml` holds, and that it is trusted like any other file
     in the repository (kept from `:3-6`);
   - the configuration layers (team file, user-wide file, per-project personal
     file), in one paragraph that links to `personal.md`;
   - stage bindings (`prompt`, `pre`, `post`), binding kinds, `when:` and
     `inherit: true`, each shown by example and linked to `work.md` for the
     full rules;
   - **how hooks run**, as a narrative linked to the reference:
     - `pre` hooks run only for the target stage;
     - a failing `pre` refuses the move unless it is forced;
     - **`pre` hooks may run again for the same move** (a Jira workflow can
       refuse the move after they ran), so they must be safe to repeat. TCW-69
       hands this sentence to this item (TCW-69 `spec.md:467-469`);
     - `post` hooks run after the move, and a failure keeps the move and exits
       6;
     - the environment variables (`TCW_SLUG`, `TCW_STAGE`, `TCW_FROM_STAGE`,
       `TCW_ITEM_PATH`, `TCW_PROJECT_ROOT`, and `TCW_FORCED` and `TCW_REASON`
       on a forced move);
     - the timeout and the output cap;
   - documentation entries (kept from `:198-248`; its `<slug>` example
     placeholders become `<folder>`, per Design 10);
   - **the git example** (Design 8).
4. **`docs/guide/multi-repo.md`.** Rewritten around "project":
   - project IDs, and the fact that paths only say where a project is;
   - connecting projects, using TCW-73's renamed keys;
   - `upstream` projects;
   - where a project is on this machine (`TCW_PROJECT_<ID>`, or personal
     configuration, depending on how TCW-72 answers its open question);
   - slugs across projects;
   - delegating with `tcw work new --project`: the three conditions (path
     resolved, work store present, no uncommitted changes in it), what happens
     in each backend, and that files written in another repository are left
     uncommitted;
   - `tcw projects list`;
   - stores in another repository, and `tcw provision`; keeping them up to date
     is the project's job, with a link to the git example;
   - inheriting taxonomy and capabilities with `extends`.

   The sections on 2.x-only machinery go: epic roll-ups, `delegate` and
   `escalate`, and the store lock.
5. **`docs/guide/taxonomy-and-capabilities.md`.** Edited:
   - The sentence at `:99-100` is replaced. Records change during implement, in
     the same change as the code; `Missing` means an acknowledged gap, never a
     plan.
   - A new section, **"From a request to the records"**, describes the chain
     one stage at a time, as in the README (Design 4.8). It shows the
     `<item>/capabilities.yaml` schema from TCW-69 Design 7: `new`, `changed`,
     `removed` and `taxonomy.{new,changed,removed}`. It does **not** use
     `spec/capabilities.yaml`; see Notes, cross-slice finding 1.
   - **Drift** is described by the 3.0 rule (TCW-69 Design 7): the newest
     declaration from a completed item wins; two items created the same day
     that disagree are reported as ambiguous; and drift also reports inherited
     capabilities nobody has reviewed.
   - `check` (`:7`, `:89`) is replaced by `tcw validate`.
   - `Planning doc` (`:78`, `:94`) is described according to TCW-76's decision
     (owner question 2). Until that decision, the guide says that work items
     point at capabilities through `capabilities.yaml`, and does not describe
     `Planning doc` as a pointer.
   - The child-ledger example (`:111-121`) keeps the path-prefix rule and
     drops "completion checks" and `set … --status Supported`.
6. **`docs/guide/linking-and-validation.md`.** Edited:
   - `tcw://` links: the project part reads "a project this one is connected
     to" for work and "a project listed by `extends`" for taxonomy and
     capabilities, using TCW-73's names (`:15-16`).
   - `tcw validate` and `tcw validate --remote`: what each checks, and that
     validation without `--remote` never needs the network.
   - The record files held to the mapping rule become `item.yaml` and
     `meta.yaml` (`:67-68`), and the `dod.yaml` sentence (`:80-83`) goes.
   - The work-item check (`:45-51`) describes the mid-work records check: an
     unreadable or malformed `capabilities.yaml`, an unknown key, a path that
     cannot be checked, and a removal of an inherited capability are reported;
     a change not yet made is not (TCW-69 Design 7).
   - New warnings: a reference to a missing item, an unresolved project, a
     stage ahead of its documents, and a tracked `tcw-config.local.yaml`
     (TCW-72).
   - The section "A leftover inheritance file from before 2.5.0" (`:85-99`)
     stays as long as `tcw validate` still reports such a file. If TCW-73
     removes that report, the section goes too.
7. **`docs/work-inbox-template.md`.** **[Decision]** Deleted. It describes 2.x
   inbox entries: loose files, `INDEX.md` folders, and "accepted" items
   (`docs/work-inbox-template.md:17-21`). In 3.0 a filesystem inbox entry is an
   item created with `tcw work new --stage inbox`, and a Jira inbox entry is a
   ticket. The request template now lives in the request prompt (TCW-74), and
   the Jira guide explains it to people outside engineering (Design 5.2). The
   README index row (`README.md:821`) goes with it.

### 6. The configure skill and its references

`skills/configure/references/` becomes the one place each configuration key is
documented.

| Reference | Covers |
| --- | --- |
| `work.md` | `work.path`, `work.repository`, `work.backend`, `work.tags`, `work.stages.<stage>` (`enabled`, `status`, `prompt`, `pre`, `post`), binding kinds and `when:`, `inherit: true`, `work.hooks` (`timeout`, `output-cap`), how hooks run, `work.procedures` |
| `jira.md` (replaces `tracker.md`) | `work.jira.*`: site, project, credentials, fields, priorities, `inbox-query`; how stages map to statuses; required custom fields; `tcw validate --remote` |
| `projects.md` | the connected-project keys (TCW-73's names), `upstream`, `TCW_PROJECT_<ID>`, `extends`, where a delegation target's Jira settings come from |
| `stores.md` | `<component>.path`, `<component>.repository`, `tcw provision`, keeping a separate store up to date (a link to the git example) |
| `docs-sync.md` | `work.documentation` entries |
| `personal.md` (**new**) | the layers and their order, `XDG_CONFIG_HOME`, `TCW_NO_PERSONAL_CONFIG`, how mappings and lists merge, `inherit: true`, `user.name`, `tcw config show --origin`, **the shared/overridable table** |

1. **[Decision] `tracker.md` is replaced by `jira.md`.** 3.0 has no
   "tracker"; the key is `work.jira`, and the file name should say so.
2. **[Decision] Each key is marked shared or overridable.** Each key's section
   in a reference starts with one line, `Shared: personal configuration cannot
   set it.` or `Overridable: personal configuration may set it.`
3. **[Decision] The table.** `personal.md` holds one table of every
   configuration key path with its marking. The overridable rows are exactly
   TCW-72's allowlist: stage `prompt` and `post`, `procedures`, credential
   variable names, and `user.*`. Every other row is shared, and the table says
   that a key added later is shared unless it is added to the allowlist.
   **This item writes the table.** TCW-72's ticket says the configure
   references are its home and that "TCW-75 links to it", which leaves the
   writing to nobody. The table is tied to TCW-72's allowlist in code by
   criterion 7, so it cannot drift away from it.
4. **[Decision] The binding rules move here.** The table of which binding kinds
   each position allows currently lives in the `work` skill's `hooks.md`
   (`skills/configure/references/work.md:26-28`). It moves into `work.md` here,
   and TCW-74's `hooks.md` links to it.
5. **The router** (`skills/configure/SKILL.md:24-35`) gets one row per
   reference in the table above. Its `description` and `when_to_use` name 3.0
   areas only, with no `work.lifecycle`, `dod.yaml`, `work.tracker`,
   `work.retain` or commit keys. Its `allowed-tools` drops `Bash(git *)`,
   since nothing in it runs git.
6. **The text test is replaced.** `tests/test_configuration_text_home.py` checks
   2.x tracker-inheritance sentences (`:22-55`). It is replaced with tests that
   every reference is linked from the router and every router link resolves
   (criterion 6). Whether the 2.x tracker-inheritance behavior survives at all
   is TCW-71's to decide; `jira.md` documents whatever TCW-71 ships.

### 7. Lifecycle documents and `AGENTS.md`

1. **`docs/lifecycle/abstraction.md`.** **[Decision]** Rewritten on this premise:

   > TCW's model sits on a small backend interface (create, read, list, update
   > properties, set stage, comment, rename, look up a backend name), which the
   > filesystem and Jira backends both implement. The technical record (stage
   > documents, rounds, handoffs, the declared record changes, taxonomy and
   > capabilities) is files in the repository in both modes, so the model may
   > read item folders directly. What a backend owns (properties, stage,
   > request, comments) it reaches only through the interface.

   - The question "Could a non-filesystem store implement this operation, even
     if less elegantly?" stays word for word. Module docstrings cite it
     (`tcw/store/base.py:3`), and `tests/test_repo_lifecycle.py:80-81` asserts
     it. It now governs **operations on what a backend owns**.
   - A second question is added for everything else: **"Who owns this fact:
     the backend, or the repository?"** A fact the repository owns may be read
     as a file in both modes. This is not a failure of the litmus test,
     because it is true in both backends.
   - The heading "Abstract spine, filesystem leverage" stays
     (`tests/test_repo_lifecycle.py:82`). Its vocabulary becomes: item, stage,
     move (`advance`), slug, reference, project relation, query, properties,
     request, comments, and the item folder's named files.
   - "Use freely" keeps documents next to code, one commit carrying a code
     change and a records change (made by the project, not TCW), and
     grep, diff and review legibility. "Atomic `mv` as transition" goes.
   - "Keep out of the model" becomes:
     - reconstructing state from git history;
     - inferring a stage from a folder location or from which documents
       exist (the stage is a property; the "stage ahead of documents" check
       only warns);
     - stage names outside the stage table;
     - treating an item folder as an open set of files (it is bounded: stage
       folders, `<stage>.md`, `round-N.md`, handoffs, `comments/`,
       `capabilities.yaml`, `item.yaml`);
     - hard-coded paths in references;
     - project relations read from directory nesting outside the
       project-resolution layer;
     - **any git operation**, since TCW never changes git state and git
       belongs to the project's own prompts and hooks.
   - The opening paragraph's "filesystem-native default … external tracker"
     framing (`:12`) is replaced by the premise above. The binding comment
     (`:1-2`) stays as it is; TCW-76 decides how 3.0 binds the file.
2. **`docs/lifecycle/implementation.md`.** Edited:
   - The store-interface rule (`:9`) becomes the backend interface, with both
     backends built and no method that only one backend could honor.
   - The section on stores in other repositories (`:14-50`) keeps its lesson
     (the store root and the project root vary independently; never prune at
     a nested repository) in "project" vocabulary. It uses the 3.0 helper names
     TCW-70 and TCW-73 settle, in place of `FsWorkStore.open`,
     `store_git_root` and `descendant_nodes`.
   - **[Decision]** "Beginning implementation" (`:52-54`) is deleted. It
     orders `tcw work start` and a commit, and 3.0 has neither. When TCW's own
     process should move an item is TCW-76's configuration to decide.
   - The test-writing rules (`:63-99`) stay.
3. **`docs/lifecycle/harness.md`.** One edit at `:12`: "hooks" becomes
   "Claude Code's own hooks (the harness's, not TCW's `pre` and `post`
   hooks)". In 3.0 the word "hooks" means TCW's stage hooks, which the `tcw`
   CLI runs identically under both harnesses. Read the old way, the sentence
   would wrongly call TCW's stage hooks Claude-only.
4. **`AGENTS.md` worktree section** (`AGENTS.md:80-101`). Rewritten as
   "Working in a git worktree":
   - TCW does not create worktrees. A contributor who makes one with
     `git worktree add` finds that the editable install still runs the primary
     checkout's source. The reason stays as written: the import hook takes
     priority over the module search path.
   - The fix is a virtual environment inside the worktree:
     `python -m venv .venv` and `.venv/bin/pip install -e '.[dev]'`, with pytest
     and `tcw` run from that environment. This leaves the shared install alone.
   - The sentences about `tcw work start --worktree` and `tcw work complete`
     tearing the worktree down go.
   - `README.md:845-848` says the same in one sentence and links here.

### 8. The opt-in git example

The example sits in `docs/guide/configuration.md` under the heading **"Example:
keeping git in step with each stage change (something your project adds)"**.
It opens by saying that TCW never runs git, and that this is one way a project
can.

1. **[Decision] The commit hook is a file**,
   `docs/guide/examples/commit-item-after-move.sh`. The guide shows its full
   text in a fenced block, and criterion 5 checks that the block and the file
   are identical and runs the file. A project copies it into its own
   repository, for example as `scripts/tcw-commit-item.sh`. TCW's own
   repository can bind it where it is (TCW-76).

   ```sh
   #!/bin/sh
   # Commit this work item's files after TCW moves it to a new stage.
   # An opt-in example: TCW itself never runs git.
   set -eu
   cd "$TCW_ITEM_PATH"
   git add -A -- .
   if git diff --cached --quiet -- .; then
       exit 0   # nothing to commit: normal in Jira mode, where a move may change no file
   fi
   git commit --quiet -m "Move $TCW_SLUG to $TCW_STAGE" -- .
   ```

   - It works from `TCW_ITEM_PATH`, not the project root. A work store kept in
     another repository is then committed in that repository, because git finds
     the repository from the current folder. TCW-69 does not say which folder
     hooks run in (2.x runs them in the project root, `tcw/work/hooks.py:94`), so
     the script does not depend on it.
   - It commits only the item's folder. The pathspec `-- .` limits both the
     staging and the commit, so other changes, staged or not, are left alone.
   - It succeeds with no commit when nothing in the folder changed.
2. **Pulling is prompt text**, so a failed pull never blocks a move:

   ```yaml
   work:
       stages:
           request:
               prompt: &pull-first
                   - blob: >-
                         Before you start, bring this branch up to date with
                         `git pull --ff-only`. If that fails, tell the user and
                         carry on with what you have.
                   - inherit: true
               post: &commit-after-move
                   - command: sh scripts/tcw-commit-item.sh
           spec: { prompt: *pull-first, post: *commit-after-move }
           plan: { prompt: *pull-first, post: *commit-after-move }
           implement: { prompt: *pull-first, post: *commit-after-move }
           review: { prompt: *pull-first, post: *commit-after-move }
           qa: { prompt: *pull-first, post: *commit-after-move }
           completed: { post: *commit-after-move }
           discarded: { post: *commit-after-move }
           postmortem: { prompt: *pull-first }
   ```

   The guide explains each part:
   - `&name` and `*name` are YAML anchors and aliases: a list written once and
     reused. TCW's own configuration edits keep them intact
     (`tcw/store/config_edit.py:14-21`).
   - Postmortem takes no `post`, because nothing ever moves into it (TCW-69
     Design 8).
   - A project leaves out the lines for stages it has turned off.
   - In Jira mode, each stage also carries its `status`.
3. **Pushing is an optional extra**, a second `post` entry:

   ```yaml
   post: &commit-and-push
       - command: sh scripts/tcw-commit-item.sh
       - command: git -C "$TCW_ITEM_PATH" push --quiet
   ```

   The guide states the consequence. A failed push, for example when offline,
   makes `advance` exit 6: the item has moved and the commit is local, and the
   next push carries it.
4. **What the example does not do**, stated in the guide:
   - Creating an item is not a move (TCW-69 Design 6), so a new item's folder
     is not committed by this hook; commit it as part of your work.
   - A project's own git hooks, such as a pre-commit check, can fail the commit.
     That is a failed `post` hook: exit 6, and the move stands.
5. **It can be personal.** `prompt` and `post` are overridable (TCW-72), so one
   person can put the same bindings in `tcw-config.local.yaml` without changing
   anything for the team. The guide says so and links to `personal.md`.

### 9. `docs/guide/cli.md`: output and exit codes

**[Decision]** A new guide, since the contract covers all three axes and the top
level. It covers:

- naming (`tcw noun [child-noun] verb`) and `--help`;
- stdout carries only the command's product, with TCW-73's per-command list;
- stderr carries the narration and names every file written or removed;
- commands never prompt;
- long text is read from stdin;
- the slug forms accepted (full slug, bare folder in the current project, Jira
  key in Jira mode), and no prefix matching;
- the exit-code table, with exit 6 meaning "the item moved, but something after
  the move failed: a `post` hook, or recording the trace comment" (TCW-69
  Design 6);
- two short examples of using the contract from a script
  (`SLUG=$(tcw work new … )`, and branching on `$?`).

### 10. Release notes and changelog

1. **Entry files.** **[Decision]** Named by the item's folder name, as the
   ticket requires: `docs/release-notes/upcoming/2026-10-01-tcw-75-documentation-for-tcw-3-0-readme-guides-and-the-opt-in-git-example.md`
   and the same name under `docs/changelogs/upcoming/`. If TCW-76 later renames
   this folder, the entry file keeps its name; the cut deletes it anyway.
2. **The 3.0.0 introduction.** **[Decision]** The release-notes entry starts
   with text before its first `##` heading. `scripts/cut_version.py` places
   such leading text first in the combined notes ("Leading blocks come first",
   `scripts/cut_version.py:106`). The introduction says, in plain language:
   - what 3.0 is, using the epic's vision in a few sentences;
   - that it is a major release with breaking changes;
   - that existing projects move over by following
     `docs/migration-guide-2.8-to-3.0.0.md` with an agent.

   It is the only `upcoming/` entry with leading text. Sibling items put
   everything under `##` headings, so the introduction stays first (see Notes,
   cross-slice finding 9).
3. **The rest of the release-notes entry** goes under `## Documentation`, a
   short list of the rewritten and new guides.
4. **Changelog entry**: `## Added` (`docs/guide/cli.md`,
   `skills/configure/references/personal.md`, the example script, the new
   tests); `## Changed` (the rewritten documents); `## Removed`
   (`docs/work-inbox-template.md`, `skills/configure/references/tracker.md`).
5. **The `upcoming/README.md` files** (`docs/changelogs/upcoming/README.md:6`
   and `docs/release-notes/upcoming/README.md:6`) say "named after the work
   item's folder name, never the full slug, whose `/` would make a path". The
   same change is made in `skills/configure/references/docs-sync.md:18-22`,
   `:45`, and in the configuration guide's example (`:212-216`, `:223`).
   TCW's own `tcw-config.yaml` entries are TCW-76's, and the
   `documentation-sync` skill's wording is TCW-74's.

### 11. Tests

New or changed tests, all run by bare `pytest` as CI does
(`.github/workflows/test.yml:76`):

- `tests/test_docs_describe_3_0.py` (new): the 2.x-vocabulary scan
  (criterion 2), link resolution (criterion 3), and the README structure
  (criterion 1).
- `tests/test_git_example.py` (new): criterion 5.
- `tests/test_configuration_text_home.py` (replaced): criteria 6 and 7.
- `tests/test_cli_guide.py` (new): criterion 8.
- `tests/test_repo_lifecycle.py`: unchanged. Its two `abstraction.md` phrases
  survive (Design 7.1), and its `implementation.md` and `harness.md` phrases
  ("don't pre-abstract", "Agentskills specification") are kept.
- `tests/test_documented_cli_surface.py`: unchanged, and it must pass
  (criterion 4).

## Abstraction litmus test

This item adds no operation and changes none. Two parts of it touch the model:

| Part | Verdict |
| --- | --- |
| The rewritten `abstraction.md` | Restates the rule for two backends. It keeps the litmus question and adds the ownership question (Design 7.1); every 3.0 operation TCW-69 lists passes both. |
| The git example | Uses only stage prompts and `post` hooks, which `advance` runs the same way in both backends. It tolerates a move that changed no file, which is the normal case in Jira mode. |

## Harness compatibility

- **Every document is plain Markdown**, read the same way under Claude Code and
  Codex.
- **The git example uses only TCW's prompt bindings and `post` hooks.**
  `tcw work stage prompt` prints the pull instruction and `tcw work advance`
  runs the commit, identically under both harnesses. It deliberately uses no
  Claude Code hook. A Codex user gets exactly the same behavior.
- **The `configure` skill** stays a router plus reference files, with nothing
  Claude-only in it. Dropping `Bash(git *)` from `allowed-tools` (Design 6.5)
  only narrows a Claude permission list, which Codex ignores.
- **`harness.md`** is corrected so that "hooks" in its Claude-only list cannot
  be read as TCW's stage hooks (Design 7.3).

## Acceptance criteria

Unless a criterion says otherwise, it is checked by a pytest test that runs under
bare `pytest`. **"Owned documents"** means: `README.md`; `docs/guide/*.md`
except `web-viewer.md`; `docs/lifecycle/{abstraction,implementation,harness}.md`;
`skills/configure/SKILL.md` and `skills/configure/references/*.md`; and the
section of `AGENTS.md` from `### Working in a git worktree` to the next `## `
heading.

1. **README structure.**
   - The `##` heading right after `## Overview` is exactly
     `## Why taxonomy and capabilities live in the repository`.
   - Every link in the README's Contents list points at a heading that exists in
     the README.
   - The `## Work` section has two headings at the same level whose text begins
     `Filesystem` and `Jira`, in that order.
   - The `## TCW Local Web App` section, and the CLI requirements paragraph
     under `### CLI`, do not contain `Node.js`.
   - The `## Documentation` table links
     `docs/migration-guide-2.8-to-3.0.0.md`,
     `docs/migration-guide-2.4.X-to-2.5.0.md` and `docs/guide/cli.md`, and does
     not link `docs/work-inbox-template.md`.
   - **By reading:** the new section makes the four points of Design 4.6 in
     that order. Point 3 is worded as a possibility ("could"), never as a
     feature.
2. **No 2.x vocabulary.** No owned document matches any pattern below
   (case-insensitive, Markdown code included):

   | Pattern | Why it goes |
   | --- | --- |
   | `tcw work (start\|submit\|rework\|complete\|drop\|inbox\|tracker\|delegate\|escalate\|reconcile\|nodes\|tombstone\|delete\|scaffold)\b` | removed or merged commands (TCW-73) |
   | `stage gate`, `stage validate`, `taxonomy init`, `capabilities init`, `taxonomy check`, `capabilities check` | removed or merged commands (TCW-73) |
   | `graveyard`, `dod\.yaml`, `definition of done`, `renames\.yaml` | removed store files (TCW-70) |
   | `state\.yaml`, `tracker\.yaml`, `intake\.md`, `initial-request\.md`, `refined-outcome\.md`, `rework\.md`, `\boutcome\.md` | 2.x item files (TCW-70) |
   | `work\.lifecycle`, `work\.tracker`, `auto-commit-transitions`, `publish-transitions`, `trunk-branch`, `work\.retain`, `builtin: true` | removed keys (TCW-69, TCW-72) |
   | `TCW_NODE_ROOT`, `TCW_STATUS`, `TCW_TRANSITION`, `TCW_RESOLUTION`, `TCW_WORK_OWNER` | removed variables (TCW-69, TCW-72) |
   | `--worktree`, `--initiative`, `--epic`, `--resolution` | removed flags (TCW-73) |
   | `docs/work/(inbox\|backlog\|active\|review\|completed\|discarded)/` | status folders (TCW-70) |
   | `spec/capabilities\.yaml` | wrong location (TCW-69 Design 4.4) |
   | `\bnodes?\b` not followed by `.js` | renamed to "project" (TCW-73) |
   | `\bno longer\b`, `\bpreviously\b`, `\bsince 3\.0\b` | a document describing a difference from 2.x |

   A mutation check (deliberately breaking the thing a test checks, to confirm
   the test fails) is part of the test: inserting `tcw work start` into a
   temporary copy of an owned document makes the scan fail.
3. **Links resolve.** Every relative Markdown link in an owned document points at
   an existing file, and an `#anchor` on a link into an owned document points at
   an existing heading. The one exception is
   `docs/migration-guide-2.8-to-3.0.0.md`. It is named in a single constant in
   the test, with a comment saying TCW-76 removes it when the guide exists.
4. **No phantom commands.** `tests/test_documented_cli_surface.py` passes
   unchanged against the 3.0 CLI.
5. **The git example works.** In a temporary git repository with a work item
   folder `docs/work/x/`, running `docs/guide/examples/commit-item-after-move.sh`
   with `TCW_ITEM_PATH`, `TCW_SLUG` and `TCW_STAGE` set:
   - after a file in `docs/work/x/` changed, exits 0 and makes exactly one new
     commit, whose changed paths are all under `docs/work/x/`;
   - when a file outside `docs/work/x/` is also changed (one staged, one not),
     leaves both uncommitted, with the staged one still staged;
   - when nothing in `docs/work/x/` changed, exits 0 and makes no commit;
   - when the item folder is inside a second git repository nested in the first,
     commits in the second repository and leaves the first unchanged.

   The fenced `sh` block under the example heading in
   `docs/guide/configuration.md` is byte-for-byte the script file. The YAML
   block in that section parses with `yaml.safe_load`, and the 3.0 config
   parser (`parse_work_config`) reports no problems for it.
6. **The configure skill is consistent.**
   - Every file in `skills/configure/references/` is linked from the router
     table in `skills/configure/SKILL.md`, and every router link resolves.
   - `tracker.md` does not exist.
   - The skill's frontmatter `description` and `when_to_use` match none of the
     criterion 2 patterns.
   - In every reference, each `##` section that documents a key has a line
     starting `Shared:` or `Overridable:` before its first code block.
7. **The override table matches the code.** The keys marked `Overridable` in
   `personal.md`'s table are exactly the key paths in TCW-72's allowlist
   constant. Every key path accepted by the 3.0 work config parser (TCW-69
   Design 8: `work.path`, `repository`, `backend`, `tags`, `documentation`,
   `procedures`, `stages.<stage>.{enabled,status,prompt,pre,post}`,
   `hooks.{timeout,output-cap}`, `jira`) has a row.
8. **The exit-code table matches the code.** The table in `docs/guide/cli.md`
   has one row per exit code constant in `tcw/exit.py`, with the same numbers,
   and no other rows.
9. **The abstraction document.** `tests/test_repo_lifecycle.py` passes
   unchanged. `docs/lifecycle/abstraction.md` contains the ownership question
   from Design 7.1, names each of the eight backend operations, and does not
   contain `mv`.
10. **Inventory carried out.** `docs/work-inbox-template.md` and
    `skills/configure/references/tracker.md` do not exist.
    `docs/guide/cli.md`, `docs/guide/examples/commit-item-after-move.sh` and
    `skills/configure/references/personal.md` exist. **By reading:** each
    document in Design 3 marked "rewrite" or "edit" has the outline given in
    Designs 4 to 7.
11. **Release notes.** Both entry files named in Design 10.1 exist. The
    release-notes entry has text before its first `##` line, and that text
    links the migration guide. Running `combine()` from
    `scripts/cut_version.py` over the current `upcoming/` release-note entries
    puts that text first.
12. **The full suite passes** under bare `pytest`.

### Coverage

| Design rule | Criteria |
| --- | --- |
| 1 Boundaries and ordering | 4, 12 (the suite passes with the other items landed) |
| 2 Writing rules | 2, 3 |
| 3 Inventory | 10 |
| 4 README | 1, 2, 3 |
| 5 Guides | 2, 3, 10 |
| 6 Configure | 6, 7 |
| 7 Lifecycle documents, `AGENTS.md` | 2, 9 |
| 8 Git example | 5 |
| 9 CLI guide | 8 |
| 10 Release notes | 11 |

## Risks

- **The documents describe code that keeps moving.** If a sibling item changes a
  command or key after this item lands, the documents go stale. Mitigation:
  this item lands after the code items (Design 1.1); criteria 2, 4, 7 and 8 tie
  the documents to the code, so a later change turns the suite red rather than
  leaving a silent mismatch.
- **The interim test failures need every code item to cooperate** (Design
  1.5). If one does not, the suite is red on the epic branch until this item
  lands. Mitigation: the rule is stated as a cross-slice finding for TCW-70,
  TCW-71 and TCW-73 to accept before they are implemented.
- **The vocabulary scan can reject legitimate text.** "No longer" may be the
  natural phrase for something unrelated to 2.x, and "node" may be needed for a
  third-party term. Mitigation: the scan is limited to owned documents. The
  writer rewords; the scan gains no exception list, because an exception list is
  how removed terms creep back.
- **The git example may be copied without being understood.** It commits whatever
  is in the item folder, including a half-written document. Mitigation: the guide
  says so, in the sentence before the script.
- **A dangling link until TCW-76 lands.** The migration guide does not exist
  when this item lands. Mitigation: one named exception in criterion 3, removed
  by TCW-76. Both land on the epic branch before 3.0.0 is cut, so no released
  version carries the dangling link.
- **Taking over the `configure` skill from TCW-74** could leave it edited by
  both items if TCW-74's ticket is not updated. Mitigation: a cross-slice
  finding, and criterion 6 fails if the router and references disagree.

## Notes

- **Decisions made in this spec, for the owner to confirm.** Each is marked
  **[Decision]** above:
  1. This item lands after TCW-69 to TCW-74 and TCW-77, and before TCW-76
     (Design 1.1).
  2. The file ownership table, including that this item owns all of
     `skills/configure/` and only the worktree section of `AGENTS.md`
     (Design 1.2).
  3. Until this item lands, each code item keeps the documentation tests
     passing with the smallest edit that does so (Design 1.5).
  4. `docs/work-inbox-template.md` is deleted (Design 5.7).
  5. `skills/configure/references/tracker.md` is replaced by `jira.md`
     (Design 6.1).
  6. Each key carries a `Shared:` or `Overridable:` line (Design 6.2).
  7. This item writes the shared/overridable table, in a new `personal.md`
     (Design 6.3).
  8. The binding rules move from the `work` skill's `hooks.md` into the
     configure reference (Design 6.4).
  9. The rewrite of `abstraction.md`: the litmus question kept word for word,
     an ownership question added, and git operations kept out of the model
     (Design 7.1).
  10. "Beginning implementation" is deleted from `implementation.md`
      (Design 7.2).
  11. The git example's commit hook ships as a tested file,
      `docs/guide/examples/commit-item-after-move.sh`, and works from
      `TCW_ITEM_PATH` (Design 8.1).
  12. The output contract gets its own guide, `docs/guide/cli.md` (Design 9).
  13. Entry files are named by the folder name, and the 3.0.0 introduction is
      this item's leading text in the release notes (Design 10.1, 10.2).
- **Cross-slice findings.** Nothing has been posted to any ticket.
  1. **`spec/capabilities.yaml` is still written in four tickets** after the
     owner confirmed `<item>/capabilities.yaml`: TCW-75's own ticket ("Add the
     `spec/capabilities.yaml` chain"), TCW-74 (the spec prompt "writes
     `spec/spec.md` and `spec/capabilities.yaml`"), TCW-77 (the
     `capabilities.yaml` form, its autocomplete row, and "work items point at
     capabilities through `spec/capabilities.yaml`"), and TCW-76's artifact
     table (corrected only in its update section). TCW-73's body also says it
     but its update section corrects it. This spec uses the confirmed location.
  2. **TCW-76 contradicts the design record on migrated verdicts.** It maps
     `refined-outcome.md` and `rework.md` to `qa/round-N.md`; the design record
     maps them to `review/round-N.md`. Either way, TCW-76 must also say what
     `judges` value a migrated verdict gets, or every migrated verdict reads as
     `stale` or `invalid` (TCW-69 Design 4.6-4.8).
  3. **Capability record owners omit TCW-74.** This ticket's "Who owns the
     rest" names TCW-69 to TCW-73 and TCW-77. TCW-74 deletes and rewrites
     skills that have records under `docs/capabilities/skills/`, so it must
     own those records too.
  4. **The `configure` skill is claimed by both TCW-74 and TCW-75.** This spec
     takes all of it (Design 1.2). TCW-74's ticket should drop `configure`
     from its list of rewritten skills, and its `hooks.md` should link to the
     configure reference for the binding rules (Design 6.4).
  5. **The shared/overridable table is left to nobody.** TCW-72 says the
     configure references are its home and that "TCW-75 links to it"; TCW-75
     says the references are the home "(TCW-72)". This spec has TCW-75 write
     it and TCW-72 provide the allowlist as a code constant that criterion 7
     can import. TCW-72 should name that constant in its spec.
  6. **Tests guarding the documentation fail mid-epic** (Problem 7). TCW-70,
     TCW-71 and TCW-73 need to accept the smallest-edit rule (Design 1.5).
     Separately, the exemption in `tests/test_documented_cli_surface.py:70-99`
     exists only because planning seeded `Missing` capabilities, which TCW-74
     reverses. TCW-74 should remove that exemption.
  7. **TCW-69's spec does not say which folder hooks run in.** 2.x uses the
     project root (`tcw/work/hooks.py:94`). The hook documentation has to state
     it, so TCW-69, or TCW-70 where the runner is wired, should fix it. The git
     example is written not to depend on it.
  8. **Nobody owns `tests/cli/scenarios/`.** Several scenarios describe 2.x
     behavior (`09-worktree-isolation-and-merge-back.md`,
     `10-cross-node-epics-and-nesting.md`,
     `11-scaffold-and-artifact-templates.md`). Suggested owner: TCW-73, since
     they drive the CLI surface.
  9. **Release-note leading text.** Only this item's release-notes entry may
     have text before its first `##` heading, or the 3.0.0 introduction stops
     being first. The rule should reach every sibling item.
  10. **Entry file naming crosses three items.** This item changes the
      `upcoming/README.md` files and the configure reference (Design 10.5).
      TCW-74 must change the `documentation-sync` skill's `<work-item-slug>`
      wording
      (`skills/documentation-sync/references/release-notes-and-changelogs.md:16`,
      `:21`, `:31`). TCW-76 changes TCW's `tcw-config.yaml` entries and the
      `AGENTS.md` Versioning section.
  11. **Does adopting a Jira ticket run `post` hooks?** TCW-71's adopt ends with
      "move to request". If that is an `advance`, the git example commits the
      new folder; if not, it does not. TCW-71's spec should say which, and the
      Jira guide will document the answer.
  12. **Terms this item depends on are still open**: TCW-73's new names for the
      connected-project keys, TCW-72's answer on `TCW_PROJECT_<ID>`, TCW-74's
      request-template section names, and TCW-74's switch for the optional
      postmortem comment (TCW-74 says it is "off by default" but not how it is
      turned on).
- **Open questions only the owner can answer.**
  1. Confirm that TCW-75 owns all of `skills/configure/` (Design 1.2) rather
     than sharing it with TCW-74.
  2. What happens to the `Planning doc` capability field? TCW-76 is assigned
     this decision but lands after this item, while this item's
     taxonomy-and-capabilities guide and `README.md` must describe the field
     either way. Deciding it before this item is implemented avoids
     documenting it twice.
  3. Delete `docs/work-inbox-template.md`, or keep a 3.0 version as a guide to
     writing a request for people outside engineering? This spec deletes it
     and covers the subject in the Jira guide.
  4. Should the 3.0.0 introduction in the release notes be this item's
     (as decided here) or TCW-76's?
  5. Accept the smallest-edit rule for code items (Design 1.5), or let the
     epic branch carry failing documentation tests until this item lands?
- **Driving this item.** It edits no code under `tcw/`, but it lands while the
  epic is changing `tcw/`, so the repository's own board is driven by editing
  files, as `CLAUDE.md` requires.
