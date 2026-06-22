# Spec — Taxonomy skill + per-component init bootstrap, with an `extends` CLI

## Summary

Three gaps, one feature set:

1. **No `tcw-taxonomy` skill.** The `tcw taxonomy` CLI exists but has no driving
   skill, so agents have no taught judgment for the nouns axis (the peer skills
   `tcw-capabilities` / `tcw-work` exist). Add a thin-router skill, including a
   brief statement of *what the taxonomy module is and what it's for*.
2. **No agent-driven bootstrap.** Adopting TCW on an existing project means
   hand-seeding terms and capabilities. Add a per-component bootstrap workflow —
   the agent deep-dives the codebase, proposes a draft, refines it with the user,
   and writes it via existing `add` commands — exposed as the slash commands
   `/tcw-taxonomy-init` and `/tcw-capabilities-init`.
3. **Taxonomy inheritance is hand-edited.** The `extends` federation map already
   resolves at read time but has no write command (`docs/taxonomy/config.yaml` is
   hand-edited). Add a canonical `tcw taxonomy extends add|rm` command so the
   bootstrap flow (and users) can declare inheritance without hand-editing.

No version cut.

## Motivation

- The taxonomy axis is the one component with a CLI but no skill — agents drive it
  blind. Closing that keeps the three-skill set symmetric.
- Bootstrapping is the single biggest adoption-friction point: a fresh repo has
  empty `docs/taxonomy/` and `docs/capabilities/` trees and no obvious on-ramp.
- `taxonomy#federate-shared-vocabulary` is already a **Partial** capability whose
  only declaration path is hand-editing YAML; a CLI is the obvious completion of
  the "never hand-edit when a command exists" ethos.

## Scope

**In:** the taxonomy skill; the `extends add|rm` CLI + store methods; two
bootstrap sub-docs; two command routers; one gated line in the capabilities
skill; docs sync; capability-ledger deltas.

**Out (non-goals):**
- Remote `extends` sources (git/URL), version-pinning, transitive multi-level
  extends — owned by backlog item `remote-extends-for-taxonomy` (Phase 6).
- `tcw taxonomy extends list` — `tcw taxonomy list` (shows inherited terms by
  origin) and `tcw taxonomy check` (validates the map) already cover visibility.
- A `tcw work`-style bootstrap (work items are created per-change, not seeded).
- Any change to the capabilities/work CLIs.

## Component 1 — `tcw-taxonomy` skill

`skills/tcw-taxonomy/SKILL.md`, a thin router modeled on `tcw-capabilities`.

Frontmatter `name: tcw-taxonomy`; a `description:` that fires when planning/seeding
domain terms or coordinating shared vocabulary, and cross-links the capabilities
and work axes.

Always-inline body (the judgment that isn't obvious from `--help`):

- **What it is / what it's for** (brief): the taxonomy axis is the *nouns* — the
  canonical domain terms a project reasons about. It exists so capabilities and
  work can point at shared, unambiguous concepts instead of re-defining words.
  Terms are referenced *by* capabilities (Subject) and work; the pointers are
  one-directional — taxonomy never points back.
- **Driving the CLI:** read with `list` / `show` / `search`; create with `add`
  (`-s` slug, `-p` parent, inline or piped description); validate with `check`;
  remove a local term with `rm`. Never hand-edit term markdown.
- **Judgment:** one term per distinct concept; a near-synonym or related concept
  is a `relatesTo` link (in `meta.yaml`), not a new term. Nest specializations
  with `--parent`. Keep descriptions short. Run `check` after edits.
- **Inheritance:** declare federation with `tcw taxonomy extends add <alias>
  <repo-path>` (see Component 2); inherited terms appear in `list` flagged by
  origin and qualify as `<alias>/<slug>`.
- **Bootstrap gate (read on demand):** to seed an empty/new taxonomy from an
  existing codebase → read [`docs/init.md`](docs/init.md).
- A quick-reference table including `extends`.

## Component 2 — `tcw taxonomy extends` (the canonical inheritance command)

### Abstract store interface (`TaxonomyStore` in `tcw/store/base.py`)

Add two methods (the operation "declare that this taxonomy extends another store"
is abstract-expressible — passes the litmus test; `ref` is opaque to the
interface, the FS adapter interprets it as a sibling-repo path, a remote adapter
would interpret it as a URL/id):

```python
def extends_add(self, alias: str, ref: str) -> None: ...
def extends_remove(self, alias: str) -> None: ...
```

### Filesystem adapter (`FsTaxonomyStore`)

Realize both by reading/writing the `extends:` map in `docs/taxonomy/config.yaml`
(via the existing `load_yaml` / `dump_yaml` helpers), then staging the file.

`extends_add(alias, ref)` validation — fail-fast, mirroring the rules
`check` already enforces; refuse (raise `ValueError`) on:
- `alias` already present in the map (tell the user to `rm` first),
- the resolved path `node_root / ref / docs/taxonomy` is not a directory,
- direct self-reference (resolved path == this taxonomy root).

`ref` is stored verbatim (relative paths preserved — resolution is relative to the
repo/node root, matching the loader at `fs.py:317`). Full transitive-cycle and
alias/term-collision detection remain `check`'s job (don't duplicate). On success,
print a confirming line naming the alias, the path, and `config.yaml`; suggest
`tcw taxonomy check`.

`extends_remove(alias)`: drop the key; refuse if the alias isn't present.

### CLI (`tcw/taxonomy/cli.py`)

