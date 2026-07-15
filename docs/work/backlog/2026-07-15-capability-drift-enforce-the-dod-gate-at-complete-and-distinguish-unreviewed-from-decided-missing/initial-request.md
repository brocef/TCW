# Capability drift: enforce the DoD gate at complete, and distinguish unreviewed from decided Missing

Source: https://github.com/brocef/TCW/issues/4. Related bug:
[capabilities set rejects inherited paths](tcw://W/2026-07-15-capabilities-set-rejects-inherited-capability-paths-that-show-list-accept)
— a likely contributing cause, worth fixing first.

Supersedes the `2026-06-19-hard-dod-gate-commit-range-enforced` backlog stub
(dropped), which carried the one-line deferred hook from
`docs/plan/phase-6-beyond.md` — *"refuse `tcw work complete` unless declared
capability files appear in the item's commit range"* (phase-5-work A.7, B.9).
That hook is mechanism 1 below, with the enforcement check still to settle.

## Product changes

`Missing` today means either "deliberately not built" or "built, nobody flipped
it", and only reading the code tells you which. In the reporter's 5-node
workspace, 10 capabilities are shipped but still read `Missing`, and
`tcw capabilities check` reports `capabilities OK` in exactly that state. Their
server node has 44 `Missing` entries; several are correctly `Missing`, so the set
is genuinely mixed and re-deriving ground truth is the expensive part. Downstream
artifacts that quote gap counts go wrong silently — one epic is scoped around a
number that was already stale when written.

Two drift vectors:
1. **Deferred at completion** — the item ships, `outcome.md` says the flips are
   deferred, the item completes `--resolution done`, nothing flips. The DoD
   "capabilities reconciled" item is self-attested with nothing behind it.
2. **Inheritance default** — a capability added to a federated master lands on
   every consumer as `Missing`, and nothing tells the consumer a new entry
   appeared. A consumer that already shipped it never overrides.

Two independent mechanisms; either helps, and they compose:

1. **Give the DoD gate teeth.** When a work item's `capabilities.yaml` sidecar
   (or its spec's `## Capability changes` section) names capabilities, have
   `tcw work complete` fail closed unless they were actually reconciled — the
   same posture `complete` already takes on a worktree merge conflict. **Open
   design question:** the old phase-6 hook framed the check as *declared
   capability files appear in the item's commit range*; issue #4 frames it as
   *the declared statuses actually moved*. These differ — a commit-range check is
   filesystem-flavored and would need the litmus test (could a Jira-backed store
   honor it?), whereas comparing declared vs. current status is expressible in
   the abstract store vocabulary. Settle this in the spec; prefer the status
   comparison unless it proves insufficient.

   The reporter explicitly pushes back on solving this with stronger skill
   wording: the instruction was read, followed as far as writing the intent down,
   then abandoned at the last step. Nothing checked.

2. **Distinguish "unreviewed" from "decided".** Have `check` (or a new
   `capabilities drift`) flag inherited capabilities with no local override as
   *unreviewed* rather than silently reporting the master's default. That gives
   `Missing` back its meaning: an explicit local decision.

Reporter offers a reproducible 5-node federation with ~10 known-drifted
capabilities to validate a detector against.

## Technical changes

## Meta changes
