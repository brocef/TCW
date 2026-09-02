# Plan: Generate a role-specific AGENTS.md from configured role definitions

Thirteen tasks. Tasks 1–10 build the mechanism bottom-up and leave the suite
green at every boundary; task 11 migrates this repository onto it; task 12
confirms the third-party preset paths; task 13 is the Documentation Sync block.

**Module layout.** A new `tcw/agents/` package: `config.py` (pure parser),
`fragments.py` (loading and merging), `render.py` (substitution and fragment
resolution), `role.py` (selection and persistence), `targets.py` (writing),
`cli.py` (the command group). `[tool.setuptools.packages.find]` uses
`include = ["tcw*"]` (`pyproject.toml:29-30`), so the package needs no packaging
change; no new package data ships.

**A deliberate import direction.** `tcw/agents/` imports from
`tcw/work/resolve.py` and `tcw/work/generate.py`. That reads as backwards — an
agents package depending on the work package — and it is chosen anyway.
`tcw/work/resolve.py`'s own docstring calls it "a library, not a command", it
already serves three callers, and the alternative is to move it to a new
top-level module, touching every existing caller to spare one import. The spec's
promise is to reuse this machinery rather than reimplement it, and reuse is the
part that matters. Task 1 makes the two helpers it needs public rather than
reaching across a package for underscore-prefixed names.

---

## Task 1 — Make the two path helpers public

**Modifies:** `tcw/work/resolve.py`

Rename `_confined` → `confined` (`tcw/work/resolve.py:107`) and `_read_file` →
`read_confined_file` (`:124`), updating every internal call site. Both are
module-private today with no external contract, so this is a rename, not an API
change. Add one line to each docstring naming the second caller, so the next
reader knows why they are public.

**Proves it:** `grep -rn "_confined\|_read_file" tcw/ tests/` returns nothing,
and `pytest tests/test_resolve.py tests/test_lifecycle_hooks.py
tests/test_generate_hook.py tests/test_scaffold.py` is green.

---

## Task 2 — Configuration model and pure parser

**Creates:** `tcw/agents/__init__.py`, `tcw/agents/config.py`,
`tests/test_agents_config.py`

`config.py` defines frozen dataclasses `RoleSpec` (`name`, `template`),
`TargetSpec` (`path`, `mode`), and `AgentsConfig` (`roles`, `fragment_files`,
`overlay`, `default_role`, `targets`, `timeout`, `output_cap`), plus
`TARGET_PRESETS` and `parse_agents_config(raw) -> tuple[AgentsConfig, list[str]]`.

`timeout` and `output_cap` come from new `agents.timeout` / `agents.output-cap`
keys defaulting to `DEFAULT_HOOK_TIMEOUT` and `DEFAULT_OUTPUT_CAP`
(`tcw/store/base.py:837`, `:615`) — the same constants `LifecyclePolicy` uses
(`:808-809`). Own keys rather than reading `work.lifecycle.timeout`, because a
project tightening its lifecycle budget has not said anything about how long its
guide fragments may take.

The parser follows `parse_lifecycle_policy`'s contract exactly
(`tcw/store/base.py:1347`): pure, never raises, never touches the filesystem,
returns problems as strings naming the offending config path. It reports the
shape faults from the spec's **Validation** list that need no disk access — a
non-mapping `agents`, an unknown top-level key, absent or empty `roles`, a role
without a `template`, an unknown fragment value key, an unknown target preset, a
`targets` list whose first entry is `mode: link`, and a `default-role` naming no
declared role. Path existence is a separate concern and belongs to task 9.

**Proves it:** `tests/test_agents_config.py` asserts one problem per malformed
shape above (message names the config path), that a well-formed block parses to
the expected `AgentsConfig`, that defaults apply when optional keys are absent,
and that the parser raises nothing for any input including `None`, a list, and a
string. Covers **AC16** (shape half).

---

## Task 3 — Fragment loading, merging, and the overlay

**Creates:** `tcw/agents/fragments.py`, `tests/test_agents_fragments.py`

`load_fragments(node_root, config) -> tuple[dict[str, Binding], set[str],
list[str]]` — the fragments, the names the overlay supplied, and problems.

