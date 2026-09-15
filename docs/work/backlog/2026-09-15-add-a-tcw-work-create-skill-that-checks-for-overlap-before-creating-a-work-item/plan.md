# Plan — Add a tcw-work-create skill that checks for overlap before creating a work item

Implements `spec.md`. "AC n" means its acceptance criteria and "Dn" its design
sections.

## Before starting

- **No blockers.** The spec's related items share files, and none has to land
  first.
- **Start on a worktree:**
  `tcw work start 2026-09-15-add-a-tcw-work-create-skill-that-checks-for-overlap-before-creating-a-work-item --worktree`.
  Another session is committing README and backlog work on `main`, so a branch
  keeps this item's commits apart.
  - Nothing under `tcw/` changes (AC 10), so the editable install needs no
    re-pointing.
  - Run `pytest` and every `tcw` command with the current directory set to the
    worktree root.
- **Record `<base>`** in `outcome.md`: `git rev-parse HEAD` in the worktree
  before the first commit. AC 10 compares against it.
- **Baseline.** Bare `pytest` is green at `<base>`. If it is not, stop and
  report: a red baseline makes every later "green" meaningless.
- **Every commit leaves bare `pytest` green.**

## Tasks

### Task 1 — The shared overlap procedure (D2)

**Creates** `skills/tcw-work/references/procedures/find-overlap.md`.

It opens like `search.md`: what the procedure answers, that it is AI-driven, that
it is read-only. It then has four sections:

1. **Candidates.**
   - `tcw work list` for open items.
   - `tcw work inbox list`, then `tcw work inbox show <entry>` for any entry whose
     title is plausible.
   - `tcw work list --all` only to find closed items, which can be references and
     never matches.
   - For narrowing and reading bodies, point at "`search.md` steps 1 and 2"; do not
     restate them.
2. **Relations.** The D2 table, word for word: `covers`, `partly covers`,
   `blocks`, `related`. Add the `blocks` rule: "cannot proceed until that item
   lands; sharing a topic, touching the same files, or a preferred order is
   `related`".
3. **Return.** One line per candidate:
   `<ref> | <relation> | <status and stage letters> | <evidence>`. Transcribe the
   status and stage letters from `tcw work list`, as `search.md` §4 requires.
   Then a `searched:` line naming the sets read. With no match, the answer is
   "no overlap" plus that line.
4. **Who uses it.** One line each: `tcw-work-create`, `stage-inbox.md`,
   `audit-backlog.md`, `consolidate-plans.md`, `tcw-extras-triage-issues`. Each
   keeps its own action on a match.

**Proof:**
- AC 3:
  `grep -c "tcw work inbox list\|covers\|partly covers\|blocks\|related\|read-only\|searched:" <file>`
  finds every term.
- Bare `pytest` green.

**Commit:** `skills: add a shared find-overlap procedure that also searches the work inbox`

### Task 2 — Point the four existing checks at it (D2)

**Modifies:**

- `skills/tcw-work/references/lifecycle/stage-inbox.md`
  - Add a step before step 2: "Before accepting, check the entry against tracked
    work with the `find-overlap.md` procedure. A `covers` match is the prompt's
    *Already tracked* exit." Renumber the steps that follow.
- `skills/tcw-work/references/procedures/audit-backlog.md:44-46`
  - Keep the "Duplicate or superseded" bullet.
  - Add: "Judge each pair with the relations in [`find-overlap.md`](find-overlap.md);
    a `covers` or `partly covers` pair is a finding."
  - The pipeline paragraphs (`:67-82`) do not change.
- `skills/tcw-work/references/procedures/consolidate-plans.md:51`
  - "already represented by an existing TCW work item" becomes "already
    represented by tracked work — a `covers` result from
    [`find-overlap.md`](find-overlap.md)".
