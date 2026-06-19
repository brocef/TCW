# TCW — Taxonomy · Capabilities · Work

A storage-abstracted framework for describing and evolving a software project
along three axes, exposed through one CLI (`tcw`) with three subcommand groups:

| Component | Is | What it is |
|---|---|---|
| **Taxonomy** | the nouns | the things an app deals with (domain entities) |
| **Capabilities** | the user stories | what a user can do with them |
| **Work** | the changes | edits to capabilities, machinery, or the project itself |

They link by loose, one-directional pointers and never duplicate each other.
The model is **storage-abstracted** (it can run against an external tracker),
with a filesystem-native default. See [`AGENTS.md`](AGENTS.md) for the design
rules and [`docs/plan/INDEX.md`](docs/plan/INDEX.md) for the build plan.

## Install

```sh
pip install -e .          # development install; puts `tcw` on PATH
# or, once published:  pipx install tcw
```

## Quickstart

```sh
cd your-git-repo
tcw init                  # scaffold docs/{taxonomy,capabilities,work}/
tcw init taxonomy work    # or just the components you name
tcw --help
```

`tcw init` operates on the current git work-tree and refuses outside a git repo.

## Status

Early build. Phase 1 (scaffold) is in place; `taxonomy`, `capabilities`, and
`work` command groups are stubbed until their phases land. Track progress in
[`docs/plan/INDEX.md`](docs/plan/INDEX.md).
