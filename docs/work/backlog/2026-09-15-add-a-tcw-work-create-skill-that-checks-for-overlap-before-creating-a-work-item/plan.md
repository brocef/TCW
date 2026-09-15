# Plan — Add a tcw-work-create skill that checks for overlap before creating a work item

Implements `spec.md` as revised after the 2026-09-15 multi review. "AC n" means
its acceptance criteria; "Dn" means its design sections.

## Before starting

- **No blockers.** Consolidation is a non-goal, so this item no longer touches
  `audit-backlog.md`.
- **Start on a worktree:**
  `tcw work start 2026-09-15-add-a-tcw-work-create-skill-that-checks-for-overlap-before-creating-a-work-item --worktree`.
  - Another session is committing README and backlog work on `main`.
  - Nothing under `tcw/` changes, so the editable install needs no re-pointing.
  - Run `pytest` and the `tcw` commands for this item with the working directory
    set to the worktree root. The one exception is Task 5.
- **Record `<base>` in `outcome.md`:** the output of `git rev-parse HEAD` in the
  worktree, before the first commit.
- **Baseline:** bare `pytest` is green at `<base>`. If it is not, stop and
  report.
- **Every commit leaves bare `pytest` green.**

## Tasks

### Task 1 — The skill, its overlap procedure, and registration in one commit (D1, D2, D4, D6)

This must be one commit. Two tests go red as soon as `skills/tcw-work-create/`
exists without its registration:

- `tests/test_plugin_manifests.py:93-112` counts the skills and checks each is
  named;
- `tests/test_eval_coverage.py:23-29` requires every skill to have an eval case
  or an exclusion.

`find-overlap.md` lives inside the new skill, so the `tcw-work` router test
(`tests/test_skill_lifecycle_parity.py:294-304`) never sees it.

**Creates `skills/tcw-work-create/SKILL.md`.**

*Frontmatter.* Checked before planning: it parses with `yaml.safe_load`, has
every AC 1 key and string, and `description` plus `when_to_use` is 864
characters. Tighten it if needed, but do not widen the triggers.

```yaml
name: tcw-work-create
description: "Turns an idea for a piece of work into a tracked TCW work item, or adds it to the item or inbox entry that already covers it, after checking the board and the work inbox and recording blockers, references and origin."
when_to_use: "Use when you notice in passing, in the middle of other work, something that should outlive this session — a bug found while doing something else, a follow-up or deferred cleanup a task or review leaves behind, a 'we should also…' — or when a user asks to file, track, open or log a work item, or to add something to the backlog. Also when handing such an idea to a subagent. Do not use it for children of an item already being planned (tcw work new --parent), GitHub issues (tcw-extras-triage-issues), triaging the work inbox (tcw-work), a bug in TCW itself (tcw-extras-report), or asking which stage should have caught a problem (tcw-post-mortem)."
allowed-tools: Bash(tcw *), Bash(git *), Read, Edit, Write
metadata:
    author: Brian Cefali
license: Apache-2.0
```

*Body.* Section by section, in D1's order. Each section carries the D1 text for
that step, reduced to what an agent must do:

1. **`## How it runs`**: the modes table (*Interactive*, *Delegated*,
   *Unattended*), the sentence that a subagent is *Delegated* unless its brief
   says otherwise, and the five brief fields as a bulleted list.
2. **`## 0. Use the primary checkout's board`**: the
   `git rev-parse --git-dir` / `git rev-parse --git-common-dir` comparison, and
   the first `worktree` path from `git worktree list --porcelain` as the working
   directory for every `tcw` command in steps 2–4.
3. **`## 1. Is the idea understandable?`**: the three mode bullets. The
   *Unattended* bullet names `tcw work inbox path` and the entry shape.
4. **`## 2. Find overlap`**: follow [`find-overlap.md`](references/find-overlap.md),
   delegated read-only in interactive runs where dispatch is available, and
   inline otherwise.
5. **`## 3. Act on the result`**: the governing-match rule, the seven-row table
   with all four mode columns, and the three rules (Appending, Revising, Closed
   items). Revising includes the inline fallback and the
   `tcw-extras-autonomous-work` precedence sentence.
