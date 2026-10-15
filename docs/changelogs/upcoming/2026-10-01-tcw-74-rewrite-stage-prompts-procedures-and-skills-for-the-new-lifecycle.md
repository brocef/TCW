## Added

- Built-in stage prompts `tcw/work/prompts/review.md` and `qa.md`, and the
  `pause-work` procedure (TCW-74).
- Backend passages in packaged prompts and procedures, filtered to the
  project's backend when composed.
- A line that starts with `<!--` and mentions `backend` but is neither
  passage marker exactly is an error naming the line.
- `agents/reviewer.md`, which reads `tcw work stage prompt review` and
  recommends a verdict.
- `skills/setup/references/jira.md`: configuring a project's Jira backend
  (`backend: jira`); it moves no existing file items.
- Tests: `tests/test_shipped_text.py` (no git words, no 2.x vocabulary, every
  command named exists, the shipped file set) with the shared vocabulary table
  `tests/doc_vocabulary.py`; `tests/test_skill_flow.py` rewritten as the 3.0
  product flow.

## Changed

- Every packaged stage prompt rewritten for the eight 3.0 stages, with a
  header naming `tcw work advance <slug> --dry-run` and, for a stage that moves
  the item on, a closing line naming `tcw work advance`; no prompt names git.
- `PROCEDURE_IDS` is `unattended-work`, `triage-issues`, `documentation-sync`,
  `create-work`, `audit-backlog`, `search`, `pause-work`.
  Configuring a removed id is a config error that says where its text went.
- The `work`, `capabilities`, `setup`, `taxonomy`, `work-create`,
  `documentation-sync`, `extras-*` and `commands-*` skills rewritten for the
  3.0 surface; `skills/README.md` re-sorted; `agents/backlog-auditor.md`
  reads `tcw work procedure audit-backlog`.
- The eval harness (`evals/`) seeds and grades 3.0 projects, with review and
  two qa cases.
- `tests/doc_allowance.py` loses the entries only TCW-74's files named and
  gains `REFUSED_VALUES` for `tcw work procedure prompt`.

## Removed

- Procedures `post-mortem`, `consolidate-plans`, `decompose`, `delegation`;
  `tcw/work/prompts/verify.md`.
- Skills `work-stage`, `commands-verify-work`, `post-mortem`; agents
  `verifier` and `post-mortem`; `skills/work/references/lifecycle/`,
  `transitions.md`, `hooks.md`, `epic-deltas.md`, `cross-node-deltas.md` and
  `skills/work/references/procedures/`.
- `tests/test_skill_lifecycle_parity.py`; the exemption for `Missing`
  capability records in `tests/test_documented_cli_surface.py`.
