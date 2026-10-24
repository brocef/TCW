As a user, I run `tcw taxonomy rename <path> <new-last-part>` to rename a term
of my project, and `tcw taxonomy move <path> --into <id-path>` or `--top` to
put its folder somewhere else in the taxonomy store. Every term nested in its
folder moves with it, and every reference to a moved term in this project is
rewritten: other terms' `parent`, `relatesTo` and `vocabulary`, capabilities'
`Subject` and `Feature`, work items' `capabilities.yaml`, and `tcw://` links in
documents. It prints one `<old> -> <new>` line per identifier it changed.

It follows the same rules as
[moving a work item](tcw://C/work/move-a-work-item): the checks
come first and a refusal writes nothing; a stop says what was written and that
running the same command again finishes it; references in other projects are
left for `tcw validate` there to report. A term another project owns is
refused, and so is a new path at which my project would inherit another
project's term.