Each declared file is resolved through `confined` (task 1), loaded with
`load_yaml(..., unique=True)` (`tcw/store/fs.py`, already used by
`tcw/validate.py:176`) so a duplicate key *within* one file is caught too, and
must be a mapping. Values become `Binding` (`tcw/store/base.py:667`): a bare
string is `Binding(kind="blob", value=<string, unstripped>)`; `{blob: …}`,
`{file: …}` and `{generate: …}` map to their kinds; anything else is a problem.
Blob text is not stripped, matching `_parse_binding`'s rule that stripping a
blob silently edits it (`tcw/store/base.py:1069`).

A key defined in two *declared* files is a problem naming the key and both
paths. The overlay is loaded last and its keys replace silently — that is its
purpose — with every replaced name returned so task 7 can name them in the
provenance header. An absent overlay file is never a problem; an overlay that
exists but is malformed is.

**Proves it:** `tests/test_agents_fragments.py` covers a bare string becoming a
`blob` binding with surrounding whitespace intact; each explicit kind; an
unknown value key reported; a duplicate across two declared files reported with
both paths (**AC10**); the overlay overriding a declared key and appearing in the
returned override set (**AC11**); an absent overlay being silent; a malformed
overlay reported; a fragment file that is a list rather than a mapping reported.

---

## Task 4 — Template substitution

**Creates:** `tcw/agents/render.py`, `tests/test_agents_render.py`

`substitute_fragments(text, resolved, *, template) -> str`, modeled on
`substitute_documentation` (`tcw/work/resolve.py:237`) and reusing its
indentation rule: continuation lines are indented to the token's column, and a
blank line is never indented.

- Tokens are `{{name}}`; `name` matches `[A-Za-z0-9_-]+`. A `{{` with no closing
  `}}` is left verbatim, as `substitute_documentation` already does for an
  unterminated span — malformed input should look wrong, not swallow the rest.
- An unknown name raises `AgentsError` naming the token, the template path, and
  the declared fragment names, sorted.
- **One pass.** Substituted text is never rescanned; the implementation walks the
  source string and appends resolved text to an output list rather than
  re-running `.replace()` over a growing result.

**Proves it:** `tests/test_agents_render.py` covers an unknown token raising with
all three facts in the message (**AC7**); a fragment whose own text contains
`{{other}}` rendering literally (**AC8**); a multi-line fragment on a line
indented four spaces emerging with every continuation line at that column, and a
blank line inside it left at column 0 (**AC9**); two templates sharing one
fragment producing byte-identical text for it (**AC2**); an unterminated `{{`
surviving verbatim.

---

## Task 5 — Fragment value resolution

**Modifies:** `tcw/agents/render.py`, `tcw/work/generate.py`
**Creates:** `tests/test_agents_generate_fragment.py`

`render_role(node_root, config, role, fragments, *, env) -> str` resolves each
fragment referenced by the role's template and then calls
`substitute_fragments`. Only referenced fragments are resolved, so an unused
`generate:` fragment costs nothing to run.

- `blob` → its value.
- `file` → `read_confined_file` (task 1).
- `generate` → `run_generate` (`tcw/work/generate.py:96`) with
  `hook_payload(None, (), …)` (`tcw/work/resolve.py:146-172`), which already
  emits `"item": null` for a `None` item. Environment is the caller's plus
  `TCW_NODE_ROOT`, `TCW_HOOK_ROLE="fragment"`, `TCW_HOOK_KIND="generate"`,
  `TCW_HOOK_ID=<fragment name>`, `TCW_HOOK_PHASE="agents"`, and
  `TCW_AGENTS_ROLE=<role>`.

`run_generate`'s cap and timeout messages name `work.lifecycle.output-cap` and
`work.lifecycle.timeout` as literal strings (`tcw/work/generate.py:180`, `:184`).
Add a keyword-only `config_prefix: str = "work.lifecycle"` parameter and
interpolate it, so an agents fragment's failure names `agents.output-cap` and
`agents.timeout`. Without this the error sends the reader to a key that does not
control it.

Resolution is all-or-nothing: every fragment resolves before anything is
rendered, so a failing generator cannot leave a half-written guide.

