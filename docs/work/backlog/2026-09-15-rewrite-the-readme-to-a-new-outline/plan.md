# Plan: Rewrite the README to a new outline

Implements `spec.md`. Documentation only: no file under `tcw/`, `web/`,
`skills/` or `agents/` is edited.

## Working arrangement

Start the item with `tcw work start 2026-09-15-rewrite-the-readme-to-a-new-outline --worktree`.
The README is rebuilt over several commits, and a worktree keeps a half-written
README off `main` until `complete` merges it back. No Python source changes, so
the editable-install repointing described in `AGENTS.md` is not needed. Run
`tcw` from the primary checkout and edit files in the worktree.

A throwaway checker script, kept in the session scratchpad and never committed,
tests the mechanical acceptance criteria (1, 3, 7, 8, 18). It is written in
Task 1 and re-run after every README task:

- **Headings (criterion 1):** list Markdown headings outside fenced code blocks
  and compare them with the Design § 1 list, including the Development
  subsections chosen in Task 9.
- **Contents anchors (criterion 3):** generate GitHub-style anchors from the
  heading text: lowercase; drop every character except letters, digits, spaces,
  hyphens and underscores; turn spaces into hyphens; add `-1`, `-2` … to repeats
  in document order. Check that every Contents link matches one, and that every
  `##`/`###` heading has a link.
- **CLI coverage (criterion 7):** parse the subcommand list from
  `tcw taxonomy --help`, `tcw capabilities --help` and `tcw work --help`, and
  compare it with the backticked names in each Usage › CLI subsection.
- **Skill and agent rows (criterion 8):** count table rows naming each entry of
  `ls skills/` and `ls agents/`.
- **Relative links (criterion 18):** every relative link target in `README.md`,
  `docs/guide/jira.md` and `docs/guide/work.md` exists.

## Tasks

### Task 1 — Format `docs/guide/work.md` on its own, and write the checker

- **Modifies:** `docs/guide/work.md` (formatting only).
- Run `pnpm prettier --write docs/guide/work.md`. The file fails the formatting
  check today (spec criterion 19). Formatting it in a commit of its own keeps
  Task 3's diff to the content change.
- Write the checker script in the scratchpad.
- **Proves it:** `git diff --stat` shows only `docs/guide/work.md`;
  `git diff -w` shows whitespace and wrapping only;
  `pnpm prettier --check docs/guide/work.md` passes.
- Commit: `docs(guide): format work.md with prettier`.

### Task 2 — Write `docs/guide/jira.md`

- **Creates:** `docs/guide/jira.md`.
- Structure, in this order: what the integration does and what it never does
  (a project with no `tracker` block is unchanged, and `tcw validate` never
  contacts Jira); configuration (the full `work.tracker` block with every key,
  including `statuses`, `comments`, `link`, `strict`, `timeout-seconds`);
  inheriting settings from parent nodes; how problems name the file to fix, and
  fail-closed parsing; claimable versus exclusive, with the two `tracker show`
  output examples; taking a ticket (`import`, the four-step claim, `--part`,
  running it again); linking and unlinking; seeing which ticket an item
  answers; tickets following their items (`statuses`, pending and conflicting,
  `tracker sync`); comments; strict mode; limits.
- Sources: `README.md:359-561` (current), plus the parts of
  `docs/guide/work.md:605-823` that `README.md` lacks.
- **Check each claim carried over from `work.md` against the code before keeping
  it:** the tracker parser help (`tcw/work/cli.py` around lines 2650-2760), the
  `tcw work tracker <verb> --help` output, `tcw/tracker/claim.py` for the claim
  steps, and `tcw/tracker/intake.py` for binding behavior. Drop the two
  sentences saying `link` claims (`work.md:615`, `work.md:771-772`). Record any
  other sentence dropped for being false in `outcome.md`.
- Check every configuration key named against `skills/tcw-configure/references/tracker.md`
  and the parser that reads `work.tracker`. A key in one and not the other is a
  finding for `outcome.md`, not something to paper over.
- **Proves it:** spec criterion 11. Search for `claim`, `transition` and
  `assign` near `link` and read each hit. Checker link test; `pnpm prettier --check docs/guide/jira.md`.
- Commit: `docs(guide): add a Jira integration guide built from the README's current tracker text`.

