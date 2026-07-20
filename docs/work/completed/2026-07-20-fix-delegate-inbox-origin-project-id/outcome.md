# Outcome

Work completed successfully.

## Changes

- `tcw.work.recursion.delegate` now resolves the current node's registered
  project ID and writes it into delegated inbox frontmatter.
- Delegation continues to resolve destinations by direct child project ID and
  remains bounded to the receiving node's raw inbox.
- Direct recursion and sibling-project regression tests now require the stable
  parent project ID instead of the legacy `"."` marker.
- User-facing release notes and the developer changelog describe the correction.

## Verification

- Focused delegation/escalation tests: `10 passed`.
- Full test suite: `648 passed`.
- `tcw capabilities check`: `capabilities OK`.
- `tcw taxonomy check`: `taxonomy OK`.
- `tcw validate`: `validate OK`.
- `git diff --check`: passed.

## Plan deviations

None.

## Follow-ups

No follow-up work is required.
