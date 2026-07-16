---
name: tcw-capabilities
description: Drives `tcw capabilities` — the Capabilities axis of TCW (what a user can do). Use when a tcw work item has a product (user-facing) delta, or when coordinating capability wording across repos. The taxonomy axis is tcw-taxonomy, the work axis is tcw-work.
when_to_use: Use when planning or completing a tcw work item that has a product (user-facing) delta, or when coordinating capability wording across repos — declaring new capabilities, linking them to taxonomy Features, checking a change against the standing ledger, flipping a capability's status as work completes, or relaying canonical product-layer wording.
allowed-tools: Bash(tcw *), Read, Grep, Glob
metadata:
  author: Brian Cefali
license: Apache-2.0
---

# The capabilities process

The standing ledger (`docs/capabilities/`) describes *what a user can currently do*. It is the third layer in the TCW chain: `Vocabulary -> Features -> Capabilities -> Work`. This skill keeps it true as work lands. Drive `tcw capabilities`: read with `list`/`show`/`search`, validate with `check`, write status/fields with `set`. Never hand-edit capability metadata when `set` applies.

Each capability is a **path-addressed folder** (`docs/capabilities/<path>/` = `meta.yaml` + `description.md`) carrying an opaque stable `id`. Address a capability by its path (e.g. `auth/login`), never a `#heading`. Capabilities may carry `Subject` (a **multi-valued** loose taxonomy pointer — a list of slugs) and `Feature` (a strong pointer to a taxonomy feature). The taxonomy axis is **REQUIRED SUB-SKILL: Use tcw-taxonomy** when a relevant Feature is missing or unclear. The work axis is **REQUIRED SUB-SKILL: Use tcw-work**.

> **Web editing:** Capabilities can also be created and edited through the local `tcw serve` web app; check failures are surfaced in the UI.

## The `## Capability changes` planning gate (at `tcw work new`)

When a work item has a product delta, name each new / changed / removed capability and record it:

- **New capability:** `tcw capabilities add <namespace/path> "<Capability name>" --status Missing` (creates the folder, mints a stable `id`, seeds `Status: Missing`), then `tcw capabilities set <namespace/path> --field "Planning doc=<work-slug>"` — the capability→work forward pointer.
- **Changed / removed existing capability:** record it in the work item's `capabilities.yaml` (the work→capability back-pointer).

**Canonical `capabilities.yaml` schema** — the completion gate reads it, so keep it in this shape: a mapping with `new:` and/or `changed:`, each a list of **current path-addressed capability paths** (`namespace/path`, the form `show` resolves — no `#`):

```yaml
new:
  - auth/login          # seeded Missing at planning; must be flipped by complete
changed:
  - billing/refund
```

(`added:` is read as `new:` for back-compat, but write `new:`.) The gate blocks `complete` if a `new:` path still reads `Missing` or any path doesn't resolve.

## Contradiction-detection (at the moment of change)

Before recording or altering a capability, check it against the standing ledger: `tcw capabilities search <term>` / `tcw capabilities show <id>` for an existing capability the change would contradict (a new capability that conflicts with a `Supported` one; a status that disagrees with reality). Run `tcw capabilities check` (non-zero ⇒ structural problems to fix first). Whether two capabilities *semantically* contradict is judgment — surface candidates to the human; never silently overwrite.

When a capability describes behavior around a registered taxonomy feature, set
`Feature=<feature-ref>` in addition to any useful `Subject=<taxonomy-ref>`.
`tcw capabilities check` verifies that `Feature` resolves to a taxonomy entry
whose kind is `Feature`.

If no suitable Feature exists, do not invent an unregistered string in the
capability. Use `tcw-taxonomy` to add or clarify the Feature first, then link it
from the capability.

A capability's `description.md` body may also cross-reference other objects in
prose with `[text](tcw://C/<path>)` links (or `T`/`W`, and an `<alias>/`-prefixed
namespace for federated objects) — additive to the structured `Subject`/`Feature`
pointers, not a replacement. `tcw validate` resolves these node-wide and the
`tcw serve` viewer makes them clickable.

## The ledger flip (at `tcw work complete`)

As the item's final pre-freeze step, apply each declared delta so the ledger describes the present:

