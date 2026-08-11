# Plan: make the TCW marketplace syncable from the claude.ai web app

Six code tasks, then a documentation block. The ordering constraint that drives
everything: **T4 must not precede T3**, because removing `norecursedirs` while
`plugins/tcw` still exists makes pytest collection recurse infinitely. Every
other boundary is green in both directions.

No blockers. Nothing in the backlog gates this item and it gates nothing, so
there is no `tcw work edit --blocked-by` to record.

## T1 — manifest metadata (no behavior change)

**Changes**

- `.claude-plugin/marketplace.json` — add top-level `description`; add
  `owner.email` = `brocef@users.noreply.github.com` (keep `owner.name`); add a
  per-plugin `author` with the same name and email; add `category`
  (`"Developer Tools"`, matching `.codex-plugin/plugin.json`) and `keywords`
  (mirroring the six in `.claude-plugin/plugin.json`) to the plugin entry.
- `.claude-plugin/plugin.json` — add `homepage` and `repository`
  (`https://github.com/brocef/TCW`, matching the Codex twin) and
  `license: "Apache-2.0"` (matching `LICENSE`).
- `.agents/plugins/marketplace.json` — add a top-level `description` and a
  `description` on the plugin entry. Add **no** version field.

**Verify** — `claude plugin validate .` exits 0 with zero warnings (AC-3;
today it emits one). `pytest tests/` green — nothing here touches the symlink,
so `test_symlink_points_at_repo_root` still passes. Version fields untouched, so
`test_plugin_manifests.py`'s 5-file agreement check is unaffected.

First because it is the only task with no ordering constraint at all, and it
lands AC-3 before anything riskier moves.

## T2 — the tests that survive the layout change

**Changes** — in `tests/test_plugin_manifests.py`, add three tests:

- **marketplace completeness** — `.claude-plugin/marketplace.json` has a
  non-empty top-level `description`, an `owner` carrying both `name` and
  `email`, and a plugin entry with an `author`.
- **manifest consistency** — `.claude-plugin/plugin.json` and
  `.codex-plugin/plugin.json` agree on `homepage`, `repository`, and `license`.
- **agents source path resolves** — the `path` in
  `.agents/plugins/marketplace.json`'s plugin `source`, joined to the repo root,
  is an existing directory.

**Verify** — `pytest tests/test_plugin_manifests.py` green.

Deliberately before T3: all three are written to be **layout-agnostic**. The
path test passes against `./plugins/tcw` today and against `"."` tomorrow, so it
is real coverage across the risky change rather than a test authored to match
the outcome. If any of these fails here, T1 was wrong and T3 has not run yet.

## T3 — remove the self-symlink (the risky one, isolated)

**Changes** — one atomic commit:

- `git rm plugins/tcw` (the `plugins/` directory goes with it).
- `.agents/plugins/marketplace.json` — plugin `source.path` → `"."`.
- `tests/test_plugin_manifests.py` — replace `test_symlink_points_at_repo_root`
  (`:95-98`) with its inverse: no tracked path is a symlink whose target
  resolves to an ancestor of itself. Enumerate via `git ls-files -s` and check
  mode `120000` entries, so the assertion covers the **class** and a future
  `plugins/<x> → ..` cannot reappear.

**Why one commit** — deleting the symlink while the old test still asserts its
existence leaves the suite red; splitting them is a broken boundary, not two
tasks.

**Verify** — `pytest tests/` green. `git ls-tree -r HEAD | awk '$1=="120000"'`
lists `CLAUDE.md` only (AC-1). T2's path test still passes, now against `"."` —
that transition is the point of writing it first.

## T4 — retire the workarounds the symlink justified

**Changes**

- `pyproject.toml:31` — drop `"plugins"` from `norecursedirs`; delete the
  explaining comment at `:28-29`. Keep `.venv`, `build`, `dist`, `*.egg-info`.
- `pyproject.toml:22` — delete `exclude = ["plugins*"]`, redundant with
  `include = ["tcw*"]` at `:21`.
- `tests/test_documented_cli_surface.py:44-56` — delete the third reason from
  the docstring (the symlink clause). **Do not touch the implementation** —
  `git ls-files` stays; its other two reasons are independently sufficient.

**Verify** — `pytest tests/` green and, specifically, collection terminates:
with `plugins/` gone there is nothing to recurse into, but a hang here is the
failure mode this ordering exists to prevent. `python -m build` (or
`pip install -e .`) still produces a wheel containing only `tcw*` packages,
confirming the `exclude` really was redundant.

**Must follow T3.** Reversed, pytest collection recurses forever.

## T5 — end-to-end packaging verification

**Changes** — none. This is a verification task with no diff.

**Verify**

