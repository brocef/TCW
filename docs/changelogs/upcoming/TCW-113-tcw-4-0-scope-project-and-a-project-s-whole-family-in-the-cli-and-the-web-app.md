## Added

- `tcw/store/base.py`: `SCOPES`, `ScopeMember`, `ProjectRegistry.scope_members`
  and `covering_scope` (which projects a scope covers, in scope order: the
  ancestors, the project, the descendants breadth first, never a sibling);
  `UNAVAILABILITY_ERRORS` and `is_unavailability` (the failures that make a
  covered project unavailable rather than stop the command); `ScopeObject`,
  `ProjectView`, `ScopeRow`, `scope_rows`, `row_order` and `text_matches`, the
  store-neutral grouping of objects and their overrides into rows, with
  `statuses` and `overridden-by`. (TCW-113)
- `tcw/scope.py`: `cover` and `Covered`, a command's scope with its projects,
  read once each, the unavailable ones and their warnings, and `--project`'s
  refusal. (TCW-113)
- `tcw/tree_scope.py`: the taxonomy and capability `list`, `show` and
  `search` across a scope (`print_rows`, `list_document`, `rows_scope`,
  `refuse_local`), and the records the CLI and the web server share
  (`term_record`, `capability_record` and their detail forms). (TCW-113)
- `tcw/work/scoped.py`: `tcw work list` and `show` across a scope, with
  `children` and `blocks` computed over every covered project's items.
  (TCW-113)
- `--scope` and `--project` on `tcw work list|show`, `tcw taxonomy
list|show|search` and `tcw capabilities list|show|search`; `projects`,
  `statuses` and `overridden-by` in their `--json`. (TCW-113)
- `tcw/config.py`: `command_state` and `command_span`, the span within which
  a command's Jira searches are kept; `tcw/work/jira/client.py`:
  `forget_kept_searches`. (TCW-113)
- `GET /api/project` answers `scopes`, each scope's projects; the read routes
  take `scope` and `project` query parameters. (TCW-113)
- The web client's scope control and project filter (`ui/scope-control.tsx`,
  `model/scope.ts`), the `owned by` badge, the capability page's status by
  project, and one notice per unavailable project. (TCW-113)
- `agents/backlog-auditor.md` and the `audit-backlog` procedure name items by
  their full identifier and cover the project's descendants. (TCW-113)

## Changed

- The default scope of the six taxonomy and capability commands is `own`;
  `show` of an id-path names the project's own object, with a hint naming
  `--scope up` when the project inherits one there. (TCW-113)
- `children` and `blocks` in a work record are computed across the scope,
  each covered project's items once; for an item named by its full
  identifier whose project the scope does not cover, that project's own
  items are counted too, in `tcw work show` and the web app's item page
  alike. (TCW-113)
- The Jira backend's list keeps a search for the length of one command, keyed
  by the site, the account, a digest of the token, the search text and the
  fields, and forgets every kept search on any write. (TCW-113)
- `GET /api/taxonomy` and `GET /api/capabilities` answer an object,
  `{terms|capabilities, projects?}`, rather than a list. Work route keys name
  another project's item by its full identifier; every write route refuses
  another project's object as read-only; `/api/resolve` answers `ok` for an
  object of another project on this machine. (TCW-113)
- `tcw/serve/files.py`: `_target` is split into `_read_target` and
  `_write_target`. (TCW-113)
- The web client's `itemKey` gives another project's work item its full
  identifier as its route key; the reference pickers read the served
  project's view (`scope=up`) whatever the scope control shows. (TCW-113)
- `moveHint` takes the served project's id; another project's item page
  names `tcw -C tcw://<owner>.path/ work advance <full id>`. (TCW-113)
- The detail routes read their key as `show --project` reads its input: a
  full identifier of another project than `project` is refused (400
  `usage`, with the CLI's message, now built once by `tcw.scope.not_its_project`
  for the CLI and the server), and a work folder name or ticket key names
  `project`'s item. The web client sends `project` on a detail request only
  when it is the object's own project (`detailScope`). (TCW-113)

## Removed

- `tcw taxonomy list --local` and `tcw capabilities list --local`: refused
  with exit 2 and a message saying `--scope own`, the default, already lists
  only the project's own objects. (TCW-113)

## Internal

- `tests/families.py`: a family of projects (ancestors, descendants, a
  sibling, one not on this machine) for the scope tests. Tests that relied on
  the old default now pass `--scope up`, and none passes `--local`. (TCW-113)
