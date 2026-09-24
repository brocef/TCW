# Command reference

| Goal                     | Command                                                                                                                                         |
| ------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| create an item           | `tcw work new "<title>" [--priority N] [--effort L\|M\|H\|VH] [--complexity …] [--tag\|--tags <t[,t]>] [--blocked-by <ref>]`                                |
| triage the inbox         | `tcw work inbox list` → `inbox show <entry>` → `inbox accept <entry> [--title <t>]`; `<entry>` is either identifier `list` printed (ref or title). With `work.tracker.inbox-query`, `list` adds a `tracker tickets:` section and `<entry>` may be a ticket key: a raw entry of that name wins, `--ticket` forces the ticket, and accepting a ticket is `tracker import` (`--part` too) |
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
| add a child item         | `tcw work new "<sub>" --parent <slug>`                                                                                                          |
| add an epic task         | `tcw work new "<task>" --initiative <epic-slug>`                                                                                                |
| make an item an epic     | `tcw work edit <slug> --type epic` · `--type ""` makes it plain again, refused while any item names it as its initiative or the project graph is partial, and under strict tracker mode |
| epic rollup              | `tcw work reconcile <epic-slug> [--complete-when-ready]`                                                                                        |
| hand work down / up      | `tcw work delegate <child-project-id> "<title>"` · `tcw work escalate "<title>"` — the ID `tcw work nodes` lists, never a path              |
| topology                 | `tcw work nodes`                                                                                                                                |
| check a stage may run    | `tcw work stage gate <id> <slug> [--no-exec]` — status legality, then the stage's `pre` checks. Prints **no** instructions and writes nothing; success is exit 0 with empty stdout. `inbox` takes no slug: `tcw work stage gate inbox` |
| read a stage's instructions | `tcw work stage prompt <id> [<slug>]` — the **only** verb that prints them; runs **no** legality check and **no** `pre` checks. The slug is optional: without one they resolve generically, with one they resolve for that item. What it prints is wrapped in a gate reminder and a next-step section |
| check a stage skill's arguments | `tcw work stage validate <id> [<slug>]` — prints nothing and exits 0 when `tcw work stage prompt` would accept them; otherwise a Markdown usage error on stdout and exit 1. Under an agent harness other than Claude Code it first prints a notice that injected commands must be run by hand. Injected at the top of `work-stage` |
| read a stage as one document | `work-stage <id> [<item>]` — the skill composes TCW's own document for the stage with the output of `tcw work stage prompt` so both arrive in one read. It reads: no legality check, no `pre` checks. `tcw work stage gate` is still what refuses |
| read a procedure         | `tcw work procedure prompt <id> [<slug>] [--no-exec]` — one of TCW's procedures (`unattended-work`, `triage-issues`, `documentation-sync`, `post-mortem`, `create-work`, `audit-backlog`, `consolidate-plans`, `decompose`, `delegation`, `search`) composed with the project's `work.procedures` text; plain text, no header, no gate. Outside a TCW node, without a slug, it prints TCW's own text. The slug is optional and lets `when:` and `generate:` see that item |
| start a document         | `tcw work scaffold <artifact> <slug> [--force]` — writes `<artifact>.draft.md` from its template and prints the locator; **never the artifact** |
| validate                 | `tcw validate [path]`                                                                                                                           |
| obtain a declared store or project | `tcw provision [--component work\|taxonomy\|capabilities] [--refresh] [--dry-run]` — fetches the stores **and connected projects** this node declares but does not have here; connected projects are followed transitively; every declared component by default; idempotent |

**Not CLI subcommands.** Two workflows are AI-driven reviews with no `tcw` verb
behind them — the CLI cannot run them, and asking it to is an argparse error:

| Goal                   | How to reach it                                                                                   |
| ---------------------- | ------------------------------------------------------------------------------------------------- |
| audit the backlog      | [`audit-backlog.md`](procedures/audit-backlog.md) — any harness · ask the `work` skill        |
| migrate external plans | [`consolidate-plans.md`](procedures/consolidate-plans.md) — any harness · ask the `work` skill |

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
`tcw work stage prompt implement` already include the entries inline. It exists
as the read-only accessor for a node's documentation entries: the
`documentation-sync` skill asks it first, before any stage prompt is resolved and
outside the lifecycle altogether, and the web app reads the same answer.

Writes never follow that fallback. A body edit always targets
`initial-request.md`; on an intake-only item it **promotes** the item, creating
the request and leaving `intake.md` byte-identical. Edit `intake.md` only as a
named artifact — raw input that quietly changes is not raw input.

