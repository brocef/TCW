# Spec — Documentation for TCW 3.0: README, guides and the opt-in git example

## Capability changes

```yaml
# <item>/capabilities.yaml
changed: [skills/configure]
taxonomy:
  changed: [configure-skill]
```

- **`skills/configure` (cap-97192e), changed.** This item owns the whole
  `configure` skill (epic decision 3, Design 1.2), so it owns the skill's
  record too. The record says the skill points to a document
  for, among other things, "the Definition of Done, whether transitions commit
  and publish themselves, the trunk branch, deleting resolved items"
  (`docs/capabilities/skills/configure/description.md:1`). 3.0 removes all of
  those settings (TCW-69 Design 8.4). It also adds settings the record does not
  list: stages and hooks, the Jira backend, and personal configuration. The
  description is rewritten to list the areas in Design 6. Its status stays
  `Supported`. Its `Planning doc` field is not this item's to touch: TCW-73
  removes the field from the capabilities commands, and TCW-76 removes it from
  every record during the migration (epic decision 9).
- **No other capability record changes.** Documentation does not change what a
  user can do with TCW. Each behavior is recorded by the item that ships it:
  TCW-69 to TCW-73 and TCW-77, as the ticket says, plus TCW-74 for every other
  skill it deletes or rewrites (epic decision 3). The 46 records under
  `docs/capabilities/work/` are TCW-70's, with TCW-71 and TCW-73 as epic
  decision 12 says.
- **`configure-skill` (taxonomy Feature), changed.** **[Decision]** This item
  owns the Feature as it owns the skill: TCW-74 says so (TCW-74 spec,
  Capability changes), following epic decision 3. The term removals and renames inside
  it are done earlier by the items that remove or rename those terms, because
  `tcw taxonomy rm` refuses to remove an entry that another entry still names
  (`README.md:307`): TCW-70 drops `work-item/definition-of-done` (TCW-70 spec,
  Capability changes, Taxonomy), TCW-71 replaces `external-work-tracker` with
  `jira-work-backend` (TCW-71 spec, Capability changes), and TCW-73 replaces `node` with
  `project` and removes `connected-project-registry` in favour of
  `project-registry` (TCW-73 spec, Capability changes). What is left for this
  item, checked against the entry as those items leave it
  (`docs/taxonomy/configure-skill/meta.yaml:3-13` today):
  - the description (`docs/taxonomy/configure-skill/description.md`) is
    reworded to name the 3.0 areas the skill covers (Design 6);
  - `relatesTo` names the Features those areas belong to:
    `configurable-work-lifecycle`, `configurable-component-store-location`,
    `jira-work-backend`, `project-registry`, and TCW-72's
    `personal-configuration`, which already relates back to this Feature
    (TCW-72 spec, Capability changes). Nothing else is added.

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
   spec hands this rewrite to this item (TCW-69 spec, Abstraction litmus test, closing paragraph).
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
   (`:22-47`) and in the `work` skill's `commands.md` (`:50-55`), a file
   TCW-74 rewrites.
   `tests/test_repo_lifecycle.py` asserts two phrases in `abstraction.md`
   (`:76-84`), but TCW-70 deletes that file with the 2.x parser it guards
   (TCW-70 Design 15.1), so those two phrases lose their only check. When
   TCW-70, TCW-71 and TCW-73 remove commands and keys, the documents still
   name them, and the documented-surface test fails before this item runs.

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
   `skills/configure/references/`. Each key says whether it is shared, can be
   overridden, or may be set only in personal configuration, and one table
   lists them all.
4. **The abstraction rules hold in 3.0.** The litmus test keeps its question
   (the one-line test "could a non-filesystem store implement this operation,
   even if less elegantly?", which module docstrings cite). It is restated for a
   model with two backends and files in git in both modes.
5. **One documented, tested git example** keeps git in step with each stage
   change using only prompt text and a `post` hook, in the project's own
   repository and in a work store kept in another repository.
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
  - Built-in prompts (`tcw/work/prompts/`), procedures, agents, `evals/`, and
    every skill except `configure` (epic decisions 3 and 14): TCW-74. This
    includes the request template's text, which lives in the request prompt.
  - The migration guide, TCW's own `tcw-config.yaml`, `docs/procedures/`,
    `docs/lifecycle/templates/`, and every part of `CLAUDE.md` and `AGENTS.md`
    except their worktree section: TCW-76.
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
  They are TCW-73's (epic decision 14).
- **Generating documentation from the records.** The README mentions it as a
  possibility only.

## Design

### 1. Boundaries and ordering

1. **Ordering.** The owner's order of work is 69 → 70 → 71 → 73 → 72 →
   {74, 77} → 75 → 76 (review decision R1): this item is blocked by TCW-74 and
   TCW-77, and so comes after every code item, and TCW-76 is blocked by it. The documents
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
   | `skills/configure/` (its `SKILL.md` and every file in `references/`, including `personal.md`), the `skills/configure` capability record, and the `configure-skill` taxonomy Feature | this item |
   | every other skill, `agents/`, `tcw/work/prompts/`, procedures, `evals/` | TCW-74 |
   | worktree section only of `AGENTS.md` (`:80-101`; `CLAUDE.md` is a symbolic link to it) | this item |
   | `CLAUDE.md` and `AGENTS.md`, everything else; `tcw-config.yaml`; `docs/procedures/`; `docs/lifecycle/templates/` | TCW-76 |
   | `docs/migration-guide-2.8-to-3.0.0.md` | TCW-76 |
   | `docs/{changelogs,release-notes}/upcoming/README.md` | this item |
   | this item's own `upcoming/` entry files | this item |

   The `configure` skill is this item's (epic decision 3). The skill is a
   router table plus the reference documents it routes to. If two items each
   wrote one half, the table and the files could disagree, and
   `tests/test_configuration_text_home.py:58-61` already checks the two
   against each other. The `work` skill, which TCW-74 rewrites, links to the
   configure references for every configuration fact.

   No earlier item writes into `skills/configure/`. TCW-72 in particular
   writes neither `personal.md`, nor the shared/overridable table, nor its
   router line, nor a test of the table: it supplies only the constant
   `tcw.config.PERSONAL_KEYS` and a test that it can be imported (TCW-72 spec
   Design 12, "Not written here", and its criterion 15). This item writes all of them.

   **[Decision]** `CLAUDE.md` is a symbolic link to `AGENTS.md` (`ls -la`
   shows `CLAUDE.md -> AGENTS.md`), so the worktree section exists once, in
   `AGENTS.md`, and the plan edits that one file. A plan step that edits
   "both" would apply the same edit twice.
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
5. **Keeping the suite passing in the meantime** follows epic decision 6.
   TCW-70 adds a temporary allowance list to
   `tests/test_documented_cli_surface.py`: the commands and keys it removes,
   with a guard test asserting that each entry really is gone from the CLI.
   TCW-71 and TCW-73 add their removals to it. TCW-74 and this item shrink it
   as they rewrite text, and TCW-76's "validate clean" step requires it to be
   empty before 3.0.0 is cut.
   - **[Decision]** After this item's rewrite, no owned document names any
     allowance entry. This item then removes every entry that no live
     document names any more. An entry still named by a document someone else
     owns stays in the list, and is named, with that file, in this item's
     implement round, so TCW-74 or TCW-76 knows it is theirs. Criterion 4
     checks the owned documents.
   - TCW-74's two new skill tests (no git words in shipped text, and every
     named command exists) skip `skills/configure/` through one named
     exclusion entry whose reason names this item (TCW-74 Design 6.2). This
     item deletes that entry when it rewrites the skill, so both tests then
     scan `skills/configure/` too. Any wording in the git example that
     legitimately says "git" or "another repository" is added to those tests'
     own allowlists, with its reason.
   - **[Decision]** `tests/test_configuration_text_home.py` is not covered by
     the allowance. It reads only `tracker.md`, `commands.md` and the router,
     whose text no code item changes, so it keeps passing until this item and
     TCW-74 change those files. This item replaces it (Design 6.6); if TCW-74
     rewrites `commands.md` first, TCW-74 deletes the one test that reads it
     (`:50-55`).

