# Outcome — Compose the five tcw-work procedure documents from project bindings

## What shipped, task by task

| Plan task | Commit | What |
| --- | --- | --- |
| 1 test machinery | `343529da` | `CONVERTED` set and `_paragraphs()` in `tests/test_shipped_procedures.py`; a converted id's source must name `tcw work procedure prompt <id>` and share no paragraph with its default |
| 2 `delegation` | `9d518000` | Converted first. Fixed: stages delegable / transitions never, the table, `verify` assessment vs approval, "Delegable means permitted, never required", "Custom agents". Default: "What makes it correct", "The shape this produces" |
| 3 `audit-backlog` | `02ada06c` | Fixed: "The approval rule". Default: everything else |
| 3 `consolidate-plans` | `e666c55d` | Fixed: "The two rules, before any step", "Deletion is limited to what git can give back". Default: intro, Scope, Process |
| 3 `decompose` | `5cbd42f9` | Fixed: the two nesting bullets (under an added lead-in line) and "Which path?". Default: rule, command, planning-time bullet, "Reach for this" |
| 3 `search` | `9567b29f` | Fixed: "It is read-only". Default: everything else |
| 4 auditor agent | `d85cc2ae` | `agents/tcw-backlog-auditor.md` runs `tcw work procedure prompt audit-backlog <slug>`; no checklist, report shape or two-line summary of its own; description no longer lists the checks; `procedure prompt` added to its allowed read verbs. New `test_the_backlog_auditor_reads_the_procedure` |
| 5 ledger | `91f1a8a7` | `capabilities.yaml`: `changed: skills/tcw-work`; one paragraph added to `docs/capabilities/skills/tcw-work/description.md`. `tcw capabilities check` → `capabilities OK` |
| 7 docs | `978123c7` | `README.md` auditor row, changelog (end of Changed, end of Internal), release notes (end of "Replacing TCW's own procedures") |
| spec fix | `df54f9a1` | Corrected decompose's line ranges (see below) |

Each converted document now opens with the same pointer paragraph: it holds
only the part a project cannot replace; run `tcw work procedure prompt <id>` and
follow what it prints; the rules on the page hold whatever it prints; if the
command fails, say so rather than working from memory.

Every conversion went red first with only its id added to `CONVERTED` (failing
on the missing command string), then green once converted. The auditor test went
red on the missing command string before the rewrite.

## Tests

- Targeted: `test_shipped_procedures`, `test_skill_lifecycle_parity`,
  `test_dynamic_skill_marker`, `test_documented_cli_surface`,
  `test_skill_path_pointers`, `test_plugin_manifests`, `test_procedure_config`,
  `test_resolve_procedure`, `test_shipped_prompts` — 525 passed.
  `test_documentation_sync_wiring` with the parity and CLI-surface modules after
  the docs commit — 397 passed.
- Mutation checks, both reverted by editing back and confirmed with an empty
  `git diff`: pasting a default paragraph back into `search.md` failed the drift
  test naming that paragraph; adding "Capability drift" to the auditor failed its
  test naming it.
- Full suite, bare `pytest -q -p no:cacheprovider` on `978123c7`: `3499 passed in 911.89s (0:15:11)`.

## Epic criteria 8 and 11

- **8:** `grep -niE '\b(codex|opus|sonnet|haiku|sendmessage|adversarial-code-reviewer)\b'`
  over the five documents and `agents/tcw-backlog-auditor.md` prints nothing
  (exit 1).
- **11:** injection never runs in a reference document, so the pointer
  paragraph naming `tcw work procedure prompt <id>` is the manual block — it is
  the only way any reader, under either harness, reaches the text.

## Nothing configured = today's text

This checkout configures no `work.procedures`. For each id, the composed reading
was built as `tcw work procedure prompt <id>` output followed by the document's
fixed part (the document minus its title and pointer paragraph), and diffed
against `git show main:skills/tcw-work/references/procedures/<id>.md`. An
order-insensitive diff (non-blank lines, sorted) was run as well, to separate
moves from changes.

