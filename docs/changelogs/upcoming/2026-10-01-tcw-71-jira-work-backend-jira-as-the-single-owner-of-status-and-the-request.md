## Added

- The Jira work backend for TCW 3.0 (TCW-71), in `tcw/work/jira/`.
  - `backend.py`: `JiraBackend`, TCW-69's `WorkBackend` over Jira tickets,
    with folders named `<KEY>-<words>` holding only `item.yaml` with the
    ticket link. Field ids are resolved by display name from the configured
    issue type's create metadata. `set_stage` makes one transition chosen by
    a fixed rule (the lone candidate, else the one whose screen asks for
    nothing but a comment, else a refusal) and decides what happened after a
    400 or a dropped connection by reading the status back. Reads fall back
    to direct reads for any key a search did not return. Offline checks
    (`jira_store_problems`, `link_exists`) never contact Jira.
  - `config.py`: `JiraConfig` and the connected-project `jira` block.
  - `mapping.py`: text to Atlassian Document Format and back as a pair that
    round-trips, and the field mapping in both directions.
  - `jql.py`: the only place JQL is built; TCW Project is matched exactly
    after a search, never with `~`.
  - `tickets.py`: the Jira inbox, adoption, and delegation into a Jira-mode
    project.
  - `remote.py`: the checks behind `tcw validate --remote`.
- Commands: `tcw work tickets list [--json]`, `tcw work tickets adopt KEY`,
  `tcw validate --remote`.

## Changed

- `tcw/work/jira/client.py` (moved from 2.x by TCW-70): `search` returns
  every page, takes a field list and an optional limit; `create_issue` takes
  any fields; `apply_transition` takes an optional comment; `comments(key,
  limit)` replaces `recent_comments`; new `edit_issue`, `add_link`,
  `delete_link`, `user`, `assignable_users`, `project`, `project_statuses`,
  `create_metadata`, `edit_metadata`, `link_types`, `workflows`. `assign` and
  `description` are gone. Error messages name `work.jira`.
- `open_backend` returns a `JiraBackend` for `work.backend: jira`;
  `open.delegate` delegates into Jira-mode projects; `open.reference_resolver`
  answers references into other projects for both `validate` paths.
- `advance.run_post` is a public function, so adoption runs the request
  stage's `post` hooks.
- `cli.resolve_item` accepts a ticket key in Jira mode.
- `TcwError` has an optional `name`, printed by `new` when set.
- `tcw validate`: Jira-mode projects get folder checks offline, and a
  filesystem reference into a Jira-mode project is answered from its folders.

## Internal

- `tests/work/jira/fake.py`: a fake Jira with projects, issue types, statuses,
  global transitions, screens and switches for each failure the backend
  handles; `fake_jql.py` evaluates exactly the query shapes TCW builds.
- `tests/work/jira/scenario.py`: Design 15.4's ten-step scenario, run against
  the fake in CI and by hand against a real Jira project.
- The shared backend contract runs against `JiraBackend` with no skips.
- Guards: no module under `tcw/` names the 2.x tracker, and no module in
  `tcw/work/jira/` starts a process.