### 2. Writing rules for every document this item writes

1. Plain language, as `CLAUDE.md` requires. A technical term is defined in the
   sentence where it first appears in each document.
2. **No 2.x vocabulary.** The terms in the table under Acceptance criterion 2
   appear in no document this item owns, except as that criterion allows.
3. **The two backends side by side.** Wherever behavior differs by backend, both
   are described at the same level of detail, with the filesystem backend
   first. "Filesystem" is the name used throughout, not "vanilla".
4. **"Project", never "node".** Slugs are written `project/folder`.
5. **Git is the project's choice.** The rule, in the design record's words, is
   that TCW **never changes git state** (review decision R4). A document may
   say so; may describe the git reads TCW makes (finding the repository root,
   the uncommitted-changes check before delegating, the linked-worktree
   check) and the clone `tcw provision` makes; and may show the opt-in example
   (Design 8). No document says that TCW "never runs git" or "does not run
   git", because it does run git for those reads and that clone; criterion 2
   refuses the phrase.
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
| `AGENTS.md` worktree section (`:80-101`; `CLAUDE.md` links to the file) | rewrite | Design 7.4 |
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
     blocked-by). An item with children is an epic. TCW never changes git
     state (Design 2.5).
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
     on the move out of implement; qa checks the product's behavior. In
     filesystem mode the agent may record the qa verdict unless the project's
     own qa prompt asks for a person (**[Decision, owner 2026-10-01]**); when
     it does, the agent still writes the round, recording the person's
     decision (review decision R17, Design 5.1).
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
10. **TCW Local Web App** (`README.md:768-805`): rewritten to match TCW-77
    (TCW-77 spec, Capability changes). It runs as one Python process with no Node.js. It
    reads, edits and creates documents, and also creates work items
    (including into another project), taxonomy entries and capabilities, and
    in Jira mode lists inbox tickets and adopts them. It runs no stage moves
    and shows the stage without letting you change it. In Jira mode, what
    Jira owns is read-only, with an "Open in Jira" link (TCW-71's
    `ticket_link`, TCW-71 spec Design 7.3). It serves one project. It keeps
    the same local-only protections. The README's list is a summary that
    links to `docs/guide/web-viewer.md` (TCW-77's) for the details.
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
      filesystem mode, and the ticket in Jira mode. Two Jira-only cases are
      explained here (epic decision 16): priority can be empty when the Jira
      project has no priority field, and a linked parent or blocking ticket
      that has no item is listed as "untracked" rather than dropped.
   2. The stage table, with every column explained in words (TCW-69 Design
      3): which stages can be turned off, side stages, terminal stages.
   3. The item folder:
      - stage folders, `<stage>/<stage>.md`, `<stage>/round-N.md`, verdicts
        and `judges`, what `stale` means and how it arises;
      - handoffs, comments and `<item>/capabilities.yaml`;
      - `tcw work path`, including `--handoff`, which prints where the stage's
        handoff file goes (epic decision 18);
      - who records the qa verdict in filesystem mode
        (**[Decision, owner 2026-10-01]**, owner answer Q9): by default the qa
        prompt lets the agent judge the result against the request and write
        `qa/round-N.md` itself. A project that wants a person to decide says
        so in its own `prompt` binding for qa (TCW-74's qa prompt). The agent
        then runs the scenarios, shows the person the evidence, asks for
        accepted or rejected with a reason, and writes `qa/round-N.md`
        recording that decision, with `decided-by: <name>` in its front
        matter (review decision R17). Jira mode is different: QA accepts or
        rejects on the ticket (Design 5.2).
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
      **[Decision, owner 2026-10-01]** `tcw work list --tag` is documented as
      kept: the flag can be repeated, and an item is listed when it carries
      any of the given tags (TCW-69's `Query.tags`, TCW-73). In Jira mode
      tags are the ticket's labels (TCW-71), and the Jira guide's "Who owns
      what" section says so.
   7. References and what `tcw validate` reports: a reference to a missing
      item and a stage ahead of its documents are warnings; a reference into
      a project that cannot be reached from here is reported as
      "unresolved", which is neither a warning nor an error (TCW-69 Design 9;
      review decisions R14 and R16). A command that has to read a declared
      project that is not on this machine exits 5 (epic decision 4); this
      section says so and links to the exit-code table in
      `docs/guide/cli.md`.
   8. Stage instructions and procedures: `stage prompt`, `lifecycle`,
      `procedure`, `docs`.
   9. "TCW never changes git state": one paragraph that names the git reads
      TCW does make (Design 2.5) and links to the example in the
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
      the request template's sections, which are TCW-74's (What and why,
      Product changes, Out of scope, Constraints, References; "none" is a
      valid answer for Product changes); following progress (the ticket's
      status is the stage); where the QA plan appears (a comment posted at
      spec); how QA accepts or rejects on the ticket (a rejection needs a
      comment saying why); that a rejected or duplicate inbox ticket is closed
      in Jira by a person, and the agent comments on it with the reason
      (review decision R19); the optional postmortem comment, which a project
      turns on through its own `prompt` binding for the postmortem stage
      (TCW-74 Design 2, postmortem).
   3. **Setting up**: a minimal `work.jira` and `work.stages.<stage>.status`
      example that links to the configure reference. **[Decision, owner
      2026-10-01]** Where the example shows status names, it uses the ones
      TCW's own Jira project uses: every optional stage turned on, with
      `spec` mapped to `Specifying`, `plan` to `Planning` and `qa` to `In QA`; the TCW Project and TCW
      Item fields; credentials named by environment variable.
   4. **Stages and statuses**: one status per enabled stage; how a move picks
      its transition (epic decision 5): when Jira offers exactly one
      transition to the target status, that one; when it offers several, the
      one whose screen asks for nothing except a comment; when that still
      leaves none or more than one, the move is refused with exit 3 and the
      message lists the candidates. A ticket in a status with no stage; a
      ticket moved by hand in Jira counts as a forced move with no reason
      recorded.
   5. **Checking the workflow**: `tcw validate --remote` and what it reports.
      It prints findings only, one per line, and a move it could not check is
      itself a finding (epic decision 10). The `setup` skill walks through
      fixing the workflow with the user; TCW changes nothing in Jira's
      workflow itself.
   6. **Adopting tickets**: the default inbox query, `inbox-query`,
      `tcw work tickets list` (one ticket key per line, details with
      `--json`, epic decision 10; it lists only tickets `adopt` would accept,
      meaning at the inbox or request status and in the same Jira project,
      review decision R19), `tcw work tickets adopt`, and which statuses a
      ticket may be adopted from (TCW-71 Design 7.2). Adopting runs the
      request stage's `post` hooks, and no `pre` hooks or gates (TCW-71
      spec Design 7.2), so a project's `post` hook, such as the git example,
      runs for an adopted item. Creating an item with `new`, and delegating,
      run no hooks.
   7. **QA on the ticket**: `advance --to completed --reason …` and
      `advance --to implement --reason …`; why a bare `advance` from qa is
      refused.
   8. **Delegating** with `tcw work new --project`: what stdout prints (a slug,
      or the ticket key when TCW stopped after creating the ticket, epic
      decision 16), and what happens with a target that is declared but not
      on this machine (owner answer Q1, review decision R5, TCW-71 Design 8):
      when this project's entry for the target has a `jira` block, TCW
      creates the ticket in the target's inbox, prints the key and exits 0;
      without one, the delegation is refused with exit 3. Delegating into an
      upstream project is refused with exit 3 (review decision R2).
   9. **What needs the network**, and what `tcw validate` without `--remote`
      checks offline: it never calls Jira, and a `tcw://` link to an item is
      checked by whether its folder exists (review decision R20).
   10. **Names of people**: `show` and `list` print display names for
       assignees and comment authors; `--json` carries Jira account IDs
       (review decision R15).
   11. **Limits**: Jira Cloud only; two people adopting the same ticket at the
       same moment; team-managed projects, where priority may be missing
       (TCW-71 Design 12); TCW never fills in a transition screen field other
       than the comment (TCW-71 Design 13).

   The request template's section names are those of TCW-74's request
   prompt. The guide lists them with one line each and says that
   `tcw work stage prompt request` prints the full template.
3. **`docs/guide/configuration.md`.** Rewritten:
   - what `tcw-config.yaml` holds, and that it is trusted like any other file
     in the repository (kept from `:3-6`);
   - the configuration layers (team file, user-wide file, per-project personal
     file), in one paragraph that links to `personal.md`, and that says a
     personal `post` list replaces the team's for that stage unless it holds
     `inherit: true`, while `pre` stays shared (**[Decision, owner
     2026-10-01]**);
   - stage bindings (`prompt`, `pre`, `post`), binding kinds, `when:` and
     `inherit: true`, each shown by example and linked to `work.md` for the
     full rules;
   - **how hooks run**, as a narrative linked to the reference:
     - `pre` hooks run only for the target stage;
     - a failing `pre` refuses the move unless it is forced;
     - **`pre` hooks may run again for the same move** (a Jira workflow can
       refuse the move after they ran), so they must be safe to repeat. TCW-69
       hands this sentence to this item (TCW-69 spec Design 6, step 7);
     - `post` hooks run after the move, and a failure keeps the move and exits
       6;
     - the working directory: hooks run with the project root as their
       working directory (epic decision 11);
     - the environment variables of a `pre` or `post` hook: `TCW_SLUG`,
       which is the full slug `project/folder` (epic decision 11),
       `TCW_STAGE`, `TCW_FROM_STAGE`, `TCW_ITEM_PATH`, `TCW_PROJECT_ROOT`,
       `TCW_CONFIG_DIR` (the folder of the file that declared the hook, TCW-72
       spec Design 6.2), and `TCW_FORCED` and `TCW_REASON` on a forced move.
       Only the 3.0 names appear here; how 2.x variables map to them, by
       meaning, is the migration guide's (TCW-76);
     - what a `generate:` prompt binding receives: the same variables, with
       `TCW_STAGE` the stage whose prompt is being composed and
       `TCW_FROM_STAGE`, `TCW_FORCED` and `TCW_REASON` absent, plus
       `TCW_HOOK_ROLE`, `TCW_HOOK_KIND`, `TCW_HOOK_ID` and `TCW_HOOK_PHASE`
       (TCW-69 Design 8); and on stdin one JSON object, `{"schema": 1,
       "item": …, "request": …, "hook": {…}}` (review decision R13). The
       `{{tcw:request}}` placeholder is named here and explained in
       `work.md`;
     - the timeout and the output cap;
   - documentation entries (kept from `:198-248`; its `<slug>` example
     placeholders become `<folder>`, per Design 10);
   - **the git example** (Design 8).
4. **`docs/guide/multi-repo.md`.** Rewritten around "project":
   - project IDs, and the fact that paths only say where a project is;
   - connecting projects, using TCW-73's renamed key (`projects`, with its
     `parent`, `children` and `upstream` entries; TCW-73 Design 9);
   - `upstream` projects;
   - where a project is on this machine: `TCW_PROJECT_<ID>`, which stays the
     only way to say it and is not personal configuration (TCW-72 Design 11);
   - **[Decision, owner 2026-10-01]** the key is `projects:` and the Feature
     is `project-registry` (TCW-73, renamed from `connected-projects:` and
     `connected-project-registry`); the guide uses only the new names;
   - what happens when a project is declared but is not on this machine: a
     command that needs it exits 5 (epic decision 4);
   - slugs across projects;
   - delegating with `tcw work new --project`: the three conditions (path
     resolved, work store present, no uncommitted changes in it, which TCW
     checks by reading git and changing nothing, Design 2.5), what happens in
     each backend, and that files written in another repository are left
     uncommitted. Delegation by where the target is (owner answer Q1, review
     decisions R2 and R5):
     - a project nothing declares: refused, exit 3;
     - declared but not on this machine, with no `jira` block in this
       project's entry for it: refused, exit 3;
     - declared but not on this machine, with a `jira` block: TCW creates the
       ticket in the target's Jira inbox, prints the key and exits 0;
     - an upstream project: refused, exit 3, because upstream projects are
       read-only;
     - `tcw work edit --blocks` into another project never creates anything,
       and is refused (exit 3) for a target known only through a `jira`
       block;
   - `tcw projects list`;
   - stores in another repository, and `tcw provision`, which clones a store
     that is missing and never updates one that exists (TCW-73 spec
     Design 8, item 4); keeping a store up to date is the project's job, and the
     git example's pull instruction covers a work store kept in another
     repository (Design 8.2);
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
     `spec/capabilities.yaml` (epic decision 19).
   - **Drift** is described by the 3.0 rule (TCW-69 Design 7): the newest
     declaration from a completed item wins; two items created the same day
     that disagree are reported as ambiguous; and drift also reports inherited
     capabilities nobody has reviewed.
   - `check` (`:7`, `:89`) is replaced by `tcw validate`.
   - `Planning doc` (`:78`, `:94`) is removed from the guide's field list.
     TCW-73 removes it and the `Tracker` field from the capabilities commands, and
     TCW-76 removes them from the records (epic decision 9). The guide says
     that work items point at capabilities through `<item>/capabilities.yaml`,
     and that a record never points back at a work item.
   - The child-ledger example (`:111-121`) keeps the path-prefix rule and
     drops "completion checks" and `set … --status Supported`.
6. **`docs/guide/linking-and-validation.md`.** Edited:
   - `tcw://` links: the project part reads "a project this one is connected
     to" for work and "a project listed by `extends`" for taxonomy and
     capabilities, using TCW-73's names (`:15-16`).
   - `tcw validate` and `tcw validate --remote`: what each checks, and that
     validation without `--remote` never needs the network (review decision
     R20). Each finding is an error, a warning, or "unresolved" (review
     decision R14); a check that was skipped is not a finding, and stderr
     says what was skipped (review decision R16).
   - The record files held to the mapping rule become `item.yaml` and
     `meta.yaml` (`:67-68`), and the `dod.yaml` sentence (`:80-83`) goes.
   - The work-item check (`:45-51`) describes the mid-work records check: an
     unreadable or malformed `capabilities.yaml`, an unknown key, a path that
     cannot be checked, and a removal of an inherited capability are reported;
     a change not yet made is not (TCW-69 Design 7).
   - New warnings: a reference to a missing item, a stage ahead of its
     documents, and a tracked `tcw-config.local.yaml` (TCW-72). A reference
     into a project that cannot be reached from here is reported as
     "unresolved", which is neither a warning nor an error (TCW-69 Design 9).
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
| `work.md` | `work.path`, `work.repository`, `work.backend`, `work.tags`, `work.stages.<stage>` (`enabled`, `status`, `prompt`, `pre`, `post`), binding kinds and `when:`, `inherit: true`, `work.hooks` (`timeout`, `output-cap`), how hooks run and every variable they get (Design 5.3, including `TCW_CONFIG_DIR`), what a `generate:` binding gets (its four `TCW_HOOK_*` variables and its stdin object, review decision R13), `{{tcw:request}}`, `work.procedures` |
| `jira.md` (replaces `tracker.md`) | `work.jira.*`, every key TCW-71's parser accepts (TCW-71 spec Design 1): `site`, `project`, `credentials` (`email-env`, `token-env`), `fields` (`project`, `item`, `effort`, `complexity`), `priorities`, `issue-type`, `inbox-query`, `timeout`; how stages map to statuses; required custom fields; `tcw validate --remote` |
| `projects.md` | the connected-project key (`projects`, TCW-73), `upstream`, `TCW_PROJECT_<ID>`, a declared project that is not on this machine (reading it exits 5, epic decision 4), delegation by where the target is (the five cases of Design 5.4), `extends`; where a delegation target's Jira settings come from: the target's own `tcw-config.yaml` when it can be read (never inherited from this project), and otherwise the optional `jira` block in this project's entry for the target, whose keys are `site`, `project`, `inbox-status`, `credentials` (`email-env`, `token-env`) and `fields` (`project`), with the site and the credential names always taken from the same file (TCW-71 spec Design 8, step 1) |
| `stores.md` | `<component>.path`, `<component>.repository`, `tcw provision` (clones a missing store, never updates an existing one), keeping a separate store up to date (a link to the git example, Design 8.2) |
| `docs-sync.md` | `work.documentation` entries |
| `personal.md` (**new**) | the layers and their order, `XDG_CONFIG_HOME`, `TCW_NO_PERSONAL_CONFIG`, how mappings and lists merge, `inherit: true`, `user.name` and the message when no identity is set (review decision R3), `tcw config show --origin` and how it prints a built-in entry (`- builtin: true  # <packaged file>`, which is never accepted in a file; review decision R8), that a linked git worktree has no `tcw-config.local.yaml` because the file is untracked (TCW-72 spec, Risks), **the shared/overridable table** |

1. **[Decision] `tracker.md` is replaced by `jira.md`.** 3.0 has no
   "tracker"; the key is `work.jira`, and the file name should say so.
2. **[Decision] Each key is marked with one of three labels.** Each key has
   its own `##` or `###` section in exactly one reference, whose heading
   contains the key path in backticks. The section's first line, before any
   code block, is one of:
   - `Shared: personal configuration cannot set it.`
   - `Overridable: personal configuration may set it.`
   - `Personal only: only personal configuration may set it.` This is for
     `user.name`, which is an error in `tcw-config.yaml` (TCW-72 spec
     Design 4.1, its allowlist table, and Design 4.5).

   A section that covers several keys, such as `work.stages.<stage>` or
   `work.jira`, is split into one sub-section per key, so that no section
   needs two labels.
3. **[Decision] The table.** `personal.md` holds one table of every
   configuration key path (the list in criterion 7) with its label. The rows
   labelled `Overridable` or `Personal only` are exactly TCW-72's allowlist
   constant, `tcw.config.PERSONAL_KEYS` (TCW-72 Design 4.1): `user.name`
   (personal only), `work.stages.*.prompt`, `work.stages.*.post`,
   `work.procedures.*`, `work.jira.credentials.email-env` and
   `work.jira.credentials.token-env`. Every other row is shared, including
   everything inside a `projects:` entry (credential names there too, TCW-72
   Design 4.1), and the table says that a key added later is shared unless it
   is added to the allowlist. The `user` row reads `user.name`, the only key
   under `user` (TCW-72 spec Notes, the changes it asks of TCW-75).
   **[Decision, owner 2026-10-01]** The table and `personal.md` state the
   owner's answer plainly: a personal `post` list for a stage **replaces** the
   team's `post` hooks for that stage unless it contains `inherit: true`
   (TCW-72 Design 4.1), so one person can drop a team hook for themselves;
   `pre` hooks are shared, so the team's gates always run.
   The table is this item's, because all of `skills/configure/` is (epic
   decision 3). TCW-72 writes neither the table nor a test of it; it supplies
   only `PERSONAL_KEYS` and a test that the constant can be imported (TCW-72
   spec Design 12 and its criterion 15). This item writes the table, `personal.md`,
   its router line, and the test that ties the table to the constant
   (criterion 7).
