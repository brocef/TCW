# Outcome — Make every procedural skill in TCW overridable by the project that uses it

Aggregate status of the six initiative children, all completed on 2026-09-16
and merged to `main` (each child's own documents are retained in the commit its
`tcw work show` names).

| # | Child | Result |
| --- | --- | --- |
| 1 | `2026-09-16-state-the-two-rules-for-an-overridable-skill-and-mark-every-skill-with-its-verdict` | `skills/README.md` states the two rules and a verdict for every shipped skill, reference and agent; `dynamic_skill` on all 16 skills with its test |
| 2 | `2026-09-16-compose-a-procedure-s-instructions-from-project-bindings-the-way-a-stage-s-are-composed` | `tcw work procedure prompt <id> [slug]`, `work.procedures`, ten ids with shipped defaults, validation, two new capabilities |
| 3 | `2026-09-16-stop-tcw-extras-autonomous-work-mandating-a-specific-advisor-closeout-and-version-policy` | the autonomous-work skill names no advisor; Codex, Opus, closeout and version policy live in the `unattended-work` default |
| 4 | `2026-09-16-compose-the-five-tcw-work-procedure-documents-from-project-bindings` | the five procedure documents keep only their fixed rules; `tcw-backlog-auditor` reads its checks from the command |
| 5 | `2026-09-16-compose-tcw-extras-triage-issues-and-tcw-post-mortem-from-project-bindings` | triage and post-mortem compose; `gh` stays a declared requirement of the default; the post-mortem agent reads the procedure |
| 6 | `2026-09-16-compose-documentation-sync-and-tcw-work-create-from-project-bindings` | documentation-sync and work-create compose; plus, at the requester's decision, the command prints TCW's default outside a TCW node and `stage-verify.md` reaches the version cut through the procedure |

## Integration

- The four conversion children changed `tests/test_shipped_procedures.py` in
  four shapes; they were unified into one `Composes` marker during merging.
- Upstream's skill and agent prefix rename (merged into local `main` by another
  session as `d08f7d31`) conflicted with the epic's edits; content was kept and
  the new names applied. Child 6's capability delta was repointed from
  `skills/tcw-work-create` to `skills/work-create`.

## Tests

- Full suite on child 6's branch before the rename merge: `3505 passed`.
- After the rename merge: targeted skill, procedure, parity and manifest tests
  `269 passed`; the full suite was stopped at the requester's instruction and
  not re-run. The other session reported `3622 passed` on `d08f7d31`.

## What the plan got wrong

- Children were started into worktrees before their spec and plan, so the spec
  and plan gates refused; filed as
  `2026-09-16-stop-an-item-reaching-implement-without-a-spec-and-plan-and-say-how-to-plan-an-item-started-too-early`.
- The routing blocker was recorded as free text because it had already
  resolved; filed as
  `2026-09-16-record-a-blocker-naming-a-resolved-item-as-a-slug-not-as-free-text`.
- File ownership missed `agents/tcw-backlog-auditor.md` and wrongly gave
  `find-overlap.md` to child 6; corrected after child 1.
- Criterion 8 had to exclude `tcw/work/procedures/` and skill frontmatter.
- Planning to let each child choose its own drift-test shape guaranteed merge
  conflicts; one shape should have been fixed in child 2.
