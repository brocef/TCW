# Refined outcome — Filesystem work backend on the new model

## Decision

**Accepted**, on 2026-10-08. For the TCW 3.0 epic the owner ruled (2026-10-02)
that a child item is approved when it passes adversarial review. The review
was bounded in advance at one review round, one fix round and one confirming
round. The confirming round ended NOT DONE with two findings that belonged to
this change. As the bound requires, the split was brought to the owner rather
than looped. The owner chose (2026-10-08): "Fix S1+S2, then close" — fix
both, each test first, and close without a fourth round.

## Evidence

- **Round 1** (`adversarial-code-reviewer` over `epic/tcw-3.0..d9b2b1fb`):
  NOT DONE. Each finding was checked against the code before it was fixed;
  all ten that belonged to this change were real:
  1. `init --work-path` deleted anything in the default store that was not
     an item folder — a 2.x board, notes, a malformed folder — without a
     word. The fault was in the spec's Design 11 wording, corrected on
     `main` (`ed3136cb`).
  2. `edit` wrote the item before checking its `--blocks` targets, so exit 3
     or 4 left a change behind.
  3. `item.yaml` and `request.md` were created owner-only (0600).
  4. A failed comment write left an empty file, and an undecodable reason
     moved the item and then exited 1 instead of 6.
  5. The delegation refusal printed a doubled apostrophe; 6. its
     "uncommitted in" note named the project's repository, not the work
     store's.
  7. `new --project` ignored an empty property; 8. `list --stage` with an
     unknown stage printed nothing and exited 0; 9. `tags` failed without a
     work folder; 10. the rename record described two things the command
     does not do.
  11. `outcome.md`'s test results were placeholders; they were already filled
      in by the time the report arrived.

  Two of its notes were folded in: `new --project <own id>` is a usage error,
  and a file error prints one line instead of a traceback.
- **Fixes:** `e2ef102e`, each with a test in
  `tests/work/test_review_findings.py` written first and seen to fail. The
  skipped init-refusal test in `test_config_edit_writers.py` was ported.
- **Round 3** (confirming, over `e2ef102e`): every round-1 item fixed,
  except that the comment fix introduced **S1**: on volumes without hard
  links (FAT, exFAT, SMB) every comment and every `--reason` note failed.
  **S2**: a title or assignee with an undecodable byte was saved, and `show`
  then failed on that item. NOT DONE.
- **Fixes after the owner's decision:** `8bf085a3`. A fallback to an
  exclusive create when `link` is not supported, cleaning up after a failed
  write; `check_encodable` in the model, applied by `validate_changes` to the
  title and assignee in both backends. Note N1 was folded in too: init keeps a
  store holding a hidden file with content, and lists at most five names. The
  failed-write test was itself found not to test the fallback (a mutation that
  removed the cleanup stayed green); it was rewritten, and the same mutation
  then made it fail.
- **Tests run now:** the whole suite in parallel, 2,646 passed and 130
  skipped. Before the review fixes, the bare serial run (2,615 passed, 131
  skipped) and the throwaway copy with no project config (the same) were both
  green; the fixes added tests and changed no skip except the ported one.

## TCW-69's items owed to this one

- A stage the table does not know reads as no stage: `list` shows the item,
  `show` prints an empty stage, and `advance` refuses with exit 3, not a
  usage error.
- The contract test settles `create(..., request="")` as no request.
- The layout is the backend's own, built from `config.enabled` and
  `backend.external_stages`.

## Definition of Done

- **Tests pass:** yes, as above. **TCW-69's AC 20 (the full suite) and the
  epic-end run stay open** at the owner's instruction for this epic.
- **Docs synced:** the changelog and release-notes entries are written. The
  README, guides, skills and configure references are deferred to TCW-74 and
  TCW-75 by the spec (Design 14); the documentation allowance lists exactly
  what they may still name.
- **Capabilities reconciled:** on the branch, by hand (Task 12), checked with
  the released 2.8.1 `tcw validate`.
- **Reviewed:** as above.
- **GitHub issue:** none; the item came from Jira (TCW-70).

## Deferred to other items

- **TCW-71:** re-read `fs_backend.py` and `open.py` against TCW-71's spec
  first, and fix anything outside its four seams as part of TCW-71.
- **TCW-73:**
  - `tcw validate` maps a `BackendError` from another project — a present
    project whose config is 2.x or invalid — to `unresolved:`, which never
    fails. The spec defines `unresolved` only for an unreachable project.
    Decide it in TCW-73's pass over findings.
  - `open.py`'s refusals mix quoting styles ('q' and `q`); settle it with
    TCW-73's message-exemption test.
  - `BrokenPipeError` (stdout piped into `head`) is now one line and exit 1;
    the usual behavior is to exit quietly.
  - `_Unreadable` and `Unreadable` in `fs_backend.py` are two copies of one
    shape.
- **End of the epic:** the Playwright hand run and the `shell-system-dark`
  and `shell-explicit-light` snapshot refresh (Task 9).

## Closeout choices

- **Merge route:** `epic/tcw-3.0` fast-forwarded to the branch, as the owner
  chose for the whole epic; `main` receives 3.0 when the epic finishes.
- **Completion:** `tcw work complete` from the primary checkout on `main`,
  whose `tcw` is the released 2.8.1 (no code under change there), which also
  syncs the Jira ticket, as for TCW-69.
