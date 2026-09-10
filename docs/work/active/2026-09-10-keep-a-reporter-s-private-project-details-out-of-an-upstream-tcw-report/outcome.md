# Outcome: keep a reporter's private project details out of an upstream TCW report

Nine commits on `claude/kind-babbage-epcpqy`, rebased onto `0029663` (`main` at
v2.0.2) partway through — the seven task commits below, plus the `→ active`
transition that opens them and this record that closes them. No Python changed: `git diff origin/main..HEAD -- tcw
tests scripts pyproject.toml` is empty.

## What shipped, by task

| Task | Commit    | What landed                                                                                                                                                                           |
| ---- | --------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1    | `878c8e6` | `plugin/report-an-issue-upstream` seeded `Missing` with the `Planning doc` back-pointer, its `description.md` written in its two siblings' voice, and the item's `capabilities.yaml`. |
| 2    | `551e877` | `## What goes in the report` — the public/private asymmetry, the mirrored default, the swap and keep lists, and the output preference.                                                |
| 3    | `32c65d0` | Fresh-environment reproduction encouraged and explicitly optional; delegating it to a subagent or agent team member in a temporary directory.                                         |
| 4    | `64a58c3` | The before/after block (7 lines including its fences), and the closing paragraph relocated from "real vs. abstract" to the command's shape.                                           |
| 5    | `93ff51e` | The bug skeleton's `Steps to reproduce` and `Actual` placeholders point at the mirrored run. Environment block and `tcw --version` step untouched.                                    |
| 6    | `c573d70` | Capability flipped to `Supported`.                                                                                                                                                    |
| 7    | `f919ffe` | `docs/changelogs/upcoming.md`, `docs/release-notes/upcoming.md`, and one clause in `skills/tcw-plugin/SKILL.md`'s router bullet. README unchanged, deliberately.                      |

`skills/tcw-report/SKILL.md` is 118 lines, against the criterion's 120.
`allowed-tools` is byte-identical to `origin/main`, and the file contains no
command that posts to GitHub.

## Test result

`python3 -m pytest -q` at `f919ffe`: **2523 passed, 4 failed** in 379s. Every
failure is this container, not the diff — which touches no Python at all:

- `tests/test_scaffold.py::test_an_unwritable_target_reports_and_prints_no_path`
  and the two `tests/test_store_editor.py` atomic-write failure tests each
  `chmod` a directory to drop write permission and assert the write fails. The
  session runs as uid 0, which bypasses the permission bits, so the writes
  succeed and the assertions invert.
- `tests/test_shipped_prompts.py::test_the_prompts_are_in_the_built_wheel` builds
  a wheel, and the build dies in this image's setuptools with
  `AttributeError: install_layout`. Reproduced outside pytest with a bare
  `pip wheel --no-deps --no-build-isolation`.

`tests/test_plugin_manifests.py` passes on its own (25 tests). `tcw validate` and
`tcw capabilities check` both exit 0. `pnpm prettier --check` passes on every file
this item **adds** — and still fails on `skills/tcw-plugin/SKILL.md`, which it
edits, for drift on a line the diff never touches. See `## Notes`.

## What the plan and spec got wrong

**The plan's task count does not match its tasks.** The preamble says "Seven
tasks" and refers to "tasks 6–7", but only Tasks 1–6 are numbered; the seventh is
the unnumbered `## Documentation Sync` block. Recorded here rather than renumbered,
because the block is a real task and the plan's ordering was followed exactly.

**The Documentation Sync table mis-counted what fires.** It says "All four of this
project's entries are considered; two fire", then marks two of the four
`Evaluate`. Three entries produced an edit, not two: the changelog and the release
notes as predicted, and `skills/<component>/SKILL.md` via the `tcw-plugin` router
bullet, which the table had left undecided. README was the one entry re-read and
deliberately left alone — its `tcw-report` row describes where a report goes, and
that has not changed.

**The plan's verification command expected 19 passing manifest tests.** `main`
grew the file to 25 between planning and implementation. The count in a plan is a
snapshot, not a criterion; criterion 10 asks only that the file passes.

**The plan's line budget was tighter than it read.** Tasks 2–4 fit in 40 lines
against a 120-line ceiling on a 78-line file, which left 2 lines of slack once the
example and both lists were written as specified. The example came in at 7 lines
including its fences, against its 12-line allowance, to buy that margin. A plan that adds prose under a
hard line cap should say what gets cut if the budget binds; this one did not, and
the answer turned out to be the example.

**The spec's file list and the diff disagree.** `## Design` opens "Eight changes,
all inside `skills/tcw-report/SKILL.md`", and the eight design items are indeed
all in that file. But the documentation gate fired on a ninth file: `plan.md`'s
Documentation Sync table anticipated `skills/tcw-plugin/SKILL.md` and bounded the
edit to one clause, which is what landed. No non-goal forbids it and the plan
scheduled it; the spec's scope sentence is the thing that reads as wrong, because
it describes the design items rather than the diff.

**The keep list dropped a word the spec chose deliberately.** The spec says keep
"the error type and message **template**"; the section first said "the error type
and its message", which invites pasting a message with an identifying path still
inside it — the exact thing the worked example swaps. Corrected to "the fixed part
of its message" after an independent read of the finished file caught it.

## Notes

- **What the verification read found, and what it changed.** An independent
  read-only pass over the ten criteria reported all ten met, and found four
  inaccuracies in this record and in the prose around it rather than in the
  skill: a false claim that Prettier passes on every file touched, a commit count
  that named the task commits rather than the branch, three different numbers for
  the example's length, and a garbled sentence in the section carrying criterion 2
  ("keep in any real detail you want there"). All four are corrected above or in
  the files; the last two reached the changelog and the skill, which is where the
  cost of leaving them would have been.
- **Where the example went.** The plan placed the worked example "inside the new
  section" without saying where. It sits after the swap and keep lists and before
  the output paragraph, so it reads as the lists made concrete.
- **The rebase moved the documentation target.** `main` cut v2.0.1 and v2.0.2
  while this item was in flight, which rotated both `upcoming.md` files. The
  entries written here landed in the fresh pair, attributed to the next version
  rather than to a release that already shipped. No conflict, and no content of
  anyone else's was displaced.
- **Found in passing, not fixed: the repository does not satisfy its own Prettier
  check.** `pnpm prettier --check .` on `origin/main` reports drift in `AGENTS.md`
  and roughly twenty files under `docs/capabilities/`, all predating this item.
  One of those files, `skills/tcw-plugin/SKILL.md`, is touched here; the
  reformatting that `--write` applied to its unrelated lines was reverted so the
  commit carries only the router clause. Repairing the rest is a mechanical
  whole-repo diff with no bearing on this item's behaviour, and it needs a
  decision about whether `prettify:check` should gate CI at all — which is why it
  is reported rather than bundled.
