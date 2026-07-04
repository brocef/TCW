# Upcoming

User-facing release notes for the next version. Plain language — no jargon or
internal module names.

## Subproject-qualified slugs for descendant work items

When you keep several projects as subfolders of one repo, `tcw work list
--include-descendants` now shows each descendant project's items with a
**subproject-qualified slug** — for example `SubprojectA/2026-07-04-add-export`
— so you can tell at a glance which project an item belongs to.

That qualified slug is a real address. From the enclosing folder you can run any
work command on it directly:

```sh
tcw work show SubprojectA/2026-07-04-add-export
tcw work start SubprojectA/2026-07-04-add-export
tcw work complete SubprojectA/2026-07-04-add-export --resolution done --confirm
```

It behaves exactly as if you had changed into `SubprojectA/` first. A plain slug
(no subproject prefix) still refers to the current project only, so nothing about
your existing commands changes.

The local web app can show subprojects too: run `tcw serve --include-descendants`
to browse and edit every descendant project's board alongside the current one.
Without that flag, `tcw serve` works exactly as before.
