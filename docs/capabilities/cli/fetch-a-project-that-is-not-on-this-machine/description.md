As a user arriving on a machine that has only some of a project's family, I
run `tcw project provision` to fetch the connected projects that are not here.
Each is cloned from the repository its deciding manifest entry gives (the entry
the lookup reads first; see [Find a project's folder from its
ID](tcw://C/cli/find-a-projects-folder-from-its-id)) into the folder that entry
names, so afterwards every command finds it where the manifests say it is.
`tcw project provision <id>` fetches that one project and the ancestors it
needs that are missing, and no store; with no ID, the stores this project
declares are provisioned first (see [Provision declared
stores](tcw://C/cli/provision-declared-stores)), then the projects.

It works in **rounds**. A round is every project the family names that is not
on this machine and has not yet been tried in this run. Every project of a
round is checked before any remote is contacted; then each is cloned in turn,
and the projects are read again, so the projects a fetched one names are
fetched in the next round. My project's parents and their parents are
followed upwards, and its children and their children downwards, one step
further each round; a parent's other children, my siblings, are never
fetched. A project
already on this machine is never fetched again, whichever rule found it, and
it is still read for the projects it names. A project that no manifest entry
gives a repository for is named, with where it was looked for, and left alone.

**What it refuses, before anything is contacted.** A folder that already holds
files (move it aside, or correct the entry); a folder that holds only `.git`,
which is a clone or submodule update that stopped part way (finish or remove it
with git); two entries naming different repositories for one folder; and an
address or branch beginning with `-`, so nothing is read by git as an option.
Projects placed in one folder by one repository share a single clone.

**How far another project's manifest may place a clone.** My own project's two
manifests, `.tcw/tcw-manifest.yaml` and `.tcw/tcw-manifest.local.yaml`, may
place a clone anywhere, and missing parent folders are made. Every other
manifest, an ancestor's or a descendant's, committed or personal, may place a
clone only in a folder directly inside its *bound*: the folder holding the
git repository of the project whose manifest it is (for a project fetched in
this run, the folder it was cloned into). So a package inside a monorepo is
bounded by the folder holding the monorepo. Such a manifest's absolute and `~`
paths are refused as written, its paths are resolved through any symbolic
links before they are compared, folders are compared as folders rather than
as text (so letter case on a disk that ignores it cannot slip through), and
nothing is ever placed when the bound is the home folder, a folder above it,
or a hidden folder below it. When git cannot say which repository holds that
project, the bound is not known and its entries are refused. Each refusal
names a way out: an entry in a manifest the lookup reads first, or `tcw -C
<folder> project provision <id>` run in the project whose manifest it is.

**Nothing half made is left behind.** Each clone is made in a staging folder,
`.tcw-staging-<hex>`, beside its destination, checked to hold the project the
entry names at the place the entry names (never through a link leading out of
the clone), and only then renamed into place, after the destination is checked
once more. A clone that fails or is refused is removed. Git's location
variables, such as `GIT_DIR` set by a git hook, are ignored, so the command
never acts on another repository.

Answers already found are kept for the whole run: if a fetched project's
manifest would move a project this run had already found, the run stops and
says which entry to add to keep it where it is. A problem in a fetched
project's own files stops the run, keeps what was fetched, and says how to
undo the fetch. The last line counts what was fetched and what failed, and
running the command again fetches the rest; it exits 1 when anything failed,
and 5 when the project I named still cannot be fetched for want of a
repository. `--dry-run` makes every check a real run makes before contacting
anything, prints the first round's plan, and fetches nothing.
