# Outcome — Override where a connected project lives on this machine

`TCW_PROJECT_<ID>` now says where a connected project sits on this machine, and
is consulted above both the declared locator and the `repository` declaration.
All eight plan tasks shipped. Two of them changed shape against the plan, and
one production behaviour the spec asked for is **not** delivered — see *What the
plan and spec got wrong* and *Deliberately not done*.

## What shipped, task by task

| Task | Commit    | What landed                                                              |
| ---- | --------- | ------------------------------------------------------------------------ |
| 1    | `daf10a7` | `override_variable`; the injectivity cases; the conftest isolation fixture |
| 2    | `bfd6559` | `ProjectOverride` + `ProjectRegistry.overrides()` on the abstract spine    |
| 3    | `7ac2736` | Rule 0 in `_target_path`, with its three outcomes and its memoisation      |
| 4    | `9b474d2` | `tcw validate` reports active overrides, before the problem block          |
| 5    | `276304a` | Tests pinning that provisioning and every command honour it — no new code  |
| 6    | `a913eaf` | The named no-override regression                                          |
| 7    | `04ebd65` | `cli/point-tcw-at-a-project-i-already-have` (`cap-75c7e9`) + the sidecar   |
| 8    | `4ee4fea` | README, release notes, changelog, and one skill reference                  |

The planning artifacts are `9472925` (plan) on top of the two spec commits that
arrived on the `claude/tcw-project-path-overrides` branch, fast-forwarded onto
`main` at the start of this session — the branch had never been merged and had
no pull request.

## Test result

```
1 failed, 2398 passed in 1066.65s (0:17:46)
```

The failure is `test_the_prompts_are_in_the_built_wheel`, and it is **not this
work**. Checked out at `ea11807` — the v1.3.0 release commit, before any of these
changes — it fails identically: `inbox` is present in `tcw/work/prompts/` in the
built wheel and absent from the test's `SHIPPED` set. Recorded here rather than
fixed, because fixing an unrelated packaging assertion inside this item hides it.
It wants its own item.

The pre-work baseline was `1 failed, 2379 passed`, so the 19 tests added here all
pass and nothing regressed.

## Verified by hand, beyond the suite

**Criterion 3, the reproduction from the intake.** Built the flat-sibling
workspace the intake describes — configs written for a nested layout, the
repositories checked out as siblings — in a scratch directory with a local git
remote. With no override, `tcw provision` fetched a second copy and `tcw
validate` reported the two problems the intake quoted, in the same words:

```
…/cache/tcw/stores/…-remote-core-263a2b4c7604/tcw-config.yaml: duplicate project
    id 'proposit-core' also used by …/ws/proposit-core/tcw-config.yaml
…/ws/proposit-orchestration/tcw-config.yaml: child locator for 'proposit-core'
    does not point back to …/ws/proposit-core
2 project graph problem(s).
```

With `TCW_PROJECT_PROPOSIT_CORE` set and the cache cleared, `tcw provision`
printed `proposit-core: already available`, created **no** cache entry, and
`tcw validate` from both nodes printed the override line and `validate OK`, exit
0. Two problems to zero, nothing fetched.

**Verification item 3, the messages read as a person.** The three shapes, run
from `proposit-core`:

- The crossed name — `TCW_PROJECT_PROPOSIT_APP` pointed at the directory
  `proposit-app`, which holds the node `proposit-app-repo`. Output carries the
  override line naming the variable and its target, then `registered key
  'proposit-app' does not match target id 'proposit-app-repo'`. The mistake is
  findable without reading source, which was the thing being checked.
- A directory that is not a node — `…/ws/notes: TCW_PROJECT_PROPOSIT_APP names a
  directory with no tcw-config.yaml`, exit 1.
- A path that is not here — falls through silently, `validate OK`, exit 0, and
  the override is correctly absent from the listed ones.

## What the plan and spec got wrong

- **The plan said the `Skill-Driven-Component` trigger would not fire. It does.**
  `skills/tcw-work/references/commands.md` teaches the connected-project ladder
  in words — "the project at `path` wins when it is here" — and that sentence is
  now incomplete. An agent reading it would tell a user to edit a config when the
  answer is a variable. The trigger fires on the guardrail a skill teaches, not
  only on a CLI surface, and the plan's Documentation Sync block reasoned from
  the narrower reading. Updated in `4ee4fea`.
- **The spec put the `tcw validate` reporting beside the `misdirected()` line.**
  `_cmd_validate` returns from inside the problem block above it, so a line
  printed there never appears on the run where a wrong override is being
  diagnosed — which is the run the reporting exists for. Moved above the problem
  block; the ordering is asserted, not just the presence. Recorded in the plan's
  Notes before implementation and confirmed correct by mutation here.
- **The spec's design had the override lookup check the target's id itself.**
  Left to `_read_config`, which already reports the mismatch naming both ids.
  Doing it in both places parses the same file twice to print two messages for
  one cause. Criterion 6 is met by the existing message; the override is recorded
  even when it is wrong so `tcw validate` prints it beside the mismatch.