### Task 3 — Replace `work.md`'s tracker section with a pointer

- **Modifies:** `docs/guide/work.md`.
- Replace everything from `## Working from an external tracker` to the end of
  the file (after Task 1's formatting, the section still runs to end of file)
  with a section of the same name, at most 10 lines: a sentence on what the
  integration is, the one-line list of `tcw work tracker` verbs, and a link to
  [`jira.md`](jira.md).
- **Proves it:** spec criterion 12 (`grep -n "claim it for an item that already exists\|does the same claim" docs/guide/work.md`
  prints nothing; the section is at most 10 lines). Checker link test; prettier check.
- Commit: `docs(guide): point work.md's tracker section at the new Jira guide`.

### Task 4 — README: title, foreword, Problem Statement, Installation

- **Modifies:** `README.md`. Replaces the whole file.
- Write the complete heading skeleton from spec Design § 1, with the line
  `<!-- readme-rewrite: unwritten -->` under each heading not yet filled, then
  fill in:
    - Title and foreword: two sentences at most, then the table from
      `README.md:6-10` without "Lives in".
    - `## Contents`: left as a placeholder until Task 10.
    - `## Problem Statement`: copy `README.md:42-53` exactly.
    - `## Installation`: `### Plugin` from `README.md:202-231`; `### CLI` from
      `README.md:233-247` without the `pip install -e .` line;
      `### Cloud Environment Instructions` with the Claude Code example
      (`README.md:251-314`), a Codex cloud example written from spec Design § 2,
      then the `tcw provision` and plugin-install notes (`README.md:316-325`).
- In the Codex example: the `tcw_session_setup.sh` script body is pasted into
  the environment's setup script. `export` does not reach the agent, so the
  `PATH` repair appends to `~/.bashrc` rather than using `$CLAUDE_ENV_FILE`.
- **Proves it:** spec criterion 5: save lines 42-53 of
  `git show 0633e7b4:README.md` and the new Problem Statement body to two
  scratch files, and `diff` prints nothing. Criteria 4 and 16 by reading the
  sections.
- Commit: `docs(readme): restructure to the new outline; foreword, problem statement and installation`.

The `readme-rewrite: unwritten` markers are temporary lines on the work branch. They never reach
`main`, because Task 10 removes the last of them before the merge.

### Task 5 — README: Overview, Taxonomy, Capabilities

- **Modifies:** `README.md`.
- `## Overview`: at most 50 lines, covering what spec Design § 2 lists. Keep the
  sentence that a checkout missing some connected projects still works, with
  the missing ones dropping out rather than breaking commands (from
  `README.md:114-116`). `tcw/store/fs.py:290` cites the README for that promise.
- `## Taxonomy` and `## Capabilities`: Overview, Relationship to Taxonomy, and
  Usage › Skills and › CLI, per spec Design § 2. Take the CLI tables from
  `tcw taxonomy --help` and `tcw capabilities --help`, and check every example
  command by running it in a throwaway node
  (`python evals/seed_fixture.py --customized <scratch dir>`, or
  `tcw init --id probe` in a scratch git repository). A capability's status
  values come from `tcw capabilities set --help` and `tcw/capabilities/`.
- **Proves it:** spec criterion 6 (count the section's lines); checker CLI
  coverage for both axes; the example commands exit 0 in the scratch node.
- Commit: `docs(readme): overview, taxonomy and capabilities sections`.

### Task 6 — README: Work › Overview and Lifecycle diagram

- **Modifies:** `README.md`.
- `### Overview` and `#### Relationship to Capabilities and Taxonomy` per spec
  Design § 2. Take the capability declaration mechanism from
  `tcw work lifecycle` (the `complete` gates) and `docs/guide/work.md` § The
  completion gate.
- `### Lifecycle`: a sentence describing the flow in words, which is what PyPI
  readers see, then the Mermaid diagram, then the transition-gates table copied
  from `tcw work lifecycle`, then the pointer to `docs/guide/configuration.md`
  for bindings. Diagram shape: a `flowchart LR` with one node per status
  (`backlog`, `active`, `review`, `completed`, `discarded`, and a removed/deleted
  node for `drop`), an edge labeled with each transition, an `inbox` entry
  node feeding `backlog` labeled `inbox accept`, and the stages written as
  labels or subgraph notes on the status they run in (`request`/`spec`/`plan`
  on backlog, `implement` on active, `verify` on review, `postmortem` noted as
  out of band on review and completed).
- **Proves it:** spec criterion 9. Save the block to a scratch `.mmd` file and
  run `npx -y @mermaid-js/mermaid-cli -i <file>.mmd -o <file>.svg`. If that
  cannot run on this machine (it downloads a headless browser), say so in
  `outcome.md` and check the diagram in GitHub's Markdown preview during
  verification instead. Do not report the criterion as met without one of the two.
- Commit: `docs(readme): work overview and lifecycle diagram`.

### Task 7 — README: Jira integration

- **Modifies:** `README.md`.
- `#### Jira integration`: the opening, the lifecycle-to-tracker table (spec
  Design § 2) with each cell re-checked against `docs/guide/jira.md` from Task 2,
  a minimal `tracker` block of at most 12 lines, three worked examples, and the
  link to `docs/guide/jira.md`.
- Worked examples, each a command sequence with one line per step saying what
  happens in TCW and in Jira:
    1. `tracker list` → `tracker import ENG-482` → `request`/`spec`/`plan` →
       `start` → `submit` → `complete`, with the ticket moving through the mapped
       statuses.
    2. `new` → `tracker link <slug> ENG-482` (Jira untouched) → `start` (claims
       the ticket).
    3. `strict: true`: `new` refused with a pointer to `tracker import`, then the
       import path.
- Refusal wording in example 3 is quoted from the code (`grep` the strict-mode
  refusal message in `tcw/work/cli.py`), not paraphrased.
- **Proves it:** spec criterion 10; the checker link test.
- Commit: `docs(readme): place the Jira integration in the work lifecycle`.

### Task 8 — README: Work › Usage, Skills and Agents, TCW Local Web App

- **Modifies:** `README.md`.
- Work › Usage › Skills: `tcw-work` and `tcw-post-mortem` (skill), with a
  pointer to Skills and Agents. › CLI: all 24 `tcw work` subcommands, grouped
  per spec Design § 2, one line each, taken from `tcw work --help`.
- `## Skills and Agents`: the opening and three tables (core cross-axis skills;
  command skills; extras), plus the agents table, per spec Design § 2. Take
  descriptions from each `skills/*/SKILL.md` `description` field and each
  `agents/*.md` file, rewritten in plain language.
- `## TCW Local Web App`: the summary per spec Design § 2, linking
  `docs/guide/web-viewer.md`.
- **Proves it:** checker CLI coverage (work) and skill/agent row counts
  (criterion 8); criterion 13, including
  `git diff 0633e7b4 -- docs/guide/web-viewer.md` printing nothing.
- Commit: `docs(readme): work usage, skills and agents, and the local web app`.

### Task 9 — README: Documentation, Development, Further Reading

- **Modifies:** `README.md`.
- `## Documentation`: the 11-row table from spec Design § 2, Configuration
  first, keeping the `--help`/`check` line.
- `## Development` with these `###` subsections, in order: `Setting up`,
  `Running the tests`, `How work is tracked here`, `Measuring the skill layer`,
  `Releasing`, `Reporting problems`, `License`. Content per spec Design § 2. The
  `Setting up` subsection states that `.claude/settings.json` enables both the
  `tcw` and `skill-cefailures` plugins and that the SessionStart hook runs
  `scripts/remote_session_setup.sh`; it also warns that `--worktree`
  implementation needs the editable install repointed, linking the `AGENTS.md`
  section.
- `## Further Reading` per spec Design § 2.
- Add these seven subsection names to the checker's expected heading list.
- **Proves it:** criteria 14 and 15; checker headings and links.
- Commit: `docs(readme): documentation map, development guide and further reading`.

### Task 10 — README: Contents, and removing the placeholders

- **Modifies:** `README.md`.
- Write `## Contents` as a nested list of every `##` and `###` heading, using the
  anchors the checker generates.
- Remove any placeholder line left.
- `pnpm prettier --write README.md`.
- **Proves it:** checker, all five tests pass; criteria 2 and 17
  (`grep -n "not built" README.md` prints nothing; no dropped heading);
  `grep -rn "readme-rewrite: unwritten" README.md` prints nothing;
  `pnpm prettier --check README.md docs/guide/jira.md docs/guide/work.md` passes.
- Commit: `docs(readme): table of contents`.

### Task 11 — Reword the README documentation entry

- **Modifies:** `tcw-config.yaml` (the `README.md` entry's `description`,
  currently lines 18-20).
- New description, with the trigger and path unchanged:

    > Public-facing overview: what TCW is, installation, each axis and its skills
    > and CLI, the work lifecycle and Jira, the local web app, and contributor
    > setup; plain, high-readability. Update when the public CLI surface or
    > user-facing behavior changes.

- **Proves it:** criterion 20; `tcw validate` exits 0; `tcw work docs` prints
  the new text.
- Commit: `chore(config): describe the restructured README in its documentation entry`.

### Task 12 — Full check

- Run from the worktree root: `pytest` (criterion 19; nothing here should affect
  it, but the documentation entry lives in config the suite reads), `tcw validate`,
  the prettier check, and the checker. Record results in `outcome.md`.
- Read the rendered README top to bottom once for plain language, in line with
  the requester's instruction to avoid shorthand and slang, and for any
  sentence that restates something the code no longer does.

### Documentation Sync

Evaluated against `tcw work docs` (source `config`) at planning time:

| Entry                                           | Trigger                  | Fires? | Why                                                                                                                                                                                             |
| ----------------------------------------------- | ------------------------ | ------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `README.md`                                     | Public-API               | —      | The README is this item's deliverable (Tasks 4-10), not a follow-on update.                                                                                                                     |
| `docs/release-notes/upcoming.md`                | Public-API               | No     | No CLI surface or user-facing behavior changes. A documentation reorganization is not a behavior change.                                                                                        |
| `docs/changelogs/upcoming.md`                   | Any-Code-Change          | No     | No code changes. The `tcw-config.yaml` edit changes a description string, not runtime behavior.                                                                                                 |
| `skills/<component>/SKILL.md`                   | Skill-Driven-Component   | No     | No component's CLI, model, lifecycle or rules change. No skill links to a README heading or to `work.md`'s tracker section (searched `skills/` and `agents/` for `README` and `guide/work.md`). |
| `skills/tcw-configure/references/<document>.md` | Configuration-Key-Change | No     | No configuration key is added, removed or changes meaning.                                                                                                                                      |

**Task 13 — re-evaluate at the end of implementation.** Make one pass over the
finished diff against the table above. If Task 2 found a disagreement between
`docs/guide/jira.md` and `skills/tcw-configure/references/tracker.md` about a
key, the `Configuration-Key-Change` entry is where it gets fixed. Raise it with
the user rather than widening this item silently.

## Verification

What the checker and suite cannot establish:

1. **Rendering on GitHub.** The Mermaid diagram, the Contents anchors on
   repeated headings, and the tables are checked by opening the README on GitHub
   once the work branch is pushed. Pushing is outward-facing, so ask before
   pushing the `work/` branch. If no push is wanted, use a local Markdown preview
   that follows GitHub's rules (the checker's anchor algorithm) and say that
   GitHub itself was not checked.
2. **Accuracy of prose.** No test catches a sentence that describes behavior
   wrongly. The verifier samples at least ten factual claims across Installation,
   the three axis sections, Jira and the web app, and checks each against
   `--help` output or the code.
3. **Plain language.** The requester's standing instruction: no shorthand,
   metaphors or slang. A reading pass, not a test.
4. **The requester's judgment on structure.** The request is a restructure
   whose success is whether the requester finds the new README better. That
   decision belongs to `verify`.

## Notes

- `tcw/store/fs.py:290` says `README.md` promises a missing parent is not
  mistaken for the root. That promise lived in the dropped "Why many
  repositories" section (`README.md:114-116`), so Task 5 keeps the sentence in
  the Overview rather than editing a source comment.
- `tcw/store/fs.py:4964` says the README describes a retention backfill
  migration. The current README does not (only `README.md:543` names
  `work.retain`), so that comment is already out of date. It is not fixed here
  because this item edits no source files. File it as an inbox entry during
  implementation.
- Risk ordering: the out-of-date Jira text is the riskiest part, so the guide is
  built and checked against the code (Tasks 2-3) before any README section
  depends on it (Task 7).
- No blockers. The plugin-separation backlog item touches `skills/` paths, but
  neither item has to wait for the other (spec Risks).
