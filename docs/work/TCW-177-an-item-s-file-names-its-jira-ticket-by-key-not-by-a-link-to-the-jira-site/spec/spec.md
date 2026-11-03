# Spec — An item's file names its Jira ticket by key, not by a link to the Jira site

## Capability changes

- **changed** `tcw.capabilities/work/keep-work-items-in-jira`: an item
  folder's `tcw-work-item.yaml` holds the ticket's key (`ticket: SHOP-42`),
  not a link to the ticket on the Jira site. A file written by TCW 4.0.0,
  holding the link, is still accepted.

No capability is added or removed. No taxonomy term changes.

## Problem

In a project whose work is kept in Jira, each item folder's state file,
`tcw-work-item.yaml`, holds a full link to the ticket on the Jira site:

- The only writer is `JiraBackend._item_file`
  (`tcw/work/jira/backend.py:942`):
  `text = f"{version_line()}ticket: {self.jira.site}/browse/{key}\n"`. It is
  called by `create` (`backend.py:1061`, for `tcw work new`) and by
  `tcw work tickets adopt` (`tcw/work/jira/tickets.py:196`).
- The only reader of the value is `tcw validate`'s `_item_file_problems`
  (`backend.py:198-232`), which requires the value to start with
  `<work.jira.site>/browse/` (`:224-228`) and the rest to equal the folder's
  key (`:229-231`). A bare key is refused today as "is not on <site>".

The site's address is often private. Committing item folders to a public
repository then publishes the name of the organisation's Jira site in every
item file. This repository is public, and all 117 of its item files under
`docs/work/` carry its site's address.

The link carries nothing the project does not already know: the folder's
name starts with the key (`folder_key`), and the site is configured in
`work.jira.site`. Where TCW shows a person a link, it already builds it from
those two (`tcw/work/jira/tickets.py:95` for `tcw work tickets list` and the
web app's ticket list, `:280` for `ticket_link`, the web app's "Open in Jira").

### Other readers and writers, swept repository-wide

A search of `tcw/` and `web/` for `"ticket"`, `ticket:`, `/browse/` and for
callers of `_item_file` and of the state file name finds:

| Where | What it does with the `ticket` line | Action |
| ----- | ----------------------------------- | ------ |
| `tcw/work/jira/backend.py:942` `_item_file` | writes it | writes the key |
| `tcw/work/jira/backend.py:198-232` `_item_file_problems` | checks it | accepts the key and the 4.0.0 link |
| `tcw/work/jira/backend.py:143`, `:207` | the "missing state file" message says the file "holds the ticket's link" | says "the ticket's key" |
| `tcw/work/jira/backend.py:945-981` `_record` | rewrites `parent`/`blocked-by`, keeping every other key's value as read | none: it keeps whichever form the file holds |
| `tcw/work/jira/tickets.py:95`, `:280` | build a link from `work.jira.site` and the key, never from the file | none |
| `tcw/work/jira/remote.py` | `tcw validate --remote` compares each folder's key with its ticket; never reads the `ticket` line | none |
| `tcw/serve/server.py:86` | an error body's `ticket` is a refused ticket's key, unrelated to the file | none |
| `web/client/src` | reads `url` from the server's ticket answers, built by `tickets.py` | none |
| `tcw/migrate/` (`stores.py:_plan_object`) | converts a 3.x `item.yaml` into `tcw-work-item.yaml` by editing the parsed 3.x file; it carries the 3.x `ticket:` line over unchanged and neither writes nor checks it (no match for `ticket` or `browse` in `tcw/migrate/stores.py`) | none; see Non-goals |

## Goals

1. `tcw work new` and `tcw work tickets adopt` write `ticket: <KEY>`, the key
   alone, in a new item's `tcw-work-item.yaml`.
2. `tcw validate` accepts `ticket: <KEY>` when it equals the folder's key, and
   refuses one that names another key.
3. `tcw validate` still accepts a file TCW 4.0.0 wrote, `ticket:
   <site>/browse/<KEY>`, checked exactly as today: on `work.jira.site`, naming
   the folder's key. Existing projects stay valid with no change.
