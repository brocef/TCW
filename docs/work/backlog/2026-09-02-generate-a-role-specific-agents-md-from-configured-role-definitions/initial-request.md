# Generate a role-specific AGENTS.md from configured role definitions

A project is worked on by people in different roles — say a software engineer, a
UI/UX engineer, and a product designer. They share one repository, but they
should not share one set of agent instructions. The engineer wants full-stack
development. The UI/UX engineer wants "do not build backend features; if you are
prototyping, stub every API call and return mock data." The product designer
wants that too, plus "I am not an engineer — communicate without technical
jargon."

Today all three get whatever single `AGENTS.md` is committed to the repository.

**What is being asked for:** a new top-level TCW feature that builds a project's
agent guide per person, the way `work.lifecycle` already builds a stage's
instructions per project. When someone first clones the repo and works through
its setup instructions, they run one `tcw` command, say which role they are, and
get an `AGENTS.md` (and `CLAUDE.md`) written for that role.

The requester's framing: **the work lifecycle system is polymorphic — the
repository manager constructs the prompt-generating mechanism for each stage.
Do the same for a project's agent guide.**

## The composition model the requester asked for

Not plain concatenation. Roles share most of their content, and that content must
be declared once:

- **Fragments** — named chunks of text, declared in YAML as a string mapping.
  Sketched by the requester:

    ```yaml
    preamble: Preamble text here
    project-commands: >-
        ```bash
        pnpm run typecheck   # tsc --noEmit
        pnpm run lint        # prettier --check + eslint
        pnpm run test        # vitest run
        ```
    engineer-instructions: Build stuff in this particular way, more instructions…
    product-instructions: Stub out all API functions the user asks you to make.
        The user is not an engineer, so do not use technical jargon.
    ```

- **A template per role** — a Markdown file that places fragments by name.
  Sketched as `AGENTS-engineer-template.md`:

    ```
    {preamble}

    {project-commands}

    {engineering-instructions}
    ```

  and `AGENTS-product-template.md` as the same first two fragments followed by
  `{product-instructions}`.

Sharing is what the template model is _for_: `preamble` and `project-commands`
are written once and appear in every role's guide.

## Constraints the requester set

These were decided in conversation and are not open for the spec to re-litigate,
though the spec owns how each is realized.

1. **A new top-level command group**, alongside `taxonomy`, `capabilities` and
   `work` — not a subcommand of `work`. An agent guide is not scoped to an item,
   a status, or a transition.
2. **No fourth store.** Role definitions are node configuration, discovered
   through `tcw-config.yaml`, the way `work.lifecycle` and `work.documentation`
   already are — so `tcw validate` can check them.
3. **Discovered files, not inline content.** `tcw-config.yaml` names the roles,
   their templates, and the fragment YAML files. The bulky content lives in files
   that can be cited from source, syntax-highlighted, and diffed.
4. **A fragment's value may be an inline string, a file, or the output of a
   script** — the same three sources a lifecycle prompt binding already has. A
   `project-commands` fragment derived from `package.json` should be able to
   never go stale.
5. **`{{fragment-name}}`** as the placeholder syntax — double braces, matching
   the existing `{{tcw:documentation}}` convention — so a fragment containing a
   code fence, JSON, or shell brace expansion needs no escaping.
6. **The generated guide is not committed.** Three people generating three
   different files into one tracked path is a merge conflict on every pull. The
   output is gitignored, and content that used to live in a committed
   `AGENTS.md` moves into fragments that every role's template includes.
7. **The chosen role is remembered**, per checkout and gitignored, so nobody
   re-answers the prompt on every run. It is a node-level identity that other
   TCW commands could read later; only the guide builder consumes it now.
8. **Output targets are configurable**, defaulting to `AGENTS.md` and
   `CLAUDE.md`, and TCW should recognize the Cursor, Copilot and Gemini
   instruction paths out of the box.
9. **A duplicate fragment key across declared YAML files is an error**, naming
   both files. One designated gitignored overlay file is the exception: it may
   override, so a person can add standing instructions of their own without
   editing shared config or dirtying the working tree.
10. **TCW's own `AGENTS.md` becomes generated** by this mechanism. The requester
    chose this deliberately as dogfooding; it is a migration for this repo.

## Scope

One work item, not an epic: the configuration model, the generate command, the
`tcw validate` coverage, and this repository's own migration. Deliberately
**out of scope** for it — recorded so they are not silently dropped:

- Detecting that a generated guide has gone stale against changed config.
- Role-aware behavior anywhere else in TCW (a `when: {role: …}` condition on
  lifecycle bindings, a role-filtered board). The persisted role must be shaped
  so this is possible later; nothing should consume it yet.
- Editing roles or fragments through `tcw serve`.

## Notes

- **Asked for reference material; none provided.** The requester's position is
  that the codebase is the reference. The spec should read `tcw/work/resolve.py`
  (binding resolution, node-root confinement, the `{{tcw:documentation}}`
  substitution), `tcw/work/generate.py` (the bounded script runner),
  `tcw-config.yaml`'s `work.lifecycle` block, and the "If you are moving rules
  out of your agent guide" section of `docs/migration-guide-0.21.X-to-1.0.0.md`.
- The requester opened with "what do you think?" and the constraints above are
  the outcome of that conversation, not an unreviewed wish list. Each was chosen
  over stated alternatives — a `work`-scoped verb, a fourth store, inline-only
  fragments, a convention-based directory with no config, and last-file-wins
  merge semantics were all considered and rejected.
- Constraint 6 conflicts with how this repository works today: `AGENTS.md` is
  committed and `CLAUDE.md` is a symlink to it. The requester accepted that
  migration when choosing it. The spec should say what happens to a project that
  already tracks the file it is now asked to generate.
- Constraint 8's symlink question is open. `CLAUDE.md` as a symlink to
  `AGENTS.md` was the requester's original sketch, but symlinks need developer
  mode on Windows. Whether targets are written as files or links is the spec's
  call.

## References

_Asked; none provided — see Notes for what the spec should read from the
codebase itself._