**Proves it:** `tests/test_agents_generate_fragment.py` covers all three kinds
rendering; a `generate:` script asserting on its stdin JSON having `item: null`
and on `TCW_AGENTS_ROLE` (**AC5**); a script exceeding the cap and one exceeding
the timeout each failing with a message naming `agents.output-cap` /
`agents.timeout`, with no file written (**AC6**); a `file:` fragment pointing
outside the node root, directly and through a symlink inside it, refused
(**AC17**). Existing `tests/test_generate_hook.py` stays green, pinning the
default prefix.

---

## Task 6 — Role resolution and persistence

**Creates:** `tcw/agents/role.py`, `tests/test_agents_role.py`

`ROLE_FILE = ".tcw/role"`. `read_persisted_role(node_root)`,
`write_persisted_role(node_root, role)` (creating `.tcw/`), and
`resolve_role(node_root, config, *, explicit, env, stdin) -> tuple[str, bool]`
returning the role and whether it should be persisted.

Precedence, first hit wins: `explicit` (the `--role` flag) · `TCW_AGENTS_ROLE` ·
the persisted role · an interactive prompt · `agents.default-role` · raise
`AgentsError` naming every declared role and `--role`.

The prompt is reached **only** when `stdin.isatty()` is true. `tcw/stdin.py:3-8`
records why: a non-terminal stdin is not the same as a pipe carrying data, and a
blocking read on an inherited descriptor strands an automated caller instead of
failing it. `stdin` is injected rather than read from `sys` so the test can pass
a fake without a pty. A role named by flag or env that is not declared raises
before anything is persisted.

`tcw agents generate` reads no piped intake and must not call
`read_piped_stdin()` — `tcw/stdin.py:22-25` states that module owns descriptor 0.

**Proves it:** `tests/test_agents_role.py` covers each precedence step in
isolation and in combination; a non-TTY stdin with a `default-role` returning the
default, and without one raising a message naming every declared role (**AC12**);
a fake TTY returning the typed answer, and an unrecognized answer re-prompting
rather than accepting; persistence round-tripping and `.tcw/` being created
(**AC13**); an undeclared explicit role raising with nothing written.

---

## Task 7 — Targets, writing, and the provenance header

**Creates:** `tcw/agents/targets.py`, `tests/test_agents_targets.py`

`TARGET_PRESETS` maps `agents|claude|gemini|copilot|cursor` to `(path, mode)`.
`resolve_targets(config)` expands presets and mappings into `TargetSpec`s and
identifies the primary — the first `mode: file`.

`provenance_header(role, overridden) -> str` returns the HTML comment from the
spec: role name, the regenerate instruction, and the overlay-supplied fragment
names (or `none`). No timestamp and no hash, so a re-render is byte-identical
and `--dry-run` is comparable to what is on disk.

`write_targets(node_root, text, targets, *, dry_run) -> list[str]` creates parent
directories, writes the primary, and for each `link` target creates a relative
symlink to the primary — replacing an existing file or link at that path. A
symlink that cannot be created (`OSError`, including Windows without developer
mode) falls back to writing a copy and records that in the returned report; it is
not a failure. Finally `ensure_ignored(node_root, …)` (`tcw/store/fs.py:592`)
adds a rule for every target path and for `.tcw/`, which appends only the lines
`.gitignore` lacks and leaves a rule the user deleted on purpose deleted.

**Proves it:** `tests/test_agents_targets.py` covers default targets producing
`AGENTS.md` as a regular file and `CLAUDE.md` as a symlink to it (**AC3**);
`os.symlink` monkeypatched to raise `OSError` producing a copy with identical
content, a report saying so, and no exception (**AC4**); `.gitignore` gaining a
rule per target plus `.tcw/`, and a second run adding nothing (**AC14**); a
`link` target replacing a pre-existing regular file; preset expansion and the
primary being the first `file` target; the header naming overridden fragments and
`none` when there are none.

---

## Task 8 — The `tcw agents` command group

**Creates:** `tcw/agents/cli.py`, `tests/test_agents_cli.py`,
`tests/cli/scenarios/15-agent-guide-generation.md`
**Modifies:** `tcw/cli.py`

