---
name: tcw-capabilities
description: Use when planning or completing a tcw work item that has a product (user-facing) delta, or when coordinating capability wording across repos — declaring new capabilities, linking them to taxonomy Features, checking a change against the standing ledger, flipping a capability's status as work completes, or relaying canonical product-layer wording. Drives `tcw capabilities`; the taxonomy axis is tcw-taxonomy and the work axis is tcw-work.
---

# The capabilities process

The standing ledger (`docs/capabilities/`) describes *what a user can currently do*. It is the third layer in the TCW chain: `Vocabulary -> Features -> Capabilities -> Work`. This skill keeps it true as work lands. Drive `tcw capabilities`: read with `list`/`show`/`search`, validate with `check`, write status/fields with `set`. Never hand-edit capability markdown when `set` applies. Capabilities may carry `Subject` as a loose taxonomy pointer and `Feature` as a strong pointer to a taxonomy feature. The taxonomy axis is **REQUIRED SUB-SKILL: Use tcw-taxonomy** when a relevant Feature is missing or unclear. The work axis is **REQUIRED SUB-SKILL: Use tcw-work**.

## The `## Capability changes` planning gate (at `tcw work new`)

When a work item has a product delta, name each new / changed / removed capability and record it:

- **New capability:** `tcw capabilities add <namespace/path> "<Capability name>" --status Missing` (seeds `**Status:** Missing`; the heading slug derives from the name), then `tcw capabilities set <namespace/path> --field "Planning doc=<work-slug>"` — the capability→work forward pointer. A freshly-added file is single-capability, so the bare id resolves.
- **Changed / removed existing capability:** record it in the work item's `capabilities.yaml` (the work→capability back-pointer).

## Contradiction-detection (at the moment of change)

Before recording or altering a capability, check it against the standing ledger: `tcw capabilities search <term>` / `tcw capabilities show <id>` for an existing capability the change would contradict (a new capability that conflicts with a `Supported` one; a status that disagrees with reality). Run `tcw capabilities check` (non-zero ⇒ structural problems to fix first). Whether two capabilities *semantically* contradict is judgment — surface candidates to the human; never silently overwrite.

When a capability describes behavior around a registered taxonomy feature, set
`Feature=<feature-ref>` in addition to any useful `Subject=<taxonomy-ref>`.
`tcw capabilities check` verifies that `Feature` resolves to a taxonomy entry
whose kind is `Feature`.

If no suitable Feature exists, do not invent an unregistered string in the
capability. Use `tcw-taxonomy` to add or clarify the Feature first, then link it
from the capability.

## The ledger flip (at `tcw work complete`)

As the item's final pre-freeze step, apply each declared delta so the ledger describes the present:

- `tcw capabilities set <id>#<heading> --status Supported` (Missing → Supported)
- scope/body edits; `tcw capabilities set <id>#<heading> --status Omitted` (Supported → Omitted)

At completion these are long-lived multi-capability files, so include the `#heading` (bare ids are refused when a file holds more than one capability). Flips are idempotent (setting the same status twice is a no-op). This satisfies the work DoD "capabilities reconciled" item by **convention** — the tool acknowledges it at `complete`, it does not verify it.

## Product-layer coordination (orchestrator-relay)

A per-node agent does **not** read the orchestrator's `docs/capabilities/`. To get canonical product-layer wording, escalate over the inbox channel: `tcw work escalate "capability wording: <name>"`. The orchestrator replies (delegates back) with canonical wording and flips the **product-layer** entry when the **epic** completes; a **task** completing flips the **leaf** entry.

The protocol is **non-blocking** — never wait on a reply. If canonical wording isn't available when needed, fall back to in-repo evidence and mark the entry `TODO: confirm wording`.

## Bootstrap (read on demand)

To seed `docs/capabilities/` for a project newly adopting TCW (deep-dive the
codebase → draft → refine with the user → write) → read [`docs/init.md`](docs/init.md).

## Quick reference

| Goal | Command |
|---|---|
| declare a new capability | `tcw capabilities add <ns/path> "<Name>" --status Missing` |
| record the planning back-pointer | `tcw capabilities set <ns/path> --field "Planning doc=<slug>"` |
| flip status at completion | `tcw capabilities set <id>#<heading> --status Supported` |
| associate a feature | `tcw capabilities set <id>#<heading> --field "Feature=<feature-ref>"` |
| check the ledger | `tcw capabilities check` |
| find / read | `tcw capabilities search <term>` · `tcw capabilities show <id>` |
| ask the orchestrator for wording | `tcw work escalate "capability wording: <name>"` |
