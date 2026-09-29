# Tidy three tracker messages left by the binding hardening review

Five small defects in tracker messages and response handling, left by the review
and verification of `2026-09-15-harden-tracker-binding-reads-and-writes-and-jira-response-parsing`:

1. `tcw work complete`'s merge-back hint reads staged files with
   `git diff --cached --name-only`, whose paths are escaped for non-ASCII names
   (`core.quotePath`) and relative to the node under `diff.relative=true`, so
   the comparison with the item's own `tracker.yaml` misses.
2. A `create_issue` answer that is not a mapping raises the generic "unexpected
   shape" error, losing the "It may exist; look for a ticket titled…" warning,
   although the ticket may have been made.
3. When creation succeeds and only the binding fails, the filing hook prints the
   placeholder "(creating it did not succeed)": `_tracker_link` never adds a
   reason.
4. Values inside a Jira response are not type-checked: `{"status": {"name": 5}}`
   crashes `tcw work tracker show` with `AttributeError: 'int' object has no
   attribute 'strip'`.
5. Strict `drop` of an item whose `tracker.yaml` cannot be read says it "is, or
   was, bound to a ticket"; it should say the binding cannot be read.

Wanted: each message says what actually happened, and no response shape crashes
a command.

## Notes

- Unattended run (2026-09-29); from `intake.md`. Reference material: asked;
  none beyond the intake's.
- The title says three; the intake grew to five at verify. All five are in scope.

## References

- `intake.md` in this folder.
