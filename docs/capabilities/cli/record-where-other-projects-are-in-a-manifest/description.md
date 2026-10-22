As a user, I record where the projects mine connects to are on disk in a
manifest, not in `.tcw/tcw-config.yaml`, so a project's location is written
once, in one place, and `projects:` names connected projects by ID only.

There are two manifests in a project's `.tcw/` folder.
`.tcw/tcw-manifest.yaml` is committed and shared by everyone who checks the
project out; `.tcw/tcw-manifest.local.yaml` is mine alone, kept out of version
control (`tcw init` lists it in `.tcw/.gitignore`), and is read first, so I can
place a project where it is on my disk without changing anyone else's
checkout. Each starts with the `tcw-version` of its format, and lists entries
under `projects:`:

    tcw-version: 4.0.0
    projects:
      lib: ../lib
      server:
        path: ../app/apps/server
        repository: https://example.com/app.git#main
        subfolder: apps/server

An entry maps a project's ID to its folder: a path relative to the project
root (in the personal manifest it may also be absolute or start with `~`), or a
mapping with that `path` and, optionally, the `repository` the project is
fetched from, written `<url>#<branch>`, and the `subfolder` of that repository
the project sits in. A manifest says where a project is and nothing else:
listing one does not connect it.

An entry that is wrong is reported, never ignored: a malformed file or entry
is an error naming the file, an entry placing a folder that holds another
project, or files and no project, is an error naming both, and an entry whose
folder is not here, or is empty, means the project is not on this machine,
which `tcw validate` reports as `unresolved` with the command that fetches it
when the entry names a repository. `tcw validate` checks every entry of the
current project's two manifests, whether or not `projects:` names it, and
reports a committed entry that my personal manifest or `TCW_PROJECT_<ID>`
overrides on this machine as a warning rather than an error.

A `projects:` entry that still holds a location, as in TCW 3, is refused with
the manifest entry to write instead. See [Find a project's folder from its
ID](tcw://C/cli/find-a-projects-folder-from-its-id) for how TCW uses the
manifests.
