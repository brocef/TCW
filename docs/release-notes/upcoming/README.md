# Upcoming release notes

User-facing release notes for the next version. Plain language — no jargon or
internal module names.

Add one file per change, named after its work item: `<work-item-slug>.md`. Work
done outside any item uses `<YYYY-MM-DD>-<short-description>.md`. Edit only your
own file, never another change's; that is what keeps branches from colliding.

Inside the file, give no `#` title. Put entries under `##` headings. Reuse a
heading another entry already uses (`## Improvements`, `## Fixes`) when yours
belongs with it, since identical headings merge; a heading of its own is fine
for a change that deserves one.

`python scripts/cut_version.py` combines every file here except this one into
`../v{version}.md` and deletes them.
