# Command reference

| Goal                     | Command                                                                                                                                         |
| ------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| create an item           | `tcw work new "<title>" [--priority N] [--effort L\|M\|H\|VH] [--complexity …] [--tag <t>] [--blocked-by <ref>]`                                |
| triage the inbox         | `tcw work inbox list` → `inbox show <entry>` → `inbox accept <entry> [--title <t>]`; `<entry>` is either identifier `list` printed (ref or title) |
| locate stores            | `tcw work path` (configured work root) · `tcw work inbox path` (its inbox); both print only the absolute resolved path                          |
| the board                | `tcw work list [--status <s>] [--tag <t>] [--all] [-i]` — hides resolved; `-i` adds descendant boards                                           |
| read an item             | `tcw work show <slug> [--json]` · `tcw work path <slug>`                                                                                        |
| the lifecycle contract   | `tcw work lifecycle [work-ref] [--json]` · `--stage <id> --directive`                                                                           |
| the documentation gate   | `tcw work docs [--json]` — the documents this project keeps in sync with code                                                                   |
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
| hand work down / up      | `tcw work delegate <child-project-id> "<title>"` · `tcw work escalate "<title>"` — the ID `tcw work nodes` lists, never a path              |
| topology                 | `tcw work nodes`                                                                                                                                |
| a stage's instructions   | `tcw work stage <id> <slug> [--no-exec]` — checks, then prompts, on stdout; writes nothing                                                     |
| start a document         | `tcw work scaffold <artifact> <slug> [--force]` — writes `<artifact>.draft.md` from its template and prints the locator; **never the artifact** |
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

**Piping never hangs, and never half-succeeds.** Reading stdin is bounded: with
nothing piped the command proceeds without intake and warns on stderr, so driving
`tcw` from a script or hook that leaves its own stdin open is safe. A stream that
starts and then stalls is **refused** (exit 1, nothing created) rather than
stored truncated. `TCW_STDIN_TIMEOUT` sets the bound in seconds; `0` never waits.
The same holds for `tcw work delegate`, `tcw work escalate`, `tcw taxonomy add`,
and `tcw capabilities add`.

## The documentation gate

`tcw work docs` prints the project's documentation entries — what must be updated
when code changes, and what to write there. They are configuration
(`tcw-config.yaml` → `work.documentation`), so `tcw validate` checks them.

`--json` adds `source`, and that field is the whole point: `config` means the
entries are authoritative and no Markdown needs reading; `agent-guide` means the
node declared nothing and the `documentation-sync` skill falls back to a
`## Documentation Sync` section in the agent guide, exactly as before.

You rarely need the verb during a stage — `tcw work stage plan` and
`tcw work stage implement` already include the entries inline. It exists for the
third invocation point, the version offer *after* `complete`, which has no stage
to hang off.

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
deliberate ownership replacement.

A claim is briefly in flight, and reads settle across that window rather than
reporting the item missing — a blocker being started elsewhere still blocks. If a
claimant died mid-claim, reads report an **interrupted claim** instead of guessing;
`tcw work start <slug> --take-over --owner <identity>` is the documented recovery,
and it still works while that state persists. A configured `work.path` changes only the
filesystem adapter location; project identity, hooks, and code worktrees stay
with the owning node.

The store may live in a **different Git repository** than the code, so never
compose a store path from the node root — `tcw work path`, `tcw work path <slug>`
and `tcw work inbox path` are the only correct answers, and they are what
`delegate`, `escalate`, `reconcile` and `tcw capabilities drift` follow too. A
`docs/work/` folder sitting next to a configured store is a leftover, not the
store; TCW ignores it. Conversely, a default-layout store missing `inbox` or any
status folder counts as *no* store at all — `tcw work init` restores it.
