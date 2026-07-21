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

This ships the `tcw-work`, `tcw-capabilities`, `tcw-taxonomy`, and `tcw-plugin`
skills plus the `/tcw-init`, `/tcw-doctor`, `/tcw-plan-work`,
`/tcw-drive-work-to-completion`, `/tcw-taxonomy-init`, and
`/tcw-capabilities-init` commands. `/tcw-init` puts the `tcw` CLI on your
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
symlink. Requires Python ≥ 3.11; the Python runtime dependency is PyYAML.
`tcw serve` additionally requires Node.js ≥ 22.12. Other commands remain
Python-only and work without Node installed. Released wheels contain the locked,
prebuilt web server and client, so installed users do not need pnpm,
`node_modules`, a network connection, or a frontend build step.

## Quickstart

```sh
cd your-git-repo
tcw init --id my-project                    # scaffold all three components
tcw init --id my-project taxonomy work      # …or just named components
tcw work init --id my-project               # …or use a component mirror
tcw serve --no-open          # browse Work, Taxonomy, and Capabilities locally
tcw validate                # check YAML soundness, tcw:// links, and tree integrity
tcw --help                  # top-level groups: init | serve | validate | taxonomy | capabilities | work
```

`tcw init --id <project-id>` marks the **current directory** as a TCW node by
writing a `tcw-config.yaml` sentinel with its canonical ID, then scaffolds
`docs/<component>/` skeletons.
It refuses outside a git repo (write transitions need git), but the node folder
can be anywhere inside the repo — not just the root. Each component is a tree of
docs under `docs/<component>/`. Each component group also has its own `init`
mirror — `tcw taxonomy init`, `tcw capabilities init`, `tcw work init` —
identical to `tcw init --id <project-id> <component>`. Existing configured nodes
may omit `--id`; legacy ID-less markers use it once to backfill their identity.

### Connected projects

Projects may be nested, siblings, or anywhere else on the filesystem. Their
canonical IDs are identity; filesystem paths are adapter locators only.

```sh
cd orchestrator && tcw init --id orchestrator
cd ../project-a && tcw init --id project-a
```

Each invocation still selects the nearest enclosing sentinel. Cross-project
operations use only reciprocal registrations:

```yaml
id: orchestrator
connected-projects:
  children:
    project-a: ../project-a
```

```yaml
id: project-a
connected-projects:
  parent:
    orchestrator: ../orchestrator
```

Relative locators resolve from the declaring config; absolute locators are also
allowed. `children` contains direct children only and `parent` has at most one
entry. TCW derives deeper descendants and ancestors transitively, never by
scanning directories or git metadata. `tcw work list --include-descendants`
groups registered boards by project ID, and any work command accepts
`<descendant-project-id>/<slug>`.

Connections do not imply component inheritance. Each axis opts in explicitly:

```yaml
# docs/taxonomy/config.yaml
extends:
  - orchestrator
```

The source project ID is also the inherited namespace.

---

## Usage

Every group has a `--help`, a `check` that validates the tree, and a bare-path
shortcut (`tcw taxonomy <path>` == `tcw taxonomy show <path>`).

### `tcw serve` — the local web viewer

`tcw serve` starts a local web app on `127.0.0.1` for the current TCW node:

```sh
tcw serve                    # http://127.0.0.1:8765/ and open a browser
tcw serve --no-open           # start the server without opening a browser
tcw serve --port 9000         # choose a different loopback port
```

This command requires Node.js 22.12 or newer. TCW checks the version before
starting and reports an actionable error when Node is missing or too old. The
Python CLI launches a private authenticated API sidecar and a packaged Fastify
server; Fastify is the only browser-facing listener. The React client and server
bundle are included in the Python package and work fully offline. pnpm is needed
only by contributors rebuilding the committed web assets.

When the served node has **descendant TCW nodes** (the orchestrator/subproject
pattern), `tcw serve` aggregates every descendant node's board alongside the
current one automatically — the same items as `tcw work list --include-descendants`.
Descendant items carry `<project-id>/<slug>` addresses, resolvable across the web
app, and their URLs use the same project-ID namespace.

