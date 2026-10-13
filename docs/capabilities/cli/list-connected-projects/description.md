As a user, I run `tcw projects list` to see which projects the current project
is connected to. It prints one project ID per line: this project first, then its
parent, its children, and the upstream projects it may read — including an
upstream declared by one of its ancestors — each once. Projects are named by ID,
never by folder, because the ID is a project's identity and a folder is only
where it happens to sit on one machine.

Only *declared* projects appear. TCW reads the `projects:` section of
`tcw-config.yaml` rather than scanning the disk, so a git repository sitting next
to or inside this one is not connected until it is declared — being nearby is not
a relationship. A declared project that is not on this machine is still listed,
so a project with children never reads as one without any.

`tcw projects list --json` prints `{"schema": 1, "projects": [...]}`, with each
project's ID, its relation to this one (`current`, `parent`, `child` or
`upstream`), whether it is present on this machine, and its folder when it is.

That makes it the command to run first when something in another project is not
behaving: the projects listed here as present are the ones
[Delegate a work item to another project](tcw://C/work/delegate-a-work-item-to-another-project)
and qualified `tcw://` links can reach. If a project I expected is missing, the
problem is its declaration, not the command I was trying to run. Upstream
projects are read here and never written — see
[Read from an upstream project](tcw://C/cli/read-from-an-upstream-project).
