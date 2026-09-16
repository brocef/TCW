# Plan — Route agents to tcw-work-stage for stage instructions and validate its arguments

Implements `spec.md`. Every task ends with the suite green (bare `pytest`, as CI
runs it) and is its own commit.

## Before task 1

- Run `tcw work start <slug>` and `tcw work stage gate implement <slug>` **before
  editing anything under `tcw/`**. After task 1 the CLI is under change, so this
  repository's rule applies from then on: drive the work system by editing
  `docs/work/` files directly, and say so.
- Work on `main` or in a `--worktree`. If in a worktree, re-point the editable
  install first (`pip install -e <worktree> --no-deps`) and restore it before
  `complete`, as `CLAUDE.md` describes.

## Tasks

### 1. Harness detection

**Creates** `tcw/harness.py` and `tests/test_harness.py`.

`tcw/harness.py` holds two public functions and no state:

- `ancestor_programs(pid: int | None = None) -> list[str] | None` returns the
  program names of the process's ancestors, nearest first, starting from the
  parent of `pid` (default `os.getpid()`). For each hop, run
  `ps -o ppid=,comm= -p <pid>` through `subprocess.run` (a 2-second timeout;
  output captured). If `ps` is missing, fall back to reading
  `/proc/<pid>/stat` (parent id is field 4, after the `)` that closes the
  program name) and `/proc/<pid>/comm`. The walk stops at pid ≤ 1, at a pid
  already seen, or after 64 hops. It returns `None` when the very first lookup
  fails, whether `ps` is absent, errors, times out or prints nothing, or `/proc`
  is absent. Once at least one name has been read, a failure ends the walk and
  returns what it has. **It never raises.**
- `detect(ancestors: list[str] | None, environ: Mapping[str, str]) -> str`
  returns `"claude"` or `"other"`.
  1. For each name in `ancestors`, take its basename, lower-cased, with a
     leading `-` removed (a login shell shows as `-bash`). `claude` → return
     `"claude"`. `codex` → return `"other"`.
  2. If none matched, or `ancestors` is `None`: any of `CODEX_THREAD_ID`,
     `CODEX_SANDBOX` or `CODEX_SESSION_ID` non-empty → `"other"`.
  3. Otherwise → `"claude"`. This covers `CLAUDECODE`, `CLAUDE_CODE_SESSION_ID`,
     and nothing set at all. The two Claude variables need no branch of their
     own; the module docstring says why (they only matter in that they must not
     outrank a Codex variable).

`tests/test_harness.py`, one test per bullet of spec criterion 9, calls `detect`
with literal lists and dicts:

- `["bash", "codex", "zsh", "claude"]` → `"other"`
- `["/opt/homebrew/bin/bash", "claude", "-bash"]` → `"claude"`
- `["bash", "claude", "codex"]` → `"claude"`
- `None` with `{"CLAUDECODE": "1", "CODEX_THREAD_ID": "x"}` → `"other"`
- `None` with `{"CLAUDECODE": "1"}` → `"claude"`
- `None` with `{}` → `"claude"`
- `["bash", "node", "login"]` with `{}` → `"claude"` (no name matched, no
  variable)
- `ancestor_programs()` returns `None` or a list of non-empty strings, and does
  not raise, both on the real machine and with `PATH` set to an empty
  directory (monkeypatched).

**Proves it:** `pytest tests/test_harness.py`. Break step 1's nearest-match rule
by searching for `claude` first; the chain test must go red.

### 2. The `validate` verb

**Modifies** `tcw/work/cli.py`, `tests/test_stage_verb.py:730`,
`skills/tcw-work/references/commands.md`. **Creates**
`tests/test_stage_validate.py`.

In `tcw/work/cli.py`:

