# Point a refused drop of an active or in-review item to the discard route

An agent working on the proposit-app project could not find a way to discard an
active work item. `tcw work drop` refuses with "cannot drop from active (only
backlog)". There is no `discard` subcommand, but the work skill's list of
transitions names `discard` as if there were one. The agent gave up and moved the
Jira ticket to "Won't Do" by hand, which left TCW and the tracker out of step.

The route already exists: `tcw work complete <slug> --resolution wontfix|duplicate|superseded --confirm`.
Nothing on the path the agent took points to it. The fix: make `drop`'s refusal
for a non-backlog item name that command, and say so where the skill lists
`discard`. Also check the status before the `--confirm` gate, so the agent isn't
told to re-run with `--confirm` only to be refused a second time.

## Origin

Reported by the proposit-app agent on 2026-09-21, while cleaning up after the
real-Jira check of the Triage fix. Bug.

## References

- tcw/work/cli.py `_drop` — where the refusal is printed
- tcw/store/base.py `drop` — raises "cannot drop from … (only backlog)"
- skills/work/SKILL.md line 40 and skills/work/references/transitions.md "discard" — the wording that suggests a verb
