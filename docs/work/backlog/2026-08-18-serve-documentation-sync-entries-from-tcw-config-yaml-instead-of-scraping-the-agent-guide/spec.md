# Spec — Serve documentation-sync entries from tcw-config.yaml instead of scraping the agent guide

## Capability changes

**New.** Two capability records under `docs/capabilities/work/`:

- *Declare which documents track which changes* — a project lists its
  documentation entries in `tcw-config.yaml` and TCW validates them.
- *Read the documentation gate for a change* — `tcw work docs` prints those
  entries, and `tcw work stage plan|implement` includes them inline.

**Changed.** The existing lifecycle-stage capabilities gain the fact that a
stage's built-in instructions can now carry project data, not only fixed text.
No records are written at this stage; the ledger is reconciled at completion.

## Problem

TCW's own built-in prompts instruct the agent to go and read a Markdown section
out of a file TCW does not own:

- `tcw/work/prompts/plan.md:20-21` — "Evaluate every Documentation Sync entry in
  the project's agent guide (`AGENTS.md` or `CLAUDE.md`) and name a task for each
  trigger that will fire."
- `tcw/work/prompts/implement.md:27-28` — the same instruction at the gate.

`skills/documentation-sync/SKILL.md:8` states the convention those prompts rely
on: "check the project's `CLAUDE.md` for a `## Documentation Sync` section". The
entries live as a Markdown bullet list of the shape
`- path [Trigger] — description`.

Four consequences, each verifiable today:

1. **Nothing validates it.** `tcw validate` returns `validate OK` on a project
   whose section has a typo'd trigger, a path that does not exist, or a missing
   bracket. Confirmed: `grep -rn 'documentation.sync\|Documentation Sync' tcw/
   --include=*.py` returns nothing — no Python in the package knows the feature
   exists. The only mentions are the two prompt files and
   `tcw/work/templates.py:78-80`.
2. **It is not guaranteed**, which this project's own harness rule
   (`docs/lifecycle/harness.md`) says is disqualifying: "anything that must be
   guaranteed belongs in the `tcw` CLI". A gate that fires only if the agent
   remembers to open a file and parse prose is not guaranteed under either
   harness.
3. **It cannot use the machinery built for exactly this.** v1.0.0 shipped
   `builtin:`/`blob:`/`file:`/`generate:`/`when:` so a project can bind its own
   instructions to a stage. Documentation entries — the most project-specific
   instructions there are — are the one thing that cannot flow through it.
4. **It blocked a real migration.** The item completed immediately before this
   one moved this repository's stage-scoped rules into `docs/lifecycle/`, and had
   to leave `## Documentation Sync` behind in `AGENTS.md` precisely because the
   skill name-matches it there. That was recorded as a limitation in
   `docs/migration-guide-0.21.X-to-1.0.0.md`; it is a defect.

## Goals

1. Documentation entries are project **configuration** in `tcw-config.yaml`,
   parsed and validated like every other `work.*` block.
2. `tcw work stage plan` and `tcw work stage implement` print the project's
   actual entries, through the same resolution path as any other stage text.
3. A project extends or overrides that text with the bindings it already has.
4. A project that has configured nothing behaves **exactly** as it does today.
5. This repository can move `## Documentation Sync` out of `AGENTS.md`.
6. The change folds into the unpushed v1.0.0.

## Non-goals

- Redesigning the trigger vocabulary. It moves and gains shape-validation; its
  meanings are unchanged, and it stays an **open** set (see Design).
- The `## Versioning` section, which `skills/documentation-sync/SKILL.md:117`
  also name-matches in `CLAUDE.md`. Same class of defect, separate decision.
  Named in the outcome, not fixed here.
- A general templating engine for built-in prompts. **One** placeholder is
  introduced; a second one is the trigger to generalize, not this.
- Making TCW parse the legacy Markdown section. TCW never reads it — the
  fallback instruction tells the *agent* to, exactly as today.
- Rewriting the four earlier migration guides.

## Design

### Where the entries live

