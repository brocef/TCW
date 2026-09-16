# Spec — Route agents to tcw-work-stage for stage instructions and validate its arguments

## Capability changes

Planned ledger deltas only. Nothing is written to the ledger at this stage.

```yaml
changed:
    - work/run-a-lifecycle-stage # a third verb, `tcw work stage validate`
    - skills/tcw-work-stage # checks its own arguments; tells a non-Claude harness to run commands by hand
    - skills/tcw-work # sends an agent to tcw-work-stage for how to work a stage
```

No new capability. `validate` answers a question about the same two arguments
`gate` and `prompt` take, so it belongs to the capability that already describes
those verbs. Right now that capability's text says "two verbs"
(`docs/capabilities/work/run-a-lifecycle-stage/description.md`), so that wording
has to change. The other skills edited below get no ledger change: none of their
capability descriptions says where the skill reads a stage from. A sweep of the
ledger for `stage-*.md`, "stage document", "stage prompt" and "stage gate" matched
only the three above, plus `web/editing` and
`skills/tcw-commands-drive-work-to-completion`. Those two use "stage documents"
for something else: the per-slice documents a `plan.md` may declare.

## Problem

1. **Agents can read a stage's document and never see the project's instructions
   for that stage.** `skills/tcw-work/SKILL.md:26-34` links each of the seven
   `references/lifecycle/stage-<id>.md` files from its "Two ladders" table.
   `skills/tcw-work/SKILL.md:41` then says to "load **only** the document for the
   first missing artifact". The stage documents are thin on purpose. Each one
   points back at `tcw work stage prompt`, and the substance lives there, for
   example project bindings such as this repository's `docs/lifecycle/abstraction.md`.
   The `tcw-work-stage` skill exists to deliver both together:
   `skills/tcw-work-stage/SKILL.md:20` runs `cat` on the stage document and
   `:24` runs `tcw work stage prompt`. As things stand, an agent that follows
   `tcw-work` has no reason to invoke it.
2. **Eight other places send agents straight to a stage document:**
   - `skills/tcw-commands-plan-work/SKILL.md:17-19`
   - `skills/tcw-commands-verify-work/SKILL.md:14`
   - `skills/tcw-commands-process-inbox/SKILL.md:14,20`
   - `skills/tcw-commands-drive-work-to-completion/SKILL.md:15-17,33`
   - `skills/tcw-post-mortem/SKILL.md:8,69`
   - `skills/tcw-extras-triage-issues/SKILL.md:22,132,175`
   - `skills/documentation-sync/SKILL.md:21-23`
   - `agents/tcw-verifier.md:51-52`

   `skills/tcw-work/references/commands.md:31` also names `lifecycle/stage-<id>.md`
   from inside `tcw-work`'s own references.
3. **The existing tests enforce the links this change removes.**
   `tests/test_skill_lifecycle_parity.py:289` (`test_the_router_routes_to_every_stage_document`)
   asserts that `tcw-work/SKILL.md` names every `stage-<id>.md`. `:294`
   (`test_the_router_routes_to_every_reference_file`) asserts that every `.md`
   file under `references/` is reachable from `SKILL.md`.
