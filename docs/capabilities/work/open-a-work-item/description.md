As a user, I run `tcw work new "<title>"` to create a work item. It prints the item's full slug, `<project-id>/<date>-<title-words>`, on stdout and nothing else. The item is a folder in the work store named by today's date and the title's words, and it never moves: its stage is a value in its `item.yaml`, not the folder it sits in. A title that reduces to nothing becomes `untitled`, and a very long one is shortened, so no title I can type produces an unusable name. A second item with the same title on the same day is refused (exit 3), naming the folder that already has it, rather than given a `-2` suffix.

Text I pipe in is the item's request: it is written to `request/request.md`, the document the `request` stage refines. With nothing piped, the item has no request yet. A new item starts at the `request` stage with `medium` priority; `--stage inbox` files it in the inbox instead (`tcw://C/work/manage-the-work-inbox`).

I can set its other properties at the same time — `--priority`, `--effort`, `--complexity`, `--tag`, `--assignee`, `--parent` and `--blocked-by` — each checked as `tcw work edit` checks it. `--project <id>` files the item in another project instead (`tcw://C/work/delegate-a-work-item-to-another-project`).

TCW never commits the new folder; it is mine to commit.
