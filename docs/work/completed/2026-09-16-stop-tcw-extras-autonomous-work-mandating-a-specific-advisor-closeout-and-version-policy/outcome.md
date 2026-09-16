# Outcome — Stop tcw-extras-autonomous-work mandating a specific advisor, closeout and version policy

## What shipped

| Task | Commit | What |
| --- | --- | --- |
| spec | `135f30c5` | `spec.md` |
| plan | `d21b4819` | `plan.md` |
| 1 | `e4d4114f` | `skills/tcw-extras-autonomous-work/SKILL.md` converted; `tcw/work/procedures/unattended-work.md` reduced to "The advisors" and "Checkpoint map"; `tests/test_shipped_procedures.py` recognizes a converted source; new `tests/test_unattended_work_skill.py` |
| 2 | `cad571b0` | `capabilities.yaml` (`changed: skills/tcw-extras-autonomous-work`); ledger description says the advisors, closeout and version policy are the replaceable default |
| 3 | `ffd9b9f6` | Documentation Sync: `README.md` skills row, `docs/changelogs/upcoming.md` (end of Changed), `docs/release-notes/upcoming.md` (end of "Replacing TCW's own procedures") |

### The skill now

- **Frontmatter**: `allowed-tools: Bash(tcw *), Bash(codex *), Bash(git merge *), Agent, SendMessage`;
  `compatibility:` says it describes TCW's shipped procedure, that a
  replacement under `work.procedures.unattended-work` may need other tools, and
  that a `tcw` with `tcw work procedure prompt` is required; `description:` says
  the advisors are Codex and an Opus subagent *by default*. `dynamic_skill`
  untouched.
- **Body, fixed**: title, opening, "Ask once"; new `## What an advisor must be`
  (independent of the session, read-only, an answer is text that was read; two
  wanted, as different as the harness allows; answers weighed, never counted,
  for one, two or three advisors); `## This project's procedure` (where the text
  comes from, that the frontmatter describes only the default, and to re-read
  per item when `--no-exec` shows a `skipped (condition)` binding), then the
  injection line; `## Hard blockers`; `## Leave the audit trail`;
  `## Document command summary`.
- **Default** (`tcw work procedure prompt unattended-work`): `## The advisors`
  and `## Checkpoint map`, byte-identical to lines 19–56 of the skill on `main`
  (checked with `diff`; the only difference is the file's final blank line).

## Nothing configured = today's text

Built the reading a Claude session gets — the new skill with its injection line
replaced by the output of `tcw work procedure prompt unattended-work` (exit 0,
this checkout configures no `work.procedures`) — and diffed it against
`git show main:skills/tcw-extras-autonomous-work/SKILL.md`. Every line of the
old file survives except two, and every other difference is an addition:

| Difference | Why |
| --- | --- |
| `description:` reworded: "consulting Codex and an Opus subagent" → "consulting read-only advisors … (by default Codex and an Opus subagent; a project can name its own)" | The advisors are now a default; the trigger words are unchanged |
| `allowed-tools:` and `compatibility:` added | Epic criterion 9. `Bash(tcw *)` is also what stops the injected command aborting the skill load |
| "ask **the two advisors**" → "ask **the advisors**" | Moved into the fixed body, where the count is not fixed |
| "or both call the item's premise wrong" → "or all of them call the item's premise wrong" | Same; identical meaning for two advisors |
| `## What an advisor must be` added | Epic criterion 9 / Goal 6. Overlaps the default's own adjudication paragraph in one idea (you are not bound; not a majority) — accepted, see Decisions |
| `## This project's procedure` added (two paragraphs) before the injected text | Says where the text comes from, the frontmatter tension, and the no-slug limitation |
| `## Document command summary` added at the end | Epic criterion 11 |

Order is unchanged: the default's two sections sit exactly where they stood.
The Codex invocation, "there is no majority of two", `SendMessage`, "Codex is
the reliable half", `adversarial-code-reviewer`, "Never cut one" and "merge the
feature branch into main **locally**. Never `git push`" all still reach the
reader, from the default.

## Tests

- Written first. Against today's skill, all four tests in
  `tests/test_unattended_work_skill.py` failed for the stated reasons: the body
  still named `Codex`, `Opus`, `SendMessage`, `adversarial-code-reviewer`; no
  "What an advisor must be" heading; no injection line; no fallback block as the
  last section. The modified drift test stayed green (source not yet converted,
  so the verbatim branch ran).
- Mutation check of the drift test's converted branch: pasted the default's
  "The brief must stand alone" paragraph back into the skill; it went red with
  "…SKILL.md still carries text from tcw/work/procedures/unattended-work.md: 'The
  brief must stand alone…'". Removed it by editing, confirmed the paragraph count
  was 0 again, suite green.
- Criterion 8 grep over the body (text after the frontmatter): prints nothing.
- Targeted: `test_unattended_work_skill.py test_shipped_procedures.py
  test_dynamic_skill_marker.py test_plugin_manifests.py
  test_skill_lifecycle_parity.py` — 209 passed; with
  `test_documented_cli_surface.py test_documentation_sync_wiring.py` — 459 passed.
- `tcw capabilities check` → `capabilities OK`; `tcw validate` → `validate OK`.
- Full suite, bare `pytest -q -p no:cacheprovider` on `ffd9b9f6`: `3502 passed in 913.66s (0:15:13)`.

## What the plan or spec got wrong

- **The epic's criterion 8 and 9 contradict each other as written.** The brief's
  grep runs over whole `SKILL.md` files; criterion 9 requires the frontmatter to
  declare the default's tools, which names `codex` and `SendMessage`. The grep
  was applied to the body, which is what criterion 8's own words say.
- **The brief's "update the `SOURCES` row"** did not fit: the row still names
  the right source. The comparison logic changed instead, recognizing any
  converted source by content, so it serves the sibling conversions too — but
  children 4–6 will each have had to change the same function, so expect a
  merge conflict there.
- **The epic spec's line numbers for the mandates** (`:22`, `:26`, `:32`, `:38`,
  `:40`, `:49`, `:54`, `:55`) are each one short, because child 1 added the
  `dynamic_skill` line after they were written.