4. **[Decision] The binding rules move here.** The table of which binding kinds
   each position allows currently lives in the `work` skill's `hooks.md`
   (`skills/configure/references/work.md:26-28`). It moves into `work.md` here.
   TCW-74 deletes `hooks.md` (TCW-74 Design 7, its file table), and the
   `work` skill links to `work.md` for the rules.
5. **The router** (`skills/configure/SKILL.md:24-35`) gets one row per
   reference in the table above. Its `description` and `when_to_use` name 3.0
   areas only, with no `work.lifecycle`, `dod.yaml`, `work.tracker`,
   `work.retain` or commit keys. Its `allowed-tools` drops `Bash(git *)`,
   since nothing in it runs git.
6. **The text test is replaced.** `tests/test_configuration_text_home.py` checks
   2.x tracker-inheritance sentences (`:22-47`, `:58-61`) and a sentence in
   the `work` skill's `commands.md` (`:50-55`). It is replaced with tests that
   every reference is linked from the router and every router link resolves
   (criterion 6). TCW-71 drops inheritance of Jira settings between projects
   (TCW-71 Capability changes, `work/inherit-tracker-settings-from-parent-nodes`), so `jira.md` says each project states
   its own `work.jira` block, and the inheritance sentences go with
   `tracker.md`. The one place another project's Jira settings are read is
   the connected-project `jira` block used for delegation, which
   `projects.md` documents (Design 6, its row).