```yaml
# tcw-config.yaml
work:
    documentation:
        - path: README.md
          trigger: Public-API
          description: >-
              Public-facing overview and `tcw` CLI usage. Update when the public
              CLI surface or user-facing behavior changes.
        - path: docs/changelogs/upcoming.md
          trigger: Any-Code-Change
          description: Developer changelog; technical, grouped by category.
```

Three required keys per entry, all non-empty strings. Parsed by a new
`parse_documentation_entries(raw) -> tuple[list[DocEntry], list[str]]` in
`tcw/store/base.py`, mirroring `parse_lifecycle_policy` (`tcw/store/base.py:1019`)
in shape: pure, filesystem-free, never raises, returns an advisory problem list
that `tcw validate` surfaces and the adapter discards.

**The plumbing, stated rather than assumed.** `LifecyclePolicy` is built from
`work.lifecycle` alone (`tcw/store/fs.py:2640`), so it does **not** carry these
entries and must not be made to — `work.documentation` is a sibling config block,
not part of the lifecycle policy, and folding it in would mean every
`parse_lifecycle_policy` caller silently acquires a second concern. The path is:

1. `DocEntry` (frozen dataclass: `path`, `trigger`, `description`) in
   `tcw/store/base.py`, beside `StageBindings`.
2. **`WorkStore.documentation() -> list[DocEntry]`** on the abstract interface,
   with the precedent that `lifecycle_policy()` (`tcw/store/base.py:1385`) is
   already a config-derived method on the ABC rather than an adapter detail.
3. `FsWorkStore.documentation()` reads `self._work_config().get("documentation")`
   through the same `_work_config` helper (`tcw/store/fs.py:2613`) that
   `lifecycle_policy`, `auto-commit-transitions`, and `trunk-branch` use.
   `FsWorkStore.documentation_problems()` mirrors `lifecycle_problems`
   (`tcw/store/fs.py:2643`) for `tcw validate`.
4. `resolve_prompts` gains a `documentation: Sequence[DocEntry] = ()` keyword,
   defaulted so every existing caller compiles unchanged and resolves to the
   fallback.
5. `tcw work stage` and `tcw work docs` pass `st.documentation()`.

A non-filesystem adapter implements one method reading its own node config. That
is the whole obligation, which is why this belongs on the interface.

**Validation is shape-only, deliberately.** `tcw validate` reports: a non-list
`documentation:`, an entry that is not a mapping, a missing or blank `path` /
`trigger` / `description`, a `path` that is absolute or escapes the node, a
`trigger` containing whitespace, and a duplicate `path`. It does **not** check
the trigger against a closed vocabulary, because
`skills/documentation-sync/SKILL.md:56` explicitly declares the set open —
"Projects may define additional named triggers… Treat any such project-defined
trigger as authoritative for that project." A whitespace check catches the
realistic typo (`Public API`, a dropped bracket) without closing a set the design
says is open.

Entry `path` is **not** required to exist. A Documentation Sync entry routinely
names a file the project intends to create; `references/setup.md` in the skill
exists to create them. Requiring existence would make `tcw validate` fail on a
correctly-configured new project.

### How the entries reach the prompt

The two built-in prompts gain one placeholder token, `{{tcw:documentation}}`.

**Substitution happens in `resolve_prompts`, on the joined `res.text`** — not in
`_resolve_one`. `_resolve_one` is shared: `resolve_artifact` calls it with
`role="artifact"` (`tcw/work/resolve.py:277-281`), so substituting there would
also rewrite artifact templates. Worse, it would do so *inconsistently*, because
`tcw work scaffold`'s implicit built-in fallback bypasses `_resolve_one`
entirely (`tcw/work/cli.py:896-897`): an explicitly-bound `builtin` template
would be substituted and the default one would not.

Doing it in `resolve_prompts` fixes both at once — `resolve_artifact` is a
separate function and is left alone, so artifact templates never see the token —
and it has a deliberate bonus: a project's own `file:` or `blob:` prompt may use
`{{tcw:documentation}}` too, since the substitution runs over the composed text.
That is what makes this "the same prompt generation" rather than a built-in-only
special case.

The token resolves to:

