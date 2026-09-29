## Fixed

- `tcw work complete`'s merge-back hint reads staged paths with
  `git diff --cached --name-only -z` from the repository top (`_staged_paths`),
  so a non-ASCII path (quoted under `core.quotePath`) or `diff.relative=true`
  no longer hides the "tracker.yaml holds a record" hint (now
  `_merge_back_hint`). `FsWorkStore`'s `git ls-tree` readers
  (`_nested_tree_path`, `_nested_in_commit`) and `git ls-files` reader
  (`_tracked_source`) take `-z` for the same reason. All four decode with
  `surrogateescape` (`_GIT_PATHS`), so a path that is not UTF-8 cannot crash
  them. `intake.ever_bound` is removed; `binding_record` replaces it.
- `JiraClient.create_issue` returns the decoded answer as it came
  (`_payload`), and `create.py` reads `key`/`id` only as non-empty strings, so
  an answer of any other shape — `[]`, `"ok"`, `{"key": null}` — gets the
  "It may exist; look for a ticket titled…" warning rather than "unexpected
  shape" or a bogus key `"None"`.
- `_check_issue` also refuses, as "unexpected shape", an issue whose `key`,
  `fields.summary`, `status.name`, `statusCategory.key`,
  `assignee.accountId` or `assignee.displayName` is present and not a string;
  `{"status": {"name": 5}}` crashed `tracker show` in `assess`.
- The filing hook no longer reports "creating it did not succeed" when the
  ticket was made and only the binding failed: `_create_one` adds a reason
  when `_tracker_link` fails.
- Strict `drop` of an item whose `tracker.yaml` cannot be read says so, in the
  CLI and the web app (`intake.binding_record`, `intake.drop_refusal`), rather
  than "is, or was, bound to a ticket".