- New handler `_stage_validate(args)`, placed after `_stage_prompt`. It builds
  a list of problems, then prints and returns:
  - `words = args.words`.
  - `len(words) == 0` → reason `No arguments were given.`
  - `len(words) > 2` → reason ``{n} arguments were given: `{' '.join(words)}`.``
  - Otherwise the stage: `LIFECYCLE_STEPS_BY_ID.get(words[0])` must exist with
    `kind == "stage"`. If not → reason
    ``'`{words[0]}` is not a stage; expected one of {legal ids, comma-separated}.'``
    Do **not** call `_stage_step`, which prints to stderr.
  - The stage is `inbox` and there is a second word → reason
    ``'`inbox` runs before a work item exists and takes no work item.'``
  - Any other stage with a second word: call `_resolve(words[1], "stage validate")`
    and `st.get(bare)` inside `contextlib.redirect_stderr(io.StringIO())`.
    - `None` from `_resolve` → the captured stderr text, stripped, is the
      reason.
    - `MultipleMatch` → `str(e)`.
    - `get` returning `None` → ``'No work item matches `{words[1]}`.'``
    - The item's status is **not** checked.
- Output, all on stdout, built as a list of paragraphs joined by a blank line:
  - if `detect(ancestor_programs(), os.environ) == "other"`, first the notice,
    verbatim:
    `Your AI agent harness does not support dynamic context injection. You will need to manually run all commands with !\`command\` to interpret this skill.`
  - if there is a reason, then
    ``**Skill Invocation Error: The tcw-work-stage skill must be invoked with one to two arguments: `tcw-work-stage stage-id [work-slug]`**``
    followed by the reason.
  - Print nothing when the list is empty. Return 1 if there is a reason,
    otherwise 0.
- Detection runs **only** after arguments are judged. That way a test that
  monkeypatches `tcw.work.cli.ancestor_programs` / `detect` controls it, and
  the import is `from tcw.harness import ancestor_programs, detect` at module
  top.
- Parser, after `pbg.set_defaults(func=_stage)` (`:2874`):
  - `pvl = stg.add_parser("validate", help="check a tcw-work-stage skill invocation's arguments; prints nothing when they are valid")`
  - `pvl.add_argument("words", nargs="*", help="the skill's arguments as typed: a stage id and, optionally, a work item")`
  - `pvl.set_defaults(func=_stage_validate)`
- The metavar at `:2848` becomes `"{prompt,gate,validate}"`.
- `_HidesRemovedSpellings` (`:1252`) is unchanged: its
  `{"prompt", "gate"} <= choices` test still holds with a third verb. Its
  docstring's "both real verbs" becomes "the real verbs".

In `tests/test_stage_verb.py:730`: `"choose from 'prompt', 'gate', 'validate'"`.

In `skills/tcw-work/references/commands.md`, a row after "read a stage's
instructions":
`| check a stage skill's arguments | \`tcw work stage validate <id> [<slug>]\` — prints nothing and exits 0 when \`tcw work stage prompt\` would accept them; otherwise a Markdown usage error on stdout and exit 1. Under an agent harness other than Claude Code it first prints a notice that injected commands must be run by hand. Injected at the top of \`tcw-work-stage\` |`

`tests/test_stage_validate.py` runs everything in-process through
`tcw.cli.main([...])` with `monkeypatch.chdir(node)` and `capsys`. It reuses the
`_node` helper pattern from `tests/test_stage_verb.py` (copied, as that module
does, not imported from a test module), and adds one item with
`tcw work new`. It monkeypatches `tcw.work.cli.ancestor_programs` to return
`None` and clears the six variables, so the result does not depend on who runs
the suite.

- Criterion 6: `spec <slug>`, `inbox` and `plan` → empty stdout, exit 0.
- Criterion 7: `[]`, `nope`, `inbox <slug>`, `spec no-such-item` and
  `spec <slug> extra` → stdout starts with the bold error line, the next
  paragraph is the expected reason, exit 1.
- Criterion 8: with `CODEX_THREAD_ID=x` set, `spec <slug>` → stdout is exactly
  the notice plus a newline, exit 0. `nope` → notice, blank line, error line,
  blank line, reason, exit 1.
- A qualified `unknown-project/slug` → exit 1, and the reason is the text
  `_resolve` printed. The captured stderr is empty.
