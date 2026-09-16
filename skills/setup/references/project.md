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
- **`tcw validate` prints `validate OK`.** TCW already works here. To change how
  it behaves, use the `configure` skill instead.

## A new project

1. **Choose a project ID.** It is the project's permanent name across every
   connected repository: lowercase letters and digits, words joined by single
   hyphens (`billing-service`). It cannot be changed afterwards. When the user
   has named the project, use that name in this form and say so; otherwise ask.
2. **Run `tcw init` from the folder the project lives in**, inside a Git
   repository:

   ```sh
   tcw init --id <project-id>                  # all three components
   tcw init --id <project-id> taxonomy work    # or only the named ones
   ```

   It marks the current folder as a TCW project by writing `tcw-config.yaml`
   with the ID, then creates each component's store under `docs/`. It refuses to
   run outside a Git repository, because transitions commit. The folder does not
   have to be the repository root, so one repository can hold several projects.
3. **A component can be added later** with its own command: `tcw taxonomy init`,
   `tcw capabilities init` or `tcw work init`.
4. **Stores somewhere other than `docs/<component>`**, including in another
   repository: see the `configure` skill's `stores.md` before running
   `tcw init`, because it covers the path flags `tcw init` takes.

Nothing `tcw init` writes is committed for you. Show the user the new files and
commit them once they agree.

## A project that is set up elsewhere

A project's `tcw-config.yaml` can declare that a store, or a connected project,
lives in another repository. A checkout that cloned only this repository does
not have those yet, and a command that needs one fails, names the declared
remote, and says to run `tcw provision`.

```sh
tcw provision --dry-run                 # print what would be fetched; contact nothing
tcw provision                           # fetch every declared store and connected project
tcw provision --component taxonomy      # only one component's store
tcw provision --refresh                 # bring an existing copy up to the declared version
```

`tcw provision` follows connected projects in turn, since a project it fetches
may declare others. **Never run `tcw init` to get past a declared store that is
missing here.** That creates a second, empty store beside the real one.

If `tcw provision` is about to fetch a copy of a project that is already on this
machine under a different folder layout, stop: the fix is the `TCW_PROJECT_<ID>`
variable, described in the `configure` skill's `projects.md`.

## Finish

1. Run `tcw validate`. It checks this project and every project below it, and
   exits non-zero on any problem.
2. To seed a taxonomy from the existing code, continue with `taxonomy.md`; for a
   capabilities ledger, `capabilities.md`, after the taxonomy.
3. To change configuration from here — documentation entries, lifecycle
   bindings, the Definition of Done, a tracker, store locations, or connected
   and inherited projects — use the `configure` skill.
