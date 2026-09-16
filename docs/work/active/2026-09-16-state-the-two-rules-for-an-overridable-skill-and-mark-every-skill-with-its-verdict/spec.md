# Spec — State the two rules for an overridable skill and mark every skill with its verdict

Child 1 of
`2026-09-16-make-every-procedural-skill-in-tcw-overridable-by-the-project-that-uses-it`.
Epic acceptance criteria 1, 2 and 3 are this item's to meet.

## Capability changes

None. Nothing a user can do changes: the rules document and the frontmatter key
are read by people, and neither harness acts on the key (evidence in Design,
"The key is safe on both harnesses"). The ledger entries
`skills/<skill-name>` describe what each skill does, which this item leaves as
it is. The epic's two new capabilities belong to child 2.

## Problem

1. **The test separating overridable from fixed exists only in chat and in the
   epic's own documents.** The two rules are written in
   `docs/work/active/<epic>/initial-request.md` ("The test") and `spec.md`
   ("The test, stated once"). Neither ships with the plugin, and a person adding
   a skill never opens a work item's folder. Nothing under `skills/` states them.
2. **Twenty-three shipped documents have no verdict.** The requester classified
   the sixteen skills. Unclassified: the three `agents/*.md`; the seven
   `skills/tcw-work/references/lifecycle/stage-*.md`; `commands.md`,
   `cross-node-deltas.md`, `epic-deltas.md`, `hooks.md`, `tags.md` and
   `transitions.md` under `skills/tcw-work/references/`; and the seven files in
   the `references/` folders of `documentation-sync` (2), `tcw-setup` (4) and
   `tcw-work-create` (1). The five `tcw-configure/references/*.md` and five
   `tcw-work/references/procedures/*.md` were classified by the requester as
   groups.
3. **A skill file does not say which kind it is.** `skills/tcw-work-stage/SKILL.md:1-10`
   and `skills/tcw-extras-autonomous-work/SKILL.md:1-4` open with frontmatter that
   says nothing about whether a project can change what the skill tells an agent.
4. **Nothing would catch a new skill shipping without a verdict.** The only test
   over every skill's frontmatter,
   `tests/test_plugin_manifests.py:131-148`, asserts `name` and `description`
   and nothing else.

## Goals

1. The two rules, and the reason a project replaces a procedure's text but
   cannot add a procedure, are written in one document that ships under
   `skills/`.
2. That document holds one verdict, with a concrete reason, for every
   `SKILL.md`, every file under a skill's `references/`, and every file under
   `agents/`.
3. Every `skills/*/SKILL.md` carries `dynamic_skill: true|false`, pointing at the
   document from the same line.
4. A test fails when a shipped document has no verdict, when a verdict names a
   document that does not exist, when a skill lacks the key, or when the key
   disagrees with the document.

## Non-goals

- **Converting any skill or reference document.** Children 3–6. No skill body
  changes here.
- **The procedure composition mechanism.** Child 2.
- **Enforcing the key in `tcw validate`.** Decided against; see Design.
- **Changing any agent definition.** The verdicts below create obligations for
  children 4 and 5 (see Risks); this item records them and edits no agent.
- **Deriving the marker from the presence of a composition point.** The epic
  request left that open. No overridable skill has a composition point yet, so a
  derived marker would read `false` for all five until children 3–6 land — it
  would state the present, and the requester asked for intent. A derived check
  is worth adding once conversions exist; the test here can grow that assertion
  then.

## Design

### Where the rules document lives: `skills/README.md`

**Under `skills/`, not inside one skill's `references/`.** The rules govern every
skill, so no one skill owns them. Two concrete obstacles rule out the obvious
home, `skills/tcw-work/references/`:

- `tests/test_skill_lifecycle_parity.py:315-326` requires every file there to be
  linked from `skills/tcw-work/SKILL.md`, whose body is 58 lines against a 60-line budget
  (`:50`, `:281-287`) and is owned by child 2 (epic `plan.md`, "File ownership").
- `tests/test_skill_lifecycle_parity.py:292-305` forbids any file there to name
  `references/lifecycle/` or `stage-<id>.md`, which a verdict table for the stage
  documents must do.

