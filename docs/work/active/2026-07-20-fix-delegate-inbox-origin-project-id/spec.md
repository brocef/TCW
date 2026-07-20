# Fix delegate inbox origin project ID

## Capability changes

No capability ledger change is required. This is a corrective change to the
existing cross-project delegation capability and does not add or remove a user
action.

## Problem

TCW 0.13.0 migrated cross-project coordination metadata from filesystem-relative
paths to registered stable project IDs. `tcw work delegate`, however, continues
to pass a hard-coded `"."` origin to the inbox document writer. A request
delegated from project `proposit-app` therefore contains `from: .`, while an
escalated request correctly contains the originating project's registered ID.

The 0.13.0 registered-project work explicitly requires inbox `from:` metadata
to persist project IDs. Two delegation tests retained the legacy `from: .`
assertion and masked the incomplete migration.

## Goals

- Make delegated inbox documents write the current node's registered project
  ID in `from:`.
- Preserve delegation destination lookup by direct child project ID.
- Add focused regression coverage for both the direct function and registered
  sibling-project fixture.
- Ship the correction in patch release 0.13.1.

## Non-goals

- Change the inbox document schema or adoption behavior.
- Change escalation, which already emits the registered project ID.
- Add a new CLI flag or command.
- Push the release commit or tag.

## Proposed behavior

`delegate(node_root, ...)` resolves the current node's ID through the validated
registered project graph and supplies that ID to `_inbox_write`. For a parent
whose ID is `proposit-app`, the generated frontmatter is:

```yaml
---
from: proposit-app
---
```

This remains storage-neutral coordination metadata: it identifies the origin
by the same stable project identity used throughout the registered graph,
without exposing a filesystem path.

## Acceptance criteria

- Delegating from a registered parent writes its project ID, never `"."`.
- Existing delegation boundaries, initiative metadata, collision handling, and
  destination resolution continue to pass.
- The full pytest suite, `tcw capabilities check`, and `tcw validate` pass.
- Release notes and the developer changelog describe the fix.
- All five version-bearing files agree on 0.13.1, with tag `v0.13.1` at the
  release commit.
