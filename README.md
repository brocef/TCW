# TCW — Taxonomy · Capabilities · Work

A storage-abstracted framework for **describing and evolving a software project
along three axes**, exposed through one CLI (`tcw`) with three subcommand groups.

| Component | Is | Holds |
|---|---|---|
| **Taxonomy** | the nouns | the *things* an app deals with — domain entities, with a real glossary and ontology |
| **Capabilities** | the user stories | what a user can *do* with those things — each a miniature user story |
| **Work** | the changes | edits to capabilities (product), machinery (technical), or the project itself (meta) |

The three link by **loose, one-directional pointers** (capability → term,
work → capability/term) and never duplicate each other. Taxonomy is the
vocabulary, capabilities are the user-facing surface, and work is the change
layer that moves capabilities and machinery forward over time.

---

## Why this exists

Most projects scatter their "what" and "why" across a dozen unsynchronized
places: a tracker for tickets, a wiki for glossaries, a `FOLLOWUPS.md` that
grows without bound, design docs that drift from code, and a planning flow where
documents *jump* between unrelated trees with no "where is this right now?"
spine. State lives everywhere and nowhere; reconstructing the current picture
means reading all of it and trusting none of it.

TCW started as an effort to fix exactly that for an agent-driven SDLC, and the
unlocking insight was that several separate-looking problems —

- no single, durable source of truth for *where a piece of work is*,
- a glossary nobody could point at,
- capability docs that drifted from the code,
- a follow-up log that rotted,
- cross-repo coordination that lived only in prose —

were all facets of **one** missing thing: a *durable, legible, per-node source
of truth* for a project's nouns, user stories, and changes. TCW is that source
of truth, built on a deliberate stance:

- **State is the status, not a log.** A work item's status *is which directory
  it lives in*; a transition is a `git mv`. The "board" is `ls active/`. There
  is no global ledger file to drift, double-count, or burn tokens
  re-summarizing.
- **Per-node, never global.** Each item, term, and capability owns one bounded
  document. Nothing grows without limit; nothing has to be reconstructed from
  history.
- **Mechanism in the tool, judgment in the human/agent.** Legal transitions,
  slug integrity, reference validity, and the Definition-of-Done gate are
  *enforced* by a deterministic CLI — not left to a prose checklist that gets
  followed only sometimes.
- **Co-located with the code it describes.** The docs live in the repo. One
  atomic commit can carry a code change *and* its status/capability change
  together, reviewable in the same diff.

The shorthand for the work component is a **"recursive, OS-native Jira"** — and
just as important is what it deliberately *refuses*: no sprints, no story
points, no burndown charts, no SLAs, no estimation ceremony. Just items,
statuses, legal transitions, and a done-gate.

## Storage abstraction (the prime directive)

TCW ships a **filesystem-native default**, but the *model* is storage-abstracted
so it can run against an external tracker (Jira, a wiki, a graph DB) where one is
already in use. That portability is what makes it viable at enterprise scale.
Every operation has to pass one test:

> **"Could a non-filesystem store implement this operation, even if less
> elegantly?"**
> Yes → it belongs in the model (the abstract store interface). No → it's a
> filesystem-adapter detail, or it gets redesigned.

So the CLI talks to abstract store interfaces (`TaxonomyStore`,
`CapabilitiesStore`, `WorkStore`); the shipped adapters (`FsTaxonomyStore`,
`FsCapabilitiesStore`, `FsWorkStore`) realize them on the filesystem. The
filesystem superpowers — co-located docs, atomic commits, grep/diff/PR
legibility, `mv`-as-transition — are *bonuses layered on top*, never
load-bearing assumptions of the model. The full rules live in
[`AGENTS.md`](AGENTS.md).

## Who it's for

- **Agent-driven development**, where an LLM needs a legible, enforced place to
  record what a project is and where its work stands — and where "told to follow
  the rules" isn't enough, because the invariants must be *mechanically* held.