- **Entries configured** → a rendered block: one Markdown table row per entry
  (`| path | trigger | what to write |`), preceded by the one-line instruction
  that the entries are the project's own.
- **Nothing configured** → the exact sentence those prompts carry today, so the
  resolved bytes are unchanged for every project that has not adopted this.

Substituting at resolve time rather than in `load_builtins()` is forced:
`load_builtins()` (`tcw/work/resolve.py:47`) takes no node context and is loaded
once per process, so a project's entries cannot reach it.

**Rendering is a list, not a table** — deliberately. A Markdown table row is
delimited by `|`, and a `description` containing one would break the table
silently. A list has no such delimiter:

```
- `README.md` — **[Public-API]**
  Public-facing overview and `tcw` CLI usage. Update when the public CLI
  surface or user-facing behavior changes.
```

`path` and `trigger` are validated to contain no newline; `description` has its
internal newlines collapsed to single spaces at render time, so a YAML block
scalar cannot break out of its bullet. No escaping rule is needed because no
delimiter is load-bearing.

**The 50-line prompt ceiling is unaffected.**
`tests/test_shipped_prompts.py:50` asserts
`len(load_builtins().stage_prompts[sid].splitlines()) <= 50` — it measures the
**authored source**, which the placeholder makes one line shorter, not the
resolved output. `plan.md` is at 41 and `implement.md` at 40 of 50. A project
with forty documentation entries renders a long prompt, and that is the project's
own doing rather than a ceiling TCW should enforce on it.

### The third invocation point

The skill runs at three points, and only two are stages
(`skills/documentation-sync/SKILL.md`, the lifecycle table): `plan`, the end of
`implement`, and the version offer **after** `complete`. The third has no stage —
`tcw work stage implement <slug>` on a completed item is refused by the status
check at `tcw/work/cli.py:786-790`, correctly.

So: **`tcw work docs [--json]`**, a read-only verb that prints the node's entries
and changes nothing.

```
$ tcw work docs
README.md                      [Public-API]       Public-facing overview and …
docs/changelogs/upcoming.md    [Any-Code-Change]  Developer changelog; …
```

`--json` emits `{"schema": 1, "source": "config" | "agent-guide", "entries": [...]}`.
`source` is what lets the skill branch without guessing: `agent-guide` means the
node configured nothing and the skill should do exactly what it does today.

**The fallback introduces no new ambiguity, because its text is byte-identical to
today's.** The built-in prompts name "the project's agent guide (`AGENTS.md` or
`CLAUDE.md`)" and the skill names `CLAUDE.md`; those two already disagree, and
this spec neither widens nor narrows it. Recorded as a pre-existing inconsistency
in `## Notes` rather than fixed here, because fixing it means deciding a
precedence rule that has nothing to do with this change.
Entries go to stdout alone; errors to stderr; nothing on stdout on failure —
the same contract `tcw work stage` established.

### The skill

`skills/documentation-sync/SKILL.md` is repointed: the entry table comes from
`tcw work docs --json`, falling back to the `## Documentation Sync` section when
`source` is `agent-guide`. The trigger reference, the partition rule, the
evaluation loop, and the three companion references are unchanged — this moves
where the entries come from, not how they are judged.

`references/setup.md` gains the config form as the recommended shape, keeping the
Markdown section documented as the fallback.

**Four more places read the section and would contradict the change if left.**
Found by review, not by the first pass:

| Location | What it says |
| -------- | ------------ |
| `skills/documentation-sync/SKILL.md:62` | "For each file listed in the Documentation Sync section" — the evaluation loop's own input. |
| `skills/documentation-sync/SKILL.md:101` | Defines "changelog files" as those "listed in the project's `## Documentation Sync` section". |
| `skills/documentation-sync/references/release-notes-and-changelogs.md:5,7` | Gates the whole opt-in structure on what "the project's `## Documentation Sync` section explicitly lists". |
| `docs/lifecycle/implementation.md:20-23` | This repo's own implement-stage prompt, which currently explains that the section *cannot* move. |

