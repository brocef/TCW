As a user, I run `tcw work new "<title>" --parent <slug>` to create a child work item under an existing item, so a large item can be broken into smaller ones that are each planned and worked on their own. An item with children is what an epic is; there is no separate epic type. `tcw work list --parent <slug>` lists an item's children, and `tcw work show` names them in its record. A child moves through the stages on its own: its parent's stage does not hold it back, and it does not move its parent. An item cannot be its own parent, and a parent that would make a cycle is refused.

Since TCW 4.0 an object is named by its full identifier,
`<project>.<namespace>/<id-path>`: commands print it, and accept it, its
`tcw://` address, or the id-path alone for an object of the project I am in.
A work item can also be named by its tracker key, bare or as
`<project>.work/<KEY>`.
