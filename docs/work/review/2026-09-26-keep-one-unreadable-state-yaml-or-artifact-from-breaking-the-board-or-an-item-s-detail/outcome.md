# Outcome — Keep one unreadable state.yaml or artifact from breaking the board or an item's detail

## What shipped

| Task | Commit | What |
| ---- | ------ | ---- |
| 1–2 | `dccb09e6` | Failing tests, then: `_safe_yaml` degrades a non-UTF-8 / non-file state to `{}` (re-raising `FileNotFoundError`); `_present` / `_resolve_body` decode with replacement; `_revision` + `_read_revision_text` make every file revision lossless; the web detail lists a damaged artifact with its revision and its GET names the file. |
| docs | `e61d71b8` | Changelog and release-note entry files. |
| review | `076cf5ad` | `_require_readable_state`: `start` and every transition refuse an item whose `state.yaml` cannot be read, before anything moves. Core-revision test; graveyard reader comment. |
| review | `36ba28de` | Plan-stage guard test. |

## Tests

- New `tests/test_unreadable_item_files.py`, 19 tests: the board with a damaged
  `state.yaml` (not UTF-8, folder, pipe); the board and `show` with a damaged
  intake or request; the web detail with a damaged `state.yaml` or `spec.md`; a
  guarded save replacing a damaged artifact, sidecar and plan stage, and a stale
  revision refused; a CRLF file keeping its revision and its guarded save;
  `_safe_yaml` still raising a mid-read `FileNotFoundError`; opening a damaged
  artifact naming the file; `start`, `submit` and `complete` refusing a damaged
  item before moving it; two differently damaged bodies getting different
  revisions.
- Mutation-checked: a strict `_revision` encode, swallowing `FileNotFoundError`,
  hashing raw bytes instead of newline-normalized text, dropping the `is_file()`
  check, the web detail dropping a damaged artifact, removing either strict
  check before a move, and a strict read in the plan-stage guard — each turns the
  intended test red. The CRLF test first passed under the raw-bytes mutation (it
  compared two values that never went through the changed code) and was
  rewritten to do a guarded save.
- Full suite before the review fixes: 4772 passed, 3 skipped. After them: see
  `refined-outcome.md`.
- Hands-on: the spec's three-row reproduction — see `refined-outcome.md`.

## What the plan or spec got wrong

- **The spec's safety argument was incomplete** (found by the code review, and
  the most serious miss here). It reasoned that a degraded `{}` could never be
  *written back*, which is true, but `start` and every transition read the item
  through the same tolerant path to decide their gates, then moved the folder,
  and only then failed on the strict read — leaving an interrupted claim, or an
  item moved to `completed/` with no commit. Before this item those reads raised
  first and nothing moved. Fixed with a strict check before any move.
- **The damage was wider than the intake.** The request text (`intake.md`,
  `initial-request.md`) also took the whole board down; found at reproduction and
  folded into the spec.
- **The web detail dropped a damaged artifact entirely** (it caught the decode
  error as a `ValueError`), so no revision reached the page and criterion 4
  could not pass as the spec designed it. `tcw/serve/__init__.py` was not in the
  plan's file list; it is now changed.
- **Criterion 6 was loosely worded.** `_safe_yaml` answers `{}` for a folder
  already gone, as `load_yaml` always did; only a disappearance *during* the read
  raises, and that is what the test simulates.
- **A changed gate, accepted:** `_present` now answers "present" for a
  `spec.md` that is not valid UTF-8, so `tcw work stage gate implement` accepts
  it where it used to crash. The file exists; `tcw validate` reports its damage.
- **Tracker sync reads `owner` from the tolerant item** (reviewer, suspected,
  not traced): a damaged item reads unowned. Every move of a damaged item is now
  refused before the tracker is asked to follow it, which bounds this; not
  pursued further.

## Autonomous decisions

- **May a guarded save replace a non-UTF-8 file? (spec)** Codex: yes, with
  lossless revisions and newline normalization kept. Opus: yes; re-raise
  `FileNotFoundError`; beware lost `parent:`. Both chose yes; done that way.
- **Review (adversarial-code-reviewer, "do not merge").** Accepted and fixed:
  the gate-then-move regression (blocking), the stale graveyard comment, the
  missing plan-stage and core-revision tests. Accepted as documented behavior:
  `_present` on a damaged spec, the tracker owner read. Filed as a follow-up:
  `2026-09-29-keep-a-child-whose-state-yaml-cannot-be-read-visible-to-its-parent-s-completion-gate`
  (the lost-`parent:` hazard, a non-goal of this item).
