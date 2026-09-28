# Upcoming changelog entries

Developer changelog for the next version. Technical and precise; grouped by
category.

Add one file per change, named after its work item: `<work-item-slug>.md`. Work
done outside any item uses `<YYYY-MM-DD>-<short-description>.md`. Edit only your
own file, never another change's; that is what keeps branches from colliding.

Inside the file, give no `#` title. Put entries under `##` headings, using these
names so they merge: `## Added`, `## Changed`, `## Fixed`, `## Removed`,
`## Internal`. A `###` heading stays with the `##` section above it.
Never start a line with `## ` inside a code block: the cut would read it as a
heading.

`python scripts/cut_version.py` combines every file here except this one into
`../v{version}.md`, one heading of each kind, and deletes them.