4. **`tcw-work-stage` does not check its arguments.** Claude Code turns a missing
   named argument into an empty string (skills reference, "When Fewer Arguments
   Are Passed Than Declared"). So `/tcw-work-stage` with no arguments renders
   `# The `` stage`, then runs `cat …/stage-.md || true` and
   `tcw work stage prompt || true`. The agent gets two error fragments in the
   middle of the document, and nothing says what the invocation should have
   been. An unknown stage or a mistyped slug fails the same way. Arguments beyond
   the second are dropped without any notice, because only `$stage` and `$item`
   are substituted.
5. **Other harnesses never run the injected lines.** Injected lines only run in
   Claude Code (`docs/lifecycle/harness.md`). The skill's fallback paragraph at
   `skills/tcw-work-stage/SKILL.md:41-49` covers that for the two reading
   commands. Nothing tells a Codex agent directly that its harness left the
   `` !`…` `` lines unrun.
6. **`skills/tcw-work/references/lifecycle/default/README.md` points at files an
   agent may not have.** It sends readers to `tcw/work/prompts/*.md`. That folder
   ships inside the Python package (`pyproject.toml`, `package-data` for
   `tcw.work`), not with the plugin, so an agent running the skill has no
   guaranteed path to it. Its only link in is `skills/tcw-work/SKILL.md:54`.
7. **A related wrong reference found during the sweep.** `skills/documentation-sync/SKILL.md:21-23`
   cites step 4 of `stage-plan.md`, step 6 of `stage-implement.md` and step 9 of
   `stage-verify.md`. Those documents have 3, 4 and 5 numbered steps. The
   documentation-sync steps are now 1, 3 and 5
   (`skills/tcw-work/references/lifecycle/stage-plan.md:27`,
   `stage-implement.md:25`, `stage-verify.md:31`).

## Goals

1. **Nothing reachable from `tcw-work` names a stage document.** Neither
   `skills/tcw-work/SKILL.md` nor any document under `skills/tcw-work/references/`
   outside `references/lifecycle/` links to or names a
   `references/lifecycle/stage-<id>.md` file.
2. **An emphasized routing note in `skills/tcw-work/SKILL.md`.** An agent that
   wants instructions on *how* to perform a stage invokes the `tcw-work-stage`
   skill with the stage id and, when there is one, the work item. The
   stage-to-artifact table and "Finding your place" say the same thing, so
   nothing in the skill still tells the agent to load a document.
3. **Each other skill's reference is resolved on its merits.** The user reviewed
   and agreed these verdicts on 2026-09-16:

   | Reference | Why it is there | Verdict |
   | --- | --- | --- |
   | `tcw-commands-plan-work:17-19` | tells the agent to read a stage document to run that stage | invoke `tcw-work-stage <stage> <slug>` instead |
   | `tcw-commands-verify-work:14` | same, for `verify` | invoke `tcw-work-stage verify <slug>` |
   | `tcw-commands-process-inbox:14,20` | same, for `inbox` and `request` | invoke `tcw-work-stage inbox` and `tcw-work-stage request <slug>` |
   | `tcw-commands-drive-work-to-completion:15-17,33` | "Load only the document for the stage you are in", and "see `stage-verify.md`" for the closeout hold | invoke `tcw-work-stage` for the current stage; name the `verify` stage rather than its file |
   | `tcw-post-mortem:8,69` | "The contract lives elsewhere" — read it to run the stage | invoke `tcw-work-stage postmortem <slug>` for the contract, including its `Produce` section |
   | `tcw-extras-triage-issues:22,132,175` | the inbox judgment it must not restate, and the `request` stage run later | invoke `tcw-work-stage inbox` / `tcw-work-stage request <slug>` |
   | `documentation-sync:21-23` | a record, for anyone checking the wiring, of where each stage document calls this skill | **deliberate: keep**; correct the step numbers to 1, 3 and 5 |
   | `agents/tcw-verifier.md:51-52` | a claim that the verify stage works without the subagent, not an instruction to read anything | reword to name the `verify` stage rather than its file |
   | `skills/tcw-work-stage/SKILL.md:20,46` | the composing line and its fallback | keep: this is the one sanctioned reader |

4. **`references/lifecycle/default/README.md` is deleted**, along with its link
   at `skills/tcw-work/SKILL.md:54`.
5. **A new verb, `tcw work stage validate`,** reports whether a `tcw-work-stage`
   invocation's arguments are ones `tcw work stage prompt` would accept.
   It adapts its output to the harness that ran it.
6. **`skills/tcw-work-stage/SKILL.md` runs `validate` first,** as an injected
   line directly after the frontmatter, ahead of the H1 heading.
7. **The tests guard the new rule.** They stop asserting that the stage documents
   are linked, and start asserting that nothing reachable from `tcw-work` names
   them.

## Non-goals

- **Changing what `gate` or `prompt` do.** `validate` reads the same arguments;
  it changes neither verb's behavior, output or exit codes.
- **Hiding the stage documents from the filesystem.** They stay where they are,
  because `tcw-work-stage` reads them by path. The goal is that no instruction
  points an agent at them, not that they cannot be opened.
- **Codex's `<plugin>` placeholder in the fallback block** (`skills/tcw-work-stage/SKILL.md:46`).
  That belongs to
  `2026-09-15-fill-codex-gaps-in-skills-and-give-each-skill-one-capability`.
- **Renaming `tcw-work-stage`.** That belongs to
  `2026-09-15-drop-the-tcw-prefix-from-the-plugin-s-skill-and-agent-names`.
  Whichever item lands second updates the other's names.
- **Shell-quoting the substituted arguments.** The existing two injected lines
  already put `$stage` / `$item` into a shell command unquoted. The new line
  inherits that exposure and adds nothing new to it. Fixing it for all three
  lines is separate work.
- **Historical documents.** `docs/changelogs/*` and `docs/work/**` name the stage
  documents as a record of past changes. They are not instructions, so they are
  left alone.
- **`tcw/work/templates.py:7` and `evals/grade.py:63`.** One is a docstring and
  the other is a grader pattern. Neither is text an agent is sent to read.

## Design

### Argument validity: exactly what `prompt` accepts

`validate` takes the raw invocation: zero or more positional words. They are
valid when all of these hold, which are the same rules `prompt` applies
(`tcw/work/cli.py:1410-1472`):

1. **One or two words.** Zero or three-plus words is invalid. The error says how
   many were given.
2. **The first word is a stage id.** It must be a stage in `LIFECYCLE_STEPS`,
   the same test `_stage_step` makes (`tcw/work/cli.py:1376`).
3. **For `inbox`, no second word.** `prompt` refuses a work item for `inbox`
   (`tcw/work/cli.py:1446`), so `validate` refuses one too.
4. **For any other stage, the second word is optional.** When present it must
   resolve, through the same `_resolve` path (`tcw/work/cli.py:127`), to exactly
   one work item. A `<project-id>/<slug>` form resolves against that node, as it
   does for `prompt`. No match, or several matches, is invalid.

The item's **status is not checked**. `prompt` prints a stage's instructions
for an item in the wrong status, adding a warning (`tcw/work/cli.py:1465-1470`),
and `gate` is the verb that refuses on status. A `validate` that refused here
would contradict the verb it guards.

The initial request said the item is optional "including `inbox`". That
contradicts `prompt`, which refuses an item for `inbox`. The request also said
validity should match `prompt`, so this spec follows `prompt`.

### Output and exit status

- **Valid, under Claude Code:** prints nothing and exits 0.
- **Invalid:** prints Markdown to stdout and exits 1. It begins with the line the
  user gave:

  > **Skill Invocation Error: The tcw-work-stage skill must be invoked with one
  > to two arguments: `tcw-work-stage stage-id [work-slug]`**

  One more line follows, saying what was wrong in this invocation: the word
  count, the unknown stage (with the list of legal ids), `inbox` given an item,
  or the item that did not resolve.
- **Under a harness other than Claude Code:** the harness notice below is printed
  **first**, followed by exactly the output above. So with valid arguments the
  command prints the notice alone and exits 0. With invalid arguments it prints
  the notice and then the error, and exits 1.

  > Your AI agent harness does not support dynamic context injection. You will
  > need to manually run all commands with !`command` to interpret this skill.

Everything goes to stdout. `gate` and `prompt` send errors to stderr so that a
pipeline receives either the whole instruction text or none of it. `validate`'s
output is the report itself, and Claude merges stderr into injected text anyway.

**Why exit 1 is safe to inject.** In Claude Code, an injected command that exits
non-zero cancels the whole skill invocation. Claude sees only
`Shell command failed for pattern "..."` (skills reference, "Command Failure
Behavior"). The skill line therefore ends in `|| true`, as the two existing
injected lines do. The message still reaches the agent, and the exit status stays
usable for anyone running the command in a script.

### Harness detection

The question is which harness **directly** ran this command. When Claude runs
`codex exec` and Codex runs `validate`, the answer must be Codex, even though
Codex inherited Claude's environment variables.

1. **Process tree first.** Walk up from the process's parent. The first ancestor
   whose program name is `claude` decides "Claude Code", and the first named
   `codex` decides "another harness". The nearest match wins, which is what makes
   the nested case come out right. From a Claude Code shell today the chain is
   `bash → claude → -bash → login → iTermServer` (observed 2026-09-16). The
   runtime dependency stays PyYAML alone, so the tree is read with the standard
   library and the platform's own tools (`ps`, or `/proc` on Linux).
2. **Environment variables when the tree gives no answer.** That covers an
   unreadable tree, no `ps`, a sandbox that blocks it, Windows, or no ancestor
   with either name.
   - Any of `CODEX_THREAD_ID`, `CODEX_SANDBOX` or `CODEX_SESSION_ID` set → another
     harness. A Codex variable wins over a Claude variable here for the same
     nesting reason. `CODEX_THREAD_ID` and `CODEX_SANDBOX` appear in the Codex
     0.154.0 binary. `CODEX_SESSION_ID`, the variable first named, appears
     neither there nor in Codex's environment-variable documentation. It is
     checked anyway because it costs nothing.
   - Otherwise `CLAUDECODE` (documented as `1` in commands Claude Code runs) or
     `CLAUDE_CODE_SESSION_ID` (set, but undocumented) → Claude Code.
3. **Nothing detected → treated as Claude Code.** A person in a plain terminal
   gets the plain validation output with no harness notice. That is what the
   user decided.

Detection is a CLI concern with nothing to do with the store, so the abstraction
litmus test has nothing to say about it. Item resolution goes through `_resolve`
and the store's `get`, so a non-filesystem store answers `validate` exactly as it
answers `prompt`.

### The skill line

Directly after the frontmatter, before `# The `$stage` stage`:

```markdown
## Skill invocation validation (Claude-only injection)

!`tcw work stage validate -- $stage $item 2>/dev/null || true`
```

**`2>/dev/null` handles an older CLI.** The plugin and the `tcw` CLI are
installed separately, so a plugin carrying this line can meet a `tcw` that has
no `validate` verb. That `tcw` exits 2 and prints argparse's usage error to
stderr, which `|| true` alone would inject at the top of every stage.
`validate` writes its whole report to stdout, so discarding stderr loses
nothing from a current CLI and hides the noise from an old one. (Added during
`plan`.)

The heading takes the user's "(Claude-only)" and pins it to the *injection*.
A bare "(Claude-only)" would tell a Codex reader to skip the section, and the
harness notice exists for exactly that reader. One sentence under the heading
tells any other harness to run the command itself first.

**`$stage $item`, not `$ARGUMENTS`.** *(Revised during `implement`, after
review.)* This spec first chose `$ARGUMENTS` so that three or more words could
be reported. But `$ARGUMENTS` puts the extra words into the shell unquoted, where
the old lines simply dropped them. A `#` then comments out `|| true`, and an
apostrophe or a parenthesis is a shell syntax error. Either way the line exits
non-zero and cancels the whole skill load. The user chose `$stage $item` on
2026-09-16. It keeps exactly the exposure the other two lines already have, and
gives up reporting extra words from the skill. `validate` still reports them
when run by hand. `--` comes first so that a stage typed as `-h` is judged, not
parsed as an option.

### Parser

`validate` joins `prompt` and `gate` in the `stage` subparser group
(`tcw/work/cli.py:2852-2875`). Four things must change with it:

- the written-out metavar `{prompt,gate}` at `:2848`;
- `_HidesRemovedSpellings` (`:1235`), which recognizes the verb group by
  `{"prompt", "gate"} <= choices` and must still fire;
- `tests/test_documented_cli_surface.py`, which discovers verbs from `--help`, so
  `validate` has to be documented where that test looks;
- the positional takes `nargs="*"` so that argparse never rejects a word count
  before the handler can report it in Markdown.

### Skill and reference edits

- `skills/tcw-work/SKILL.md`:
  - The "Two ladders" table keeps the stage and artifact columns. Its document
    column becomes the `tcw-work-stage` invocation for that stage.
  - "Finding your place" names the stage to invoke, not a document to load.
  - The "Always" bullet at `:52-54` drops "the stage document only what the CLI
    cannot" and the `lifecycle/default/` link.
  - The emphasized note sits above the table, where an agent looking for a stage
    reads first.
  - The body stays within `SKILL_LINE_BUDGET = 60`
    (`tests/test_skill_lifecycle_parity.py:50`). **It is at exactly 60 today**,
    so every line the note adds must be removed from somewhere else in the skill.
    Raising the budget is not the answer; the test's own message is "extract,
    don't grow".
- `skills/tcw-work/references/commands.md:31` describes `tcw-work-stage` without
  naming the stage document path, and gains a `validate` row.
- The skills in Goal 3 are edited per their verdicts. Each names the skill and
  its arguments in words ("invoke the `tcw-work-stage` skill with `verify` and
  the item"), the way `tests/test_skill_path_pointers.py` asks cross-skill
  pointers to be written.

### Tests

- Replace `test_the_router_routes_to_every_stage_document` with its inverse: no
  `stage-<id>.md` name, and no `references/lifecycle/` path, appears in
  `tcw-work/SKILL.md` or in any file under `tcw-work/references/` outside
  `lifecycle/`.
- `test_the_router_routes_to_every_reference_file` keeps its orphan check but
  exempts `references/lifecycle/`, which now exists to be reached through
  `tcw-work-stage`. Deleting `default/README.md` removes the one other file
  there.
- Add an assertion that `tcw-work/SKILL.md` names `tcw-work-stage`, so the
  routing note cannot be lost without a failure.
- Add an assertion that `tcw-work-stage/SKILL.md`'s first body line that is not
  a heading or blank is the `validate` injection.
- `tests/test_documentation_sync_wiring.py` reads the stage documents by path
  from Python. That is not agent routing, so it stays as it is.
- Unit-test `validate`: each validity rule, the exact output under each detected
  harness, and detection order (tree beats variables, a Codex variable beats a
  Claude variable, nothing detected means Claude). The process tree is injected,
  so the tests never depend on who runs the suite.

## Acceptance criteria

1. `grep -rnE 'stage-(inbox|request|spec|plan|implement|verify|postmortem)\.md|references/lifecycle/' skills/tcw-work --include='*.md' | grep -v '^skills/tcw-work/references/lifecycle/'`
   prints nothing.
2. `skills/tcw-work/references/lifecycle/default/` does not exist, and nothing
   outside `docs/changelogs/` and `docs/work/` names `lifecycle/default`.
3. `skills/tcw-work/SKILL.md` contains an emphasized (bold) sentence that tells
   an agent wanting how to perform a stage to invoke the `tcw-work-stage` skill,
   and names both arguments.
4. None of the following contains `stage-<id>.md`:
   - `skills/tcw-commands-plan-work/SKILL.md`
   - `skills/tcw-commands-verify-work/SKILL.md`
   - `skills/tcw-commands-process-inbox/SKILL.md`
   - `skills/tcw-commands-drive-work-to-completion/SKILL.md`
   - `skills/tcw-post-mortem/SKILL.md`
   - `skills/tcw-extras-triage-issues/SKILL.md`
   - `agents/tcw-verifier.md`

   Each of the six skills names `tcw-work-stage` wherever it previously named a
   stage document.
5. `skills/documentation-sync/SKILL.md` still cites the three stage documents,
   now as steps 1, 3 and 5. Step 1 of `stage-plan.md` and step 3 of
   `stage-implement.md` name the `documentation-sync` skill. Step 5 of
   `stage-verify.md` is the version-cut offer.
6. With no harness detected (tree and variables both empty, via the test seam):
   - `tcw work stage validate spec <an existing slug>` prints nothing and exits 0;
   - `tcw work stage validate inbox` prints nothing and exits 0;
   - `tcw work stage validate plan` prints nothing and exits 0.
7. Each of these prints the bold Skill Invocation Error line plus a reason line,
   and exits 1:
   - `tcw work stage validate` (no words)
   - `tcw work stage validate nope`
   - `tcw work stage validate inbox <slug>`
   - `tcw work stage validate spec no-such-item`
   - `tcw work stage validate spec <slug> extra`
8. With the harness detected as Codex, the valid invocation from criterion 6
   prints only the harness notice and exits 0. An invalid one from criterion 7
   prints the notice, then the error, and exits 1.
9. **Detection order**, tested with the tree and environment supplied by the test:
   - an ancestor chain `bash → codex → zsh → claude` → another harness;
   - `bash → claude → codex` → Claude Code;
   - an unreadable tree with `CLAUDECODE=1` and `CODEX_THREAD_ID` set → another
     harness;
   - an unreadable tree with only `CLAUDECODE=1` → Claude Code;
   - nothing at all → Claude Code.
10. `skills/tcw-work-stage/SKILL.md` has
    `` !`tcw work stage validate -- $stage $item 2>/dev/null || true` `` before its H1.
    **Invoking `/tcw:tcw-work-stage` with no arguments in a real Claude Code
    session** loads the skill: no "Shell command failed" notice, and the rendered
    text contains the Skill Invocation Error. Invoking it with valid arguments
    renders no validation text.
11. **A real Codex session** runs `tcw work stage validate spec <slug>` from its
    shell and prints the harness notice. The process chain it saw is recorded in
    `outcome.md`, which confirms or corrects the program name `codex`.
12. `tcw work stage --help` lists `prompt`, `gate` and `validate`.
    `tcw work stage nope` still reports only those three as choices, not the
    seven removed per-stage spellings.
13. `pytest` (bare, as CI runs it) passes.
14. The ledger entries under **Capability changes** describe three verbs and the
    new skill behavior. `tcw capabilities check` exits 0.

## Risks

- **Process names are not a guarantee.** A wrapper script, a renamed binary, an
  npm-installed Claude Code running as `node`, or a parent that exited (its
  children move to process 1) can each hide the real harness from the tree walk.
  The variable fallback covers the first three only where the variables survive.
  The walk can also go wrong: under an unrecognized `node` Claude that was itself
  launched from Codex, the walk skips past Claude and finds the outer Codex. The
  harness notice is advisory, so a wrong answer costs one misleading paragraph,
  never a refused stage.
- **Codex's real process chain is unobserved.** Codex hit its usage limit during
  this spec, so the `codex` program name is taken from the binary's file name
  (`~/.codex/packages/standalone/releases/0.154.0-*/bin/codex`), and macOS
  sandboxing may insert `sandbox-exec` into the chain. Criterion 11 exists to
  confirm this before anything relies on it.
- **Removing the links might make the stage documents harder to maintain**, for
  someone editing them who used `tcw-work/SKILL.md` as the index. The
  `tcw-work-stage` fallback block and the parity tests keep every one of them
  addressed by path.
- **Collision with the rename item.** Both items edit `skills/tcw-work/SKILL.md`,
  `skills/tcw-work-stage/SKILL.md` and the command skills. Whichever lands second
  has to rebase over the other's names. Neither blocks the other.
- **The eval harness's fallback detection** (`evals/grade.py:63`) treats a `cat`
  of `skills/tcw-work/references/lifecycle/stage-` as "the agent did it by hand".
  Fewer routes to those files should only make that signal cleaner. Nothing here
  changes the grader.

## Notes

- Decisions the user made in chat on 2026-09-16, after `initial-request.md` was
  written:
  - the command is `tcw work stage validate`;
  - under a non-Claude harness the notice is always printed, before the normal
    output;
  - the item is optional; this spec reads that as "wherever `prompt` accepts
    one";
  - exit 1 on invalid arguments, with `|| true` on the skill line;
  - detection by process tree with a variable fallback, not by variables alone.
    That one was prompted by the finding that `CODEX_SESSION_ID` does not exist
    in Codex 0.154.0;
  - delete `lifecycle/default/README.md`;
  - the per-skill verdicts in Goal 3.
- Assumption, not verified: Claude Code runs an injected command through the same
  shell the Bash tool uses, so the command's ancestors include `claude`. The
  observed chain came from a Bash tool call. Criterion 10 checks it for real.
- References read: the Claude Code skills and environment-variable references,
  and the Codex environment-variable reference, all linked in
  `initial-request.md`. The Codex reference documents only `CODEX_HOME`. The
  variables Codex sets for the commands it runs are not documented there.
