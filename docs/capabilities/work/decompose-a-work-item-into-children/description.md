As a user, I run `tcw work new "<title>" --parent <item>` to create a child work item under an existing item, so a large item can be broken into smaller ones that are each planned and worked on their own. An item with children is what an epic is; there is no separate epic type. `tcw work list --parent <item>` lists an item's children, and `tcw work show` names them in its record. A child moves through the stages on its own: its parent's stage does not hold it back, and it does not move its parent. An item cannot be its own parent, and a parent that would make a cycle is refused.

I name the parent by its full identifier (`<project>.work/<folder>`), its
`tcw://` address, its folder name alone for an item of the project I am in,
or, when the project keeps its items in Jira, its ticket key, bare or as
`<project>.work/<KEY>`. Whatever form I give, the child's `tcw-work-item.yaml` keeps
the parent's full identifier, and `tcw work show` prints the parent and the
children by full identifier.

A child made with `--parent` is made inside its parent's folder when the parent is an item of this project. `--flat`, or the web app's matching option, keeps it at the top of the work store instead, and `--flat` without `--parent` is a usage error (exit 2). The folder does not set the parent; `--parent` does.

A part that belongs to another project is made from that project, naming the
parent by its full identifier: usually
`tcw -C tcw://<id>.path/ work new "<title>" --parent <epic>`, which makes it
at the top of that project's store, since the parent's folder is not there,
and says so. When the
part's project keeps its items in Jira and the parent is not a ticket on the
same Jira site, the parent is recorded in the part's folder, and Jira itself
does not show it.
