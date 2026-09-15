# Outcome: name the item's actual body artifact in the stage prompts

Nine commits, `d75c10e..c78410d`. `pytest` green at every boundary; **1759
passed** at the end (1734 before, +25 from `tests/test_body_prompt.py`).
`tcw validate` → `validate OK`.

## What shipped, task by task

| Task | Commit    | What                                                                                                                                  |
| ---- | --------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| 1    | `d75c10e` | `_BODY_ORDER` promoted out of `tcw/store/fs.py` to `tcw.store.base.BODY_ORDER`. Pure move.                                              |
| —    | `1fd7526` | **Not in the plan.** Out-of-band fix, see below.                                                                                        |
| 2    | `49b4901` | `substitute_body` + `BODY_OPEN`/`BODY_CLOSE` in `tcw/work/resolve.py`, wired into `resolve_prompts`; `tests/test_body_prompt.py` (unit). No shipped prompt carried the token yet, so output was unchanged. |
| 3    | `d6128ef` | `spec.md` and `plan.md` prompts rewritten; e2e tests; four stale test expectations updated; `prompt_fallback` re-baselined for those two stages. |
| 4    | `d68b9fc` | `postmortem.md` spine gains the intake; `prompt_fallback` re-baselined for that stage.                                                   |
| 5    | `e6a79de` | `LIFECYCLE_STEPS.inputs` for `spec`/`plan`/`postmortem`; `lifecycle_baseline` regenerated; **plus the three skill stage documents** (see below); `.gitignore`. |
| 6    | `dc73608` | Sweep rows 8–15 and two more (18–19).                                                                                                    |
| 7    | `8cfee98` | Sweep rows 16–17, the two capability descriptions.                                                                                       |
| 8    | `c78410d` | Documentation Sync: README, release notes, changelog.                                                                                    |
| 9    | —         | This document.                                                                                                                           |

## Sweep rows, by number

| #  | Location                                                    | Result                                                            |
| -- | ----------------------------------------------------------- | ------------------------------------------------------------------- |
| 1  | `tcw/work/prompts/spec.md`                                  | Fixed — `{{tcw:body}}`; `## References` conclusion scoped. `d6128ef` |
| 2  | `tcw/work/prompts/plan.md`                                  | Fixed — `{{tcw:body}}`. `d6128ef`                                   |
| 3  | `tcw/work/prompts/postmortem.md`                            | Fixed — spine names both. `d68b9fc`                                 |
| 4  | `tcw/store/base.py` `LIFECYCLE_STEPS.inputs`                | Fixed — `intake.md` added to three stages. `e6a79de`                |
| 5  | `skills/tcw-work/references/stage-spec.md`                  | Fixed. `e6a79de` (moved from Task 6, see below)                     |
| 6  | `skills/tcw-work/references/stage-plan.md`                  | Fixed. `e6a79de`                                                    |
| 7  | `skills/tcw-work/references/stage-postmortem.md`            | Fixed. `e6a79de`                                                    |
| 8  | `skills/tcw-triage-issues/SKILL.md` §5                      | Fixed — acceptance pipes the issue in as `intake.md`; an explicit "do not write `initial-request.md` here". `dc73608` |
| 9  | `skills/tcw-triage-issues/SKILL.md` §8                      | Fixed — `tcw work show`, not a fixed filename. `dc73608`            |
| 10 | `skills/tcw-work/references/transitions.md`                 | Fixed — same. `dc73608`                                             |
| 11 | `agents/tcw-post-mortem.md`                                 | Fixed. `dc73608`                                                    |
| 12 | `agents/tcw-backlog-auditor.md`                             | Fixed. `dc73608`                                                    |
| 13 | `commands/tcw-process-inbox.md`                             | Fixed. `dc73608`                                                    |
| 14 | `skills/tcw-post-mortem/SKILL.md`                           | Fixed. `dc73608`                                                    |
| 15 | `skills/tcw-work/references/audit-backlog.md`               | Fixed. `dc73608`                                                    |
| 16 | `docs/capabilities/plugin/triage-github-issues`             | Fixed. `8cfee98`                                                    |
| 17 | `docs/capabilities/work/complete-a-work-item`               | Fixed. `8cfee98`                                                    |
| 18 | `skills/tcw-work/references/cross-node-deltas.md:20`        | **Found during implementation.** The slice's epic link is written into whichever body the slice has. `dc73608` |
| 19 | `skills/tcw-work/references/cross-node-deltas.md:37-39`     | **Found during implementation**, and stale on its own terms: it said `tcw work reconcile` writes into `initial-request.md`; it has written the `rollup.md` sidecar since `_evict_legacy_rollup` (`tcw/work/recursion.py:171`). `dc73608` |

