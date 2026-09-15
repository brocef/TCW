# Outcome — Migrate TCW itself to the 1.0.0 lifecycle and write the consumer migration guide

## What shipped

| Task | Commit    | What                                                                              |
| ---- | --------- | --------------------------------------------------------------------------------- |
| 1    | `b8826ae` | `docs/migration-guide-0.21.X-to-1.0.0.md`                                          |
| 2    | `2a47a82` | Linked it from `docs/release-notes/v1.0.0.md`                                      |
| 3    | `f642167` | `docs/lifecycle/{abstraction,harness,implementation}.md`, moved verbatim           |
| 4    | `85d173e` | `docs/lifecycle/templates/{spec,spec-bug}.md`                                      |
| 5+6  | `7d4ca4e` | The `work.lifecycle` block, `scripts/require_artifact.py`, `tests/test_repo_lifecycle.py` |
| —    | `4c1815b` | Filed the `scaffold` draft-staging finding as its own backlog item                 |
| 7    | `19e7ba8` | `AGENTS.md` 80 → 54 lines                                                          |
| 8    | `0b64cbf` | Ten references repointed at `docs/lifecycle/`                                      |
| 9    | `42792d9` | `docs/changelogs/upcoming.md`                                                      |
| 10   | `fe5bca4` | The dogfooding findings folded into the guide                                      |
| 11   | `81fda5a` | Re-captured `tests/fixtures/lifecycle_baseline/self.json` (unplanned — see Corrections) |

## Tests

Full suite, on the finished tree:

```
1592 passed in 276.60s (0:04:36)
```

Baseline before any change, captured at `8d9450a`: `1581 passed in 416.84s`, exit 0.
Criterion 12 required ≥ 1581 passed and 0 failed.

**The +11 is fully accounted for**, not assumed: `tests/test_repo_lifecycle.py`
adds 5, and `test_documented_cli_surface.py::test_documented_verbs_and_flags_exist`
is parametrized over every git-tracked non-archival Markdown file, so the 6 new
`.md` files add 6 more. 1581 + 5 + 6 = 1592.

That parametrization is worth naming as evidence in its own right: it parses
every `tcw …` invocation in the new migration guide and asserts the verb and its
flags actually exist. The guide's commands are checked, not just proofread.

Acceptance criteria, each run rather than asserted:

| # | Result |
| - | ------ |
| 1, 2, 3 | Guide covers the break with both spellings and both fixes before any feature; all six behavior changes present; upgrade-ordering section present. |
| 4 | `tcw validate` → `validate OK`, exit 0. |
| 5 | `tcw work stage spec` → builtin at offset 0, `abstraction.md` at 2507, `harness.md` at 4847. Order asserted programmatically against file contents. |
| 6 | Item without a spec → exit 1, **0 bytes** on stdout, refusal on stderr. Item with a spec → exit 0, 4508 bytes. |
| 7 | `bug`-tagged item's draft contains `## Reproduction` (1 occurrence); untagged item's does not (0). Both carry the litmus section. |
| 8 | `plan` draft carries every `_PLAN` heading — missing: none. |
| 9 | `tcw work lifecycle --json` parses; `spec`, `plan`, `implement` report `bind`, `plan` and `complete` report `pre`. |
| 10 | `Abstract spine` 0, `Harness compatibility` 0, `abstraction litmus test` 1 (the permitted pointer line, not a heading). `## Documentation Sync` and `## Versioning` both still present. |
| 10a | No reference to a moved rule remains. |
| 11 | `tests/test_repo_lifecycle.py` → 5 passed. |
| 12 | 1592 passed, 0 failed. |
| 13 | `tcw/` modified in module-docstring text only, as criterion 10a permits. |

Also verified beyond the criteria: the `implement` binding composes in the right
order (builtin → `implementation.md` → `harness.md`); `tcw work stage plan` on an
`active` item is refused with the status reason; and `--no-exec` skips the `pre`
check, reporting it as "would run" on stderr while still printing the prompt.

## Corrections

Seven things the spec or plan got wrong. All corrected in place.

1. **The `plan` artifact template was dropped.** The plan called for one. Written,
   it came out byte-identical to `tcw.work.templates._PLAN` — so binding it would
   have bought nothing while taking on the drift that first-match-wins creates.
   Deleted before it was bound, and `test_the_plan_stage_has_no_bound_template`
   now pins the decision so nobody re-adds an unchanged copy. Criterion 8 is met
   by the built-in, which was always the honest reading.
