As a user, I name connected projects by ID, and TCW finds each one's folder on
this machine, the same way for every command and every project that names it.

It asks, in order, and the first answer decides:

1. `TCW_PROJECT_<ID>`, when it names a folder that is here (see [Point TCW at
   a project I already have](tcw://C/cli/point-tcw-at-a-project-i-already-have)).
2. The manifests (see [Record where other projects are in a
   manifest](tcw://C/cli/record-where-other-projects-are-in-a-manifest)): those
   of the project naming the ID, then its ancestors' nearest first, then its
   descendants', each person's own manifest before the committed one. The
   first entry for the ID decides, even when its folder is not here, so a
   project placed by a manifest is never found somewhere else by accident.
3. With no entry anywhere, a search: the folders next to the naming project,
   then the folders enclosing it, each tested for a project with that ID. It
   never looks inside a folder it tests, so it reads a handful of folders,
   and on macOS, which asks my permission before a program reads them, it
   never reads inside `Desktop`, `Documents` or `Downloads` in my home
   folder unless the project is in one. Two folders declaring the ID are an
   error naming both, with the manifest entry to add.

A project not found at all is not on this machine: commands that do not need
it keep working, and one that does says where its manifest entry places it, or
that no manifest lists it and which file to add it to. One command finds each
ID in one folder only: two lookups finding the ID in two folders are reported
as a duplicate naming both. Each folder is read once per command, however many
projects ask. `tcw project list --json` says, for each project, how it was
found. Inside a linked git worktree the search outside the repository is made
from the main checkout (see [Run TCW from inside a git
worktree](tcw://C/cli/run-from-a-git-worktree)).
