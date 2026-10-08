As a user, I add a dated remark to a work item with `echo "text" | tcw work comment <slug>`. The text comes from stdin, and an empty comment is refused (exit 2). The command prints nothing on stdout.

In a filesystem project each comment is its own file under the item's `comments/` folder, named by the time it was written (`comments/20261002T101500Z.md`), so two comments never overwrite each other and the folder reads in order. TCW never commits them; they are files in my working tree like any other.

TCW writes comments too: a forced move (`tcw://C/work/advance-a-work-item`) and a discard (`tcw://C/work/discard-a-work-item`) leave their reason the same way, so the item's comments are the record of why it moved.
