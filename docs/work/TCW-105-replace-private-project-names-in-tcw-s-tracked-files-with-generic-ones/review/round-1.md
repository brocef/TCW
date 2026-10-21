---
verdict: accepted
judges: 1
---
# Review round 1 — TCW-105

Reviewed by the session that delegated the work, which did not write it. It
read the commit's diff and ran the checks below just now.

1. **Met.** A search of `main` for the private names (excluding `pnpm-lock.yaml`)
   finds only the kept Jira site address.
2. **Met.** The implementer's mutation checks (eight, listed in the implement
   round) cover each changed assertion. The recomputation method was
   validated against the old value.
3. **Met, with the timing failures explained.** On `main`, the affected test
   files pass (274 passed, 38 skipped). The full suite at `6a91ff29`, which
   lacked only this commit, gave `2 failed, 5160 passed`. The two failures
   are a timing test unchanged since v3.0.1 that fails only under load (see
   TCW-101's review round). CI judges it on publication.

Repository rules: the suite was run as CI runs it, in the worktree;
`documentation-sync` needs nothing (no behavior change, names only); not
from a GitHub issue.
