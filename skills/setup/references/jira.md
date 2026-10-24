# Keep a project's work in Jira

Read this when a working TCW project should keep its work items in a Jira
project instead of in files. It is a conversation with the user, not an
automatic change: TCW reads Jira's workflow and reports what it needs, and the
user changes the workflow in Jira's own settings. **TCW changes nothing in
Jira's configuration.**

Every configuration key named here is documented in the configure skill's Jira
reference; this page does not repeat them. Run `tcw validate` first: the
project must already work on files (see `project.md`).

**Switching moves no items.** Once the project says `backend: jira`, TCW reads
its items from Jira only, and items kept as files are not seen by any
`tcw work` command. Before step 2, run `tcw work list` with the user and settle
every unfinished item first: take it to completed, or discard it with
`tcw work discard <item> --reason "<why>"`, where `<item>` is the item's full
identifier (`<project>.work/<id-path>`) or its path in the work store. Anything still wanted is filed as a
Jira ticket once the switch is made.

## 1. Choose the stages and their statuses

Ask which stages the project will use. Request and qa happen on the ticket in
Jira, and the work between them happens through TCW. Each enabled stage needs
**its own Jira status**: two stages mapped to one status are refused, because
TCW could not tell from the ticket which stage it is at. The inbox is the
status where new tickets arrive.

Write the list down with the user before touching anything: stage, the Jira
status it maps to, and whether that status exists yet.

## 2. Write the configuration

In `.tcw/tcw-config.yaml`, set `work.backend: jira`, the `work.jira` block (the site,
the Jira project key, the names of the environment variables holding the
credentials, and the Jira fields TCW writes), and a `status` for each enabled
stage under `work.stages`. The credentials themselves never go in the file:
the configuration names the variables, and the user sets them in their own
shell. Run `tcw validate`; it reports a missing key or a status mapped twice
before anything contacts Jira.

## 3. Check the workflow against Jira

```sh
tcw validate --remote
```

It reads Jira and changes nothing. Its standard output is the findings, one per
line; what passed is narrated on standard error. It reports statuses that do
not exist, moves between stages that have no transition, transition screens
that ask for a field other than the comment, and fields TCW writes that are
missing from the create or edit screens.

## 4. Work through each finding with the user

For each one, say what TCW needs and why, then help the user change the
workflow in Jira. Three kinds of finding need their own explanation:

- **A move that could not be checked.** The check reads existing tickets to
  learn the workflow, so on a new Jira project with no tickets, or without
  permission to read the workflow, some moves cannot be checked. That is a
  finding, not a pass. Offer to create one sample ticket in each status, with
  the user's agreement, so the next run can check those moves; name every
  ticket you created so the user can delete them afterwards.
- **More than one transition into a stage's status.** `tcw work advance`
  prefers the transition whose screen asks for nothing but a comment. If more
  than one such transition remains, every such move is refused (exit 3),
  listing them. Help the user remove the extra transitions, or restrict them
  so only one applies.
- **A transition screen that requires a field.** TCW never fills one in.
  Suggest setting the value in a workflow post function instead, so the
  screen asks for nothing TCW cannot give.

## 5. Run it again

Repeat `tcw validate --remote` until it prints no findings. Then try one item
end to end with the user: adopt a ticket from the inbox with
`tcw work tickets adopt <KEY>`, which prints the new item's full identifier,
and move it with `tcw work advance <item>`, giving that full identifier or the
ticket's key.