```bash
# AC-2 — Codex, scratch clone, isolated CODEX_HOME
git clone . /tmp/tcw-ac2 && export CODEX_HOME=$(mktemp -d)
codex plugin marketplace add /tmp/tcw-ac2      # → Added marketplace `tcw`
codex plugin add tcw@tcw                       # → Added plugin `tcw`
ls "$CODEX_HOME"/plugins/cache/tcw/tcw/*/skills | wc -l   # → 8
# installed version must equal pyproject's, read not hard-coded

# AC-4 — Claude CLI still fine
CLAUDE_CONFIG_DIR=$(mktemp -d) claude plugin marketplace add https://github.com/brocef/TCW

# AC-6 — no stale references
grep -rn "plugins/tcw" --include='*.py' --include='*.toml' --include='*.json' .
# → nothing outside docs/changelogs/
```

Separate from T3/T4 because it exercises the *published* shape through two real
CLIs, which is a different claim than "the suite is green".

## T6 — changelog (fires unconditionally)

**Changes** — `docs/changelogs/upcoming.md` [Any-Code-Change]. Technical,
grouped: **Removed** the `plugins/tcw` self-symlink and the `plugins/`
directory; **Changed** the Codex marketplace to address the plugin root-relatively
and the four manifests' metadata; **Internal** the `norecursedirs`/`exclude`
retirement, the docstring correction, and the four test changes. Record that the
symlink's removal was measured equivalent for Codex packaging, so a future
reader does not re-derive it.

**Verify** — entry exists, names every changed file, and claims nothing about
web sync.

## AC-7 gate — everything below waits for the user

`documentation-sync` predicts three more triggers, and **all three are gated on
AC-7, which the user runs at `verify`, not during `implement`.** They cannot be
written in the implementation pass:

- `docs/release-notes/upcoming.md` [Public-API] — plain-language note that the
  plugin can be added from the web/desktop plugin directory.
- `README.md` [Public-API] — `README.md:96-131` documents the CLI install only;
  adding a web-directory line is a genuine user-facing addition.
- the `plugin/install-as-a-plugin` capability body — the clause distinguishing
  the CLI from the web/desktop directory, plus its `capabilities.yaml`
  `changed:` entry, applied at `complete`.

**If AC-7 passes**, all three land. **If AC-7 fails**, none of them do: the
changelog from T6 stands alone, `verify` records that the diagnosis was not
confirmed, and the fork probe (`obra/superpowers` → the user's account) becomes
the follow-up item. Writing any of the three on the strength of T1–T6 would
publish a claim nothing verified.

## Documentation Sync evaluation

| Entry | Trigger | Fires | Task |
| --- | --- | --- | --- |
| `docs/changelogs/upcoming.md` | `[Any-Code-Change]` | yes | **T6** |
| `docs/release-notes/upcoming.md` | `[Public-API]` | only if AC-7 passes | AC-7 gate |
| `README.md` | `[Public-API]` | only if AC-7 passes | AC-7 gate |
| `skills/<component>/SKILL.md` | `[Skill-Driven-Component]` | no | — |

`skills/` does not fire: no component's CLI surface, model/fields, lifecycle, or
guardrails change. Re-evaluate all four against the finished diff at
`stage-implement.md` step 6 rather than trusting this table.

## Verification

What the suite covers: AC-1 (T3), AC-3 (T1), AC-5 (T1–T4), and the manifest
shape (T2).

What it cannot cover, and why:

- **AC-2 and AC-4** need two real CLIs and network/filesystem state outside
  pytest. T5 runs them by hand. They could be automated later; doing it here
  would be building test infrastructure to verify a packaging change.
- **AC-7 is manual, user-only, and decisive.** No agent can log into the user's
  claude.ai account. Every automatable criterion can pass while AC-7 fails —
  that is not a gap in the plan, it is the shape of the unresolved diagnosis
  (`spec.md` → Risks). The plan's job is to make sure a failed AC-7 is
  *visible* rather than absorbed, which the gate above does by withholding all
  three user-facing artifacts.
- **Nothing here proves which change fixed it**, by design (`spec.md` →
  Non-goals).

## Notes

- T5 asserts the installed version equals `pyproject.toml`'s rather than the
  literal `0.18.2`, so the task does not rot at the next version cut.
- If T1 alone turns AC-3 green *and* the user opts to test the web UI early, a
  passing AC-7 after T1 would isolate metadata as the cause for free. Not
  planned — it costs the user an extra manual test for knowledge no goal needs —
  but the ordering makes it available at no cost if they want it.
- The `.claude/settings.local.json` entry `Bash(ln -s .. plugins/tcw)` becomes
  dead at T3. Untracked and machine-local; out of scope, mentioned so it is not
  read as a missed dependent.
