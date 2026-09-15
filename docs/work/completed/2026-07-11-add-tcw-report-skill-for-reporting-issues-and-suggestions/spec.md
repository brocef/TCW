# Spec — Add tcw-report skill

## Problem
TCW users hit `tcw` bugs and have feature ideas, but there is no in-plugin
guidance for sending that feedback *upstream* to the TCW project. Left to
improvise, reports land unactionable (no version, no repro) or not at all.

## Change
Add a new agent-facing skill, `tcw-report`, that routes such feedback to the
project's GitHub issue tracker with a ready-to-fill skeleton for each kind
(bug, suggestion/feature). No `tcw` CLI surface change — reporting targets the
upstream GitHub repo, not the local store (litmus test: not a store operation
at all, so nothing belongs in the store interface).

## Acceptance
- `skills/tcw-report/SKILL.md` exists as a thin, inline router (no `references/`
  split — short and always relevant) pointing at
  `https://github.com/brocef/TCW/issues`.
- Two skeletons: **bug** (environment, steps to reproduce, expected vs. actual,
  remediation) and **suggestion/feature** (motivation, description, benefits).
- Tells reporters to search existing issues first to avoid duplicates.
- Discoverable via the `tcw-plugin` skill map; README + doc-sync entries updated.

## Out of scope
No CLI, model, or store-interface change. Pure additive guidance.
