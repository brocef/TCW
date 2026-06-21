# Upcoming

User-facing release notes for the next version. Plain language — no jargon or
internal module names.

## Work item priority

You can now give a work item a priority. Pass `--priority N` when you create or
edit it (any whole number — higher means more important):

```
tcw work new "Urgent fix" --priority 5
tcw work edit some-slug --priority 9
```

The board (`tcw work list`) shows prioritized items first, highest number at the
top. Items without a priority keep their usual order, below the prioritized ones.
Priority never lets an item jump ahead of something that's blocking it.

