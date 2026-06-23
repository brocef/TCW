# Upcoming

User-facing release notes for the next version. Plain language — no jargon or
internal module names.

## Multiple projects in one git repo

A single git repo can now hold several TCW projects as subfolders. Run
`tcw init` inside each project folder to mark it as its own node — each gets its
own `docs/` tree and its own `tcw` board:

```sh
cd project-a && tcw init
cd ../project-b && tcw init
```

From inside `project-b`, all `tcw` commands operate on `project-b`'s data, not
the repo root's.

Sibling projects can share vocabulary: add an `extends` block in project-b's
taxonomy config pointing at the sibling, and project-b's taxonomy commands
inherit project-a's terms automatically.

> Cross-node operations (`tcw work nodes`, epics, delegate, escalate) still
> discover peers by git-repo boundary — subfolder nodes within the same repo
> will appear as cross-node peers in a later update.