### 7. Lifecycle documents, and the worktree section of `CLAUDE.md` and `AGENTS.md`

1. **`docs/lifecycle/abstraction.md`.** **[Decision]** Rewritten on this premise:

   > TCW's model sits on a small backend interface of eleven operations
   > (create, read, list, update properties, set stage, comment, rename, look
   > up a backend name, read the request, read comments, and name the current
   > user), which the filesystem and Jira backends both implement. The
   > technical record (stage
   > documents, rounds, handoffs, the declared record changes, taxonomy and
   > capabilities) is files in the repository in both modes, so the model may
   > read item folders directly. What a backend owns (properties, stage,
   > request, comments) it reaches only through the interface.

   - The interface is TCW-69's eight operations plus the three reads epic
     decision 1 adds (`read_request`, `read_comments`, `current_user`). The
     document lists them under a heading `## The backend interface` as a
     bullet list of exactly eleven items, each starting with its name in
     bold, using the names of TCW-69's litmus table (TCW-69 spec, Abstraction litmus test table):
     **create**, **read**, **list**, **update**, **set stage**, **comment**,
     **rename**, **lookup**, **read request**, **read comments**, **current
     user**. Each item says in plain words what the operation does; the
     signatures live in `tcw/work/backend.py` and are not repeated. It also
     says that an
     item can carry the keys of linked tickets that have no item
     ("untracked"), and that a property such as priority can be empty when a
     backend has no place for it (epic decision 16), since both are how an
     honest backend reports what it cannot map.
   - The question "Could a non-filesystem store implement this operation, even
     if less elegantly?" stays word for word. Module docstrings cite it
     (`tcw/store/base.py:3`), and `tests/test_repo_lifecycle.py:81` asserts
     it today. That test file is deleted by TCW-70 (Design 15.1 there), so
     this item's own test asserts the phrase instead (criterion 9). It now
     governs **operations on what a backend owns**.
   - A second question is added for everything else: **"Who owns this fact:
     the backend, or the repository?"** A fact the repository owns may be read
     as a file in both modes. This is not a failure of the litmus test,
     because it is true in both backends.
   - The heading "Abstract spine, filesystem leverage" stays
     (asserted today at `tests/test_repo_lifecycle.py:82`, and by criterion 9
     once that file is gone). Its vocabulary becomes: item, stage,
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
     - **any operation that changes git state**, since TCW never changes
       git state and committing, pulling and pushing belong to the project's
       own prompts and hooks. The git reads TCW makes (Design 2.5) sit in the
       project-resolution and delegation code, not in the model.
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
   - The test-writing rules (`:63-99`) stay, except that "If a helper builds
     a node" (`docs/lifecycle/implementation.md:71`) says "project", since
     criterion 2's `node` pattern matches it.
