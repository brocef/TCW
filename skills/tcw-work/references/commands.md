# Command reference

| Goal                     | Command                                                                                                                                         |
| ------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| create an item           | `tcw work new "<title>" [--priority N] [--effort L\|M\|H\|VH] [--complexity …] [--tag\|--tags <t[,t]>] [--blocked-by <ref>]`                                |
| triage the inbox         | `tcw work inbox list` → `inbox show <entry>` → `inbox accept <entry> [--title <t>]`; `<entry>` is either identifier `list` printed (ref or title) |
| locate stores            | `tcw work path` (configured work root) · `tcw work inbox path` (its inbox); both print only the absolute resolved path                          |
| the board                | `tcw work list [--status <s>] [--tag\|--tags <t[,t]>] [--all] [-i]` — hides resolved; `-i` adds descendant boards                                           |
| read an item             | `tcw work show <slug> [--json]` · `tcw work path <slug>` — `show` answers from the graveyard for an item retention deleted, naming the commit its documents are in                                                                                        |
| the lifecycle contract   | `tcw work lifecycle [work-ref] [--json]` · `--stage <id> --directive`                                                                           |
| the documentation gate   | `tcw work docs [--json]` — the documents this project keeps in sync with code                                                                   |
| start work               | `tcw work start <slug> [--worktree] [--force]`                                                                                                  |
| submit for verification  | `tcw work submit <slug>`                                                                                                                        |
| send back for rework     | `tcw work rework <slug>` (refused while `refined-outcome.md` exists)                                                                            |
| finish work              | `tcw work complete <slug> --resolution done --confirm [--already-integrated]`                                                                   |
| close without shipping   | `tcw work complete <slug> --resolution wontfix\|duplicate\|superseded --confirm`                                                                |
| delete a backlog item    | `tcw work drop <slug> --confirm` (no record kept)                                                                                               |
| finish a pending removal | `tcw work delete <slug>` — for an item a `work.retain.<status>: false` node resolved but whose `auto-delete` archive failed; runs the same bindings, refuses a live or retained item |
| record a resolved slug   | `tcw work tombstone add <slug> [--resolution <r>] [--resolved <ISO>]` — for work resolved *before* the store kept records; refuses only a **live** slug or one already recorded, so it works on the machine still holding the resolved folder and is safe to re-run; commits and publishes |
| record / clear a blocker | `tcw work edit <slug> --blocked-by <ref>` · `--unblocked-by <ref>` — one flag per blocker, never comma-separated                                |
| set priority / estimates | `tcw work edit <slug> --priority N --effort <l> --complexity <l>`                                                                               |
| retitle an item          | `tcw work edit <slug> --title "<new title>"` — the slug is the stable ID and does not change; the body's `#` heading is prose you edit yourself |
| tags                     | `tcw work tags add\|rm\|list` · `tcw work edit <slug> --tag <t> --untag <t>` — every tag value may be `a,b,c`                                                                    |
| nest a coupled piece     | `tcw work new "<sub>" --parent <slug>`                                                                                                          |
| add an epic task         | `tcw work new "<task>" --initiative <epic-slug>`                                                                                                |
| epic rollup              | `tcw work reconcile <epic-slug> [--complete-when-ready]`                                                                                        |
| hand work down / up      | `tcw work delegate <child-project-id> "<title>"` · `tcw work escalate "<title>"` — the ID `tcw work nodes` lists, never a path              |
| topology                 | `tcw work nodes`                                                                                                                                |
| check a stage may run    | `tcw work stage gate <id> <slug> [--no-exec]` — status legality, then the stage's `pre` checks. Prints **no** instructions and writes nothing; success is exit 0 with empty stdout. `inbox` takes no slug: `tcw work stage gate inbox` |
| read a stage's instructions | `tcw work stage prompt <id> [<slug>]` — the **only** verb that prints them; runs **no** legality check and **no** `pre` checks. The slug is optional: without one they resolve generically, with one they resolve for that item. What it prints is wrapped in a gate reminder and a next-step section |
| read a stage as one document | `tcw-work-stage <id> <item>` — the skill composes `lifecycle/stage-<id>.md` with the output of `tcw work stage prompt` so both arrive in one read. It reads: no legality check, no `pre` checks. `tcw work stage gate` is still what refuses |
| start a document         | `tcw work scaffold <artifact> <slug> [--force]` — writes `<artifact>.draft.md` from its template and prints the locator; **never the artifact** |
| validate                 | `tcw validate [path]`                                                                                                                           |
| obtain a declared store or project | `tcw provision [--component work\|taxonomy\|capabilities] [--refresh] [--dry-run]` — fetches the stores **and connected projects** this node declares but does not have here; connected projects are followed transitively; every declared component by default; idempotent |

