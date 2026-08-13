# TCW — Taxonomy · Capabilities · Work

A storage-abstracted framework for **describing and evolving a software project
along three axes**, exposed through one CLI (`tcw`) with three subcommand groups.

| Component        | Is               | Holds                                                                                |
| ---------------- | ---------------- | ------------------------------------------------------------------------------------ |
| **Taxonomy**     | the nouns        | the _things_ an app deals with — domain entities, with a real glossary and ontology  |
| **Capabilities** | the user stories | what a user can _do_ with those things — each a miniature user story                 |
| **Work**         | the changes      | edits to capabilities (product), machinery (technical), or the project itself (meta) |

The three link by **loose, one-directional pointers** (capability → term,
work → capability/term) and never duplicate each other. Taxonomy is the
vocabulary, capabilities are the user-facing surface, and work is the change
layer that moves capabilities and machinery forward over time.

---

## Why this exists

Most projects scatter their "what" and "why" across a dozen unsynchronized
places: a tracker for tickets, a wiki for glossaries, a `FOLLOWUPS.md` that
grows without bound, design docs that drift from code, and a planning flow where
documents _jump_ between unrelated trees with no "where is this right now?"
spine. State lives everywhere and nowhere; reconstructing the current picture
means reading all of it and trusting none of it.

TCW started as an effort to fix exactly that for an agent-driven SDLC, and the
unlocking insight was that several separate-looking problems —

- no single, durable source of truth for _where a piece of work is_,
- a glossary nobody could point at,
- capability docs that drifted from the code,
- a follow-up log that rotted,
- cross-repo coordination that lived only in prose —

were all facets of **one** missing thing: a _durable, legible, per-node source
of truth_ for a project's nouns, user stories, and changes. TCW is that source
of truth, built on a deliberate stance:

- **State is the status, not a log.** A work item's status _is which directory
  it lives in_; a transition is a `git mv`. The "board" is `ls active/`. There
  is no global ledger file to drift, double-count, or burn tokens
  re-summarizing.
- **Per-node, never global.** Each item, term, and capability owns one bounded
  document. Nothing grows without limit; nothing has to be reconstructed from
  history.
- **Mechanism in the tool, judgment in the human/agent.** Legal transitions,
  slug integrity, reference validity, and the Definition-of-Done gate are
  _enforced_ by a deterministic CLI — not left to a prose checklist that gets
  followed only sometimes.
- **Co-located with the code it describes.** The docs live in the repo. One
  atomic commit can carry a code change _and_ its status/capability change
  together, reviewable in the same diff.

The shorthand for the work component is a **"recursive, OS-native Jira"** — and
just as important is what it deliberately _refuses_: no sprints, no story
points, no burndown charts, no SLAs, no estimation ceremony. Just items,
statuses, legal transitions, and a done-gate.

## Storage abstraction (the prime directive)

TCW ships a **filesystem-native default**, but the _model_ is storage-abstracted
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
legibility, `mv`-as-transition — are _bonuses layered on top_, never
load-bearing assumptions of the model. The full rules live in
[`AGENTS.md`](AGENTS.md).

## Who it's for