6. **`## 4. Create`**: the three-question table with all five columns, the
   blocker rule, the body shape (`# <title>`, the idea, `## Origin`,
   `## References`, one line per blocker), and this command, following
   `tcw-extras-triage-issues` §5:
   `tcw work new "<title>" --tag <t> [--blocked-by <ref> …] <<'MD' … MD`. Then the
   commit rule, `git -C <path tcw work path prints> commit -- <changed paths>`,
   and the batching sentence.
   - **Strict mode (D6):** if `tcw work new` refuses and names
     `tcw work tracker import`, relay it (*Interactive*), return it
     (*Delegated*), or write the inbox entry (*Unattended*).
7. **`## 5. Report`**: the seven outcomes, each on its own line exactly as D1
   step 5 spells them.

Keep the body under 150 lines. No test enforces that, but the body loads on
every use.

**Creates `skills/tcw-work-create/references/find-overlap.md`.** It is D2,
in four sections:

- **`## What this answers`**: one idea checked against the board. It is
  read-only: no transition, no `tcw work edit`, no file written.
- **`## Candidates`**: the three sources, and the narrowing steps.
- **`## Relations`**: the four-row table; the `blocks` rule; and, for
  `partly covers`, a note on whether the rest can be separated.
- **`## Return`**: the line format, stage letters copied from `tcw work list`,
  the `searched:` line, and "no overlap" never left as silence.

**Modifies `.codex-plugin/plugin.json:24`.**

- "fifteen skills" → "sixteen skills".
- After the `tcw-work-stage` clause, insert: "tcw-work-create, which turns an idea
  into a work item after checking what the board and the work inbox already
  track;".

**Modifies `evals/evals.json`.**

- In the schema note, change `"A1-A8 or B1-B12"` to `"A1-A8 or B1-B13"`.
- Append case B13:

```json
{
  "id": "B13",
  "axis": "B",
  "skill": "tcw-work-create",
  "invokes": "tcw-work-create",
  "item": "active",
  "arms": ["with-skill", "no-skill"],
  "prompt": "I'm partway through {item}. Unrelated, but signing in has been taking about eight seconds for accounts with a lot of invoices, and it started right after Tuesday's invoice import. We'll need to deal with that at some point. Don't work on {item} in this turn.",
  "assertions": [
    {"predicate": "tool_input_contains", "args": {"text": "tcw-work-create"},
     "text": "the agent invoked the tcw-work-create skill or opened its file for an idea mentioned in passing"},
    {"predicate": "tool_input_contains", "args": {"text": "inbox"},
     "text": "the agent read the work inbox while searching for overlap"},
    {"predicate": "files_changed_exactly", "args": {"paths": ["docs/work/inbox/slow-login.md"]},
     "text": "the new fact (Tuesday's invoice import) reached the inbox entry that already covers the report, and nothing else changed"},
    {"predicate": "new_item_count", "args": {"count": 0},
     "text": "no item was created: the inbox entry covers the report"}
  ],
  "note": "The fixture seeds docs/work/inbox/slow-login.md in step 9 of seed() (evals/seed_fixture.py:474-477), which every non-bare variant runs; its text (:105-108) already says eight seconds for accounts with many invoices, but not the import. What tells runs apart is files_changed_exactly: an agent that ignores the remark changes nothing, one that creates an item or a second entry changes other paths. tool_input_contains 'tcw-work-create' is also satisfied by a Bash command naming the skill folder, so it is a routing signal, not proof of behavior. In the no-skill arm the first assertion and files_changed_exactly are expected to fail. new_item_count reads items that run_one does not yet write (2026-09-15-eval-runs-under-this-checkout-grade-and-behave-wrongly)."
}
```

**Modifies `tests/test_eval_grading.py:190-201`.**

- Add `WORK_SKILL = "/p/skills/tcw-work/SKILL.md"` and
  `CREATE_SKILL = "/p/skills/tcw-work-create/SKILL.md"` beside the existing path
  constants.
