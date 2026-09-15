# Plan: Rewrite the README to a new outline

Implements `spec.md`. Documentation and configuration only: no file under
`tcw/`, `tests/`, `web/`, `skills/` or `agents/` is edited. Criterion numbers
below are the spec's acceptance criteria.

## Working arrangement

Start the item with
`tcw work start 2026-09-15-rewrite-the-readme-to-a-new-outline --worktree`.
The README is rebuilt over several commits, and a worktree keeps a half-written
README off `main` until `complete` merges it back. No Python source changes, so
the editable-install repointing described in `AGENTS.md` is not needed. Run
`tcw` from the primary checkout, and edit and run `pytest` in the worktree.

A throwaway checker script, kept in the session scratchpad and never committed,
tests the mechanical criteria. It is written in Task 1 and re-run after every
README task, and a check whose section is not written yet is reported as
pending rather than failed:

- **Headings (criterion 1):** Markdown headings outside fenced code blocks, with
  their levels, compared with the spec's Design § 1 list.
- **Contents (criterion 3):** the link targets in `## Contents`, compared with
  the anchor column of the spec's Design § 1 table, in order.
- **Overview length (criterion 6):** lines from `## Overview` up to
  `## Taxonomy`.
- **CLI coverage (criterion 7):** the names under "positional arguments" in
  `tcw taxonomy --help`, `tcw capabilities --help` and `tcw work --help`,
  compared both ways with the backticked `tcw <group> …` spans in each
  `#### CLI` subsection.
- **Skill and agent rows (criterion 8):** first-column table rows naming each
  entry of `ls skills/` and `ls agents/`.
- **Relative links (criterion 19):** every relative link target in `README.md`,
  `docs/guide/jira.md` and `docs/guide/work.md` exists.

## Tasks

### Task 1 — Format `docs/guide/work.md` on its own, and write the checker

- **Modifies:** `docs/guide/work.md` (formatting only).
- Run `pnpm prettier --write docs/guide/work.md`. The file fails the formatting
  check today (criterion 20). Formatting it in a commit of its own keeps Task 3's
  diff to the content change.
- Write the checker script in the scratchpad.
- **Proves it:** `git diff --stat` shows only `docs/guide/work.md`;
  `git diff -w` shows whitespace and wrapping only;
  `pnpm prettier --check docs/guide/work.md` passes.
- Commit: `docs(guide): format work.md with prettier`.

### Task 2 — Write `docs/guide/jira.md`

- **Creates:** `docs/guide/jira.md`.
- Headings, in order: what the integration does and never does (a project with
  no `tracker` block is unchanged; `tcw validate` never contacts Jira);
  Configuration; Inherited settings; Claimable and exclusive; Taking a ticket;
  Linking and unlinking; Seeing which ticket an item answers; Tickets following
  their items (statuses and sync); Comments; Strict mode; Limits.
- Sources, in the order of trust set by spec Design § 3:
  `skills/tcw-configure/references/tracker.md` and
  `skills/tcw-work/references/commands.md:82-269`, then `README.md:359-561`,
  then the listed true parts of `docs/guide/work.md:605-823`. Rewrite the
  agent-facing skill text for people.
- **Check every sentence against the code before keeping it:**
  `tcw work tracker <verb> --help` for each of `list`, `show`, `import`,
  `link`, `unlink`, `sync`; the tracker parser in `tcw/work/cli.py` (from line
  2619); `tcw/tracker/claim.py` for the claim steps; `tcw/tracker/intake.py` for
  bindings; `tcw/tracker/sync.py` and `tcw/tracker/progress.py` for following
  and comments; the `work.tracker` configuration parser (find it with
  `grep -rn "candidate-query" tcw --include=*.py`) for every key and default.
  Leave out the three false claims named in the spec's Problem section. Record
  in `outcome.md` any other sentence left out for being false, and any
  disagreement between a skill reference and the code. The code wins.
- **Proves it:** criterion 12. Read every sentence containing `link` (for example
  `grep -n "link" docs/guide/jira.md`), and
  `grep -n "No other command gains a network dependency\|Everything but" docs/guide/jira.md`
  prints nothing. Checker link test; `pnpm prettier --check docs/guide/jira.md`.
- Commit: `docs(guide): add a Jira integration guide checked against the tracker code`.

### Task 3 — Replace `work.md`'s tracker section with a pointer

- **Modifies:** `docs/guide/work.md`.
- Replace everything from `## Working from an external tracker` to the end of
  the file (after Task 1 the section still ends the file), and the `---` rule
  just before it, with a section of the same name of at most 10 lines: one
  sentence on what the integration is, the command list `tcw work tracker list | show | import | link | unlink | sync`
  in backticks, and a link to [`jira.md`](jira.md).
