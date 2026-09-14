# Make eval checks measure what the agent did: working-tree file changes, tool-call routing, and named fixture variants

## What is being asked for

This item was split out of
`2026-09-14-consolidate-the-setup-skills-into-a-single-tcw-setup-skill` on
2026-09-14, at the requester's direction, after that item's third review round.
It carries that item's eval-harness work, which has no dependency on the skill
restructure and can start now.

Three changes to the eval harness under `evals/`:

1. **`files_changed_exactly` must measure what the agent changed.** Today it
   compares the last two commits, so it measures whether the agent committed.
   The requester decided (revision note 11 of the parent) to fix it rather than
   route around it, even though existing case B10 depends on it.
2. **A way to check which skill documents an agent actually opened.** The
   existing transcript checks search every piece of transcript text, including
   skill text the agent merely loaded, so a routing check can pass or fail for
   the wrong reason. The parent's second review found this.
3. **Fixture variants by name, including a `bare` repository** that does not use
   TCW yet, selectable per case. The parent's requester accepted an eval case
   for setting TCW up in a fresh repository (revision note 7), and that case
   needs this fixture.

The eval cases that *use* 2 and 3 belong to
`2026-09-14-restructure-tcw-s-skills-setup-and-configure-skills-command-and-extras-skills-and-no-slash-commands`,
which is blocked by this item.

## Notes

- Constraints inherited from the parent: running the paid eval harness is not
  part of this work; every assertion is mutation-checked (deliberately broken to
  confirm it fails) before it is trusted, as `CLAUDE.md` § Measuring the skill
  layer requires.
- Reference material: the parent item's request and reviews; nothing else
  provided.

## References

- `2026-09-14-consolidate-the-setup-skills-into-a-single-tcw-setup-skill` —
  `spec.md` D6 and `plan.md` tasks 1–3 as of commit `9fbaa25a`, which this
  item's spec and plan are carved from.
- `2026-09-11-run-the-eval-harness-and-act-on-what-it-finds` — the item that
  will run the harness these changes affect.