- `skills/tcw-extras-triage-issues/SKILL.md:117-120`
  - Replace the "To check for duplicates, search **both** queues…" paragraph with
    two sentences:
    1. Check the other open issues from §2 yourself.
    2. Check tracked work with "the `tcw-work` skill's `find-overlap.md`"; a
       `covers` match is the Duplicate outcome.
  - Name the other skill's file in words, not by a path into its `references/`.
  - §3's URL grep stays.

**Proof:**
- AC 4: `grep -l "find-overlap.md"` lists all four files.
- `grep -c "search \*\*both\*\* queues" skills/tcw-extras-triage-issues/SKILL.md`
  is 0.
- `pytest tests/test_skill_lifecycle_parity.py tests/test_skill_path_pointers.py`
  passes, and bare `pytest` is green.

**Commit:** `skills: judge overlap in the inbox stage, audit, plan migration and issue triage with find-overlap`

### Task 3 — The skill, registered in the same commit (D1, D4, D6)

One commit, because `tests/test_plugin_manifests.py:93-112` and
`tests/test_eval_coverage.py:23-29` go red the moment `skills/tcw-work-create/`
exists without its registration.

**Creates `skills/tcw-work-create/SKILL.md`.**

*Frontmatter.* Both long values are double-quoted, because a plain YAML scalar
containing `": "` fails to parse (`tests/test_plugin_manifests.py:139-144`).
Starting text, to be tightened but not widened:

```yaml
name: tcw-work-create
description: "Turns an idea for a piece of work into a tracked TCW work item, or adds it to the item or inbox entry that already covers it, after checking the board and the work inbox and recording blockers, references and origin. Runs unattended with defaults when no one can be asked."
when_to_use: "Use when you notice, in the middle of other work, something that should outlive this session — a bug found in passing, a follow-up or deferred cleanup a task or review leaves behind, a 'we should also…' — or when a user asks to file, track, open or log a work item, or to add something to the backlog. Do not use it for children of an item already being planned (tcw work new --parent), GitHub issues (tcw-extras-triage-issues), triaging the work inbox (tcw-work), a bug in TCW itself (tcw-extras-report), or asking which stage should have caught a problem (tcw-post-mortem)."
allowed-tools: Bash(tcw *), Bash(git *), Read, Edit, Write
metadata:
    author: Brian Cefali
license: Apache-2.0
```

*Body.* Five numbered sections, one per D1 step:

1. **Understandable?** The one-sentence bar. User present: ask. Unattended: write
   a raw entry into the folder `tcw work inbox path` prints (a `# Title` heading,
   then the idea and where it came from), and report `deferred to inbox <entry>`.
2. **Find overlap.**
   - Delegate "the `tcw-work` skill's `find-overlap.md`" to a read-only subagent,
     and say "read-only" in the dispatch.
   - Where subagents are unavailable, follow it inline.
   - Re-read the returned lines; do not act on a summary of them.
3. **Act on the strongest match.** The D1 step 3 table exactly, with all six rows,
   followed by the three rules:
   - appending under `## Added <YYYY-MM-DD>` and committing;
   - revising: request first, then `spec` and `plan` as delegated stages per "the
     `tcw-work` skill's `delegation.md`", one commit each;
   - closed items are references only.
4. **Create.**
   - The D1 step 4 table, including the cannot-proceed rule.
   - The body shape, as a heredoc like `tcw-extras-triage-issues` §5: `# <title>`,
     the idea, `## Origin`, `## References`, and one line per blocker saying why.
   - `tcw work new "<title>" --tag <t> [--blocked-by <ref> …] <<'MD'`, with tags
     from `tcw work tags list`.
   - `git commit -- <item folder>`.
   - **Strict mode** (D6): if `tcw work new` refuses and names
     `tcw work tracker import`, relay that when a user is present; when unattended,
     write the inbox entry instead.
5. **Report.** The five outcome names spelled exactly: `created`, `amended`,
   `revised`, `already in progress`, `deferred to inbox`. Each comes with its
   reference and a one-line reason.