- Status is ignored: an item in `backlog` validates for `verify`, exit 0.
- Criterion 12: `subprocess.run(["tcw", "work", "stage", "--help"])` lists all
  three verbs.

**Proves it:** `pytest tests/test_stage_validate.py tests/test_stage_verb.py tests/test_documented_cli_surface.py`.
Delete the `inbox`-with-item branch; its test must go red.

### 3. Inject `validate` into `tcw-work-stage`

**Modifies** `skills/tcw-work-stage/SKILL.md`, `tests/test_skill_lifecycle_parity.py`.

Insert directly after the closing `---` of the frontmatter, before
`# The \`$stage\` stage`:

```markdown
## Skill invocation validation (Claude-only injection)

Under any harness other than Claude Code, run `tcw work stage validate` with this skill's arguments before reading on.

!`tcw work stage validate -- $stage $item 2>/dev/null || true`

```

*(Corrected during `implement`: the plan first used `$ARGUMENTS`. See spec.md,
"The skill line", for why.)*

In the "composing skill" section of `tests/test_skill_lifecycle_parity.py`, add
`test_the_composing_skill_validates_its_arguments_first`. The first line of the
body (after the frontmatter) that starts with `` !` `` must be exactly
`` !`tcw work stage validate -- $stage $item 2>/dev/null || true` ``, and it must come
before the `# The` heading. The existing
`test_every_injected_command_survives_its_own_failure` already covers `|| true`.

**Proves it:** `pytest tests/test_skill_lifecycle_parity.py`. Move the line below
the H1; the new test must go red.

### 4. Route `tcw-work` to the stage skill; delete `lifecycle/default/`

**Modifies** `skills/tcw-work/SKILL.md`,
`skills/tcw-work/references/commands.md:31`,
`tests/test_skill_lifecycle_parity.py`. **Deletes**
`skills/tcw-work/references/lifecycle/default/README.md`, and with it the
folder.

`skills/tcw-work/SKILL.md`, lines 21-54, becomes the following. The body budget
is 60 lines and the body is at 60 today, so the added note is paid for by
dropping the Document column, joining the transitions line (`:36-37`), shortening
the gate bullet (`:52-54`) to two lines, and joining the `tags.md`,
`epic-deltas.md` and `cross-node-deltas.md` bullets (`:63-65`) into one:

```markdown
## Two ladders

A **stage** produces one artifact. A **transition** moves status. Nothing is
both. Stage detection is artifact presence; status is the folder.

**To learn how to perform a stage, invoke the `tcw-work-stage` skill with the stage id and the work item — `tcw-work-stage <stage> [<slug>]`.**
It is where a stage's instructions come from, composed with this project's own.

| Stage        | Produces                                |
| ------------ | --------------------------------------- |
| `inbox`      | — (creates the item)                    |
| `request`    | `initial-request.md`                    |
| `spec`       | `spec.md`                               |
| `plan`       | `plan.md`                               |
| `implement`  | `outcome.md`                            |
| `verify`     | `refined-outcome.md` **or** `rework.md` |
| `postmortem` | `post-mortem.md`                        |

`start` · `submit` · `rework` · `complete` · `discard` → [`transitions.md`](references/transitions.md)

## Finding your place

Read the item, then invoke `tcw-work-stage` for **only** the first missing artifact's stage:
no `initial-request.md` → `request` · no `spec.md` → `spec` · no `plan.md` →
`plan` · no `outcome.md` → `implement` · no `refined-outcome.md`/`rework.md` →
`verify`. Resume across sessions with `tcw work list --status active` →
`tcw work show <slug>`; for an epic, `tcw work reconcile <slug>` first.

## Always

- **Commit each stage artifact as you write it.** `[judgment]` — nothing enforces
  it. Never batch several stages into one commit. TCW commits the _transitions_
  itself; do not commit those by hand.
- **`tcw work stage gate <id> <slug>`** at every stage entry — it refuses; `tcw-work-stage` carries the instructions.
  Bindings → [`hooks.md`](references/hooks.md) · declaring them: the `tcw-configure` skill
```