- Add the `CASE_ROUTING` row
  `("B13", "tool_input_contains", WORK_SKILL, CREATE_SKILL)`.
  `_case_routing_assertion` requires exactly one assertion per predicate, but
  B13 has two `tool_input_contains` assertions. Change the helper to take an
  optional `text` argument that selects the assertion whose `args.text`
  matches. Pass `"tcw-work-create"` from the B13 row, and keep the existing rows
  working without it: a fourth tuple field defaulting to `None`, with the
  parametrize ids unchanged.

**Proof:**

- **AC 1:**
  `python -c "import yaml; L=open('skills/tcw-work-create/SKILL.md').read().splitlines(); e=L.index('---',1); f=yaml.safe_load('\n'.join(L[1:e])); assert f['name']=='tcw-work-create'; assert len(f['description'])+len(f['when_to_use'])<=1536; assert all(s in f['when_to_use'] for s in ['in passing','work item','tcw-extras-report','tcw-post-mortem']); print('ok')"`
  prints `ok`. It finds the frontmatter the same way
  `tests/test_skill_lifecycle_parity.py:282` does.
- **AC 2:** a loop runs one `grep -qF` per AC 2 string and prints any that are
  missing:
  `for s in Interactive Delegated Unattended "git rev-parse --git-common-dir" "git worktree list --porcelain" find-overlap.md "## Added" "## Origin" "## References" "determine automatically" "tcw work inbox path" "tcw work tracker import" created amended revised "already tracked" "already in progress" "deferred to inbox" "needs decision"; do grep -qF -- "$s" skills/tcw-work-create/SKILL.md || echo "MISSING: $s"; done`
  It must print nothing.
- **AC 3:** the same loop over
  `"tcw work inbox list" covers "partly covers" blocks related searched: read-only`
  against `find-overlap.md` prints nothing.
- **AC 7:**
  `pytest tests/test_plugin_manifests.py tests/test_eval_coverage.py tests/test_eval_grading.py`
  passes.
- **Mutation checks.** Break each one temporarily, run it, then restore:
  - Change B13's first assertion text to `tcw-work`. The B13 routing test goes
    red, because the wrong route now passes.
  - Remove the `CASE_ROUTING` row's text selector. The helper's
    exactly-one-assertion check goes red for B13.
  - Delete `find-overlap.md`. The AC 3 loop prints every string as missing.
- Bare `pytest` is green.

**Commit:** `skills: add tcw-work-create with its overlap procedure, register it for Codex, and give it eval case B13`

### Task 2 — Point existing skills at it (D3)

**Modifies:**

- **`skills/tcw-work/SKILL.md`:** one new bullet under `## Read on demand`,
  directly after the `delegation.md` bullet:
  `- Turning an idea into a work item without duplicating tracked work → the `tcw-work-create` skill`.
  The body goes from 59 to 60 lines, exactly the budget.
- **`skills/tcw-commands-plan-work/SKILL.md`:** after the stage list, add:
  "Planning from a chat request with no existing item: run the `tcw-work-create`
  skill first, in interactive mode. The chat request answers its references and
  origin questions. If it reports `already tracked`, `amended` or
  `already in progress`, stop and report that. If it reports `revised`, resume
  from the first missing artifact."
- **`skills/tcw-configure/references/docs-sync.md:46-55`:** replace the lead-in
  sentence and the `tcw work new "<deferred item>"` code block with one sentence:
  "When a task leaves code-related TODOs (…the existing examples…), file them with
  the `tcw-work-create` skill, so work already tracked gets the new information
  instead of a duplicate." The heading and the two paragraphs after the block
  stay.

**Proof:**

- **AC 4:** `grep -qF tcw-work-create skills/tcw-work/SKILL.md`, and
  `pytest tests/test_skill_lifecycle_parity.py` passes. That covers the line
  budget and the router's reference check.