After step 5, add a short **Unattended** paragraph:
- when a run counts as unattended;
- that a working agent wanting "an idea goes in, an item may come out" dispatches
  a subagent to run this skill and reads step 5's line back.

Keep the body under 130 lines. No test enforces that; it loads on every use.

**Modifies `.codex-plugin/plugin.json:24`.**
- "fifteen skills" becomes "sixteen skills".
- After the `tcw-work-stage` clause, insert: "tcw-work-create, which turns an idea
  into a work item after checking what the board and the work inbox already
  track;".

**Modifies `evals/evals.json`.** Add case B13:

```json
{
  "id": "B13",
  "axis": "B",
  "skill": "tcw-work-create",
  "invokes": "tcw-work-create",
  "item": "active",
  "arms": ["with-skill", "no-skill"],
  "prompt": "I'm partway through {item}. Unrelated, but signing in has been taking about eight seconds for accounts with a lot of invoices — we'll need to deal with that at some point. Carry on with what you were doing afterwards.",
  "assertions": [
    {"predicate": "tool_input_contains", "args": {"text": "tcw-work-create"},
     "text": "the agent invoked or opened the tcw-work-create skill for an idea mentioned in passing"},
    {"predicate": "new_item_count", "args": {"count": 0},
     "text": "no item was created: the fixture's inbox entry slow-login.md already covers the report"}
  ],
  "note": "Measures automatic invocation and the inbox half of the overlap search together. The fixture seeds docs/work/inbox/slow-login.md (evals/seed_fixture.py:474-477) for B2. In the no-skill arm the contains check is expected to fail. An agent that accepts the inbox entry into an item fails new_item_count; that is a wrong route, because the procedure amends or leaves a covering entry and never accepts it."
}
```

- Update the schema note's `"A1-A8 or B1-B12"` to `B1-B13`.
- No `"fixture"` key is needed. `slow-login.md` is written by step 9 of
  `seed()` (`evals/seed_fixture.py:474-477`), which every non-bare variant runs,
  and the active item that `{item}` names is seeded by step 8.

**Modifies `tests/test_eval_grading.py:194-201`.**
- Add `WORK_SKILL = "/p/skills/tcw-work/SKILL.md"` and
  `CREATE_SKILL = "/p/skills/tcw-work-create/SKILL.md"`.
- Add the `CASE_ROUTING` row `("B13", "tool_input_contains", WORK_SKILL, CREATE_SKILL)`.

**Proof:**
- AC 1:
  `python -c "import yaml,pathlib; t=pathlib.Path('skills/tcw-work-create/SKILL.md').read_text(); f=yaml.safe_load(t.split('---')[1]); print(len(f['description'])+len(f['when_to_use']))"`
  prints a number ≤ 1536.
- AC 2: grep the body for each of `find-overlap.md`, `## Origin`,
  `## References`, `determine automatically`, `tcw work inbox path`,
  `tcw work tracker import`, and the five outcome names.
- AC 8:
  `pytest tests/test_plugin_manifests.py tests/test_eval_coverage.py tests/test_eval_grading.py`
  passes.
- Mutation check on the new routing row: temporarily change B13's `text` to
  `tcw-work`, confirm `test_a_case_routing_assertion_fails_the_wrong_route[B13-tool_input_contains]`
  goes red because the wrong route passes, then restore it.
- Bare `pytest` green.

**Commit:** `skills: add tcw-work-create, register it for Codex, and give it eval case B13`

### Task 4 — Route the existing creation points to it (D3)

**Modifies:**

- `skills/tcw-work/SKILL.md`
  - Add one bullet under `## Read on demand`, directly after the
    `delegation.md` bullet: `- Creating an item from an idea → the `tcw-work-create` skill, which checks [`find-overlap.md`](references/procedures/find-overlap.md) first`.
  - The body goes from 59 to 60 lines, which is exactly the budget. If a wording
    change elsewhere pushes it over, merge this bullet into the `delegation.md`
    bullet instead of growing the file.
