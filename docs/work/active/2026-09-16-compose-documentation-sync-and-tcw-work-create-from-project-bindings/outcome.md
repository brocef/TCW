# Outcome — Compose documentation-sync and tcw-work-create from project bindings

## What shipped

| Task | Commit | What |
| --- | --- | --- |
| spec | `6a8c8ca1` | `spec.md` |
| plan | `f20d0c9f` | `plan.md` |
| 1 | `27e00972` | `tcw-work-create` keeps its opening paragraph and step 2 (the overlap search, moved above the injection), then injects `tcw work procedure prompt create-work`, then a "Document command summary" block. `tcw/work/procedures/create-work.md` loses exactly those two pieces. `tests/test_shipped_procedures.py` gains a `CONVERTED` map and `test_a_converted_skill_reads_its_procedure`. |
| 2 | `9f4e0bf3` | `documentation-sync` keeps today's lines 7-51 (where entries come from, the lifecycle points, the Markdown fallback entry form), then injects `tcw work procedure prompt documentation-sync 2>/dev/null \|\| cat "${CLAUDE_PLUGIN_ROOT}/tcw/work/procedures/documentation-sync.md" \|\| true`, then its command summary. Frontmatter gains `allowed-tools: Bash(tcw *), Bash(cat *)`. The default loses exactly lines 7-51. Both `references/` files unchanged. |
| 3 | `c0dc8ac6` | Item `capabilities.yaml` (`changed:` both skills); one sentence appended to each skill's capability description. |
| docs | `a5a641bb` | One bullet at the end of `## Changed` and one at the end of `## Internal` in `docs/changelogs/upcoming.md`; one bullet at the end of "Replacing TCW's own procedures" in `docs/release-notes/upcoming.md`. |

Failing tests first: after moving each row, the new test failed with
"skills/…/SKILL.md does not inject tcw work procedure prompt <id>", and went
green after the conversion. Its other two assertions were mutation-checked by
hand: the pre-conversion `tcw-work-create` body still contains the default's
first prose line (so "no copy of the default" goes red on it), and removing the
command from the fenced block makes the block assertion false.

## Tests

- Targeted, after task 2: `tests/test_shipped_procedures.py`,
  `test_dynamic_skill_marker.py`, `test_plugin_manifests.py`,
  `test_skill_lifecycle_parity.py`, `test_eval_grading.py`,
  `test_documentation_sync_wiring.py`, `test_documentation_config.py`,
  `test_shipped_prompts.py`, `test_unpushed_version_script.py` — 318 passed.
- Full suite, bare, once on `a5a641bb`: `3498 passed in 925.94s (0:15:25)`
- `tcw capabilities check` → `capabilities OK`; `tcw validate` → `validate OK`.

## "Nothing configured = today's text"

Method: in the worktree (no `work.procedures` configured), take each skill after
its frontmatter, replace the single `` !`tcw work procedure prompt …` `` line with
that command's actual output, and `diff` against `git show main:<path>` after
its frontmatter. Frontmatter diffed separately.

`tcw-work-create` — frontmatter: identical. Body:

```
8a9,15
> ## 2. Find overlap
> (the five lines of step 2, verbatim)
52,58d58
< ## 2. Find overlap
< (the same five lines)
168a169,182
> ## Document command summary
> (fallback block)
```

1. **Step 2 moved** from between step 1 and step 3 to just after the opening
   paragraph, so the overlap search sits in the part a project cannot replace.
   Words unchanged; position changed. Steps keep their numbers, so a reader
   meets step 2 before "How it runs" and steps 0-1.
2. **Fallback block added**: names the command, and says the opening paragraph
   and step 2 apply whatever the command's output says. That last sentence is
   new wording and is what makes the rules win over an override.

`documentation-sync` — frontmatter: `+allowed-tools: Bash(tcw *), Bash(cat *)`,
so Claude Code will run the injected commands. Body:

```
132a133,150
> ## Document command summary
> (fallback block)
```

3. **Fallback block added**: names both commands, says the `cat` is for when the
   verb fails, that `references/` in the output means this skill's folder, and
   that the fixed part above applies whatever the output says.

