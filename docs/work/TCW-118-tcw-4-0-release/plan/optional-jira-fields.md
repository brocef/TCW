# Jira mode without the TCW Project and TCW Item fields

Added to TCW-118 during the release evaluation. The user decided that the two
fields become optional, and accepted the weaker guarantees listed below; the
details are decided by the dispatching session.

## Why

A team whose Jira site does not allow new custom fields cannot use Jira mode,
because `work.jira.fields.project` and `work.jira.fields.item` are required and
every write sets them. Every Jira-mode item already has a folder with a state
file, named with its ticket's key (`folder_key`, `link_exists`), so the
repository alone can say which tickets are its items.

## The rule

- `work.jira.fields` is optional, and so are its `project` and `item` keys,
  but `project` and `item` are given together or not at all: one without the
  other is a configuration problem that names the missing one. `effort` and
  `complexity` keep their current meaning, with or without the other two.
- **With both fields configured**, nothing changes from today.
- **With neither**, the item folders are the record of which tickets are this
  project's items, and TCW never reads or writes a TCW Project or TCW Item
  value. Call this "without the TCW fields" in docs and messages.

## Each operation without the TCW fields

1. **Listing items** (`tcw work list`, and everything built on the backend's
   `list`). Collect the keys of this project's item folders, then search Jira
   with `key IN (...)` in chunks of `jql.MAX_KEYS`, with the same status,
   parent, assignee and label clauses `item_query` adds today, and keep the
   order the field search gives (`created ASC`) across chunks. No project
   filter after the search is needed: the keys come from this project's
   folders. A folder whose ticket is not returned is simply not listed;
   `tcw validate --remote` is what reports a ticket that is gone.
2. **The inbox** (`tcw work tickets list`). Tickets at the inbox status, or
   matched by `inbox-query`, with no folder named for their key in this
   project. Tickets at the request status are **not** offered without the
   fields, unlike today: with the fields, an empty TCW Item shows that no
   project has adopted the ticket, but without them such a ticket is most
   likely another repository's item.
3. **Adopting** (`tcw work tickets adopt`). The "already an item" check is the
   folder check alone. A ticket at the request status with no folder here is
   refused, saying that it may be an item of another repository sharing this
   Jira project and that, if it is not, moving it back to the inbox status
   lets it be adopted. An adoption interrupted part way must still be
   resumable from this checkout: if the field-setting step was what marked
   the progress, order the steps so the folder (without its state file, as
   today's resume rule reads it) exists before the ticket moves.
4. **Creating** (`tcw work new`). Skip step 4 (setting TCW Item) and the
   TCW Project value in the create request (`mapping.create_fields`).
5. **Moving and renaming** (`tcw work move`, `rename`, and the
   `_set_items` / `_set_item` paths). Skip every TCW Item rewrite and the
   reads that check the old value; the folder move is the whole change.
6. **Reading one item** (`show`, the request, comments) already goes through
   the folder's key and needs no change; check that nothing on that path
   reads `field_ids["item"]` or `["project"]`.
7. **`tcw validate --remote`**. Do not look for the two fields on the create
   and edit screens and do not compare ticket values with folders; keep every
   status, transition and screen check for the fields still configured
   (effort, complexity, priority). Report a folder whose ticket does not
   exist, if that is not already reported.
8. **Metadata** (`metadata().field_ids`). It must not require or resolve the
   two field names when they are not configured; code that indexes
   `field_ids["item"]` must not be reached without the fields.
9. **`tcw migrate`**. A 3.x configuration always has the fields, and migrate
   keeps them; the 3.x TCW Item conversion is unchanged. Nothing new is
   needed, but migrate must not break on a project that has none.
10. **Setup.** Whatever `tcw init`, `tcw work jira` setup help or the
    stage prompts say about creating the two fields must say they are
    optional and what is lost without them.

## What is lost without the fields (to be written in docs/guide/jira.md)

- An adoption or a new item is known to other copies of the repository only
  once its folder reaches them through git. Two people can adopt the same
  ticket on different branches; `tcw validate` reports the two folders when
  the branches meet, but nothing prevents it.
- Nothing in Jira says which repository or folder holds a ticket's item.
- With several projects sharing one Jira project, a ticket adopted by one is
  invisible to the others' inboxes only once it leaves the inbox status,
  which adoption does at once.
- Turning the fields on later: configuring them on a project that ran
  without them leaves existing tickets with empty values, so `list` would
  miss them. Either `tcw validate --remote` reports this and says how to fill
  them, or TCW gives a way to fill them; the implementer picks the smaller
  of the two and says which.

## Docs and checks

- `docs/guide/jira.md`: setup says the fields are optional; a section on
  running without them, with the losses above; the "Limits" section updated.
- `docs/use-cases.md`: the shared-Jira-project case.
- `docs/migration-guide-3.X-to-4.0.0.md` only if it says the fields are
  required.
- The changelog entry `docs/changelogs/upcoming/TCW-118-tcw-4-0-release.md`
  under `## Added` or `## Changed`, and the release notes entry if TCW-118
  has one.
- `tcw/reference_fields.py` describes TCW Item; say it is optional.
- Tests against the Jira fake (`tests/work/jira/`) for every numbered
  operation above without the fields, and a configuration test for one field
  given alone. The fake's JQL parser must accept the new key search with the
  extra clauses (`tests/work/jira/fake_jql.py`).