- Add `"extends"` to the module's `SUBCOMMANDS` set (so the `tcw taxonomy <path>`
  show-sugar in `tcw/cli.py:_normalize` does not treat `extends` as a term path).
- Add an `extends` subparser with nested `add` (`alias`, `path`) and `rm`
  (`alias`) sub-subparsers, wired to thin `_extends_add` / `_extends_rm` handlers
  that call the store methods and translate `ValueError` to a `tcw taxonomy
  extends: <msg>` stderr message + exit 1.

### Tests (`tests/`)

pytest over a `tmp_path` git repo (follow existing taxonomy test patterns):
- `extends add` writes the map; the inherited terms then resolve via `list`/`get`.
- `add` refuses: duplicate alias, missing path, missing `docs/taxonomy`, self-ref.
- `rm` removes the key; refuses an absent alias.
- `extends` is recognized as a subcommand (show-sugar doesn't capture it).

## Component 3 — bootstrap sub-docs (read on demand)

Same four-beat shape in each; written to the agent as a procedure, not prose.

### `skills/tcw-taxonomy/docs/init.md`

1. **Ensure the tree exists** — `tcw taxonomy init` if `docs/taxonomy/` is absent.
2. **Inheritance** — ask *"Does this project inherit its taxonomy from other
   repos?"* If yes, collect a list of sibling-repo paths; for each, derive an
   alias from the repo directory name and confirm it; run `tcw taxonomy extends
   add <alias> <path>`. (The doc may also write other `config.yaml` keys directly
   when bootstrapping additional adapter config; `extends` goes through the
   command.) Run `tcw taxonomy check`.
3. **Deep-dive** — survey the codebase for candidate domain nouns (core
   models/entities, ubiquitous-language terms, bounded-context names; skip generic
   framework nouns). Produce a draft forest with one-line descriptions and
   proposed parent nesting.
4. **Refine + write** — present the draft, run a lightweight refine loop with the
   user (add/cut/rename/merge), then write the agreed terms via `tcw taxonomy add`
   (`--parent` for nesting, piped description). Finish with `tcw taxonomy check`.
   *Lightweight inline loop — do **not** invoke `superpowers:brainstorming`.*

### `skills/tcw-capabilities/docs/init.md`

Same shape for capabilities, with two differences:
- **Do taxonomy first** — capabilities reference terms (Subject); if the taxonomy
  is empty, point the user at `/tcw-taxonomy-init` first.
- Deep-dive targets *user stories* (what a user can do): routes/commands/handlers,
  user-facing features. Draft `## <Capability>` headings grouped by namespace,
  each with a status (`Supported` for what already ships, `Missing`/`Partial`
  otherwise). Write via `tcw capabilities add`; set status with `tcw capabilities
  set`.

## Component 4 — command routers

Thin routers matching the existing `commands/tcw-init.md` shape:
- `commands/tcw-taxonomy-init.md` → "read `skills/tcw-taxonomy/docs/init.md` in
  this plugin and follow it; ground every step in the actual repo."
- `commands/tcw-capabilities-init.md` → same, pointing at the capabilities init
  doc.

## Component 5 — capabilities skill update

Add one gated line to `skills/tcw-capabilities/SKILL.md` (introducing progressive
disclosure there, as `tcw-work` already has): a "Bootstrap (read on demand)"
pointer → `docs/init.md`. No other change to that skill's judgment.

## Capability-ledger deltas (dogfood)

Applied as the **first implementation step** (after `tcw work start`), per the
tcw-capabilities planning gate — declared now in this spec, written then:

- **New** `taxonomy#bootstrap-the-taxonomy` (flat file
  `docs/capabilities/taxonomy/bootstrap-the-taxonomy.md`, since `add` cannot
  append a heading to the existing namespace file) — `--status Missing`, with
  `--field "Planning doc=<this work slug>"`. Flips to `Supported` at completion.
- **New** `capabilities#bootstrap-the-capabilities` (flat file under
  `docs/capabilities/capabilities/`) — same treatment.
- **Changed** `taxonomy#federate-shared-vocabulary` — body edit only: the
  declaration path becomes `tcw taxonomy extends add <alias> <path>` (config.yaml
  still valid). **Stays Partial** (remote sources still deferred). Recorded as a
  work→capability back-pointer in this item's `capabilities.yaml`.

## Documentation sync

Per the CLAUDE.md Documentation Sync triggers (fire on this change):
- `README.md` [Public-API] — new `tcw-taxonomy` skill, the two `*-init` commands,
  and the `tcw taxonomy extends` CLI.
- `docs/release-notes/upcoming.md` [Public-API] — plain-language: "bootstrap your
  taxonomy/capabilities from your codebase" + "declare taxonomy inheritance from
  the CLI".
- `docs/changelogs/upcoming.md` [Any-Code-Change] — Added/Changed entries with the
  commit hash range.
- `skills/tcw-taxonomy/SKILL.md` + `skills/tcw-capabilities/SKILL.md`
  [Skill-Driven-Component] — created/updated by this work (Components 1 & 5).

## Testing

- The Component 2 pytest suite above (the only new executable logic).
- `tcw taxonomy check` clean on a repo with a CLI-declared `extends`.
- Manifest guard: confirm no test enumerates the command/skill set that the two
  new commands + skill would break (check `tests/test_plugin_manifests.py`); if it
  does, update it.

## Abstraction litmus

`extends_add` / `extends_remove` pass: declaring federation is an abstract
operation; only the *realization* (a `config.yaml` map of alias→repo-path) is
filesystem-specific, and it lives entirely in the FS adapter. The CLI and skills
speak the abstract operation.