4. This repository's own item files are rewritten to the key form.
5. The Jira guide, the validation guide, the capability description, the
   release notes and the changelog say so.

## Non-goals

- **Converting existing files.** No command rewrites a 4.0.0 file's link to
  the key; a project that wants its files changed edits them (a one-line
  substitution). This repository does so by a script in its own commit.
- **`tcw migrate`.** Its conversion of a 3.x project carries the 3.x
  `ticket:` line over unchanged (see the table above); the result is the
  4.0.0 link form, which stays valid. Changing what the 3.x to 4.0 migration
  writes is not asked for and would change a documented conversion.
- **Rewriting git history.** Commits already pushed keep the old links; only
  what is committed from now on changes (the request).
- **Other private names in the repository** (the site address in this
  repository's `.tcw/tcw-config.yaml`, in test fixtures and in the 3.0
  migration log). They are not item files; the request names only the item
  files.
- **Old TCW reading new files.** TCW 4.0.0 refuses `ticket: <KEY>` as "is not
  on <site>"; that is accepted (`docs/use-cases.md` S-9: old code reading
  files a newer version wrote is not a constraint).

## Design

Decided by the maintainer's request ("Just refer to the TCW ticket slug, not
the full link") and its follow-up decisions:

1. **The writer.** `_item_file` writes `ticket: <KEY>`. Nothing else in the
   file changes: `tcw-version` first, then `ticket`, then any recorded
   `parent` and `blocked-by`.
2. **The check.** `_item_file_problems` reads the `ticket` value `v` of a
   file that has passed the version, keys, `id` and recorded-reference checks
   (unchanged), and applies these rules in order:
   1. `v` is not a string: an error, "ticket <v> is not the folder's key,
      <KEY>".
   2. `v` contains no `/` (the key form): it must equal the folder's key;
      otherwise an error, "ticket '<v>' names <v>, but the folder's key is
      <KEY>".
   3. `v` contains a `/` (the 4.0.0 link form): checked as today. It must start
      with `<work.jira.site>/browse/`, or an error, "ticket '<v>' is not on
      <site> (work.jira.site)"; the rest must equal the folder's key, or an
      error, "ticket '<v>' names <rest>, but the folder's key is <KEY>".
3. **The missing-file message** says the file "holds the ticket's key".
4. **This repository's item files** are rewritten by a short script that
   replaces each `ticket: <site>/browse/<KEY>` line with `ticket: <KEY>`,
   checking that each key equals its folder's key prefix, in a commit of its
   own.

## Abstraction litmus test

No new operation, and no backend operation changes. The `ticket` line is part
of the Jira backend's own item folder state file, a private detail of the
Jira backend (`tcw/work/jira/backend.py`); its form changes, and the
interface (`tcw/work/backend.py`) does not. The key is a name the Jira
backend owns and already reads from the folder's name.

## Use cases

- **UC-1 A single project**: unaffected unless it keeps its work in Jira; no
  configuration, output or time added.
- **UC-5 One Jira project shared by several TCW projects**: each item file
  holds its ticket's key, which is unique across the Jira project; the site
  still comes from each project's own `work.jira` (its own or inherited), so
  a link built for display is the same as before.
- **UC-7 A library published to the public**, and any public repository
  keeping its work in Jira: the item files no longer publish the Jira site's
  address. This is the case the request is for.
- **S-3 Which backend keeps the work**: Jira only. The filesystem backend's
  state file has no `ticket` line.
- **S-9 Upgrades**: new code reads both forms (Design 2.3 keeps the 4.0.0
  check). TCW 4.0.0 reading a new file refuses it, which S-9 says is not a
  constraint; a project upgrades everyone working on it.
- **S-11 Version control**: TCW changes no git state; this repository's
  rewrite is a commit made by hand.