- **Agent-driven development**, where an LLM needs a legible, enforced place to
  record what a project is and where its work stands — and where "told to follow
  the rules" isn't enough, because the invariants must be _mechanically_ held.
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
```

Or, in the Claude **web app** or **desktop app**, open the plugin directory, add
`brocef/TCW` as a marketplace, and install `tcw` from it — no terminal needed.

**Then start a new session** — the plugin installs the `tcw` CLI when a session
begins, and one installed mid-session can't run until the next one starts.

This ships the `tcw-work`, `tcw-capabilities`, `tcw-taxonomy`, `tcw-plugin`,
`tcw-post-mortem`, `tcw-report`, `tcw-triage-issues`, and `documentation-sync`
skills; the
`/tcw-doctor`, `/tcw-process-inbox`, `/tcw-triage-issues`, `/tcw-plan-work`,
`/tcw-drive-work-to-completion`, `/tcw-verify-work`, `/tcw-post-mortem`,
`/tcw-audit-work-backlog`, `/tcw-consolidate-plans`, `/tcw-taxonomy-init`,
`/tcw-capabilities-init`, `/tcw-docs-sync-setup`, and `/tcw-cut-version`
commands; and the read-only `tcw-verifier` and
`tcw-post-mortem` agents. There is nothing to run afterwards: the plugin puts
`tcw` on your PATH at session start by installing `tcw-cli` from PyPI (via pipx),
and refreshes it the same way when a plugin update lands. It's the same package
you'd install by hand, so if you already ran `pipx install tcw-cli` there's
nothing to undo — the plugin installs over it rather than beside it. A
development checkout installed with `pip install -e .` is left alone, and so is a
machine without `pipx` — choosing a Python environment isn't something that
should happen unasked at session start. Run `/tcw-doctor` any time `tcw` goes
missing or looks wrong.

**This needs network the first time.** The plugin no longer carries a CLI to fall
back on, so the first session after you install or update the plugin has to reach
PyPI. If it can't, the session says so in one line and `tcw` won't be available
until a session that can.

In **Codex** (no slash commands — skills only):

```bash
codex plugin marketplace add brocef/TCW --ref main
codex plugin add tcw@tcw
```

Codex has no session-start hook, so ask the agent to run the **`tcw-plugin`**
setup — it installs the `tcw` CLI by running the same script Claude runs
automatically.

### As a Python package

```sh
pipx install tcw-cli        # recommended (isolated, on PATH)
pip install -e .            # development install from a clone
```

The package is called **`tcw-cli`** on PyPI because `tcw` was already taken by
an unrelated project. The command it installs is still `tcw`, and the importable
package is still `tcw` — only the name you type after `pipx install` differs.

This is the same install the plugin performs for you: if you use the plugin, you
don't need to run this, and if you run it anyway the plugin will install over it
rather than beside it. Use it when you want the CLI without an agent harness at
all, or to move ahead of the plugin's refresh cycle with `pipx upgrade tcw-cli`.

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
tcw work init --id my-project --path ../orchestrator/CoreLib/work
tcw serve --no-open          # browse Work, Taxonomy, and Capabilities locally
tcw validate                # validate this project and all registered descendants
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

Scaffolding `work` also adds `.gitignore` rules for `docs/work/completed/` and
`docs/work/discarded/`, keeping each folder's `.gitkeep` tracked. Resolved items
therefore stay on your disk and in the history that tracked them while they were
live, without piling up in the tree forever. Delete the rules to track resolved
work instead; on a node that predates them, re-run `tcw work init` to add them
and `git rm -r --cached docs/work/completed docs/work/discarded` to drop what git
already tracks.

To keep a project's work in another Git repository while preserving its own ID
and lifecycle configuration, set `work.path` in its `tcw-config.yaml` or pass
`tcw work init --path <path>` (`tcw init --work-path <path> work`). Relative
paths are anchored to the owning project's primary checkout; absolute paths and
symlinks are supported. Existing non-pristine stores are never moved
automatically.

Everything that reads or writes work follows `work.path`: `delegate` and
`escalate` land in the target project's configured inbox, `reconcile` writes and
commits the epic rollup in the store's repository, `tcw capabilities drift` finds
completed planning items there, and status transitions and web edits commit there
too. What stays with the code repository is what the code owns — lifecycle hooks,
the `.gitignore` entry for worktrees, and the branches and linked worktrees
themselves. A project that names a `work.path` and also happens to have a leftover
`docs/work/` folder is read through its configured path, not the leftover.

When the two repositories differ, `tcw work start --worktree` commits the item's
state in the store repository and the `.gitignore` change in the code repository,
then creates the worktree — and if either commit is refused it stops, says which
repository already committed, and creates no worktree. A code branch cannot carry
lifecycle files that live in another repository, so the work branch holds the
code side only; the item itself stays visible through the store.

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
scanning directories to discover a project. `tcw work list --include-descendants`
groups registered boards by project ID, and any work command accepts
`<descendant-project-id>/<slug>`.

Inside a **linked git worktree** a relative locator would otherwise be off by the
worktree's nesting depth, because it was written against the project's position
in its primary checkout. TCW re-anchors it against the main worktree root — but
only when the target leaves the worktree. A target that stays inside is a sibling
on the same branch and stays with the worktree, so several projects in one repo
behave the same inside a worktree as outside it. This is the one place git
metadata is consulted, and it only re-points a locator: it never discovers a
project or infers a relation. Projects outside a worktree, and projects not in a
git repository at all, are unaffected.

Connections do not imply component inheritance. Each axis opts in explicitly:

```yaml
# docs/taxonomy/config.yaml
extends:
    - orchestrator
