# Outcome: check capabilities.yaml paths while an item is still being worked

## What shipped

- **Code** — `37407efc`: `capability_gate(st, item, *, in_progress=False)`
  (`tcw/work/recursion.py`). With `in_progress=True` it drops the checks only true
  at completion (`new` still `Missing`, `removed` still resolving), skips an
  unresolved `new:` path while the item is in backlog, and returns nothing when
  the ledger or registry cannot open (validate reports that once elsewhere).
  `tcw/validate.py` gains `_open_sidecar_problems`, run on whole-node validates and
  on a work-item target, for items in backlog, active and review — never
  completed or discarded — each problem as `<sidecar>:<line>: <problem>`.
  The completion gate (`in_progress=False`) is unchanged.
- **Docs** — `a7970994`: `docs/guide/linking-and-validation.md`,
  `skills/capabilities/SKILL.md`, changelog, release notes.
- **Review fold-in** — `f12fbcd0`: the line number is the line that lists the
  path (`_listed_paths`: a `- path` item or a `[a, b]` flow list), never a
  comment or a longer path containing it; the pass is skipped after a YAML syntax
  problem, so a broken sidecar is reported once; the docstring describes
  `in_progress`; the skill says "active or in review"; the guide names the
  removed-inherited check.

## Tests

- `tests/test_sidecar_paths_in_validate.py` (11). The first five failed on main
  for the stated reason. Of the fold-in's tests, the line-number and
  reported-once tests failed on the commit before it; `new` in review failed
  when the status condition was mutated to `!= "active"`; the wrong-shape and
  work-target tests guard behaviour the first commit already had.
- Full suite on the final code: see `refined-outcome.md`.
- Hands-on with the worktree's `tcw` in a scratch node: a sidecar with a comment
  naming `shared/auth/login`, `new: [shared/auth/login]` and
  `changed: [auth/login]` — in backlog, `validate OK`; after `start`,
  `…/capabilities.yaml:3: shared/auth/login: declared (new) but does not
  resolve`, exit 1.
- This repository's own `tcw validate` stays OK (the reviewer ran it with this
  branch's code); no open item here has a `capabilities.yaml` yet.

## What the plan or spec got wrong

- Criterion 5's first test proved nothing — validate's YAML check already
  reported a syntax-broken sidecar. Replaced by a wrong-shape sidecar (parses,
  but `new:` is not a list), which only this pass catches, and a test that the
  syntax-broken one is reported once.
- The spec's non-goal "the first line naming the path" was the wrong rule; it
  matched comments and longer paths. Now the line that lists the path.
- GitHub #27's example (`shared/…`) is not a routing failure when the node has
  its own ledger: routing treats an unknown prefix as a local path. It is caught
  as "does not resolve" instead — for `new:` only once the item is active.

## Documentation Sync

| Entry | Fired? | Done |
| --- | --- | --- |
| `README.md` | Checked, no | Does not list what validate checks. |
| `docs/guide/jira.md` | No | — |
| `docs/guide/<topic>.md` | Yes | `linking-and-validation.md`. |
| `docs/release-notes/upcoming.md` | Yes | One line. |
| `docs/changelogs/upcoming.md` | Yes | One Added entry. |
| `skills/<component>/SKILL.md` | Yes | `skills/capabilities/SKILL.md`. |
| `skills/configure/references/` | No | — |

## Autonomous decisions

Run unattended on 2026-09-26 (`extras-autonomous-work`).

- **Where, which statuses, which checks, the shorthand?** Both advisors: in
  `tcw validate` above the stores (not `FsWorkStore.check`), review included,
  the `shared/` shorthand left to its own item (filed as
  `2026-09-26-decide-whether-a-capability-path-may-name-a-connected-project-by-an-unambiguous-shorthand`).
  Codex also corrected my claim that unknown prefixes fail routing (they do not;
  see above). Chose all of it.
- **Report an unresolved `new:` path mid-work?** Codex: no, the planning
  guidance is inconsistent about when a new capability is created. Opus: yes in
  active and review, no in backlog — the capabilities skill seeds it as
  `Missing` at planning, so by implementation it exists. Chose Opus's split: it
  is what the skill tells an agent to do, and backlog is exempt for the case
  Codex raised.
- **Code review** (adversarial-code-reviewer): NOT DONE — wrong line numbers,
  a double report, a test that proved nothing, missing tests. All fixed above.
  Not filed, recorded here: a stale copy of another item's sidecar in the
  primary checkout, while that item is worked in a worktree, could name a `new:`
  capability main's ledger lacks and so fail validate — and therefore every
  `complete` — until merged. The reviewer marked it suspected and dependent on
  seeding a capability inside a worktree rather than at planning; the message
  names the file, and the same risk already applies to every validate problem.
- **Verify** (tcw:verifier): accept in substance; all seven criteria met on the
  branch by hand and in tests (line numbers, each status, routing and
  inherited-removal messages). It asked for the `tcw/validate.py` conflict with
  main to be resolved and the suite re-run: resolved (this pass, then main's
  rewritten step (d)), full suite re-run on the merged code. It also noted that
  one YAML syntax error anywhere hides every sidecar problem until fixed — the
  same rule as the component checks, kept. Decision: accept.