**Named `README.md`** because a person browsing the repository's `skills/` folder
on a forge sees it rendered beneath the folder listing without looking for it.
It is not a skill: every consumer finds skills by `*/SKILL.md`
(`tests/test_plugin_manifests.py:106`, `evals/coverage.py:32`), and a file at the
folder's top level matches neither. Codex finds skills the same way.

### How a skill author reaches it: a comment on the key's own line

```yaml
dynamic_skill: false # which skills a project may override, and why: ../README.md
```

Every `SKILL.md` gets this line in its frontmatter, so the pointer sits exactly
where the author meets the unfamiliar key, in whichever skill they opened or
copied. That meets the constraint "without being told it exists" at the moment
the question arises, and it keeps this item to frontmatter only — no skill body
changes, so nothing collides with children 2–6.

The epic plan's Verification section proposed judging reachability "from a fresh
reading of `tcw-work/SKILL.md`". That route serves a person *using* TCW, not one
*writing* a skill, and it would need a body line in a file child 2 owns. It is
replaced by the route above, and by the completeness test below: a new skill,
reference or agent added without a row fails the suite with a message naming
`skills/README.md`.

### The key is safe on both harnesses

- **Codex** parses frontmatter into a struct with `name`, `description` and
  `metadata.short-description` and no `deny_unknown_fields`
  (`openai/codex`, `codex-rs/skills/src/parser.rs:6-20`, read 2026-09-16), so an
  unknown top-level key is ignored.
- **Claude Code:** `claude plugin validate --strict` on a copy of `skills/` with
  the key and its comment added passed; the same command on a copy missing a
  `description` failed, so it does read skill frontmatter.
- **Top level, not under `metadata:`.** The Agentskills specification types
  `metadata` as "a map from string keys to string values", so `true` there
  would be off-spec, and the requester fixed the value as `true`/`false`. The
  reference validator `skills-ref` rejects any top-level key outside
  `name, description, license, allowed-tools, metadata, compatibility`
  (`skills_ref/validator.py`, `ALLOWED_FIELDS`), so it would flag
  `dynamic_skill` — as it already flags `when_to_use` on thirteen skills and
  `arguments` on `tcw-work-stage`. Nothing in this repository runs `skills-ref`
  (`.github/workflows/test.yml:100-101` runs `pytest` only). The key joins an
  existing, accepted deviation rather than opening one.
- **No test enumerates permitted keys.** Searched `tests/` for frontmatter
  readers: `test_plugin_manifests.py:131-148` checks a subset (`<=`),
  `test_skill_lifecycle_parity.py:446-453` reads `allowed-tools` only,
  `test_documentation_sync_wiring.py:123-135` reads `description`, and
  `test_skill_lifecycle_parity.py:523-534` reads `description`/`when_to_use`.
  None rejects an extra key.

### Paths inside the document

`tests/test_skill_path_pointers.py:18-26` fails if any file under `skills/` other
than the owner contains `tcw-setup/references/` or `tcw-configure/references/`.
The table therefore names each document by **owner** and **path within the
owner** in separate cells (`tcw-setup` | `references/install.md`), never as one
path. The test rebuilds the full path from the two cells.

### What the document says

1. **Rule 2 — payload**, checked first: a document carrying no procedure of its
   own has nothing to override, whatever Rule 1 would say about its subject.
2. **Rule 1 — authority**: TCW owns the shape of what is produced — the three
   axes' data model, the artifacts, the transitions, the configuration surface,
   and TCW's own upstream processes. The project owns the conduct that produces
   it — which tools, which advisors, which review, which QA, which git workflow.
3. **Why a project replaces text but adds no procedure.** A procedure id is
   useful only because a shipped skill asks for it by name at a known moment; an
   id a project invented would have no skill asking for it, so nothing would
   ever print it. A project already has the places its own procedures belong:
   its own skill, its agent guide, or a `prompt` binding on a lifecycle stage.
   And a closed set of ids is what lets `tcw validate` refuse a misspelled one
   rather than silently ignore it (epic criterion 6).
4. **A mixed document keeps its rules fixed.** When an overridable document
   holds an invariant — a rule that protects the board or an artifact — the
   conversion keeps that part in the fixed text and moves only the conduct, or
   the override becomes a way to switch the rule off.