- `tcw capabilities set <path> --status Supported` (Missing → Supported)
- scope/body edits; `tcw capabilities set <path> --status Omitted` (Supported → Omitted)

Address the capability by its path — **any path `show` accepts, including an inherited one** (`set shared/auth/login --status Supported`, or the bare `auth/login`); the local override is written for you. Flips are idempotent (setting the same status twice is a no-op). This is now **enforced**, not by convention: `tcw work complete` fails closed if a capability the item declared `new:` in its `capabilities.yaml` still reads `Missing`, or if a declared path doesn't resolve. Flip it, mark it `Omitted` (deliberately not built), or `--force` with the reason in `outcome.md`. (`changed:` entries are checked only for resolution.)

## Federation (inherit another project's capabilities)

A project can `extends` another's capabilities so shared user stories are declared once — e.g. a web frontend and a mobile app that both drive the same server. `tcw capabilities extends <alias> <path-to-other-repo>` (`--rm <alias>` to drop). Inherited capabilities surface in `list`/`show` flagged by origin (`<alias>/<path>`); they are read-only in structure (`remove` refuses an inherited one) — a child may only:

- **override metadata** — just `tcw capabilities set <path> --status <S>` / `--field K=V` on the inherited path; the override is materialized for you as a local folder whose `meta.yaml` has `overrides: <alias>/<id>` plus the fields you changed (e.g. `Status: Missing`, or `Status: Omitted` for "we deliberately don't have this"). Hand-authoring that file is **not** required — don't; a hand-authored override anywhere in the tree keeps working and `set` updates it in place. (A YAML `null` clears an inherited field, which the store/web `fields` API can write; the CLI's `--field K=` sets an empty string, not a clear.);
- **compose the body** — a `description.md` in that override folder replaces the upstream body; `prependedDocs`/`appendedDocs` (bounded lists in `meta.yaml`) wrap it (e.g. a mobile app appending "…or take a photo with the camera"). The override body is a *delta*: an empty one means "no delta", so **clearing an override's body re-inherits the upstream body** rather than blanking it (that fallback is what makes append-only overrides work). To say "we deliberately don't have this", use `Status: Omitted`, not an empty body.

`tcw capabilities check` validates override targets (dangling / ambiguous / must-be-inherited), attachment lists, and federation cycles.

## Product-layer coordination (orchestrator-relay)

A per-node agent does **not** read the orchestrator's `docs/capabilities/`. To get canonical product-layer wording, escalate over the inbox channel: `tcw work escalate "capability wording: <name>"`. The orchestrator replies (delegates back) with canonical wording and flips the **product-layer** entry when the **epic** completes; a **task** completing flips the **leaf** entry.

The protocol is **non-blocking** — never wait on a reply. If canonical wording isn't available when needed, fall back to in-repo evidence and mark the entry `TODO: confirm wording`.

## Bootstrap (read on demand)

To seed `docs/capabilities/` for a project newly adopting TCW (deep-dive the
codebase → draft → refine with the user → write) → read [`references/init.md`](references/init.md).

## Quick reference

| Goal | Command |
|---|---|
| declare a new capability | `tcw capabilities add <ns/path> "<Name>" --status Missing` |
| record the planning back-pointer | `tcw capabilities set <ns/path> --field "Planning doc=<slug>"` |
| flip status at completion | `tcw capabilities set <path> --status Supported` (local or inherited) |
| flip an inherited entry | `tcw capabilities set <alias>/<path> --status <S>` — writes the override for you |
| associate a feature | `tcw capabilities set <path> --field "Feature=<feature-ref>"` |
| link taxonomy (multi-valued) | `tcw capabilities set <path> --field "Subject=term-a,term-b"` |
| federate another project | `tcw capabilities extends <alias> <path-to-repo>` (`--rm <alias>`) |
| list only local (not inherited) | `tcw capabilities list --local-only` |
| check the ledger | `tcw capabilities check` (this tree) · `tcw validate` (whole node: YAML + `tcw://` links + all component checks) |
| find drift | `tcw capabilities drift` — inherited-but-unreviewed + local-Missing whose Planning doc is a completed item (exit non-zero if any) |
| find / read | `tcw capabilities search <term>` · `tcw capabilities show <path>` |
| ask the orchestrator for wording | `tcw work escalate "capability wording: <name>"` |
