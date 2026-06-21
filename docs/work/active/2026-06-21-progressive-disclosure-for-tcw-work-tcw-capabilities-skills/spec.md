# Spec — progressive disclosure for the tcw-work skill

## Scope decision (refines content.md)

The original item proposed splitting **both** `tcw-work` and `tcw-capabilities`.
At planning we narrowed to **`tcw-work` only**:

- `tcw-work` grew from 54 → **107 lines** (the nested-work-items feature added the
  decompose + cross-node-epic blocks). ~60% of the body is now conditional
  sub-procedure → splitting clears the bar.
- `tcw-capabilities` (45 lines) has only ~7 deferrable lines (orchestrator-relay).
  Splitting saves nothing for the cost of indirection → **left untouched**, per the
  item's own "may be a no-op for content this small" caveat.

## Target state

`tcw-work` becomes a **router + gated docs**, the `tcw-plugin` shape.

`skills/tcw-work/SKILL.md` (router, ~45 lines) keeps **inline**:
- frontmatter description (the always-loaded trigger list — unchanged)
- intro (state machine + REQUIRED SUB-SKILL: tcw-capabilities)
- Three-axis / product-first planning + the "write spec.md/plan.md in the folder" rule
- The lifecycle handshake (new / start / complete)
- Resume (across sessions)
- a **"Sub-procedures (read on demand)"** section gating the three docs
- the Quick reference table (kept whole — it is the always-useful cheat sheet)

`skills/tcw-work/docs/` (read only on the matching branch):
- `process-inbox.md` — Recursive process-inbox (incl. orchestrator-triages-own-inbox)
- `decompose.md` — Keep items small / decompose into `--parent` child items
- `cross-node-epic.md` — Orchestrator cross-node epic + the "which path?" decision

## Acceptance criteria

1. **No guidance lost** — every line of the current `tcw-work/SKILL.md` survives
   verbatim-or-equivalent, either inline in the router or moved into a `docs/` file.
   (diff check: concatenating router + docs covers the old content.)
2. Router is **self-sufficient for the core lifecycle** — new/start/complete,
   planning, resume need no `docs/` read.
3. Each `docs/` file is reachable by a **clear gate condition** stated in the router
   (e.g. "Triaging an inbox? →", "Splitting a large item? →", "Across separate repos? →").
4. `docs/` links use relative paths (`docs/x.md`) like `tcw-plugin/SKILL.md`.
5. `tcw-capabilities` is **unchanged**.
6. AGENTS.md documents the skill-authoring convention (router + gated `docs/`).
7. Changelog `Internal` entry added; no README / release-note change (no CLI or
   user-facing behavior change).

## Out of scope

- Any `tcw` CLI / model / lifecycle change. This is doc restructuring only.
- Refactoring `tcw-capabilities`.
- The stale `0.2.0` plugin-cache copy (separate install concern; not a repo file).
