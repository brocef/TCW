# Refined outcome — The epic owner walk stops at a parent that has no work store

_Accepted._

## Decision

Accepted, with the limitation stated rather than papered over: this ships proven
against fixtures and unproven against a real graph, because no real graph has the
shape yet. The `proposit-app` repository-root node will be the first, and it is
the next piece of work.

## Evidence

- **Suite:** 2271 passed; the failures are the established environmental set.
- **Eight new tests** over a routing-node graph that `tcw validate` accepts, so
  the shape under test is one a user could legally build today — which is what
  makes the silent failure a defect rather than an unsupported configuration.
- **Both directions fixed and both asserted.** The upward walk finds an epic two
  levels up; the downward walk finds its slice. The count assertion on
  `initiative_children` guards the risk that a wider walk double-counts.
- **The two refusals now differ.** "This is the root" and "no registered ancestor
  keeps a work store" are separate messages with separate tests, because they
  send the reader to different places.
- **No regression in the ordinary shape.** Every pre-existing multi-node,
  recursion and epic test passes unchanged, which is what "a graph with no
  storeless nodes behaves exactly as today" means in practice.

## Deferred follow-ups

- **The real-graph check remains open.** When the `proposit-app` root node
  exists, run a cross-repository epic rollup from the orchestration node and
  confirm the package slices appear. Recorded in `outcome.md` as outstanding.
- **The reconcile timing comparison was not run** and could not be meaningfully:
  this node has no registered children, so the widened walk does not execute
  here. Worth a look on a graph where it does.
- **The fixture did not land as a red commit**, which the plan asked for. No
  further action, but the deviation is on the record.

## Closeout choices

- **Merge route:** the session branch.
- **Documentation:** README, release notes, changelog, the cross-node skill
  reference, two capability bodies.
- **Capabilities:** `work/inspect-the-node-topology` and
  `work/escalate-a-request-to-the-parent-node` reworded. No new capability — this
  restores a relation rather than adding one.
- **Version:** deferred to the end of the run.
- **Originating GitHub issue:** none.

## Notes

Accepting work whose only proof is a fixture is a judgement, not an oversight.
The alternative was to hold this item until the consumer-side node existed, which
would have inverted the dependency: that node cannot be built until TCW tolerates
it.