All four are rewritten to read "the project's documentation entries
(`tcw work docs`)", keeping the Markdown section named only as the fallback.
`docs/lifecycle/implementation.md` loses its explanation entirely, since the
constraint it explains is what this item removes.

### This repository

`work.documentation` in `tcw-config.yaml` gets the four entries currently in
`AGENTS.md`, and the `## Documentation Sync` section is removed — completing the
migration the previous item could not finish. `## Versioning` stays; it is
out of scope.

### Abstraction litmus test

Three operations are added. Verdicts:

| Operation | Verdict |
| --------- | ------- |
| Read a node's documentation entries | **Model.** `tcw-config.yaml` is node configuration, not store content; a Jira-backed node has one exactly as a filesystem node does, the same way `work.tags` and `work.lifecycle` already work. |
| Render entries into a stage's prompt text | **Model.** Pure text substitution over data already in the policy. No filesystem, no store access. |
| `tcw work docs` | **Model.** Reads node configuration and prints it. Composes no store path and does not touch the work store at all. |

Nothing here is a filesystem trick. The one thing that would have been —
TCW parsing `CLAUDE.md` to extract the legacy section — is explicitly a non-goal;
the fallback tells the *agent* to read the file, which is what happens today and
requires no capability of the store.

## Acceptance criteria

1. `tcw validate` reports a problem naming the entry index and key for each of:
   a non-list `documentation:`, a non-mapping entry, a blank `path`, a blank
   `trigger`, a blank `description`, an absolute `path`, a `path` escaping the
   node, a `trigger` containing whitespace, and a duplicate `path`.
2. `tcw validate` exits 0 on a `documentation:` entry whose `path` does not exist
   on disk, and on a project-defined trigger not in the four-name base set.
3. On a node with no `work.documentation`, `tcw work stage plan <slug>` and
   `tcw work stage implement <slug>` produce **byte-identical** output to the
   same commands before this change. Pinned by a recorded fixture, not by eye.
4. On a node with entries, both commands print every entry's path, trigger, and
   description, and do **not** print the agent-guide fallback sentence.
5. `tcw work docs` lists every configured entry; `tcw work docs --json` parses
   and reports `"source": "config"`.
6. On an unconfigured node, `tcw work docs --json` reports
   `"source": "agent-guide"` with `"entries": []`, and exits 0.
7. `tcw work docs` writes nothing. Asserted by hashing every path under the work
   store and the node config before and after the call and comparing the two
   manifests — not by `git status`, which is meaningless in a tree that is
   intentionally dirty during implementation and would not catch a write
   followed by a restore.
7a. `{{tcw:documentation}}` placed in an **artifact** template is left verbatim
   by `tcw work scaffold`, whether the template is bound explicitly or falls
   back to the built-in. Substitution is a prompt-role behavior and the two
   scaffold paths must agree.
7b. `{{tcw:documentation}}` in a project's own `file:` or `blob:` **prompt**
   binding is substituted, same as in the built-in.
8. `tests/test_shipped_prompts.py` passes unchanged: both edited prompts stay
   within the 50-line ceiling.
9. `tests/fixtures/lifecycle_baseline/` passes **without re-capture**.
   `tcw work lifecycle` reports bindings and resolves no `builtin`, so editing
   built-in prompt text must not move any recorded row. If it does, the
   assumption is wrong and the spec is wrong.
10. `skills/documentation-sync/SKILL.md` names `tcw work docs` and no longer
    instructs the reader to find entries in `CLAUDE.md` except as the documented
    fallback. `tests/test_documentation_sync_wiring.py` passes.
11. This repository's `AGENTS.md` has no `## Documentation Sync` section, its
    `tcw-config.yaml` carries the four entries, and `tcw work stage implement`
    on a real item prints all four.
11a. No file in the repository instructs a reader to find documentation entries
    in a Markdown section except as the named fallback — specifically
    `skills/documentation-sync/SKILL.md:62,101`,
    `skills/documentation-sync/references/release-notes-and-changelogs.md:5,7`,
    and `docs/lifecycle/implementation.md`.
