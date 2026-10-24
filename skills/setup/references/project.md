# Start using TCW in a project

Read this when a repository does not use TCW yet, or when a project that does
use TCW is missing parts on this machine. Check `tcw --version` first; if it
fails, follow `install.md` before anything here.

## Is this project already set up?

Look for `tcw-config.yaml` in the current folder or any folder above it, and run
`tcw validate`.

- **No `tcw-config.yaml` anywhere above.** The project does not use TCW. Start
  at "A new project" below.
- **`tcw-config.yaml` exists, and a command says a store or project is declared
  but not here.** The project uses TCW and this machine lacks part of it. Go to
  "A project that is set up elsewhere".
- **`tcw validate` exits 0 with no findings.** TCW already works here. To
  change how it behaves, use the `configure` skill instead.

## A new project

1. **Choose a project ID.** It is the project's permanent name across every
   connected repository: lowercase letters and digits, words joined by single
   hyphens (`billing-service`). It cannot be changed afterwards. When the user
   has named the project, use that name in this form and say so; otherwise ask.
2. **Run `tcw project new` from the folder the project lives in:**

   ```sh
   tcw project new --id <project-id>                  # all three components
   tcw project new --id <project-id> taxonomy work    # or only the named ones
   ```

   It marks the current folder as a TCW project by writing `tcw-config.yaml`
   with the ID, then creates each component's store under `docs/`. The folder
   does not have to be the root of a repository, so one repository can hold
   several projects.
3. **A component can be added later** by naming it: `tcw project new taxonomy`,
   `tcw project new capabilities` or `tcw project new work`, run in the project's folder.
4. **Stores somewhere other than `docs/<component>`**, including in another
   repository: read the configure skill's reference on stores before running
   `tcw project new`, because it covers the path flags `tcw project new` takes.

`tcw project new` only writes files. Show the user what it wrote; keeping those files,
in version control or otherwise, is the project's own choice.

## A project that is set up elsewhere

A project's `tcw-config.yaml` can declare that a store, or a connected project,
lives in another repository. A checkout that cloned only this repository does
not have those yet, and a command that needs one fails, names the declared
remote, and says to run `tcw project provision`.

```sh
tcw project provision --dry-run                 # print what would be fetched; contact nothing
tcw project provision                           # fetch every declared store and connected project
tcw project provision --component taxonomy      # only one component's store
```

`tcw project provision` follows connected projects in turn, since a project it fetches
may declare others. It does not prompt: cloning a private repository whose
credentials cannot be found without asking fails, naming the reason, and the
fix is for the user to set up a credential helper or load an ssh key into an
ssh agent, not to retry. The exception is an ssh command the user has set
(`GIT_SSH_COMMAND`, `GIT_SSH`, or `core.sshCommand` in their global or system
configuration or given on the command line, not the current repository's own
setting): TCW leaves it alone, so ssh may still ask. **Never run `tcw project new` to
get past a declared store that is missing here.** That creates a second, empty
store beside the real one.

If `tcw project provision` is about to fetch a copy of a project that is already on this
machine under a different folder layout, stop: the fix is the `TCW_PROJECT_<ID>`
variable, described in the configure skill's reference on projects.

## Finish

1. Run `tcw validate`. It checks this project and every project below it, and
   exits non-zero on any problem.
2. To seed a taxonomy from the existing code, continue with `taxonomy.md`; for a
   capabilities ledger, `capabilities.md`, after the taxonomy.
3. To keep the work in Jira instead of in files, continue with `jira.md`.
4. To change configuration from here — documentation entries, stage bindings,
   store locations, or connected and inherited projects — use the `configure`
   skill.
