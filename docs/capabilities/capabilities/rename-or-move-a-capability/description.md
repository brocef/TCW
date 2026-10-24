As a user, I run `tcw capabilities rename <path> <new-last-part>` to rename a
capability of my project, and `tcw capabilities move <path> --into <id-path>`
or `--top` to put its folder somewhere else. Every capability nested in its
folder moves with it, and every reference to a moved capability in this
project is rewritten: other capabilities' `Superseded by`, `Blocked by`,
`Roles` and `When`, work items' `capabilities.yaml`, and `tcw://` links in
documents. It prints one `<old> -> <new>` line per identifier it changed.

It follows the same rules as
[moving a work item](tcw://C/work/move-a-work-item). An override
is not moved or renamed away from the path of the capability it overrides,
and a move to a path where my project would inherit another project's
capability is refused, since it would make an override. A move that would
leave a reference somewhere its field does not allow, such as a `Roles` value
outside `roles/`, is refused before anything is written.
