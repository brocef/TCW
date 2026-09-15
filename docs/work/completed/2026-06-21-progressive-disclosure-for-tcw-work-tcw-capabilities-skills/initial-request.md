# Progressive-disclosure for tcw-work + tcw-capabilities skills

## Product changes

## Technical changes

- Refactor `skills/tcw-work/SKILL.md` (54 lines) and `skills/tcw-capabilities/SKILL.md`
  (45 lines) into a **thin router** + `docs/` sub-docs read on demand, the way
  `skills/tcw-plugin/` now works (router gates on a cheap check; detail lives in
  `docs/*.md` pulled in only for the relevant sub-case).
- **Defer only the genuinely rare sub-procedures; keep the core lifecycle inline:**
  - `tcw-work`: move *Recursive process-inbox* and *Decompose into a cross-node
    epic* to `docs/`; keep the lifecycle handshake (new/start/complete) in SKILL.md.
  - `tcw-capabilities`: move *Product-layer coordination (orchestrator-relay)* to
    `docs/`; keep the planning gate, contradiction-detection, and ledger flip inline.

## Meta changes

- **Caveat — marginal payoff.** Unlike `tcw-plugin` (a ~40-line procedure needed
  only when `tcw` is broken), these skills are already ~50 lines of mostly
  always-relevant judgment. Splitting saves ~20–25 lines of always-loaded context
  each, at the cost of indirection. Decide during planning whether it clears the
  bar; it may be a no-op for content this small.
- If adopted, document the **skill-authoring convention** (router + `docs/` sub-docs,
  gated read) in AGENTS.md so future skills follow it.

Spec/plan to be written into this folder at planning time.