and the three "Read on demand" bullets become one:

```markdown
- [`tags.md`](references/tags.md) — the node's tag vocabulary · [`epic-deltas.md`](references/epic-deltas.md) — `type: epic` differences · [`cross-node-deltas.md`](references/cross-node-deltas.md) — work across registered nodes
```

`commands.md:31` becomes:
`| read a stage as one document | \`tcw-work-stage <id> [<item>]\` — the skill composes TCW's own document for the stage with the output of \`tcw work stage prompt\` so both arrive in one read. It reads: no legality check, no \`pre\` checks. \`tcw work stage gate\` is still what refuses |`

In `tests/test_skill_lifecycle_parity.py`:

- `test_the_router_routes_to_every_stage_document` (`:289`) is replaced by
  `test_nothing_in_tcw_work_names_a_stage_document`. It is parametrised over
  `STAGE_IDS`. For `SKILL.md` and every `*.md` under `REFS` that is not under
  `REFS / "lifecycle"`, the text contains neither `stage-{id}.md` nor
  `references/lifecycle/` nor `lifecycle/stage-`. The docstring states the
  reason: an agent that opens a stage document directly skips the project's
  instructions.
- `test_the_router_routes_to_every_reference_file` (`:294`) skips paths whose
  `relative_to(REFS)` starts with `lifecycle/`. Its docstring says those are
  reached through `tcw-work-stage`, which `test_the_composing_skill_reads_a_router_that_exists`
  already resolves.
- New `test_the_router_names_the_stage_skill_in_bold`: `SKILL.md` contains a
  `**…**` span that includes `tcw-work-stage`, `<stage>` and `<slug>`.
- `SKILL_LINE_BUDGET` is not changed.

**Proves it:** `pytest tests/test_skill_lifecycle_parity.py tests/test_documented_cli_surface.py`,
plus spec criteria 1 and 2 run as written. Re-add one stage link; the new test
must go red.

### 5. The other skills and the verifier agent

**Modifies** these files, per the verdicts in spec Goal 3:

- `skills/tcw-commands-plan-work/SKILL.md:14-19` →
  ```markdown
  Read the `tcw-work` skill's `SKILL.md`, find the first missing artifact, and run the
  stages from there through `plan.md`, invoking the `tcw-work-stage` skill for
  **only** the stage you are running:

  - `tcw-work-stage request <slug>` → `initial-request.md`
  - `tcw-work-stage spec <slug>` → `spec.md`
  - `tcw-work-stage plan <slug>` → `plan.md`
  ```
- `skills/tcw-commands-verify-work/SKILL.md:14` →
  ``Invoke the `tcw-work-stage` skill with `verify` and the item's slug.``
- `skills/tcw-commands-process-inbox/SKILL.md:14` → begins
  ``Invoke the `tcw-work-stage` skill with `inbox`, and work through every entry``.
  `:19-20` → ``Accepting an entry writes it as the item's `intake.md`. Then invoke
  the `tcw-work-stage` skill with `request` and the new item's slug, and run the `request` stage over that intake to``.
- `skills/tcw-commands-drive-work-to-completion/SKILL.md:15-17` →
  ``type, status, and existing artifacts. Invoke the `tcw-work-stage` skill for **only** the stage
  you are in; the router's "Finding your place" section maps missing artifacts to
  stages.``
  `:33` → ``user explicitly approves closeout — see the `verify` stage (`tcw-work-stage verify <slug>`). At closeout,``
- `skills/tcw-post-mortem/SKILL.md:8-9` →
  ``**The contract lives elsewhere.** The `postmortem` stage — invoke the `tcw-work-stage` skill with `postmortem` and the item's slug —``
  followed by the existing `defines the inputs, …` sentence unchanged.
  `:69` → ``Write `post-mortem.md` per the `postmortem` stage's `Produce` section. Then create``
