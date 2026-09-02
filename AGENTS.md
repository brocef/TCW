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

**Exception — do not drive the lifecycle with the `tcw` CLI while TCW's own code
is being changed in the working tree.** The CLI you would be driving is the thing
under modification, so its behavior is in flux: results are unreliable and it can
hang (`tcw work new` once blocked inside a capture script). As soon as a session
starts editing `tcw/`, switch to recording work as plain Markdown documents in
`docs/work/inbox/`, and say so rather than silently alternating between the two.
Do **not** hand-move item folders between status directories to compensate — that
is the filesystem shortcut the prime directive refuses. Leave a stale status in
place and file an inbox note about it.

**Closing the originating GitHub issue waits for publication.** `docs/work/dod.yaml`
lists _"originating GitHub issue answered and closed, if the item came from one"_
as a completion criterion, but an issue closed before the fix ships tells the
reporter it is fixed when they still cannot install it. The order is: complete
every work item → cut the version → push → then answer and close the issues.
Complete the item anyway and record the deferral explicitly in
`refined-outcome.md`, naming this sequencing as the reason; batch the version cut
across a run of items rather than cutting one per item. Nothing is ever posted to
an issue without the exact text being approved first.

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

### Working in a `--worktree` branch

`tcw work start <slug> --worktree` puts implementation edits in
`.worktrees/<slug>/` on a `work/<slug>` branch while the primary checkout stays
on `main` — but the editable install (`pip install -e`) registers an import hook
pinned to the primary checkout path, so **the worktree's source is not what runs**.
`PYTHONPATH=<worktree>` does not override it, because import hooks take priority
over the module search path. `import tcw` only resolves to the worktree when the
shell's current directory is the worktree root, which puts its own `tcw/` first
on the search path.

To actually exercise worktree source, re-point the install once —
`pip install -e <worktree> --no-deps`, preceded by `pip uninstall tcw -y` if a
stale `tcw-0.0.1` hook lingers, since a version-mismatched hook shadows the
right one — and run pytest and the CLI with the current directory set to the
worktree.

**Restore it before finishing.** `tcw work complete` tears the worktree down as
part of completing (and refuses to run from inside the worktree it is about to
remove, so run it from the primary checkout). Re-point the install first —
`pip install -e /Users/brian/Projects/TCW` — or it is left pointing at a deleted
path.

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
