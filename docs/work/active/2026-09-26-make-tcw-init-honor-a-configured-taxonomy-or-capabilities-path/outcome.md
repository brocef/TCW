# Outcome — Make tcw init honor a configured taxonomy or capabilities path

## What shipped

| Task | Commit | What |
| ---- | ------ | ---- |
| 1–2 | `e30ca698` | Tests, then `init` reads `<component>.path` back from the config for every component it scaffolds (never writing it back), builds a tree store at `STORE_CLASSES[c]._local_root(...)` — where the readers look — and refuses to scaffold an empty local store for a component that declares a `repository`. |
| 1 | `f0976e53` | The linked-worktree anchoring test. |
| docs | `93e7b178` | `skills/configure/references/stores.md`, changelog and release-note entry files. |
| review | `22507f6e` | The repository refusal tells an already-provisioned store ("nothing to scaffold") from one not yet fetched ("run `tcw provision`"), and names the other components to scaffold; the path test uses spellings that writing back would change. |

## Tests

- `tests/test_init_configured_tree_path.py`, 8 tests: criteria 1–5, both
  components at once, linked-worktree anchoring, and at review the
  several-components hint and the already-provisioned refusal (a real
  `tcw provision` of a local-path remote, then `tcw taxonomy init`).
- Mutation-checked at review: dropping the "read from config" mark (so init
  writes the path back) turns both path-spelling tests red; making the
  provisioned check always fail turns the provisioned test red.
- Full suite: see `refined-outcome.md`.
- Hands-on: the spec's reproduction, run before review — `tcw taxonomy init`
  built `knowledge/terms`, `tcw taxonomy list` exited 0, the config was
  unchanged.

## What the plan or spec got wrong

- **Provisioned stores were not considered after provisioning.** The refusal
  said "run `tcw provision`" even when that had already succeeded, a loop found
  by review. Fixed; the criterion-5 wording still holds for the unprovisioned
  case.
- **The first "not written back" test could not fail:** `knowledge/terms`
  survives a round trip through `Path` unchanged.

## Autonomous decisions

- **Honor the configured path in `init`, or only reword the refusal? (spec)**
  Codex: honor it, with a guard against scaffolding over a declared
  repository, and anchor paths the way the readers do. Opus: the same, and also
  suggested passing the resolver's underlying reason through the "run
  `tcw init`" advice. Chose honor-plus-guard with reader anchoring; the reason
  pass-through was left as a non-goal (the advice becomes true once `init`
  honors the path).
- Review (adversarial-code-reviewer, "merge after fixes"): accepted findings 1
  and 2. Finding 3 (a malformed `repository:` value gets the provision advice)
  is now answered by the resolver's own message in the unprovisioned branch.
  Findings 4–6 (explicit `--taxonomy-path` not anchored in a worktree; a
  symlinked root skipping re-anchoring; an absolute path outside any
  repository) predate this change and were left out, as the reviewer
  classified them.
- The reviewer's question — should `tcw init` of every component refuse
  outright when one declares a repository? — answered yes: refusing before any
  write is the rule `init` follows for every other problem, and the message
  now names the command for the rest.
