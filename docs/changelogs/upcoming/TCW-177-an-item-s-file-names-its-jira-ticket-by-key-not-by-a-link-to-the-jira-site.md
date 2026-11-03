## Changed

- A Jira-mode item's state file holds `ticket: <KEY>` instead of
  `ticket: <work.jira.site>/browse/<KEY>`: `JiraBackend._item_file`, used by
  `tcw work new` and `tcw work tickets adopt`, writes the key alone, so an
  item file no longer carries the Jira site's address. (TCW-177)
- `tcw validate` (`_item_file_problems` in `tcw/work/jira/backend.py`)
  accepts a `ticket` value with no `/` when it equals the folder's key, and
  reports "ticket '<v>' names <v>, but the folder's key is <KEY>" otherwise;
  a value that is not a string is reported as not the folder's key. A value
  with a `/`, the link TCW 4.0.0 wrote, is checked as before: on
  `work.jira.site`, naming the folder's key. (TCW-177)
- The message for a Jira item folder with no state file reads "is missing;
  it holds the ticket's key". (TCW-177)

## Internal

- This repository's item files under `docs/work/` name their tickets by key.
  (TCW-177)
