## Upgrading

- **Everyone working on a project that keeps its work in Jira should move to
  4.1 together.** That includes CI jobs and any other automation pinned to
  an older TCW. TCW 4.1 changes what an item file holds (see "An item's file
  names its Jira ticket by key" below), and TCW 4.0.0 refuses an item file
  that TCW 4.1 wrote. Its `tcw validate` reports each one as:

  ```
  error: docs/work/SHOP-42-refund-a-payment/tcw-work-item.yaml: was written by TCW 4.1 (tcw-version 4.1.0), newer than this TCW (4.0.0); upgrade TCW
  ```

  Upgrading is the fix. Files already written by 4.0.0 are not affected:
  4.1 reads them as they are.

## Improvements

- **An item's file names its Jira ticket by key.** In a project that keeps its
  work in Jira, the `tcw-work-item.yaml` of a new item, an adopted ticket, or
  an item converted by `tcw migrate` from TCW 3 now holds the ticket's key
  alone, such as `ticket: SHOP-42`, instead of a link to the ticket on your
  Jira site. Committing those item folders to a public repository no longer
  publishes your Jira site's address. Links to tickets shown by TCW are
  still built from `work.jira.site`.

  Existing item files written by TCW 4.0.0 hold the link, stay valid, and
  need no change; TCW does not rewrite them. To change one, replace the link
  with the key by hand.