```

The source project ID is also the inherited namespace. Inheritance is
transitive: if one source extends another, both sources' terms are available
under their own project IDs.

---

## Usage

Every group has a `--help` and a `check` that validates the tree. Taxonomy and
capabilities also have a bare-path shortcut (`tcw taxonomy <path>` ==
`tcw taxonomy show <path>`), except that `path` itself is reserved as the store-
location command; use explicit `show path` to read an object with that name.

Print the absolute, resolved folders used by the filesystem stores with:

```sh
tcw taxonomy path
tcw capabilities path
tcw work path
tcw work inbox path
```

The work commands follow a configured `work.path`, so they report the physical
external store and its inbox when work storage lives outside the project.

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

Contributor formatting is repository-wide and deterministic:

```sh
pnpm prettify          # format maintained source and documentation
pnpm prettify:check    # verify formatting without rewriting files
```

Dependencies, generated bundles and caches, closed work items (completed and
discarded), and versioned
release archives are excluded; current source, configuration, taxonomy,
capabilities, active/backlog work, this README, and upcoming notes remain in the
formatting surface. `pnpm typecheck` also runs the formatting check.

The Settings gear immediately after the Work tab controls appearance. Choose
**Light**, **Dark**, or **System**; System is the default and follows operating-
system appearance changes as they happen. The choice is stored only in the
current browser, not in the TCW project or an API.

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
detail pane. A clear control appears inside a non-empty filter, tree controls
provide larger keyboard-accessible targets, and Work rows tint their full
surface by backlog, active, completed, or discarded status. Each axis keeps its create
control immediately above the object tree. Every Taxonomy, Capability, and Work
entry shows its last-modified timestamp in both the tree row and detail header.
Above that are **multi-select category filters**: on the Work board,
`Status` and `Tags` dropdowns use a checkbox per value (select several to match
**any**), and in the Taxonomy view a `Kind` dropdown covers `Feature` and
`Vocabulary`. Backlog and active statuses are selected by default; completed and
discarded are not. Work items can be sorted by name or last-modified time in
either direction; the selected sort applies within the fixed active, backlog,
completed, then discarded status groups. All of these compose with the text filter. Each work row has a
button to copy its slug to the clipboard. Beyond browsing, you can **create and
edit** any object directly from the browser:

- **Work items** — create new items with all fields (title, priority, effort,
  complexity, tags, blockers, parent, initiative); view and edit Initial
  Request, Spec, and Implementation Plan in first-class content tabs; edit
  other lifecycle artifacts and the `capabilities.yaml` sidecar using a
  Markdown editor with live preview; and run lifecycle actions (start,
  complete, drop).
  Completing as `done` requires resolving blockers and acknowledging every
  Definition-of-Done item, plus a capabilities reconciliation reminder;
  discarding drops all three for a single confirmation.
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

Bare `tcw validate` checks the active TCW project and every registered descendant
project recursively. Use `--no-recurse` to check only the active project, or pass
a path to run a bounded active-project scan (which also disables recursion):

```sh
tcw validate                    # active project + all registered descendants
tcw validate --no-recurse       # active project only
tcw validate docs/capabilities  # one active-project tree only
```

For each selected project it reports malformed YAML (including duplicate keys),
a `tcw://` link that doesn't resolve, and problems surfaced by each component's
own `check` (taxonomy + capabilities + work). Recursive diagnostics include the
project ID so matching relative paths remain distinguishable. It exits `0` with
`validate OK` only when every selected project is clean; otherwise it prints the
problems and exits `1`. `tcw://` examples inside Markdown code spans are ignored,
so docs that teach the scheme don't fail themselves.

### `tcw taxonomy` — the nouns

Taxonomy entries form a **forest, and the slug _is_ the path**:
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
to the vocabulary they involve. A ref is a term path (`admin/permission`), a
`<project-id>/<path>` into an inherited taxonomy, or a leaf slug that is unique
across your own terms — which is stored as its full path. `tcw taxonomy add`
refuses a ref that does not resolve, is ambiguous, or names a feature where a
vocabulary entry is expected, and writes nothing when it refuses; so register
vocabulary before the features that name it. `tcw taxonomy check` validates the
same refs across the whole tree.
Taxonomies can **federate**: `tcw taxonomy extends add <project-id>` writes the
registered source ID to the `extends` list in `config.yaml`. Each project ID is
its own namespace, including sources inherited transitively, and there is **no
silent merge** — a local `permission` and an imported `acme/permission` stay
distinct. Capabilities federate separately and additionally let a
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
raw inbox entry  --accept-->  backlog  --start-->  active  --submit-->  review
                                  |                    |                   |
                                  |                    |     <--rework-----+
                                  |                    |                   |
                                  |   --resolution done-+-------------------+--> completed
                                  |                    |                   |    ("we shipped it")
                                  +--- wontfix / duplicate / superseded ---+--> discarded
                                                            ("we closed it without shipping")
                         (drop deletes a backlog item outright)
