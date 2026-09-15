# Plan — Give every TCW skill a taxonomy Feature and exactly one capability

Implements `spec.md`. "AC n" refers to its acceptance criteria. The larger plan
this replaces is in git history at commit `9fbaa25a`.

## Before starting

- **Blocked.** This item waits for two others, and `tcw work start` refuses until
  both complete:
  - `2026-09-14-restructure-tcw-s-skills-setup-and-configure-skills-command-and-extras-skills-and-no-slash-commands`;
  - `2026-09-14-delete-a-capability-with-tcw-capabilities-rm`.
- **Read the delete item's spec and outcome.** Note the exact form it defines for
  declaring a deleted capability in `capabilities.yaml`. Task 3 uses it.
- **Record `<base>`** in `outcome.md`: the last commit before this item's first
  implementation commit. AC 9 reads the deleted bodies as they stood there.
- **Check the naming convention first.** Confirm that `ls skills` lists the fifteen
  skills in the spec's table, and that no existing taxonomy slug ends in `-skill`
  (`tcw taxonomy list`). If either differs, stop and return to `spec`.
- **Every commit leaves bare `pytest` green, and `tcw validate` exits 0.**

## Tasks

### Task 1 — Register the `skill` term and fifteen Features (D1)

**Commands**

- `tcw taxonomy add "Skill" -s skill "<definition from the spec>"`
- One per row of the spec's Taxonomy table:
  `tcw taxonomy add "<Feature name>" --kind feature -s <slug> --vocab <term> [--vocab <term> …] "<one-sentence description of the interaction area>"`
- Edit `relatesTo` in each listed Feature's `meta.yaml`, as the table gives.
  Find each file with `tcw taxonomy path`.
- `tcw taxonomy check`

**Proof**

- ACs 1–3.
- The commit touches only the taxonomy store.

### Task 2 — Write the fifteen capabilities and delete the nine they replace (D2)

**For every new capability**

- `tcw capabilities add skills/<s> "<name in the spec's form>" --status Supported`
- `tcw capabilities set skills/<s> --field "Feature=<s>-skill" --field "Subject=skill"`
- Write the body in `description.md` (find it with `tcw capabilities path`), in
  "As a user or agent, I …" form.
- Build each folded body from the deleted bodies as they stood at `<base>`
  (`git show <base>:docs/capabilities/<path>/description.md`). Reword every
  removed name:
  - slash commands become "ask the `<skill>` skill";
  - old skill names become the new ones.

**Commits, one per group in D2, each green**

1. `skills/tcw-work`, `skills/tcw-commands-plan-work`,
   `skills/tcw-commands-drive-work-to-completion`. Then run `tcw capabilities rm`
   on `work/consolidate-plans`, `work/search-the-work-items`,
   `work/audit-work-backlog` and `plugin/work-lifecycle`.
2. `skills/tcw-extras-report`, `skills/tcw-post-mortem`,
   `skills/tcw-extras-triage-issues`. Then `rm` `plugin/report-an-issue-upstream`,
   `plugin/run-a-post-mortem` and `plugin/triage-github-issues`. Change
   `docs/capabilities/work/complete-a-work-item/description.md:20`'s link to
   `tcw://C/skills/tcw-extras-triage-issues`.
3. `skills/tcw-setup`. Then `rm` `taxonomy/bootstrap-the-taxonomy` and
   `capabilities/bootstrap-the-capabilities`.
4. The remaining eight: `skills/tcw-configure`, `skills/tcw-taxonomy`,
   `skills/tcw-capabilities`, `skills/documentation-sync`, `skills/tcw-work-stage`,
   `skills/tcw-commands-verify-work`, `skills/tcw-commands-process-inbox`,
   `skills/tcw-extras-autonomous-work`.

**After each commit**

- `tcw capabilities check` prints `capabilities OK`.
- `tcw validate` exits 0.

**Proof:** ACs 4–8.

### Task 3 — This item's `capabilities.yaml` (D2)

- In the item's folder, write `capabilities.yaml`:
  - `new:` lists the fifteen `skills/*` paths;
  - `changed:` lists `work/complete-a-work-item`;
  - the nine deletions are recorded in the form the delete item defined.
- Commit it on its own, after task 2's last commit, so every path it names already
  matches the ledger.

**Proof:** `tcw work show <slug>` reads it without error.

### Task 4 — Note on the backlog-audit item (D3)

Add one line under `## Notes` in
`2026-09-01-fan-the-backlog-audit-out-across-every-connected-work-root`'s body
document. It says that `work/audit-work-backlog` was folded into `skills/tcw-work`,
so its capability delta should name that path.

**Proof:** committed.

## Documentation Sync

Evaluated with `tcw work docs`:

- **`docs/changelogs/upcoming.md` [Any-Code-Change] — fires as a ledger change.**
  Task 5 adds, under "Changed":
  - the `skill` term and fifteen Features;
  - one `skills/*` capability per skill;
  - the nine capability paths deleted, and which successor each folded into.
- **`docs/release-notes/upcoming.md` [Public-API] — fires.** Anyone who links to a
  capability path needs to know the nine old paths are gone. Task 6 adds one plain
  sentence listing the new `skills/` namespace.
- **`README.md` [Public-API] — expected not to fire.** The README doesn't list
  capability paths. Re-check at the documentation pass.
- **`skills/<component>/SKILL.md` [Skill-Driven-Component] — does not fire.** No
  CLI changes.
- **`skills/tcw-configure/references/<document>.md` [Configuration-Key-Change] —
  does not fire.** No configuration changes.

## Verification

1. **ACs 1–8 and 10.** Run the commands exactly as the spec writes them, and
   record the output in `outcome.md`.
   - AC 2 as a loop over the table's Feature paths.
   - AC 4 as a loop over `ls skills`.
2. **AC 6:**

   ```sh
   grep -rl -- '-skill' $(tcw capabilities path) | grep -v '/skills/'
   ```

   It must print nothing.
3. **AC 9, by reading.** For each deleted capability, read its body at `<base>`
   against its successor's body. List in `outcome.md` each behavior and the
   successor sentence that carries it.

## Notes

- **Traceability.**
  - ACs 1–3 → task 1.
  - ACs 4–8 → task 2.
  - AC 9 → task 2 and Verification.
  - AC 10 → every task.
  - Task 3 carries D2's `capabilities.yaml`.
  - Task 4 carries D3.
- **Why a single session.** Every task writes the same two stores, so the tasks run
  in order in one session.
