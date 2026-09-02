# Plan: split `tcw work stage` into `prompt` and `begin`

Six tasks. The suite is green at every commit boundary. The ordering principle
here is that the **migration is the risk, not the plumbing** — so the new verbs
and every in-repo caller move in one commit rather than leaving a window where
the tree names a command that does not exist.

## Task 1 — Extract the shared tail of `_stage`

Pure refactor, no behavior change, no test change.

**Modifies:** `tcw/work/cli.py`

`_stage` (816-903) and `_stage_without_item` (768-813) share ~25 lines from the
pre-check block through the final `print(res.text)`. Extract them into:

```python
def _stage_tail(args, step, st, item, slug, status, artifacts) -> int:
```

Both existing functions call it. The item path passes `item`, `bare`,
`item.status`, `st.artifacts(bare)`; the inbox path passes `None`, `""`, `""`,
`()`. The comment explaining why the `--no-exec` plan goes to stderr moves into
the helper, where it now covers both callers — today it exists only in the item
copy, which is how the review found the two had already drifted.

**Proves it:** `pytest -q` unchanged at 2244 passed. `tcw work stage spec <slug>`
output byte-identical to before, diffed.

## Task 2 — Add `prompt` and `begin`; remove the bare form

The large one. Code, tests, and the recorded fixture move together, because a
commit that adds the verbs without updating callers leaves the suite red.

**Modifies:** `tcw/work/cli.py`, `tests/test_stage_verb.py`,
`tests/test_body_prompt.py`, `tests/test_falsification_rule.py`,
`tests/fixtures/prompt_fallback/capture.py`,
`tests/fixtures/prompt_fallback/unconfigured.json`,
`tests/cli/scenarios/03-lifecycle-gates-and-illegal-transitions.md`,
`tests/cli/scenarios/04-stage-prompts-bindings-and-hooks.md`,
`tests/cli/scenarios/05-documentation-entries.md`,
`tests/cli/scenarios/11-scaffold-and-artifact-templates.md`

- Replace `pstg`'s two positionals with a subparser group holding `prompt` and
  `begin`. `prompt` takes `stage` plus `nargs="?"` slug; `begin` takes both.
- `begin` is today's `_stage`, unchanged.
- `prompt` resolves the store via `_store()` when no slug is given and via
  `_resolve()` when one is, then calls `_stage_tail` with no legality check and
  `pre` bindings skipped.
- `inbox` refuses a slug on both verbs; `begin inbox` runs inbox's `pre`
  bindings and skips legality.
- Unknown subcommand error names `begin`.
- Error prefixes become `tcw work stage prompt:` and `tcw work stage begin:`.
- `--no-exec` is accepted by `begin`, rejected by `prompt`.

**The JSON fixture is edited by hand, never re-captured.**
`tests/fixtures/prompt_fallback/unconfigured.json` holds six recorded `argv`
arrays plus frozen `stdout`. Only the `argv` arrays change, from
`["work","stage",<stage>,<slug>]` to `["work","stage","begin",<stage>,<slug>]`.
Re-running `capture.py` would overwrite the recorded stdout with what the code
does now, destroying the back-compat evidence its own docstring exists to
protect — and the suite would still pass.

**Proves it:** criteria 1, 2, 6, 9, 10, 11, 12, 13, 14. Plus a diff of
`unconfigured.json` with `argv` lines excluded, showing zero changed bytes
(criterion 16).

## Task 3 — The illegal-status notice and node-qualified resolution

Separated from Task 2 so the behavior that gives up a guarantee is isolated and
reviewable on its own.

**Modifies:** `tcw/work/cli.py`, `tests/test_stage_verb.py`

- When `prompt` is given a slug and the stage is not legal for that item's
  status, print the notice on stderr, print the instructions on stdout, exit 0.
- Add tests for the two-node case: `prompt <stage> <project-id>/<slug>` resolves
  that node's `prompt:` bindings, not the anchor node's.
- Add a `when: {tags: [bug]}`-conditioned prompt binding to the fixture node and
  assert it is skipped by `prompt <stage>` and matched by
  `prompt <stage> <slug>` when the item carries the tag. This is what makes the
  optional slug worth having rather than cosmetic: it is the only test that
  shows the two invocations resolve *different text* on purpose.

**Proves it:** criteria 5, 7, and 8.

## Task 4 — The gate-non-execution evidence

**Creates:** a scratch-node fixture in `tests/test_stage_verb.py`

A node whose `plan.pre` binds a throwaway command that creates a sentinel file.
Then: `prompt plan <slug>` on an item with no `spec.md` exits 0 and the sentinel
does **not** appear; `begin plan <slug>` on the same item exits 1 and the
sentinel **does** appear.

The paired assertion is the point. Without the `begin` half, the `prompt` half
passes just as well when the gate is broken and never runs at all. This
repository's own `require_artifact.py` cannot serve here — it writes nothing, so
its non-execution leaves no trace to observe.

**Proves it:** criteria 3 and 4.

## Task 5 — Migrate the documentation surface