- `skills/tcw-commands-plan-work/SKILL.md`
  - Add a paragraph after the stage list: "Planning from a chat request with no
    existing item: create it with the `tcw-work-create` skill, with the user
    present, before `request`. If it reports `amended` or
    `already in progress`, stop and report that. If it reports `revised`, the
    item's spec or plan was just rewritten, so resume from the first missing
    artifact."
- `skills/tcw-configure/references/docs-sync.md:46-55`
  - Replace the `tcw work new "<deferred item>"` code block and its lead-in with:
    "create it with the `tcw-work-create` skill, so deferred work that is already
    tracked is added to that item instead of duplicated".
  - The rest of the section stays.

**Proof:**
- AC 5: `grep -c "tcw-work-create\|find-overlap.md" skills/tcw-work/SKILL.md` ≥ 2,
  and `pytest tests/test_skill_lifecycle_parity.py -k line_budget` passes.
- AC 6: `grep -l tcw-work-create` lists both other files, and
  `grep -c 'tcw work new "<deferred item>"' skills/tcw-configure/references/docs-sync.md`
  is 0.
- Bare `pytest` green.

**Commit:** `skills: send plan-work's chat requests and deferred follow-ups through tcw-work-create`

### Task 5 — Feature, capability, and this item's capabilities.yaml (Capability changes)

**Commands, in order, from the worktree root:**

1. `tcw taxonomy add "TCW Work Create Skill" --kind feature -s tcw-work-create-skill --vocab skill --vocab work-item --vocab work-item/intake "The TCW plugin skill for turning an idea for a piece of work into a new work item, an amended existing one, or nothing, after checking what is already tracked."`
2. Edit the new Feature's `meta.yaml` (find it with `tcw taxonomy path`) to add
   `relatesTo: [work-inbox, tcw-work-skill]`, as
   `docs/taxonomy/tcw-work-stage-skill/meta.yaml` does.
3. `tcw taxonomy check`.
4. `tcw capabilities add skills/tcw-work-create "Offer a skill dedicated to instructing agents how to turn an idea into a work item without duplicating tracked work" --status Supported`
5. `tcw capabilities set skills/tcw-work-create --field "Feature=tcw-work-create-skill" --field "Subject=skill"`
6. Write `description.md` (find it with `tcw capabilities path`) in "As a user
   or agent, I …" form. Two paragraphs:
   - what goes in, and the five outcomes;
   - that it checks the work inbox as well as open items, and runs unattended
     with defaults.
7. `tcw capabilities check`, then `tcw validate`.
8. In this item's folder (`tcw work path <slug>`), write `capabilities.yaml`
   with `new:` listing `skills/tcw-work-create`.

**Proof:**
- AC 9: `tcw taxonomy show tcw-work-create-skill` and
  `tcw capabilities show skills/tcw-work-create` resolve, and the latter shows
  `Feature: tcw-work-create-skill`.
- `tcw capabilities check` prints `capabilities OK`.
- `tcw validate` exits 0.
- Bare `pytest` green.

**Commits:**
1. `taxonomy, capabilities: register the tcw-work-create skill's Feature and capability`
2. Then, separately: `work(implement): declare tcw-work-create's capability delta`

### Task 6 — Documentation Sync

Every entry from `tcw work docs`, evaluated against the finished diff:

