# Fill the Codex gaps in the setup and stage skills, and give each skill one capability

## What is wanted

What the plugin's skills and their capability documents tell a reader should be
complete under Codex and said in one place.

1. **The `setup` skill never says how to run the install under Codex.**
   `skills/setup/references/install.md` says "Under Codex there is no hook, and you
   run it", without the path to `scripts/session_bootstrap.sh` or its two arguments —
   although the script's own header says those arguments exist for exactly this case.
   `README.md` says the skill "runs the same install script".
2. **`work-stage`'s manual fallback writes `<plugin>` for the plugin folder** with no
   instruction for finding that folder under Codex.
3. **One skill, two capabilities.** `work/run-a-lifecycle-stage` still has two paragraphs
   about the `work-stage` skill, which now has its own capability,
   `skills/work-stage`. Wanted: what those paragraphs say that the skill's capability
   does not is moved there, leaving `work/run-a-lifecycle-stage` about the two CLI
   commands.
4. **The issue-closing rules are written twice**, in `work/complete-a-work-item` and
   `skills/extras-triage-issues`. Wanted: one home, linked from the other.

## Out of scope

- Parts 1 and 5 of the skill restructure guards and §3 of the capability overlaps (test
  coverage) — tracked in
  `2026-09-15-check-the-whole-tracked-tree-ledgers-included-for-removed-skill-names`.
- Parts 2 and 6 of the guards (eval coverage) — tracked in
  `2026-09-15-eval-runs-under-this-checkout-grade-and-behave-wrongly`.

## Notes

- Merged at triage from two entries, because both are about what the skills and their
  capabilities tell a reader; both kept verbatim in `intake.md`.
- Part 1 predates the skill restructure; the text moved unchanged from `tcw-plugin`.
- Part 3 is the unmet half of the per-skill ledger item's second goal ("no second
  capability describes the same skill").
- Checked at triage on `main`: all four still present.
- Reference material: asked; none provided.

## References

- `scripts/session_bootstrap.sh` — its header documents the `[plugin-root]` and
  `[sentinel-path]` arguments the install reference should name.