The app has tabs for the Taxonomy tree, Capabilities ledger, and Work board, and
its **URL reflects the current view** (`/taxonomy`, `/work/<slug>`, …) so any state
is deep-linkable and Back/Forward work. Any `tcw://` reference in an object's body
(see [`tcw://` links](#tcw-links--reference-a-tcw-object)) renders as a **clickable
in-app link** that navigates to the target object; a link to something this viewer
isn't hosting renders inert. The list/detail divider and the
editor/preview split are **drag-resizable**. The object list is a **collapsible
tree** that mirrors each axis's hierarchy — nested paths for taxonomy terms and
capabilities (a path segment with no item of its own is a plain folder label),
parent/child relations for work items. Selecting or deep-linking a nested item
expands its ancestors automatically, and the text filter prunes the tree to
matches plus the ancestors needed to reach them. The list column scrolls
independently, so a long tree stays navigable without moving the header or the
detail pane. Each axis keeps its create control immediately above the object
tree. Above that is a **multi-select category filter**: on the Work
board a `Tags` dropdown (checkbox per registered tag; select several to match
**any**), and in the Taxonomy view a `Kind` dropdown (`Feature` / `Vocabulary`).
The Work board also carries a row of **status-filter toggles** (`backlog` /
`active` / `completed`) — toggle one on to show items of that status; `completed`
is hidden by default. All of these compose with the text filter. Each work row
has a button to copy its slug to the clipboard. Beyond browsing, you can **create and edit** any object
directly from the browser:

- **Work items** — create new items with all fields (title, priority, effort,
  complexity, tags, blockers, parent, initiative); edit body and metadata; edit
  lifecycle artifacts and the `capabilities.yaml` sidecar using a Markdown
  editor with live preview; and run lifecycle actions (start, complete, drop).
  The complete action requires resolving blockers and acknowledging every
  Definition-of-Done item, plus a capabilities reconciliation reminder.
- **Taxonomy entries** — create Vocabulary or Feature entries; edit name,
  description, kind, and relations. Validation check failures are shown in the
  UI after saving.
- **Capabilities** — create path-addressed capability folders and edit metadata
  and the Markdown body. Inherited (federated) capabilities show their origin.
  Check failures are surfaced in the UI.

Structured reference fields search the Work, Taxonomy, and Capability objects
already loaded in the browser. Results show and highlight both the display name
and canonical identifier; use Up/Down and Enter or point at a result to select
it. Multi-value fields keep free-form entry for external or not-yet-registered
references. After any object, lifecycle artifact, or sidecar is saved, TCW runs
its standard validation rules against that saved object. Findings appear as a
persistent **Saved with validation issues** notice and do not undo the save;
fixing the object and saving again clears the notice.

All Markdown editing uses a raw-Markdown textarea paired with a live-rendered
preview pane. Its renderer is included in the locked, prebuilt package assets;
no runtime download or user-side build is required.

**Local-first safety:** the server binds only to `127.0.0.1` (loopback). Mutating
requests (create, edit, lifecycle actions) additionally require
`Content-Type: application/json` and a loopback `Host`/`Origin` header, blocking
cross-origin or DNS-rebinding attacks. Request bodies are capped at 1 MiB.
Concurrent stale edits are rejected (HTTP 409) so two editors never silently
overwrite each other.

If `tcw serve` fails before printing its URL, run `node --version` and confirm it
is at least `v22.12.0`. Reinstall TCW if the error reports missing packaged web
assets. Port-collision errors can be resolved with `--port <available-port>`.

### `tcw://` links — reference a TCW object

Any object's body prose can point at another TCW object with a `tcw://` link:

```
tcw://[<project-id>/]<axis>/<ref>
```

- `<axis>` is `T` (Taxonomy), `C` (Capabilities), or `W` (Work).
- `<project-id>` (optional) is a registered descendant for `W`, or a project
  explicitly listed by that axis's `extends` for `T`/`C`. Absent = local.
- `<ref>` is the identifier within that axis (taxonomy slug/path, capability
  path, work slug).

```markdown
See [Read a capability](tcw://C/capabilities/read-a-capability) and the
[reference](tcw://T/reference) term, or work item [tcw://W/2026-01-01-x](tcw://W/2026-01-01-x).
```

These are inline Markdown links, so they render as normal links in any viewer and
become **in-app navigation** in `tcw serve`. They're additive — they don't replace
the structured pointers (a capability's `Subject`/`Feature`, a work item's
`blocked_by`). Stored Markdown is never rewritten.

### `tcw validate` — one-pass soundness check

`tcw validate [path]` checks a whole node (or a single file/directory) in one pass:

```sh
tcw validate                 # the whole node: docs/{taxonomy,capabilities,work}/
tcw validate docs/capabilities   # narrow the scan to one tree
```

It reports, grouped by source, any of: malformed YAML (including duplicate keys),
a `tcw://` link that doesn't resolve, and the problems surfaced by each
component's own `check` (taxonomy + capabilities). It exits `0` with `validate OK`
when clean, else prints the problems and exits `1`. `tcw://` examples inside
Markdown code spans are ignored, so docs that teach the scheme don't fail
themselves.

### `tcw taxonomy` — the nouns

Taxonomy entries form a **forest, and the slug *is* the path**:
`admin/permission` is a different entry from `billing/permission`, and addressing
is by that path. Entries have two kinds: **Vocabulary** for the fundamental
language of the project, and **Feature** for the user- or application-facing
manifestations that operate on or involve vocabulary.

```sh
tcw taxonomy add Invoice "A bill issued to a customer."     # vocabulary by default
tcw taxonomy add Permission -p admin                        # -> admin/permission
tcw taxonomy add Note -p invoice -s memo                    # custom leaf slug
tcw taxonomy add "User Authentication" --kind feature --vocab user

tcw taxonomy list                  # the forest, indented, flagged by origin
tcw taxonomy list --local          # local terms only (hide imported)
tcw taxonomy show admin/permission # read one term (or: tcw taxonomy admin/permission)
tcw taxonomy search invoice        # match names + descriptions
tcw taxonomy check                 # validate inheritance + references

tcw taxonomy extends add acme-shared   # inherit a registered project
tcw taxonomy extends rm acme-shared    # drop the import
```

A taxonomy entry's body comes from the argument or from **stdin** (`echo "..." | tcw
taxonomy add Foo`). Feature entries can carry repeatable `--vocab <ref>` links
to the vocabulary they involve; `tcw taxonomy check` validates those refs.
Taxonomies can **federate**: `tcw taxonomy extends add <project-id>` writes the
registered source ID to the `extends` list in `config.yaml`. Each project ID is
its own namespace, and there
is **no silent merge** — a local `permission` and an imported `acme/permission`
stay distinct. Capabilities federate the same way, and additionally let a
consumer **override** an inherited entry per-project (see `tcw capabilities`
above).

To **bootstrap** a taxonomy or capabilities ledger on a project newly adopting
TCW, run `/tcw-taxonomy-init` or `/tcw-capabilities-init`: the assistant studies
your code, proposes a first draft, refines it with you, and writes it.

### `tcw capabilities` — the user stories

A capability is a **path-addressed folder** (`docs/capabilities/<path>/` holding
`meta.yaml` + `description.md`) with an opaque stable `id`. It carries metadata
fields — notably **`Subject:`** (a loose, **multi-valued** pointer to taxonomy
entries), **`Feature:`** (a strong pointer to a taxonomy feature), and
**`Planning doc:`** (the forward pointer to a work item).

```sh
tcw capabilities add billing/invoices "Download an invoice as PDF"   # mints a stable id
tcw capabilities add billing/invoices/bulk "Download many at once"    # nested path

tcw capabilities list                      # every capability, flagged by status + origin
tcw capabilities list --status Missing     # filter by status
tcw capabilities list --local-only         # hide inherited (federated) capabilities
tcw capabilities show billing/invoices     # read one capability by path
tcw capabilities search pdf
tcw capabilities check                     # paths, metadata vocab, Subject/Feature, federation
tcw capabilities drift                     # inherited-but-unreviewed + shipped-but-Missing (CI-usable)

tcw capabilities set billing/invoices --status Supported
tcw capabilities set billing/invoices --field "Subject=invoice,billing"   # multi-valued
tcw capabilities set billing/invoices --field "Planning doc=2026-06-19-pdf-export"
```

`set` updates a capability's status/fields in place (stage-only) — the mechanism
the work→capability lifecycle uses to flip `Missing → Supported` at completion.

Status is one of `Supported · Partial · Missing · Blocked · Omitted`. `check`
validates the metadata vocabulary, resolves each `Subject:` pointer against the
taxonomy store, and verifies that each `Feature:` pointer resolves to a taxonomy
feature. The tool never parses capability prose; it only follows pointers.

**Federation.** Capabilities can `extends` another project's — so a web frontend
and a mobile app that drive the same server declare their shared user stories
once:

```sh
tcw capabilities extends web-frontend       # inherit a registered project
tcw capabilities extends web-frontend --rm  # drop it
```

Inherited capabilities surface flagged by origin (`web-frontend/<path>`) and are
read-only in structure — a project can't delete one, only **override** it. Set an
inherited capability exactly like a local one, by any path `show` accepts:

```sh
tcw capabilities set web-frontend/auth/login --status Omitted
```

The override is written for you. It is a local folder whose `meta.yaml` has
`overrides: <upstream-id>` plus the changes: metadata fields partial-merge (e.g.
`Status: Missing`, or `Status: Omitted` for "we deliberately don't have this"; a
YAML `null` clears a field), and the body composes as `prependedDocs` + (a local
`description.md`, if present, else the upstream body) + `appendedDocs` — e.g. a
mobile app appending "…or take a photo with the camera." That file shape is
worth knowing (you can hand-author one anywhere, and `set` will keep using it),
but `set` is the front door. Local sibling-repo paths only.

To undo an override and go back to the upstream value, `reset` it:

```sh
tcw capabilities reset shared/auth/login   # drop the local override, re-inherit upstream
```

`reset` removes only your local override folder (never the upstream node). It
refuses with a clear message when there's nothing to drop — a standalone local
capability (use `remove`) or a path that already inherits verbatim.

### `tcw work` — the changes

Raw requests enter through a permissive inbox, then accepted requests become
formal work in a **single-node state machine** where status is the folder a work
item lives in and a transition is a move between folders:

```
raw inbox entry  --accept-->  backlog  --start-->  active
                                                       |
                                                   completed
                         (drop deletes a backlog item)
```

Blocked-ness is a **derived overlay**: an item is blocked when it has at least
one unresolved blocker recorded in its data — there is no separate "blocked"
folder or status.

```sh
tcw work init                          # docs/work/{inbox,backlog,active,completed}/

tcw work inbox list                    # list each raw file or folder entry
tcw work inbox show request.md         # inspect metadata, text, and resource manifest
tcw work inbox accept request.md       # consume it into a new backlog item; print the slug
tcw work inbox accept request.md --title "Clear title"

slug=$(tcw work new "Add PDF export")  # creates a backlog item, prints its slug
tcw work new "Add PDF export" --blocked-by "other-slug,external:JIRA-123"
                                       # create with blockers pre-attached
tcw work new "Urgent fix" --priority 5 # integer priority (higher = higher); default unspecified
tcw work new "Big rework" --effort high --complexity very-high
                                       # optional estimates (low|medium|high|very-high; L/M/H/VH shorthand ok)
tcw work new "Sub-task" --parent "$slug"  # a child item, nested inside the parent's folder

tcw work tags add bug tech-debt        # register a project's valid tags (in tcw-config.yaml)
tcw work tags list                     # print the registered tags
tcw work tags rm tech-debt             # unregister (warns about items still carrying it)
tcw work new "Login crash" --tag bug   # apply a registered tag (repeatable; unregistered → error)

tcw work list                          # the board: priority first, then topologically ordered (hides completed)
tcw work list --status active          # filter to one column
tcw work list --tag bug                # only items carrying a tag (repeatable = match any)
tcw work list --all                    # include completed items too
tcw work list -i                       # descendant boards; --incl-desc and --include-descendants are aliases
tcw work audit-work-backlog            # report stale, duplicate, blocked, or misplaced backlog items
tcw work consolidate-plans docs/plans  # dry-run: find external plans to migrate
tcw work consolidate-plans docs/plans --apply --delete
                                       # create backlog items, then delete migrated sources
tcw work show "$slug"                  # state + body (includes blocked_by/type/initiative/effort/complexity/tags if set)
tcw work path "$slug"                  # current filesystem path of the slug

tcw work start "$slug"                 # backlog → active (refused if blocked/gated)
tcw work start "$slug" --force         # override unresolved blockers or initiative gates

tcw work edit "$slug" --blocked-by other-slug    # record a new blocker
tcw work edit "$slug" --blocks downstream-slug   # this item now blocks another
tcw work edit "$slug" --unblocked-by other-slug  # clear a resolved blocker
tcw work edit "$slug" --priority 9               # set/raise integer priority
tcw work edit "$slug" --effort medium --complexity low   # set effort/complexity estimates
tcw work edit "$slug" --tag bug --untag stale    # apply/remove tags (repeatable)

tcw work complete "$slug" --resolution done --confirm
tcw work complete "$slug" --resolution done --confirm --force   # override blockers, gates, or unreconciled capabilities
tcw work drop some-slug                # delete a backlog item
```

`complete` **enforces capability reconciliation**: if the item's `capabilities.yaml`
declares a `new:` capability that still reads `Missing`, or any declared path that
no longer resolves, the completion is refused (flip it with `tcw capabilities set`,
mark it `Omitted`, or `--force` past). For a `--worktree` item the check runs after
the branch merges back, so a status flip made on the work branch counts.

**Tags** classify items for filtering. Each project registers its valid tag set
centrally in `tcw-config.yaml` (`tcw work tags add|rm|list`); an item then carries
zero or more of those tags via `--tag` on `new`/`edit` (and `--untag` to remove).
Applying an unregistered tag is refused, and `tcw validate` flags any item still
carrying a tag that was later unregistered. Tags don't affect board ordering.

After `tcw work new` and `tcw work start`, the CLI prints the **next transition to
run** (e.g. "→ next: when you begin implementing, run `tcw work start …`") so the
lifecycle is hard to skip — the slug still goes to stdout alone, the hint to stderr.
`tcw work new` also prints an "→ edit: …/initial-request.md" line (stderr) pointing
at the new item's body so you can open it for editing right away.
Inbox entries are deliberately permissive. A direct child of `docs/work/inbox/`
may be any standalone file, or a folder with exactly one `INDEX.md` or
`INDEX.txt`; other folder files become bounded `attachments/` on acceptance.
Hidden files and empty directories are ignored, symlinks are not followed, and
binary contents are never printed. See the optional
[`docs/work-inbox-template.md`](docs/work-inbox-template.md) for a useful request
shape; the command does not require or parse that template.

`initial-request.md` is always-present — it is the item body/overview surface and
the canonical request lifecycle artifact, seeded with title, the three-axis scaffold
(Product / Technical / Meta changes), and any piped stdin.

The **board** (`tcw work list`) prints a `|`-delimited row per item —
`slug | status | stages | priority | title` (priority is the integer, or `-`
when unspecified). `stages` is a compact lifecycle artifact string: `R` for
`initial-request.md`, `S` for `spec.md`, `P` for `plan.md`, `O` for
`outcome.md`, and `F` for `refined-outcome.md`; missing or empty artifacts do
not contribute letters, and `-` means no lifecycle artifacts are present. The
board shows the live columns (backlog and active) and hides completed items
by default — pass `--status completed` to list them or `--all` for everything.
It sorts by priority first (higher integer above lower, unspecified-priority
items keeping creation order), then topologically — blockers appear before the
items they block, since a priority preference can't jump a hard dependency —
and annotates blocked items with their unresolved blockers.

Pass `-i`, `--incl-desc`, or `--include-descendants` to list every **registered
descendant work node**. The output is grouped by project ID (`# .` for the
current node), and the same `--status` / `--all` filters apply to every group.
Initiative tasks are indented beneath their visible owning epic, including tasks
from descendant nodes; each descendant row keeps its project-qualified slug and
is printed only once.

Descendant items are printed with a **project-qualified slug** —
`<project-id>/<slug>` — so each printed slug is a usable address. You can pass that
qualified slug to any work command from the enclosing node
(`tcw work show project-a/<slug>`, `start`, `edit`, `complete`, `drop`, …).
A **bare** slug still resolves against the current node only. (`blocked-by:`
refs shown on a qualified row stay node-local — they are bare slugs within that
descendant.)

`tcw work audit-work-backlog` reviews backlog items in board order and prints
read-only cleanup recommendations. It flags likely duplicates or already-finished
work, broken local file references, stale blockers, malformed capability deltas,
vague or under-specified items, and items that appear to belong in another TCW
node. The command reports evidence and suggested next actions; it does not move,
complete, drop, or rewrite items.

`tcw work consolidate-plans [PATH ...]` finds Markdown planning documents outside
`docs/work/` and migrates them into backlog items. It is dry-run by default:
without `--apply`, it prints each candidate source and inferred title. With
`--apply`, it creates one backlog item per source, writes `initial-request.md`
with the source content and provenance, and copies obvious spec/plan sections
into `spec.md` and `plan.md`. With `--delete`, it removes each source document
only after its work item has been created successfully.

A large item can be **decomposed into child items** with `tcw work new
"<title>" --parent <slug>`: the child's folder is created inside the parent's,
and `tcw work list` renders children indented under their parent. A child shares
its parent's status by living inside it — starting or completing the parent
carries its children along, while transitioning a child on its own promotes it
to a top-level item. (That keeps any one item small; for work spanning *separate
repos*, use a cross-node epic instead — see below.)

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

For cross-node discovery (`tcw work nodes` / epics / delegate / escalate), a
**node** is a git repo with a `docs/work/`; "orchestrator" and "project" are
relative roles. (The *current node* — where `tcw` operates day-to-day — is the
nearest `tcw-config.yaml` ancestor, which may be a subfolder.) A node nested
under another is a **child**, the enclosing one its **parent**. An **epic** is
an ordinary work item that tasks in child nodes point at via an
`initiative:` back-pointer.

```sh
tcw work nodes                              # show this node's parent + child nodes

epic=$(tcw work new "Redesign checkout" --epic)
tcw work new "Slice 1" --initiative "$epic" # in a child node: link a new task to the epic
tcw work edit "$slug" --initiative "$epic"  # …or link an existing one

tcw work reconcile "$epic"                  # follow registered descendants → rollup
tcw work reconcile "$epic" --commit         # …and commit it
tcw work reconcile "$epic" --complete-when-ready  # …and auto-close it if every child is resolved

echo "needs an API change" | tcw work delegate child-repo "Expose X"  # request DOWN to a child inbox/
echo "cross-repo scope"    | tcw work escalate "Coordinate the redesign" # request UP to the parent inbox/
```

`reconcile` consolidates every child task for an initiative into a managed
rollup block in the epic's `initial-request.md` — a slice table, surfaced capability
deltas, and the next ready actions — and is **read-only** on the capabilities
ledger. `delegate`/`escalate` only ever write a request into the target node's
`inbox/`, never its tracked work, respecting the node write-boundary.

Initiative transitions are relation-gated: a task with `initiative: <epic>` is
refused at `start` until the epic is active, and an epic is refused at
`complete` while related child tasks are still open. `--force` overrides these
gates when the relationship cannot be resolved or the user intentionally
deviates. Once **every** child is resolved, the epic is flagged `ready-to-close`
in `tcw work list` and in its rollup, and it may be completed **directly from
`backlog`** — a coordinator epic that never had its own spec/plan doesn't need a
throwaway `start` just to close it (the Definition-of-Done and capability gates
still apply).

Run an item in an isolated checkout with `--worktree`:

```sh
tcw work start "$slug" --worktree           # active on trunk + a git worktree/branch for the code
```

Status transitions stay on the node's primary checkout (the board is always
`ls active/`); in-flight edits live on the work branch. `complete` merges that
branch back into the primary checkout, then tears the worktree down — and if the
merge conflicts it stops with the branch and worktree left intact, so committed
work is never silently dropped.