**Not CLI subcommands.** Two workflows are AI-driven reviews with no `tcw` verb
behind them — the CLI cannot run them, and asking it to is an argparse error:

| Goal                   | How to reach it                                                                                   |
| ---------------------- | ------------------------------------------------------------------------------------------------- |
| audit the backlog      | [`audit-backlog.md`](procedures/audit-backlog.md) — any harness · `/tcw-audit-work-backlog` in Claude        |
| migrate external plans | [`consolidate-plans.md`](procedures/consolidate-plans.md) — any harness · `/tcw-consolidate-plans` in Claude |

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

You rarely need the verb during a stage — `tcw work stage prompt plan` and
`tcw work stage prompt implement` already include the entries inline. It exists for the
third invocation point, the version offer *after* `complete`, which has no stage
to hang off.

Writes never follow that fallback. A body edit always targets
`initial-request.md`; on an intake-only item it **promotes** the item, creating
the request and leaving `intake.md` byte-identical. Edit `intake.md` only as a
named artifact — raw input that quietly changes is not raw input.

## Working from an external tracker

`list` and `show` only read. `import` and `link` change the ticket (a claim) and
then the store; `unlink` changes only the store. No other command gains a network
dependency because of any of them.

| Goal | Command |
| ---- | ------- |
| list tickets the configured query selects | `tcw work tracker list` |
| one ticket, plus its claimability report | `tcw work tracker show <ticket>` |
| claim a ticket and create a bound backlog item | `tcw work tracker import <ticket> [--part <id>] [--title <title>]` |
| claim a ticket for an existing unresolved item | `tcw work tracker link <slug> <ticket> [--part <id>]` |
| remove a binding, keeping a record and the reason | `tcw work tracker unlink <slug> --reason <text>` |

Configured under `work.tracker` in the node sentinel: `provider` (only
`jira-cloud`), `base-url`, `candidate-query`, `credentials.email-env`,
`credentials.token-env`, `transitions.claim`, and optional `timeout-seconds`
(default 15). All but the last are required. Unknown keys are reported rather than
ignored, so a config written for a later release complains instead of silently doing
less.

**Credentials are named, never stored** — the config holds two environment variable
names, read at request time.

**Settings inherit from parent nodes, opt-in.** A node whose own `work.tracker` is a
non-empty mapping takes every key it leaves out from its ancestors (direct parent
first, all the way up, including nodes without a board). The nearest file wins each
key; `credentials` and `transitions` merge key by key; a nearer `null` lets the
farther value through. A node with no block, or `tracker: {}`, has no tracker and no
problems whatever its ancestors hold — there is no `tracker: none`. Rules to know:

- **`credentials` must come from the same file as `base-url`, or a nearer one.** A
  child that sets `base-url` — even to its parent's value — and inherits
  `credentials`, or either one of its keys, has no tracker, and `validate` says why.
- **A node with a board that holds shared settings is checked like any tracking
  node**, so it needs its own `candidate-query`. Keep shared settings in a node
  without a board instead.
- **A problem names the file its value came from.** `tcw-config.yaml: …` is the
  node's own file; `<path>/tcw-config.yaml (project '<id>'): …` is an ancestor's —
  fix it there. A missing required key is blamed on the node being checked. When a
  declared ancestor is not checked out, any tracker problem comes with an extra one
  naming it (run `tcw provision`).

**A malformed block does not break a board read.** It reads as no tracker at all
(the parse fails closed) and `tcw validate` reports it. With no tracker configured,
nothing changes and no tracker code is even imported.

**`tcw validate` never contacts the tracker**, because a project may bind it as a
`pre` hook on `complete` and a `pre` failure stops the item moving. Do not add a
network call to that path.

