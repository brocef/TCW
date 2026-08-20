## Origin

Found by adversarial review during 2026-07-30-fix-non-git-write-paths-work-new-and-init-fail-outside-a-git-repository (see its refined-outcome.md, "Deferred, with the user's agreement").

## Problem

`load_yaml` ends in `return data or {}`, so a `tcw-config.yaml` whose entire
content is `[]`, `false`, or `0` is indistinguishable from an empty or absent
file. `init` now rejects a config that is a non-empty non-mapping, but the falsy
forms slip through as "no configuration" and the command proceeds.

## Shape

Every caller shares the contract, so this is a change to `load_yaml` and its
callers rather than to one command — which is why it was recorded and left alone
during the non-git work. Distinguishing "absent" from "present but not a
mapping" is the substance of it.