`cli.py` follows `tcw/work/cli.py:33-37`'s module contract: `NAME = "agents"`,
`SUBCOMMANDS = {"generate", "show", "roles", "role"}`, `DEFAULT_SUBCOMMAND =
None`, `add_subparser(sub)`. Flags per the spec: `generate [--role R]
[--no-save] [--dry-run]`, `show [--role R]`, `roles`, `role [<name>]`.

In `tcw/cli.py`, import the module and append it to `_BUILT`
(`tcw/cli.py:34`). **Do not** add `agents` to `COMPONENTS` or
`PROVISION_COMPONENTS` — it has no store, so `tcw init` and `tcw provision` must
not offer it, and `_STUBBED` (`:35`) is derived from `COMPONENTS` and is
unaffected. `_normalize` (`:271`) reads `DEFAULT_SUBCOMMAND` and skips a module
whose value is `None`, so `tcw agents <thing>` stays an argparse error rather
than becoming a `show`.

Stream discipline per `tests/cli/README.md`: `tcw agents role` and
`tcw agents show` print only their payload on stdout; every progress and
fallback message goes to stderr.

The scenario document is prose, matching the current state of `tests/cli/` —
`scenarios/*.md` exist, the `.sh` scripts do not yet. It covers what only a shell
test can: `tcw agents` in `tcw --help`, exit codes, `</dev/null` stdin, the
symlink fallback, and `git status --porcelain` staying clean after a generate.

**Proves it:** `tests/test_agents_cli.py` drives `tcw.cli.main([...])`
in-process: `main(["agents", "generate", "--role", "x"])` writing every target
and returning 0; `--dry-run` writing nothing and reporting no changes on two
consecutive runs against an up-to-date tree (**AC15**); `--role` persisting and a
bare re-run reusing it, with `--no-save` leaving `.tcw/role` untouched
(**AC13**); `roles` listing declared roles and marking the persisted and default
ones; a missing `agents:` block exiting non-zero with a message naming the
config key. `tcw --help` containing `agents` is **AC1**.

---

## Task 9 — `tcw validate` covers the agent-guide configuration

**Modifies:** `tcw/validate.py`
**Creates:** `tests/test_agents_validation.py`

Add a node-configuration pass that runs only for a whole-node validation — when
both `path` and `target` are `None`. That is the same scoping
`lifecycle_problems` and `documentation_problems` already have
(`tcw/store/fs.py:4083-4086`, guarded by `identifier is None`), and it is right
for the same reason: `agents:` has no store tree, so `_scan_roots` and
`_components_to_check` (`tcw/validate.py:62`, `:77`) cannot select it by path.

The pass runs `parse_agents_config` (task 2) and then the checks that need the
disk: each role `template` exists and resolves inside the node; each fragment
file exists, is readable, and is a mapping; each `file:` fragment resolves inside
the node; no duplicate key across declared files; every token in every template
names a declared fragment; and every declared fragment is referenced by at least
one template. Problems are prefixed `agents:` and name the offender.

Token and fragment checks are static — no `generate:` script is executed.
Validation must not run a project's shell.

**Proves it:** `tests/test_agents_validation.py` builds a node per fault and
asserts the problem is reported and names the offender, covering every entry in
the spec's **Validation** list, plus a clean node reporting none (**AC16**), and a
template or fragment path escaping the node root through an inner symlink being
refused (**AC17**). One test asserts a node whose only fault is an unreferenced
fragment still *generates* successfully — validate reports it, generate does not
refuse it.

---

## Task 10 — Confirm the third-party preset paths

**Modifies:** `tcw/agents/targets.py`, `tests/test_agents_targets.py`

The spec's Notes record that the `cursor`, `copilot` and `gemini` paths came from
general knowledge and were not verified. Check each against that vendor's current
published documentation and record the source in a comment beside the table.
**Any preset that cannot be confirmed is deleted**, not shipped on a guess — the
mapping form accepts any path, so a missing preset costs a config line and a
wrong one silently writes a file no tool reads. If a preset is dropped, remove it
from the README table in task 13 too.

**Proves it:** every remaining entry in `TARGET_PRESETS` carries a comment citing
where its path was confirmed, and `tests/test_agents_targets.py` asserts the
table's exact contents so a later edit is deliberate.

---

## Task 11 — Migrate this repository's own guide

