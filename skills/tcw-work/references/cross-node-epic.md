# Orchestrator-level work: coordinate across sub-projects

When work spans **registered child projects** (see `tcw work nodes`), the unit
of coordination is a cross-node epic at the orchestrator project, not a nested
work item. Physical layout is irrelevant: direct child and parent connections
must be reciprocal in `tcw-config.yaml`, and every project has a canonical ID.
Use `--parent` children only when the slices are work items in the same project.

1. **Open the epic** at the orchestrator node:
   `tcw work new --epic "<epic title>"` → note its slug.
2. **Hand each slice down** to the owning sub-project:
   `tcw work delegate <child-project-id> "<slice title>" --initiative <epic-slug>` —
   this drops a request (with `from:`/`initiative:` front-matter) into that
   child node's `inbox/`. The orchestrator never writes into a child's tracking
   tree directly; the child agent runs process-inbox and
   `tcw work new --initiative <epic-slug>` to adopt the slice.

   The adopted slice carries the epic's bare slug in its `state.yaml`, which is
   machine-tracked but invisible to a human reading the request. Link the epic in
   prose too, at the top of the slice's `initial-request.md`:

   ```
   Epic: [<epic title>](tcw://W/<orchestrator-project-id>/<epic-slug>)
   ```

   `<project-id>/<slug>` resolves to any node in the registered graph, in any
   direction, so the upward link validates. Note the viewer caveat: a child's
   `tcw serve` aggregates descendants, so it cannot open an ancestor's item.
3. **Each sub-project works its slice independently**, linking its own
   capabilities. Product-layer wording is coordinated over the inbox channel
   (`tcw work escalate "capability wording: …"`) — **non-blocking**; never wait
   on a reply (tcw-capabilities).
4. **A sub-project escalates up** when it needs the orchestrator:
   `tcw work escalate "<title>"` writes into the parent node's `inbox/`.
5. **Roll up progress** from the orchestrator:
   `tcw work reconcile <epic-slug>` follows registered descendants for
   `initiative == <epic-slug>` and writes a consolidated table (node, slug,
   status, blockers, next-ready) into the epic's `initial-request.md`. Re-run it to
   refresh before deciding the next move.

**Which path?** Same TCW project → `--parent` children
([`decompose.md`](decompose.md)). Multiple registered projects → an `--epic` +
`delegate`/`--initiative`/`reconcile` (this doc).
