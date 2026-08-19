# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category.

## Internal

- **This repository configures its own work lifecycle.** `tcw-config.yaml` gains
  a `work.lifecycle` block: `prompt:` bindings on `spec`, `plan`, and
  `implement`, each led by `builtin: true` so TCW's shipped instructions are
  composed with rather than replaced; a `when: { tags: [bug] }` spec template
  under `artifacts:`; and two `pre:` checks. Nothing under `tcw/` changes — this
  is the node's own configuration, and the first exercise of the 1.0.0
  configuration surface against a project with real rules.
- **`docs/lifecycle/`** holds the prose those bindings resolve: `abstraction.md`
  (the litmus test and the abstract spine, bound at `spec` and `plan`),
  `harness.md` (Claude/Codex parity, bound at `spec` and `implement`),
  `implementation.md` (the implementation rules, bound at `implement`), and
  `templates/spec.md` + `templates/spec-bug.md`. All moved verbatim out of
  `AGENTS.md`, which drops from 80 lines to 54.
- **`scripts/require_artifact.py`** — the `plan` stage's `pre` check. Reads
  `TCW_SLUG` from the hook environment and asks `tcw work show --json` whether a
  named artifact is present, rather than composing a store path. Not packaged
  (`pyproject.toml` includes `tcw*` only); fails closed on an unset `TCW_SLUG`,
  a missing `tcw`, or unreadable JSON.
- **`tests/test_repo_lifecycle.py`** — five tests over the real repo tree rather
  than a `tmp_path` fixture, since the subject is this node's own configuration.
  The load-bearing one is `test_repo_templates_carry_every_builtin_heading`:
  `artifacts:` is first-match-wins, so a bound template replaces the built-in,
  and nothing else would catch this repo's `spec` template drifting from
  `tcw.work.templates._SPEC` when a future release adds a section.
  `test_the_moved_rules_are_reachable` is what makes deleting the prose from
  `AGENTS.md` safe to commit.
- **Ten references repointed** from `AGENTS.md` to `docs/lifecycle/` —
  `README.md` (2), `tcw/store/base.py` and `tcw/store/fs.py` (module docstrings,
  comment text only), and `docs/plan/` (6). `AGENTS.md` keeps
  `## Documentation Sync` and `## Versioning`, which
  `skills/documentation-sync/SKILL.md` locates by name in `CLAUDE.md` and which
  therefore cannot move into a stage prompt.
- **`docs/migration-guide-0.21.X-to-1.0.0.md`**, linked from
  `docs/release-notes/v1.0.0.md`.

## Added

- **`tcw/stdin.py`** — `read_piped_stdin()`, the single bounded reader all intake
  paths use, plus `StdinTruncated`. The read is `select`-gated per chunk, so the
  bound measures a *gap in the stream* rather than total duration: a producer
  that streams for a minute is read in full, one that never starts gives up after
  one interval. New module rather than a home in `tcw/cli.py`, which imports all
  three component CLIs and would cycle.
- **`TCW_STDIN_TIMEOUT`** (seconds, float; `0` disables waiting) overrides the
  2.0s default. Unparseable or negative values fall back to the default silently —
  a malformed environment variable must not break item creation.

## Fixed

- **The three duplicated `_stdin_body()` copies are gone.** `tcw/work/cli.py`,
  `tcw/taxonomy/cli.py`, and `tcw/capabilities/cli.py` each carried the same
  `if sys.stdin.isatty(): return "" / sys.stdin.read()` body. `isatty()` false
  means "not a terminal", not "a pipe with data", so an inherited-and-open
  descriptor blocked forever. Five call sites now share one implementation:
  `work new`, `work delegate`, `work escalate`, `taxonomy add`,
  `capabilities add`. `taxonomy add`'s `args.description or …` short-circuit is
  preserved.
- **`StdinTruncated` subclasses `ValueError`** so all five sites report it as
  `tcw <command>: <message>` with exit 1 through the `except` clauses they
  already had — no new error handling was added anywhere.
- **`tcw/work/hooks.py` runs `command:` bindings with `stdin=subprocess.DEVNULL`.**
  Previously they inherited the caller's stdin, so a hook that read it could
  consume the piped intake or stall to the full hook timeout — which aborts the
  transition, not merely delays it. `tcw/work/generate.py` is unchanged: its
  `Popen` owns `stdin=PIPE` deliberately and writes the payload.

## Internal

- `tests/test_stdin.py` drives real descriptors (pipe, devnull, regular file,
  socketpair, closed fd) rather than mocks. `tests/test_stdin_cli.py` shells out,
  because a parent holding a pipe's write end open is not reproducible in-process.
- **Every `subprocess` spawn under `tcw/` now declares its stdin**, and
  `tests/test_subprocess_stdin.py` walks the package AST to keep it that way.
  `tcw/store/fs.py` gained a `_git()` helper covering its 19 git calls; four
  singletons in `store/project.py`, `work/cli.py`, `serve/__init__.py` and
  `serve/runtime.py` close it inline. This closes **no known hang** — git
  redirects its own hooks' stdin (measured), no TCW git call contacts a remote,
  and none takes input on stdin. It is an explicitness invariant with a test
  behind it, and the test earned its place: it found the `tcw serve` node server
  holding fd 0. Timeouts on git calls remain out of scope.

