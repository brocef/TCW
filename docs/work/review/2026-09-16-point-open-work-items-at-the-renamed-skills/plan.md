# Plan: Point open work items at the renamed skills

One task per verdict class, applied by exact line edits on `main`. Line numbers
are from the grep run on 2026-09-17 (50 matches, 21 files); re-run it before
editing and stop if the roster changed.

Paths are relative to `docs/work/backlog/`. Every rewritten target was confirmed
to exist: `skills/{work,setup,configure,capabilities,work-stage,extras-triage-issues,commands-process-inbox}`,
`skills/work/references/{hooks,transitions,commands}.md`,
`skills/work/references/procedures/search.md`,
`skills/setup/references/install.md`, `skills/configure/references/{work,tracker}.md`,
and `docs/capabilities/skills/{work,work-stage,extras-triage-issues}`.

## Task 1 — rewrite (instructions)

Each rewrite changes the skill name only (`tcw-X` → `X`), plus "the `X` skill"
where a bare name would read as an ordinary word.

| File | Lines | Why it instructs |
| --- | --- | --- |
| `2026-08-12-separate-the-agent-plugin-from-the-python-cli-source/initial-request.md` | 84 | audit note telling the planner where the install text now lives |
| `…separate-the-agent-plugin…/plan.md` | 155 | task naming a constant to modify |
| `…separate-the-agent-plugin…/spec.md` | 8, 26 | audit note telling the re-spec which skill to name |
| `2026-08-18-report-the-missing-skill-caveat…/initial-request.md` | 10, 46, 63 | cites the file to change and where the text moved |
| `2026-08-18-serve-version-cut-instructions…/initial-request.md` | 57 | where new key documentation goes |
| `2026-08-31-nothing-verifies-that-a-changed-capability…/initial-request.md` | 6 | cites the file it quotes |
| `2026-09-01-fan-the-backlog-audit…/intake.md` (only body) | 97 | capability path to declare under `changed:` (kind 2) |
| `2026-09-10-let-a-node-declare-its-own-work-item-state-fields/initial-request.md` | 84 | where new key documentation goes |
| `2026-09-10-record-a-work-item-s-branch…/initial-request.md` | 51 | where new key documentation goes |
| `…record-a-work-item-s-branch…/plan.md` | 278, 287 | files to modify |
| `2026-09-11-refine-the-plugin-skills…/initial-request.md` | 45, 78 | the file to change; the current skill set to refine (the removed names on 78 stay) |
| `2026-09-11-run-the-eval-harness…/initial-request.md` | 120, 140 | current eval case skill names |
| `2026-09-15-eval-runs-under-this-checkout…/intake.md` (only body) | 70-75 | the assertion strings to add |
| `2026-09-15-fill-codex-gaps…/initial-request.md` | 8, 9, 13, 16, 17, 21 | files and capabilities to change |
| `2026-09-15-make-the-capability-gate-honor-a-configured-ledger/initial-request.md` | 29 | the rule the fix must follow |
| `2026-09-15-record-a-time-of-day…/plan.md` | 246, 248, 250 | files to modify |
| `2026-09-15-show-the-tracker-s-untriaged-tickets…/plan.md` | 205, 206 | files to modify |

On line 78 of the refine item, `commands-*` and `extras-*` are rewritten with
`setup`/`configure` so the sentence names one consistent set, although the
intake's regular expression does not match a `*`.

## Task 2 — leave (records), with reasons

| File | Lines | Reason |
| --- | --- | --- |
| `…separate-the-agent-plugin…/spec.md` | 16 | names `…/lifecycle/default/README.md`, which was deleted after the rename, so no current path exists to point at; the note above it already says to re-run the spec stage |
| `2026-09-09-descend-through-a-storeless-routing-node…/intake.md` | 16 | verbatim quote of GitHub issue text (`>`-prefixed) |
| `2026-09-15-fill-codex-gaps…/intake.md` | all 12 | arrival record; `initial-request.md` supersedes it |
| `2026-09-15-make-the-capability-gate-honor-a-configured-ledger/intake.md` | 26 | arrival record; `initial-request.md` supersedes it and carries the same rule (line 29) |
| `2026-09-16-add-a-rename-verb…/intake.md` | 20 | states what an id became — a record of the rename |

## Task 3 — check

- Re-run the grep: the remaining lines are exactly Task 2's rows (criterion 1).
- `git diff --stat` and `git diff -U0` for criteria 2-3.
- `tcw validate` (criterion 4).

## Documentation Sync

No entry fires: only `docs/work/` changes. No changelog line — no code, and
nothing a user of TCW sees.

## Verification

The suite does not read `docs/work/backlog/` prose; verification is the grep and a
reviewer reading Task 2's rows against the files.
