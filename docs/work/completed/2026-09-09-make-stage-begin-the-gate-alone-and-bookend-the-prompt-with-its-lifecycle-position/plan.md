# Plan: `stage gate` alone, and bookended prompts

Five tasks. The suite is green at every commit boundary. The rename and the
behaviour change land together, because a commit that renames without narrowing
ships a verb whose name lies for one revision.

## Task 1 — The bookend table and the wrapper

**Modifies:** `tcw/store/base.py` (the table), `tcw/work/resolve.py` (the wrap).

`STAGE_NEXT_STEPS`, keyed by stage id, beside `STAGE_STATUSES` — lifecycle
metadata, which is where the sibling table already lives. `postmortem` maps to
the empty string, meaning "nothing follows", and the wrapper renders that as a
sentence rather than skipping the section, so a reader never wonders whether the
footer failed to resolve.

`resolve_prompts` wraps its result. Wrapping happens **after** binding
resolution and unconditionally, so a project's own `prompt:` bindings are
bookended exactly as the built-in floor is.

**Proves it:** criteria 7, 8, 9, 10.

## Task 2 — `gate`: the rename and the narrowing

**Modifies:** `tcw/work/cli.py`.

- `begin` becomes `gate` in the subparser, in every message, and in the
  removed-form handler's advice.
- `_stage` stops calling the shared tail. It resolves the item, checks legality,
  runs the `pre` bindings, prints the pointer line on stderr, and returns.
- `_stage_tail` is now reached only by `prompt`, so it is folded back into
  `_stage_prompt`. This undoes Task 1 of the split item, which extracted it
  because the two verbs shared a tail; they no longer share one. Recording that
  rather than leaving a helper with one caller.
- `prompt` accepts `--no-exec`: plan on stderr, stdout empty, exit 0. The
  refusal branch and its message go.

**Proves it:** criteria 1–6, 11, 12.

## Task 3 — The recorded fixture

**Modifies:** `tests/fixtures/prompt_fallback/capture.py`,
`tests/fixtures/prompt_fallback/unconfigured.json`.

Re-captured, not hand-edited — the opposite of what the split item did, and for
the opposite reason. That file froze the prompt bytes to prove the split did not
change them. This change **does** change them, deliberately, by adding the
bookends. Keeping the old bytes would assert something now false.

The docstring says so, names this release, and keeps the rule for every future
change: re-capture only when the release intends the text to move, and say which
release did it.

**Proves it:** criterion 14.

## Task 4 — Documents

**Modifies:** the seven `stage-*.md`, `skills/tcw-work-stage/SKILL.md`,
`skills/tcw-work/references/commands.md`, `.../hooks.md`,
`.../lifecycle/default/README.md`, `skills/documentation-sync/SKILL.md` and its
`references/setup.md`, `AGENTS.md`, `docs/guide/configuration.md`,
`docs/guide/work.md`, the three capability descriptions,
`tcw/work/templates.py`, `tcw/work/resolve.py` and `tcw/store/base.py`
docstrings, `scripts/require_artifact.py`, and the four
`tests/cli/scenarios/` documents.

Each stage document names both verbs: `gate` to enter, `prompt` to read. The
parity test's literal becomes `tcw work stage gate <id>`.

The composing skill drops its own gate paragraph — the resolved prompt now
carries the header itself, and two copies would drift.

**Proves it:** criterion 13.

## Task 5 — Documentation Sync

**Modifies:** `docs/migration-guide-1.X-to-2.0.0.md` (rewritten — its central
promise that `begin` behaves exactly as 1.x did is now false and there is no
`begin`), `docs/release-notes/upcoming.md`, `docs/changelogs/upcoming.md`,
`README.md` **[Public-API]** — checked, not assumed; it names no stage verb.

**Proves it:** criteria 15, 16.

## Documentation Sync

| Entry | Trigger | Fires | Task |
| --- | --- | --- | --- |
| `README.md` | Public-API | check only — it names no `tcw work stage` form | 5 |
| `docs/release-notes/upcoming.md` | Public-API | yes | 5 |
| `docs/changelogs/upcoming.md` | Any-Code-Change | yes | 5 |
| `skills/<component>/SKILL.md` | Skill-Driven-Component | yes — the component's CLI surface changes again | 4 |

## Risks

- **The header becomes wallpaper.** It is prepended to every prompt an agent
  ever reads, so it will be skimmed. Mitigated only partly, by keeping it to two
  sentences and by `gate` remaining the thing every stage document names first.
  Worth revisiting at post-mortem: if agents stop running the gate, this change
  cost more than the duplication it removed.
- **Re-capturing the fixture is irreversible evidence loss.** The bytes it held
  proved the split was text-preserving. After this they prove nothing about the
  split. Task 3 records that in the file itself so a future reader does not
  mistake the new capture for the old guarantee.
- **Two breaks to one command in one release.** Acceptable only because both are
  unreleased: `begin` never shipped, so what users migrate from is 1.x's bare
  form, once.
