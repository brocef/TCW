# TCW — agent working guide

**TCW** (Taxonomy · Capabilities · Work) is a storage-abstracted framework for describing and evolving a software project along three axes, exposed through one CLI, `tcw`, with three subcommand groups (`tcw taxonomy | capabilities | work`). This guide governs all work in this repo.

- **Live status & pending work:** `tcw work list` — this repo dogfoods its own work component: its items are kept in the Jira project `TCW`, and each item's documents are under `docs/work/`; the historical build-phase tracker is retired.

## Generic instructions

- Git commit messages should not include any co-authoring content.

## Work Planning and Implementation

**All work in this repository should be tracked by the `tcw work` system!**
This project keeps its items in Jira (the `TCW` project): each item's stage,
request and comments are on its ticket, and its folder under `docs/work/`
holds its other documents.

The rules for _how_ to do that work are bound to the lifecycle stages rather than
written here. Before working a stage, run
**`tcw work stage prompt <stage> <item>`**: it prints TCW's own instructions for
that stage composed with this repo's, and it behaves identically under Claude
Code, Codex and Pi. When the stage's output is written, **`tcw work advance <item>`**
moves the item to its next stage and runs the checks bound to that move;
**`tcw work advance <item> --dry-run`** says whether the move would be allowed,
and moves nothing.

| Stage       | What this repo adds to TCW's own instructions                                                                                                                                                                                                                                     |
| ----------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `spec`      | [`docs/lifecycle/abstraction.md`](docs/lifecycle/abstraction.md) · [`docs/lifecycle/harness.md`](docs/lifecycle/harness.md) · the spec outline, [`spec.md`](docs/lifecycle/templates/spec.md) or, for an item tagged `bug`, [`spec-bug.md`](docs/lifecycle/templates/spec-bug.md) |
| `plan`      | [`docs/lifecycle/abstraction.md`](docs/lifecycle/abstraction.md) — and the move into `plan` refuses until the spec is written                                                                                                                                                     |
| `implement` | [`docs/lifecycle/implementation.md`](docs/lifecycle/implementation.md) · [`docs/lifecycle/harness.md`](docs/lifecycle/harness.md) — and the move into `implement` refuses until the spec and plan are written                                                                     |
| `review`    | [`docs/lifecycle/review.md`](docs/lifecycle/review.md): the suite run as CI runs it, and the documentation entries, before an accepted verdict                                                                                                                                    |
| `completed` | the move into `completed` runs `tcw validate`, and refuses unless it passes                                                                                                                                                                                                       |

Every stage's instructions from `request` on start by asking for
`git pull --ff-only`, and every move to a stage after `inbox` runs
`docs/guide/examples/commit-item-after-move.sh`, which commits the item's
folder when the move changed a file in it. The bindings are in
`.tcw/tcw-config.yaml`; `tcw work lifecycle` lists them.

**Advance an item to `implement` before the first change to code.** As soon as
its plan is written, `tcw work advance <item>` moves it from `plan` to
`implement`, so that its ticket shows the work as in progress while it is
being done.

