---
name: tcw-plugin
description: TCW orientation across the plugin's skills, plus getting the `tcw` CLI on PATH from PyPI. Use for cross-skill orientation, or when `tcw` is missing or broken — not on PATH, `tcw --version` fails, or a plugin update left it stale. Under Claude a `SessionStart` hook already installs the CLI automatically, so getting here means it did not finish the job; Codex has no hook and uses this skill directly.
when_to_use: Use for TCW orientation across the plugin's skills, or when the `tcw` CLI is missing or broken — not found on PATH, `tcw --version` fails, or a plugin update left it stale — to install it from PyPI.
allowed-tools: Bash(tcw *), Bash(command -v *), Bash(realpath *), Bash(head *), Bash(pipx *), Bash(python3 *), Bash(node --version), Bash(*/scripts/session_bootstrap.sh *), Read
metadata:
    author: Brian Cefali
compatibility: Requires Python 3.11+ and network access to PyPI on first install; `tcw serve` additionally requires Node.js 22.12+; installs the `tcw-cli` distribution via pipx.
license: Apache-2.0
---

# TCW skill map

TCW has three project axes plus this plugin-maintenance skill:

1. **Taxonomy (`tcw-taxonomy`)** registers the project's language:
    - **Vocabulary** entries are conceptual terms.
    - **Feature** entries are user- or application-facing manifestations that
      operate on or involve vocabulary.
2. **Capabilities (`tcw-capabilities`)** describe what users can do. A
   capability can point loosely at a taxonomy `Subject` and strongly at a
   taxonomy `Feature`.
3. **Work (`tcw-work`)** tracks planned and completed changes to vocabulary,
   features, capabilities, code, and docs through the SDLC artifacts.

Plus two GitHub-issue skills, orthogonal to the three axes and pointing in
opposite directions:

- **Report (`tcw-report`)** teaches a user how to send feedback about TCW
  _itself_ — a `tcw` bug or a suggestion — upstream as a GitHub issue, with a
  ready-to-fill skeleton and a mirrored example in place of the project's own
  names, since that tracker is public. It is not for the user's own project work
  (that is `tcw-work`).
- **Triage (`tcw-triage-issues`)** reads the issues **on the user's own project**
  and turns the ones worth doing into work items, rejecting the rest with a
  reply. It is the intake counterpart to `stage-inbox.md`: a GitHub issue is an
  inbox entry that happens to live on GitHub.

Use the axis skills in that order when the task changes product meaning:

`Vocabulary -> Features -> Capabilities -> Work`

Practical routing:

- If the user is naming or organizing project concepts, use `tcw-taxonomy`.
- If the user is describing user-visible behavior, use `tcw-capabilities`; check
  whether a registered taxonomy Feature should be linked.
- If the user is planning, implementing, verifying, or closing a change, use
  `tcw-work`; it invokes the capability gate for product deltas.
- If the user wants to report a `tcw` bug or send a suggestion upstream to the
  TCW project, use `tcw-report`.
- If the user wants to check, sweep, or work through the GitHub issues on _their
  own_ project, use `tcw-triage-issues`. Note the direction: `tcw-report` writes
  an issue to TCW, this one reads issues from the user's repo.
- If `tcw` itself is unavailable or the plugin install is stale, stay in this
  skill and follow the install procedure below.

The axes point forward, not backward: taxonomy entries do not point to
capabilities or work; capabilities point to taxonomy and planning work; work
records the changes being made.

# Getting `tcw` on PATH

The plugin ships the skills; `tcw` is a Python package that has to be installed.
**Under Claude it installs itself:** a `SessionStart` hook runs
`scripts/session_bootstrap.sh`, which installs the published `tcw-cli`
distribution from PyPI with `pipx` and reinstalls it when a plugin update changes
the plugin's version. The first install needs network — there is no offline
fallback — and the script is silent on success and on every deliberate skip, so
it says nothing most sessions. Under Codex there is no hook, and you run it.

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

**A `tcw` that runs is not this skill's problem.** In particular, a `tcw work`
command reporting that the store is _declared but not provisioned here_ is a
working install telling you the truth: the project keeps its store in another
repository and this machine has not obtained it. Run `tcw provision`.

**Installing into a cloud environment** — a session that is thrown away, so
anything installed by hand is gone by the next one — is a session-start hook in
the user's own repository rather than anything this skill does. The README's
_Install → In a cloud environment_ carries the script and the rules it must obey.

Node.js is not a general TCW prerequisite. Check for Node 22.12 or newer only
when the user intends to run or diagnose `tcw serve`. Installed TCW already
contains the prebuilt Fastify/React assets; pnpm and `node_modules` are
contributor-only requirements and must not be added to install steps.
