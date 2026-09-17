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
- **Review fixes** — `3d5d81b7`. Three lines the intake's expression cannot match:
  `…record-a-work-item-s-branch…/plan.md:288-289` ("Neither does the
  `skills/work-stage/` skill"), and `…run-the-eval-harness…/initial-request.md:125`
  and `:140` (`commands-*`). The spec gains rules 3 and 4.
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
  `skills/tcw-work/references/lifecycle/default/README.md`, which was deleted (commit `92e478dc`)
  shortly before the rename merged. The plan left it rather than invent a path; the note it sits in already
  says that item's spec must be re-run.
- **Line numbers inside the rewritten text are not re-checked.** For example,
  `skills/work/references/hooks.md:83` is cited by the missing-skill-caveat item
  while "Two limits worth knowing" is now at line 67. That is other staleness, which
  the spec puts out of scope.

- **The intake's expression misses wildcard forms.** `tcw-commands-*` and
  `skills/tcw-work-stage-*/` have a `*` or `-` after the name, so the first pass
  missed three instructing lines; the verifier and the reviewer both found them.
  Fixed in `3d5d81b7`. The only remaining wildcard match is
  `…refine-the-plugin-skills…/initial-request.md:78`'s list of removed skills.

## Autonomous decisions

Run unattended under `autonomous-work`; these replace the human checkpoints.

- **Should `intake.md` be rewritten when an `initial-request.md` also exists?**
  Codex: no — it is a verbatim arrival record once superseded; rewrite only when it
  is the only body. Opus: the same, with the caution to check the instruction was
  carried into `initial-request.md` (it was, for both items). Chose to leave it;
  written into the spec as rule 5.
- **Should a verbatim quoted GitHub issue with an old name be rewritten?** Codex and
  Opus: leave it; Opus suggested an optional note outside the quote. Left it, no
  note — the current file is easy to find, and adding prose is outside a rename.
- **Review/verifier findings accepted:** the two `tcw-commands-*` lines and the
  `tcw-work-stage-*` line (all rewritten); the README-deletion timing in this outcome
  (corrected).
- **Review findings rejected, as separate changes:** `…record-a-time-of-day…/plan.md:248`
  claims `skills/work/references/procedures/search.md:66` still shows
  `started: <timestamp>`, but that file is 10 lines and the text is gone; and the
  separate-plugin spec's bullet about a link out of the plugin folder is moot. Both
  are staleness other than the rename, which the spec puts out of scope; the first
  item's plan will be re-read when it starts, and the second item's spec is already
  flagged to be re-run.
- **Verify decision:** accept. `tcw-verifier` reported all four criteria met; the
  three added rewrites were checked by re-running both searches after `3d5d81b7`.