- **Proves it:** criterion 13:
  `grep -n "claim it for an item that already exists\|does the same claim" docs/guide/work.md`
  prints nothing, the section is at most 10 lines, and `grep -c "tcw work tracker" docs/guide/work.md`
  is at least 1. `pytest tests/test_documented_cli_surface.py` passes. Checker
  link test; prettier check.
- Commit: `docs(guide): point work.md's tracker section at the new Jira guide`.

### Task 4 — README: title, foreword, Problem Statement, Installation

- **Modifies:** `README.md`. Replaces the whole file.
- Write the complete heading skeleton from spec Design § 1, with the line
  `<!-- readme-rewrite: unwritten -->` under each heading not yet filled, then
  fill in:
    - Title and foreword: two sentences at most, then the table from
      `README.md:6-10` without "Lives in".
    - `## Problem Statement`: copy `README.md:42-53` exactly.
    - `## Installation`: `### Plugin` from `README.md:202-231`; `### CLI` from
      `README.md:233-247` without the `pip install -e .` line;
      `### Cloud Environment Instructions` with the Claude Code example
      (`README.md:251-314`), then a Codex cloud example: the same script body goes
      into the environment's setup script, set in the environment settings; the
      `PATH` repair appends to `~/.bashrc` instead of `$CLAUDE_ENV_FILE`, because
      `export` does not reach the agent; and the agent has no internet access by
      default, so the install belongs in the setup script. Then the
      `tcw provision` and plugin-install notes (`README.md:316-325`).
- **Proves it:** criterion 5: save lines 42-53 of `git show 0633e7b4:README.md`
  and the new Problem Statement body to two scratch files, and `diff` prints
  nothing. Criteria 4 and 17 by reading the sections. Checker headings test.
- Commit: `docs(readme): restructure to the new outline; foreword, problem statement and installation`.

The `readme-rewrite: unwritten` markers are temporary lines on the work branch.
Task 10 removes the last of them before the merge.

### Task 5 — README: Overview, Taxonomy, Capabilities

- **Modifies:** `README.md`.
- `## Overview`: the points spec Design § 2 lists, in at most 60 lines,
  including the promise that a checkout missing some connected projects still
  works (`README.md:114-116`, cited by `tcw/store/fs.py:290`). Command
  descriptions are written fresh, not copied from `tcw --help`.
- `## Taxonomy` and `## Capabilities`: Overview, Relationship to Taxonomy, and
  Usage › Skills and › CLI, per spec Design § 2. Take the CLI tables from
  `tcw taxonomy --help` and `tcw capabilities --help`. A capability's status
  values come from `tcw capabilities set --help` and `tcw/capabilities/cli.py`.
- Check every example command by running it in a throwaway node: in a scratch
  directory, `git init`, then `tcw init --id probe`, then the example commands.
- **Proves it:** checker Overview length (criterion 6) and CLI coverage
  (criterion 7) for both groups; each example command exits 0 in the scratch
  node.
- Commit: `docs(readme): overview, taxonomy and capabilities sections`.

### Task 6 — README: Work › Overview and Lifecycle

- **Modifies:** `README.md`.
- `### Overview` and `#### Relationship to Capabilities and Taxonomy` per spec
  Design § 2. The capability reconciliation gate comes from `tcw work lifecycle`
  (the `complete` gates) and `docs/guide/work.md` § The completion gate.
- `### Lifecycle`, in order:
    1. the two ladders, and a sentence describing the flow in words (what PyPI
       readers see);
    2. the Mermaid diagram: a `flowchart LR` with nodes `backlog`, `active`,
       `review`, `completed`, `discarded` and `removed`; an `inbox` node joined to
       `backlog` by an `inbox accept` edge; edges labeled `start`, `submit`,
       `rework`, `complete` (from review and from active), `discard` (from
       backlog, active and review), `drop` (backlog → removed) and
       `not retained` (completed and discarded → removed); stages shown as notes
       on the status they run in (`request`, `spec`, `plan` on backlog;
       `implement` on active; `verify` on review, noting it may also run in
       active; `postmortem` on review and completed, noted as out of band);
    3. the transitions table: one row per diagram edge except `inbox accept`,
       with each row's gates taken from the `gates:` lines of `tcw work lifecycle`
       and no `pre:` or `bind:` lines. The `drop` row says backlog only, from
       `tcw work drop --help`. The `not retained` row says it happens only
       under `work.retain`, and that `tcw work delete` finishes one a failed
       `pre` binding left pending;
    4. the pointer to `docs/guide/configuration.md` for bindings.