- **AC 5:**
  - `grep -qF tcw-work-create skills/tcw-commands-plan-work/SKILL.md`;
  - `grep -qF tcw-work-create skills/tcw-configure/references/docs-sync.md`;
  - `grep -cF 'tcw work new "<deferred item>"' skills/tcw-configure/references/docs-sync.md`
    prints 0;
  - `pytest tests/test_skill_path_pointers.py` passes.
- Bare `pytest` is green.

**Commit:** `skills: send plan-work's chat requests and deferred follow-ups through tcw-work-create`

### Task 3 — Feature, capability, and this item's capabilities.yaml

**Commands, in order, from the worktree root:**

1. `tcw taxonomy add "TCW Work Create Skill" --kind feature -s tcw-work-create-skill --vocab skill --vocab work-item --vocab work-item/intake "The TCW plugin skill for turning an idea for a piece of work into a new work item, an amended existing one, or nothing, after checking what is already tracked."`
2. In the new Feature's `meta.yaml` (find it with `tcw taxonomy path`), add
   `relatesTo` with `work-inbox` and `tcw-work-skill`, in the list form
   `docs/taxonomy/tcw-work-stage-skill/meta.yaml` uses.
3. `tcw taxonomy check`.
4. `tcw capabilities add skills/tcw-work-create "Offer a skill dedicated to instructing agents how to turn an idea into a work item without duplicating tracked work" --status Supported`.
5. `tcw capabilities set skills/tcw-work-create --field "Feature=tcw-work-create-skill" --field "Subject=skill"`.
6. Write `description.md` (find it with `tcw capabilities path`) in the
   "As a user or agent, I …" form, covering the four points in the spec's
   Capability changes.
7. `tcw capabilities check`, then `tcw validate`.
8. Commit steps 1–7.
9. In the item's folder (`tcw work path <slug>`), write `capabilities.yaml`
   containing `new:` with `skills/tcw-work-create`, and commit it on its own.

**Proof:**

- **AC 8 (ledger half):** both `show` commands resolve, and
  `tcw capabilities show skills/tcw-work-create` includes
  `Feature: tcw-work-create-skill`.
- `tcw capabilities check` prints `capabilities OK`.
- `tcw validate` exits 0.
- Bare `pytest` is green.

**Commits:**

1. `taxonomy, capabilities: register the tcw-work-create skill's Feature and capability`
2. `work(implement): declare tcw-work-create's capability delta`

### Task 4 — Documentation Sync

Every entry from `tcw work docs`, evaluated against the finished diff:

| Entry | Fires? | Action |
| --- | --- | --- |
| `README.md` [Public-API] | Yes: a new user-facing skill | At `README.md:584-589`, "Fifteen skills" becomes "Sixteen skills", and "eight core skills (seven in the table below" becomes "nine core skills (eight in the table below". Add a core-table row after `tcw-work`: `tcw-work-create`, "Turns an idea into a work item, or adds it to the item or inbox entry that already covers it, after checking what is tracked". |
| `docs/release-notes/upcoming.md` [Public-API] | Yes | One plain-language entry: agents check the board and the work inbox before filing new work, and add to what already exists instead of duplicating it. |
| `docs/changelogs/upcoming.md` [Any-Code-Change] | Yes | **Added:** the `tcw-work-create` skill with `references/find-overlap.md`, and eval case B13. **Changed:** `tcw-commands-plan-work` and `tcw-configure`'s `docs-sync.md` route new work through it; `tests/test_eval_grading.py`'s routing helper selects an assertion by text. |
| `skills/<component>/SKILL.md` [Skill-Driven-Component] | No new firing | No component's CLI, fields or lifecycle changed. The skill edits are this item's subject (Tasks 1–2). |
| `skills/tcw-configure/references/<document>.md` [Configuration-Key-Change] | No | No configuration key changed. The `docs-sync.md` edit concerns where deferred work goes. |

Then invoke the `documentation-sync` skill over the finished diff, and record
anything it adds.

**Proof:** AC 6: `grep -qF tcw-work-create README.md`,
`grep -qF "Sixteen skills" README.md`, and
`grep -qF "sixteen skills" .codex-plugin/plugin.json`.

**Commit:** `docs: document tcw-work-create in the README, release notes and changelog`

