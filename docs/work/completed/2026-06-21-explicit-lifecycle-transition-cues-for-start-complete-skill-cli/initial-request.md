# Explicit lifecycle-transition cues for start/complete (skill + CLI)

## Product changes

## Technical changes

## Meta changes

## Product changes

## Technical changes

- Make the `tcw-work` skill's lifecycle section imperative + trigger-based:
  explicit "run `tcw work start` before the first line of code" / "run
  `tcw work complete` the moment work is done & verified" cues, plus a self-check
  (editing code while the item is still in `backlog` ⇒ you skipped `start`).
- Add CLI next-step nudges to **stderr** (matching the existing `escalate`
  reminder): `tcw work new` → hint to run `start`; `tcw work start` → hint to run
  `complete`. Reaches the agent even when the skill never loads — the likely cause
  of the reported miss.

## Meta changes