- **Teams that want their domain glossary, feature inventory, and change log to
  live next to the code** and move in the same commits and PRs, instead of in
  three drifting external tools.
- **Anyone who wants a no-ceremony work tracker** that is just folders, files,
  and `git`, but can later be pointed at a real tracker without rewriting how the
  project is described.

---

## Install

### As a plugin (recommended)

In **Claude Code**:

```
/plugin marketplace add brocef/TCW
/plugin install tcw
/tcw-init        # installs the `tcw` CLI from the plugin's own clone (via pipx)
```

This ships the `tcw-work`, `tcw-capabilities`, and `tcw-plugin` skills plus the
`/tcw-init` and `/tcw-doctor` commands. `/tcw-init` puts the `tcw` CLI on your
PATH from the plugin's *own clone*, so there's one copy — **don't also
`pip install tcw` separately**, or the two can drift (`/tcw-doctor` detects this
and re-points). Run `/tcw-doctor` any time `tcw` goes missing or a plugin update
leaves it stale.

In **Codex** (no slash commands — skills only):

```bash
codex plugin marketplace add brocef/TCW --ref main
codex plugin add tcw@tcw
```

Then ask the agent to run the **`tcw-plugin`** setup — it installs the `tcw` CLI
from the plugin clone the same way `/tcw-init` does.

### As a Python package

```sh
pipx install tcw            # once published — recommended (isolated, on PATH)
pip install -e .            # development install from a clone
```

`tcw` is a real Python package (entry point `tcw = tcw.cli:main`), not a
symlink. Requires Python ≥ 3.11; the only runtime dependency is PyYAML.

## Quickstart

```sh
cd your-git-repo
tcw init                    # scaffold docs/{taxonomy,capabilities,work}/
tcw init taxonomy work      # …or just the components you name
tcw --help                  # top-level groups: init | taxonomy | capabilities | work
```

`tcw init` operates on the current git work-tree and refuses outside a git repo.
Each component is a tree of docs under `docs/<component>/`.

---

## Usage

Every group has a `--help`, a `check` that validates the tree, and a bare-path
shortcut (`tcw taxonomy <path>` == `tcw taxonomy show <path>`).

### `tcw taxonomy` — the nouns

Terms form a **forest, and the slug *is* the path**: `admin/permission` is a
different term from `billing/permission`, and addressing is by that path.

```sh
tcw taxonomy add Invoice "A bill issued to a customer."     # root-level term
tcw taxonomy add Permission -p admin                        # → admin/permission
tcw taxonomy add Note -p invoice -s memo                    # custom leaf slug

tcw taxonomy list                  # the forest, indented, flagged by origin
tcw taxonomy list --local          # local terms only (hide imported)
tcw taxonomy show admin/permission # read one term (or: tcw taxonomy admin/permission)
tcw taxonomy search invoice        # match names + descriptions
tcw taxonomy check                 # validate aliases + references
```

A term's body comes from the argument or from **stdin** (`echo "..." | tcw
taxonomy add Foo`). Taxonomies can **federate**: a `config.yaml` maps a
consumer-chosen alias to a source taxonomy via `extends`, each alias is its own
namespace, and there is **no silent merge** — a local `permission` and an
imported `acme/permission` stay distinct. (Vocabulary is canonical-shared, so
taxonomy federates *directly*, unlike capabilities.)

### `tcw capabilities` — the user stories

A capability is one `## heading` user story inside a `capabilities.md`,
addressed as `namespace/path#heading`. Each carries metadata fields — notably
**`Subject:`** (a loose pointer to a taxonomy term) and **`Planning doc:`** (the
forward pointer to a work item).

```sh
tcw capabilities add billing/invoices "Download an invoice as PDF"
tcw capabilities add billing/invoices --folder        # scaffold a folder + capabilities.md

tcw capabilities list                      # every capability, flagged by status
tcw capabilities list --status Missing     # filter by status
tcw capabilities show billing/invoices     # whole file…
tcw capabilities show billing/invoices#download-an-invoice-as-pdf   # …or one heading
tcw capabilities search pdf
tcw capabilities check                     # identifiers, metadata vocab, Subject refs

tcw capabilities set billing/invoices#download-an-invoice-as-pdf --status Supported
tcw capabilities set billing/invoices --field "Planning doc=2026-06-19-pdf-export"
```

