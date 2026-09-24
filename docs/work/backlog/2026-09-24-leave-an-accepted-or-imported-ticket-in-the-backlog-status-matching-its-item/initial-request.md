# Leave an accepted or imported ticket in the backlog status, matching its item

## What is wanted

After `tcw work inbox accept <KEY>` or `tcw work tracker import <KEY>`, the
ticket should sit where its new item sits: in the backlog, still claimed by the
person who took it. Today the claim moves the ticket to In Progress through
`work.tracker.transitions.start`, while the item it creates is a backlog item, so
the tracker says the work has started when it has not.

The user asked for this to be fixed straight away and shipped in a patch release
(2026-09-24).

## Why

Seen accepting TCW-1: Triage → To Do (`Accept`) → In Progress (`Start`), with the
item in `backlog`. Nothing brings the two back into line afterwards —
`tcw work tracker sync` reports the item "current" — so the ticket had to be moved
back by hand. The TCW Jira workflow had no way back to To Do at all until a `Stop`
transition (In Progress / In Review → To Do) was added the same day.

## Constraints

- Keep what the claim protects: two people importing the same ticket at once must
  still not both end up holding it.
- Do not pull back a ticket someone was **already** working when they imported it
  (the claim finds it In Progress and assigned to them). `deliver` refuses to move
  a backlog item's ticket for exactly that reason, after a `sync` once did so
  silently.
- A workflow with no way back must not make the import fail: the item already
  exists and is bound by then.

## Notes

- Origin, symptom and references are in `intake.md`.
- Reference material: the request came from chat; the references in `intake.md`
  are the ones gathered while filing it. Nothing further asked.
