# Fix delegate inbox origin project ID

## Product changes

Fix `tcw work delegate` so the generated inbox document identifies the
originating project by its registered stable project ID. In TCW 0.13.0,
delegating from the `proposit-app` project incorrectly writes `from: .` rather
than `from: proposit-app`.

## Technical changes

Replace the delegation path's hard-coded `"."` origin with the current node's
registered project ID, matching `escalate` and the registered-project graph
contract. Update regression tests that still encode the legacy relative-path
metadata.

## Meta changes

Cut a patch release after implementation, verification, documentation sync,
and work-item closeout. Do not push the resulting commit or tag.
