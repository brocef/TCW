# Upcoming

User-facing release notes for the next version. Plain language — no jargon or
internal module names.

## Break big work items into smaller ones

You can now split a large work item into smaller **child items** instead of
letting any one item grow unwieldy:

```
tcw work new "Sub-task" --parent <parent-slug>
```

The child is filed inside its parent, and `tcw work list` shows children
indented under the item they belong to. A child moves through the workflow
alongside its parent: starting or completing the parent brings its children
along, and starting a child on its own makes it a top-level item of its own.
