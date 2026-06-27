# Orchestrator-level work: coordinate across sub-projects

When work spans **separate sub-project repos** (child *nodes* — see
`tcw work nodes`), the unit of coordination is a **cross-node epic** at the
orchestrator node, not a nested child. Use this path when the slices live in
different repos and progress independently; use `--parent` children when the
whole thing lives in one repo (see [`decompose.md`](decompose.md)).

1. **Open the epic** at the orchestrator node:
   `tcw work new --epic "<epic title>"` → note its slug.
2. **Hand each slice down** to the owning sub-project:
   `tcw work delegate <child-node> "<slice title>" --initiative <epic-slug>` —
   this drops a request (with `from:`/`initiative:` front-matter) into that
   child node's `inbox/`. The orchestrator never writes into a child's tracking
   tree directly; the child agent runs process-inbox and
   `tcw work new --initiative <epic-slug>` to adopt the slice.
3. **Each sub-project works its slice independently**, linking its own
   capabilities. Product-layer wording is coordinated over the inbox channel
   (`tcw work escalate "capability wording: …"`) — **non-blocking**; never wait
   on a reply (tcw-capabilities).
4. **A sub-project escalates up** when it needs the orchestrator:
   `tcw work escalate "<title>"` writes into the parent node's `inbox/`.
5. **Roll up progress** from the orchestrator:
   `tcw work reconcile <epic-slug>` scans every node for
   `initiative == <epic-slug>` and writes a consolidated table (node, slug,
   status, blockers, next-ready) into the epic's `initial-request.md`. Re-run it to
   refresh before deciding the next move.

**Which path?** Same repo, one big item → `--parent` children
([`decompose.md`](decompose.md)). Multiple sub-project repos → an `--epic` +
`delegate`/`--initiative`/`reconcile` (this doc).