3. **`docs/lifecycle/harness.md`.** One edit at `:12`: "hooks" becomes
   "Claude Code's own hooks (the harness's, not TCW's `pre` and `post`
   hooks)". In 3.0 the word "hooks" means TCW's stage hooks, which the `tcw`
   CLI runs identically under both harnesses. Read the old way, the sentence
   would wrongly call TCW's stage hooks Claude-only.
4. **The worktree section of `AGENTS.md`** (`:80-101`; `CLAUDE.md` is a
   symbolic link to `AGENTS.md`, Design 1.2). Rewritten as "Working in a git
   worktree":
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
It opens by saying that TCW never changes git state, and that this is one way
a project can keep git in step with its work items.

1. **[Decision] The commit hook is a file**,
   `docs/guide/examples/commit-item-after-move.sh`. The guide shows its full
   text in a fenced block, and criterion 5 checks that the block and the file
   are identical and runs the file. A project copies it into its own
   repository, for example as `scripts/tcw-commit-item.sh`. TCW's own
   repository can bind it where it is (TCW-76).

   ```sh
   #!/bin/sh
   # Commit this work item's files after TCW moves it to a new stage.
   # An opt-in example: TCW itself never changes git state.
   set -eu
   cd "$TCW_ITEM_PATH"
   git add -A -- .
   if git diff --cached --quiet -- .; then
       exit 0   # nothing to commit: normal in Jira mode, where a move may change no file
   fi
   git commit --quiet -m "Move $TCW_SLUG to $TCW_STAGE" -- .
   ```

   - It works from `TCW_ITEM_PATH`, not the project root. Hooks run with the
     project root as their working directory (epic decision 11), but a work
     store kept in another repository has to be committed in that repository,
     and git finds the repository from the current folder. Changing to the
     item folder first makes the script right in both layouts.
   - The commit message uses `TCW_SLUG`, which is the full slug
     `project/folder` (epic decision 11), so a commit names the project as
     well as the item.
   - It commits only the item's folder. The pathspec `-- .` limits both the
     staging and the commit, so other changes, staged or not, are left alone.
   - It succeeds with no commit when nothing in the folder changed.
2. **Pulling is prompt text**, so a failed pull never blocks a move. The
   text tells the agent to pull the project's own checkout and, when the work
   store is kept in another repository, that repository too, because the
   project's checkout does not contain it:

   ```yaml
   work:
       stages:
           request:
               prompt: &pull-first
                   - blob: >-
                         Before you start, bring this checkout up to date with
                         `git pull --ff-only`. If the folder that
                         `tcw work path <item>` prints is inside a different
                         git repository, also run
                         `git -C <that folder> pull --ff-only`. If either
                         pull fails, tell the user and carry on with what
                         you have.
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
   - A work store kept in another repository is brought up to date only by
     this instruction, when an agent starts a stage; nothing refreshes it
     between stages. The guide says so.
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
   - Creating an item is not a move (TCW-69 Design 6), so `tcw work new` and
     delegation run no hooks and a new item's folder is not committed by this
     example; commit it as part of your work. Adopting a Jira ticket is
     different: `tickets adopt` runs the request stage's `post` hooks (TCW-71
     spec Design 7.2), so the example does commit an adopted item's folder.
   - A project's own git hooks, such as a pre-commit check, can fail the commit.
     That is a failed `post` hook: exit 6, and the move stands.
5. **It can be personal.** `prompt` and `post` are overridable (TCW-72), so one
   person can put the same bindings in `tcw-config.local.yaml` without changing
   anything for the team. The guide says so and links to `personal.md`.
   **[Decision, owner 2026-10-01]** It also says what that costs: a personal
   `post` list replaces the team's `post` list for that stage, so a person
   adding this hook for themselves writes `- inherit: true` in the list to keep
   the team's hooks as well; `pre` hooks cannot be changed personally.

### 9. `docs/guide/cli.md`: output and exit codes

**[Decision]** A new guide, since the contract covers all three axes and the top
level. It covers:

- naming (`tcw noun [child-noun] verb`) and `--help`;
- stdout carries only the command's product, with TCW-73's per-command list.
  The format rules are TCW-73's (epic decision 10): one identifier per line
  (a slug, a ticket key, a qualified path or a project ID), and details only
  through `--json`, where a command offers it. `tcw work tickets list` prints
  keys; `tcw validate --remote` prints findings only, and a move it could not
  check is a finding;
- stderr carries the narration and names every file written or removed;
- commands never prompt;
- long text is read from stdin;
- the slug forms accepted (full slug, bare folder in the current project, Jira
  key in Jira mode, review decision R6), and no prefix matching;
- the exit-code table, with one row per code in `tcw/exit.py` and the meanings
  and examples from TCW-73 Design 4. Exit 5 covers both an unreachable Jira and
  reading a project that is declared but not on this machine; reading a
  project nothing declares is exit 4 (review decision R5). Delegating follows
  the five cases of Design 5.4: exit 3 for a project nothing declares, for a
  declared project not on this machine with no `jira` block, and for an
  upstream project; exit 0 with the ticket key on stdout for a declared
  project not on this machine with a `jira` block (owner answer Q1; review
  decisions R2 and R5). Exit 1 includes "no identity configured" (review
  decision R3). Exit 6 means "the
  item moved, but something after the move failed: a `post` hook, or
  recording the trace comment" (TCW-69 Design 6). The guide names the
  exception classes only to say that each one carries its code; they live in
  `tcw/errors.py` (epic decision 8), and the guide does not depend on their
  names;
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

   It is the only `upcoming/` entry with leading text: every sibling item puts
   everything under `##` headings (epic decision 15), so the introduction
   stays first. Criterion 11 checks it.
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
  (criterion 2), link resolution (criterion 3), the README structure
  (criterion 1), and the lifecycle-document phrases (criterion 9).
