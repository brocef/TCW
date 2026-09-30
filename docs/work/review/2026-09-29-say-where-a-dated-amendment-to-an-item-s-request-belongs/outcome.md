# Outcome

Documentation only. It now says where a later amendment to an item's request
goes:

- appended to `initial-request.md` under a dated `## Added <YYYY-MM-DD>`
  heading;
- with the spec and plan revised, or a reason given for leaving them;
- routed through `rework.md` when the item is in review.

The same rule appears in three places: `skills/work/references/commands.md`
("Amending a request"), `docs/guide/work.md` ("Amending a request after it is
written"), and `tcw/work/procedures/create-work.md`. The `request` stage
prompt now keeps existing `## Added` sections on a re-run.

## What shipped, task by task

| Task | What | Commit |
| ---- | ---- | ------ |
| 1 | the rule in `commands.md`, the guide, and `create-work.md`; the capability description | `0b674c65` |
| 2 | the request prompt and the lifecycle reference keep `## Added` sections | `0b674c65` |
| 3 | the router's pointer, and the prompt-fallback fixture re-baselined | `f820f64a` |
| 4 | review fixes | `d4afcf08` |
| 5 | changelog and release notes | `0b674c65` |

## What the plan and spec got wrong

- **The router's line budget.** The plan put a new sentence under the router's
  table. `skills/work/SKILL.md` has a 60-line body budget
  (`test_skill_lifecycle_parity`), and that made it 63. The pointer went into
  the `request` row of the table instead.
- **The fixture.** The spec did not foresee that changing
  `tcw/work/prompts/request.md` moves the prompt-fallback fixture. It was
  re-baselined by its procedure: only the `request` entry's two added lines
  moved, and a history note was added in `capture.py`.
- **The spec assumed the `request` stage runs on any open item.** It runs
  only in backlog. Review found this, and the rule now says so: past backlog,
  write `initial-request.md` directly, or use the web app's body editor.
  - That changes again with
    `2026-09-29-let-a-started-item-still-pass-its-planning-gates-or-stop-start-from-letting-it-past-them`
    (#71), which makes `request` legal in `active`.
  - That item's plan now carries the update to this rule, found while writing
    this outcome.

## Review

The adversarial code review returned eight findings and "merge after fixes".
All eight were applied in `d4afcf08`. The substantive ones:

- the `request` stage is legal in backlog only (above);
- in review, verify never reads `rework.md`, so the amendment must also reach
  the spec after `tcw work rework`, and the rule says so;
- `tcw work show` prints only the start of the body, so "check with `show`"
  was wrong advice. The web app's request tab shows the whole file;
- the table row's wording;
- the paragraph about body writes never following the fallback to
  `intake.md` had been moved out of "The body surface", and was moved back.

## Checks

- `tcw validate` and `tcw capabilities check` pass.
- The documentation-surface tests pass.
- Full suite on `main` at `9dbe4384`, which includes the review fixes: see
  `refined-outcome.md`.

## Autonomous decisions

- **Documentation only, or a new file or command?**
  - Opus: documentation only (option A), writing the request first on an
    intake-only item. It added the spec and plan revision goal, and cited
    `tcw/work/recursion.py`'s removal of mechanically written requests as
    precedent.
  - Sonnet: the same, and it added the prompt goal.
  - Chose A, with both additions.
- **Review findings:** all eight applied, none rejected.
- **Sequencing with #71:** its plan gained a task to update this rule, rather
  than this item documenting a route that #71 changes in the same release.
