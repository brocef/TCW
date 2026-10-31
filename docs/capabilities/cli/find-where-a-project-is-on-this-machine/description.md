As a user, I run `tcw project path <id>` to learn which folder on this machine
holds project `<id>`. It prints that folder's absolute path and nothing else,
so I can use it in a script: `cd "$(tcw project path core)"`. With no ID it
prints the current project's own folder. It finds the folder the same way every
other command run here does (see [Find a project's folder from its
ID](tcw://C/cli/find-a-projects-folder-from-its-id)): a manifest entry, a
`TCW_PROJECT_<ID>` variable, or the search. Run in a linked git worktree, it
answers for that worktree. It writes nothing.

When the project is not on this machine, it prints nothing on standard output
and exits 5, saying where the deciding manifest entry would place the project
and, when that entry gives a repository, naming `tcw project provision <id>`,
which fetches it. An ID no project in the graph declares exits 1 and asks me to
check the spelling; an ID that is not a valid project ID is a usage error (exit
2). When two folders on this machine both declare the ID, it names both and
exits 1 rather than choosing one. A folder `tcw project provision` left behind
while staging a clone (`.tcw-staging-<hex>`) is never taken for a second copy.