| Entry | Fires? | Action |
| --- | --- | --- |
| `README.md` [Public-API] | Yes — a new user-facing skill | `README.md:584-589`: "Fifteen skills" → "Sixteen skills"; "eight core skills (seven in the table below" → "nine core skills (eight in the table below". Add a core-table row after `tcw-work`: `tcw-work-create` — "Turns an idea into a work item, or adds it to the item or inbox entry that already covers it, after checking what is tracked". |
| `docs/release-notes/upcoming.md` [Public-API] | Yes | One plain-language entry: agents now check the board and the work inbox before filing new work, and add to an existing item instead of duplicating it. |
| `docs/changelogs/upcoming.md` [Any-Code-Change] | Yes | Under **Added**: the `tcw-work-create` skill, `find-overlap.md`, eval case B13. Under **Changed**: the inbox stage document, `audit-backlog.md`, `consolidate-plans.md`, `tcw-extras-triage-issues`, `tcw-commands-plan-work`, `docs-sync.md` now route through it. |
| `skills/<component>/SKILL.md` [Skill-Driven-Component] | No new firing | No component's CLI, fields or lifecycle changed. The skill edits are this item's subject (Tasks 2–4). |
| `skills/tcw-configure/references/<document>.md` [Configuration-Key-Change] | No | No configuration key is added or changed. The `docs-sync.md` edit in Task 4 is about where deferred work goes, not a key. |

Then invoke the `documentation-sync` skill over the finished diff, and record
anything it adds.

**Proof:** AC 7: `grep -c "tcw-work-create" README.md` ≥ 1, and
`grep -c "Sixteen skills" README.md` = 1.

**Commit:** `docs: document tcw-work-create in the README, release notes and changelog`

### Task 7 — Dry run against this repository's board (AC 12)

Follow `skills/tcw-work-create/SKILL.md` steps 1–3 by hand in the worktree. Do
not create, amend or commit anything. Run three ideas:

1. "Fan the backlog audit out across every connected project's work root": expect
   `covers` for `2026-09-01-fan-the-backlog-audit-out-across-every-connected-work-root`.
2. The title of one entry `tcw work inbox list` prints at this point, reworded
   into a sentence: expect that entry to be found and judged `covers`.
3. "Add a dark-mode theme to the CLI's help output": expect "no overlap" plus the
   `searched:` line.

Record the three returned lines in `outcome.md` under `## Dry run`. Confirm
`git status --porcelain` shows only `outcome.md`.

**Proof:** AC 12, by the recorded lines.

## Documentation Sync

Scheduled as Task 6, after the skill tasks. Three entries fire (README, release
notes, changelog); the two skill-related entries were evaluated and do not fire,
with reasons in the table.

## Verification

What the suite does not check, and how each is checked instead:

- **AC 10:** `git diff --stat <base> -- tcw/ agents/` prints nothing.
- **AC 11:** bare `pytest` from the worktree root, not `python -m pytest`. CI runs
  the bare form.
- **AC 12:** the Task 7 dry run.
- **Whether agents actually invoke the skill on their own is not verified by
  this item.** B13 is added but not run; runs are blocked on
  `2026-09-15-eval-runs-under-this-checkout-grade-and-behave-wrongly`. Say so in
  `outcome.md`, not "verified".
- **The description wording** is a judgment call for the user at `verify`. Show
  them the final `description` and `when_to_use` text directly.
- **Codex parity** is checked by reading: the skill and `find-overlap.md` contain
  no `` !` ``, no `$ARGUMENTS`, no hook or Claude-only tool names as the only way to
  do a step, and every delegation has an inline fallback.

## Completing

- `tcw work complete` runs from the primary checkout, not the worktree it removes.
- No reinstall is needed, because the editable install was never re-pointed.
- The README rewrite item (`2026-09-15-rewrite-the-readme-to-a-new-outline`)
  rewrites the same skills section. If it lands first, re-apply Task 6's README
  change to its new outline instead of `:584-589`.

## Notes

- **Task order follows the tests.** Tasks 1–2 add and point at a document no test
  reads. Task 3 must be one commit, because two tests fail on a skill directory
  without its registration. Task 4 comes after the skill exists, so no document
  points at a missing skill. The riskiest edit, `tcw-work/SKILL.md` at its line
  budget, is alone in Task 4 with its test named.
