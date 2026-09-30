# Suggest what was meant when a subcommand or stage name is wrong

From GitHub issues [#69](https://github.com/brocef/TCW/issues/69) and
[#71](https://github.com/brocef/TCW/issues/71) (point 2 only), both filed
2026-09-29 by @brocef, preserved as this item's `intake.md`.

## The request

When a word typed on the command line is wrong, `tcw` lists every valid choice
but never says which one was meant. Three real cases, all on tcw 2.6.4:

1. **A subcommand given at the wrong level.** `tcw tracker status` fails
   listing the top-level groups; the agent meant `tcw work tracker show`.
   `tracker` exists, one level down. The agent concluded the CLI could not show
   a ticket's sync state and went to Jira directly.
2. **A likely synonym.** `tcw work status <slug>` fails listing every `work`
   verb; the agent meant `tcw work show`.
3. **An artifact name where a stage name is expected.**
   `tcw work stage gate refined-outcome <slug>` fails with "unknown stage"; the
   artifact `refined-outcome.md` is written by the `verify` stage, and nothing
   says so.

Asked for:

- When the mistyped word is a subcommand somewhere else in the tree, suggest
  it ("did you mean `tcw work tracker`?").
- A short alias or suggestion for `status` → `show`.
- When the word given as a stage is the name of an artifact, name the stage
  that writes it ("`refined-outcome.md` is written in the verify stage").

## Out of scope

- #71 point 1 (planning gates on an item already started) and its follow-up
  comment about `start` letting an item past them: tracked in
  `2026-09-29-let-a-started-item-still-pass-its-planning-gates-or-stop-start-from-letting-it-past-them`.

## Notes

- Written autonomously (an `/autonomous-work` run); there was no requester to
  ask. Reference material: the two issues; nothing else was offered.

## References

- `2026-09-29-let-a-started-item-still-pass-its-planning-gates-or-stop-start-from-letting-it-past-them`
  — takes #71's other point; the two touch the same `stage gate` refusals.