12. `docs/migration-guide-0.21.X-to-1.0.0.md` no longer advises readers to work
    around the limitation, and instead documents the configuration form.
13. `python -m pytest -q` reports ≥ 1592 passed and 0 failed — the baseline
    measured at the close of the preceding item.

## Risks

- **Criterion 3 is the whole back-compat story and is easy to get subtly wrong.**
  `_join` (`tcw/work/resolve.py:214`) rstrips parts and joins with one blank
  line, so a substitution that leaves a stray blank line changes bytes without
  changing meaning. Mitigated by recording the fallback output *before* the
  change, in its own commit, exactly as `tests/fixtures/lifecycle_baseline/`
  was built.
- **The placeholder is a new concept in built-in prompts.** One token, one
  substitution site. The named ceiling: if a second placeholder is ever wanted,
  this becomes a templating engine and should be generalized deliberately rather
  than by adding a second special case.
- **Two sources of truth during the transition.** A project could configure
  `work.documentation` *and* keep a `## Documentation Sync` section, and they
  could disagree. Config wins and the skill never reads the section when
  `source` is `config`, but nothing warns about the stale section. Accepted;
  a warning is a follow-up, not a blocker.
- **`WorkStore` grows a method, which every future adapter must implement.**
  That is the cost of putting it on the interface rather than in the FS adapter,
  and it is the right cost: a node's documentation entries are node
  configuration, and an adapter that cannot report them cannot serve the gate.
- **Folding into v1.0.0 rewrites a tag.** Safe only because the tag is local —
  `skills/documentation-sync/scripts/unpushed-version.sh` exists to prove that
  (exit 0 = still local), and it is run before the fold rather than assumed.

## Notes

- Verified rather than recalled: `grep -rn 'documentation.sync\|documentation_sync\|Documentation Sync' tcw/`
  returns three files — `tcw/work/prompts/plan.md`, `tcw/work/prompts/implement.md`,
  and `tcw/work/templates.py` — and no Python that implements anything.
- Current prompt lengths, measured: `implement.md` 40 lines, `plan.md` 41,
  ceiling 50.
- Criterion 13's baseline (1592 passed) is from the completed item
  `2026-08-18-migrate-tcw-itself-to-the-1-0-0-lifecycle-and-write-the-consumer-migration-guide`,
  `outcome.md`.
- Criteria 1–11 and 13 are executable and will be run at `implement`. Criterion
  3's fixture must be captured **before** the prompts are edited, or it records
  the new behavior and proves nothing — the same discipline
  `tests/fixtures/lifecycle_baseline/capture.py` documents.
- **Criterion 9's assumption was tested, not reasoned.** No row in
  `tests/fixtures/lifecycle_baseline/self.json` contains the string
  "Evaluate every Documentation Sync" — `tcw work lifecycle --stage plan
  --directive` reports which bindings are configured and resolves no `builtin`.
  So editing built-in prompt text cannot move the corpus, and criterion 9 asserts
  that rather than hoping for it.
- All other spec citations re-resolved before commit. Two were wrong and are
  fixed above: the open-trigger-set statement is at `SKILL.md:56`, not `:54`
  (`:54` is the partition rule), and `unpushed-version.sh` ships inside the skill
  at `skills/documentation-sync/scripts/`, not in the repo's top-level `scripts/`.
- **Reviewed by `codex` before planning; six defects, all verified against the
  tree and all accepted.** They changed the design rather than decorating it:
  the substitution site moved from `_resolve_one` to `resolve_prompts` (it would
  have rewritten artifact templates, and inconsistently, since
  `tcw work scaffold`'s implicit fallback bypasses `_resolve_one`); the
  `LifecyclePolicy`-carries-the-entries assumption was wrong and the plumbing is
  now specified through the `WorkStore` interface; four more documents that read
  the Markdown section were found; the Markdown table became a list because a
  `|` in a description would have broken it; the fallback's determinism is now
  stated; and criterion 7 stopped resting on `git status`.
- `bllm-review` was again unavailable — the invocation from the previous item was
  still running after an hour having produced nothing, so no second review was
  attempted. This spec, like the last, has had one reviewer rather than two.
