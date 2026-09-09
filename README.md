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
leaves a development checkout (`pip install -e .`) alone. Run `/tcw-doctor` any
time `tcw` goes missing or looks wrong.

In **Codex** (skills only, no slash commands):

```bash
codex plugin marketplace add brocef/TCW --ref main
codex plugin add tcw@tcw
```

Codex has no session-start hook, so ask the agent to run the **`tcw-plugin`**
setup — it runs the same install script Claude runs automatically.

The plugin ships the agent skills, slash commands, and read-only review agents
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
codebase, run `/tcw-taxonomy-init` or `/tcw-capabilities-init` — the assistant
studies your code, proposes a first draft, refines it with you, and writes it.

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

The CLI is the _mechanism_. Seven skills in [`skills/`](skills/) supply the
_judgment_ that drives it — the parts a deterministic tool cannot decide.

| Skill                                                      | What it does                                                                                                                           |
| ---------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| [`tcw-work`](skills/tcw-work/SKILL.md)                     | Plans a request through spec and plan, drives implementation and verification, triages the inbox, runs the lifecycle, decomposes epics |
| [`tcw-capabilities`](skills/tcw-capabilities/SKILL.md)     | The capability-delta planning check, contradiction detection, and the ledger flip at completion                                        |
| [`tcw-taxonomy`](skills/tcw-taxonomy/SKILL.md)             | Declaring vocabulary and features, linking them, and federating shared vocabulary                                                      |
| [`tcw-plugin`](skills/tcw-plugin/SKILL.md)                 | Installs and repairs the CLI; the source of the `/tcw-doctor` procedure                                                                |
| [`tcw-report`](skills/tcw-report/SKILL.md)                 | Reporting a `tcw` bug or suggestion upstream to [this project's issues](https://github.com/brocef/TCW/issues)                          |
| [`tcw-triage-issues`](skills/tcw-triage-issues/SKILL.md)   | Sweeps **your** project's GitHub issues and turns the ones worth doing into work items                                                 |
| [`documentation-sync`](skills/documentation-sync/SKILL.md) | Keeps README, changelogs, release notes, and driving skills moving with the code that changes them                                     |

They name `tcw` commands and never reimplement tool logic: mechanism stays in the
binary, judgment stays in the skills.

Two read-only review agents ship alongside them — `tcw-verifier` and
`tcw-post-mortem` — plus slash commands for each skill's main procedure
(`/tcw-plan-work`, `/tcw-drive-work-to-completion`, `/tcw-verify-work`,
`/tcw-process-inbox`, `/tcw-triage-issues`, `/tcw-audit-work-backlog`,
`/tcw-taxonomy-init`, `/tcw-capabilities-init`, `/tcw-docs-sync-setup`,
`/tcw-cut-version`, `/tcw-post-mortem`, `/tcw-doctor`).

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