```

The **resolution picks the destination**, so `completed/` answers "what
shipped?" on its own. A backlog item can be discarded directly — abandoning an
idea never needed a throwaway `start`.

`review` means **implemented, acceptance pending**. It is not a finished state:
an item sitting in review still blocks whatever depends on it and still holds
its epic open, because verification can send it back. `rework` is the only
reverse move in the machine — nothing ever leaves `completed/` or `discarded/`.

Review is **optional**. A small change can still go straight from `active` to
`completed`; `tcw work complete` just prints a note saying the verify step was
skipped, and completes.

Blocked-ness is a **derived overlay**: an item is blocked when it has at least
one unresolved blocker recorded in its data — there is no separate "blocked"
folder or status.

### Binding your own skills and commands to the lifecycle

The lifecycle has named **stages** (each producing one document) and named
**transitions** (each moving status). A node can bind its own agent skills or
shell commands to any of them:

```yaml
# tcw-config.yaml
work:
    lifecycle:
        stages:
            spec: [{ skill: superpowers:brainstorming }]
        transitions:
            complete:
                pre: [{ command: "pytest -q" }]
```

A binding is a `skill:` **or** a `command:` — never a bare string, because
guessing which one was meant is a class of bug bought for nothing. `tcw validate`
rejects an unknown id, a malformed shape, a blank or duplicated reference, and a
binding declaring neither or both.

`pre` hooks run **before** anything is written: a non-zero exit aborts the
transition and the item does not move. `post` hooks run after, and a failure
there **never rolls back** — the move already happened, so `tcw` reports it and
exits non-zero while the item stays where it went. Commands run through the shell
with the node root as the working directory and `TCW_SLUG`, `TCW_STATUS`,
`TCW_TRANSITION`, and `TCW_NODE_ROOT` in the environment, with a 300-second
default timeout (`work.lifecycle.timeout`).

Skill bindings are **reported, never run** — `tcw` cannot invoke a skill, only
your agent can. Run `tcw work lifecycle` to see what is bound.

Two things worth knowing: `tcw-config.yaml` is a file in your own repository and
is trusted exactly as much as any other file there — this is not a sandbox. And
`tcw serve` does **not** run hooks, so a `pre` hook that would block a transition
does not block it from the web app.

**Every transition commits its own move.** `tcw work start`, `submit`, `rework`,
and `complete` each leave a commit recording just that item's status change —
scoped to the item's own folders, so unrelated edits in your working tree are
never swept in. Set `work.auto-commit-transitions: false` in `tcw-config.yaml` to
turn it off and commit them yourself. `work.trunk-branch: main` adds a warning
when you transition an item from some other branch; it is advisory only and
never checks anything out.

**The completion checklist is yours to set.** `tcw work complete --resolution
done` prints a Definition of Done and refuses until you re-run with `--confirm`.
Write your own as a plain list in `docs/work/dod.yaml`:

```yaml
- tests pass
- docs synced
- capabilities reconciled
- reviewed
- version offered
```

Two things to know. The file **replaces** the built-in list rather than adding to
it — those five are the defaults, so a list that leaves one out drops that check
from every completion, with no error. And it is printed only when the resolution
is `done`: discarding an item (`wontfix`, `duplicate`, `superseded`) prints no
checklist at all, so a line meant to cover those closures has nowhere to land.

If the item came from a GitHub issue — `/tcw-triage-issues` records it — closing
the item out means answering that issue and usually closing it too. A checklist
line is the natural place to be reminded.

```sh
tcw work init                          # docs/work/{inbox,backlog,active,review,completed,discarded}/

tcw work inbox list                    # list each raw file or folder entry
tcw work inbox show request.md         # inspect metadata, text, and resource manifest
tcw work inbox accept request.md       # consume it into a new backlog item; print the slug
tcw work inbox accept request            # …or the bare title `inbox list` printed, same entry
tcw work inbox accept request.md --title "Clear title"

slug=$(tcw work new "Add PDF export")  # creates a backlog item, prints its slug
tcw work new "Add PDF export" --blocked-by other-slug --blocked-by "external: JIRA-123"
                                       # create with blockers pre-attached (flag is repeatable —
                                       # one blocker per flag, so its text may contain commas)