---

## Skills — the judgment layer

The CLI is the *mechanism*; five skills in [`skills/`](skills/) are the *judgment*
that drives it (the work↔capability lifecycle the tool only enforces structurally):

- **[`tcw-work`](skills/tcw-work/SKILL.md)** — plan a request or existing work item
  through `initial-request.md`, `spec.md`, and `plan.md`; drive implementation
  or epic coordination through `outcome.md` and user verification in
  `refined-outcome.md`; commit each lifecycle stage before beginning the next;
  triage `docs/work/inbox`; run the start/complete lifecycle; resume active work;
  and decompose work into a cross-node epic.
- **[`tcw-capabilities`](skills/tcw-capabilities/SKILL.md)** — the `## Capability
  changes` planning gate, contradiction-detection, the `Missing → Supported`
  ledger flip at completion, product-layer wording coordination, and bootstrapping
  a capabilities ledger (`/tcw-capabilities-init`).
- **[`tcw-taxonomy`](skills/tcw-taxonomy/SKILL.md)** — declaring vocabulary and
  feature entries, linking features to vocabulary, `relatesTo` links, federating
  shared vocabulary (`tcw taxonomy extends`), and bootstrapping a taxonomy from
  an existing codebase (`/tcw-taxonomy-init`).
- **[`tcw-plugin`](skills/tcw-plugin/SKILL.md)** — install/repair the `tcw` CLI
  from the plugin's own clone (pipx); the single source of the `/tcw-init` and
  `/tcw-doctor` procedure, and the Codex shim for them.
