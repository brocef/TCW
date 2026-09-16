# Refined outcome — State the two rules for an overridable skill and mark every skill with its verdict

## Decision

**Accepted** by the requester on 2026-09-16, as delivered, including every
judgment call listed in `outcome.md` and presented at verify:

1. The rules and verdicts live in `skills/README.md`, reached from the comment on
   each `dynamic_skill` line.
2. `dynamic_skill` is a top-level frontmatter key, not under `metadata:`.
3. `tcw-work-stage` is `true`, verdict "composes already".
4. The seven stage documents and `tcw-work`'s six other references are fixed
   under Rule 1.
5. `tcw-setup`'s `taxonomy.md` and `capabilities.md` are fixed.
6. `tcw-work-create/references/find-overlap.md` is fixed and does not travel with
   its skill.
7. The three agents get a fifth verdict, "fixed (accelerator)".
8. `tcw validate` does not report the key; the test alone guards it.
9. `true` records intent until children 3–6 convert the skills.

## Evidence

Checked by the coordinating session on 2026-09-16, in the worktree:

- `pytest -q tests/test_dynamic_skill_marker.py tests/test_plugin_manifests.py tests/test_skill_lifecycle_parity.py`
  → `191 passed`.
- `claude plugin validate --strict skills` → `Validation passed`.
- `git diff --stat main -- agents 'skills/*/references'` → empty (criterion 5).
- The 16 `SKILL.md` diffs are one added frontmatter line each: 10 `false`, 6
  `true`, matching the requester's classification (criteria 3 and 4).
- Full suite, bare, reported by the implementing subagent on `e77771f2`:
  `3435 passed in 1451.08s`. Later commits touch only the changelog and this
  item's documents; the skill, manifest and changelog tests were re-run after
  them (`206 passed`). Not re-run in full by the coordinating session.

## Capability reconciliation

None to reconcile: `spec.md` declares no capability change.

## Follow-ups

- The epic's plan and two sibling briefs are corrected on `main` to match these
  verdicts: child 4 (`2026-09-16-compose-the-five-tcw-work-procedure-documents-from-project-bindings`)
  now owns `agents/tcw-backlog-auditor.md`; child 6
  (`2026-09-16-compose-documentation-sync-and-tcw-work-create-from-project-bindings`)
  no longer converts `references/find-overlap.md`.
- Filed from defects found while working this item:
  `2026-09-16-stop-an-item-reaching-implement-without-a-spec-and-plan-and-say-how-to-plan-an-item-started-too-early`
  and `2026-09-16-record-a-blocker-naming-a-resolved-item-as-a-slug-not-as-free-text`.

## Closeout

- **Merge route:** `tcw work complete` merges `work/<slug>` into `main` locally.
  Not pushed.
- **Documentation:** `docs/changelogs/upcoming.md` updated in `db5f4251`. No
  other documentation entry fires (no CLI, configuration or user-facing change).
- **Version:** none cut. The epic's plan accumulates every child's entries in
  `upcoming.md` and cuts no version per child.
- **GitHub issue:** none; the item did not come from one.