- `skills/tcw-extras-triage-issues/SKILL.md`:
  - `:22` → ``So the judgment already exists: the `inbox` stage holds it (invoke the `tcw-work-stage` skill with `inbox`) —``
  - In `:24-25`, "**Read that document before accepting anything**" becomes
    "**Read it before accepting anything**".
  - `:132` → ``Per the `inbox` stage — retitle, pick tags, split if it is really several items.``
  - `:175` → ``` `request` stage (`tcw-work-stage request <slug>`) when the item is picked ```
- `skills/documentation-sync/SKILL.md:21-23`: in the Reference column, `step 4`
  → `step 1`, `step 6` → `step 3`, `step 9` → `step 5`. The paths stay (a
  deliberate reference). Re-align the table's column padding.
- `agents/tcw-verifier.md:51-52` →
  ``You are an accelerator. Every TCW stage stands alone without you, and the
  `verify` stage is followable with no subagent at all.``

**Proves it:**

- Spec criterion 4, as a command:
  `grep -nE 'stage-(inbox|request|spec|plan|implement|verify|postmortem)\.md' skills/tcw-commands-*/SKILL.md skills/tcw-post-mortem/SKILL.md skills/tcw-extras-triage-issues/SKILL.md agents/tcw-verifier.md`
  prints nothing.
- Spec criterion 5, by reading the three cited steps.
- `pytest tests/test_skill_path_pointers.py tests/test_skill_lifecycle_parity.py tests/test_documentation_sync_wiring.py`.
- Nothing new is automated for this task. A test pinning prose wording in eight
  files would break on every rewording and catch nothing.

### 6. Capabilities

**Creates** `capabilities.yaml` in the item folder. **Modifies**
`docs/capabilities/work/run-a-lifecycle-stage/description.md`,
`docs/capabilities/skills/tcw-work-stage/description.md` and
`docs/capabilities/skills/tcw-work/description.md`.

- `capabilities.yaml`:
  ```yaml
  changed:
      - work/run-a-lifecycle-stage
      - skills/tcw-work-stage
      - skills/tcw-work
  ```
- `work/run-a-lifecycle-stage`:
  - The first paragraph's "two verbs, each doing one job" becomes "three verbs,
    each doing one job", and gains a third sentence pair:
    `` `tcw work stage validate <id> [<ref>]` asks **would `prompt` accept this**: it prints nothing when it would, and a Markdown usage error with the reason when it would not. ``
  - The "They are two verbs because…" paragraph keeps its history and is
    retitled in place to say the *instruction* verbs are two. `validate` checks
    arguments; it answers neither question.
  - A new paragraph, placed after the `inbox` paragraph, covering: `validate`
    exists for the `tcw-work-stage` skill; its status blindness matches
    `prompt`; exit 1 on invalid arguments; the harness notice printed first
    under a harness other than Claude Code, decided by the nearest `claude` or
    `codex` ancestor process and then by `CODEX_*` variables.
  - "Neither verb writes anything" → "No verb writes anything".
- `skills/tcw-work-stage`: add a sentence. The skill first checks its own
  arguments, and a missing or wrong stage, or an item that does not resolve,
  gets a usage error at the top of the skill instead of broken sections. Under a
  harness that did not run it, the skill says to run the check by hand.
- `skills/tcw-work`: add a sentence. Asking the skill how to perform a lifecycle
  stage sends me to the `tcw-work-stage` skill, which delivers the stage
  together with my project's own instructions for it.

**Proves it:** `tcw capabilities check` exits 0, and
`tcw capabilities show <path>` for each of the three reads as described.
Running either CLI command is safe here, because the ledger is not code.

### 7. Documentation Sync block

Evaluated against `tcw work docs`:

