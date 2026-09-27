# Outcome: strict gate refuses unfollowable moves; import nests children

## What shipped

- **Code** — `7744ce9e`: `authorize` (`tcw/tracker/sync.py`) takes `move` and
  `resolution` and asks `assess_move`, with the configured transition name, as
  `deliver` does; a `submit`, `rework` or `complete` whose workflow offers no
  transition, or several and no name, is refused before the item moves. Skipped
  for an unmapped target and while another open part holds the ticket.
  `_strict_refusal` passes the move and resolution. `tracker import` takes
  `--parent` (checked before the claim) and `--initiative`.
- **Review fold-in** — `97f657bb`, `c301b249`: a legacy `catch-up` binding with
  more than one rung to climb is walked by `deliver`, so the gate does not refuse
  it (a one-step move still is); the parent pre-check catches every store
  error; a changelog sentence and a spec bullet that claimed an impossible fix
  corrected; the jira.md and commands.md strict tables updated.
- **Capability**: `work/require-tracker-backed-work` description (the gate's new
  refusal, nesting by import, the pre-strict epic worktree); declared in
  `capabilities.yaml` as `changed`.
- **Docs**: jira.md, commands.md, changelog, release notes.

## Tests

- `tests/test_tracker_strict_gate.py` (13). On the pre-change code: the
  no-transition, two-routes and three import tests failed; the held-sibling,
  named-transition and unmapped-target guards each failed under the matching
  mutation; the catch-up tests each failed on the commit before them.
- Gap 2 (held item with an owed claim) was already fixed after triage; its test
  exists: `tests/test_tracker_strict.py::test_a_held_item_drops_its_record_so_strict_mode_does_not_lock_it`.
- Full suite on the final code: 4635 passed, 3 skipped.

## What the plan or spec got wrong

- The spec's "real resolution" problem cannot occur: `statuses.completed` is
  never per-resolution. Removed.
- It missed legacy `catch-up` bindings, which `deliver` walks; first exempted
  too widely, then narrowed to walks of more than one rung.
- The plan put all five criteria's tests in the new file; criterion 5's already
  existed.

## Documentation Sync

| Entry | Fired? | Done |
| --- | --- | --- |
| `README.md` | Checked, no | — |
| `docs/guide/jira.md` | Yes | Strict table rows for submit/rework and complete. |
| `docs/guide/<topic>.md` | No | — |
| `docs/release-notes/upcoming.md` | Yes | A fix and a new option. |
| `docs/changelogs/upcoming.md` | Yes | Added and Fixed entries. |
| `skills/<component>/SKILL.md` | Checked, no | `skills/work/references/commands.md` updated instead. |
| `skills/configure/references/` | No | — |

## Autonomous decisions

Run unattended on 2026-09-26/27 (`extras-autonomous-work`).

- **Refuse "none" only, or "several" too?** Both advisors: both, through the same
  call and configured name `deliver` uses; skip for held siblings and unmapped
  targets. Taken.
- **Gap 2?** Both: already fixed after triage; a regression test only (it existed).
- **How to nest under strict mode?** Both: `tracker import --parent/--initiative`;
  letting `new --parent` through would break "work only from a ticket", which
  both flagged as a person's product decision. Chose import; `new` stays refused.
- **Pre-strict epic worktree?** Both: document, do not refuse (it would trap the
  epic). Documented in the capability.
- **The `claim_refusal` cross-reference?** Both: not here; the items it named were
  discarded and its part moved to a completed item. Dropped.
- **Code review** round 1: NOT DONE (catch-up refusal, an impossible-fix claim,
  two doc tables); round 2: DONE with a note that the catch-up skip was too wide,
  taken. Not done, as the reviewer split them: a catch-up `complete` held by
  someone else (predates this item); `import --parent` re-run on an already-bound
  ticket not nesting it silently.
- **The request** was overwritten by the run early on and restored from git
  (`cfab9429`).
- **Verify** (tcw:verifier): all criteria met, with 13 probes of its own
  (rework, complete with and without a configured name, a resolved sibling, a
  resolved parent, non-strict import). It found the spec claiming `--initiative`
  is validated before the claim while the code — like `new` — does not
  validate it; the spec is corrected. The catch-up walk broken part-way added to
  the follow-up. Decision: accept.