- `tests/test_git_example.py` (new): criterion 5.
- `tests/test_configuration_text_home.py` (replaced): criteria 6 and 7.
  Criterion 7's table test is new here; TCW-72 has no test of the table to
  extend (Design 6.3).
- `tests/test_cli_guide.py` (new): criterion 8.
- `tests/test_repo_lifecycle.py`: not this item's. TCW-70 deletes it with the
  2.x parser it guards (TCW-70 Design 15.1), and TCW-76 writes a 3.0
  replacement for the parts about TCW's own configuration (TCW-76 Design 7).
  **[Decision]** The four phrases its `test_the_moved_rules_are_reachable`
  checks (`:76-86`: the litmus question and the "Abstract spine, filesystem
  leverage" heading in `abstraction.md`, "don't pre-abstract" in
  `implementation.md`, "Agentskills specification" in `harness.md`) move into
  `tests/test_docs_describe_3_0.py`. They guard documents this item owns, so
  this item keeps them checked whatever happens to that file.
- `tests/test_documented_cli_surface.py`: it must pass (criterion 4). This
  item removes allowance entries (Design 1.5). **[Decision]** It also adds
  `tcw work advance`, `tcw work discard` and `tcw work tickets adopt` to the
  verbs that must be findable by reading (`DOCUMENTED_VERBS`,
  `tests/test_documented_cli_surface.py:261-271`), which after TCW-70 holds
  only `tcw work stage prompt` (TCW-70 spec Design 14). The new verbs are
  checked in `docs/guide/work.md` only, through their own parametrization,
  because the other document that test reads,
  `skills/work/references/commands.md`, is TCW-74's.

## Abstraction litmus test

This item adds no operation and changes none. Two parts of it touch the model:

| Part | Verdict |
| --- | --- |
| The rewritten `abstraction.md` | Restates the rule for two backends. It keeps the litmus question and adds the ownership question (Design 7.1); each of the eleven backend operations (TCW-69's eight and epic decision 1's three reads) passes both. |
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
heading (`CLAUDE.md` is a symbolic link to `AGENTS.md`, so it is not read
separately).

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
   | `work\.lifecycle`, `work\.tracker`, `auto-commit-transitions`, `publish-transitions`, `trunk-branch`, `work\.retain` | removed keys (TCW-69) |
   | `connected-projects`, `connected-project-registry` | renamed to `projects` and `project-registry` (TCW-73; owner, 2026-10-01) |
   | `TCW_NODE_ROOT`, `TCW_STATUS`, `TCW_TRANSITION`, `TCW_RESOLUTION`, `TCW_WORK_OWNER` | removed variables (TCW-69, TCW-72) |
   | `--worktree`, `--initiative`, `--epic`, `--resolution` | removed flags (TCW-73) |
   | `docs/work/(inbox\|backlog\|active\|review\|completed\|discarded)/` | status folders (TCW-70) |
   | `spec/capabilities\.yaml` | wrong location (TCW-69 Design 4.4) |
   | `\bnodes?\b` not followed by `.js` | renamed to "project" (TCW-73) |
   | `\bno longer\b`, `\bpreviously\b`, `\bsince 3\.0\b` | a document describing a difference from 2.x |
   | `\b(never\|does not\|doesn't) runs? git\b` | false: TCW reads git and `provision` clones; the rule is "never changes git state" (review decision R4) |

   **[Decision]** `builtin: true` is not in the table. Review decision R8 keeps
   it as the form `tcw config show` prints for a built-in entry, so
   `personal.md` shows it in that output while saying it is never accepted in
   a file.

   A mutation check (deliberately breaking the thing a test checks, to confirm
   the test fails) is part of the test: inserting `tcw work start` into a
   temporary copy of an owned document makes the scan fail.
3. **Links resolve.** Every relative Markdown link in an owned document points at
   an existing file, and an `#anchor` on a link into an owned document points at
   an existing heading. The one exception is
   `docs/migration-guide-2.8-to-3.0.0.md`. It is named in a single constant in
   the test, with a comment saying TCW-76 removes it when the guide exists.
4. **No phantom commands.** `tests/test_documented_cli_surface.py` passes
   against the 3.0 CLI, and no entry left in its temporary allowance
   (epic decision 6) is named by any owned document: a test fails when an
   owned document names an allowance entry. Entries still named by other
   documents are listed in the implement round with the file that names them
   (Design 1.5). `tcw work advance`, `tcw work discard` and
   `tcw work tickets adopt` are each found in `docs/guide/work.md` by that
   file's verb check (Design 11).
5. **The git example works.** In a temporary git repository with a work item
   folder `docs/work/x/`, running `docs/guide/examples/commit-item-after-move.sh`
   with `TCW_ITEM_PATH`, `TCW_SLUG` and `TCW_STAGE` set:
   - after a file in `docs/work/x/` changed, exits 0 and makes exactly one new
     commit, whose changed paths are all under `docs/work/x/`;
   - when a file outside `docs/work/x/` is also changed (one staged, one not),
     leaves both uncommitted, with the staged one still staged;
   - when nothing in `docs/work/x/` changed, exits 0 and makes no commit;
   - when the item folder is inside a second git repository nested in the first,
     and a file in the first repository is also changed, commits in the second
     repository, makes no commit in the first, and leaves the first
     repository's change uncommitted.

   The fenced `sh` block under the example heading in
   `docs/guide/configuration.md` is byte-for-byte the script file. The
   example's configuration is the **first** fenced `yaml` block under that
   heading (the push snippet that follows is a fragment and is not checked
   this way). In a temporary project whose `tcw-config.yaml` is `id: x` plus
   that block, TCW-72's `load_config` (which merges the layers, resolves
   `inherit: true`, and then runs `parse_work_config`) reports no problems,
   with `TCW_NO_PERSONAL_CONFIG=1` set. For every stage whose block has a
   `prompt`, the resolved `prompt` list holds the pull instruction followed
   by the built-in prompt entry, so a writer who drops `- inherit: true` fails
   the test. The block contains no `pre` key, and the pull instruction's text
   contains `git -C`.
6. **The configure skill is consistent.**
   - Every file in `skills/configure/references/` is linked from the router
     table in `skills/configure/SKILL.md`, and every router link resolves.
   - `tracker.md` does not exist.
   - The skill's frontmatter `description` and `when_to_use` match none of the
     criterion 2 patterns.
   - For every key path in criterion 7's list, exactly one reference has a
     `##` or `###` heading containing that key path in backticks, and that
     section's first non-blank line before any code block starts with
     `Shared:`, `Overridable:` or `Personal only:`, matching the key's label
     in `personal.md`'s table (Design 6.2). A wrong label, a missing label,
     or a key documented under two headings fails.