**Creates:** `docs/agents/common.yaml`, `docs/agents/release.yaml`,
`docs/agents/contributor.md`, `docs/agents/maintainer.md`,
`tests/test_repo_agent_guide.py`
**Modifies:** `tcw-config.yaml`, `.gitignore`, `scripts/remote_session_setup.sh`,
`tests/test_repo_lifecycle.py`, `tests/test_documentation_sync_wiring.py`,
`tests/test_remote_session_setup.py`
**Untracks:** `AGENTS.md`, `CLAUDE.md` (`git rm --cached`; `CLAUDE.md` is a
tracked symlink today)

The current `AGENTS.md` splits into fragments in `docs/agents/common.yaml` —
`preamble`, `work-planning`, `generic-instructions`, `development-environment`,
`documentation-sync`, `versioning` — with the release *procedure* in
`docs/agents/release.yaml` as `release-process`. `contributor.md` places
everything but `release-process`; `maintainer.md` places all of it.

**`## Documentation Sync` and `## Versioning` appear in both templates.** Two
skills locate those headings by name — `skills/documentation-sync/SKILL.md:13`
and `skills/documentation-sync/references/cut-version.md:14` — and a role missing
either disables that gate silently. The maintainer role differs by carrying the
release procedure, not by dropping the heading that names it.

`tcw-config.yaml` gains the `agents:` block with both roles,
`default-role: contributor`, and default targets. `.gitignore` gains `AGENTS.md`,
`CLAUDE.md` and `.tcw/`. `scripts/remote_session_setup.sh` runs
`tcw agents generate` after installing the CLI, keeping its existing contract —
idempotent, exit 0 on every path, silent unless something failed — and the manual
`--force` path documented for Codex and local shells gets it too.

The two tests that read `REPO / "AGENTS.md"` are retargeted to
`docs/agents/`, which is the tracked, reviewable source once the guide is
generated: `tests/test_repo_lifecycle.py:110` (documentation-entry triggers must
not be listed in the guide) and `tests/test_documentation_sync_wiring.py:30`
(no dangling references to the absorbed plugin). Retarget rather than delete —
both still pin real contracts, just at the file that now carries the text.

This is one task, not two. Untracking the guide and retargeting the tests that
read it must land together: split either way, one commit leaves a test asserting
against a file whose status just changed.

**Proves it:** `tests/test_repo_agent_guide.py` asserts this repo's `agents:`
block parses with no problems; that `contributor` and `maintainer` each render
containing `## Documentation Sync` and `## Versioning`; that `maintainer`
contains the release procedure and `contributor` does not (**AC18**); and that
`AGENTS.md` and `CLAUDE.md` are absent from `git ls-files` and matched by
`git check-ignore` (**AC19**). `tests/test_remote_session_setup.py` gains a case
asserting the script leaves a generated `AGENTS.md` on disk and that two runs
produce byte-identical content (**AC20**). The full suite green is **AC21**.

---

## Task 12 — Documentation Sync

One pass over the finished diff, per the `implement` stage's rule. Every trigger
fires.

**`README.md` — [Public-API].** A new `### tcw agents — the audience` section
under Usage, after `### tcw work`: the config block, the fragment forms, the
`{{token}}` rule, the target table as task 10 left it, and the four commands.
It must carry three warnings, because each is a way to lose silently:

- Tooling that greps the guide **by heading name** keeps working only if every
  role's template still produces that heading — lesson #1 of
  `docs/migration-guide-0.21.X-to-1.0.0.md`, now applying to the guide's
  production rather than its contents.
- A `generate:` fragment **runs the repository's own shell** from a setup command
  a new contributor runs on a fresh clone, under the trust model at
  `tcw/work/hooks.py:11-14`. Say it where `generate:` is introduced, not in a
  footnote.
- A clone with no `default-role` and no setup step wiring `tcw agents generate`
  gives its agent **no guide at all**, and nothing reports that.

**`docs/release-notes/upcoming.md` — [Public-API].** Plain language, no module
names: one repository can now give different people different agent instructions;
shared text is written once; the generated file is not committed.

**`docs/changelogs/upcoming.md` — [Any-Code-Change].** Grouped. *Added:* the
`tcw agents` group, the `agents:` configuration block, `tcw validate` coverage.
*Changed:* `_confined`/`_read_file` made public (task 1); `run_generate` gains
`config_prefix` (task 5); this repository's guide is generated (task 11).

