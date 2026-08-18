# Plan — Serve documentation-sync entries from tcw-config.yaml instead of scraping the agent guide

Nine tasks. The order is set by one constraint above all others: **the
back-compat fixture is captured before the prompts are edited**, or it records
the new behavior and proves nothing. Everything else follows the usual rule of a
green suite at each boundary — the parser and the store method exist before
anything resolves through them, and the CLI verb exists before the skill points
at it.

## Tasks

### 1. Capture the fallback baseline, before touching a single prompt

**Creates:** `tests/fixtures/prompt_fallback/` (one JSON per stage),
`tests/fixtures/prompt_fallback/capture.py`
**Modifies:** nothing

Record `tcw work stage <id> <slug>` stdout for every stage that runs against an
item, on a scratch node with no `work.documentation` and no lifecycle config, in
its own commit. Modelled on `tests/fixtures/lifecycle_baseline/capture.py`, whose
docstring states exactly why this has to come first.

`tests/test_prompt_fallback.py` replays them. It passes trivially now — that is
the point; it is a tripwire armed before the change, and it is what makes
criterion 3 evidence rather than an assertion.

**Proves it:** the test passes on an unmodified tree, and its fixture diff in
this commit contains no substituted text.

**Commit:** `test: record built-in stage prompt output before the doc-sync change`

### 2. `DocEntry` and the pure parser

**Modifies:** `tcw/store/base.py`
**Creates:** `tests/test_documentation_config.py`

`DocEntry` (frozen; `path`, `trigger`, `description`) beside `StageBindings`, and
`parse_documentation_entries(raw) -> tuple[list[DocEntry], list[str]]` mirroring
`parse_lifecycle_policy` (`tcw/store/base.py:1019`): pure, filesystem-free, never
raises, advisory problem list.

Problems reported, each naming the entry index and key: non-list
`documentation:`, non-mapping entry, blank/missing `path`/`trigger`/`description`,
absolute `path`, `path` escaping the node lexically, newline in `path` or
`trigger`, whitespace in `trigger`, duplicate `path`.

**Not** reported: a `path` that does not exist on disk (the parser touches no
filesystem, and an entry naming a file the project intends to create is
correct), and a `trigger` outside the four-name base set
(`skills/documentation-sync/SKILL.md:56` declares the vocabulary open).

**Proves it:** acceptance criteria 1 and 2, as table-driven cases.

**Commit:** `feat: parse work.documentation entries from node configuration`

### 3. The store interface and `tcw validate`

**Modifies:** `tcw/store/base.py` (the `WorkStore` ABC), `tcw/store/fs.py`,
`tcw/validate.py`, `tests/test_documentation_config.py`

`WorkStore.documentation() -> list[DocEntry]` on the ABC — precedent:
`lifecycle_policy()` at `tcw/store/base.py:1385` is already a config-derived
method there rather than an adapter detail. `FsWorkStore.documentation()` reads
`self._work_config().get("documentation")` through the existing helper
(`tcw/store/fs.py:2613`); `documentation_problems()` mirrors
`lifecycle_problems()` (`tcw/store/fs.py:2643`) and is folded into the same
`check` path `tcw validate` already consumes.

**Proves it:** `tcw validate` on a fixture node with each malformed entry reports
the problem and exits non-zero; on a valid one, `validate OK`.

**Commit:** `feat: expose a node's documentation entries through WorkStore`

### 4. Render, substitute, and edit the two prompts

**Modifies:** `tcw/work/resolve.py`, `tcw/work/prompts/plan.md`,
`tcw/work/prompts/implement.md`, `tests/test_prompt_fallback.py`
**Creates:** tests in `tests/test_documentation_prompt.py`

`render_documentation(entries) -> str` produces the bullet list from the spec —
not a table, because a `|` in a description would break one. `description` has
internal newlines collapsed to single spaces at render time.

Substitution runs in `resolve_prompts` over the joined `res.text`, **not** in
`_resolve_one`, which `resolve_artifact` also uses
(`tcw/work/resolve.py:277-281`) and which `tcw work scaffold`'s implicit fallback
bypasses (`tcw/work/cli.py:896-897`). `resolve_prompts` gains
`documentation: Sequence[DocEntry] = ()`, defaulted so every existing caller
compiles unchanged and resolves to the fallback.

With no entries the token becomes the sentence the prompts carry today,
byte-for-byte. The two prompt files replace that sentence with
`{{tcw:documentation}}` and so get one line shorter — 41 → 40 and 40 → 39 against
a ceiling of 50.

**Proves it:** acceptance criteria 3 (task 1's fixtures still replay
byte-identically), 4, 7a, 7b, 8, and 9.

**Commit:** `feat: render a node's documentation entries into the stage prompts`

### 5. `tcw work docs`

**Modifies:** `tcw/work/cli.py`
**Creates:** tests in `tests/test_documentation_prompt.py`

Read-only verb; `--json` emits
`{"schema": 1, "source": "config"|"agent-guide", "entries": [...]}`. stdout alone
on success, stderr for errors, nothing on stdout on failure — the contract
`tcw work stage` set. Serves the skill's third invocation point, the version
offer after `complete`, which has no stage to hang off because
`tcw work stage implement` on a completed item is refused by the status check at
`tcw/work/cli.py:786-790`.

**Proves it:** acceptance criteria 5, 6, and 7 — the last by hashing every path
under the work store and the node config before and after the call and comparing
manifests.

**Commit:** `feat: add tcw work docs`

### 6. Repoint the skill and its references

