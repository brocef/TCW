# Resolve capabilities.yaml sidecar paths while an item is still being worked

## Origin

GitHub issue [#27](https://github.com/brocef/TCW/issues/27), filed 2026-09-02
by @brocef, against tcw 1.2.2.

> ### Steps to reproduce
>
> A work item's `capabilities.yaml` sidecar lists `new:` / `changed:` capability paths. A federated capability must be named by its canonical node id (`proposit-shared/arguments/see-version-history`) or bare (`arguments/see-version-history`); the `shared/…` shorthand that specs and plans habitually use does not resolve.
>
> 1. In a node that inherits a federated capability, confirm the resolver rejects the shorthand:
>
> ```
> $ tcw capabilities show arguments/see-version-history
> ## See an argument's full version history  (proposit-shared/arguments/see-version-history)  [proposit-shared]
> ...
> $ tcw capabilities show proposit-shared/arguments/see-version-history
> ## See an argument's full version history  (proposit-shared/arguments/see-version-history)  [proposit-shared]
> ...
> $ tcw capabilities show shared/arguments/see-version-history
> tcw capabilities show: no such capability: shared/arguments/see-version-history
> ```
>
> 2. Now leave such a path in a sidecar. Two items in my store carry one today:
>
> ```
> docs/proposit-mobile/work/completed/<slug>/capabilities.yaml:5:    - shared/authoring/build-with-the-assistant
> docs/proposit-mobile/work/completed/<slug>/capabilities.yaml:18:   - shared/authoring/add-a-claim-to-a-premise
> ```
>
> 3. Run both validation commands:
>
> ```
> $ tcw validate
> ... 25 problem(s).      # every one a tcw:// link problem; neither sidecar mentioned
> $ tcw capabilities check
> capabilities OK
> ```
>
> ### Expected vs. actual
>
> - **Expected:** a capability path in a `capabilities.yaml` sidecar that does not resolve is reported by `tcw validate`, by `tcw capabilities check`, or by both — the same way #10 made `taxonomy add --vocab` refs checkable.
> - **Actual:** neither command resolves sidecar capability paths at all. Both pass with unresolvable paths sitting in the store. The error surfaces only much later, at `tcw work complete`, as `declared (changed) but does not resolve` — by which point the item is finished and the sidecar has usually been copied into sibling slices of the same epic.
>
> This is the `capabilities.yaml` analogue of #10 (`taxonomy add --vocab` accepting unresolvable refs silently), and sits next to #8, which was about the same file failing a different way.
>
> ### Remediation
>
> Resolve sidecar `new:`/`changed:` paths in `tcw capabilities check` (and/or `tcw validate`), reporting each unresolvable one with its file and line — so a bad path is caught when it is written rather than at completion.
>
> Separately worth considering: whether `<prefix>/…` should resolve when the prefix is an unambiguous suffix of exactly one connected node id (`shared/` → `proposit-shared`). Rejecting it is defensible; doing so silently at write time is what costs the time.
>
> ### Important scoping constraint
>
> Do **not** validate sidecars on completed items. A completed work item is a
> historical record of what was true when it shipped; its owner cannot reasonably
> be expected to keep its `capabilities.yaml` current as capabilities are later
> renamed, moved between nodes, or retired. Resolving paths across the whole store
> would therefore make `tcw validate` permanently and increasingly noisy, and the
> noise would grow with every completed item — which is a worse outcome than the
> bug being reported here.
>
> The value is entirely in catching a bad path *while the item is still being
> worked*, before it is copied into sibling slices of the same epic. Scoping the
> check to `backlog/` and `active/` (and to whatever `tcw work complete` is about
> to write) gets all of that benefit with none of the noise. The two stale paths
> quoted above are illustrative of the validators not resolving sidecar paths at
> all; they are not themselves things that need fixing.

## Triage notes

Confirmed against the working tree at 1.2.3. The resolution logic already exists
and is reusable — `capability_gate()` in `tcw/work/recursion.py:25-66` resolves
both `new:` and `changed:` paths through `FsCapabilitiesStore` — but its only
callers are the `complete` path and `reconcile --complete-when-ready`. Neither
`FsCapabilitiesStore.check()` nor `tcw/validate.py` reads a work item's
`capabilities.yaml` at all, so the reporter's "neither command resolves sidecar
paths" is accurate rather than a scoping choice made elsewhere.

Distinct from two adjacent backlog items, which this does not subsume:

- `2026-08-31-nothing-verifies-that-a-changed-capability-was-actually-changed` —
  a declared `changed:` path that resolves but was never edited. Semantics, not
  resolution.
- `2026-08-21-nothing-enforces-a-spec-s-declared-capability-deltas-without-a-capabilities-yaml`
  — a spec declaring deltas with no sidecar at all. No file, no gate.

The prefix-shorthand question (`shared/` → `proposit-shared`) is the reporter's
own aside and is recorded here as an open question, not as accepted scope.