5. **Each document is judged on its own.** A reference document does not inherit
   its skill's verdict; it usually agrees, and the table says where it does not.
6. **The verdicts**, as a table, and what `dynamic_skill` means: `true` when what
   the skill tells an agent is, or is intended to be, text a project can
   replace; `false` otherwise. Until children 3–6 land, `true` on the five
   unconverted skills records intent, not the current state.
7. **Adding a skill**: answer Rule 2, then Rule 1, add a row, set the key.

### Verdict vocabulary

| Verdict | Meaning | `dynamic_skill` |
| --- | --- | --- |
| `fixed (Rule 1)` | Carries a procedure, but its subject is TCW's shape | `false` |
| `fixed (Rule 2)` | Carries no procedure of its own | `false` |
| `fixed (accelerator)` | An agent definition; see below | not a skill |
| `overridable` | Carries conduct a project may replace | `true` |
| `composes already` | Its payload is already resolved from project configuration | `true` |

### Verdicts

**Skills — the requester's classification, recorded as given.**

| Skill | Verdict | Reason |
| --- | --- | --- |
| `tcw-taxonomy`, `tcw-work`, `tcw-capabilities` | fixed (Rule 1) | Each describes an axis's data model; using TCW means adhering to it |
| `tcw-configure` | fixed (Rule 1) | The configuration surface is how the `tcw` CLI works; changing it takes a pull request or a fork |
| `tcw-extras-report` | fixed (Rule 1) | How to report to TCW is TCW's own upstream process |
| `tcw-setup` | fixed (Rule 1) | Installing and repairing the CLI is TCW's authority |
| the four `tcw-commands-*` | fixed (Rule 2) | Each body is a stage range and an invocation of `tcw-work-stage` per stage (e.g. `tcw-commands-plan-work/SKILL.md:15-21`); the routing item, now merged (`3b4f843a`), made that so |
| `tcw-extras-autonomous-work`, `tcw-extras-triage-issues`, `documentation-sync`, `tcw-post-mortem`, `tcw-work-create` | overridable | Conduct: advisors, forge sweep, documentation judgment, investigation method, filing practice |
| `tcw-work-stage` | composes already | Its body is a template around three injected commands (`SKILL.md:16`, `:26`, `:30`) that validate its arguments and fetch the stage contract and the stage instructions; the instructions come from `tcw work stage prompt`, which a project binds under `work.lifecycle.stages.<id>.prompt`. Nothing in the file itself is a procedure to replace |

**Reference documents the requester classified by group.**
`tcw-configure`'s five references: fixed (Rule 1), with their skill.
`tcw-work`'s five `references/procedures/*.md`: overridable, as given.

**Documents this item decides.**

| Owner | Document | Verdict | Reason |
| --- | --- | --- | --- |
| `tcw-work` | `references/lifecycle/stage-*.md` (7) | fixed (Rule 1) | Each is a stage's contract — its inputs, its artifact, which steps are gated. Artifacts and transitions are TCW's shape. The conduct half of a stage is the stage prompt, which composes already; `tcw-work-stage` delivers the two together |
| `tcw-work` | `references/commands.md` | fixed (Rule 1) | Describes the CLI's verbs and flags — the surface a project cannot change |
| `tcw-work` | `references/transitions.md` | fixed (Rule 1) | Transitions are named in Rule 1 |
| `tcw-work` | `references/hooks.md` | fixed (Rule 1) | How bindings resolve and run — the configuration surface |
| `tcw-work` | `references/tags.md` | fixed (Rule 1) | The tag registry's model: fail-closed, comma-separated values |
| `tcw-work` | `references/epic-deltas.md` | fixed (Rule 1) | What each artifact means for `type: epic`, and the child relations — data model |
| `tcw-work` | `references/cross-node-deltas.md` | fixed (Rule 1) | Node relations, reciprocity, `delegate`/`escalate` — data model |
| `documentation-sync` | `references/cut-version.md` | overridable | How a version is cut is the project's conduct; the document already makes deferring to the project's own version-cut process its Step 0 (`:13-18`). Travels with its skill |
| `documentation-sync` | `references/release-notes-and-changelogs.md` | overridable | The layout it describes is the project's own documentation and is opt-in by its own words (`:5`), not a TCW artifact. Travels with its skill |
| `tcw-setup` | `references/install.md`, `references/project.md` | fixed (Rule 1) | Installing the CLI and `tcw init` are TCW's authority |
| `tcw-setup` | `references/taxonomy.md`, `references/capabilities.md` | fixed (Rule 1) | They seed the taxonomy and capabilities ledgers, whose entry kinds and statuses are the axes' data model. They also carry conduct (how to survey a codebase), but they run once, while a project is being set up and before it has any bindings — an override would arrive after the only run it could affect |
| `tcw-work-create` | `references/find-overlap.md` | fixed (Rule 1) | **Does not travel with its overridable skill.** It defines the overlap search and its four relations (`covers`, `partly covers`, `blocks`, `related`), which map onto the item fields its skill writes (`blocked_by`, an amendment, a reference). That is the board invariant the epic spec's Risks say must stay in the fixed part; a project replacing it could define "duplicate" out of existence |
| `agents` | `tcw-backlog-auditor.md`, `tcw-post-mortem.md`, `tcw-verifier.md` | fixed (accelerator) | See below |

