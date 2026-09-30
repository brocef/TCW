## New

- **Read a project that does not name you back.** A project can now list another
  under `connected-projects.upstream` and read its taxonomy, capabilities and work
  items without that project mentioning it — for example a private application
  reading a public library, where the library must not name the application. The
  whole family of the reader (its parents, children and their children) can read
  it too. Nothing beyond the upstream's own settings is read, so a problem in its
  connections never blocks you, and `tcw provision` fetches it without fetching
  what it connects to.
- **Upstream projects are read-only.** Commands that would change an upstream's
  work items — `start`, `edit`, `drop`, `delegate`, the stage and procedure
  commands, and the web app's edit actions — refuse and tell you to run them in
  the upstream's own checkout. `tcw work nodes` lists upstreams separately.
- **Moving a child to upstream is safe in steps.** Move the entry from
  `children` to `upstream` in the parent first; until the former child removes
  its `parent` entry, `tcw validate` shows a warning rather than blocking either
  project. See "Working across repositories" in the guide.

## Fixes

- **A tracker block with nowhere to inherit from says so.** A project whose
  `work.tracker` block is incomplete and which has no parent now gets a line
  saying there is no parent to inherit the rest from — declare the whole block
  or remove it.
