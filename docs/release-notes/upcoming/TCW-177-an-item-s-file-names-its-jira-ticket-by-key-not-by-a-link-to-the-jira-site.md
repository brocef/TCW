## Improvements

- **An item's file names its Jira ticket by key.** In a project that keeps its
  work in Jira, a new item's `tcw-work-item.yaml` now holds the ticket's key
  alone, such as `ticket: SHOP-42`, instead of a link to the ticket on your
  Jira site. Committing item folders to a public repository no longer
  publishes your Jira site's address. Links to tickets shown by TCW are still
  built from `work.jira.site`. Files written by TCW 4.0.0, which hold the
  link, stay valid and need no change; to change one, replace the link with
  the key. A file holding the key is refused by TCW 4.0.0, so everyone
  working on the project should upgrade together.