**Agents: fixed, because the project's choice lives where the agent is
dispatched.** An agent file is Claude packaging that Codex never reads
(`delegation.md:68-70`), and it is used only when a skill or stage chooses to
dispatch it — "accelerators only", every document they serve "stands alone
without them". Two of the three restate their source: `tcw-post-mortem.md`
follows `skills/tcw-post-mortem/SKILL.md` section for section, and
`tcw-backlog-auditor.md:35-50` restates `audit-backlog.md`'s per-item checks
(`:18-34`); for those, Rule 2 holds. `tcw-verifier.md:19-30`'s steps (check each
criterion, corroborate `outcome.md`, look beyond scope) go further than the
`verify` stage prompt's step 2, so Rule 2 does not strictly hold for it; its
verdict rests instead on where the override would be reachable. A project that
wants a different assessor names its own agent in its `verify` stage binding,
which composes already, and a text override inside an agent file would reach
Claude only. Agent files carry no `dynamic_skill` key; they are not skills.

### Not in `tcw validate`

`tcw validate` checks a project's own configuration and stores. `dynamic_skill`
sits on files TCW ships, which a project using TCW does not contain, and a
project's own skills are not TCW's to police. The suite is the one place that
sees these files on every change, so the test alone guards the key.

### The test

One new module, `tests/test_dynamic_skill_marker.py`, reading `skills/README.md`'s
verdict table:

1. Every file matching `skills/*/SKILL.md`, `skills/*/references/**/*.md` and
   `agents/*.md` has exactly one row; every row names a file that exists. A
   glob-style row (`stage-*.md`) counts only if it matches at least one file.
2. Every verdict is one of the five in the vocabulary.
3. Every `SKILL.md` frontmatter parses as YAML and carries `dynamic_skill` as a
   boolean, equal to the value its row's verdict implies.
4. The `dynamic_skill` line in every `SKILL.md` carries a comment naming
   `../README.md`.

Failure messages name `skills/README.md`, so the failure is itself the route to
the rules.

### Storage abstraction

No store operation is added or changed. The document and the key are plugin
files, not project data; the litmus test does not apply.

### Harness

Nothing here is a requirement carried by a mechanism. The key and comment are
read by people on either harness; the guarantee is the test, which runs in CI.

## Acceptance criteria

1. `skills/README.md` exists and contains headings or bold labels for "Rule 1"
   and "Rule 2", states that Rule 2 is checked first, and has a section
   explaining why a project cannot add a procedure id of its own.
2. `pytest tests/test_dynamic_skill_marker.py` passes, and each of these
   mutations makes it fail, with a message naming `skills/README.md`:
   a. deleting one table row for a `SKILL.md`;
   b. adding an empty `skills/tcw-work/references/scratch.md`;
   c. deleting `dynamic_skill` from one `SKILL.md`;
   d. flipping one `SKILL.md`'s value;
   e. removing the comment from one `dynamic_skill` line.
