# Declare the cross-node recursion capabilities

_Compressed planning, at the user's direction: a ledger back-fill of shipped
behavior with no runtime change._

## Capability changes

New — five, all declared `Supported` directly (they describe behavior that already
ships, so the `Missing` + `Planning doc` seeding would falsely claim this item
built them):

| Path | Name | Subject | Feature |
| --- | --- | --- | --- |
| `work/inspect-the-node-topology` | Inspect the node topology | `node` | `connected-project-registry` |
| `work/coordinate-a-cross-node-epic` | Coordinate a cross-node epic | `work-item`, `node` | `connected-project-registry` |
| `work/reconcile-an-epic-rollup` | Reconcile an epic rollup | `work-item`, `node` | `connected-project-registry` |
| `work/delegate-a-request-to-a-child-node` | Delegate a request to a child node | `node` | `work-inbox` |
| `work/escalate-a-request-to-the-parent-node` | Escalate a request to the parent node | `node` | `work-inbox` |

Every `Subject` and `Feature` above is an existing registered taxonomy entry
(`tcw taxonomy list`): `node` and `work-item` are Vocabulary, and
`connected-project-registry` and `work-inbox` are Features. **No taxonomy change** —
nothing had to be minted.

Changed: none. `work/view-the-board` already documents `--include-descendants` and
already carries `Feature: connected-project-registry`; the new entries must not
restate its aggregation behavior.

## Problem

`docs/capabilities/` describes 60 capabilities, 23 under `work/`, and none of them
covers cross-node recursion. `tcw work nodes`, epics and the `initiative`
back-pointer, `reconcile`, `delegate`, and `escalate` all ship and are documented
in `README.md` and `skills/tcw-work`, but the axis whose job is "what can a user
currently do" is silent on all five.

Found while looking for a capability to attach a `changed:` delta to in
`2026-08-13-report-a-refused-reconcile-commit-as-a-cli-error-not-a-traceback`, and
finding none.

## Goals

- Five accurate `Supported` capabilities covering the five commands.
- Content verified against the code and live CLI, not paraphrased from `README.md`.
- Existing entries left alone, with no overlap against `work/view-the-board`.

## Non-goals

- Any runtime change, including to `--help` strings (see the finding below).
- Auditing the rest of the ledger for other gaps.
- New taxonomy entries.
- Restating this session's completed fixes; they already landed in their own
  capabilities.

## Design

One folder per capability via `tcw capabilities add <path> "<Name>" --status
Supported`, then `tcw capabilities set <path> --field "Subject=…"` and
`--field "Feature=…"`, then the `description.md` body. Never hand-edit `meta.yaml`
where `set` applies.

Each body states what the user does, what the command guarantees, and where it
refuses — the shape the existing `work/` entries use. Content each must carry,
verified against source:

- **inspect-the-node-topology** — `tcw work nodes` prints the current node, its
  registered parent, and its registered children; `(none — root)` / `(none — leaf)`
  when either is absent (verified from live output). Only *registered* nodes are
  reported: nearby unregistered repositories are never visited, and a registered
  node whose configured work store does not open is not listed.
- **coordinate-a-cross-node-epic** — `tcw work new --epic` creates a `type: epic`
  item; a task points at it with `--initiative <slug>`, settable later with
  `tcw work edit --initiative`. The relation is gated: a task refuses to `start`
  until its epic is active, and an epic refuses to `complete` while related child
  tasks are open. Once every child is resolved the epic is flagged `ready-to-close`
  and may be completed **directly from `backlog`**, with the Definition-of-Done and
  capability gates still applying. `--force` overrides the relation gates.
- **reconcile-an-epic-rollup** — `tcw work reconcile <epic>` follows registered
  descendants and writes a managed rollup block into the epic's
  `initial-request.md`: a slice table keyed by node, surfaced capability deltas, and
  the next ready actions. Read-only on the capabilities ledger. Idempotent —
  re-running an unchanged rollup writes and commits nothing. `--commit` commits it
  in the repository holding the work store; `--complete-when-ready` auto-completes a
  ready epic with the gates still running. Link to the two capabilities above with
  `tcw://C/…` prose links.
- **delegate-a-request-to-a-child-node** — `tcw work delegate <child-id> "<title>"`,
  body on stdin, optional `--initiative`. Writes exactly one entry into the child's
  configured inbox and nothing else: the node write-boundary is inbox-only, never
  the child's tracked work. **The argument is the child's canonical project ID, not
  a filesystem path** (see the finding). An unknown ID is refused with the list of
  valid children.
- **escalate-a-request-to-the-parent-node** — the same, upward, with no ref
  argument; refuses at the root node with "no parent node to escalate to".

Both request entries record the sending project's canonical ID as `from:`, and
land in the target's inbox wherever `work.path` puts it — failing loudly rather
than creating a phantom `docs/work` if that store cannot be reached (behavior
established by `2026-08-12-honor-the-configured-work-path-at-every-work-store-call-site`).

### Finding, deliberately not fixed here

`tcw work delegate --help` describes its first argument as
`child node path (relative to this node)`. That is wrong. `delegate` builds
`{registered_project_id(node_root, c): c for c in child_nodes(node_root)}` and
matches against the **canonical project ID**. Verified empirically on a fixture
where the directory name and project ID differ:

```
'sub-dir-name'   -> ValueError: no child node 'sub-dir-name'. children: canonical-id
'canonical-id'   -> OK  …/sub-dir-name/docs/work/inbox
```

The existing tests miss it because `mk_node` derives the project ID from the
directory name, so the two always coincide. Correcting the help string is a runtime
change and out of scope here; it needs its own item. The capability describes the
true behavior, so the ledger and `--help` will disagree until that lands — stated
here so the disagreement is a known, tracked one rather than a fresh inconsistency.

## Acceptance criteria

1. All five paths exist under `docs/capabilities/work/`, each with `meta.yaml` and
   a non-empty `description.md`, and each reads `Status: Supported`.
2. Each carries the `Subject` and `Feature` values in the table above, and
   `tcw capabilities check` passes (it validates that `Feature` resolves to a
   taxonomy entry of kind Feature).
3. `tcw capabilities list` shows 65 capabilities, 28 under `work/`.
4. `delegate-a-request-to-a-child-node`'s body states the argument is a canonical
   project ID, not a path.
5. No existing capability's `meta.yaml` or `description.md` is modified.
6. No file under `tcw/` is modified.
7. Any `tcw://` link used in the bodies resolves — `tcw validate` exits 0.
8. `tcw taxonomy check`, `tcw capabilities check`, `tcw capabilities drift`, and
   `tcw validate` all exit 0, and the full Python suite passes.

## Risks

- **Back-filling from documentation instead of source** is the whole failure mode
  here, and the `--help` finding is proof it is not hypothetical: the README and
  `--help` are not reliable sources for what the code does. Every claim in a body
  must come from source or live CLI output.
- Overlap with `work/view-the-board`, which already covers descendant aggregation.
  The new entries describe topology, epics, rollups, and requests — not board
  rendering.
- Declaring five `Supported` capabilities at once inflates the ledger's apparent
  coverage. That is the point — the behavior already shipped — but it means
  `tcw capabilities drift` can no longer flag this area as missing, so an error in
  these descriptions is now the ledger lying rather than the ledger being silent.

## Notes

- `capabilities.yaml` for this item lists all five under `new:`. The completion
  gate requires a `new:` capability not to read `Missing` at `complete`; declaring
  them `Supported` at creation satisfies it, which is correct here because the
  behavior genuinely exists.
