# TCW — agent working guide

**TCW** (Taxonomy · Capabilities · Work) is a storage-abstracted framework for describing and evolving a software project along three axes, exposed through one CLI, `tcw`, with three subcommand groups (`tcw taxonomy | capabilities | work`). This guide governs all work in this repo.

- **Live status & pending work:** `tcw work` — this repo dogfoods its own work component (`docs/work/`); the historical build-phase tracker is retired.

## Generic instructions

- Git commit messages should not include any co-authoring content.

## Work Planning and Implementation

**All work in this repository should be tracked by the `tcw work` system!**

The rules for *how* to do that work are bound to the lifecycle stages rather than
written here. Run **`tcw work stage <stage> <work-item-slug>`**: it prints TCW's
own instructions for that stage composed with this repo's, and it behaves
identically under Claude and Codex.

| Stage       | What this repo adds to TCW's own instructions                                                                                |
| ----------- | ---------------------------------------------------------------------------------------------------------------------------- |
| `spec`      | [`docs/lifecycle/abstraction.md`](docs/lifecycle/abstraction.md) · [`docs/lifecycle/harness.md`](docs/lifecycle/harness.md)     |
| `plan`      | [`docs/lifecycle/abstraction.md`](docs/lifecycle/abstraction.md) — and refuses until the spec is written                        |
| `implement` | [`docs/lifecycle/implementation.md`](docs/lifecycle/implementation.md) · [`docs/lifecycle/harness.md`](docs/lifecycle/harness.md) |

The bindings are in `tcw-config.yaml`; `tcw work lifecycle` lists them.

**The prime directive is the abstraction litmus test** — _"could a non-filesystem
store implement this operation, even if less elegantly?"_ It governs every change
to an operation, not only the ones made at a lifecycle stage, and it lives in
full in [`docs/lifecycle/abstraction.md`](docs/lifecycle/abstraction.md).

## Development environment

A **Claude Code remote session** provisions itself at session start:
`scripts/remote_session_setup.sh`, wired to `SessionStart` in
`.claude/settings.json`, installs this checkout with its dev extras
(`pip install -e '.[dev]'`) and installs the `tcw` plugin from the checkout, so
`tcw`, `pytest`, and the plugin's skills are present without a manual step. It
is idempotent, exits 0 on every path, and prints only when something failed —
a session start that says nothing succeeded.

Everywhere else — Codex, a local shell, a session where the hook never fired —
run the same provisioning by hand:

```sh
scripts/remote_session_setup.sh --force
```

That script is contributor tooling, **not** the published install path. The
published one is `scripts/session_bootstrap.sh`, which installs the released
`tcw-cli` from PyPI with pipx for a _user_; leave it alone when changing this
one.

## Documentation Sync

Before reporting any code change complete, invoke the `documentation-sync` skill
to evaluate this project's documentation entries. They are **configuration, not
prose**: they live in `tcw-config.yaml` under `work.documentation`, `tcw validate`
checks their shape, and `tcw work docs` prints them. `tcw work stage plan` and
`tcw work stage implement` include them inline, so a plan should already name a
task for every trigger expected to fire.

The reasoning stays here; the facts live in config. The version is duplicated
across five files for the reason given below, and the documentation entries are
what they are because this project ships a CLI, a plugin, and a set of skills
that drift from each other if nobody is told to look.

## Versioning

The version string is **duplicated across 5 files** — a release bumps _all_ of them in lockstep, not just `pyproject.toml`. Keep them identical. `tests/test_plugin_manifests.py` guards that they agree.

**Cut a release with `python scripts/cut_version.py <patch|minor|major|X.Y.Z>`** — it bumps all 5 files, rotates `docs/{changelogs,release-notes}/upcoming.md` → `v{version}.md` (recreating fresh `upcoming.md`), commits, and tags. It aborts on version drift; it does **not** push (publishing stays a human step). Write the changelog/release-note entries into `upcoming.md` _before_ running it. The 5 files:

1. `pyproject.toml` — `project.version`
2. `tcw/__init__.py` — `__version__`
3. `.claude-plugin/plugin.json` — `version`
4. `.claude-plugin/marketplace.json` — `plugins[0].version`
5. `.codex-plugin/plugin.json` — `version`

(`.agents/plugins/marketplace.json` deliberately carries **no** version — don't add one.)
