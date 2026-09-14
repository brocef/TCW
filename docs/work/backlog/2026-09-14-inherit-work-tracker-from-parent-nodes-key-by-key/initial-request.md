# Inherit work.tracker from parent nodes, key by key

## Request

In a workspace of connected TCW nodes, every node that reads the same Jira
project has to repeat the whole `work.tracker` block in its own
`tcw-config.yaml`. Only `candidate-query` really differs from node to node. The
site, the credential variable names and the claim transition name describe the
Jira site and its workflow, not the node. The requester's workspace has six
nodes and six copies of the block. A copy that someone forgot to update still
parses, so nothing reports it, and it keeps working with old values. A copy
damaged during an edit disables that node's tracker completely.

The requester wants a node's `work.tracker` settings to come from its parent
nodes, with the node's own settings winning key by key. A child that only
narrows the query should need to write nothing but `candidate-query`.

What the requester asked for, in their terms:

- **Every ancestor, not just the direct parent.** A node looks up the whole
  chain of parents, including a parent that keeps no board of its own. The
  requester's workspace has three levels (workspace root → repository root →
  packages), and settings written once at the workspace root should reach the
  packages. The nearest node that sets a key wins for that key.
- **Merge per key, not per block.** A child that writes `tracker:` with one key
  keeps every other key from its ancestors. Nested mappings (`credentials`,
  `transitions`) merge the same way.
- **An explicit opt-out: `tracker: none`.** A child that tracks nothing writes
  that to cut off inheritance. A child that reads a different site can instead
  set its own `base-url` and credentials.
- **Validation sees the merged result.** `tcw validate` checks the settings a
  node actually ends up with, and each problem names the file the offending
  value came from, the way tracker problems are already prefixed with their
  file.

Benefits the requester named: one place to change the site, credentials or
transition names for a whole workspace; no forgotten copy left behind using old
values; one line of tracker configuration for a new node.

## Constraints

- **Only `work.tracker`.** Other settings under `work:` (lifecycle bindings,
  documentation entries, retention) stay per node. Inheriting those would be a
  separate item.
- **The key set is not fixed.** Planned items under the same initiative (claim,
  sync, strict mode) will add keys under `work.tracker`. The claim item is being
  planned by another session at the same time. Inheritance should apply to keys
  added later without being changed for each one.
- **Blocked by** `2026-09-12-configure-an-external-tracker-and-read-its-tickets`,
  which is now completed.

## Out of scope

- The two notes from `tcw work tracker show` that the issue's "side notes"
  describe. Those were fixed on the configure item (commits `cbbcd72d`,
  `29394fd7`).
- Inheritance for any `work:` setting other than `tracker`.

## Notes

- Came from GitHub issue #36, filed by the requester. The issue stays open
  until this item ships; see `intake.md` for the full text.
- The issue says taxonomy `extends` resolves one level only. That is out of
  date: `2026-07-01-transitive-taxonomy-inheritance` made it resolve through
  every ancestor, and the requester chose the same rule here.
- Questions the requester was not asked, left for `spec` to settle and mark as
  its own decisions:
  - Whether a parent may hold a partial block that is not usable by itself
    (for example, site and credentials but no `candidate-query`), and what
    `tcw validate` reports at that parent.
  - What a node gets when a declared parent is not checked out on this machine.
  - How any future list-valued key under `work.tracker` merges.
- Reference material: asked; the requester selected none. The references below
  are the agent's suggestions.

## References

- GitHub issue [#36](https://github.com/brocef/TCW/issues/36) — the original
  report, with the six-node example.
- `docs/work/completed/2026-07-01-transitive-taxonomy-inheritance/` — the
  existing precedent for resolving settings through every ancestor.
- `docs/work/completed/2026-09-12-configure-an-external-tracker-and-read-its-tickets/spec.md`
  — defines the `work.tracker` keys and the rule that a malformed block means
  no tracker at all.
- `docs/work/active/2026-08-04-supplement-filesystem-tcw-work-with-an-external-tracker-bridge/spec.md`
  — the later items that will add keys under `work.tracker`.
