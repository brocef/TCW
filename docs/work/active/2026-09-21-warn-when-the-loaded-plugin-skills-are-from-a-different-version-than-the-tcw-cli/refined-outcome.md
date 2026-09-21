# Refined outcome: warn when the plugin skills and the tcw CLI differ in version

## Decision

**Accepted** on 2026-09-21 in an autonomous run. The requester had authorized the
batch to be finished, self-reviewed, verified and released while they were away.

## Evidence

- Full suite as CI runs it (bare `pytest`, no git identity): **3934 passed** at
  87e321c0. After the verify fixes, `test_check_versions`, `test_session_bootstrap`
  and `test_plugin_manifests` gave 115 passed. Each fix's test failed before it and
  after a mutation check.
- `tcw:verifier`: accept. `adversarial-code-reviewer`: its findings were all fixed.
- Criterion 16's Claude and Codex transcripts are in outcome.md.

## Deferred

- Unverified: whether `codex plugin marketplace upgrade tcw` alone updates an
  installed plugin (the warning gives both Codex commands), and whether Codex runs
  the plugin's SessionStart hook.
- No GitHub issue is attached. Reported by the proposit-app agent.

## Closeout

`tcw work complete` merges `work/<slug>` into `main` locally. The push happens with
the v2.5.1 release.
