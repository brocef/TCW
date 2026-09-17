# Outcome: Point open work items at the renamed skills

## What shipped

- **Task 1 — rewrites** — `79282d2a`. 34 lines in 17 files under
  `docs/work/backlog/`, exactly the plan's Task 1 rows. Each changes the skill
  name only, except where a bare new name would read as an ordinary word:
  "documented in the `configure` skill" (three items), "the `setup` and
  `configure` skills are new", "over the `taxonomy` and `capabilities` skills",
  "The `setup` skill never says", "route into the `setup` skill", "fires for the
  `work` skill". The one kind-2 instance —
  `2026-09-01-fan-the-backlog-audit-out-across-every-connected-work-root/intake.md:97`
  — now says to declare `skills/work` under `changed:`.
- **Task 2 — left alone** — the 16 lines the plan lists, with its reasons.
- **Documentation Sync** — no entry fires; only `docs/work/` changed.

## Evidence

- Criterion 1: the intake's `git grep`, over `docs/work/{backlog,active,blocked,review,inbox}`
  and outside this item, returns 16 lines: `…separate-the-agent-plugin…/spec.md:16`,
  `…descend-through-a-storeless-routing-node…/intake.md:16`, twelve lines of
  `…fill-codex-gaps…/intake.md`, `…make-the-capability-gate…/intake.md:26`,
  `…add-a-rename-verb…/intake.md:20` — Task 2's rows exactly.
- Criterion 2: `git diff --stat` lists 17 files, all under `docs/work/backlog/`;
  the two `intake.md` files among them belong to items with no
  `initial-request.md`.
- Criterion 3: no removed line differs only in `tcw-config`, `tcw-cli` or a slug;
  slugs containing `tcw-` (`…single-tcw-setup-skill`, `…restructure-tcw-s-skills…`)
  are intact on every changed line.
- Criterion 4: `tcw validate` → `validate OK`.

## What the plan or spec got wrong

- **The spec's first count was wrong** (49 in 20 files); it was corrected to 50 in
  21 before committing, by counting per file.
- **One stale path has no current name to point at.**
  `…separate-the-agent-plugin…/spec.md:16` names
  `skills/tcw-work/references/lifecycle/default/README.md`, which was deleted after
  the rename. The plan left it rather than invent a path; the note it sits in already
  says that item's spec must be re-run.
- **Line numbers inside the rewritten text are not re-checked.** For example,
  `skills/work/references/hooks.md:83` is cited by the missing-skill-caveat item
  while "Two limits worth knowing" is now at line 67. That is other staleness, which
  the spec puts out of scope.
