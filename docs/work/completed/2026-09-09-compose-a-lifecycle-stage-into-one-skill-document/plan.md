# Plan: compose a lifecycle stage into one skill document

Small and single-file, so planning is compressed. Two tasks and a measurement
step, in one branch already carrying the release this ships in.

## Task 0 — Measure the injection contract before designing on it

The Claude Code skills documentation leaves three things unstated that decide the
design, so each was probed with a throwaway skill and a headless `claude -p` run
rather than assumed:

- **Does argument substitution happen before or after the injected commands
  run?** If after, every form breaks inside a `` !`cmd` `` and the design is
  impossible as sketched.
- **Does stderr reach the model, or only stdout?** `prompt`'s illegal-stage note
  is on stderr, and losing it would make the skill silently deliver instructions
  for a stage the item is not ready for.
- **What does a non-zero exit do?** The docs say it aborts the invocation; what
  the reader sees in that case decides whether to tolerate the exit.

## Task 1 — The skill

**Creates:** `skills/tcw-work-stage/SKILL.md`.
**Modifies:** `skills/tcw-work/references/commands.md` (one row).

The command reference rather than `skills/tcw-work/SKILL.md`: the router is at
its 60-line budget and its own test says extract, never grow. Discovery for
Claude comes from the skill's `description`, which is the mechanism that
actually drives auto-invocation.

## Task 2 — The tests

**Modifies:** `tests/test_skill_lifecycle_parity.py`.

Three, all reading the skill as text, because nothing at runtime can check them —
`|| true` is deliberately swallowing exactly the failure a rename would cause:

- the interpolated router path resolves for every id in `STAGE_IDS`;
- the skill names `prompt` for reading and `begin` for entering;
- both injected commands are declared in `allowed-tools`.

## Documentation Sync

| Entry | Trigger | Fires | Where |
| --- | --- | --- | --- |
| `README.md` | Public-API | no — no CLI surface change, and the README does not enumerate skills | — |
| `docs/release-notes/upcoming.md` | Public-API | yes — a new skill users invoke | Task 1 |
| `docs/changelogs/upcoming.md` | Any-Code-Change | yes | Task 1 |
| `skills/<component>/SKILL.md` | Skill-Driven-Component | yes — the `tcw-work` component gains a delivery surface; landed in its `references/commands.md` under the budget rule above | Task 1 |

`docs/capabilities/work/run-a-lifecycle-stage/description.md` also gains a
paragraph: same user capability, new delivery.

## Risks

- **The skill becomes the route rather than the ergonomic.** Mitigated by
  criterion 8 and by the skill naming `begin` itself, with a test on both.
- **A silent empty render.** Two independent causes — an undeclared command and
  a non-zero exit — both produce *nothing*, not an error. `allowed-tools` and
  `|| true` address them; the tests pin both.
- **`${CLAUDE_PLUGIN_ROOT}` not set.** Then `cat` fails, `|| true` keeps the rest
  rendering, and the closing section tells the reader to run the commands.