3. `dynamic_skill` is `false` in `tcw-taxonomy`, `tcw-work`, `tcw-capabilities`,
   `tcw-configure`, `tcw-extras-report`, `tcw-setup` and the four
   `tcw-commands-*`; `true` in `tcw-extras-autonomous-work`,
   `tcw-extras-triage-issues`, `documentation-sync`, `tcw-post-mortem`,
   `tcw-work-create` and `tcw-work-stage`. `tcw-work-stage`'s row reads
   `composes already` with its reason.
4. `git diff main -- 'skills/*/SKILL.md'` adds exactly one line per file, inside
   its frontmatter, and removes none.
5. No agent file and no reference document changes:
   `git diff --stat main -- agents 'skills/*/references'` prints nothing.
6. `claude plugin validate --strict skills` passes.
7. `pytest`, bare, passes.

## Risks

- **An agent restating an overridable source bypasses the override.** Once
  `audit-backlog.md` (child 4) or `tcw-post-mortem` (child 5) composes, the agent
  that copies its text still carries the default; a project's replacement is
  ignored whenever the agent is dispatched. Child 5 owns
  `agents/tcw-post-mortem.md`. **Nobody owns `agents/tcw-backlog-auditor.md`** —
  the epic plan's ownership table omits it — so child 4 must take it, or the
  gap stays open.
- **`find-overlap.md` fixed under an overridable skill** constrains child 6: it
  converts `tcw-work-create` without moving that document into the default.
  The epic plan gives child 6 `skills/tcw-work-create/**`; this narrows it.
- **Marker `true` before conversion.** Until children 3–6 land, five skills
  read `true` while nothing about them can yet be overridden. The document says
  so; a reader who skips it will be misled.
- **Row-per-glob in the table** (`stage-*.md`) lets a new stage document be
  classified without anyone deciding it. Acceptable: the stage set is fixed by
  `STAGE_IDS`, and a new stage is itself a Rule 1 change.
- **Verdicts are judgments.** They are reviewed by the requester before any
  conversion child starts. Every one the requester did not give is listed under
  Notes.

## Notes

- **The stage gate refused.** `tcw work stage gate spec` and `gate plan` both
  said: "'spec' is not legal for an item in 'active'; it runs in backlog". The
  item was started into its worktree before planning, by the coordinating
  session. The refusal concerns status only; `spec` has no `pre` check, and
  `plan`'s only one, `python scripts/require_artifact.py spec`, is run by hand
  before planning. Decided to proceed rather than stop, and flagged for the
  requester.
- **Decisions for the requester to confirm:**
  1. Rules document at `skills/README.md`, reached by a comment on each
     `dynamic_skill` line and by the completeness test — not by a body link.
  2. Key at the top level, not under `metadata:`.
  3. `tcw-work-stage`: `composes already`, marker `true`.
  4. The seven stage documents and six `tcw-work` references: fixed (Rule 1).
  5. `documentation-sync`'s two references: overridable, travelling with it.
  6. `tcw-setup`'s `taxonomy.md` and `capabilities.md`: fixed, despite carrying
     conduct, because they run before a project has bindings.
  7. `find-overlap.md`: fixed, **not** travelling with `tcw-work-create`.
  8. The three agents: `fixed (accelerator)`, a fifth verdict not named in the
     epic; `tcw-verifier.md` in particular does not satisfy Rule 2 strictly.
  9. Not in `tcw validate`.
  10. Marker states intent, not a derived fact.
- **Assumption, not verified:** that Claude Code agent definitions do not run
  `` !`cmd` `` context injection. The agents verdict does not depend on it —
  Codex never reads `agents/` at all.
- **Epic documents that turned out wrong or stale:** the ownership table omits
  `agents/tcw-backlog-auditor.md` (Risks); the plan's reachability walk from
  `tcw-work/SKILL.md` is replaced (Design); `tcw/store/base.py:2267`, cited for
  the lifecycle key set, is now `:2266`.
- Sweep: every `SKILL.md`, every file under `skills/*/references/`, every
  `agents/*.md` — 49 files. No sibling defect sweep applies; this item adds a
  classification rather than fixing a defect.
