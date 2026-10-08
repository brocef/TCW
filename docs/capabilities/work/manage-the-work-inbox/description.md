As a user, I keep raw requests in the inbox: an item at the `inbox` stage, which
says nothing has been decided about it yet. `tcw work new "<title>" --stage inbox`
files one, with any text I pipe in as its request, and work another project
delegates to mine lands there too
([Delegate a work item to another project](tcw://C/work/delegate-a-work-item-to-another-project)).

`tcw work list --stage inbox` lists them. A plain `tcw work list` shows them
beside every other unfinished item.

Taking a request on is moving it to the next stage with
`tcw work advance <slug>`; turning it down is
`tcw work discard <slug> --reason "<why>"`. Either way the item keeps its
folder and its request, so nothing has to be copied from one place to another.