`set` updates a capability's status/fields in place (stage-only) — the mechanism
the work→capability lifecycle uses to flip `Missing → Supported` at completion.
A `#heading` is required when a file holds more than one capability.

Status is one of `Supported · Partial · Missing · Blocked · Omitted`. `check`
validates the metadata vocabulary *and* resolves each `Subject:` pointer against
the taxonomy store — the one cross-component link, kept loose: the tool never
parses capability prose, it only follows pointers.

### `tcw work` — the changes

Work is a **single-node state machine** where status is the folder a work item
lives in, and a transition is a move between folders:

```
inbox  →  backlog  →  active
                         ↓
                     completed        (drop: delete from inbox|backlog)
```

Blocked-ness is a **derived overlay**: an item is blocked when it has at least
one unresolved blocker recorded in its data — there is no separate "blocked"
folder or status.

```sh
tcw work init                          # docs/work/{inbox,backlog,active,completed}/

slug=$(tcw work new "Add PDF export")  # creates a backlog item, prints its slug
tcw work new "Add PDF export" --blocked-by "other-slug,external:JIRA-123"
                                       # create with blockers pre-attached
tcw work new "Urgent fix" --priority 5 # integer priority (higher = higher); default unspecified
tcw work list                          # the board: priority first, then topologically ordered (hides completed)
tcw work list --status active          # filter to one column
tcw work list --all                    # include completed items too
tcw work show "$slug"                  # state + body (includes blocked_by if set)
tcw work path "$slug"                  # current filesystem path of the slug

tcw work start "$slug"                 # inbox|backlog → active (refused if blocked)
tcw work start "$slug" --force         # override unresolved blockers

tcw work edit "$slug" --blocked-by other-slug    # record a new blocker
tcw work edit "$slug" --blocks downstream-slug   # this item now blocks another
tcw work edit "$slug" --unblocked-by other-slug  # clear a resolved blocker
tcw work edit "$slug" --priority 9               # set/raise integer priority

tcw work complete "$slug" --resolution done --confirm
tcw work complete "$slug" --resolution done --confirm --force   # override blockers
tcw work drop some-slug                # delete an inbox|backlog item
```

The **board** (`tcw work list`) prints a row per item —
`slug  status  phase  priority  title` (priority is the integer, or `-` when
unspecified). It shows the live columns (inbox, backlog, active) and hides
completed items by default — pass `--status completed` to list them or `--all`
for everything. It sorts by priority first (higher integer above lower,
unspecified-priority items keeping creation order), then topologically — blockers
appear before the items they block, since a priority preference can't jump a hard
dependency — and annotates blocked items with their unresolved blockers.

Items are referenced by a **stable slug**, resolved to "wherever it now lives,"
so moves never break references. Only the legal transitions above are permitted
— anything else is refused, not silently allowed.

**Completion is gated.** `tcw work complete` prints the Definition of Done and
refuses without `--confirm` (and without `--force` if unresolved blockers exist):

```
Definition of Done — acknowledge each item:
  [ ] tests pass
  [ ] docs synced
  [ ] capabilities reconciled
  [ ] reviewed
  [ ] version offered
```

Resolutions are `done · wontfix · duplicate · superseded`. The
"capabilities reconciled" item is the structural link back to the capabilities
axis: a work item declares its capability delta at creation and reconciles it at
completion, so the standing capability ledger stays current by construction.

#### Cross-node recursion (epics across repos)

Any git repo with a `docs/work/` is a **node**; "orchestrator" and "project" are
relative roles. A node nested under another is a **child**, the enclosing one its
**parent**. An **epic** is an ordinary work item that tasks in child nodes point
at via an `initiative:` back-pointer.

