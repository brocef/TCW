# Stop an item reaching implement without a spec and plan, and say how to plan an item started too early

## What happened

On 2026-09-16 the coordinating session for
`2026-09-16-make-every-procedural-skill-in-tcw-overridable-by-the-project-that-uses-it`
ran `tcw work start <child> --worktree` on two children that had
`initial-request.md` but no `spec.md` or `plan.md`. Then:

- `tcw work stage gate spec <child>` and `gate plan <child>` refused:
  "'spec' is not legal for an item in 'active'; it runs in backlog". No verb
  moves an item back to `backlog`, so neither gate could ever pass again short of
  hand-editing the store. The plan stage's bound pre-check
  (`python scripts/require_artifact.py spec`) could then only be run by hand.
- `tcw work stage gate implement <child>` **passed**, with no spec or plan.
- `tcw work start` itself printed nothing about the missing plan, although
  `transitions.md` describes `plan.md` being present as a check on `start`.

The requester chose to proceed with the items active and write spec and plan
anyway; both children record the refusal in their notes.

## What is wanted

Decide and fix, in whichever layer is right:

1. **`start` on an item with no `plan.md`** — at least a visible warning naming
   the missing artifacts and that `spec`/`plan` gates will refuse once it moves;
   possibly a refusal without `--force`.
2. **The `implement` gate on an item with no `plan.md`** — this repo binds no
   artifact check to `implement` (`tcw work lifecycle`); either TCW's default
   gate should check it, or this repo's `tcw-config.yaml` should bind
   `scripts/require_artifact.py plan` there as it binds `spec` to `plan`.
3. **Recovery** — what an agent should do with an item started before planning:
   whether `spec`/`plan` may run in `active`, or a documented way back to
   `backlog`.

## Origin

Found while implementing the epic above; reported by the child 1 subagent and
confirmed by the coordinating session. The requester asked for it to be filed
as a work item on 2026-09-16.