Re-classified, unchanged, as the spec set out: `skills/tcw-work/SKILL.md:30,43`
(both correct under 1.0.0 — the table maps stage→*produces*, and "no
`initial-request.md` → `request`" is the right rule), `commands.md`,
`stage-request.md`, `epic-deltas.md`, `decompose.md`, `commands/tcw-plan-work.md`,
`README.md`'s body-surface section, `consolidate-plans.md:54`,
`reconcile-an-epic-rollup` (historical), and `retitle-a-work-item` (owned by
`2026-08-19-derive-an-accepted-inbox-item-s-title-…`).

## Acceptance criteria

| #     | Result                                                                                                       |
| ----- | -------------------------------------------------------------------------------------------------------------- |
| 1–2   | Met — `tests/test_body_prompt.py`, 10 unit tests incl. the inline-placement assertion.                        |
| 3     | Met — `tests/test_documentation_prompt.py` passes **unmodified**.                                             |
| 4–6   | Met — e2e over all three body states × both stages. Re-run by hand at Task 9; output in the verification note. |
| 7     | **Reworded during implementation** — see below.                                                               |
| 8     | Met — `test_no_token_survives_into_a_resolved_prompt`, 6 cases.                                                |
| 9     | Met — every prompt ≤ 50; `spec.md` at 49, `postmortem.md` at 42. `tests/test_shipped_prompts.py` unmodified.   |
| 10    | Met — all three stages list `intake.md`; the fixture diff was 55 lines across 11 files, every one an `inputs` line. |
| 11    | Met — table above.                                                                                            |
| 12    | **Not met as claimed when this was written.** 1759 passed and `validate OK` were true, but only **two** of the three capability wording deltas had shipped — `work/run-a-lifecycle-stage` was missed. Caught at `verify` reconciling the ledger; fixed in `696da94`. |

## What the plan and spec got wrong

Four corrections, none of which changed the design.

1. **Criteria 4 and 7 asserted something the design cannot deliver.** They
   required that an intake-only item's prompt "not print `initial-request.md`"
   and contain "no sentence concluding 'nobody asked'". But the branch prose is
   static — a non-goal explicitly ruled out conditional language — so both
   artifacts are always *named* in `spec`'s paragraph; only the substituted
   value varies. The tests now assert the properties that are actually load
   bearing: the paragraph **opens** with the resolved artifact
   (`para.startswith("**Inputs.** \`intake.md\`")`), and every sentence carrying
   the "nobody asked" conclusion also names `initial-request.md` — i.e. the
   conclusion is *scoped*, not absent. The intake branch is asserted positively
   alongside it, so deleting the guidance cannot pass.

2. **Tasks 5 and 6 cannot be separate commits.**
   `tests/test_skill_lifecycle_parity.py::test_inputs_names_every_artifact_the_table_lists`
   asserts each skill stage document's `## Inputs` names every artifact
   `LIFECYCLE_STEPS.inputs` lists. Sweep rows 5–7 therefore move with row 4 or
   the suite is red between the two commits. Folded into `e6a79de`.

3. **The spec named one fixture set to regenerate; there are two.**
   `tests/fixtures/prompt_fallback/unconfigured.json` is a byte-exact tripwire
   over shipped prompt text, captured before the documentation substitution
   existed. It fired correctly. Rather than re-capturing it wholesale — which
   would destroy the evidence it was captured to hold — only the `spec`, `plan`,
   and `postmortem` entries were replaced, each time after asserting the
   remaining stages were byte-identical. The reason is recorded in that file's
   own module docstring so the next reader does not re-derive it.

4. **The 50-line ceiling bit, as the spec's risk section predicted.** `spec.md`
   reached 51. The clause cut was "a spec written without reading the code it
   changes is a guess" — already carried by step 2's *ground every claim in the
   code, with file and line*. `spec.md` landed at 49, so the ceiling keeps a
   line of margin rather than sitting at exactly 50. Step 2 also said "the
   request's references"; the body may be an intake, so it now says "the body's".

## Out-of-band: the test suite was launching the developer's editor

Reported mid-implementation, unrelated to this item, fixed in `1fd7526`.

`tests/test_serve.py::test_the_open_gate_agrees_with_what_the_payload_advertises`
reached the `/open` **success** path on a real artifact and — unlike its three
sibling `/open` tests — never stubbed the opener. So every `pytest` run executed
`open <tmp>/…/post-mortem.md` (`tcw/serve/__init__.py:97`) and launched the
default Markdown editor. Nothing in TCW's runtime opens a file unprompted;
`/open` is the web UI's explicit "open in editor" button.

Fixed where all callers route through rather than in that one test: an autouse
guard in a new `tests/conftest.py` fails any test that spawns `open`/`xdg-open`
or a browser, and `stub_desktop_opener` is how a test reaches the success path
deliberately. Both are argv-aware and delegate everything else to the real
`Popen` — `tcw.serve.subprocess` **is** the stdlib module, so the naive blanket
stub also broke every `git` call `FsWorkStore` makes, which is how the first
attempt failed.

Not tracked as its own work item: it was a test-only defect, fixed in one
commit, and it is recorded in `docs/changelogs/upcoming.md`. Raise it at
`verify` if it should have been an item.

## Notes

- `tests/fixtures/*/_scratch/` is now gitignored. Both fixture capture scripts
  default their throwaway node to `_scratch/` inside the fixture directory,
  which lands a **nested git repository** in the tree — `git add` refuses with
  "does not have a commit checked out". Found the hard way in Task 5.
- The `spec` prompt's first rendered line is short on an intake-only item
  ("**Inputs.** `intake.md`, read as filed. An") because the source line was
  hard-wrapped for the longer token. Cosmetic — Markdown reflows it — and
  fixing it would mean re-wrapping at render time. Left alone deliberately.
- The taxonomy still has no term for the body surface or for intake. Real gap,
  out of scope here, worth a backlog item.
- Dual review of the spec (`codex` + `bllm-review`) caught the design flaw that
  would have broken this: the first draft shared `substitute_documentation`'s
  block walk, which would have rendered a line break mid-sentence. Both
  reviewers found it independently. `codex` also found sweep rows 14–17.
