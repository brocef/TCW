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
| record a resolved slug   | `tcw work tombstone add <slug> [--resolution <r>] [--resolved <ISO>]` — for work resolved *before* the store kept records; refuses only a **live** slug or one already recorded, so it works on the machine still holding the resolved folder and is safe to re-run; commits and publishes |
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
| obtain a declared store or project | `tcw provision [--component work\|taxonomy\|capabilities] [--refresh] [--dry-run]` — fetches the stores **and connected projects** this node declares but does not have here; connected projects are followed transitively; every declared component by default; idempotent |

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
registered graph this checkout can open — descendant, ancestor, or sibling. A
qualifier naming a project that is declared but whose repository is not here
fails saying exactly that, naming the config that declared it; a qualifier naming
a project nobody declared still reports that there is no such project. A `<status>/…/<slug>` path
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

**The work store can also declare where it comes from.** `work.repository` in
`tcw-config.yaml` names the repository holding the store (`url`, and optionally
`ref`, `path` within it, and a local `checkout`), which is the portable half:
`work.path` says where it is on one machine, `repository` says how any machine
gets it. Resolution prefers a store that is **already here** — the declaration
answers only when the local one is absent, so one config serves a laptop that has
the folder and a fresh clone that does not.

**A connected project declares the same way.** An entry under
`connected-projects` may be `{path, repository}` instead of a bare locator, with
the same ladder — the project at `path` wins when it is here — so a checkout that
cloned one repository can still resolve `extends`, cross-node refs and the
topology. Declarations follow the graph: each config names only its own edges.

`tcw provision` obtains the missing stores and connected projects. `--component`
scopes the component pass; connected projects are obtained after it and
**transitively**, since a project just obtained may declare others. That is the
one place a URL the user did not write is contacted, so every remote is printed
first and `--dry-run` plans the whole queue without a network call. Nothing else
reaches the network: a
command that needs an unprovisioned store fails, names the declared remote, and
tells the user to run it — do not work around that by composing a path or running
`tcw init`, which would scaffold a second, empty store beside the real one. A
*malformed* `repository` block fails the same way and names the offending config
line instead of the remote; the response there is to fix that line, and `tcw init`
is just as wrong.

The store may live in a **different Git repository** than the code, so never
compose a store path from the node root — `tcw work path`, `tcw work path <slug>`
and `tcw work inbox path` are the only correct answers, and they are what
`delegate`, `escalate`, `reconcile` and `tcw capabilities drift` follow too. A
`docs/work/` folder sitting next to a configured store is a leftover, not the
store; TCW ignores it. Conversely, a default-layout store missing `inbox` or any
status folder counts as *no* store at all — `tcw work init` restores it.

**Items stay inside their own store.** An item is discovered by its
`state.yaml`, so a `state.yaml` that is a symlink out of the store is not an
item, and an artifact, sidecar or plan document that is a symlink out reads as
absent rather than being followed. Nothing supported is lost — Git cannot track
a file through a symlink anyway. The same containment applies to taxonomy and
capability entries and the files inside them.

**A transition on a provisioned store talks to its remote.** It refreshes before
moving and pushes after committing, so a transition can now fail *after* having
succeeded locally — a state the rest of this document does not otherwise describe.
Read the error rather than assuming the transition did not happen: if the refresh
failed nothing moved and the item is untouched, but if the push failed the item
**has** moved and is committed, and the message says where. Re-running is safe.
Only a provisioned store does this (`work.publish-transitions: false` turns it
off); a local `work.path` store never publishes, and neither do the taxonomy and
capabilities trees, whose entries land with the code change that realizes them.

**Every write needs a Git repository; every read does not.** Outside one, any
writing command refuses with `not inside a git repository. Run `git init`
first.`, exits non-zero, and changes nothing on disk — including `delegate` and
`escalate`, which need a repository at the *destination* node. That is a
refusal to act on (run `git init`, or move to the right directory), never a
crash to retry or to route around by writing the files by hand. `tcw work list`,
`show`, `nodes` and `tcw validate` keep working. A different message —
`tcw: git command failed (exit N): …` — means the repository is there but Git
refused: a lock another process holds, a hook that said no. Whatever that
command *created* is removed, so there is no half-made item to clean up. An
*edit* to something that already existed is not undone — the change is on disk
and the item may already have moved — so fix the Git problem and re-run the
command; re-running is the fix in both cases.

**With an external `work.path`, two repositories are in play** — the store's and
the code node's — and a command can need both. `tcw work start --worktree`
writes the node's `.gitignore` and creates the worktree there, so it refuses
unless the *node* is in a repository even when the store is fine; a plain
`start` needs only the store. `tcw work complete` on a worktree item merges the
work branch back in the node's repository, and refuses rather than completing
if that repository is gone — a completion that skipped its merge-back would
leave the branch stranded with nothing to say so. `--already-integrated` is the
exception, and deliberately: it says the merge already happened, so there is no
merge to protect and the worktree teardown is best-effort from there.