## Working from an external tracker

`list`, `show` and `link` only read the ticket; `import` claims it and then writes
the store; `create` makes a ticket that did not exist; `unlink` touches the store
alone and needs no tracker configured. `sync` and the lifecycle commands `start`,
`submit`, `rework` and `complete` write to a **bound** item's ticket when a
tracker is configured — see "Lifecycle synchronization".

**`tcw work new` and `inbox accept` gain a network dependency only under
`work.tracker.create.on-new`**, and even then they never fail because of it: the
item is filed and the ticket is recorded as *owed*, shown on the board, and made
later by `tracker create` — not by `tracker sync`, which settles the other kind
of debt. Filing on the web board always records the ticket as owed, because the
web app does not talk to the tracker. Nothing else here gains a dependency.

| Goal | Command |
| ---- | ------- |
| list tickets the configured query selects | `tcw work tracker list` |
| one ticket, plus its claimability report | `tcw work tracker show <ticket>` |
| claim a ticket and create a bound backlog item | `tcw work tracker import <ticket> [--part <id>] [--title <title>]` |
| say an item and its ticket are yours | `tcw work tracker claim <slug> [--take-over]` — sets the item's owner and assigns the ticket; applies no transition and moves neither status |
| let go of an item and its ticket | `tcw work tracker release <slug> [--force]` — clears the owner and unassigns the ticket; status and binding untouched |
| make a ticket for an item that has none, and bind it | `tcw work tracker create <slug> [--part <id>] [--dry-run]` · `tcw work tracker create --all` — needs `work.tracker.create` and `statuses.backlog`; refuses a closed item, and reports rather than duplicates one already bound |
| record that an existing item and a ticket are the same work | `tcw work tracker link <slug> <ticket> [--part <id>]` |
| remove a binding, keeping a record and the reason | `tcw work tracker unlink <slug> --reason <text>` |
| retry tickets that did not follow their items | `tcw work tracker sync <slug>` · `tcw work tracker sync --all` |

**Configured with the `configure` skill's `tracker.md`**, including settings a
node merges from its ancestors'. At runtime:

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
offer `transitions.start`, the transition `import` claims through. **workflow** is
about exclusivity: would a second claimant be refused. It is asked about
`exclusive-claim-transition` — the key strict mode's promise rests on — or about
`transitions.start` where that key is unset, and it is only readable from
`statuses.active`, where the claim leads, so a ticket nobody has started reports
`not determined`. On a workflow offering every transition from every status — Jira's
default — a started ticket reports `not exclusive`, and two people claiming it would
both succeed. On a workflow that does not offer the transition from
`statuses.active`, a started ticket reports `exclusive`.
Where `work.tracker.transitions.start` is not set at all, `show` says the setting
names no transition rather than reporting it as a name the ticket does not offer —
the reader is sent to their own configuration file, not to the ticket's workflow.

### Claiming and binding

**`link` claims nothing.** It reads the ticket — which is what proves the key
exists and yields the id, key and URL the binding stores — and writes the binding.
The ticket keeps its status and assignee, so a ticket somebody else holds is
bindable, and nothing but `tracker.yaml` is written, so the item keeps its status,
owner and documents. Any status can be linked or unlinked, `completed` and
`discarded` included, which is how finished work is tied to the ticket that tracked
it and how a wrong binding on it is repaired. Resolved folders are gitignored by
default, so such a binding is written to disk but never committed. `tcw work start`
claims a linked ticket; `import` on one refuses, saying it is linked but not claimed.

### Lifecycle synchronization

For a **bound** item in a node with a tracker configured, a lifecycle command sends
its move to the ticket **after** the local move, its commit and `post` hooks:
`start` claims — first taking a ticket out of a `work.tracker.pre-backlog` status
such as `Triage`, then an assignment read back, applying no transition unless
`exclusive-claim-transition` names one — and then moves the ticket to
`statuses.active` like any other move; `submit`, `rework`, `complete` and a discard
move the ticket to `work.tracker.statuses` for the item's new status (nothing when
unmapped). No tracker configured, or an unbound item: nothing, and no tracker code
is imported.

- **A claim gates work, not resolution.** `submit` and `rework` of a bound item are
  **refused before the local move** unless the ticket is assigned to the signed-in
  account — held by another names them; held by nobody names `tcw work tracker
  claim <slug>` — in every mode, strict or not. An unreachable tracker does not
  refuse outside strict mode. An unbound item is not gated; the local `owner` is not a
  permission. `complete` and a discard need no claim: they move the ticket whoever
  holds it, and leave the assignee alone.