| Id | Ordered diff | Order-insensitive diff |
| --- | --- | --- |
| `audit-backlog` | none | none |
| `consolidate-plans` | the two fixed sections move from before "Scope" to after "Process" | none |
| `search` | "It is read-only" moves from after the intro to the end | none |
| `decompose` | the two nesting bullets move from under the command to before "Which path?" | one added line: "What nesting a child with `--parent` does:" |
| `delegation` | the top rules and "Delegable means permitted" move after "The shape this produces" | two reworded sentences, below |

Every difference, explained:

1. **Position.** A reader gets the fixed part and the resolved text as two
   pieces, so fixed sections that sat between conduct sections now sit together.
   No sentence is lost.
2. **The pointer paragraph and the repeated title** are what a reader sees in
   addition — the document's own title, then the default's same title in the
   command output. Excluded from the composed build by construction.
3. **Decompose's lead-in line** replaces the command block the bullets used to
   hang from, which stayed in the default.
4. **`delegation.md`, criterion 8:** "Claude and Codex both have subagents" →
   "Both harnesses TCW ships to have subagents"; "Claude packaging — Codex
   defines its own in `.codex/agents/*.toml`" → "Claude Code packaging — another
   harness defines its agents in its own format". The Codex path is still in
   `docs/lifecycle/harness.md`.
5. **Dangling "above" in the consolidate-plans default.** Process step 7 says
   "the grouped deletion approval above … both git checks": in the printed
   default, those are now on the document page, not above. Kept verbatim because
   the default must be today's text; a reader has read the page first.

## What the plan or spec got wrong

- **Decompose's ranges.** The spec put the first nesting bullet (`:12-13`, the
  child's folder is inside the parent) in the default. It is the same nesting
  mechanics as `:14-16`, so it went to the fixed part; the spec was corrected in
  `df54f9a1`.
- **The plan's task 1 described the auditor test** and then said it belonged to
  task 4; it was added in task 4, as the plan's own note said.
- **The epic's plan said each conversion child "exercises its skill end to end in
  a real session".** The requester deferred that to `verify` for all conversion
  children; not done here.
- **Nothing in the mechanism was missing.** `tcw work procedure prompt
  audit-backlog <slug>` accepts a backlog item and prints the default (checked).

## Decisions for the requester to confirm

1. "Delegable means permitted, never required" and "Custom agents" are fixed, as
   statements about what TCW ships (its stage documents and its `agents/`), not
   project conduct. "What makes it correct" and "The shape this produces" are
   the project's.
2. The audit approval rule is fixed whole, including "group the asks by kind"
   and the final `git status --porcelain` check.
3. Consolidation's "start only when asked", itemized deletion approval and
   git-recoverable deletion are fixed as protection against losing files.
4. Decompose's nesting mechanics and the `--parent`/`--initiative` choice are
   fixed (they restate `epic-deltas.md`'s data model); "keep items small" is
   conduct.
5. The two criterion-8 rewordings in `delegation.md`.
6. The documents' pointers pass no slug; the auditor passes its slug.
7. No fallback copy of any default anywhere: a reader or auditor whose command
   fails reports that instead of working from memory.
8. `README.md`'s auditor row now says it checks against the project's procedure,
   "by default" listing the old checks.

## Not done — deferred to verify

- A live Claude Code session opening each document, to confirm an agent runs the
  command before acting on the fixed rules.
- A live backlog audit dispatching `tcw-backlog-auditor` with a
  `work.procedures.audit-backlog` replacement configured, to confirm the agent
  audits against the replacement.
- A Codex session reading the documents.

## Notes

- **`skills/tcw-work/SKILL.md` needs no change.** Its links at `:63` and `:66`
  still resolve, and `test_the_router_routes_to_every_reference_file` still
  passes; the documents themselves now carry the pointer. Stage documents and
  `commands.md` cite `delegation.md` for rules it still holds.
- **Merging with siblings:** children 3, 5 and 6 will also edit
  `tests/test_shipped_procedures.py`. Here `CONVERTED` is a set literal right
  under `SOURCES`, and `test_each_default_is_todays_text` gained an early branch
  for it; a sibling that chose a different shape will conflict in that function.
- Gate refusals for `spec` and `plan` are recorded in those artifacts; the
  `implement` gate passed.