tcw work new "Urgent fix" --priority 5 # integer priority (higher = higher); default unspecified
tcw work new "Big rework" --effort high --complexity very-high
                                       # optional estimates (low|medium|high|very-high; L/M/H/VH shorthand ok)
tcw work new "Sub-task" --parent "$slug"  # a child item, nested inside the parent's folder

tcw work tags add bug tech-debt        # register a project's valid tags (in tcw-config.yaml)
tcw work tags list                     # print the registered tags
tcw work tags rm tech-debt             # unregister (warns about items still carrying it)
tcw work new "Login crash" --tag bug   # apply a registered tag (repeatable; unregistered → error)

tcw work list                          # the board: priority first, then topologically ordered
                                       # (hides completed and discarded)
tcw work list --status active          # filter to one column (backlog|active|review|completed|discarded)
tcw work list --tag bug                # only items carrying a tag (repeatable = match any)
tcw work list --all                    # include completed and discarded items too
tcw work list --status discarded       # only the items closed without shipping
tcw work list -i                       # descendant boards; --incl-desc and --include-descendants are aliases
tcw work lifecycle                     # the stage/transition contract + this node's bindings
tcw work lifecycle --json              # the same, machine-readable
tcw work lifecycle --stage spec --directive
                                       # one instruction line for an agent, or nothing if unbound

tcw work show "$slug"                  # state + body (includes blocked_by/type/initiative/effort/complexity/tags if set)
tcw work path                           # absolute, resolved work-store folder
tcw work path "$slug"                  # current filesystem path of the slug
tcw work inbox path                     # absolute, resolved inbox folder

tcw work start "$slug"                 # backlog → active (refused if blocked/gated)
tcw work start "$slug" --force         # override unresolved blockers or initiative gates

tcw work submit "$slug"                # active → review (implemented, acceptance pending)
tcw work rework "$slug"                # review → active (verification rejected the work;
                                       # refused while refined-outcome.md still says it passed)

tcw work edit "$slug" --blocked-by other-slug    # record a new blocker (repeatable)
tcw work edit "$slug" --blocks downstream-slug   # this item now blocks another
tcw work edit "$slug" --unblocked-by other-slug  # clear a resolved blocker (repeatable;
                                                 # accepts the "external: …" form show/list print,
                                                 # and fails if it matches no blocker)
tcw work edit "$slug" --title "A better title"   # rename the item (the slug never changes)
tcw work edit "$slug" --priority 9               # set/raise integer priority
tcw work edit "$slug" --effort medium --complexity low   # set effort/complexity estimates
tcw work edit "$slug" --tag bug --untag stale    # apply/remove tags (repeatable)

tcw work complete "$slug" --resolution done --confirm
tcw work complete "$slug" --resolution done --confirm --force   # override blockers, gates, or unreconciled capabilities
tcw work complete "$slug" --resolution done --confirm --already-integrated
                                       # the work branch was merged outside TCW (a merged PR):
                                       # skip the merge-back, keep every other gate
