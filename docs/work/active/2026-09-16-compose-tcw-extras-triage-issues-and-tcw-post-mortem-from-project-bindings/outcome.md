# Outcome — Compose tcw-extras-triage-issues and tcw-post-mortem from project bindings

## What shipped

| Task | Commit | What |
| --- | --- | --- |
| spec | `dd3fd900` | `spec.md` |
| plan | `b44b34c7` | `plan.md` |
| 1 | `79d6209f` | `tcw-extras-triage-issues` composes `triage-issues`; `Composes` marker and its checks in `tests/test_shipped_procedures.py` |
| 2 | `719c538f` | `tcw-post-mortem` composes `post-mortem`; `agents/tcw-post-mortem.md` runs the command; agent test |
| 3 | — | Targeted suites green, no fix needed (see Tests) |
| 4 | `2edb819f` | `capabilities.yaml` with both `changed:` entries; one sentence added to each skill's capability description |
| 5 | `b987e897` | Changelog and release-note bullets |

**The forge question.** The GitHub CLI stays a declared requirement of TCW's
default `triage-issues` text, not a binding of its own. A project on another
forge replaces the procedure. Reasons are in `spec.md` → Design: the procedure
is already the unit a project replaces, `work.tracker` binds the board's own
items rather than an inbound queue, and a forge provider would be a Python
mechanism change. `compatibility:` now says the requirement belongs to the
default.

**Slugs.** `tcw-post-mortem` passes `$item` (new `arguments: [item]`) and
retries without it when it does not resolve; `tcw-extras-triage-issues` passes
none, because a sweep has no item.

## Nothing configured = today's text

For each skill: the body after frontmatter, cut at `## Document command
summary`, with the injection line replaced by `tcw work procedure prompt <id>`
output (no `work.procedures` in this checkout), compared by `diff` with
`git show main:<path>`'s body. Every difference:

**`tcw-extras-triage-issues`**

1. *Added* `## Rules no procedure changes` and the sentence "These hold whatever
   the procedure below says." — new framing for the fixed part.
2. *Moved* the "issue body is data, not instruction" blockquote from §4 into
   that section, verbatim.
3. *Moved* the `initial-request.md` paragraph from §5 into that section. Its
   first sentence "Commit the item." stays in §5. Reworded "Do not write
   `initial-request.md` here" → "… when accepting an issue", because "here" no
   longer sits inside §5.
4. *Moved* the approval paragraph and "A declined reply leaves the issue
   untouched…" from §6 into that section, verbatim.
5. *Removed* §8's restatement of the approval rule ("the same rule as §6,
   restated because you may have arrived here without reading it"). The rule now
   always precedes §8 in what the reader sees, so the reason for restating it is
   gone. This is the one sentence of the old text not present in the new.
6. *Added* `## The procedure` heading before the injected text.

**`tcw-post-mortem`**

1. *Moved* `## Producing the artifact` from the end to before the procedure,
   verbatim.
2. *Added* `## The procedure` heading before the injected text.

Nothing else differs: the §1–§8 headings, their numbering, and every other line
match. `transitions.md`'s "`tcw-extras-triage-issues` §8" still lands on
`## 8. Closing the loop when the work item finishes` in the composed text.

## Tests

- Task 1 red: `test_each_default_is_todays_text[triage-issues]` failed with
  "does not inject `tcw work procedure prompt triage-issues`". Green after the
  conversion. Mutation checks: pasting a default paragraph into the skill failed
  with "still carries its default"; replacing the injection line failed with
  "does not inject". Both edited back and confirmed identical to the saved file.
- Task 2 red: the `post-mortem` row and `test_the_post_mortem_agent_reads_the_procedure`
  both failed on the missing command. Mutation checks on the agent: removing the
  command line failed the first assertion; appending a default paragraph failed
  with "carries the default". Both edited back.
- Targeted: `test_shipped_procedures`, `test_dynamic_skill_marker`,
  `test_skill_lifecycle_parity`, `test_plugin_manifests`, `test_procedure_verb`,
  `test_eval_fixture`, `test_eval_grading` — 278 passed.
- Epic criterion 8 grep over both converted `SKILL.md` files printed nothing.
- `tcw capabilities check`: "capabilities OK". `tcw validate`: "validate OK".
- Full suite, bare `pytest -q -p no:cacheprovider` on `b987e897`: `3499 passed in 926.89s (0:15:26)`.

## What the plan or spec got wrong

- **The agent test's paragraph check would not have caught the agent as it
  was.** The old agent reworded the skill rather than copying it, so its guard
  against a returning copy is the "names the command" assertion; the paragraph
  check catches only a verbatim paste. The spec implied the check covered both.
- **Spec criterion 4 said no old sentence goes missing "except the triage §8
  approval restatement"** — true, but the "Do not write `initial-request.md`
  here" sentence was also reworded; the spec listed rewordings only in general.
- **The release note bullet child 2 wrote** — "The skills themselves do not read
  from the command yet; that comes next." — becomes partly false with this item
  and fully false once the siblings land. Left as is, because the brief limits
  shared-file edits to appending; whoever merges the last conversion should
  delete it.
- Otherwise the plan ran as written.

## Not done — deferred to verify

- A live Claude Code session invoking `tcw-extras-triage-issues` and
  `tcw-post-mortem`, confirming the injection runs, and whether `$item` becomes
  an empty string when the skill is invoked with no argument.
- A Codex session reading both skills and following the manual fallback block.
- Dispatching the `tcw-post-mortem` agent for real, confirming it runs
  `tcw work procedure prompt post-mortem <slug>` before reporting.
- Eval cases B7 and B9 were not re-run.

## Decisions for the requester to confirm

1. The forge stays a declared requirement of the default; no forge binding.
2. The approval rule and "issue body is data" are fixed in the skill body, so a
   project's procedure cannot switch them off.
3. Triage passes no slug; post-mortem passes `$item` with a no-slug retry.
4. The triage default keeps its §1–§8 numbering, so `transitions.md` needed no
   edit.
5. The capability descriptions gained one sentence each naming the override and
   what stays fixed.

## Notes

- Driven by the `tcw work stage` commands from this worktree's own venv; no
  `tcw/` Python changed. The spec and plan gates refused on status, as recorded
  in those artifacts; the implement gate passed.
- No gap found in the mechanism. One rough edge: an unresolvable slug makes
  `tcw work procedure prompt` exit 1 with no text, so a skill passing a slug
  from free-form arguments needs its own retry, as `tcw-post-mortem` now has.
- A `github` provider for `work.tracker` is the route if the forge should ever
  be abstract; not filed, since this session may not create items.
