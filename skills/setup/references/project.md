# Start using TCW in a project

Read this when a repository does not use TCW yet, when a project that does
use TCW is missing parts on this machine, or when a project still uses TCW
3.x. Check `tcw --version` first; if it fails, follow `install.md` before
anything here.

## Is this project already set up?

A TCW project is a folder holding a `.tcw/` folder with its configuration
file, `.tcw/tcw-config.yaml`, in it. Look for `.tcw/tcw-config.yaml` in the
current folder or any folder above it, and run `tcw validate`, which finds the
nearest one the same way.

- **No `.tcw/tcw-config.yaml` anywhere above, and no 3.x project either.**
  The project does not use TCW: `tcw validate` exits 1, saying there is no
  TCW project here and to run `tcw project new --id <id>`. Start at "A new
  project" below.
- **A command says the folder is a TCW 3.x project.** That project was made
  with TCW 3.x: it has no `.tcw/` folder, and its configuration file is at its
  root, as `tcw-config.yaml`, which `tcw migrate` moves into `.tcw/`. Go to
  "A 3.x project".
- **`.tcw/tcw-config.yaml` exists, and a command says a store or a related
  project is not on this machine.** The project uses TCW and this machine lacks
  part of it. Go to "A project that is set up elsewhere".
- **`tcw validate` exits 0 and prints `0 errors, 0 warnings, 0 unresolved`.**
  TCW already works here. To change how it behaves, use the `configure` skill
  instead.

## A new project

1. **Choose a project ID.** It is the project's permanent name across every
   related project: lowercase letters and digits, words joined by single
   hyphens (`billing-service`). It cannot be changed afterwards. When the user
   has named the project, use that name in this form and say so; otherwise ask.
