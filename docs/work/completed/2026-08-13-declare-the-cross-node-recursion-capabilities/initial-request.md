# Declare the cross-node recursion capabilities

## Product changes

The standing capability ledger has no entry for any of TCW's cross-node recursion
behavior, even though all of it ships, is documented in `README.md`, and is driven
by `skills/tcw-work`. A reader asking "what can a user do with TCW?" from
`docs/capabilities/` alone would conclude the tool has no notion of connected
projects, epics, or requests between them.

Five commands are unrepresented:

| Command | What a user does with it |
| --- | --- |
| `tcw work nodes` | See this node's registered parent and child nodes |
| `tcw work new --epic` / `--initiative` | Coordinate slices across nodes under one epic |
| `tcw work reconcile <epic>` | Consolidate child slices into the epic's rollup |
| `tcw work delegate <child> "<title>"` | Send a request *down* into a child node's inbox |
| `tcw work escalate "<title>"` | Send a request *up* into the parent node's inbox |

Nothing is broken. This is a ledger that has drifted behind the tool: the
capabilities axis is supposed to describe what a user can currently do, and for
this whole area it describes nothing.

## Technical changes

None. No runtime code changes. This adds folders under `docs/capabilities/work/`
via `tcw capabilities add`, each with `meta.yaml` and `description.md`.

The entries describe **already-shipped** behavior, so they are declared
`Supported` directly rather than seeded `Missing` with a `Planning doc` pointer.
That pointer exists for capabilities a work item is about to build; using it here
would claim this item built the behavior, which it did not.

## Constraints

- Describe behavior as it is today, verified against the code and the CLI — not as
  the README summarizes it. A back-fill that restates documentation without
  checking it just moves any existing inaccuracy into a second place.
- Match the ledger's existing granularity: one capability per user-facing command,
  the way `discard-a-work-item` and `drop-a-work-item` are separate.
- Link `Subject` and `Feature` where a registered taxonomy entry already fits. Do
  not invent unregistered feature strings.
- Do not restate the fixes from this session's completed items. Those already
  landed in the capabilities they belong to.

## Out of scope

- Auditing the rest of the ledger for other gaps. This item covers the cross-node
  recursion area that was found; a broader sweep is separate work.
- Any new taxonomy Vocabulary or Feature entry. If a needed Feature turns out not
  to exist, note it rather than minting one here.
- Changing existing capability descriptions, except where a new entry makes one
  read as overlapping.

## References

- `2026-08-13-report-a-refused-reconcile-commit-as-a-cli-error-not-a-traceback` —
  its `spec.md` recorded this gap. It was found by checking the ledger for a
  capability to attach a `changed:` delta to, and finding none.
- `README.md` — "Cross-node recursion (epics across repos)" is the user-facing
  description of all five commands, and the closest thing to a spec for them today.
- `skills/tcw-work/references/cross-node-deltas.md` and `epic-deltas.md` — the
  agent-facing account of the same behavior.

## Notes

- Granularity (five per-command entries rather than three merged ones) and the
  compressed planning depth were both chosen by the user when this item was filed.
- Asked for further reference material; none beyond the above.