`show` reports two distinct things. **claimable** is about this ticket now: does it
offer the configured claim transition. **exclusive** is about the workflow: would a
second claimant be refused. Exclusivity is only readable from the status the claim
leads to, so a ticket nobody has started reports `not determined`. On a workflow
offering every transition from every status — Jira's default — a started ticket
reports `not exclusive`, and two people claiming it would both succeed. On an
exclusive workflow a started ticket still reports `not determined`, and a second
`show` will not change that; only a claim, or the workflow definition, confirms it.

### Claiming and binding

**The claim decides from the ticket, never from Jira's reply.** `import` and `link`
read the ticket, apply the configured claim transition, assign the ticket to the
signed-in account only if that transition applied and nobody had it, then read the
ticket again. It counts as claimed only when it is now in the status the claim
leads to and assigned to this account. A transition's error text is shown on a
`detail:` line and never used as the reason.

- **Who may claim:** an unassigned ticket, or one already assigned to this
  account. Assigned to anyone else, or in a done status: refused, naming the
  assignee and status.
- **Already yours:** a ticket assigned to this account that no longer offers the
  claim is bound without a transition ("not claimed by this run"). This is how a
  claim that stopped before its item was created finishes on a re-run.
- **One item per ticket and part:** re-running `import` prints the existing slug and
  exits 0. `--part` (lowercase letters, digits, hyphens; default `default`) makes
  another item for the same ticket on purpose. The lookup covers unresolved items in
  **this node** of this working copy: a binding nobody has committed and pushed is
  invisible to other clones, and a binding in one node is invisible to its siblings, so
  importing one ticket in two nodes gives an item in each.
- **Not guarded:** on a workflow that offers the claim from its own destination, two
  accounts can both claim one ticket; and two runs by one account at the same moment
  can both create an item. Both are accepted limits, not bugs to work around.

**The binding is `tracker.yaml`**, a sidecar marked `generated`: written by these
commands, never by hand; the web app offers no edit for it, though its server does
not yet refuse a write. It records provider,
project id, part, the ticket's stable id, key and URL, the claiming account id and
name, the date, and an `unlinked` history. No credential and no e-mail address.
**Never treat a binding as proof of a claim** — `import` re-reads the ticket even
when a binding exists, and refuses when the tracker disagrees. A binding that is not
a readable mapping, or two items holding one ticket and part, makes `import` and
`link` refuse and name the items; `tcw validate` reports a binding that is not a
mapping, as it does for any record TCW writes.

`import` puts the ticket's description into the item's **intake** with a link to the
ticket; the `request` stage still runs. It does not set `owner` — importing is not
starting. `unlink` makes no tracker call and needs no tracker configured.

Neither `list` nor `show` detects a wrong `transitions.claim` value. A ticket not offering it
may not have reached the claim yet, or may have been claimed already, and both are
indistinguishable from a typo without reading the project's workflow definition.

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

**"Already here" includes another repository on this disk.** Before fetching,
resolution asks the project registry whether some project it has located is a
checkout of the declared repository, and if so reads the store inside that copy.
So a workspace cloned flat where the config describes it nested needs no symlink
and no machine-specific path — `TCW_PROJECT_<ID>` below is enough. A store
reached that way does **not** publish: it is the user's own checkout, on
whatever branch they have it on, and they push it themselves. Only a copy TCW
fetched publishes.

**A connected project declares the same way.** An entry under
`connected-projects` may be `{path, repository}` instead of a bare locator, with
the same ladder — the project at `path` wins when it is here — so a checkout that
cloned one repository can still resolve `extends`, cross-node refs and the
topology. Declarations follow the graph: each config names only its own edges.

**One rung sits above both: `TCW_PROJECT_<ID>`** (the id uppercased, `-` as `_`),
naming where that project is on *this* machine. It wins over the declared path
and the declaration, because the case it exists for is a path that resolves to
the *wrong* node — a workspace laid out flat where the config describes it
nested, which is what makes `tcw provision` fetch a second copy of a project the
machine already has. Reach for it before editing a shared config to match one
machine. It reaches component stores too, through the rung above: a store whose
declared repository is a project this variable located is read there. A variable naming a path that is not here is not an error and falls
through to `repository`, so one set can serve a whole environment; one naming a
directory that is present and wrong is refused — by `tcw provision` too, which
stops before contacting anything rather than falling back to a fetch.
`tcw validate` lists the ones in effect — if a graph resolves for a reason no
config explains, that list is where to look.

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