tcw work complete "$slug" --resolution wontfix --confirm        # → discarded/ (no Definition of Done; legal from backlog)
tcw work drop some-slug --confirm      # erase a mis-created item, leaving no record
```

`complete` **enforces capability reconciliation**: if the item's `capabilities.yaml`
declares a `new:` capability that still reads `Missing`, or any declared path that
no longer resolves, the completion is refused (flip it with `tcw capabilities set`,
mark it `Omitted`, or `--force` past). For a `--worktree` item the check runs after
the branch merges back, so a status flip made on the work branch counts.

A **discard is not a shipment**, so none of the shipping gates apply to one: no
Definition-of-Done checklist, no capability enforcement (just a warning naming
anything left `Missing`), no branch merge-back, and **no blocker check** — being
blocked indefinitely is one of the best reasons to give up on something, so
needing `--force` to act on it would be backwards. `--confirm` is still
required, since closing is permanent. Discarding a `--worktree` item tears down
the worktree but **keeps the unmerged branch**, naming it so you can delete it
deliberately — deciding work isn't wanted is not the same as authorizing its
destruction.

An **epic** is the one exception: open initiative children block closing it by
either route, because a child can't start until its epic is active, so closing
the epic would strand them.

**Tags** classify items for filtering. Each project registers its valid tag set
centrally in `tcw-config.yaml` (`tcw work tags add|rm|list`); an item then carries
zero or more of those tags via `--tag` on `new`/`edit` (and `--untag` to remove).
Applying an unregistered tag is refused, and `tcw validate` flags any item still
carrying a tag that was later unregistered. Tags don't affect board ordering.

After `tcw work new` and `tcw work start`, the CLI prints the **next transition to
run** (e.g. "→ next: when you begin implementing, run `tcw work start …`") so the
lifecycle is hard to skip — the slug still goes to stdout alone, the hint to stderr.
`tcw work new` also prints an "→ edit: …" line (stderr) pointing at the new
item's body file when it has one — piped stdin lands in `intake.md`, so that is
what the hint points at. Created with nothing piped, an item has no body file
yet and the line is simply omitted.
Every command that moves an item also names where it now lives, as a path
relative to the project root — `tcw work start` and `tcw work complete` on
stdout ("started my-item → docs/work/active/my-item"), `tcw work new` and
`tcw work inbox accept` on stderr beside their other hints, leaving their stdout
the bare slug.
Inbox entries are deliberately permissive. A direct child of `docs/work/inbox/`
may be any standalone file, or a folder with exactly one `INDEX.md` or
`INDEX.txt`; other folder files become bounded `attachments/` on acceptance.
Hidden files and empty directories are ignored, symlinks are not followed, and
binary contents are never printed. See the optional
[`docs/work-inbox-template.md`](docs/work-inbox-template.md) for a useful request
shape; the command does not require or parse that template. Accepting an entry
records what arrived as the item's `intake.md` — the entry body, a manifest
naming every preserved resource and the entry it came from, and a note standing
in for a primary resource that is not text — and leaves the item's `request`
stage still to run.

An item's **body surface** resolves to `initial-request.md` when it exists, and
otherwise to `intake.md` — the raw, unprocessed input the item started from
(piped stdin, or an accepted inbox entry with its manifest and attachments).
An item created with neither has no body yet, which is a state rather than a
defect: `initial-request.md` is the `request` stage's own artifact, so it exists
once that stage has run and not before. Presence everywhere means *exists and is
non-empty*.

Editing an item's body always writes `initial-request.md`, never the intake. On
an item that has only intake, that edit **promotes** it — the request is created,
the intake is left byte-for-byte as it arrived, and the tool says a promotion
happened rather than letting it look like an ordinary save. Raw input that
quietly changes is not raw input, so `intake.md` is editable only as a named
artifact.

For large implementations, `plan.md` may optionally declare a bounded DAG of
stage documents in YAML frontmatter. Each declaration has a lowercase kebab-case
`id`, a title, and `depends_on`; optional effort, complexity, priority, and tags
reuse the work item's controlled vocabularies. The corresponding document is
stored as `plan/<id>.md`. This keeps `plan.md` concise so agents can read it
first, then load only the relevant stage. Dependencies communicate ordering and
parallelism but do not create stage statuses or block lifecycle transitions.
Legacy single-file plans remain valid.

The **board** (`tcw work list`) prints a `|`-delimited row per item —
`slug | status | stages | priority | title` (priority is the integer, or `-`
when unspecified). `stages` is a compact lifecycle artifact string: a lowercase `i` for
`intake.md`, then `R` for `initial-request.md`, `S` for `spec.md`, `P` for
`plan.md`, `O` for `outcome.md`, and `F` for `refined-outcome.md`; the letters
read in lifecycle order. Missing or empty artifacts do not contribute letters,
and `-` means no lifecycle artifacts are present — so `R` means the `request`
stage has actually run. The
board shows the live columns (backlog and active) and hides both closed
columns by default — pass `--status completed` or `--status discarded` to list
one, or `--all` for everything.
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

A qualified slug addresses **any node in the registered graph, in any direction** —
descendant, ancestor, or sibling — not just nodes below you. A child project can
therefore address (and link) an epic that lives in its parent. Project IDs are
canonical and connections must be reciprocal, so there is nothing ambiguous to
resolve; an unregistered project, or a path-shaped qualifier such as
`some/folder/<slug>`, still does not resolve. A qualifier that names no registered
project reports `no such project in this graph: <id>` rather than a misleading
"no such work item".

Note that `tcw work list -i` and `tcw serve` remain **descendant-only** — they
aggregate boards downward. Addressing and linking are graph-wide; aggregation is
not.

Two backlog chores are **AI-driven reviews rather than CLI commands** — they need
judgment the CLI cannot supply, so the assistant runs them:

**Auditing the backlog** reviews items in board order and reports read-only
cleanup recommendations: likely duplicates or already-finished work, broken file
references, stale blockers, malformed capability deltas, vague items, and items
that look like they belong in another TCW node. It reports evidence and suggested
next actions and asks before changing anything. Ask the assistant to audit the
backlog, or run `/tcw-audit-work-backlog` in Claude Code; the procedure lives in
the `tcw-work` skill, so it works under either harness.

**Consolidating external plans** finds Markdown planning documents outside
`docs/work/` and migrates them into backlog items, writing `initial-request.md`
with the source content and provenance and copying obvious spec/plan sections
into `spec.md` and `plan.md`. It runs only when you ask for it, lists every
source file it proposes to delete before deleting any, and deletes only files git
has already committed — anything untracked or with uncommitted changes is
reported and left alone. Ask the assistant to consolidate external plans, or run
`/tcw-consolidate-plans` in Claude Code; the procedure lives in the `tcw-work`
skill, so it works under either harness.

A large item can be **decomposed into child items** with `tcw work new
"<title>" --parent <slug>`: the child's folder is created inside the parent's,
and `tcw work list` renders children indented under their parent. A child shares
its parent's status by living inside it — starting or completing the parent
carries its children along, while transitioning a child on its own promotes it
to a top-level item. (That keeps any one item small; for work spanning _separate
repos_, use a cross-node epic instead — see below.)

Items are referenced by a **stable slug**, resolved to "wherever it now lives,"
so moves never break references. Only the legal transitions above are permitted
— anything else is refused, not silently allowed.

**Completion is gated.** `tcw work complete --resolution done` prints the
Definition of Done and refuses without `--confirm` (and without `--force` if
unresolved blockers exist). A discard prints no checklist and is not
blocker-gated, but still refuses without `--confirm`:

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
**node** is a git repo with a usable work store — `docs/work/` by default, or
wherever its `work.path` points; "orchestrator" and "project" are
relative roles. (The _current node_ — where `tcw` operates day-to-day — is the
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

echo "needs an API change" | tcw work delegate child-repo "Expose X"  # request DOWN (child's project id, not a path)
echo "cross-repo scope"    | tcw work escalate "Coordinate the redesign" # request UP to the parent inbox/
```

