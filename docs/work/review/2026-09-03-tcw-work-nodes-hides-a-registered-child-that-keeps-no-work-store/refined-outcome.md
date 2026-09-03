# Refined outcome — `tcw work nodes` hides a registered child that keeps no work store

_Accepted._

## Decision

Accepted, including the reversal of an existing assertion, which is the part that
deserved scrutiny and got it.

## Evidence

- **Suite:** 2311 passed; the established environmental failures.
- **The orchestration root lists both children** where it read `(none — leaf)`.
- **The two reasons are distinguished** and each is asserted: a routing node
  gets `(no work store)`, a declared-but-unobtained one gets
  `(work store not provisioned here)`.
- **A genuine leaf still prints `(none — leaf)`.**
- **`child_nodes` is untouched**, so every cross-node operation still sees the
  filtered set — asserted by the cross-node suites passing unchanged.

## Deferred follow-ups

- **`tcw work nodes` cannot run at a routing node**, because it is a work
  subcommand and the node has no work store. Its topology is visible from either
  side, so nothing is unreachable — but a node-level `tcw nodes` would be the
  honest home for this command, and that is a separate question.

## Closeout choices

- **Merge route:** the session branch.
- **Documentation:** the routing-node changelog entry, and the
  `work/inspect-the-node-topology` body.
- **Capabilities:** `work/inspect-the-node-topology` changed. Its old sentence —
  omitted projects mean the listing shows what cross-node commands can reach —
  was a real contract, and the replacement keeps that guarantee by attaching it
  to the unmarked entries rather than dropping it.
- **Version:** deferred to the run's single cut.
- **Originating GitHub issue:** none.

## Notes

One pre-existing assertion was reversed. It said an unprovisioned child
"says so by absence", which was true of a graph where every registered node kept
a board; with routing nodes supported, absence became ambiguous between two
situations and false about a third — a node having children at all. The
replacement asserts more than the original did, which is the test to apply before
reversing an assertion someone wrote deliberately.
