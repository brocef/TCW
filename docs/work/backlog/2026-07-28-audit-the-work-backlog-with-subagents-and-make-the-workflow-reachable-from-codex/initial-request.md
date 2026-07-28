# Audit the work backlog with subagents, and make the workflow reachable from Codex

## Origin

Raised in chat after a full `/tcw-audit-work-backlog` run over the 10-item
backlog. The run was sequential and single-context: one agent read all ten item
folders and verified every claim against the working tree. It worked, but it is
the shape that scales worst — cost grows linearly with backlog size in a single
context, and the per-item checks are embarrassingly parallel.

## Product changes

The audit workflow gains a delegated execution model and becomes reachable from
Codex. No `tcw` CLI surface changes — this is judgment-layer and packaging work.

The `plugin/*` capability entries may need a body edit if the audit workflow is
described there as a Claude-only or CLI-backed affordance; check at spec time.

## Technical changes

### 1. Split the review checklist into two lists

The current checklist is eight flat bullets. Split by *what context a check
needs*:

- **Per-item checks** — answerable from one item folder plus shared reads (the
  working tree, the node registry, the capability ledger):
  already completed · outdated · wrong repository/node · unactionable or
  oversized · blocked without a next action · capability drift.
- **Inter-item checks** — require seeing the backlog as a set:
  duplicate or superseded · missing relationship edges · tag hygiene.

**User's rule for ambiguous checks: if a check cannot be split cleanly, it goes
in the inter-item list.** That rule is what puts tag hygiene wholly inter-item —
"does this item carry the right tags" reads per-item, but "does this reveal a
broadly useful category missing from the registry" is only visible across items,
and splitting one bullet across two agents is worse than running it once with
full context.

**Missing relationship edges** is a new check, not in today's list. It comes
directly from the audit run: `2026-06-19-remote-extends-for-taxonomy` states in
prose that `2026-07-01-transitive-taxonomy-inheritance` "should land first", but
`state.yaml` carries no `blocked_by`, so `tcw work list` shows both as equally
pickable. Prose-stated dependencies that never became recorded edges are a
recurring backlog defect, and the inter-item agent is the only one positioned to
see them.

### 2. Delegate: one subagent per item, one for the set — pipelined

- One subagent per backlog item, running the per-item list against that item
  only.
- One subagent running the inter-item list over the whole set.

**They pipeline, they do not run in parallel from zero.** The duplicate and
superseded checks need to know what each item is *about*, which means reading
every item folder — exactly the work the per-item agents just did. So each
per-item agent returns its findings **plus** a two-line "what this item is
about", and the inter-item agent consumes those summaries instead of re-reading
ten folders. One pass of reading instead of two, and the inter-item agent starts
better-informed than a cold read would leave it.

Two instructions must appear in every per-item subagent prompt, because they
currently live in the command's closing paragraph and will not otherwise reach a
subagent's context:

- **Read-only.** Never mutate, transition, or tag. The parent agent asks the
  user for approval; a subagent has no standing to act.
- **Verify against the working tree; do not summarize the item's prose.** This is
  where the value is. The strongest findings in the seed run — stale line
  citations in a plan, and an item whose stated goal ("fix the README command
  drift") had already been fixed by another item — came only from checking the
  tree. Ten agents summarizing prose would cost more than the sequential run and
  find less.

Cap concurrency so a large backlog does not spawn an unbounded fleet; pick the
number at spec time.

### 3. Make the workflow reachable from Codex

Codex **does** have subagents — `.codex/agents/*.toml`, model-driven spawning,
parallel with `[agents] max_concurrent_threads_per_session`, and it "respects
applicable `AGENTS.md` or skill instructions that request delegation"
(<https://learn.chatgpt.com/docs/agent-configuration/subagents>). So the
delegation itself needs no Claude-only mechanism and no sequential fallback.

The reachability gap is elsewhere, and it predates this item:

- `.codex-plugin/plugin.json` exposes `"skills": "./skills/"` only — **no
  `commands` key**, unlike `.claude-plugin/plugin.json`. Codex never sees
  `commands/`.
- The entire audit checklist lives in `commands/tcw-audit-work-backlog.md`.
- The skill's only pointer to the workflow is
  `skills/tcw-work/references/commands.md:25`, which lists
  `tcw work audit-work-backlog` — **a CLI verb that does not exist**
  (`tcw work` accepts init, inbox, nodes, reconcile, delegate, escalate, tags,
  new, list, show, path, start, submit, rework, lifecycle, edit, complete,
  drop). `README.md:582` and `README.md:713` document the same fictional verb.

So today a Codex user cannot reach this workflow at all, and any delegation
instructions written into `commands/` would be Claude-only content — exactly the
failure mode CLAUDE.md's harness-compatibility section exists to prevent.

Fix: move the checklist into `skills/tcw-work/references/audit-backlog.md`
(matching the skill-authoring rule — a rare sub-procedure behind a clear gate in
the thin router), leave `commands/tcw-audit-work-backlog.md` as a thin pointer to
it, and repoint the three docs that cite the fictional verb at the skill
reference.

## Meta changes

- **CLAUDE.md / AGENTS.md carry a stale claim.** The harness-compatibility
  section lists "custom subagents" among the Claude-only features. Codex has
  them (see above). The line should be corrected rather than left to mislead the
  next planning pass — it nearly forced a pointless sequential fallback into this
  item's design.
- Litmus test: not applicable in the usual sense — nothing here touches the store
  interface. This is judgment-layer prose and plugin packaging.

## Known drift found while scoping (fold in or split at spec)

- `.codex-plugin/plugin.json`'s `longDescription` says the plugin "ships six
  skills"; `skills/` holds seven (`tcw-post-mortem` landed 2026-07-27). Same file
  being edited for the reachability fix.

## Open questions for spec

1. Concurrency cap for the per-item fan-out, and behavior on a large backlog —
   cap and batch, or cap and let the parent queue?
2. What exactly the per-item agent returns: freeform report lines, or a fixed
   shape the parent can collate without re-reading? The two-line summary for the
   inter-item agent argues for a fixed shape.
3. Does the inter-item agent also need the **completed** and **active** item
   lists (the duplicate check names all three statuses), and does it get those as
   summaries or read them itself?
4. Is `commands/tcw-audit-work-backlog.md` reduced to a pointer, or deleted in
   favor of the skill reference alone? Deleting changes the Claude UX (the
   `/tcw-audit-work-backlog` slash command disappears), so probably reduced.
5. Should the fictional `tcw work audit-work-backlog` verb be *built* instead of
   removed from the docs? It would make the workflow harness-neutral by the
   CLAUDE.md rule ("anything that must be guaranteed belongs in the CLI") — but
   the CLI cannot host an AI-driven review, so it could only print the procedure.
   Decide deliberately rather than by default.
