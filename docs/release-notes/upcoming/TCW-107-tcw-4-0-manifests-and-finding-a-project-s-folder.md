## Where other projects are: the manifest

`projects:` in `.tcw/tcw-config.yaml` now names connected projects by ID only:

    projects:
      parent:
        ws:
      upstream:
        lib:

Where each one is on disk goes in a manifest beside it. `.tcw/tcw-manifest.yaml`
is committed and shared; `.tcw/tcw-manifest.local.yaml` is yours alone, read
first, and kept out of version control (`tcw init` adds it to
`.tcw/.gitignore`). An entry is a path relative to the project, or a mapping
that also gives the repository the project comes from:

    tcw-version: 4.0.0
    projects:
      ws: ..
      lib:
        path: ../lib
        repository: https://example.com/lib.git#main

A `projects:` entry that still holds a location, as in TCW 3, is refused with
the manifest entry to write instead.

## TCW finds a project even with no manifest

When no manifest places a project, TCW looks for it in the folders next to the
project that names it and in the folders enclosing it, never inside a project.
Two folders declaring the same ID are an error naming both. `TCW_PROJECT_<ID>`
still decides over everything. `tcw projects list --json` now says how each
project was found.

## A project not on this machine says how to get it

A connected project that is not here, including one whose folder is empty or
holds only `.git`, is reported with where its manifest places it and, when the
entry gives a repository, the command that fetches it:
`tcw project provision <id>`. `tcw provision` no longer fetches connected
projects; it still fetches the component stores a project declares.
`tcw validate` checks every entry of your manifests, and warns when your
personal manifest is tracked by version control.

## Git worktrees

A linked worktree has no personal files until you make them. When it has no
`.tcw/tcw-config.local.yaml` or `.tcw/tcw-manifest.local.yaml` of its own, the
main checkout's is used. Projects outside the repository are found from the
main checkout.