### Task 5 — The by-hand run against this repository's board (AC 9)

Run it from the implementation worktree, following
`skills/tcw-work-create/SKILL.md` exactly, and stop each run before its first
write.

1. Record `git status --porcelain` for both the worktree and the primary
   checkout.
2. **(a)** Run step 0 and record which directory it selects. It must be
   `/Users/brian/Projects/TCW`.
3. **(b)** Idea: "Fan the backlog audit out across every connected project's work
   root." Record the step 2 lines and the governing match. Expect `covers` on
   `2026-09-01-fan-the-backlog-audit-out-across-every-connected-work-root`, and
   the outcome `already tracked`.
4. **(c)** Pick the first entry that `tcw work inbox list` prints. Restate its
   `# ` heading as a sentence, and add "it was first seen on 2026-09-15". Expect
   `covers` on that entry, and the outcome `amended`. Do not append.
5. **(d)** If `tcw work list --status active` prints an item, restate its title.
   Expect `already in progress`. If nothing is active, record that.
6. **(e)** Idea: "Add a dark-mode colour theme to `tcw serve`'s web viewer." Run
   `tcw work list --all | grep -i dark` first. If that finds something, choose
   another idea with no hit, and record both. Expect "no overlap" with a
   `searched:` line, and the outcome `created`. Do not create.
7. **(f)** Repeat (b) in *Delegated* mode, using a brief that holds only the
   idea. Expect `already tracked`, and no `needs decision`.
8. Re-run step 1's two `git status --porcelain` commands. Both outputs must be
   unchanged, apart from `outcome.md` in the worktree.

Record every step's lines under `## By-hand run` in `outcome.md`. Any result
that differs from the expectation is a defect in the skill text: fix it, then
re-run that step.

**Proof:** AC 9, from the recorded lines.

## Documentation Sync

This is Task 4, scheduled after the skill tasks. Three entries fire (README,
release notes and changelog). The two skill-related entries were evaluated and
do not fire; the reasons are in the table.

## Verification

What the suite does not check, and how each is checked instead:

- **AC 8 (the diff half):** `git diff --stat <base> -- tcw/ agents/` prints
  nothing.
- **Bare `pytest`** from the worktree root, not `python -m pytest`, because CI
  runs the bare form.
- **AC 9:** the Task 5 run.
- **AC 10 is not verified by this item.** Whether agents invoke the skill on
  their own waits on eval runs. `outcome.md` names both AC 10 checks as open and
  owned by
  `2026-09-11-refine-the-plugin-skills-and-lifecycle-prompts-against-the-eval-findings`.
  It does not call them verified.
- **The description wording** is a judgment for the user at `verify`. Show them
  the final `description` and `when_to_use` text.
- **Codex parity**, checked by reading:
  - `grep -F '!`' skills/tcw-work-create -r` prints nothing, and neither does
    `grep -F '$ARGUMENTS' skills/tcw-work-create -r`;
  - every delegation in the skill has an inline fallback;
  - no step depends on a Claude-only tool name.

## Completing

- Run `tcw work complete` from the primary checkout, not from the worktree it
  removes. No reinstall is needed.
- **README:** if `2026-09-15-rewrite-the-readme-to-a-new-outline` lands first,
  re-apply Task 4's README change to its new outline instead of
  `README.md:584-589`.
- **After completing,** use the new skill from the primary checkout to file the
  follow-up the spec names under Risks: "no CLI verb adds or amends a work inbox
  entry". That is its first real use. Record the outcome line in
  `refined-outcome.md`.

## Notes

- **Why the tasks are in this order.**
  - Task 1 must be one commit, for the two tests named there.
  - Task 2 points at a skill that already exists.
  - Keeping `find-overlap.md` inside the new skill removes the red commit the
    review found in the previous plan: `tcw-work`'s router test would have
    required a link in the same commit.
- **The one test edit beyond a new row** is the `_case_routing_assertion`
  selector in Task 1. It is needed because B13 carries two assertions with the
  same predicate. The mutation checks confirm that it still fails on the wrong
  route.
