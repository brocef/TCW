# Refined outcome — Harden _effect_transition against a lost status-transition race

**Accepted** by the user on 2026-08-11, in `review`, after the assessment below
was presented in full — including the reviewer that failed to report and the
residual that was found and deliberately not fixed.

## The decision

Approved as delivered. Closing `--resolution done`, on `main`, with a version cut
to follow. The `get_detail` residual found at this stage is folded into the
existing follow-up item rather than fixed here.

## What was accepted

Seven commits on `main`:

| Commit | What |
| --- | --- |
| `239a9ff` | `_require_dir` + the eight-guard collapse (net **−10 lines** in `fs.py`) |
| `7a16b16` | Guards for the four remaining unguarded `_find` sites |
| `6cf20c0` | The race-aware error in `_effect_transition` — the only new behavior |
| `bb6f2bf` | The residual pin + the follow-up item |
| `e234e62` | Changelog and release notes |
| `c0779e9` | CLI coverage for the bare `tcw work:` prefix on a lost `submit` |
| `80d637e` | The `get_detail` residual folded into the follow-up |

Full suite: **1212 passed**, run by the coordinating session rather than taken on
the implementer's word.

## Evidence

All 10 acceptance criteria met. The evidence that mattered:

- **Criterion 4 (fails-first) is real, not asserted.** Every new test was run
  against reverted code and the actual exception recorded. Codex independently
  re-ran them against reverted code and reached the same results.
- **Both `git_mv` failure branches are now pinned**, which was an accident of
  covering criterion 2 properly. `submit` targets `review/` (tracked) and fails
  pre-fix with `CalledProcessError` from `git add -- None`; `complete` targets
  `completed/` (gitignored) and fails pre-fix with `FileNotFoundError` from
  `shutil.move("None", …)`. The spec predicted both from reading `git_mv`; both
  are now observed. **The original bug report's guess of `TypeError` was wrong on
  both counts** — that correction survives in the two tests' docstrings.
- **Criterion 6** (no bare `_find` dereference) re-checked by hand at HEAD.
- **No test passes either way.** Codex verified the monkeypatch call-counting
  targets the correct `_find` lookup in each test, that `monkeypatch.undo()`
  precedes the Task 4 post-condition read, and that no class-attribute patch
  leaks between tests.

## What this does and does not deliver

**Delivers:** the loser of a transition race no longer crashes, and is told where
the item actually went.

**Does not deliver:** a handled race. The pre-move `set_field` writes still land
— `tests/test_external_work_store.py::test_lost_complete_leaves_its_resolution_written`
exists to prove it, asserting the residual rather than the desired outcome. Anyone
reading this item's title should read that test before assuming otherwise.

## Deferred follow-ups

One item, now carrying both halves:
`2026-08-11-roll-back-or-reorder-the-pre-move-set-field-writes-on-a-lost-transition`

1. The pre-move `owner`/`started`/`resolution` writes that land on a lost
   transition — including the status/resolution disagreement that
   `_status_resolution_problems` still documents as impossible.
2. **Folded in at this stage:** `get_detail`'s `None` escaping through
   `create_work` (`fs.py:2852`) and `update_work` (`fs.py:2955`), both of which
   declare `-> "WorkDetail"`. Not a regression — the same timing previously raised
   `TypeError` inside `get_detail` and now raises `AttributeError` at the caller —
   and no present-day caller is unsafe. It belongs with the other half because it
   is the same question: what does a write path that loses the race return?

Two limitations are pinned as tests rather than left to be rediscovered, and both
should be **inverted, not deleted**, when the follow-up lands: the residual pin
above, and `test_work_target_reports_an_item_that_vanishes_mid_check`, which
asserts that `tcw work validate` racing a healthy transition reports a *false*
`no such work item` line — accepted because a spurious line beats a traceback.

## Closeout choices

- **Route:** `main` directly. No branch, no PR — the work was committed there as
  it went and the user confirmed that is fine.
- **Capabilities:** no reconciliation. This node has no capabilities component
  (`tcw capabilities list` → "no tcw capabilities node here").
- **Documentation:** handled at implement (`e234e62`). `README.md` and
  `skills/tcw-work/SKILL.md` were evaluated and did not fire; the changelog and
  release-note entries did.
- **Version:** a cut follows this closeout, at the user's instruction.

## Notes

- **Three reviews were commissioned; two reported.** Codex reviewed both the spec
  and the implementation and found real defects at each stage. The local-LLM
  review timed out at 9 minutes on the full diff; a retry on a source-only diff
  returned, and — despite misnaming two functions that do not exist — produced the
  `get_detail` finding above. **The `tcw-verifier` subagent never reported**,
  going idle twice including after a direct request. Its assessment is absent
  from this record rather than reconstructed. The verification rests on the
  coordinating session's own suite run and diff read plus Codex's independent
  re-runs.
- **The dual review earned its cost at the spec stage, not the implementation
  stage.** At spec it caught a self-contradiction — the proposed error message
  told the user "Nothing was changed" while the spec's own non-goals admitted the
  field writes land first — and chasing that down surfaced the entire residual
  that now owns the follow-up item. At implementation it found one Low coverage
  gap. The expensive defects were in the thinking, not the code.
- **Two agents were dispatched** (`plan`, `implement`) under the delegation rules;
  transitions and this decision stayed with the coordinating session. The plan
  agent corrected an error in its own dispatch brief (`--tags bug,work` would have
  failed; the flag is `--tag`, repeatable), which is the re-read check working as
  intended.