**Modifies:** the seven `skills/tcw-work/references/lifecycle/stage-*.md`,
`skills/tcw-work/SKILL.md`, `skills/tcw-work/references/commands.md`,
`skills/tcw-work/references/hooks.md`,
`skills/tcw-work/references/lifecycle/default/README.md`,
`skills/documentation-sync/SKILL.md`,
`skills/documentation-sync/references/setup.md`, `AGENTS.md`,
`docs/capabilities/work/run-a-lifecycle-stage/description.md`,
`docs/capabilities/work/read-the-documentation-gate-for-a-change/description.md`,
`docs/capabilities/work/customize-lifecycle-artifact-templates/description.md`,
`tcw/work/templates.py` and `tcw/work/resolve.py` (docstrings),
`tcw/store/base.py` (comment), `scripts/require_artifact.py` (docstring),
`tests/test_skill_lifecycle_parity.py`, `tests/test_documented_cli_surface.py`,
`tests/test_shipped_prompts.py`

- Everything agent-facing says `begin`. `prompt` appears only in
  `default/README.md` and the README examples that demonstrate reading.
- `test_skill_lifecycle_parity.py`'s literal becomes
  `f"tcw work stage begin {stage_id}"`, and it fails if a router names the bare
  form or `prompt`.
- `DOCUMENTED_VERBS` becomes `("tcw work stage prompt", "tcw work stage begin",
  "tcw work scaffold")`.
- `run-a-lifecycle-stage` states the refusal guarantee applies to `begin`, and
  drops the in-flight item's deferred claim that `tcw work stage inbox` is
  refused.
- Nothing under `ARCHIVAL` (`tests/test_documented_cli_surface.py:36-42`) is
  touched: `docs/work/`, `docs/plan/`, `docs/superpowers/`, `docs/changelogs/`
  and `docs/release-notes/` record what was true when written. The two
  `upcoming.md` files are the exception and belong to Task 6, because they
  describe the release being cut rather than a past one.

**Proves it:** criteria 15, 17, 18, 22.

## Task 6 — Documentation Sync, version, migration guide

All four of this project's documentation entries fire. Scheduled as one block
at the end, answered in one pass over the finished diff.

**Modifies:** `README.md` **[Public-API]** — the CLI surface changed;
`docs/release-notes/upcoming.md` **[Public-API]**;
`docs/changelogs/upcoming.md` **[Any-Code-Change]**;
`skills/tcw-work/SKILL.md` **[Skill-Driven-Component]** — the component's CLI
surface changed (the router edits land in Task 5; this is the final pass).
**Creates:** `docs/migration-guide-1.X-to-2.0.0.md`.
**Modifies:** `pyproject.toml`, `tcw/__init__.py`, `.claude-plugin/plugin.json`,
`.claude-plugin/marketplace.json`, `.codex-plugin/plugin.json`.

- Both `upcoming.md` files are **rewritten, not appended to**. They currently
  carry the in-flight item's claims that inbox "is the one stage you run without
  naming a work item" and that "Every other stage is unchanged and still takes
  its work item". Both become false. The two items ship in one release, so this
  item owns the reconciliation.
- Version to `2.0.0` in all five files, via
  `python scripts/cut_version.py 2.0.0` — which also rotates the two
  `upcoming.md` files, so the rewrite above must land first.
- The migration guide follows the five existing `docs/migration-guide-*.md` in
  form, showing before/after for both verbs.

**Proves it:** criteria 19, 20, 21, 23.

## Documentation Sync

| Entry | Trigger | Fires | Task |
| --- | --- | --- | --- |
| `README.md` | Public-API | yes — the public CLI surface changes | 6 |
| `docs/release-notes/upcoming.md` | Public-API | yes | 6 |
| `docs/changelogs/upcoming.md` | Any-Code-Change | yes | 6 |
| `skills/<component>/SKILL.md` | Skill-Driven-Component | yes — `tcw-work` drives the changed component | 5 and 6 |

## Verification

Things the suite cannot decide, to be checked by hand before the item is
submitted:

- **The stderr notice reads as a warning, not an error.** It fires on a success
  path with exit 0, and its wording has to make that obvious to someone who has
  just piped stdout somewhere.
- **The migration guide is accurate**, not merely present — every before/after
  pair in it actually runs as shown.
- **The recorded `stdout` in `unconfigured.json` is unchanged.** The diff-with-
  argv-excluded check in Task 2 proves the bytes; that it was hand-edited rather
  than re-captured is a fact about how, which only inspection of the commit
  shows.
- **`prompt` is worth its cost.** The spec names the failure condition: if the
  routers' `begin` path is what everyone uses and `prompt` is invoked only by
  its author, the sibling-verb alternative would have been the better trade.
  Worth revisiting at post-mortem rather than pretending the question closed.

## Notes

Task 1 removes the duplication reported by the review of
`claude/tcw-work-list-zx961v`, and Task 2 deletes the untested
`'<stage>' needs a work item` branch that review also flagged. Neither is fixed
on that branch, because nothing ships between the two items.

`pre` was specified and dropped during intake. Should a caller ever appear,
`begin` already contains it and Task 1's `_stage_tail` is the seam to add it on.
