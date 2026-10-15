# Auditing unfinished work

Keep the unfinished items relevant, actionable, and in the right project. This
is a review done by an agent, not a `tcw` command. Ask the `work` skill for it;
under any harness, this document is the procedure.

Start with `tcw work list`, which lists every item that has not ended. For each
one, read what it asks for and its comments with `tcw work show <slug>`, and
whichever of its documents exist: `tcw work path <slug> spec`,
`tcw work path <slug> plan`, the newest round in `tcw work path <slug>
implement`, and `capabilities.yaml` in the folder `tcw work path <slug>`
prints.

## The two checklists

Checks are split by **the context they need**, because that is what decides
whether a check can be handed out one item at a time.

### Per item: one item's documents, plus shared reads

- **Already done:** the work shipped elsewhere, or outside the lifecycle.
  Recommend `tcw work discard <slug> --reason "done in <where>"` once the
  evidence is checked.
- **Outdated:** the spec or plan names files, interfaces, commands or
  capabilities that have since been removed or replaced. Line numbers cited
  in a plan are a common casualty.
- **Wrong project:** the item belongs in another TCW project, or should be
  split across projects. Recommend `tcw work new "<title>" --project <id>` for
  each part there, and discarding this one.
- **Unactionable or too large:** no acceptance criteria, a vague request, no
  clear next step, or work that should be split with
  `tcw work new "<part>" --parent <slug>`.
- **Blocked with no next action:** blockers that have ended (look each one up
  with `tcw work show <blocker>`), or an outside blocker that names no owner,
  no condition to wait for, and no follow-up.
- **Capability drift:** `capabilities.yaml` lists under `changed:` or
  `removed:` a capability that does not exist, or under `new:` one whose
  wording contradicts the standing records.

"Wrong project" and "capability drift" look like they need the whole set but
do not: each compares one item against a **shared read** (the list of
projects, the capability records) that one agent can do alone.

### Across items: needs the set

- **Duplicate or superseded:** another item, finished or not, covers the same
  work. Recommend discarding the weaker one with a reason naming the other,
  after moving anything useful into it.
- **Missing blockers:** an item states a dependency in prose that was never
  recorded, so the list shows both as equally ready. Fix with
  `tcw work edit <slug> --blocked-by <ref>`.
- **Tags:** an item with no tags despite matching a registered one, a tag that
  has stopped fitting, or a useful category missing from the registry. Read
  `tcw work tags list` first. Register with `tcw work tags add <tag>` **only**
  for categories that will be reused; apply with
  `tcw work edit <slug> --tag <tag>`; remove with `--untag <tag>`.

Tags sit here whole: "does this item carry the right tags" reads per item, but
"is a category missing" shows only across items, and a check that does not
split cleanly belongs on this side.

## Running it

Hand out the per-item list: **one subagent per item**, then **one subagent**
for the across-items list. Where subagents are not available, walk the same two
lists in one session; the result is the same, only slower.

**Chain them; do not run both from nothing.** The duplicate check needs to know
what each item is _about_, which means reading every item, the work the
per-item agents just did. So each per-item agent returns its findings **plus**
two lines on what the item is about, and the across-items agent reads those
summaries instead of every item again. It also reads `tcw work list --all`,
because a duplicate can be finished work. It opens an item only when a summary
makes a candidate look real.

Hand out **at most 8 at a time**. Sixty items must not start sixty agents.

The two-line summary is part of what each agent must return: if one leaves it
out or returns something malformed, send that item again or read it yourself.
A bad return must never silently drop an item from the across-items check.

### What every per-item brief must say

- **Read only.** Never change, move or tag anything. Approval belongs to the
  session holding the conversation with the user. Prefer the `backlog-auditor`
  agent where your harness has it, which has no file-editing tools; it still
  needs to run commands to check anything, so say this in the brief either
  way. Without that agent, use any agent without write tools and paste this
  section into its brief. Never skip the audit for want of a named agent.
- **Check against the code; do not summarize the item's prose.** This is where
  the value is. An item claiming a defect is worthless until you check
  whether the defect still exists; the strongest findings come from plans
  whose cited code has moved and from items whose goal another item reached.

## Reporting

Per item:

```
<slug> | <recommendation> | <severity> | <reason>
  evidence: <specific evidence>
  action: <exact next step or command>
```

**Severity** is one of `critical` · `high` · `medium` · `low`, scored on the
cost of acting on the item _as it stands_, not on how interesting the finding
is. `high` means starting it now would waste real work (a plan whose every
reference has moved). `low` means a touch-up someone will absorb in passing.

An item with nothing wrong still gets a line, `<slug> | keep as-is | none |
<why it is healthy>`, because "audited, clean" and "not audited" must not look
the same.

Close with the across-items findings and the checks that found nothing: "no
duplicates, no capability drift" is a result worth stating, for the same
reason.

Finally, confirm nothing changed: `tcw work list --all --json` read before the
audit and after it must match. Every agent here can run commands, so read-only
is a rule honored rather than a wall; check it rather than assume it.