No other difference in either. Outside a TCW node, and with no `tcw` on
`PATH`, the documentation-sync injection command prints the shipped default
(85 lines) and exits 0 — the same text as the in-node result.

Epic criterion 8: the grep over both converted `SKILL.md` files prints nothing
(exit 1). Epic criterion 11: both carry the "Document command summary" block,
asserted by the new test.

## What the spec, plan, epic or mechanism got wrong

- **The mechanism does not serve builtin text outside a TCW node.**
  `tcw work procedure prompt` refuses with "no tcw work node here"
  (`tcw/work/cli.py:1572-1574`), though `documentation-sync` explicitly supports
  projects that are not nodes. Worked around in the skill with a `cat` of the
  shipped file; the proper fix is the verb printing TCW's default when there is
  no node (a mechanism change, not made). Cost of the workaround: inside a node
  whose documentation-sync binding fails to resolve, stderr is suppressed and
  TCW's text is served silently instead of the project's.
- **One id cannot make two overridable references separately replaceable.**
  `skills/README.md:99-100` calls both documentation-sync references
  overridable, but child 2 shipped one id. A project can only replace the whole
  procedure, which is the only text pointing at them. Real per-reference
  overrides need a second id (for example `cut-version`), which is a mechanism
  change and naturally belongs to
  `2026-08-18-serve-version-cut-instructions-from-tcw-config-yaml-instead-of-the-agent-guide`.
  That item is still in `backlog`, so there was no configuration to reuse.
- **`skills/tcw-work/references/lifecycle/stage-verify.md:35` bypasses an
  override**: it names `documentation-sync`'s `references/cut-version.md`
  directly. Not this child's file; same owner as above.
- **Injection needs `allowed-tools`.** Neither the epic nor the brief mentions
  it. Any converted skill without a grant for its injected command likely gets
  no injection under Claude Code. `tcw-work-create` already had `Bash(tcw *)`.
  Not verified live.
- **The drift test's shape assumed rows would change, not leave.** With the
  fixed part in the skill and the rest in the default, no file holds a copy to
  compare, so the rows moved to `CONVERTED` and the id-coverage test now takes
  the union. Siblings converting other ids will edit the same map and the same
  test; expect a textual merge conflict there.
- **Plan was followed as written.** No task was reordered or redesigned.

## Not done — deferred to verify

- A live Claude Code session invoking each converted skill: both injections run
  (including the new `allowed-tools` grant), and the reader sees one document.
- A Codex session reading each skill: follows the command summary and gets the
  same text.
- documentation-sync in a project that is not a TCW node, live, through the
  `cat` fallback.
- A `work.procedures.create-work` override in a real project replaces the
  conduct while step 2 still runs.
- Eval arms touching these skills (`evals/evals.json:787`) not re-run.

## Decisions for the requester to confirm

1. documentation-sync's two references stay as unchanged files reached through
   the default, not folded in and not given an id.
2. documentation-sync's injection falls back to `cat` of TCW's shipped default
   when the verb fails, with stderr suppressed.
3. `allowed-tools: Bash(tcw *), Bash(cat *)` added to documentation-sync.
4. tcw-work-create's fixed part is the opening paragraph and the whole of step 2
   (including its permissive sentence about a subagent), moved above the
   injection. Step 0 (which checkout), step 3's precedence and step 5's report
   lines are overridable. "Closed items are never a match" stays protected
   through the fixed `find-overlap.md`.
5. Each fallback block ends with one new sentence saying the fixed part applies
   whatever the procedure says.
6. The drift test's converted rows moved to a `CONVERTED` map with a new check.
7. Capability descriptions each gained one sentence naming the procedure id and
   what cannot be replaced.

## Notes

- `spec` and `plan` gates refused on status ("not legal for an item in
  'active'"), as the requester expected; the `plan` pre-check
  `scripts/require_artifact.py spec` exited 0. The `implement` gate passed.
- No `tcw work` transition was run; `tcw-work-create/references/find-overlap.md`
  and both documentation-sync references are unchanged against `main`.
