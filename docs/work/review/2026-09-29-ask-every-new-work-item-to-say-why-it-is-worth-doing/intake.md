# Ask every new work item to say why it is worth doing

Extend this project's `create-work` procedure (the text `tcw work procedure
prompt create-work` prints, which the `work-create` skill injects) so that
every item or inbox entry it creates carries a section justifying the work.

## Why

- **Without it:** items record what to change and where the idea came from,
  but not the case for doing it. Whoever triages the backlog later has to
  reconstruct the value of each item, or guess it, and low-value items get
  the same weight as important ones.
- **With it:** each item states what goes wrong if it is skipped and what
  improves if it is done, so it can be prioritized or dropped on its merits.
- **Cost and risk:** one `work.procedures` binding in `tcw-config.yaml` and
  one Markdown file; TCW's own text is kept (`builtin: true`). The only risk
  is longer intake notes.

## Origin

Requested by the user in chat on 2026-09-29, during the bug-fix session.

## References

- `skills/work-create/SKILL.md` — where the procedure is injected.
- `skills/configure/references/work.md` ("Procedures: `work.procedures`") —
  how a project adds its own text to a procedure.
