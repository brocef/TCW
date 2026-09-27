# Outcome: resolve sibling nodes to their worktree copies

## What shipped

- **Code** — `2528fc87`: Rule 2 of `ProjectRegistry._locator_path`
  (`tcw/store/project.py`) aliased only the current node's main-checkout path
  onto the worktree. It now aliases any config path under the main worktree
  (not already inside this worktree) whose counterpart under this worktree
  exists; `_counterpart_path` is gone.
- **Review fold-in** — `31419ef0`, `96d3715f`: the redirect is one helper,
  `_worktree_copy`, applied to `repository:` declarations as well as locators;
  it never crosses into a separate repository nested in the worktree, but does
  follow a submodule of this repository (`_same_repository`: a `.git` file
  pointing into the main repository's git directory).
- **Docs**: `docs/guide/multi-repo.md`, changelog, release notes.

## Tests

- `tests/test_worktree_sibling_nodes.py` (9) with real repositories and
  `git worktree add`: 5 of the first 6 failed on main; the `repository:`,
  nested-repository and submodule tests each failed on the commit before them;
  the primary-only-node test fails when the file-exists check is removed.
- Full suite on the final code: 4631 passed, 3 skipped.
- Hands-on with the worktree's `tcw`, the issue's layout: `tcw validate` from
  `app-wt/pkg-a`, `app-wt/pkg-b` and `app-wt` — `validate OK` each (four
  problems from `pkg-a` on main).

## What the plan or spec got wrong

- The spec covered locators only; a child declared by `repository:` reached the
  same bug.
- "A config exists at the copy" is not "the same node": a separate clone nested
  at the same place would have been taken for it. Restricted to the same
  repository, then widened to its submodules.

## Documentation Sync

| Entry | Fired? | Done |
| --- | --- | --- |
| `README.md` | Checked, no | — |
| `docs/guide/jira.md` | No | — |
| `docs/guide/<topic>.md` | Yes | `multi-repo.md`, the linked-worktree section. |
| `docs/release-notes/upcoming.md` | Yes | One line. |
| `docs/changelogs/upcoming.md` | Yes | One Fixed entry. |
| `skills/<component>/SKILL.md` | Checked, no | — |
| `skills/configure/references/` | Checked, no | — |

## Autonomous decisions

Run unattended on 2026-09-27 (`extras-autonomous-work`).

- **No advisor consult**: the issue named the cause and the fix, and no open
  question remained in the spec; review stood in as the second opinion.
- **Code review** round 1: DONE with findings — the `repository:` route, nested
  clones, a weak test; all folded in. Round 2: DONE on condition that submodules
  be decided; decided to follow them (their worktree checkout is the commit the
  branch pins), with a test that fails without it. Not done, as the reviewer
  split them: an absolute locator spelled with different letter case loads a
  node twice; running from a node whose own config is a symlink fails even in
  the primary checkout; whether a `TCW_PROJECT_<ID>` override naming the main
  checkout's copy should be redirected.
- **The request** was overwritten by the run and restored from git (`ebf452be`).
- **Verify** (tcw:verifier): all five criteria met, each compared with main's
  build (4/4/8 problems on main from `pkg-a`/`pkg-b`/root; none on the branch),
  in both the sibling and the `.worktrees/<name>` layouts, and for
  `repository:`, a nested clone and a submodule. It found two submodule layouts
  still uncovered (running from inside a submodule's own checkout; a repository
  that is itself a submodule) — both predate this item; the guide now says so,
  and they are on the project-graph follow-up. Decision: accept.
