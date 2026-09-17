# Getting `tcw` on PATH

The plugin ships the skills; `tcw` is a Python package that has to be installed.
**Under Claude it installs itself:** a `SessionStart` hook runs
`scripts/session_bootstrap.sh`, which installs the published `tcw-cli`
distribution from PyPI with `pipx` and reinstalls it when a plugin update changes
the plugin's version. The first install needs network — there is no offline
fallback — and the script is silent on success and on every deliberate skip, so
it says nothing most sessions. Under Codex there is no hook, so once the check
below finds no `tcw`, run it yourself:

```sh
bash <plugin>/scripts/session_bootstrap.sh <plugin>
```

`<plugin>` is the plugin's root folder — the one holding `skills/` and `scripts/`,
three levels above the folder this file is in. Quote it if the path has a space. The script's second argument, a file recording which
plugin version it last installed for, can be left off: you run the script only when
`tcw` is missing, and that file only saves a reinstall on a later run. The script
prints nothing when it succeeds or declines, so run `tcw --version` afterwards; if
there is still no `tcw`, follow the steps below.

**Check before reading further:**

```
tcw --version      # prints a version? → nothing to do. stop here.
```

If it does not:

1. `pipx install tcw-cli`. The distribution is `tcw-cli` because `tcw` on PyPI is
   an unrelated project; the command and the import package are both still `tcw`.
   Installing over an existing `pipx install tcw-cli` replaces it in place.
2. **No `pipx`?** `python3 -m pip install --user pipx && pipx ensurepath`, then
   (1). `python3 -m pip install --user tcw-cli` works too. Never `pip install`
   into a managed base interpreter. The bootstrap script stops rather than
   choosing here, on purpose: picking someone's Python environment is a judgment
   call that must not happen silently at session start.
3. **Behind the latest release?** `pipx upgrade tcw-cli`. Report it, don't treat
   it as breakage: the installed CLI floats, and it is not required to equal the
   plugin's version.

**Check who owns a `tcw` that is already on PATH before replacing it.** Read its
shebang for the interpreter that owns the install — never the `python3` on PATH,
which for a pipx or venv install is a different environment and will report no
such distribution. If that interpreter reports `tcw-cli` as an editable install
(`direct_url.json` → `dir_info.editable`), it is a developer's `pip install -e`
checkout: say so and leave it alone. A non-Python shebang names no owner, so it
is not yours to replace either. `pipx install --force` over either one silently
destroys a working setup, and the bootstrap script declines for the same reason —
which is why it sometimes does nothing and prints nothing.

**A `tcw` that runs is not an install problem.** In particular, a `tcw work`
command reporting that the store is _declared but not provisioned here_ is a
working install telling you the truth: the project keeps its store in another
repository and this machine has not obtained it. Run `tcw provision`. That is
`project.md`'s concern, not this document's.

**Installing into a cloud environment** — a session that is thrown away, so
anything installed by hand is gone by the next one — is a session-start hook in
the user's own repository rather than anything this skill does. That hook does
nothing when `tcw` is already on PATH; otherwise it runs `pipx install tcw-cli`,
or, with no `pipx`, installs `tcw-cli` into the container's own Python. That is
acceptable only because the container is disposable and has no user environment
to damage. The hook exits 0 on every path, so a failed install never stops a
session from starting, and prints one line when the install failed.

Node.js is not a general TCW prerequisite. Check for Node 22.12 or newer only
when the user intends to run or diagnose `tcw serve`. Installed TCW already
contains the prebuilt Fastify/React assets; pnpm and `node_modules` are
contributor-only requirements and must not be added to install steps.
