# Scan every Markdown file for phantom CLI verbs, excluding archives

## Origin

Post-mortem recommendation #1 from
`2026-07-28-audit-the-work-backlog-with-subagents-and-make-the-workflow-reachable-from-codex`
(see its `post-mortem.md`, finding 1). Rated **worth making**.

## Problem

`tests/test_documented_cli_surface.py` enumerates the directories it scans:

```python
DOC_FILES = sorted(
    [REPO / "README.md"]
    + list((REPO / "skills").rglob("*.md"))
    + list((REPO / "commands").glob("*.md"))
    + list((REPO / "agents").glob("*.md"))
    + list((REPO / "docs" / "capabilities").rglob("*.md"))
)
```

An inclusion list is a scope that can be got wrong, and it already was. The
acceptance criterion it enforces is universally quantified — *"no file **in the
repo** documents …"* — while the check enumerates five roots. The fifth was added
only after a phantom verb survived in `docs/capabilities/` precisely because the
list did not name it. The same blind spot was inherited by three lifecycle stages
in a row, because each reused the previous one's scope instead of re-deriving it
from the criterion.

The next tree someone adds is outside the list by default. That is the defect.

## Product changes

None. Contributor-facing test change; no `tcw` CLI surface or user-visible
behavior changes.

## Technical changes

Invert the scope: scan **every `*.md` in the repo except the archival trees**.

Archives are documents that record what was decided at a point in time, and are
expected to name commands that no longer exist:

- `docs/work/` — lifecycle artifacts, frozen once written
- `docs/plan/` — the retired build-phase specs
- `docs/superpowers/` — archived specs and plans
- `docs/changelogs/`, `docs/release-notes/` — historical entries

**Verified viable before filing** (not assumed): scanning every `*.md` outside
those five trees produces exactly **three** failures, all archival —
`docs/plan/phase-5-work.md` (`tcw work rename`) and two `docs/superpowers/`
documents (`tcw work block`, `unblock`, `check`). So the exclusion list is a
principled class, not an allowlist reverse-engineered to make the test pass.

Also exclude `node_modules/` and any build output under `web/`.

Consider whether the exclusion list belongs in the test or in a small shared
constant — `tcw validate` may eventually want the same notion of "archival tree".
Do not build that abstraction speculatively; note it and move on if only one
consumer exists.

## Meta changes

The point is to replace a judgment ("remember to widen the scope") with a
mechanism, matching the repo directive that anything which must be guaranteed
belongs in the tooling rather than in an instruction someone has to remember.

## Acceptance criteria

- The test derives its file list by exclusion, not inclusion.
- Adding a new documentation tree brings it under the guard automatically, with
  no test edit. Prove it: add a temporary `.md` naming a fake verb somewhere new
  and confirm the suite goes red.
- The exclusion list names archival trees only, each with a one-line reason.
- `pytest` green.

## Notes

The companion post-mortem recommendation — a one-line rule at the `spec` stage
that a sweep for sibling defects is repo-wide by default, or states why it is
narrowed — is **not** covered here. It addresses prose claims the guard cannot
parse (a stale factual assertion, a safety flag in an unopened file). Decide at
spec time whether to fold that one-line edit to `stage-spec.md` into this item or
leave it separate; it is small enough that a separate item may cost more than the
change.