The checklist: 1 — it locates nothing new; 2 — it writes only the item's own
state file, as before; 3 — no cross-project read; 4 — Jira only, litmus test
above; 5 — no person assumed; 6 — the CLI carries all of it, so every harness
gets it; 7 — the writer writes one file in one call, as before; 8 — no cost
to UC-1; 9 — a file format changes, read by new code in both forms (S-9);
10 — the tests run in a Jira-mode project with the fake Jira site.

## Acceptance criteria

1. **The writer.** A Jira-mode `tcw work new` writes
   `tcw-version: <version>\nticket: TCW-1\n` and nothing else
   (`test_a_new_item` in `tests/work/jira/test_jira_write.py`). Adoption
   writes the key too (an adopt test asserting the file's `ticket` line).
2. **The key form is accepted.** A folder `TCW-1-x` whose file holds
   `ticket: TCW-1` passes `tcw validate` with exit 0.
3. **A wrong key is refused.** A folder `TCW-1-x` whose file holds
   `ticket: TCW-2` is an error naming TCW-2 and the folder's key TCW-1; exit 1.
4. **The 4.0.0 link form is still accepted.** `ticket:
   <site>/browse/TCW-1` in folder `TCW-1-x` passes with exit 0.
5. **The 4.0.0 link form is still checked.** A link on another site is an
   error containing "is not on"; a link naming TCW-2 in folder `TCW-1-x` is
   an error containing "names TCW-2"; both exit 1.
6. **A ticket that is not a string** (for example `ticket: 7`) is an error,
   exit 1.
7. **The missing-file message** reads "is missing; it holds the ticket's
   key".
8. Criteria 2, 3 and 6 fail before the change (red) and pass after (green);
   1 and 7 fail before because the old form is asserted elsewhere and pass
   after.
9. **This repository.** Every `docs/work/*/tcw-work-item.yaml` holds `ticket:
   <KEY>` with the key equal to its folder's key prefix; no item file holds
   `/browse/`; `tcw validate` and `tcw validate --remote`, run with this
   checkout's `tcw`, report 0 errors.
10. **Documentation.** `docs/guide/jira.md` describes the file as holding the
    ticket's key and says a 4.0.0 file with the link stays valid;
    `docs/guide/linking-and-validation.md` gives the new missing-file message;
    the `keep-work-items-in-jira` capability description says "the ticket's
    key"; `docs/release-notes/upcoming/` and `docs/changelogs/upcoming/` each
    hold an entry file named by this item's folder. No document added by this
    change names a real Jira site.
11. The full suite passes, run as CI runs it (bare `pytest` from the root).

### Coverage

Design rule 2's sub-rules against the criteria:

| #   | 2.1 not a string | 2.2 key form | 2.3 link form | 1 writer | 3 message |
| --- | ---------------- | ------------ | ------------- | -------- | --------- |
| 1   | n/a (writer only, `backend.py:942`) | n/a | n/a | `test_a_new_item`; adopt test | n/a |
| 2   | n/a | key accepted test | n/a | n/a | n/a |
| 3   | n/a | wrong key test | n/a | n/a | n/a |
| 4   | n/a | n/a | `test_a_clean_tree_is_clean` (link fixture) | n/a | n/a |
| 5   | n/a | n/a | `test_each_error` "is not on", "names TCW-2" | n/a | n/a |
| 6   | not-a-string test | n/a | n/a | n/a | n/a |
| 7   | n/a | n/a | n/a | n/a | `test_a_key_named_folder_with_no_state_file_is_no_item` |

## Risks

- **Moving to another Jira site.** A key-form file no longer records the site,
  so a project whose `work.jira.site` changes keeps valid files; a 4.0.0 file
  then fails "is not on". This is no worse than today, and the key form is
  the remedy.
- **A key containing `/`.** Jira keys are letters, digits and one hyphen
  (`folder_key`), so a value containing `/` is always the link form.
- **Old TCW.** A teammate still on 4.0.0 sees new files refused by
  `tcw validate`. Ships in 4.0.1; S-9 accepts this.

## Notes

QA plan posted as a comment on the ticket.