7. **The override table matches the code.** **[Decision]** The test holds
   the full list of key paths as one constant, and `personal.md`'s table has
   exactly one row per path, no more and no fewer:
   - `id`; `user.name`;
   - `taxonomy.path`, `taxonomy.repository`, `taxonomy.extends`, and the same
     three under `capabilities`;
   - `work.path`, `work.repository`, `work.backend`, `work.tags`,
     `work.documentation`, `work.procedures.*`,
     `work.stages.*.{enabled,status,prompt,pre,post}`,
     `work.hooks.{timeout,output-cap}`;
   - `work.jira.{site,project,issue-type,inbox-query,timeout,priorities}`,
     `work.jira.credentials.{email-env,token-env}`,
     `work.jira.fields.{project,item,effort,complexity}`;
   - `projects.{parent,children,upstream}.*.{path,repository}` and
     `projects.{parent,children,upstream}.*.jira.{site,project,inbox-status,credentials.email-env,credentials.token-env,fields.project}`.

   The rows labelled `Overridable` or `Personal only` are exactly the paths
   in `tcw.config.PERSONAL_KEYS`, and the `Personal only` row is `user.name`
   alone. Each `work.*` path in the list is accepted by the code: in a
   temporary project, a configuration that sets it to a valid value (and
   `backend: jira` for the `work.jira` and `status` paths), loaded through
   `load_config`, reports no problem naming that path. The plan writes the
   sample values. A key that no parser accepts any more therefore fails the
   test; a key added to a parser later is not caught automatically, and is
   shared by default (Risks).
8. **The exit-code table matches the code.** The table in `docs/guide/cli.md`
   has one row per exit code constant in `tcw/exit.py`, with the same numbers,
   and no other rows.
9. **The lifecycle documents.** `tests/test_docs_describe_3_0.py` asserts the
   four phrases listed in Design 11 (the litmus question and the "Abstract
   spine, filesystem leverage" heading in `abstraction.md`, "don't
   pre-abstract" in `implementation.md`, "Agentskills specification" in
   `harness.md`). `docs/lifecycle/abstraction.md` also contains the ownership
   question from Design 7.1 word for word; has a `## The backend interface`
   heading whose bullet list has exactly eleven items, whose bold leading
   names are exactly the eleven of Design 7.1 (epic decision 1); and does not
   match `\bmv\b`.
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
| 7 Lifecycle documents, `CLAUDE.md` and `AGENTS.md` worktree section | 2, 9 |
| 8 Git example | 5 |
| 9 CLI guide | 8 |
| 10 Release notes | 11 |

## Risks

- **The documents describe code that keeps moving.** If a sibling item changes a
  command or key after this item lands, the documents go stale. Mitigation:
  this item lands after the code items (Design 1.1); criteria 2, 4, 7 and 8 tie
  the documents to the code, so a removed command, a removed key, a change to
  the allowlist or to the exit codes turns the suite red. A configuration key
  added to a parser later is not caught by criterion 7, which lists keys by
  hand; it is shared by default (TCW-72 Design 4.1), so the risk is a missing
  row, not a wrong permission.
- **The temporary allowance could outlive the epic** (Design 1.5). An entry
  left in it lets a document name a removed command. Mitigation: TCW-70's
  guard test proves each entry really is removed; criterion 4 proves no owned
  document names one; and TCW-76's "validate clean" step requires the list to
  be empty before 3.0.0 is cut (epic decision 6).
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
- **The configure skill is half-updated while the epic is under way.** Code
  items land before this item, and none of them writes into
  `skills/configure/` (Design 1.2), so between TCW-72 and this item the skill
  describes 2.x keys. Mitigation: TCW-74's scans exclude the skill until this
  item removes the exclusion (Design 1.5), the epic is unreleased until
  TCW-76, and criterion 6 fails if the router and references disagree.

## Notes

- Reconciled with the epic's cross-slice decisions on 2026-10-01.
- **Decisions made in this spec, for the owner to confirm.** Each is marked
  **[Decision]** above:
  1. Ordering is now the owner's (review decision R1), not a decision here
     (Design 1.1).
  2. The file ownership table (Design 1.2). That this item owns all of
     `skills/configure/` is the owner's epic decision 3; the decisions here
     are that no earlier item writes into the skill, and that the worktree
     section is edited once, in `AGENTS.md`, since `CLAUDE.md` links to it.
  3. Under the temporary documentation allowance (epic decision 6), this item
     removes every entry its own documents no longer name and lists the rest
     with the file that still names them; `tests/test_configuration_text_home.py`
     needs no allowance (Design 1.5).
  4. `docs/work-inbox-template.md` is deleted, and writing a request for
     people outside engineering is covered in the Jira guide (Design 5.7).
  5. `skills/configure/references/tracker.md` is replaced by `jira.md`
     (Design 6.1).
  6. Each key has its own section with a `Shared:`, `Overridable:` or
     `Personal only:` line (Design 6.2).
  7. The shared/overridable table is this item's, and this item writes the
     test tying it to `PERSONAL_KEYS`, with a hand-written list of every key
     path (Design 6.3, criterion 7). The earlier text here said it would
     extend a TCW-72 table test, which TCW-72 does not write.
  8. The binding rules move from the `work` skill's `hooks.md`, which TCW-74
     deletes, into the configure reference `work.md` (Design 6.4).
  9. The rewrite of `abstraction.md`: the litmus question kept word for word,
     an ownership question added, the eleven operations named, and git
     operations kept out of the model (Design 7.1).
  10. "Beginning implementation" is deleted from `implementation.md`
      (Design 7.2).
  11. The git example's commit hook ships as a tested file,
      `docs/guide/examples/commit-item-after-move.sh`, and works from
      `TCW_ITEM_PATH` (Design 8.1).
  12. The output contract gets its own guide, `docs/guide/cli.md` (Design 9).
  13. Entry files are named by the folder name (Design 10.1).
  14. The four lifecycle-document phrases that `tests/test_repo_lifecycle.py`
      checks move into this item's own test, since TCW-70 deletes that file
      (Design 11).
- **Cross-slice findings, and how each was settled.** Nothing has been posted
  to any ticket.
  1. `spec/capabilities.yaml` in four tickets: settled by epic decision 19;
     every spec uses `<item>/capabilities.yaml`.
  2. TCW-76's mapping of migrated verdicts (`refined-outcome.md` and
     `rework.md` to `qa/round-N.md` against the design record's
     `review/round-N.md`, and the `judges` value a migrated verdict gets): not
     settled by the decisions, and not this item's. It is TCW-76's to answer;
     this item documents only 3.0 and never describes migrated items.
  3. Who owns the skill capability records: settled by epic decision 3.
     TCW-74 owns every skill's record except `skills/configure`, which is
     this item's.
  4. The `configure` skill claimed by TCW-74 and TCW-75: settled by epic
     decision 3 (TCW-75). TCW-74's spec deletes `hooks.md` and links to the
     configure references.
  5. The shared/overridable table left to nobody: settled by epic decision 3
     (this item owns the table); TCW-72 supplies only the constant in
     `tcw/config.py` and an import test (Design 6.3).
  6. Documentation tests failing mid-epic: settled by epic decision 6 (the
     temporary allowance). The `Status: Missing` exemption in
     `tests/test_documented_cli_surface.py:70-99` is deleted by TCW-74 (TCW-74
     spec Design 12, its tests table).
  7. Which folder hooks run in: settled by epic decision 11 (the project
     root). The git example still changes to `TCW_ITEM_PATH` so that a work
     store in another repository is committed there (Design 8.1).
  8. Nobody owns `tests/cli/scenarios/`: settled by epic decision 14 (TCW-73).
  9. Release-note leading text: settled by epic decision 15 (only this item's
     entry has it).
  10. Entry file naming across three items: unchanged. This item changes the
      `upcoming/README.md` files and the configure reference (Design 10.5);
      TCW-74 changes the `documentation-sync` skill's `<work-item-slug>`
      wording
      (`skills/documentation-sync/references/release-notes-and-changelogs.md:16`,
      `:21`, `:31`), which its file table already plans; TCW-76 changes TCW's
      `tcw-config.yaml` entries and the Versioning section of `CLAUDE.md` and
      `AGENTS.md`.
  11. Does adopting a Jira ticket run `post` hooks? Settled by TCW-71:
      `tickets adopt` runs the request stage's `post` hooks and no `pre`
      hooks or gates (TCW-71 Design 7.2), while `new` and
      delegation run none. The Jira guide (Design 5.2) and the git example
      (Design 8.4) say so.
  12. Terms this item depended on: settled. The connected-project key is
      `projects` and its Feature `project-registry` (TCW-73 Design 9).
      Settled by the owner on 2026-10-01: `connected-projects:` is renamed
      `projects:`, and `connected-project-registry` is renamed
      `project-registry`; `TCW_PROJECT_<ID>` stays the only way to place a project
      on this machine (TCW-72 Design 11); the request template's sections are
      TCW-74's (Design 2 there); the postmortem comment is turned on by a
      project's own `prompt` binding for postmortem (TCW-74 Design 2).