- **Forward only for a lifecycle move.** A `start` whose ticket is already past
  `active` (in review, say) claims it, leaves it there, reports it `held`, and exits 0
  with no record. Only `tracker sync` moves a ticket backwards.
- **`start` on an active item nobody holds** (after `tracker release`) takes it,
  rather than refusing. Active and held by somebody else is refused, naming
  `tcw work tracker claim <slug> --take-over`.

- **Moved only when** assigned to the signed-in account (not asked for `complete` or
  a discard), not already resolved, and —
  for a lifecycle move — in the status the previous local status maps to (or, with a
  record, its `since` or its move's target). Otherwise *conflicting*. Exactly one
  offered transition must lead to the target.
- **Not updated → the item still moved**, exit 1, and `tracker.yaml` gains a `sync`
  record: `pending` (unreachable, rate limited, no or bad credentials, a tracker
  block with problems) or `conflicting` (Jira answered: 400/403/404, assignee,
  drift, no single transition; a claim that failed because Jira did not answer is
  `pending`). A record whose `move` is `start` means that start was never delivered:
  `tracker sync` claims first, delivers the start, then the move after it. There is no `claim` key —
  one still on disk from an older version is read and ignored. Success removes the
  record; a first-time success writes nothing.
- **`show`** prints `tracker sync: <state> after <move> (<at>): <reason>`; the board
  row reads `ticket: KEY (pending)`; `--json` has `tracker.sync`.
- **`tcw work tracker sync <slug> | --all`** reconciles the ticket to the item: the
  item's status is the source of truth, so a ticket ahead of it is brought back and one
  behind is brought forward, and a backwards move prints a line saying so. It skips an
  item whose `owner` is not this identity (it acts as whoever runs it). It does **not**
  reconcile a binding whose `part` is not `default` unless a record says what is owed —
  another part may be holding that ticket, and a hold leaves no evidence outside the
  checkout it happened in. `--all` visits only items with a record or an owed comment.
  Exit 1 while any stays unresolved — and a **named** slug skipped while it still owes a
  record is itself exit 1, naming `TCW_WORK_OWNER` and `start --take-over`; a `--all`
  sweep still exits 0 over other people's items.
- **Bringing a ticket along is `link`, then `claim`, then `sync`.** A plain `link` on
  an item past `backlog` changes nothing in the tracker. When the ticket's status does
  not match the item's, it warns and notes `status-synced: false` on the binding;
  while the ticket's status stays out of step, later moves report it `held` — linked
  without its status synced — and move nothing, and strict mode refuses them with the
  same explanation. Another holder, an unclaimed ticket in step, or a misnamed
  transition is still `conflicting`. The note clears once a delivery or `sync` finds
  the ticket in step. `tcw work tracker claim <slug>` then `tcw work tracker sync
  <slug>` brings it along in one transition. **`link --sync-status` is retired**:
  it refuses, names those three commands, and writes nothing.
- **`catch-up: true` is read, never written.** A binding an older `--sync-status`
  wrote still walks its ticket forward one mapped status at a time (straight there
  when the workflow offers it), never backwards and never on a resolved ticket; a
  plain `sync` makes one move. `tracker create` for work under way records the item's
  start as undelivered instead, so it claims, delivers the start, then the move after
  it.
- **Triage:** a move that takes a ticket — `start`, `sync` of an undelivered start or
  a catch-up, `import`, `inbox accept` — first applies the transition
  `work.tracker.pre-backlog` names when the ticket is in one of its statuses, and says
  the ticket was moved out; nothing else leaves triage, and without the key the
  refusal names it.
- **No `transitions.start`:** the key is optional (required under strict mode —
  `validate` reports it), and a lifecycle `start` with no
  name works its transition out from `statuses.active`. `import` and `inbox accept`
  cannot — a claim has no status of its own to derive from — so they refuse and name
  the key (row `1d`), unless the ticket is already assigned to the running account,
  which needs no transition and still imports (row `1e`).
- **Parts:** a status move is held while another open item here shares the ticket.
- **Another site:** a binding whose `ticket.url` is not on `base-url` is never
  written through; `import`/`link` refuse it naming the item.
- **Not delivered:** moves made in `tcw serve`, and a command interrupted between
  its commit and the tracker call — no record, so `sync` checks but will not move.
- **Unretained items:** when delivery fails on an item about to be removed, no
  record is written and the item is kept; move the ticket by hand, then
  `tcw work delete`.

### Progress comments

With `work.tracker.comments: true`, after the status step each lifecycle move posts
one comment: `TCW: "<title>" (part <part>) <started | went to review | went back to
work | was completed | was discarded as <resolution>>.`, the `link` template's URL
when set, and a `tcw-event: <move>-<hex>` line. No lifecycle document is copied.

- **Status step pending/conflicting:** the comment is owed with it (`comment` record
  in `tracker.yaml`, beside `sync`), whoever holds the ticket.
- **Otherwise:** posted only when the ticket is assigned to the signed-in account;
  not → no comment, a `→` line, and any older owed comment is dropped.
- **Post failed:** exit 1, `comment` record (`move`, `event`, `state`, `reason`,
  `at`). One at a time; a later move's comment replaces it. An item about to be
  auto-deleted takes no record and is still removed.
- **`sync`:** an item with only a `comment` record skips the status step. Before
  posting, it looks for the event among the account's newest 100 comments and
  clears the record when found. It drops the record when comments are off, when the
  record is unreadable, or when the ticket is no longer the account's.
- **`show`** prints `tracker comment: <state> after <move> (<at>): <reason>`; the row
  reads `ticket: KEY (comment pending)`; `--json` has `tracker.comment`.
- **Strict mode** does not refuse over an owed comment. `tcw serve` moves post none.

### Strict mode

With `work.tracker.strict: true`, a ticket authorizes local work **before** it
happens. Epics are never gated; discards never refused; no flag bypasses a gate
(`--force`, `--take-over` included). A refusal exits 1, names what did not happen and
the fix, and writes nothing — no `sync` record — though a refused `start` or `import`
that got as far as claiming leaves the ticket claimed.

| Command | Under strict |
| ------- | ------------ |
| `new` (not `--epic`), `inbox accept` of a raw entry | refused → `tcw work tracker import <ticket>` (`inbox accept <ticket>` is import, gated as import) |
| `start` | unbound: refused. Bound: claim first, through `exclusive-claim-transition` (after the store's own status and blocker checks; the epic-active and repository checks come after it), move only if claimed and the workflow does not offer that transition again from `statuses.active` — so a second claimant the workflow refuses is stopped before their item moves. A ticket already yours is checked the same way without applying anything, when it is in `statuses.active`; one still in the backlog status is accepted unchecked. Where the ticket is already in `statuses.active` and the workflow offers the transition there, refused before anything is sent. An epic cannot start with `--worktree` |
| `submit`, `rework` | read the ticket: assigned to you, and in the mapped status of the item's status (or the target), or of an earlier status when an item for another part of the ticket is here; else refused |
| `complete --resolution done` | read the ticket: in that status, as above; who holds it is not asked. Checked before the worktree merge |
| `complete` with a discard resolution | allowed |
| `drop` | refused if the item has a `tracker.yaml` (bound, unlinked or unreadable) → discard instead |
| `tracker import` | claims through `transitions.start` (required under strict). Refused after the claim when the ticket is not in `statuses.active` or still offers `exclusive-claim-transition` or `transitions.start` there — it takes the ticket through the latter, so both must exclude; the ticket stays claimed |
| `tracker claim` | the same exclusivity check as `start`, before the item is claimed locally. On an unassigned ticket in `statuses.active` that does not offer the transition (a released item's ticket), refused with both ways out: assign it to yourself in the tracker, or move it back to a status offering the transition. `start --take-over` gives the same refusal |
| strict `start` claim | refused when `exclusive-claim-transition` is not offered or the workflow refuses it, when the workflow still offers it from `statuses.active`, or when the assignment does not read back as yours. A strict `start` refused after leaving a `pre-backlog` status writes no sync record: run `start` again |
| `tcw serve` create (not an epic), start, complete `done`, drop of an ever-bound item | 409, naming the `tcw work` command (PUT `tracker.yaml` is refused in every mode, below) |

- **Tracker unreachable, or an undelivered `sync` record:** refused. Run
  `tcw work tracker sync <slug>` first. A `sync` of an item with nothing recorded
  never writes a record, so it cannot create one of these.
- **A tracker block with problems:** refused, not switched off; run `tcw validate`.
- **Not gated:** `edit`, artifact writes, `tracker link`/`unlink`.
- **Parts held elsewhere:** the earlier-status allowance needs another part's item
  *in this checkout*. A part completed in another clone, or removed by `work.retain`,
  is not seen, so the last part is refused; move the ticket to the status named, or
  discard.

**The claim decides from the ticket, never from Jira's reply.** `import`
reads the ticket, applies the configured claim transition, assigns the ticket to the
signed-in account only if that transition applied and nobody had it, then reads the
ticket again. It counts as claimed only when it is now in the status the claim
leads to and assigned to this account. Once the backlog item exists and is bound,
`import` moves a ticket its claim moved back to where the claim found it (the
backlog status, after any triage step), still assigned; where the workflow offers
no single way back it warns and leaves it. Not under strict mode, and not for a
ticket already held and under way, which the claim does not move. A transition's error text is shown on a
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
commands, never by hand; the web app offers no edit for it, and its server refuses a
write to it in every mode, naming the commands that write it. It records provider,
project id, part, the ticket's stable id, key and URL, the date, and an `unlinked`
history. It names no account: a binding says two things are the same work, never
who took the ticket. No credential and no e-mail address.
**Reading a binding needs no tracker command.** `tcw work show` prints a
`tracker:` line (ticket, provider, part, URL), a board row ends ` | ticket: <key>`
(followed by `(part …, <sync state>, comment <state>)` when any applies),
and `show --json` carries `tracker` — `null` when unbound (no file, or unlinked),
`{"problem": …}` when the file cannot be read, else provider, project, part,
`ticket` {id, key, url}, `bound`, `sync` and `comment` (each `null` unless a
record is owed). All three report what the file records, not
what the tracker says, and need no tracker configured.
**Never treat a binding as proof of a claim** — `import` re-reads the ticket even
when a binding exists, and refuses when the tracker disagrees. A binding that is not
a readable mapping, or two items holding one ticket and part, makes `import` and
`link` refuse and name the items; the scan skips resolved items, so a ticket held
by a finished one can be bound to a second item, open or finished; `tcw validate` reports a binding that is not a
mapping, as it does for any record TCW writes.

`import` puts the ticket's description into the item's **intake** with a link to the
ticket; the `request` stage still runs. It does not set `owner` — importing is not
starting. `unlink` makes no tracker call and needs no tracker configured.

Neither `list` nor `show` detects a wrong `transitions.start` value. A ticket not offering it
may not have reached the claim yet, or may have been claimed already, and both are
indistinguishable from a typo without reading the project's workflow definition. An
*unset* key is a different case, and `show` does report it: nothing has to be read
from the workflow to know the setting is empty. `list` reports it no more than it
reports a wrong value — it prints one row per ticket and consults no transition.

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

## Command skills

Five skills carry the everyday workflows: `commands-process-inbox`,
`commands-plan-work`, `commands-drive-work-to-completion`,
`commands-verify-work` and `commands-pause-work`. Each works by invoking the
skill, under any harness. The first four each invoke the `work-stage` skill for
the stage they run; `commands-pause-work` stops the work in hand instead, and
reaches a stage only if the agent resumes into one.

# Claims and external work stores

Treat `start` as a claim: supply a stable owner (flag, environment, or Git
identity), choose another item after contention, and use `--take-over` only as a
deliberate ownership replacement. An active item with no owner (after `tracker
release`) is simply taken by `start`.

A claim is briefly in flight, and reads settle across that window rather than
reporting the item missing — a blocker being started elsewhere still blocks. If a
claimant died mid-claim, reads report an **interrupted claim** instead of guessing;
`tcw work start <slug> --take-over --owner <identity>` is the documented recovery,
and it still works while that state persists. A configured `work.path` changes only the
filesystem adapter location; project identity, hooks, and code worktrees stay
with the owning node.

A store may also declare the repository it comes from, which `tcw provision`
fetches. Resolution prefers a store that is **already here**: the declaration
answers only when the local one is absent. Declaring a store's location or its
repository is the `configure` skill's `stores.md`.

**"Already here" includes another repository on this disk.** Before fetching,
resolution asks the project registry whether some project it has located is a
checkout of the declared repository, and if so reads the store inside that copy.
So a workspace cloned flat where the config describes it nested needs no symlink
and no machine-specific path — `TCW_PROJECT_<ID>`, a per-machine environment
variable, is enough. A store
reached that way does **not** publish: it is the user's own checkout, on
whatever branch they have it on, and they push it themselves. Only a copy TCW
fetched publishes.

A connected project can declare a repository the same way, and
`TCW_PROJECT_<ID>`, a per-machine environment variable, can say where a project
is on this machine, ahead of every declaration. Declaring either is the
`configure` skill's `projects.md`.

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
