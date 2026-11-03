## Changed

- A Jira-mode item's state file holds `ticket: <KEY>` instead of
  `ticket: <work.jira.site>/browse/<KEY>`: `JiraBackend._item_file`, used by
  `tcw work new` and `tcw work tickets adopt`, writes the key alone, so an
  item file no longer carries the Jira site's address. (TCW-177)
- `tcw validate` (`_item_file_problems` in `tcw/work/jira/backend.py`)
  accepts a `ticket` value with no `/` when it equals the folder's key, and
  reports "ticket '<v>' is not the folder's key, <KEY>" otherwise, the value
  quoted so an empty or multi-line one reads on one line; a value that is
  not a string is reported the same way. A value
  with a `/`, the link TCW 4.0.0 wrote, is checked as before: on
  `work.jira.site`, naming the folder's key. (TCW-177)
- The message for a Jira item folder with no state file reads "is missing;
  it holds the ticket's key". (TCW-177)

- `tcw migrate` writes a 3.x Jira item's `ticket: <work.jira.site>/browse/<KEY>`
  as `ticket: <KEY>` when `<KEY>` is the folder's key (`_ticket_key` in
  `tcw/migrate/stores.py`, the site read by `_jira_site` in
  `tcw/migrate/plan.py` from the project's own layers); any other value is
  carried over as before. A 3.x file left beside a 4.0 file holding either
  form is an equal pair, not B11 (`_both`'s `also`). (TCW-177)
- The item file format changes, so this release is 4.1.0, not a patch:
  TCW 4.0.0 refuses a file stamped `tcw-version: 4.1.0` as written by a newer
  TCW. (TCW-177)

## Internal

- This repository's item files under `docs/work/` name their tickets by key,
  and are stamped `tcw-version: 4.1.0` as part of the release commit.
  (TCW-177)