| Entry | Fires? | Task |
| --- | --- | --- |
| `README.md` [Public-API] | **yes**: a new public verb | `README.md:621` row → ``| `tcw work stage`     | `stage gate` checks a stage may run; `stage prompt` prints its instructions; `stage validate` checks a `tcw-work-stage` invocation's arguments |``. Also check that README's skills section describes `tcw-work-stage` accurately. |
| `docs/guide/jira.md` [Tracker-Change] | no | none |
| `docs/release-notes/upcoming.md` [Public-API] | **yes** | Plain-language entries: `tcw-work-stage` now tells you when it was invoked with a missing or wrong stage or work item; under Codex it says to run its commands yourself; the `tcw-work` skill and the command skills now send agents to `tcw-work-stage` for a stage's instructions. |
| `docs/changelogs/upcoming.md` [Any-Code-Change] | **yes** | Added: `tcw work stage validate`, `tcw/harness.py`. Changed: stage routing in `tcw-work` and six skills, `tcw-verifier` wording, `documentation-sync` step numbers. Removed: `skills/tcw-work/references/lifecycle/default/README.md`. Internal: parity tests inverted. |
| `skills/<component>/SKILL.md` [Skill-Driven-Component] | **yes** | Covered by tasks 2, 4 and 5. At the documentation pass, confirm `tcw-work`'s commands reference names `validate` and nothing still says "two verbs". |
| `skills/tcw-configure/references/<document>.md` [Configuration-Key-Change] | no: no configuration key changes | none |

Not a declared entry, but it describes the stage verbs:
`docs/guide/configuration.md` §"Checking a stage, reading its instructions, and
starting its document" (`:94`) gains a paragraph on `validate`, after the
`prompt` paragraph. Update it in the same pass.

**Proves it:** `pytest tests/test_documented_cli_surface.py`, since every
`tcw …` spelling added to these documents must exist.

## Verification

What the suite cannot check. Record the results in `outcome.md`.

1. **Claude Code, for real (criterion 10).** From a scratch TCW node with one
   item, using this checkout's plugin (`--plugin-dir /Users/brian/Projects/TCW`,
   never the installed `tcw@tcw`):
   - invoke `/tcw:tcw-work-stage` with no arguments: the skill loads, the
     transcript shows no "Shell command failed", and the rendered text contains
     the Skill Invocation Error;
   - invoke `/tcw:tcw-work-stage spec <slug>`: no validation text renders.

   Record the command used and the relevant transcript lines.
2. **Codex, for real (criterion 11).** Once Codex's usage limit has reset, run
   a `codex exec` session from **inside this Claude session**, so that the
   nesting case is the one exercised. Use `-c sandbox_mode=read-only`,
   `--disable shell_snapshot`, `-o <file>` and `< /dev/null`, and ask it to run
   exactly two commands from the scratch node:
   `tcw work stage validate spec <slug>`, then
   `ps -o pid=,ppid=,comm= -p <each ancestor>` (the same walk).
   Confirm the harness notice printed. Record the observed chain in `outcome.md`.
   If the program name is not `codex`, or `ps` is refused inside the sandbox,
   fix `detect` and add that chain to `tests/test_harness.py` before finishing.
   An empty `-o` file is no answer, not a pass.
3. **The older-CLI case.** Run `tcw-cli` 2.3.0 in a throwaway virtual
   environment: `bash -c 'tcw work stage validate spec x 2>/dev/null || true'`
   prints nothing and exits 0.
4. **Reviews.** An adversarial code review of the combined diff, with
   particular attention to `tcw/harness.py`'s never-raise promise and the
   `_resolve` stderr capture.

## Notes

- **Order.** Task 1 lands before task 2 because `validate` imports it. Task 3
  follows task 2 because the injected line would otherwise run a verb that does
  not exist yet. For a local checkout that is harmless (`2>/dev/null || true`),
  but the suite would be exercising a skill ahead of its CLI.
- **The riskiest change is task 4**, where a line budget and two parity tests
  meet. By then the verb and the injection are already tested, so a red suite
  can only come from the routing edits.
- **No blockers.** `2026-09-15-drop-the-tcw-prefix-from-the-plugin-s-skill-and-agent-names`
  and `2026-09-15-fill-codex-gaps-in-skills-and-give-each-skill-one-capability`
  touch the same files, but neither has to land first (spec Risks).