Claiming an item is atomic, and concurrent commands read across it safely: an
item mid-claim is never mistaken for a missing one, so a blocker being started
elsewhere still blocks. If a process dies holding a claim, reads report an
interrupted claim and point at `tcw work start <slug> --take-over --owner <id>`
rather than pretending the item is gone.

`reconcile` consolidates every child task for an initiative into a managed
rollup block in the epic's `initial-request.md` — a slice table, surfaced capability
deltas, and the next ready actions — and is **read-only** on the capabilities
ledger. `delegate`/`escalate` only ever write a request into the target node's
`inbox/`, never its tracked work, respecting the node write-boundary — into the
target's *configured* inbox, and they fail loudly rather than inventing a
`docs/work/` folder when that store cannot be reached. `delegate` addresses its
target by canonical project ID, the form `tcw work nodes` lists — never by
filesystem path. A delegated request's `--initiative` survives acceptance, so a
slice accepted in the child stays linked to the epic that asked for it.

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
work is never silently dropped. Moving the item through its lifecycle while the
branch is open is not a conflict: `submit` relocates the item's folder on the
primary checkout, and the merge-back carries the branch's files into the folder's
new home rather than stopping to ask. The same applies to any other directory
renamed on the primary checkout while the branch was open, code included — files
the branch added under the old path follow the rename. With a `work.path` in
another repository the
setup commits split by owner — item state in the store repository, `.gitignore`
in the code one — and the work branch carries the code side only, because one
Git branch cannot contain another repository's files.

Run `complete` **from the primary checkout**, not from inside the item's own
worktree: both the merge-back and the teardown act on the primary checkout, and
`git worktree remove` would be deleting the directory you are standing in. From
inside, TCW refuses and names where to re-run it. Every other command works from
either place.

---

## Skills — the judgment layer

The CLI is the _mechanism_; seven skills in [`skills/`](skills/) are the _judgment_
that drives it (the work↔capability lifecycle the tool only enforces structurally):