2. **Tasks 5 and 6 became one commit.** The plan had the guard test committed
   before the config it guards, which directly contradicts the plan's own
   green-at-every-commit-boundary rule. The test was still written first and
   watched fail for the right reason (`KeyError: 'lifecycle'`); it just does not
   get a red commit of its own. The plan's step 1 and its Task 5 wording were
   inconsistent with each other and step 1 wins.
3. **The spec enumerated six stale `AGENTS.md` references; there are ten.** The
   spec's list came from a review sweep that matched on the rule *names*. Four
   more cited the rules without naming them — "don't pre-abstract" in
   `phase-4-shared-core.md`, `phase-1-scaffold.md` (twice), and the ABC+adapter
   rule in `phase-5-work.md`. Criterion 10a is the general statement, so all ten
   were fixed. **Lesson: grep for the guide's filename, not the rule's title.**
   This is now point 2 of the guide's own migration advice.
4. **Only one Documentation Sync trigger fires, not the two the plan predicted.**
   `skills/tcw-work/SKILL.md` [Skill-Driven-Component] does **not** fire: the
   trigger is "whenever the component it drives changes — its CLI surface,
   model/fields, lifecycle, or guardrails", and none of those changed. This item
   *configures* the work component; it does not change it. `SKILL.md` already
   names `tcw work stage`, so there is no gap to close either. Only
   `docs/changelogs/upcoming.md` fires, under `## Internal` — with precedent:
   v1.0.0's own `## Internal` covers `scripts/cut_version.py`, which is likewise
   unpackaged repo tooling.
5. **Neither the spec nor the plan anticipated Task 11.**
   `tests/test_lifecycle_baseline.py::test_this_repository_s_own_lifecycle_output_is_unchanged`
   replays `tcw work lifecycle` against the **live repo** and compares against a
   recording. Configuring this node's lifecycle fails it by construction. Exactly
   10 of the 26 recorded rows changed — the three configured stages, the
   `complete` transition, and the two aggregate views — and no others; the ten
   fixture-backed corpus rows stayed byte-identical in the same run, which is
   what proves the delta is the config and not the renderer. The recording was
   re-captured and the procedure written into the test's docstring, where it
   previously had to be derived from `capture.py`.
6. **Criterion 9 appeared to fail and had not.** The first probe read
   `steps[].bind`; bindings are nested under `steps[].bindings`. The config was
   right and the check was wrong. Recorded because "the criterion failed" was a
   claim made for about a minute on no evidence.
7. **The dual review only half-ran.** `codex` reviewed the spec, found four
   defects — all verified against the tree and all accepted — and independently
   confirmed the two load-bearing claims (prompts concatenate, templates are
   first-match-wins; stage `pre` runs only from `tcw work stage`). `bllm-review`
   produced **zero bytes in over 30 minutes** and was still running at the end of
   the session. So the spec had one review, not two. Flagged rather than papered
   over.

## Notes

- **One CLI finding filed, not fixed**, per the spec's non-goals:
  `2026-08-18-decide-whether-tcw-work-scaffold-should-stage-its-draft-in-git`.
  `tcw work scaffold` calls `self._stage(p)` at `tcw/store/fs.py:3538`, so a
  draft that the board, `--json`, and the web app all agree is *not* a document
  nonetheless lands in the git index — three stray `*.draft.md` files had to be
  `git reset` by hand during this work. Filed via piped stdin, which also
  confirmed the new intake behavior end to end: the text landed in `intake.md`
  and the board shows `i`.
- **The bindings this repo does not use.** `generate:` is unexercised, as the
  spec's non-goals said it would be: this repo has no rule whose text depends on
  the item, and writing one to demonstrate the feature is the demonstration text
  the spec ruled out. `blob:` is unexercised deliberately — every prompt here is
  `file:` so that source comments can cite it, which became point 2 of the
  guide's advice.
- **What could not move, and why it matters.** `## Documentation Sync` and
  `## Versioning` stay in `AGENTS.md` because
  `skills/documentation-sync/SKILL.md:8` and `:117` locate them by name in
  `CLAUDE.md`. Moving them would have made TCW's own repository fail the skill
  TCW ships. This is the single most useful thing the migration produced and is
  point 1 of the guide's advice.
- **Codex parity is reasoned, not tested.** `tcw work stage` is the CLI, so it
  behaves identically under both harnesses by construction — but nothing in this
  repo executes a Codex agent to prove the moved rules are reached. Named here
  as reasoning so `verify` can weigh it as such.
- **The accepted risk stands and needs a human read.** An agent that never runs
  `tcw work stage` now sees 54 lines of `AGENTS.md` instead of 80. Whether that
  is still sufficient is Verification item 2 and is the main thing to put in
  front of the user.
