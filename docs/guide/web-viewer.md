# The local web viewer

`tcw serve` starts a local web app that browses and edits all three axes.

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
in-app link** that navigates to the target object. A reference to a real object on
a board this viewer isn't serving is marked as **off-board**, with the name of the
project that owns it shown beside the link text; a reference that doesn't resolve
at all is shown inert with the reason it failed. The list/detail divider and the
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
  complete, drop). Each content tab shows only its own document: on an item
  whose request has not been written, the tab says so and the editor opens
  empty rather than pre-filling it with the item's raw intake. Saving a body
  that creates the request says that it did.
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