**Modifies:** `skills/documentation-sync/SKILL.md` (lines 8, 62, 101),
`skills/documentation-sync/references/setup.md`,
`skills/documentation-sync/references/release-notes-and-changelogs.md` (lines 5, 7)

Entries come from `tcw work docs --json`; the Markdown section is named only as
the fallback taken when `source` is `agent-guide`. The trigger reference, the
partition rule, the evaluation loop, and the three companion references are
otherwise unchanged — this moves where entries come from, not how they are
judged. `setup.md` gains the config form as the recommended shape.

**Proves it:** acceptance criteria 10 and 11a;
`tests/test_documentation_sync_wiring.py` passes.

**Commit:** `docs: point documentation-sync at tcw work docs`

### 7. Migrate this repository

**Modifies:** `tcw-config.yaml`, `AGENTS.md`, `docs/lifecycle/implementation.md`,
`tests/test_repo_lifecycle.py`, `tests/fixtures/lifecycle_baseline/self.json`

The four entries move from `AGENTS.md`'s `## Documentation Sync` section into
`work.documentation`; the section is deleted. `docs/lifecycle/implementation.md`
loses the paragraph explaining that the section could not move, since this item
is what removes that constraint. A test in `tests/test_repo_lifecycle.py` asserts
this repo's four entries parse and that `AGENTS.md` no longer carries the section.

`self.json` is re-captured **only if** it moves. Per the spec it should not —
`tcw work lifecycle` resolves no `builtin` — and if it does, that contradicts
criterion 9 and the change is wrong, not the fixture.

**Proves it:** acceptance criterion 11.

**Commit:** `docs: move this repo's documentation entries into tcw-config.yaml`

### 8. Rewrite the migration guide's advice

**Modifies:** `docs/migration-guide-0.21.X-to-1.0.0.md`

Its "If you are moving rules out of your agent guide" section currently opens by
telling readers that a rule another skill reads out of `CLAUDE.md` by name cannot
move, and gives `documentation-sync` as the case. That advice describes a bug
this item fixes. Rewritten to document `work.documentation` as the configuration
form, keeping the general lesson — *check what reads your agent guide* — which is
still true for `## Versioning`.

**Proves it:** acceptance criterion 12.

**Commit:** `docs: document work.documentation in the migration guide`

### 9. Documentation Sync

Evaluated against the four entries — now, for the first time, by running
`tcw work docs` against this repo rather than reading a Markdown section:

| Entry | Trigger | Fires? | Why |
| ----- | ------- | ------ | --- |
| `README.md` | Public-API | **Yes** | `tcw work docs` is a new public verb and `work.documentation` is a new public config block. The lifecycle-binding section needs both. |
| `docs/release-notes/upcoming.md` | Public-API | **Yes** | A user-facing feature. Written to `upcoming.md` in the normal flow; the post-completion fold moves it into `v1.0.0.md`. |
| `docs/changelogs/upcoming.md` | Any-Code-Change | **Yes** | Behavior-affecting code in `tcw/`. Grouped Added/Changed. |
| `skills/tcw-work/SKILL.md` | Skill-Driven-Component | **Yes** | The work component gains a CLI verb and a config block. Unlike the previous item, where nothing about the component changed, this one changes its surface. |

All four fire — the first time every entry has. Run the `documentation-sync`
skill over the finished diff before considering this done; a trigger this table
missed means the table was wrong, and that goes in `outcome.md`.

**Modifies:** `README.md`, `docs/release-notes/upcoming.md`,
`docs/changelogs/upcoming.md`, `skills/tcw-work/SKILL.md`

**Commit:** `docs: README, release notes, changelog and skill for tcw work docs`

## Verification

1. **Criterion 3 is the one that matters and the one a test can genuinely
   settle.** Task 1's fixtures were recorded before the change; if they replay
   byte-identically afterwards, every project that has configured nothing is
   provably unaffected. If they do not, the change is wrong regardless of how
   good the new behavior looks.
2. **Whether the rendered entries actually read well inside the prompt.** No test
   covers whether a fifteen-entry project produces instructions an agent can act
   on, or a wall of text. Read the resolved `tcw work stage implement` output for
   this repo's four entries and judge it.
3. **That the skill still works end to end.** The wiring tests check that files
   reference each other, not that the gate fires correctly. Confirm by invoking
   `documentation-sync` at task 9 and seeing it read `tcw work docs`.
4. **Full suite:** ≥ 1592 passed, 0 failed. Once, at the end — it takes ~5
   minutes.

## Notes

- **The v1.0.0 fold is not a task here.** The lifecycle offers a version cut
  *after* `complete` (`tcw work stage verify`, step 9), so the fold happens after
  this item closes, following
  `skills/documentation-sync/references/cut-version.md` → "Folding into an
  unpushed version". That procedure requires
  `skills/documentation-sync/scripts/unpushed-version.sh` to exit `0` first —
  re-confirmed against the network at that moment, not assumed from this
  session's knowledge that the tag is local.
- No `--blocked-by` links: every dependency is between tasks inside this item.
- Self-review against the spec: criteria 1–2 → task 2; 3 → tasks 1 and 4; 4, 7a,
  7b, 8, 9 → task 4; 5, 6, 7 → task 5; 10, 11a → task 6; 11 → task 7; 12 → task
  8; 13 → Verification 4. Every task traces back: 1→c3, 2→c1/c2, 3→c1/c2 at the
  CLI boundary, 4→c3/c4/c7a/c7b/c8/c9, 5→c5/c6/c7, 6→c10/c11a, 7→c11, 8→c12,
  9→the Documentation Sync gate.