- **Proves it:** criterion 9. Save the block to a scratch `.mmd` file and run
  `npx -y @mermaid-js/mermaid-cli@11 -i <file>.mmd -o <file>.svg`. If that
  command cannot run on this machine, record that in `outcome.md` and leave the
  criterion open for Verification item 1. Do not report it met without one of
  the two. Criterion 10: the table's rows match the diagram's edge labels.
- Commit: `docs(readme): work overview and lifecycle diagram`.

### Task 7 — README: Jira integration

- **Modifies:** `README.md`.
- `#### Jira integration`:
    - a short opening;
    - the lifecycle-to-tracker table and the five-point strict-mode list from
      spec Design § 2, each cell re-read against `docs/guide/jira.md` from Task 2;
    - a minimal `tracker` block of at most 12 lines;
    - three worked examples;
    - the link to `docs/guide/jira.md`.
- Worked examples, each a command sequence with one line per step saying what
  happens in TCW and in Jira:
    1. `tracker list` → `tracker import ENG-482` → the request, spec and plan
       stages → `start` → `submit` → `complete`, with the ticket moving through
       the mapped statuses.
    2. `new` → `tracker link <slug> ENG-482` (Jira untouched) → `start` (claims the
       ticket).
    3. `strict: true`: `new` refused with its pointer to `tracker import`
       (message quoted from `tcw/work/cli.py:414-418`), then the import path.
- **Proves it:** criterion 11; checker link test.
- Commit: `docs(readme): place the Jira integration in the work lifecycle`.

### Task 8 — README: Work › Usage, Skills and Agents, TCW Local Web App

- **Modifies:** `README.md`.
- Work › Usage › Skills: `tcw-work` and `tcw-post-mortem` (skill), with a
  pointer to Skills and Agents. › CLI: all 24 `tcw work` subcommands, grouped
  per spec Design § 2, one line each, taken from `tcw work --help`.
- `## Skills and Agents`: the opening, three skill tables (cross-axis core
  skills; command skills; extras) and the agents table, per spec Design § 2.
  Descriptions come from each `skills/*/SKILL.md` `description` field and each
  `agents/*.md` file, rewritten in plain language. Use only names from
  `ls skills/` and `ls agents/`, because `tests/test_skill_lifecycle_parity.py`
  fails on removed names.
- `## TCW Local Web App`: the summary per spec Design § 2, linking
  `docs/guide/web-viewer.md`.
- **Proves it:** checker CLI coverage for `work` (criterion 7) and row counts
  (criterion 8); criterion 14, including
  `git diff 0633e7b4 -- docs/guide/web-viewer.md` printing nothing;
  `pytest tests/test_skill_lifecycle_parity.py` passes.
- Commit: `docs(readme): work usage, skills and agents, and the local web app`.

### Task 9 — README: Documentation, Development, Further Reading

- **Modifies:** `README.md`.
- `## Documentation`: the 11-row table from spec Design § 2, Configuration
  first, keeping the `--help`/`check` line.
- `## Development` with the seven `###` subsections in spec Design § 1 order,
  content per spec Design § 2. `Setting up` says `.claude/settings.json` enables
  the `tcw` plugin, names no other plugin, and links the worktree section of
  `AGENTS.md`.
- `## Further Reading` per spec Design § 2.
- **Proves it:** criteria 15 and 16; checker headings and links.
- Commit: `docs(readme): documentation map, development guide and further reading`.

### Task 10 — README: Contents, and removing the markers

- **Modifies:** `README.md`.
- Write `## Contents` as a nested list with exactly the 28 links in the spec's
  anchor table, in order: `##` headings at the top level, `###` headings nested
  under their parent.
- Remove any `readme-rewrite: unwritten` marker left, then run
  `pnpm prettier --write README.md`.
- **Proves it:** every checker test passes. Criteria 2 and 18 (no dropped
  heading; `grep -n "not built" README.md` prints nothing).
  `grep -n "readme-rewrite: unwritten" README.md` prints nothing.
  `pnpm prettier --check README.md docs/guide/jira.md docs/guide/work.md` passes.
- Commit: `docs(readme): table of contents`.

### Task 11 — Documentation entries

- **Modifies:** `tcw-config.yaml`, under `work.documentation`.
- Reword the `README.md` entry's `description`, currently lines 18-20, keeping
  its path and trigger:

    > Public-facing overview: what TCW is, installation, each axis and its skills
    > and CLI, the work lifecycle and Jira, the local web app, and contributor
    > setup; plain, high-readability. Update when the public CLI surface or
    > user-facing behavior changes.