**Exception — do not drive the lifecycle with the `tcw` CLI while TCW's own code
is being changed in the working tree.** The CLI you would be driving is the thing
under modification, so its behavior is in flux: results are unreliable and it can
hang (`tcw work new` once blocked inside a capture script). As soon as a session
starts editing `tcw/`, work the lifecycle by hand, and say so rather than
silently alternating between the two: move each ticket in Jira itself, to the
status of the stage it is going to (`work.stages` in `.tcw/tcw-config.yaml` gives
each stage's status), and write the files in an item's folder directly. A hand
move runs none of the checks or hooks bound to it — no `pre` checks and no
commit — so do what they would have done yourself. A hand move that skips a
stage whose document was never written is reported by `tcw validate --remote`
as a stage ahead of its documents.

**Closing the originating GitHub issue waits for publication.** An item that
came from a GitHub issue is not finished until the issue is answered and
closed, but an issue closed before the fix ships tells the reporter it is fixed
when they still cannot install it. The order is: complete every work item → cut
the version → push → then answer and close the issues. Complete the item anyway,
and say in its qa findings (on this project, a comment on its ticket) that the
closing waits for publication, naming this sequencing as the reason; batch the
version cut across a run of items rather than cutting one per item. Nothing is
ever posted to an issue without the exact text being approved first.

**The prime directive is the abstraction litmus test** — _"could a non-filesystem
store implement this operation, even if less elegantly?"_ It governs every change
to an operation, not only the ones made at a lifecycle stage, and it lives in
full in [`docs/lifecycle/abstraction.md`](docs/lifecycle/abstraction.md).

**Check every change against the setups TCW is used in**:
[`docs/use-cases.md`](docs/use-cases.md) lists them (a single project, a
library others read, a monorepo of several projects, many repositories with a
planning workspace, a Jira project shared by several projects, and the
situations that cut across them), each with its requirements and known gaps.
Every spec names the cases it touches in its `## Use cases` section.

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

### Working in a git worktree

TCW does not create worktrees. A contributor who makes one with
`git worktree add`, to work on a branch while the primary checkout stays on
`main`, finds that **the worktree's source is not what runs**: the editable
install (`pip install -e`) registers an import hook pinned to the primary
checkout's path. `PYTHONPATH=<worktree>` does not override it, because import
hooks take priority over the module search path. `import tcw` resolves to the
worktree only when the shell's current directory is the worktree's root, which
puts its own `tcw/` first on the search path.

To exercise the worktree's source, give the worktree its own virtual
environment, a private Python installation inside the worktree, and leave the
shared install alone:

```sh
python -m venv .venv
.venv/bin/pip install -e '.[dev]'
```

Run both from the worktree's root, then run pytest and `tcw` from that
environment (`.venv/bin/pytest`, `.venv/bin/tcw`), with the current directory
set to the worktree. `.venv/` is ignored, so nothing needs undoing when the
worktree is removed.

## Measuring the skill layer

`evals/` holds the harness that measures whether this project's lifecycle
instructions actually reach an agent, and what the plugin's skills add. pytest
cannot answer either question: it can prove a skill file still says the right
words, never that an agent read them.

```sh
python evals/seed_fixture.py --customized /tmp/probe   # build one fixture project
python evals/seed_fixture.py --bare /tmp/probe         # ...or a repo with no TCW yet
python -m evals.run_evals --axis a --dry-run           # see the arms, spawn nothing
python -m evals.run_evals --axis a                     # spend money
python -m evals.grade eval-runs/iteration-1            # read the result
```

**The runner pins both the plugin and the `tcw` command to this checkout.**
`--plugin-dir` is not optional, and the runner passes it for you: enabling
`tcw@tcw` instead loads `~/.claude/plugins/marketplaces/tcw`, which is a
different commit from your working tree and auto-updates, so a run would measure
the published plugin rather than your changes. The same goes for the `tcw` the
agent runs: the first one on PATH is usually an installed release, whose stage
prompts are not the ones under test, so the runner puts its own Python's folder
first on the agent's PATH. Run the harness with a Python that has this checkout
installed (`pip install -e .`), or that folder holds no `tcw` of yours. The
runner records which plugin the spawned session loaded (from its own `init`
event) and where its `tcw` imports from in each run's `timing.json`, as
`isolation_problems` when either is not this checkout; `evals.grade` prints them
and exits non-zero for any run that has one.

Two rules for anyone changing the harness. Every assertion is mutation-checked
before it is trusted — break what it claims to observe, confirm it goes red, and
read _why_ it went red. And a nonce in an artifact is not enough on its own:
each lifecycle case also checks that the agent ran `tcw work stage prompt
<stage>`, because that command is the one source of stage text and no skill
injects it any more.

Run outputs are disposable and gitignored. The instrument is not.

## Documentation Sync

Before reporting any code change complete, invoke the `documentation-sync` skill
to evaluate this project's documentation entries. They are **configuration, not
prose**: they live in `.tcw/tcw-config.yaml` under `work.documentation`, `tcw validate`
checks their shape, and `tcw work docs` prints them. `tcw work stage prompt plan` and
`tcw work stage prompt implement` include them inline, so a plan should already name a
task for every trigger expected to fire.

The reasoning stays here; the facts live in config. The version is duplicated
across five files for the reason given below, and the documentation entries are
what they are because this project ships a CLI, a plugin, and a set of skills
that drift from each other if nobody is told to look.

## Versioning

The version string is **duplicated across 5 files** — a release bumps _all_ of them in lockstep, not just `pyproject.toml`. Keep them identical. `tests/test_plugin_manifests.py` guards that they agree.

**Cut a release with `python scripts/cut_version.py <patch|minor|major|X.Y.Z>`** — it bumps all 5 files, combines the entry files in `docs/{changelogs,release-notes}/upcoming/` into each folder's `v{version}.md` (merging sections by heading, deleting the entry files, keeping each folder's `README.md`), commits, and tags. It aborts on version drift or a missing `upcoming/` folder; it does **not** push (publishing stays a human step). Each change adds its own `upcoming/<work-item-folder>.md` entry files, named by the item's folder name, _before_ the cut — never edit another change's file. The 5 files:

1. `pyproject.toml` — `project.version`
2. `tcw/__init__.py` — `__version__`
3. `.claude-plugin/plugin.json` — `version`
4. `.claude-plugin/marketplace.json` — `plugins[0].version`
5. `.codex-plugin/plugin.json` — `version`

(`.agents/plugins/marketplace.json` deliberately carries **no** version — don't add one.)