**`skills/<component>/SKILL.md` — [Skill-Driven-Component].** This trigger fires
for a *new* component, so it needs a new skill, not an edit: `skills/tcw-agents/
SKILL.md` plus references, teaching an agent to declare roles, write fragments
and templates, and run the generator — naming `tcw …` commands rather than
reimplementing them, as the other axis skills do. Also:

- `skills/tcw-plugin/SKILL.md` maps the skills and must list the new one.
- `.codex-plugin/plugin.json`'s `longDescription` says "ships eight skills" —
  now nine. Both manifests glob `./skills/`, so no path list changes.
- A `commands/tcw-generate-agent-guide.md` router is optional and Claude-only;
  if added, the procedure must live in the skill so a Codex user reaches it
  (`docs/lifecycle/harness.md`, and the pattern
  `tests/test_documentation_sync_wiring.py:23-26` already pins).

**`tests/test_documented_cli_surface.py`** parses `tcw`-prefixed invocations out
of every non-archival Markdown file git knows about. Every `tcw agents …`
invocation written in task 12 must exist in the parser by then — tasks 8 and 10
guarantee it, and this test is the check.

---

## Verification

What the suite cannot decide, to be checked by hand before `submit`:

1. **The interactive prompt.** Task 6's tests inject a fake TTY; no test attaches
   a real one. Run `tcw agents generate` from a terminal in a node with two
   roles and no persisted role: confirm it prompts, accepts a role, re-prompts on
   an unrecognized answer, and persists the answer.
2. **Symlink behavior on Windows.** AC4 is proved by monkeypatching `os.symlink`
   to raise, which pins the fallback path but not the trigger. If a Windows
   checkout is available, confirm `CLAUDE.md` is created at all — as a link with
   developer mode on, as a copy without.
3. **A fresh remote session.** Start a new Claude Code remote session on this
   branch and confirm `SessionStart` leaves a generated `AGENTS.md` on disk and
   that the agent reads it. The migration's whole risk is a clone with no guide,
   and only a real session start proves the wiring.
4. **Task 10's confirmations.** That each preset path is current is a claim about
   another vendor's documentation. A test can pin the table's contents; it cannot
   tell whether the contents are right.
5. **The generated guide reads as a guide.** Composition can produce text that is
   valid and useless — fragments in an order that reads as a non-sequitur,
   duplicated headings, a missing blank line between two fragments. Read both
   rendered roles end to end and compare against the current `AGENTS.md`.

## Notes

- **Every acceptance criterion is covered.** AC1 → task 8 · AC2 → 4 · AC3 → 7 ·
  AC4 → 7 · AC5 → 5 · AC6 → 5 · AC7–AC9 → 4 · AC10 → 3 · AC11 → 3 · AC12 → 6 ·
  AC13 → 6, 8 · AC14 → 7 · AC15 → 8 · AC16 → 2, 9 · AC17 → 5, 9 · AC18 → 11 ·
  AC19 → 11 · AC20 → 11 · AC21 → 11. Tasks 1, 10 and 12 carry no criterion of
  their own: task 1 is a rename the spec's reuse depends on, task 10 discharges
  the spec's one recorded unverified assumption, and task 12 is the documentation
  gate.
- **Two changes to existing behavior**, both in task 1 and task 5, both
  internal: a rename with no external contract, and a new keyword argument whose
  default preserves every current message. Neither is user-visible.