- Add, directly after the `README.md` entry:

    ```yaml
    - path: docs/guide/jira.md
      trigger: Tracker-Change
      description:
          User-facing guide to the Jira integration; plain language. Update
          whenever a `tcw work tracker` command's behavior, what a lifecycle command
          does to a bound ticket, or a `work.tracker` key changes.
    ```

- **Proves it:** criterion 21: `tcw validate` exits 0, and `tcw work docs` prints
  both entries as specified.
  `pytest tests/test_documentation_config.py tests/test_body_prompt.py` passes.
- Commit: `chore(config): describe the restructured README and track the Jira guide`.

### Task 12 — Remove `skill-cefailures` from this repository

- **Modifies:** `.claude/settings.json`: delete the
  `"skill-cefailures@skill-cefailures": true` line and fix the trailing comma
  on the `tcw@tcw` line.
- **Proves it:** criterion 22:
  `python -c "import json; d=json.load(open('.claude/settings.json')); assert d['enabledPlugins']=={'tcw@tcw': True}"`
  exits 0, and
  `git grep -n skill-cefailures -- README.md AGENTS.md .claude skills scripts`
  prints nothing. `pytest tests/test_documentation_sync_wiring.py` passes.
- Commit: `chore(settings): stop enabling the skill-cefailures plugin in this repository`.

### Task 13 — Full check

- From the worktree root: `pytest`, `tcw validate`, the prettier check from
  criterion 20, and the checker. Record the results in `outcome.md`.
- Read the README top to bottom once for plain language, following the
  requester's instruction to avoid shorthand and slang, and for any sentence
  that describes something the code no longer does.

### Documentation Sync

Evaluated against `tcw work docs` (source `config`) at planning time:

| Entry                                           | Trigger                  | Fires? | Why                                                                                                                                                                                             |
| ----------------------------------------------- | ------------------------ | ------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `README.md`                                     | Public-API               | —      | The README is this item's deliverable (Tasks 4-10), not a follow-on update.                                                                                                                     |
| `docs/release-notes/upcoming.md`                | Public-API               | No     | No CLI surface or user-facing behavior changes. A documentation reorganization is not a behavior change.                                                                                        |
| `docs/changelogs/upcoming.md`                   | Any-Code-Change          | No     | No code changes. The `tcw-config.yaml` and `.claude/settings.json` edits change no runtime behavior of `tcw`.                                                                                   |
| `skills/<component>/SKILL.md`                   | Skill-Driven-Component   | No     | No component's CLI, model, lifecycle or rules change. No skill links to a README heading or to `work.md`'s tracker section (searched `skills/` and `agents/` for `README` and `guide/work.md`). |
| `skills/tcw-configure/references/<document>.md` | Configuration-Key-Change | No     | No configuration key is added, removed or changes meaning; Task 11 adds an entry under an existing key.                                                                                         |
| `docs/guide/jira.md` (added by Task 11)         | Tracker-Change           | —      | The guide is this item's deliverable (Task 2).                                                                                                                                                  |

**Task 14 — re-evaluate at the end of implementation.** Make one pass over the
finished diff against the table above. If Task 2 found a skill reference that
disagrees with the code, that is a `Skill-Driven-Component` or
`Configuration-Key-Change` fix. Raise it with the requester as a separate inbox
entry rather than widening this item.

## Verification

What the checker and suite cannot establish:

1. **Rendering on GitHub.** The Mermaid diagram, the Contents anchors and the
   tables are confirmed by opening the README on GitHub. That needs the
   `work/2026-09-15-rewrite-the-readme-to-a-new-outline` branch pushed, and
   pushing is outward-facing, so ask the requester first. If they decline, say
   plainly that GitHub rendering was not checked, and that criterion 9 then rests
   on the mermaid-cli run alone, or is unmet if that did not run either.
2. **Accuracy of prose.** No test catches a sentence that describes behavior
   wrongly. The verifier samples at least ten factual claims across Installation,
   the three axis sections, Jira and the web app, and checks each against
   `--help` output or the code.
3. **Plain language.** The requester's standing instruction: no shorthand,
   metaphors or slang. A reading pass, not a test.
4. **The requester's judgment on structure.** The request is a restructure whose
   success is whether the requester finds the new README better. That decision
   belongs to `verify`.

## Notes

- `tcw/store/fs.py:4964` says the README describes a retention backfill
  migration. The current README does not (only `README.md:543` names
  `work.retain`), so that comment is already out of date. This item edits no
  source files, so file it as an inbox entry during implementation.
- Risk ordering: the out-of-date Jira text is the riskiest part, so the guide is
  built and checked against the code (Tasks 2-3) before any README section
  depends on it (Task 7).
- No blockers. The plugin-separation and claim-exclusivity backlog items overlap
  (spec Risks), but neither has to finish before this one.
