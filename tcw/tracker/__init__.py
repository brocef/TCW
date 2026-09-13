"""External tracker coordination.

Deliberately **not** under `tcw/store/`. A tracker is not a store: putting these
operations behind `WorkStore` would make every adapter owe a tracker
implementation, which inverts what a store is for. A coordinator composes a
tracker client with the configured store, and no tracker call goes inside
`FsWorkStore`.

`jira.py` is the intended home for *all* Jira HTTP work in this package, including
anything a future `JiraWorkStore` would need, so that a second Jira client never
gets written.
"""