- **[`tcw-work`](skills/tcw-work/SKILL.md)** — plan a request or existing work item
  through `initial-request.md`, `spec.md`, and `plan.md`; drive implementation
  or epic coordination through `outcome.md` and user verification in
  `refined-outcome.md`; commit each lifecycle stage before beginning the next;
  triage `docs/work/inbox`; run the start/complete lifecycle; resume active work;
  and decompose work into a cross-node epic.
  For unusually large plans it can declare staged plan documents, load only the
  stage being executed, and use that stage's pre- and post-checks.
- **[`tcw-capabilities`](skills/tcw-capabilities/SKILL.md)** — the `## Capability
changes` planning check, contradiction-detection, the `Missing → Supported`
  ledger flip at completion, product-layer wording coordination, and bootstrapping
  a capabilities ledger (`/tcw-capabilities-init`).
- **[`tcw-taxonomy`](skills/tcw-taxonomy/SKILL.md)** — declaring vocabulary and
  feature entries, linking features to vocabulary, `relatesTo` links, federating
  shared vocabulary (`tcw taxonomy extends`), and bootstrapping a taxonomy from
  an existing codebase (`/tcw-taxonomy-init`).
- **[`tcw-plugin`](skills/tcw-plugin/SKILL.md)** — install/repair the `tcw` CLI
  from PyPI (pipx); the single source of the `/tcw-doctor` procedure and of the
  install the session-start hook performs automatically, and the Codex entry
  point for both.
- **[`tcw-report`](skills/tcw-report/SKILL.md)** — how to report a `tcw` bug or
  send a suggestion **upstream to the TCW project** as a GitHub issue, with a
  ready-to-fill skeleton for each. Found a bug or have an idea? File it at
  [github.com/brocef/TCW/issues](https://github.com/brocef/TCW/issues).
- **[`tcw-triage-issues`](skills/tcw-triage-issues/SKILL.md)** — the other
  direction: sweep the GitHub issues on **your own project**, triage them, and
  turn the ones worth doing into work items (`/tcw-triage-issues`). Most issues
  shouldn't become work items, so it decides first — duplicate, not worth doing,
  too vague to act on — and offers a reply to the reporter either way, which you
  approve before anything is posted.
- **[`documentation-sync`](skills/documentation-sync/SKILL.md)** — the cross-cutting
  process skill the work lifecycle invokes at its plan and completion gates:
  evaluate a project's `## Documentation Sync` triggers so docs (README, changelog,
  release notes, driving skills) move with the code that changes them. It also
  sets a project's Documentation Sync section up in the first place
  (`/tcw-docs-sync-setup`) and runs the version cut when a change set is done
  (`/tcw-cut-version`) — including folding later work into a version that was
  cut locally but never pushed.

The six axis/plugin skills name `tcw …` commands (and, for `tcw-plugin`, `pipx`;
for `tcw-triage-issues`, `gh`) and never reimplement tool logic — mechanism stays
in the binary, judgment in the skills; `documentation-sync` is a cross-cutting
process skill rather than a CLI driver.

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

## Releasing

Releases publish themselves. `scripts/cut_version.py` bumps every
version-bearing file, rotates the changelog and release-note working files,
commits, and tags; pushing that tag is what ships it:

```sh
python scripts/cut_version.py <patch|minor|major|X.Y.Z>
git push origin main --tags
```

The `v*` tag triggers `.github/workflows/release.yml`, which runs the full test
suite, checks that the tag matches the version in `pyproject.toml`, builds, and
uploads to PyPI. There is no API token — PyPI mints a short-lived credential
from GitHub's OIDC claim ("Trusted Publishing"), which is why the workflow
declares `id-token: write` and `environment: pypi`.

Two things are configured once, outside the repo, and must match the workflow
exactly or the upload fails authentication:

| Where | Setting |
| --- | --- |
| pypi.org → Publishing | project `tcw-cli`, owner `brocef`, repository `TCW`, workflow `release.yml`, environment `pypi` |
| GitHub → Settings → Environments | an environment named `pypi` |

**A version can only be uploaded to PyPI once.** If the workflow fails *after* a
successful upload, that version number is spent — recover with a patch bump, not
by re-running the job.

## Further reading

- [`AGENTS.md`](AGENTS.md) — the working rules and the prime directive (read first).
- `tcw work list` — current and pending work; this repo tracks its own work via `tcw work` (`docs/work/`).
- [`docs/plan/phase-2-taxonomy.md`](docs/plan/phase-2-taxonomy.md) · [`phase-3-capabilities.md`](docs/plan/phase-3-capabilities.md) · [`phase-5-work.md`](docs/plan/phase-5-work.md) — the per-component source-of-truth designs.
