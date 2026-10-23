As a user, I run `tcw work edit <slug> --blocked-by <slug>` to record that another work item blocks mine, `--unblocked-by <slug>` to remove that, and `--blocks <slug>` to record that my item blocks another — including an item in another project, under the conditions of [delegation](tcw://C/work/delegate-a-work-item-to-another-project). Each flag repeats. A blocker is always a work item, named by its folder or its full slug, and is kept in the item's `item.yaml`; an item cannot block itself. `tcw work show` lists what an item is blocked by and, worked out from the other items, what it blocks. `tcw validate` warns about a blocker that names no item, without failing.

Since TCW 4.0 an object is named by its full identifier,
`<project>.<namespace>/<id-path>`: commands print it, and accept it, its
`tcw://` address, or the id-path alone for an object of the project I am in.
A work item can also be named by its tracker key, bare or as
`<project>.work/<KEY>`.