- **[`tcw-report`](skills/tcw-report/SKILL.md)** — how to report a `tcw` bug or
  send a suggestion **upstream to the TCW project** as a GitHub issue, with a
  ready-to-fill skeleton for each. Found a bug or have an idea? File it at
  [github.com/brocef/TCW/issues](https://github.com/brocef/TCW/issues).

They name `tcw …` commands (and, for `tcw-plugin`, `pipx`) and never reimplement
tool logic — mechanism stays in the binary, judgment in the skills.

---

## Status

**The single-node core is built.** Phases 1–5 are complete: `tcw` installs and
exposes `init | taxonomy | capabilities | work`; the three filesystem stores sit
on a shared bounded-tree core; the test suite (pytest over throwaway git repos)
is green.

**Cross-node recursion is now built (work Spec 2):** for cross-node discovery,
any git repo with a `docs/work/` is a "node;" "orchestrator" and "project" are
relative roles, cross-node initiatives (epics) link by an `initiative:`
back-pointer, `tcw work reconcile` rolls child tasks up into the epic, the inbox
is the inter-node channel (`delegate`/`escalate`), and `tcw work start
--worktree` isolates an item's code in its own checkout.

**Sentinel-based node detection (work Spec 1):** `tcw init` now marks the
current directory a TCW node (writing a `tcw-config.yaml` sentinel), so a
single git repo can hold multiple projects as subfolders. Taxonomy `extends`
works across sibling subfolder projects by construction.

**The skill layer is now built (work Spec 3):** the `tcw-work` and
`tcw-capabilities` skills drive the lifecycle, and `tcw capabilities set` flips
the capability ledger as work completes.

**Still deferred (Phase 6):** remote (Jira/wiki/graph-DB) store adapters and
tracker sync — additive on top of the interfaces that already exist.

## Further reading

- [`AGENTS.md`](AGENTS.md) — the working rules and the prime directive (read first).
- `tcw work list` — current and pending work; this repo tracks its own work via `tcw work` (`docs/work/`).
- [`docs/plan/phase-2-taxonomy.md`](docs/plan/phase-2-taxonomy.md) · [`phase-3-capabilities.md`](docs/plan/phase-3-capabilities.md) · [`phase-5-work.md`](docs/plan/phase-5-work.md) — the per-component source-of-truth designs.