- **No blockers recorded.** The item this touches —
  [2026-08-18-serve-version-cut-instructions-from-tcw-config-yaml-instead-of-the-agent-guide](tcw://W/2026-08-18-serve-version-cut-instructions-from-tcw-config-yaml-instead-of-the-agent-guide)
  — is complementary, not sequential: task 11 keeps `## Versioning` in both
  roles' templates, which is exactly what that item would later make unnecessary.
  Neither blocks the other, so neither is recorded with `--blocked-by`.
- **Where this could still turn out too large.** Task 11 is the one to watch: it
  migrates the guide, retargets two tests, and edits the session-setup script in
  one commit because they cannot be split safely. If it grows past that during
  implementation, the honest move is to stop and decompose the *migration* into
  its own work item, leaving tasks 1–10 and 12 as a mechanism that this
  repository has not yet adopted — the feature stands without the dogfooding.

## Open questions

Raised with the requester when the plan was filed; **none blocks starting**, and
each names the default that will be taken if nobody answers. Written down here
rather than left in a chat log so whoever picks this up next can decide without
the conversation. Two of the three are cheap to revisit later; question 3 gets
expensive once task 11 is committed.

### 1. Is `tcw/agents/` importing `tcw/work/` acceptable?

**Default if unanswered:** yes — proceed as planned.

Task 1 makes two helpers in `tcw/work/resolve.py` public so `tcw/agents/` can use
them, and task 5 calls `run_generate` from `tcw/work/generate.py`. An agents
package depending on the work package reads backwards.

The alternative is to move the shared resolution machinery to a top-level module
(`tcw/resolve.py`, say), leaving `tcw/work/` and `tcw/agents/` as peers that both
import it. That is the layering most people would draw, and it touches every
existing caller — `tcw/work/cli.py`, `tcw/serve/`, and four test modules — to
spare one import. `docs/lifecycle/implementation.md` says don't pre-abstract, and
one new consumer is the thinnest possible evidence that a shared layer is needed.

**Cost of changing later:** low. A second consumer arriving would be a better
reason to move it than this one is, and the move is mechanical.

### 2. Does a bare string in a fragment map mean `blob`?

**Default if unanswered:** yes — a bare string is `blob`, per task 3.

The requester's sketch is `preamble: Preamble text here`, and a fragment map is
mostly prose, so requiring `blob:` on every entry makes the common case worse.

But `_parse_binding` (`tcw/store/base.py:1018-1076`) deliberately rejects a bare
string in a lifecycle binding list, and the capability text for that says so
outright: "a bare string is rejected rather than guessed at". The spec's argument
for diverging is that a list position is genuinely ambiguous — a bare string
there could be a command, a file, or a skill — while a keyed mapping admits one
reading. That may still read as one rule with two answers to someone learning
both surfaces at once.

**Cost of changing later:** low *before* release, breaking after. If bare strings
should be rejected, decide it before this ships, because every adopting project's
fragment files would have to be rewritten afterwards.

### 3. Should this repository's own migration be a separate work item?

**Default if unanswered:** no — keep task 11 in this item.

Task 11 untracks `AGENTS.md` and `CLAUDE.md`, retargets
`tests/test_repo_lifecycle.py` and `tests/test_documentation_sync_wiring.py`,
adds `docs/agents/`, and edits `scripts/remote_session_setup.sh` — one commit,
because splitting it leaves a test asserting against a file whose tracked status
just changed. It is the largest task here and the only one that changes how this
repository is worked in.

Splitting it out would let tasks 1–10 and 12 land as a reviewable feature, with
the dogfooding as a follow-up. The argument against is that dogfooding is what
proves the mechanism works on a real guide, and a feature this repository has not
adopted is a feature nobody has used.

**Cost of changing later:** this is the one that gets expensive. Decide before
task 11 is committed; afterwards, splitting means reverting a commit that changed
the repo's own agent guide, on a branch where subsequent work already assumes it.

### Also unresolved, but not a question for the requester

**The Cursor, Copilot and Gemini preset paths are unverified** — recorded in the
spec's Notes and discharged by task 10, which confirms each against current
vendor documentation and **deletes any it cannot confirm**. This needs a
documentation check, not a decision, so it is a task rather than a question. Do
not ship a preset on a guess: the mapping form accepts any path, so a missing
preset costs one config line, while a wrong one silently writes a file no tool
reads.

## Resuming this item

Branch `claude/agents-md-role-builder-x898h9`; item
`2026-09-02-generate-a-role-specific-agents-md-from-configured-role-definitions`,
status `backlog`, artifacts `initial-request.md` · `spec.md` · `plan.md` all
committed, one commit each.

Read the three artifacts in order, settle the questions above — or accept their
defaults — and then `tcw work start
2026-09-02-generate-a-role-specific-agents-md-from-configured-role-definitions`
before the first code edit, followed by `tcw work stage implement <slug>` for the
implementation instructions this repository binds. Nothing here has been started:
no code exists, and `docs/agents/` does not yet exist.
