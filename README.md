# TCW — Taxonomy · Capabilities · Work

TCW keeps three things about a software project inside the repository itself,
next to the code, through one command-line tool (`tcw`):

| Component        | Answers                                                 | Lives in             |
| ---------------- | ------------------------------------------------------- | -------------------- |
| **Taxonomy**     | What things does this project deal with?                | `docs/taxonomy/`     |
| **Capabilities** | What can a user do with those things?                   | `docs/capabilities/` |
| **Work**         | What are we changing, and where does each change stand? | `docs/work/`         |

They link by one-directional pointers — a capability names the taxonomy terms it
involves, a work item names the capability it changes — and never copy each
other's content.

## Contents

- [The problem](#the-problem)
- [What it looks like](#what-it-looks-like)
- [Why many repositories is the case it is built for](#why-many-repositories-is-the-case-it-is-built-for)
- [What it deliberately refuses](#what-it-deliberately-refuses)
- [What adopting it costs](#what-adopting-it-costs)
- [Who it's for](#who-its-for)
- [Storage abstraction (the prime directive)](#storage-abstraction-the-prime-directive)
- [Install](#install)
  - [As a plugin (recommended)](#as-a-plugin-recommended)
  - [As a Python package](#as-a-python-package)
  - [In a cloud environment](#in-a-cloud-environment)
- [Quickstart](#quickstart)
- [Working from your Jira tickets](#working-from-your-jira-tickets)
- [Documentation](#documentation)
- [Skills — the judgment layer](#skills--the-judgment-layer)
  - [Reading a lifecycle stage](#reading-a-lifecycle-stage)
  - [Review agents and command skills](#review-agents-and-command-skills)
- [Status](#status)
- [Further reading](#further-reading)

---

## The problem

Ask three people at a company with twenty repositories what one of those
repositories does, what a user can do with it, and what is being changed in it
right now. You get three different answers, assembled from four different places:
a ticket tracker that knows about work but not about the product, a wiki whose
glossary was last edited two years ago, a `FOLLOWUPS.md` that only grows, and
design documents that stopped matching the code some time back.

None of those places is wrong on purpose. They drift because none of them sits
next to the code, and nothing makes them move when the code moves.

TCW puts all three in the repository. One commit carries a code change and the
description of what it changed, and a reviewer sees both in the same diff.

## What it looks like

Setting up one repository and taking a change through it:

```sh
tcw init --id billing-service          # marks this directory a TCW node

tcw taxonomy add Invoice "A bill issued to a customer."
tcw taxonomy add "PDF Export" --kind feature --vocab invoice

tcw capabilities add billing/invoices "Download an invoice as PDF"
tcw capabilities set billing/invoices --status Missing --field "Feature=pdf-export"

tcw work new "Export invoices as PDF"  # → 2026-09-09-export-invoices-as-pdf
tcw work start 2026-09-09-export-invoices-as-pdf
#                                      …write the code…
tcw work complete 2026-09-09-export-invoices-as-pdf --resolution done --confirm
tcw capabilities set billing/invoices --status Supported
```

That leaves the whole model on disk — no database, no server, no account:

```
docs/
├── taxonomy/
│   ├── invoice/            meta.yaml, description.md
│   └── pdf-export/         meta.yaml, description.md   ← a Feature, linked to invoice
├── capabilities/
│   └── billing/invoices/   meta.yaml, description.md   ← Status: Supported
└── work/
    ├── inbox/  backlog/  active/  review/
    ├── completed/2026-09-09-export-invoices-as-pdf/
    └── discarded/
```

**A work item's status is the folder it is in.** A transition is a `git mv`, the
board is `ls docs/work/active/`, and there is no separate ledger file to fall out
of step, double-count, or re-summarize. `tcw serve` renders all three axes as a
local web app if you would rather click than type.

## Why many repositories is the case it is built for

Every repository keeps and owns its own taxonomy, capabilities, and board. What
TCW adds on top is one model across all of them:

- **Shared vocabulary, without a silent merge.** A repository can inherit
  another's taxonomy. Terms stay namespaced by the project they came from, so an
  inherited `acme/permission` never quietly becomes your `permission`.
- **Shared user stories, with local overrides.** A web frontend and a mobile app
  driving the same server declare their common capabilities once, and each
  overrides only what differs.
- **Work addressed across the graph.** An item in any registered project is
  addressable as `<project-id>/<slug>`, and one epic can hold slices living in
  several repositories and roll their status back up.
- **One board for the whole estate.** `tcw work list --include-descendants` and
  `tcw serve` aggregate every registered repository's board into a single view,
  and `tcw validate` checks them all in one pass and exits non-zero — so it works
  as a CI gate.

Projects are identified by a canonical ID, never by a filesystem path. A checkout
holding only some of the repositories still works: the absent ones drop out of
the graph rather than breaking your commands.

## What it deliberately refuses

No sprints, no story points, no burndown charts, no SLAs, no estimation ceremony.
Just items, statuses, legal transitions between them, and a definition-of-done
gate. The shorthand for the work component is a **"recursive, OS-native Jira"** —
recursive because projects nest inside one another, and OS-native because the
storage is folders and `git` rather than a service.

Four stances follow from that, and they are worth knowing before you adopt it:

- **State is the status, not a log.** Nothing is reconstructed from history.
- **Per-node, never global.** Each item, term, and capability owns one bounded
  document, so nothing grows without limit.
- **Mechanism in the tool, judgment in the person or agent.** Legal transitions,
  slug integrity, reference validity, and the definition-of-done gate are
  enforced by the CLI, not left to a prose checklist somebody follows sometimes.
- **Co-located with the code it describes.** The documents live in the repository
  and move in its commits and pull requests.

## What adopting it costs

Worth knowing before you propose it to a team:

- **Everyone needs the CLI.** Python 3.11 or newer, and Node 22.12 for the
  optional web viewer. It installs with `pipx`, or automatically as a Claude Code
  or Codex plugin.
- **It does not replace a tracker for people outside the codebase.** There are no
  notifications, no permissions model, no assignee workflow, no dashboards, and
  no way to file or read an item without a checkout. Teams needing those keep
  them, and use TCW for the parts that belong beside the code.
- **The descriptions are only as current as the discipline around them.** TCW
  enforces structure — legal transitions, slug integrity, that every pointer
  resolves — but nothing makes anyone write a good capability description. The
  lifecycle bindings and agent skills exist to make that automatic rather than
  remembered.
- **Adoption is per-repository and incremental.** A repository can adopt the work
  component alone and add taxonomy and capabilities later, or never. There is no
  central instance to stand up first, and no migration required to start.
- **Only filesystem storage exists today** — see
  [Storage abstraction](#storage-abstraction-the-prime-directive).

## Who it's for

- **A product spread across many repositories** that needs one description of
  what it is and one board across all of it, without a central service to run.
- **Agent-driven development**, where a coding agent needs a legible, enforced
  place to record what a project is and where its work stands — and where "told
  to follow the rules" is not enough, because the invariants have to be held
  mechanically.
- **Teams that want their glossary, feature inventory, and change log to move in
  the same commits and pull requests as the code**, instead of in three drifting
  external tools.
- **Anyone who wants a work tracker with no ceremony** that is just folders,
  files, and `git`.

## Storage abstraction (the prime directive)

TCW ships **filesystem-backed stores, and only those today.** Adapters for an
external tracker (Jira, a wiki, a graph database) and tracker synchronization are
designed for but not built; they are open items on TCW's own board.

What exists now is the separation that makes them addable later. The CLI talks to
abstract store interfaces (`TaxonomyStore`, `CapabilitiesStore`, `WorkStore`) and
the shipped adapters (`FsTaxonomyStore`, `FsCapabilitiesStore`, `FsWorkStore`)
realize them on the filesystem. Every operation must pass one test before it
enters the model:

> **"Could a non-filesystem store implement this operation, even if less
> elegantly?"**
> Yes → it belongs in the model (the abstract store interface). No → it is a
> filesystem-adapter detail, or it gets redesigned.

So the filesystem advantages — co-located documents, atomic commits, readable
diffs and pull requests, `mv` as a status transition — are layered on top rather
than assumed by the model. The full rules live in
[`docs/lifecycle/abstraction.md`](docs/lifecycle/abstraction.md), which TCW's own
repository binds to its `spec` and `plan` stages.

---

## Install

### As a plugin (recommended)

In **Claude Code**:

```
/plugin marketplace add brocef/TCW
/plugin install tcw
```

Or, in the Claude **web app** or **desktop app**, open the plugin directory, add
`brocef/TCW` as a marketplace, and install `tcw` from it — no terminal needed.

**Then start a new session.** The plugin installs the `tcw` CLI at session start
by installing `tcw-cli` from PyPI with `pipx`, so one installed mid-session
cannot run until the next one begins. That first session needs network access. It
installs over an existing `pipx install tcw-cli` rather than beside it, and
leaves a development checkout (`pip install -e .`) alone. If `tcw` goes missing
anyway, `pipx install tcw-cli` is the whole fix — the **`tcw-setup`** skill
carries the cases where it is not.

In **Codex**:

```bash
codex plugin marketplace add brocef/TCW --ref main
codex plugin add tcw@tcw
```

Codex has no session-start hook, so ask the agent to run the **`tcw-setup`**
skill — it runs the same install script Claude runs automatically.

The plugin ships the agent skills, command skills, and read-only review agents
listed under [Skills](#skills--the-judgment-layer).

### As a Python package

```sh
pipx install tcw-cli        # recommended (isolated, on PATH)
pip install -e .            # development install from a clone
```

Use this when you want the CLI without an agent harness at all. The PyPI package
is named **`tcw-cli`** because `tcw` was taken by an unrelated project; the
command it installs is still `tcw`.

Requires **Python ≥ 3.11** (its only runtime dependency is PyYAML). `tcw serve`
additionally requires **Node.js ≥ 22.12**; every other command is Python-only.
Released wheels carry the prebuilt web assets, so there is no frontend build step
and no network needed after install.

### In a cloud environment

A cloud agent session — Claude Code on the web, a Codex container, a CI job —
starts from a clean image and is thrown away when it ends, so a `tcw` you install
by hand is gone by the next one. Install it **from your repository**, with a
session-start hook, and every session gets it without anyone remembering to.

Add a script to your repository:

```sh
#!/usr/bin/env bash
# Make `tcw` available in a disposable agent container.
# Exit 0 on every path — a session must start even when this cannot finish.
set -u

command -v tcw >/dev/null 2>&1 && exit 0

# pipx where it exists; otherwise install into the container's own interpreter.
# That is the right answer *here* and nowhere else: the container is disposable
# and single-purpose, so there is no user environment to damage.
if command -v pipx >/dev/null 2>&1; then
    pipx install tcw-cli >/dev/null 2>&1 || echo "tcw: pipx install tcw-cli failed"
elif ! python3 -m pip install tcw-cli >/dev/null 2>&1 &&
    ! python3 -m pip install tcw-cli --break-system-packages >/dev/null 2>&1; then
    echo "tcw: pip install tcw-cli failed — the tcw CLI is not available."
fi

# An install that landed outside PATH is installed and unusable. $CLAUDE_ENV_FILE
# is the harness's own channel for repairing that.
if ! command -v tcw >/dev/null 2>&1 && [ -n "${CLAUDE_ENV_FILE:-}" ]; then
    userbin="$(python3 -m site --user-base 2>/dev/null)/bin"
    [ -x "$userbin/tcw" ] && echo "export PATH=\"$userbin:\$PATH\"" >>"$CLAUDE_ENV_FILE"
fi

exit 0
```

Then wire it to `SessionStart` in your repository's `.claude/settings.json`:

```json
{
    "hooks": {
        "SessionStart": [
            {
                "hooks": [
                    {
                        "type": "command",
                        "command": "\"${CLAUDE_PROJECT_DIR}\"/scripts/tcw_session_setup.sh"
                    }
                ]
            }
        ]
    }
}
```

Three things make the difference between a hook that helps and one that wastes a
session:

- **Exit 0 on every path, and print only on failure.** A hook that fails the
  session start over a missing CLI has cost more than the CLI was worth.
- **Print to stdout.** Claude Code adds a `SessionStart` hook's stdout to the
  agent's context, where it will be read; stderr becomes a transcript notice
  nobody sees.
- **Check for `tcw` first.** The hook runs every session, including the ones
  where a previous install is still there.

**If your work store lives in another repository**, the container holds only the
repository it cloned, so the board is declared but absent. Run `tcw provision`
after the install — it obtains what the checkout does not have, and does nothing
on a machine that already holds it. See
[Working across repositories](docs/guide/multi-repo.md).

Installing the **plugin** in such a session is a separate step from installing the
CLI, and only needed where the harness does not carry your plugins in: append
`claude plugin marketplace add brocef/TCW` and `claude plugin install tcw@tcw` to
the same script, guarded on `command -v claude`.

This repository's own [`scripts/remote_session_setup.sh`](scripts/remote_session_setup.sh)
is the same pattern written for a _contributor_ rather than a user — it installs
the checkout with `pip install -e` instead of the release from PyPI, and installs
the plugin from the checkout too. Read it as the worked example.

## Quickstart

```sh
cd your-git-repo
tcw init --id my-project                # scaffold all three components
tcw init --id my-project taxonomy work  # …or just named components
tcw serve --no-open                     # browse all three locally
tcw validate                            # check this project and its descendants
tcw --help                              # init | serve | validate | taxonomy | capabilities | work
```

`tcw init --id <project-id>` marks the **current directory** as a TCW node by
writing a `tcw-config.yaml` file carrying its canonical ID, then scaffolds the
`docs/<component>/` skeletons. It refuses to run outside a git repository,
because write transitions need git — but the node folder can sit anywhere inside
that repository, not only at its root, so one repository can hold several
projects. Each component group also has its own `init`: `tcw taxonomy init`,
`tcw capabilities init`, `tcw work init`.

To bootstrap a taxonomy or capabilities ledger on a project that already has a
codebase, ask for the `tcw-setup` skill — the assistant studies your code,
proposes a first draft, refines it with you, and writes it. To change a working
project's configuration afterwards — documentation entries, lifecycle bindings,
a tracker, where stores live — ask for the `tcw-configure` skill.

---

## Working from your Jira tickets

A project can name the Jira Cloud site it uses, read its tickets, and take one as
a work item.

```sh
tcw work tracker list              # tickets the configured query selects
tcw work tracker show ENG-482      # one ticket, and whether it is yours to take
tcw work tracker import ENG-482    # take the ticket and get a work item for it
tcw work tracker link <slug> ENG-482       # record that an item and a ticket are the same work
tcw work tracker unlink <slug> --reason "wrong ticket"
tcw work tracker sync --all        # retry tickets that did not follow their items
```

Configuration goes in the node's `tcw-config.yaml`:

```yaml
work:
    tracker:
        provider: jira-cloud
        base-url: https://yourcompany.atlassian.net
        candidate-query: assignee = currentUser() AND status = "To Do"
        credentials:
            email-env: TCW_JIRA_EMAIL
            token-env: TCW_JIRA_API_TOKEN
        transitions:
            claim: Start Progress
        statuses: # optional: where a bound ticket goes as its item moves
            active: In Progress
            review: In Review
            completed: Done
            discarded: Won't Do
        timeout-seconds: 15 # optional
```

**Credentials are named, never stored.** The file holds the names of two
environment variables; TCW reads them at the moment it makes a request, so a token
cannot be committed by accident.

**Write the shared settings once.** In a workspace of connected nodes, a node's
`tracker` block takes any setting it leaves out from its parent nodes, all the way
up. So the site, credentials and claim transition can live in the workspace root,
and each package writes only the tickets it wants to see:

```yaml
# packages/api/tcw-config.yaml
work:
    tracker:
        candidate-query: project = EX AND component = api AND status = "To Do"
```

The nearest file wins each setting, and `credentials` and `transitions` merge
setting by setting too. A node with no `tracker` block of its own has no tracker,
whatever its parents say. Two rules keep this safe:

- **`credentials` must sit beside `base-url`.** A node that sets its own `base-url`
  must also set both of its own `credentials` keys, even if the address is the same
  as its parent's, so a token is never sent to a site chosen in a different file.
- **A node with its own board is checked like any tracking node.** If it holds the
  shared settings, it needs a `candidate-query` of its own. Keeping shared settings
  in a node without a board avoids that.

A mistake in a parent's settings is reported by `tcw validate` in every node that
inherits it, naming the parent's file.

`tracker show` reports two different things, and the distinction matters:

- **claimable** — whether this ticket currently offers the transition you
  configured as the claim.
- **exclusive** — whether your Jira workflow would actually refuse a second person
  trying to take the same ticket.

Many Jira workflows allow a status change from any status, including the one it
leads to. On a workflow like that, two people who both take one ticket both
succeed and neither is told. So a ticket that has been started reports
`not exclusive` when that is the truth, and a ticket that has not been started
reports `not determined`, because it cannot show you what happens to the second
person. Making a workflow exclusive is a Jira administration change, not something
TCW can do for you.

**Taking a ticket.** `tracker import` moves the ticket through your configured
claim transition, assigns it to you if nobody had it, and then checks Jira again:
only when the ticket really is started and yours does it create a backlog item. The
ticket's text goes into the item as its raw input, with a link back, and the item's
request still gets written the usual way. A ticket assigned to someone else is
refused, and so is one that is already closed.

Running `import` again for the same ticket in the same node gives you the same item
rather than a second one, and if the first run took the ticket but stopped before creating the
item, the second run finishes the job. One ticket can deliberately become several
items with `--part api`, `--part web`, and so on.

**Recording that a ticket and an item are the same work.** `tracker link` is the
other half, and it does only that: it writes the cross-reference down and leaves
Jira alone. The ticket keeps its status and whoever holds it — you can link a ticket
somebody else is assigned, because writing a note about a ticket takes it from
nobody. On your side nothing but the binding is written, so the item keeps its
status, its owner and its documents. Any item can be linked, a finished one
included, which is how work that is already done gets tied to the ticket that
tracked it; the same goes for `unlink`, so a binding pointed at the wrong ticket is
repairable wherever you find it. A finished item's folder is kept out of git by
default, so a binding on one stays on your machine along with the rest of that
item. `unlink` keeps a record of what was bound and your
reason, and like `link` it never changes the ticket in Jira.

**Seeing which ticket an item answers.** A bound item says so wherever you read it:
`tcw work show` adds a `tracker:` line with the ticket, the provider, the part and
the ticket's link; its row on `tcw work list` ends with the ticket key; `tcw work show
--json` carries it as `tracker`; and `tcw serve`'s item page shows the ticket as a
link. What you see is what the binding records, not what Jira says right now, so
none of it needs the tracker configured or reachable. A binding file that cannot be
read is reported in the same places instead of breaking the board.

**Tickets follow their items.** `link` claims nothing, so `tcw work start` does:
starting a bound item claims its ticket by the same rules `import` uses. After that,
`submit`, `rework`, `complete` and discarding move the ticket to the status you map
the item's new status to under `statuses` (`discarded` can name a status per
resolution, such as `duplicate: Duplicate`); a status you leave out sends nothing,
and `active` is required once you map any other. `import` on a ticket that is only
linked still refuses rather than claiming it.

TCW moves a ticket only when it is assigned to you and is still where the item's
previous status left it. A ticket someone else holds, one moved on in Jira, or one
whose workflow does not offer a single transition to the mapped status is left
alone. Your local move always happens and is committed first; when the ticket does
not follow, the command exits 1, says the item moved, and records why — *pending*
when Jira could not be reached or your credentials are missing, *conflicting* when
Jira's answer stopped it. `tcw work show` and `tcw work list` show that state, and
`tcw work tracker sync <slug>` (or `--all`) retries it once the cause is fixed. `sync`
acts only on items you started, because it acts as whoever runs it. A ticket that
followed first time leaves no record and no change in your repository.

Two things are not caught: a move made in `tcw serve`, and a command interrupted
between its commit and its call to Jira, leave no record, so the board shows them as
in step; `sync <slug>` checks such an item but will not move its ticket. And a
binding whose ticket link is on a different Jira site from the one configured is
never written through — `import` and `link` refuse it and name the item.

Five limits to know. A ticket bound to several parts moves only when the last open
part here moves; parts in other nodes are not seen. On a workflow that lets anyone start a ticket from any status,
two people can both take the same ticket, and TCW does not stop that outside strict
mode (below). Two runs by the
same Jira account at the same moment can both create an item. Each node keeps its
own bindings: importing one ticket in two nodes of a workspace, even nodes sharing
inherited settings, gives two items, one in each. And a ticket held by a finished
item can be bound to a second item, open or finished, with no warning — a discarded
item's ticket is meant to be available again, and TCW cannot tell that case from the
other.

**Comments on the ticket.** Set `comments: true` in the `tracker` block and each
move also leaves a short comment on the ticket, such as
`TCW: "Checkout page" (part api) went to review.`, for anyone who follows the work
in Jira rather than in the repository. A `link` template adds a link, for example
`link: https://tcw.example.com/work/{slug}` for a team that hosts `tcw serve`; the
only placeholders are `{project}` and `{slug}`. Nothing from `spec.md`, `plan.md` or
the other lifecycle documents is ever copied. A comment is posted only while the
ticket is assigned to you, and a ticket held by someone else gets none. When a
comment cannot be posted, the command exits 1, `show` prints a `tracker comment:`
line, and `tcw work tracker sync` sends it later. Before resending, it looks for the
comment on the ticket, so a post that landed without an answer is not repeated.
Limits: a newer move's comment replaces one still waiting; two runs at once, or an
edited or deleted comment, can still give a repeat; moves in `tcw serve` post
nothing. On a Jira Service Management project a comment may be visible to
customers, so leave comments off there unless item titles may be seen. Every copy
of `tcw` on the project must understand these keys before you set them: an older
one treats the whole `tracker` block as broken.

**Strict mode: no work without a ticket.** Set `strict: true` in the `tracker` block
when every piece of work must come from a ticket you have claimed. Then:

- `tcw work new` and `tcw work inbox accept` refuse and point you at
  `tcw work tracker import <ticket>`. `new --epic` is allowed; epics are never gated.
- `tcw work start` refuses an item with no ticket. For a bound item it claims the
  ticket *first*, and starts the item only if the claim worked.
- `submit`, `rework` and completing as `done` read the ticket first and refuse unless
  it is assigned to you and is where the item's last step left it. A `--worktree`
  item is checked before anything is merged.
- A claim on a workflow that would let a second person claim the same ticket is
  refused, by `start` and by `import`; the ticket is left claimed for you to release.
- An epic can be created and started, since it only groups work, but not with
  `--worktree`.
- A ticket shared by several parts is recognised only from the parts' items in
  this checkout. If the part that held the ticket back was completed elsewhere, or
  was not kept (`work.retain`), the last part's `complete` is refused; put the
  ticket in the status the message names, or discard.
- Discarding is always allowed. `drop` refuses an item that was ever bound — discard
  it instead, so the record stays.
- `tcw serve` refuses the same changes, since it cannot check a ticket, and names the
  command to use.

A refusal changes nothing in your project and says what to fix; a `start` or `import`
refused after claiming leaves the ticket claimed. There is no flag to get past it;
`--force` and `--take-over` do not. Strict mode needs Jira: while it cannot be
reached, gated commands refuse. It also needs `statuses.active`,
`statuses.completed` and a `statuses.discarded` covering every discard reason, which
`tcw validate` checks. To turn it off, set `strict: false` or remove the key.

Two guarantees worth stating plainly. A project with no `tracker` block behaves
exactly as before, with no new required setting and no network access. And
`tcw validate` never contacts the tracker, which matters because projects commonly
run it when closing a work item — finishing your work must not depend on Jira being
reachable.

---

## Documentation

| Document                                                             | Covers                                                                                                                 |
| -------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| [The Work component](docs/guide/work.md)                             | The state machine, the command reference, tags, the definition-of-done gate, decomposition, and cross-repository epics |
| [Taxonomy and Capabilities](docs/guide/taxonomy-and-capabilities.md) | Declaring the nouns and the user stories, and federating both across projects                                          |
| [Working across repositories](docs/guide/multi-repo.md)              | Connecting projects, keeping a store in another repository, and obtaining what a checkout does not have                |
| [Configuration](docs/guide/configuration.md)                         | `tcw-config.yaml`: lifecycle bindings, prompts, artifact templates, and documentation entries                          |
| [The local web viewer](docs/guide/web-viewer.md)                     | `tcw serve`                                                                                                            |
| [Linking and validation](docs/guide/linking-and-validation.md)       | `tcw://` references between objects, and `tcw validate` as a CI gate                                                   |
| [The abstraction rules](docs/lifecycle/abstraction.md)               | The prime directive in full                                                                                            |
| [Releasing TCW](docs/releasing.md)                                   | How this repository publishes itself — not needed to use TCW                                                           |

Every command group also has `--help`, and a `check` that validates its tree.

---

## Skills — the judgment layer

The CLI is the _mechanism_. Fifteen skills in [`skills/`](skills/) supply the
_judgment_ that drives it — the parts a deterministic tool cannot decide. They
come in three groups, told apart by name: eight core skills (seven in the table
below, and `tcw-work-stage`, which composes a lifecycle stage and is described
after it), four `tcw-commands-*` skills for the everyday workflow, and three
optional `tcw-extras-*` skills.

| Skill                                                      | What it does                                                                                                                                               |
| ---------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [`tcw-work`](skills/tcw-work/SKILL.md)                     | Plans a request through spec and plan, drives implementation and verification, triages the inbox, runs the lifecycle, decomposes epics, searches the board |
| [`tcw-capabilities`](skills/tcw-capabilities/SKILL.md)     | The capability-delta planning check, contradiction detection, and the ledger flip at completion                                                            |
| [`tcw-taxonomy`](skills/tcw-taxonomy/SKILL.md)             | Declaring vocabulary and features, linking them, and resolving vocabulary inherited from another project                                                   |
| [`tcw-setup`](skills/tcw-setup/SKILL.md)                   | Gets TCW working: installs or repairs the CLI, sets up a repository, starts a taxonomy or capabilities ledger                                              |
| [`tcw-configure`](skills/tcw-configure/SKILL.md)           | Changes a project's configuration: lifecycle bindings, Definition of Done, documentation entries, tracker, stores, connected and inherited projects        |
| [`documentation-sync`](skills/documentation-sync/SKILL.md) | Keeps README, changelogs, release notes, and driving skills moving with the code that changes them                                                         |
| [`tcw-post-mortem`](skills/tcw-post-mortem/SKILL.md)       | Finds which lifecycle stage could first have caught a problem, once one has surfaced                                                                       |

**Extras.** `tcw-extras-*` skills are optional, built for one way of working, and not needed to use TCW.

| Skill | What it does |
| ----- | ------------ |
| [`tcw-extras-autonomous-work`](skills/tcw-extras-autonomous-work/SKILL.md) | Drives work items to completion unattended, consulting two read-only advisors wherever the lifecycle would ask you                                         |
| [`tcw-extras-triage-issues`](skills/tcw-extras-triage-issues/SKILL.md) | Sweeps **your** project's GitHub issues and turns the ones worth doing into work items                                                                     |
| [`tcw-extras-report`](skills/tcw-extras-report/SKILL.md) | Reporting a `tcw` bug or suggestion upstream to [this project's issues](https://github.com/brocef/TCW/issues)                                              |

They name `tcw` commands and never reimplement tool logic: mechanism stays in the
binary, judgment stays in the skills.

### Reading a lifecycle stage

One more skill, [`tcw-work-stage`](skills/tcw-work-stage/SKILL.md), hands you a
stage's own working document and the instructions your project resolves for it,
as a single read rather than a file you open and a command you run separately.
It takes the stage id and the work item, so it reaches all seven stages
including `inbox` and `postmortem`, under Claude and Codex alike. It only reads
— `tcw work stage gate` is still what refuses.

### Review agents and command skills

Three read-only review agents ship alongside them — `tcw-verifier`,
`tcw-backlog-auditor`, and `tcw-post-mortem`, which accelerates the skill of the
same name. Four command skills carry the everyday workflows:
`tcw-commands-plan-work`, `tcw-commands-drive-work-to-completion`,
`tcw-commands-verify-work` and `tcw-commands-process-inbox`. The three extras,
`tcw-extras-autonomous-work`, `tcw-extras-triage-issues` and
`tcw-extras-report`, are optional. Under Claude and Codex alike, every entry
point is a skill.

---

## Status

TCW is used daily to manage its own development: this repository tracks all of
its own work through `docs/work/`.

**Built and in use.**

| Area                    | State                                                                                                |
| ----------------------- | ---------------------------------------------------------------------------------------------------- |
| The three axes          | Taxonomy, capabilities, and work all ship with filesystem stores on a shared bounded-tree core       |
| Cross-repository work   | Connected projects, graph-wide addressing, epics, delegate/escalate, rollup, and isolating worktrees |
| Web viewer              | `tcw serve` browses and edits all three axes, aggregating descendant boards                          |
| Lifecycle customization | Per-stage prompts, artifact templates, and pre-transition checks bound from `tcw-config.yaml`        |
| Agent integration       | A Claude Code and Codex plugin carrying skills, commands, and review agents                          |
| Tests                   | pytest over throwaway git repositories, plus Playwright end-to-end coverage of the viewer            |

**Not built.** Store adapters for external trackers — Jira, a wiki, a graph
database — and synchronization with them. The abstract store interfaces they
would implement exist and are what every command already talks to, but no such
adapter ships today. They are open items on TCW's own backlog.

## Further reading

- [`AGENTS.md`](AGENTS.md) — the working rules for contributing (read first).
- [`docs/lifecycle/abstraction.md`](docs/lifecycle/abstraction.md) — the prime directive in full.
- [`docs/plan/`](docs/plan/) — the per-component source-of-truth designs.
- `tcw work list` — what is currently being changed here.
