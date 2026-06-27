# tcw work new prints content.md path for quick editing

## Product changes

## Technical changes

## Meta changes

## Product changes
`tcw work new` should also print the path to the new item's `content.md` so agents/humans can open it immediately for editing. Extends the existing **work#open-a-work-item** capability (stays Supported).

## Technical changes
Add `FsWorkStore.body_path(slug)` (keeps the `content.md` filename in the FS adapter), call it from `_new` in `tcw/work/cli.py`, print to stderr alongside the existing next-step hint.

## Meta changes
None.
