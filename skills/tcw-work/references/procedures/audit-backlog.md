# Auditing the backlog

Keep the backlog relevant, actionable, and correctly located. This is an
AI-driven review, not a `tcw` subcommand — there is no `tcw work
audit-work-backlog`. Claude users can reach it as `/tcw-audit-work-backlog`;
under any harness, this document is the procedure.

Start with `tcw work list --status backlog`. Read each item folder via
`tcw work path <slug>` — `initial-request.md` **or** `intake.md` (the item's
body; an inbox-adopted item has only the intake), `spec.md`, `plan.md`,
`content.md`, `capabilities.yaml`, `state.yaml`, whichever exist.

## The two checklists

Checks are split by **the context they need**, because that is what decides
whether a check can be delegated per-item.

### Per-item — one item's folder, plus shared reads

- **Already completed:** the work shipped or was completed outside the lifecycle.
  Recommend completing it, usually `--resolution done`, once evidence is verified.
- **Outdated:** specs or plans reference files, APIs, architecture, frameworks,
  commands, or capability entries that no longer exist or have been replaced.
  Line-number citations in a plan are a common casualty.
- **Wrong repository / node:** the item belongs in another TCW node, or should be
  split across nodes. Recommend moving, delegating, escalating, or creating
  replacement items in the proper homes.
- **Unactionable or oversized:** no acceptance criteria, a vague request, no clear
  next implementation step, or work that should be decomposed with
  `tcw work new "<subtask>" --parent <slug>`.
- **Blocked without a next action:** blockers that are stale or already completed
  (look each one up — `tcw work show <blocker>`), or external blockers naming no
  owner, wait condition, or follow-up.
- **Capability drift:** `capabilities.yaml` references missing capability files,
  carries stale status assumptions, or disagrees with the ledger.

"Wrong node" and "capability drift" look set-wide but are not — each compares one
item against a **shared read** (the node registry, the capability ledger) that a
single agent can perform alone.

### Inter-item — requires seeing the backlog as a set

- **Duplicate or superseded:** another backlog, active, or completed item covers
  the same work. Recommend a duplicate/superseded resolution, or merge the useful
  context into the better item.
- **Missing relationship edges:** an item states a dependency in prose that was
  never recorded, so `tcw work list` shows both as equally pickable. Fix with
  `tcw work edit <slug> --blocked-by <ref>`.
- **Tag hygiene:** an item with no tags despite matching a registered category, a
  tag that no longer fits, or a broadly useful category missing from the
  registry. Read `tcw work tags list` first. Register with
  `tcw work tags add <tag>` **only** for reusable categories; apply with
  `tcw work edit <slug> --tag <tag>`; remove with `--untag <tag>`.

Tag hygiene sits here whole rather than split. "Does this item carry the right
tags" reads per-item, but "does this reveal a missing category" is visible only
across items — and a check that does not split cleanly belongs on this side.

## Running it

Delegate the per-item list: **one subagent per backlog item**, then **one
subagent** for the inter-item list. Both harnesses support this; see
[`delegation.md`](delegation.md). Where subagents are unavailable, walk the same
two checklists in one session — the result is identical, only slower.

**Pipeline them; do not run both from zero.** The duplicate check needs to know
what each item is _about_, which means reading every folder — the work the
per-item agents just did. So each per-item agent returns its findings **plus** a
two-line "what this item is about", and the inter-item agent consumes those
summaries instead of re-reading the backlog. It additionally reads the one-line
output of `tcw work list --status active`, `--status review`, and
`--status completed` — the duplicate check spans **every** status, and an item in
`review` is the likeliest near-duplicate of all, since it is the work that just
happened. Open a folder only when a summary makes a candidate look real.

Dispatch in **batches of at most 8**. A 60-item backlog must not spawn 60 agents.

The two-line summary is a **return contract**: if an agent omits it or returns
something malformed, re-dispatch that item or read the folder yourself. One bad
return costs one item's sequential reading; it must never silently drop the item
from the inter-item agent's input.

### What every per-item dispatch must say

- **Read-only.** Never mutate, transition, or tag. Approval belongs to the session
  holding the user relationship. Prefer the `tcw-backlog-auditor` agent, which
  holds no file-editing tools — that narrows the blast radius, though it still
  needs `Bash` to verify anything, so say this in the dispatch either way. **If
  that agent is not in your roster** — it ships with the plugin, so any session on
  an older release lacks it — use any agent without `Write`/`Edit` and paste this
  section into the dispatch. Never skip the audit for want of a named agent.
- **Verify against the working tree; do not summarize the item's prose.** This is
  where the value is, and it is not enforceable — only instructable. An item
  claiming a defect is worthless until you check whether the defect still exists;
  the strongest findings come from plans whose cited code has moved and from items
  whose stated goal another item already achieved.

## Reporting

Per item:

```
<slug> | <recommendation> | <severity> | <reason>
  evidence: <specific evidence>
  action: <exact next step or command>
```

**Severity** is one of `critical` · `high` · `medium` · `low`, scored on the cost
of acting on the item _as it currently stands_ — not on how interesting the
finding is. `high` means starting it now would waste real work (a plan whose
every anchor has moved). `low` means it needs a touch-up someone will absorb in
passing. Without a fixed scale two audits are not comparable.

An item with nothing wrong still gets a line — `<slug> | keep as-is | none |
<why it is healthy>` — because "audited, clean" and "not audited" must not look
the same.

Close with the inter-item findings and a short list of categories that produced
nothing — "no duplicates, no capability drift" is a result worth stating, for the
same reason.

Finally, confirm you changed nothing: `git status --porcelain` should be empty.
Every agent in this procedure holds `Bash`, so read-only is a rule honored rather
than a wall enforced — check it rather than assume it.

## The approval rule

**Do not silently mutate, drop, complete, or move items.** Ask before performing
any cleanup, including tag registration and tag edits.

**Group the asks by kind** — one approval for the tag edits, one for the blocker
edges, one for the drops. A real audit produces a dozen or more candidate
actions; asking per item is unusable and asking once for everything is a blanket
yes on decisions that deserve individual thought. Drops and completions are
irreversible enough to name individually inside their group.

When the user approves, use TCW commands for state transitions and tag edits
wherever a command exists, and preserve useful context in the remaining or
replacement item.
