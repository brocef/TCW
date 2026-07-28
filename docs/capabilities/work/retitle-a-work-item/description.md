As a user, I run `tcw work edit <slug> --title "<new title>"` to change a work
item's title after creation. The item's slug is its stable ID and is not
recomputed, so a retitle never breaks an existing reference to the item. The body
of `initial-request.md` is left alone — its heading is prose I edit myself.
