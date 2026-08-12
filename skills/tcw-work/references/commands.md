# Command reference

| Goal                     | Command                                                                                                                                         |
| ------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| create an item           | `tcw work new "<title>" [--priority N] [--effort L\|M\|H\|VH] [--complexity …] [--tag <t>] [--blocked-by <ref>]`                                |
| triage the inbox         | `tcw work inbox list` → `inbox show <entry>` → `inbox accept <entry> [--title <t>]`                                                             |
| locate stores            | `tcw work path` (configured work root) · `tcw work inbox path` (its inbox); both print only the absolute resolved path                          |
| the board                | `tcw work list [--status <s>] [--tag <t>] [--all] [-i]` — hides resolved; `-i` adds descendant boards                                           |
| read an item             | `tcw work show <slug>` · `tcw work path <slug>`                                                                                                 |
| the lifecycle contract   | `tcw work lifecycle [work-ref] [--json]` · `--stage <id> --directive`                                                                           |
| start work               | `tcw work start <slug> [--worktree] [--force]`                                                                                                  |
| submit for verification  | `tcw work submit <slug>`                                                                                                                        |
| send back for rework     | `tcw work rework <slug>` (refused while `refined-outcome.md` exists)                                                                            |
| finish work              | `tcw work complete <slug> --resolution done --confirm [--already-integrated]`                                                                   |
| close without shipping   | `tcw work complete <slug> --resolution wontfix\|duplicate\|superseded --confirm`                                                                |
| delete a backlog item    | `tcw work drop <slug> --confirm` (no record kept)                                                                                               |
| record / clear a blocker | `tcw work edit <slug> --blocked-by <ref>` · `--unblocked-by <ref>` — one flag per blocker, never comma-separated                                |
| set priority / estimates | `tcw work edit <slug> --priority N --effort <l> --complexity <l>`                                                                               |
| retitle an item          | `tcw work edit <slug> --title "<new title>"` — the slug is the stable ID and does not change; the body's `#` heading is prose you edit yourself |
| tags                     | `tcw work tags add\|rm\|list` · `tcw work edit <slug> --tag <t> --untag <t>`                                                                    |
| nest a coupled piece     | `tcw work new "<sub>" --parent <slug>`                                                                                                          |
| add an epic task         | `tcw work new "<task>" --initiative <epic-slug>`                                                                                                |
| epic rollup              | `tcw work reconcile <epic-slug> [--complete-when-ready]`                                                                                        |
| hand work down / up      | `tcw work delegate <child> "<title>"` · `tcw work escalate "<title>"`                                                                           |
| topology                 | `tcw work nodes`                                                                                                                                |
| validate                 | `tcw validate [path]`                                                                                                                           |

**Not CLI subcommands.** Two workflows are AI-driven reviews with no `tcw` verb
behind them — the CLI cannot run them, and asking it to is an argparse error:

| Goal                   | How to reach it                                                                                   |
| ---------------------- | ------------------------------------------------------------------------------------------------- |
| audit the backlog      | [`audit-backlog.md`](audit-backlog.md) — any harness · `/tcw-audit-work-backlog` in Claude        |
| migrate external plans | [`consolidate-plans.md`](consolidate-plans.md) — any harness · `/tcw-consolidate-plans` in Claude |

## The body surface

An item's body resolves to `initial-request.md` when it exists and non-empty, and
to `intake.md` otherwise — the raw input the item started from, written by
`tcw work new` from piped stdin or by `tcw work inbox accept` from the entry.
Neither is created empty: `tcw work new "<title>"` with nothing piped leaves an
item with no body file at all, which is why `R` on the board means the `request`
stage has run and `i` means raw input is waiting for it.

Writes never follow that fallback. A body edit always targets
`initial-request.md`; on an intake-only item it **promotes** the item, creating
the request and leaving `intake.md` byte-identical. Edit `intake.md` only as a
named artifact — raw input that quietly changes is not raw input.

## Addressing

A **bare slug** is local. `<project-id>/<slug>` resolves any node in the
registered graph — descendant, ancestor, or sibling. A `<status>/…/<slug>` path
also works, but the status segment must match the item's real status; the slug is
always the identity.

Reference another object in prose with `[text](tcw://W/<slug>)`, or
`tcw://W/<project-id>/<slug>` across nodes.

## Slash commands (Claude only)

`/tcw-process-inbox`, `/tcw-plan-work`, `/tcw-drive-work-to-completion`,
`/tcw-verify-work`. **Codex has no slash commands**, so every one of these
workflows is also reachable by invoking the `tcw-work` skill and following the
stage documents directly. Nothing is only available through a command.

# Claims and external work stores

Treat `start` as a claim: supply a stable owner (flag, environment, or Git
identity), choose another item after contention, and use `--take-over` only as a
deliberate ownership replacement. A configured `work.path` changes only the
filesystem adapter location; project identity, hooks, and code worktrees stay
with the owning node.