```sh
tcw work nodes                              # show this node's parent + child nodes

epic=$(tcw work new "Redesign checkout" --epic)
tcw work new "Slice 1" --initiative "$epic" # in a child node: link a new task to the epic
tcw work edit "$slug" --initiative "$epic"  # …or link an existing one

tcw work reconcile "$epic"                  # scan child nodes → rollup into the epic
tcw work reconcile "$epic" --commit         # …and commit it

echo "needs an API change" | tcw work delegate child-repo "Expose X"  # request DOWN to a child inbox/
echo "cross-repo scope"    | tcw work escalate "Coordinate the redesign" # request UP to the parent inbox/
```

`reconcile` consolidates every child task for an initiative into a managed
rollup block in the epic's `content.md` — a slice table, surfaced capability
deltas, and the next ready actions — and is **read-only** on the capabilities
ledger. `delegate`/`escalate` only ever write a request into the target node's
`inbox/`, never its tracked work, respecting the node write-boundary.

Run an item in an isolated checkout with `--worktree`:

```sh
tcw work start "$slug" --worktree           # active on trunk + a git worktree/branch for the code
```

Status transitions stay on the node's primary checkout (the board is always
`ls active/`); in-flight edits live on the work branch and merge back. `complete`
runs once the branch is integrated and tears the worktree down.

---

## Skills — the judgment layer

The CLI is the *mechanism*; three skills in [`skills/`](skills/) are the *judgment*
that drives it (the work↔capability lifecycle the tool only enforces structurally):

- **[`tcw-work`](skills/tcw-work/SKILL.md)** — triage a `docs/work/inbox`, plan a
  change product-first along the three axes, run the start/complete lifecycle,
  resume an active item, and decompose work into a cross-node epic.
- **[`tcw-capabilities`](skills/tcw-capabilities/SKILL.md)** — the `## Capability
  changes` planning gate, contradiction-detection, the `Missing → Supported`
  ledger flip at completion, and product-layer wording coordination.
- **[`tcw-plugin`](skills/tcw-plugin/SKILL.md)** — install/repair the `tcw` CLI
  from the plugin's own clone (pipx); the single source of the `/tcw-init` and
  `/tcw-doctor` procedure, and the Codex shim for them.

They name `tcw …` commands (and, for `tcw-plugin`, `pipx`) and never reimplement
tool logic — mechanism stays in the binary, judgment in the skills.

---

## Status

**The single-node core is built.** Phases 1–5 are complete: `tcw` installs and
exposes `init | taxonomy | capabilities | work`; the three filesystem stores sit
on a shared bounded-tree core; the test suite (pytest over throwaway git repos)
is green.

**Cross-node recursion is now built (work Spec 2):** any git repo with a
`docs/work/` is a "node," "orchestrator" and "project" are relative roles,
cross-node initiatives (epics) link by an `initiative:` back-pointer, `tcw work
reconcile` rolls child tasks up into the epic, the inbox is the inter-node
channel (`delegate`/`escalate`), and `tcw work start --worktree` isolates an
item's code in its own checkout.

**The skill layer is now built (work Spec 3):** the `tcw-work` and
`tcw-capabilities` skills drive the lifecycle, and `tcw capabilities set` flips
the capability ledger as work completes.

**Still deferred (Phase 6):** remote (Jira/wiki/graph-DB) store adapters and
tracker sync — additive on top of the interfaces that already exist.

## Further reading

- [`AGENTS.md`](AGENTS.md) — the working rules and the prime directive (read first).
- `tcw work list` — current and pending work; this repo tracks its own work via `tcw work` (`docs/work/`).
- [`docs/plan/phase-2-taxonomy.md`](docs/plan/phase-2-taxonomy.md) · [`phase-3-capabilities.md`](docs/plan/phase-3-capabilities.md) · [`phase-5-work.md`](docs/plan/phase-5-work.md) — the per-component source-of-truth designs.
