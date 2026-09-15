# Request — Add a tcw-work-create skill that checks for overlap before creating a work item

## What is wanted

A procedure for creating a new TCW work item properly, packaged as a new
top-level skill, `tcw-work-create`. It turns an idea for a piece of work into
one of three results: a new item, an existing item amended with the new
information, or no change because the work is already covered.

The main reason for a separate skill rather than another reference document
under `tcw-work` is **automatic invocation**. Agents should reach for this skill
on their own, in the middle of other work, whenever they notice something that
ought to be tracked. A skill of its own has a description that can be tuned to
make that more likely. The requester is not certain this reasoning is right and
wants `spec` to test it, not simply accept it.

## The procedure, in the requester's terms

### Before deciding to create an item

1. **The idea must be understandable.** It does not need spec-level detail.
2. **Look for open work that already covers it**, including inbox entries.
   When an existing item covers the idea but is missing information that
   matters, what happens depends on how far that item has got:
   - **Inbox entry, or a backlog item whose request has not been specced yet:**
     amend it with the new information.
   - **Backlog item with a spec or plan already written:** ask the user whether
     to dispatch a subagent to revise those artifacts, or to leave the item as
     it is.
   - **Item already being implemented, in review, or being verified:** tell the
     user which item it is and what the new information is, then move on. Do
     not try to find or message the agent working on it. The user can give
     further instructions if they want.
3. **If nothing covers it, create the item.**

### Once an item will be created

Ask the user for anything the conversation has not already answered:

- **Known blockers?** Accepted answers: work item slugs; "no"; a description
  (search the backlog for matching items, then confirm with the user); or
  "determine automatically" (search the backlog and set any blockers found
  without asking for confirmation).
- **Reference material?** Links, documentation, related items that are not
  blockers. Reference material already in the conversation counts as the
  answer; ask only when there is none.
- **Is it a bug, or a follow-up to another work item?** If so, record that on
  the item.

### After creating it

Tell the user the new item's slug.

### When no user is present

An agent working unattended must be able to run the whole procedure, using
"determine automatically" and equivalent defaults in place of every question.
Two of those defaults were settled explicitly:

- **The matching item already has a spec or plan:** revise it automatically —
  dispatch the revision subagent without asking.
- **The idea is too unclear to file:** drop it into the work inbox as a raw
  entry, so a later triage with a user present decides what it means.

## Consolidation the requester wants considered

This overlaps existing procedures, and they should be unified where that
makes sense, not given a fifth copy. Checks for duplicate or already-tracked
work are currently written separately in four places (listed under
References). The duplicate and superseded check is the part most obviously
shared.

## Context isolation

Searching the backlog pulls a lot of text into the context of the agent doing
it, and the agent that notices the idea is usually busy with something else.
The requester suggested an agent definition the working agent could hand the
idea to, shaped roughly like a function: an idea goes in; an item may or may
not come out. `spec` should decide how much of the procedure that agent can
own, given that `delegation.md` says a subagent cannot ask the user questions.

## Out of scope

- **Jira and other external trackers.** Nothing about creating or linking a
  ticket. Note for `spec`: under `work.tracker.strict: true`, `tcw work new`
  is refused and points to `tcw work tracker import`, so the skill must at
  least not break in that configuration.
- **Another agent changing the matching item while the search runs.** The
  requester accepts that risk; no re-check before amending is required.
- **Messaging the agent that is working an active item.**

## References

- [`skills/tcw-work/references/procedures/audit-backlog.md`](../../../../skills/tcw-work/references/procedures/audit-backlog.md)
  — its inter-item "Duplicate or superseded" check is the overlap the
  requester named first.
- [`skills/tcw-work/references/procedures/search.md`](../../../../skills/tcw-work/references/procedures/search.md)
  — the read-only "is there an item about X" procedure; closest in shape to the
  one-idea-against-the-board check.
- `tcw work stage prompt inbox` — its "Already tracked" exit is a third
  duplicate check, and it says not to ask for more detail at that stage.
- [`skills/tcw-extras-triage-issues/SKILL.md`](../../../../skills/tcw-extras-triage-issues/SKILL.md)
  — §3 "Drop the ones already tracked" is the fourth.
- `tcw work stage prompt request` — already asks for reference material and
  records "asked; none provided"; it does not ask about blockers or origin.
- [`skills/tcw-work/references/procedures/delegation.md`](../../../../skills/tcw-work/references/procedures/delegation.md)
  — `inbox` and `request` are not delegable because a subagent cannot ask the
  user, and a custom agent must earn its place with a different tool set.
- [`agents/tcw-backlog-auditor.md`](../../../../agents/tcw-backlog-auditor.md)
  — the existing read-only research agent pattern.
- [`docs/lifecycle/harness.md`](../../../../docs/lifecycle/harness.md) — the
  skill must work under Codex as well as Claude.
- [`2026-09-01-fan-the-backlog-audit-out-across-every-connected-work-root`](tcw://W/2026-09-01-fan-the-backlog-audit-out-across-every-connected-work-root)
  — also changes `audit-backlog.md`; not a blocker.
- [`2026-09-11-refine-the-plugin-skills-and-lifecycle-prompts-against-the-eval-findings`](tcw://W/2026-09-11-refine-the-plugin-skills-and-lifecycle-prompts-against-the-eval-findings)
  — may rewrite the same inbox and request stage prompts; not a blocker. The
  eval harness it depends on is also how "agents invoke the skill on their
  own" could be measured.
- [`2026-09-15-rewrite-the-readme-to-a-new-outline`](tcw://W/2026-09-15-rewrite-the-readme-to-a-new-outline)
  — the README lists the skills, so a new top-level skill touches it.

## Notes

- **Blockers:** determined by searching the backlog; none found. The related
  items above share files or subject matter, and none has to finish first.
- **Reference material:** taken from the conversation that produced this
  request, as the procedure itself says to do.
- **Origin:** not a bug, and not a follow-up to another work item. It came out
  of a brainstorm in which Codex was also consulted. Codex recommended a shared
  read-only overlap procedure plus stronger `inbox` and `request` stages rather
  than a separate skill. The requester chose a separate skill anyway, for the
  automatic-invocation reason above.
- **Status and stage are separate in TCW**, and the user's original wording
  mixed them ("active/implement, review, or verify stage"). The three branches
  above are the intended meaning: not specced yet, specced or planned, work
  underway.