2. **Run `tcw project new` from the folder the project lives in:**

    ```sh
    tcw project new --id <project-id>                  # all three components
    tcw project new --id <project-id> taxonomy work    # or only the named ones
    ```

    It marks the current folder as a TCW project by writing
    `.tcw/tcw-config.yaml`, which holds the line `tcw-version: 4.0.0` (the
    version of TCW the file is written for) and the ID. Inside a repository it
    also writes `.tcw/.gitignore`, which keeps the two personal files,
    `.tcw/tcw-config.local.yaml` (this machine's own settings) and
    `.tcw/tcw-manifest.local.yaml` (where related projects are on this
    machine), out of version control; outside one it writes no ignore file and
    prints a note saying so. It then creates each component's store under
    `docs/`, with an empty `.gitkeep` file in each, and names every file and
    folder it wrote on standard error. A new project needs `--id`; without it the command exits 2
    and writes nothing. The folder does not have to be the root of a
    repository, so one repository can hold several projects.

3. **A component can be added later** by naming it: `tcw project new taxonomy`,
   `tcw project new capabilities` or `tcw project new work`, run in the
   project's folder. A component whose store already exists is left as it is.
4. **Stores somewhere other than `docs/<component>`**, including in another
   repository: read the configure skill's reference on stores before running
   `tcw project new`, because it covers the path flags `tcw project new` takes.

`tcw project new` only writes files. Show the user what it wrote; keeping those
files, in version control or otherwise, is the project's own choice.

## A 3.x project

TCW 4.0 reads only 4.0 projects. In a 3.x project, every command except
`tcw migrate` exits 1 and changes nothing, `tcw validate` and
`tcw project new` among them, with a line ending
`run 'tcw migrate' in it to move it to TCW 4`. A 4.0 project whose parent is
still a 3.x project gets the same line, naming the parent's folder.
`tcw migrate` moves the project over:

```sh
tcw migrate --dry-run    # say what would change, and change nothing
tcw migrate              # make the change
```

Moving a project over is the user's decision, not a step to take for them:
once it is done, TCW 3.x cannot read the project, so everyone who works on it
upgrades at the same time, and its files are saved first (in version control,
or as a copy) so the change can be undone. Before running anything, read the
migration guide with the user: `docs/migration-guide-3.X-to-4.0.0.md` in the
TCW repository, at
https://github.com/brocef/TCW/blob/main/docs/migration-guide-3.X-to-4.0.0.md.
It says what to check first, how to read what `tcw migrate --dry-run` prints,
the order for related projects (parents before children), and what replaces
each 3.x command, setting and file.

## A project that is set up elsewhere

A project's `.tcw/tcw-config.yaml` can declare that a store lives in another
repository, and the project can have related projects (its parents, named
under `parents:`, and its children, named under `children:`) that this
machine does not have yet. A checkout that cloned only this repository lacks
them, and what still works depends on what is missing:

- **A store declared in another repository and not fetched here:** every
  command that needs that store exits 1, naming the repository and the command
  that fetches it, `tcw project provision --component <axis>`.
- **A related project not on this machine:** commands that need only this
  project still work, and its own taxonomy and capabilities listings warn and
  show only its own entries. A command that needs what the missing project
  passes down exits 7: a listing with `--scope up`, and the commands that read
  or register tags when that project passes `config`. `tcw validate` reports
  what it could not check as unresolved and exits 0. Each message ends with the
  command that fetches the project, such as `tcw project provision core`, when
  a manifest (the file that says where each related project is on this
  machine, `.tcw/tcw-manifest.yaml` or `.tcw/tcw-manifest.local.yaml`) gives
  the repository to fetch it from.

```sh
tcw project provision --dry-run                 # print what would be fetched; contact nothing
tcw project provision                           # fetch every declared store and related project
tcw project provision <id>                      # only that project and the projects it inherits from
tcw project provision --component taxonomy      # only one component's store
```

`tcw project provision` clones what is missing and leaves alone what is
already here, so running it again fetches nothing more. It works in rounds,
since a project it fetches may name others. A run that fetched some things and
failed others keeps what it fetched and exits 1. It does not prompt: cloning a
private repository whose credentials cannot be found without asking fails,
naming the reason, and the fix is for the user to set up a credential helper
or load an ssh key into an ssh agent, not to retry. The exception is an ssh
command the user has set (`GIT_SSH_COMMAND`, `GIT_SSH`, or `core.sshCommand`
in their global or system configuration or given on the command line, not the
current repository's own setting): TCW leaves it alone, so ssh may still ask.
**Never run `tcw project new` to get past a declared store that is missing
here.** That creates a second, empty store where the real one should be.

**Where a clone may go.** The active project's own two manifests may place a
clone anywhere. Any other manifest, such as one in a parent's repository, may
place a clone only in a folder directly inside the folder holding that
manifest's owner's repository, never in a folder whose name starts with `.`,
and never when that folder is the home folder, a folder above it, or a hidden
folder below it. Anything else is refused (exit 1), and the refusal names the two
ways out: run the command as the manifest's owner,
`tcw -C <folder> project provision <id>` with the owner's folder as
`<folder>`, which makes that manifest the active project's own; or add an
entry for the project, with both its `path` and its `repository`, to the
owner's `.tcw/tcw-manifest.local.yaml`, and run the same command. The cases
these rules leave out are in the guide on related projects,
`docs/guide/multi-repo.md` in the TCW repository, under "Where a clone may be
placed".

If `tcw project provision` is about to fetch a copy of a project that is
already on this machine in another folder, stop: the fix is an entry for it in
`.tcw/tcw-manifest.local.yaml` (read on this machine only), or the
`TCW_PROJECT_<ID>` variable, both described in the configure skill's
reference on projects.

## Finish

1. Run `tcw validate`. It checks this project's own files, stores and work
   items, and exits 1 when it finds an error; run it in each project that was
   set up.
2. To seed a taxonomy from the existing code, continue with `taxonomy.md`; for a
   capabilities ledger, `capabilities.md`, after the taxonomy.
3. To keep the work in Jira instead of in files, continue with `jira.md`.
4. To change configuration from here — documentation entries, stage bindings,
   store locations, or parent links, children and inheritance — use the
   `configure` skill.