## Changed

- **The two artifact-presence rules are now stated on the `WorkStore` interface.**
  `artifacts()` answers *did this stage produce anything?* — present means
  non-whitespace content, so a blank artifact is **absent**. `read_artifact`
  answers *is there a resource at this name?* — mere existence, so the same blank
  artifact **is** returned, with a revision. Both docstrings now say so, and say
  why they must differ: routing the read through the content rule makes it
  contradict `write_artifact`, which still sees the file and refuses
  `revision=""` as stale. `read_sidecar` and `read_plan_stage` are annotated with
  the same resource rule; `FsWorkStore._present` no longer calls itself "the one
  presence rule".

  **No behavior change in the store layer** — verified structurally by comparing
  the ASTs of `tcw/store/base.py` and `tcw/store/fs.py` before and after with
  docstrings stripped; both are identical. This is a contract change for anyone
  implementing the interface: an adapter reporting a blank field as present from
  `artifacts()` was within the documented contract before and is not now.

## Internal

- **`tcw serve` no longer reports two different presence answers in one payload.**
  Writing the rules down exposed that the work-detail endpoint derived its
  `present` flag from `read_artifact` returning content, while the tab it gates
  is opened through the lifecycle rule — so a whitespace-only artifact rendered
  as present and then 404'd on click. The flag now comes from `artifacts()`.
  Reproduced over real HTTP before and after.

- `tests/test_work.py::test_the_two_artifact_presence_rules_disagree_on_purpose`
  pins all four facts about a whitespace-only artifact in one test, so none can be
  "fixed" in isolation. It was needed: with `read_artifact` mutated to use
  `_present`, **388 tests across the work-store, scaffold, serve, projection and
  show-json suites passed and only this one failed**.

## Added

- **`work.documentation` in `tcw-config.yaml`** — a list of `{path, trigger,
  description}` entries. `DocEntry` and `parse_documentation_entries` in
  `tcw/store/base.py` mirror `parse_lifecycle_policy`: pure, filesystem-free,
  never raises, advisory problem list. Validation is **shape-only** by design:
  the trigger vocabulary is explicitly open, and `path` is not required to exist
  (this repo's own entry is the pattern `skills/<component>/SKILL.md`).
- **`WorkStore.documentation()`** on the abstract interface, with
  `FsWorkStore.documentation()` / `documentation_problems()` reading through the
  existing `_work_config` helper. On the ABC rather than the adapter for the same
  reason `lifecycle_policy()` is: it is node configuration, and an adapter that
  cannot report it cannot serve the gate.
- **`tcw work docs [--json]`** — read-only; `{"schema": 1, "source":
  "config"|"agent-guide", "entries": [...]}`. Serves the skill's third invocation
  point (the version offer after `complete`), which has no stage to hang off
  because `tcw work stage implement` on a completed item is correctly refused.
- **`{{tcw:documentation}}…{{/tcw:documentation}}`** in stage prompts, with
  `render_documentation` and `substitute_documentation` in `tcw/work/resolve.py`.

## Changed

- `tcw/work/prompts/plan.md` and `implement.md` wrap their documentation
  instruction in the new span. `resolve_prompts` gained
  `documentation: Sequence[DocEntry] = ()`, defaulted so every existing caller
  compiles unchanged.
- This repository's four documentation entries moved from `AGENTS.md` into
  `tcw-config.yaml`; `docs/lifecycle/implementation.md` lost the paragraph
  explaining that they could not move. `skills/documentation-sync/` and its
  references now take entries from `tcw work docs`, naming the Markdown section
  only as the fallback.

## Internal

- **The span carries its own fallback, which is a change from the spec's design.**
  The spec assumed one token with a fallback string held in Python. The two
  prompts word the instruction differently, so one constant could not reproduce
  both byte-for-byte. Putting the fallback inside the span makes back-compat
  hold *by construction* and keeps prompt prose in the prompt file.
- Substitution runs in `resolve_prompts` over the joined text, **not** in
  `_resolve_one`, which `resolve_artifact` also uses and which
  `tcw work scaffold`'s implicit built-in fallback bypasses. So an artifact
  template containing the token is left verbatim by both scaffold paths, while a
  project's own `file:`/`blob:` prompt gets substitution. Both pinned by tests.
- `tests/fixtures/prompt_fallback/` was captured **before** any prompt was
  touched, in its own commit, and `tests/test_prompt_fallback.py` replays it —
  the back-compat guarantee is evidence rather than an assertion.
- Rendering is a list, not a table: a `|` in a description would break a table
  silently. Continuation lines are indented to the token's column, and the prose
  after a span resumes at the list indent rather than one column deeper — at four
  spaces after a list, CommonMark reads it as a code block.