- **Owner answers applied on 2026-10-01.** Q3 (status names in the Jira
  guide's example, Design 5.2), Q8 (a personal `post` list replaces the
  team's, `pre` stays shared; Designs 5.3, 6.3 and 8.5), Q9 (filesystem qa
  verdict may be recorded by the agent; Designs 4.8 and 5.1), Q10
  (`list --tag` kept and repeatable; Design 5.1) and Q11 (`projects:` and
  `project-registry`; Design 5.4, criterion 2, cross-slice finding 12). While
  applying Q8, Design 6.3's list of overridable keys was corrected to match
  TCW-72's constant: the two credential keys are named one by one, and
  credentials inside a `projects:` entry are shared.
- **Open questions only the owner can answer.** None remain for this item.
  The five earlier questions were settled by epic decisions 3, 9, 15 and 6,
  and by the **[Decision]** to delete the inbox template (Design 5.7), which
  the owner can reverse at no cost to the rest of the design.
- **Driving this item.** It edits no code under `tcw/`, but it lands while the
  epic is changing `tcw/`. Per epic decision 7, the repository's 2.x board is
  edited by hand for this item, and its Jira ticket (TCW-75) is moved by hand
  to In Progress, In Review and Done as the item moves. A read-only view of
  the board may use a released 2.8 `tcw` installed outside the checkout.

### Review 2026-10-02

Review `scratchpad/reviews/TCW-75.md`, checked against the repository and the
sibling specs, with review decisions R1 to R20 applied.

1. **ACCEPTED.** Delegation now follows owner answer Q1 and R5: exit 0 with a
   key when the entry has a `jira` block, exit 3 otherwise, exit 3 for
   upstream (R2); the block's keys are in the `projects.md` row (Designs 5.2,
   5.4, 6, 9).
2. **ACCEPTED.** TCW-72 writes no table and no table test (TCW-72 spec
   Design 12); this item writes both, and documents the linked-worktree case
   and the `user.name` row TCW-72 asks for (Designs 1.2, 6, 6.3, criterion 7,
   Risks).
3. **ACCEPTED.** The wording is "never changes git state" everywhere (R4);
   writing rule 2.5 allows describing git reads and the `provision` clone, and
   criterion 2 now refuses "never runs git".
4. **ACCEPTED.** The pull instruction also pulls a work store kept in another
   repository with `git -C`, and the guide says that is the store's only
   refresh (Design 8.2); criterion 5 checks for `git -C`.
5. **ACCEPTED.** Criterion 5 loads the example through `load_config` and
   checks the built-in prompt survives `inherit: true`; "the YAML block" is
   now the first `yaml` block under the heading. TCW-69 spec Design 8 lists
   no `inherit` binding kind and refuses unknown binding keys, so the raw
   parse would indeed fail.
6. **ACCEPTED.** `issue-type`, `timeout`, the connected-project `jira` block,
   `TCW_CONFIG_DIR`, the `generate` variables and its stdin object (R13) are
   added; criterion 7 now lists every key path, including `id`, `taxonomy.*`,
   `capabilities.*`, `work.jira.*` and the `projects` entry, and the Risks
   claim is narrowed to what a hand-written list can catch.
7. **ACCEPTED.** A third label, `Personal only:`, is used for `user.name`
   (Design 6.2).
8. **ACCEPTED.** Note 11 is settled from TCW-71 (adopt runs `post` hooks) and
   Design 8.4 says the example commits an adopted item; note 6 now names
   TCW-74 as removing the `Missing` exemption.
9. **ACCEPTED.** `docs/lifecycle/implementation.md:71` ("builds a node") is
   reworded (Design 7.2).
10. **ACCEPTED.** `CLAUDE.md` is a symbolic link to `AGENTS.md`; the section
    is edited once and criterion text no longer checks two copies.
11. **ACCEPTED.** Criterion 6 now defines a key's section by its heading and
    requires one label per section (sections are split per key); criterion 9
    names the eleven bold names under `## The backend interface`; `mv` is
    matched as `\bmv\b`.
12. **ACCEPTED.** Both citations corrected. Because the sibling specs are
    being revised in parallel and their line numbers keep moving, every
    citation of a sibling spec now names its section (for these two, TCW-69's
    Abstraction litmus test section and its Design 6, step 7); line numbers
    are kept only for files in the repository.
13. **ACCEPTED.** "Unresolved" is reported as neither a warning nor an error
    (TCW-69 Design 9, R14, R16) in Designs 5.1 and 5.6.
14. **ACCEPTED.** **[Decision]** `advance`, `discard` and `tickets adopt` join
    `DOCUMENTED_VERBS`, checked in `docs/guide/work.md` only (Design 11,
    criterion 4).
15. **ACCEPTED.** Design 5.1 item 3 is split into separate bullets.
16. **ACCEPTED.** The README web app section lists creating items, taxonomy
    and capability entries, and adopting tickets; "Open in Jira" cites
    TCW-71's `ticket_link`, which TCW-71 now decides (Design 7.3 there).
17. **NARROWED.** No relation was missing from the ownership: TCW-74 and epic
    decision 3 already give the Feature to this item. What was true is that
    no one reconciles its description and `relatesTo` at the end, so this
    item now declares `configure-skill` changed (Capability changes). TCW-70
    spec (Capability changes, Taxonomy) still says the Feature's text is TCW-74's, which
    disagrees with TCW-74 spec (Capability changes); this spec follows epic decision 3.

Other R-decisions applied that the review did not raise: R1 (ordering, Design
1.1), R3 (no identity, Designs 6 and 9), R6 (Jira key as an item name, Design
9), R8 (`builtin: true` kept as `config show`'s output form and dropped from
criterion 2), R15 (display names, Design 5.2), R17 (a person's qa decision is
still written as a round, Designs 4.8 and 5.1), R19 (Jira inbox rejections and
what `tickets list` shows, Design 5.2), R20 (offline `validate`, Designs 5.2
and 5.6). R8 also overrides TCW-72 spec Design 3.4, which still says
`config show` prints `builtin: <packaged file>`.