- **One test passed for the wrong reason and was rewritten.** The empty-variable
  case originally used a whitespace value, which resolves to a nonexistent
  directory whether the guard exists or not — it proved nothing. The real failure
  is that `Path("")` is `Path(".")`, so it now runs from a directory that *is* a
  valid node for that id and fails if the guard goes.
- **A stale `__pycache__` entry cost real time.** A same-size restore after a
  mutation left Python running the mutated bytecode, and a correct test read as
  failing for several minutes. Every mutation check in tasks 1–5 was re-run from
  a cleared cache with `PYTHONDONTWRITEBYTECODE=1`; all seven bite.

## Deliberately not done

**`tcw provision` still fetches when an override is present and wrong.** The
registry refuses — `check()` carries the problem, `require_valid()` raises,
`get()` is None, and nothing falls through to the declaration, which is criterion
5 as written. But `_provision_nodes` decides what to fetch from
`declared_connected_projects`, a raw config read that never consults
`registry.check()`, so `tcw provision` obtains a copy anyway.

Not absorbed silently, and not fixed here. Making provisioning refuse on registry
problems is a wider behaviour change than this item specified —
`_declared_nodes_in_graph` documents deliberately *not* requiring a valid graph,
since completing an incomplete graph is what the command is for — and deciding
which problems should stop it is a spec question. The user-visible effect is
bounded: the failure is loud in `tcw validate`, and what `tcw provision` does is
what it did before this feature existed. Flagged for the verify decision; it
wants a follow-up item if it is wanted at all.

## Second pass — the rework

`rework.md` sent this back on 2026-09-09 over the gap recorded under
*Deliberately not done* below, which the user assigned to this item rather than a
follow-up. That section now describes something that has been fixed; it is left
standing because it is the record of what verification found.

| Task | Commit    | What landed                                                        |
| ---- | --------- | ------------------------------------------------------------------ |
| R1   | `e05c6e7` | `tcw provision` refuses a failed override before contacting anything |
| R2   | `da130aa` | The wheel test builds from a pristine tracked tree                   |
| —    | `7c4d374` | Documentation sync for both                                          |

**R1.** `ProjectOverride` gained a `problem` field, and `_load_graph` now ends
with `_reconcile_overrides`. The test it applies is the outcome rather than a
list of failure modes: an override is satisfied when the graph holds its project,
under its id, at the place it pointed. That covers both shapes with one rule,
which mattered because they are found at different moments — a directory with no
config when the override resolves, a directory holding the wrong node only after
that node's config is read. `run_provision` refuses on any override carrying a
problem, and the gate is failed overrides only, never graph problems at large.

Verified in the reproduction, all four cases: a wrong-node override exits 1 with
`TCW_PROJECT_PROPOSIT_CORE names …/ws/proposit-app, which is 'proposit-app-repo',
not 'proposit-core'` and no cache entry; a not-a-node override exits 1 likewise;
a good override still reports `already available` at exit 0; an absent one still
falls through and fetches. Mutation-checked three ways, including deleting the
`problem` filter so the gate refuses everything, which fails the two tests that
assert a good override and an absent one still work.

**R2, and the diagnosis changed.** `test_the_prompts_are_in_the_built_wheel` was
recorded below as a pre-existing packaging failure. It is not a packaging failure
at all. `tcw/work/prompts/` holds six files and git tracks exactly those six; the
wheel gained a seventh because a stale `build/lib/tcw/work/prompts/inbox.md`
dated 2026-09-02 sat in setuptools' staging directory, which
`pip wheel --no-build-isolation` reuses. `build/` is gitignored, so CI never had
one and this only ever failed on a machine that had built before — a test reading
developer-local state and reporting it as a repository defect, the same class of
problem the `TCW_PROJECT_*` conftest fixture was added for.

It now copies the files `git ls-files` names into `tmp_path` and builds there.
`git ls-files` rather than `git archive HEAD`, so uncommitted edits to tracked
files are still exercised. It passes with the stale `inbox.md` still in `build/`,
and still goes red when package data is genuinely missing — emptying `tcw.work`'s
`package-data` in `pyproject.toml` fails it.

## Notes

- Provisioning needed no code change for the *working* case. `_provision_nodes`
  asks the registry where each project is, so rule 0 reached it for free. That
  was a design claim in the spec; it is a test now.
- The current node's own id is not overridable — `_target_path` runs for declared
  edges only, and you are standing in the current node. Correct, and not stated
  anywhere, so it is stated here.
- A relative value resolves against the process's working directory, the only
  path in `project.py` that does. A locator lives in a file and means "relative
  to that file"; a variable lives in a shell.
- The spec's Non-goals hold. No per-machine config file, no `work.path` /
  `taxonomy.path` override, no change to the duplicate-id or reciprocity checks.
  `resolve_store`'s matching gap is untouched.
