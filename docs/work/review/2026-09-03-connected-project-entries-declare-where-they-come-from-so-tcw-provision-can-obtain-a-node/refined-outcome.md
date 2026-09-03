# Refined outcome — Connected-project entries declare where they come from

_Accepted._

## Decision

Accepted. Every acceptance criterion is met, and the one that mattered — a real
two-hop fetch across three real repositories — was run rather than simulated.

## Evidence

- **Suite:** 2266 passed, 4 failed, all four the environmental ones that
  reproduce at `v1.2.3`.
- **The end-to-end path works against the real repositories.** From `apps/server`
  of a `proposit-app` checkout with nothing else on disk, one `tcw provision`
  followed the declaration on a sibling package to the orchestration node, then
  that node's declaration to `proposit-core`, and 85 federated taxonomy entries
  resolved where an unreachable-project error used to be.
- **The locator still wins.** Asserted by pointing a declaration at an
  unreachable URL and confirming a present project resolves without it being
  consulted — the test would fail with a network error if the ladder were the
  other way round.
- **Backward compatibility is asserted, not assumed.** A bare string and an
  equivalent `{path: …}` mapping produce identical graphs, and every pre-existing
  registry test passes unchanged.
- **Failing closed still fails closed.** Five malformed entry shapes, each
  reporting its own message and none reading as an unreachable edge.
- **Nothing else reaches the network.** The whole suite runs with no outbound
  access; every provisioning test uses local git repositories.

## Deferred follow-ups

- **The consumer-side configuration** — the `repository` blocks in `proposit-app`
  and `proposit-orchestration`, and the monorepo root node — is out of this
  item's scope by design and is the next piece of work.
- **`tcw validate` is noisier in a partial checkout**: a provisioned node's own
  children are reported unreachable when their repository is not here. Correct
  and non-fatal, and the consumer configuration is where it settles. If it is
  still noisy afterwards, that is a reporting item, not this one.
- **`--refresh` on nodes** works by construction (same provisioner, no
  node-specific branch) but has no dedicated test beyond the component ones.

## Closeout choices

- **Merge route:** the session branch, as with every item in this run.
- **Documentation:** README (entry shape, transitive rule), release notes,
  changelog, the `tcw-work` commands reference — including removing the sentence
  saying `--component` accepts only `work`.
- **Capabilities:** `cli/declare-a-connected-projects-home-repository`
  (`cap-596612`) flipped `Missing` → `Supported`;
  `cli/provision-declared-stores` and `cli/host-multiple-projects-in-one-repo`
  reworded.
- **Version:** deferred to the end of the run, per `CLAUDE.md`.
- **Originating GitHub issue:** none.

## Notes

Two of the four corrections were found by running the thing against real
repositories rather than by a test — including the one that would have shipped a
`tcw provision` that reported "Nothing to provision" in the exact checkout this
feature exists for. That is worth remembering the next time a plan's verification
section is tempted to call a fixture equivalent.