- **The epic plan's Verification** requires each child to run its skill end to
  end before submitting; the requester deferred that to verify.

## Gaps in the mechanism (not changed)

- **Frontmatter cannot be composed.** `allowed-tools` pre-approves what TCW's
  default runs. A project whose replacement needs other tools gets permission
  prompts, which an unattended run will stall on; its only remedy today is its
  own harness permission settings. The skill body and `compatibility:` say so,
  but nothing in `tcw` can surface a replacement's tool needs.
- **A multi-item skill has no item at injection time.** `when:` never matches
  without an item, so a project's per-item bindings are skipped in the injected
  text. The skill tells the agent to check with `--no-exec` and re-read per
  item; the command itself has no "these bindings are conditional" signal on the
  normal (not `--no-exec`) path unless every binding was skipped.

## Not done — deferred to verify

- A live Claude Code session invoking the converted skill, confirming the
  injection renders and the frontmatter's `allowed-tools` lets it run.
- An unattended run against a real backlog item.
- A Codex session confirming the manual fallback block is found and followed.

## Decisions for the requester to confirm

1. Fixed in the skill: title, opening, "Ask once", hard blockers, audit trail,
   and the new advisor contract. Replaceable default: "The advisors" and
   "Checkpoint map".
2. Two advisors are wanted. Adjudication is stated count-free in the skill
   ("weighed, never counted"; one advisor is weighed against your own reading,
   three do not vote); the default keeps "there is no majority of two" as its
   own wording, so the idea reads twice when nothing is configured.
3. "the two advisors" → "the advisors"; "both call" → "all of them call".
4. No slug is passed to the injected command; per-item re-reading is
   instructed when `--no-exec` shows a conditioned binding.
5. The closeout does not defer to `work.trunk-branch` or
   `work.publish-transitions`: the first only warns and never merges, the second
   governs pushing a provisioned work store, not the code branch, and rewording
   would change the default's text.
6. Criterion 8's grep covers the body, not the frontmatter.
7. `allowed-tools` pre-approves `Bash(git merge *)` for the default's closeout,
   and deliberately not `git push`.
8. The ledger description was rewritten to say the advisors, closeout and
   version policy are a default; status unchanged.

## Notes

- The `spec` and `plan` gates refused ("not legal for an item in 'active'"),
  as the requester expected; `TCW_SLUG=<slug> python scripts/require_artifact.py
  spec` exited 0. The `implement` gate passed.
- Tests and the CLI ran from a venv inside the worktree
  (`.venv`, gitignored); the shared editable install was not touched.
- No transition was run.
