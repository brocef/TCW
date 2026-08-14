# Outcome — Ship built-in stage prompts with the CLI

Seven tasks, seven commits, in the plan's order. The suite was run in full at
every commit boundary.

## What shipped

### 1. The six prompt files and their packaging — `8700d11`

`tcw/work/prompts/{request,spec,plan,implement,verify,postmortem}.md`, one per
lifecycle stage that runs against an existing item; `inbox` ships none because
it runs before one exists. Each is condensed from the matching
`skills/tcw-work/references/stage-*.md` against the spec's §5 table: purpose,
inputs, the artifact and its required sections, the steps that change
behaviour, the gating `tcw` commands, and the exit-badly branches move into the
prompt, while delegability, `[gated]`/`[judgment]` notation, epic and
cross-node deltas, sub-skill names, and store mechanics stay in the skill. Step
1 of every source document — run `tcw work lifecycle --stage <id>` and honour
what it reports — is dropped as circular. Plus
`"tcw.work" = ["prompts/*.md"]` in `[tool.setuptools.package-data]`, beside the
`tcw.serve` entry, which is what carries them into a wheel.

Line counts as landed: 39, 40, 40, 39, 40, 40 — four of the six sit exactly on
the 40-line ceiling.

### 2. The loader — `d7a6c5a`

`load_builtins()` in `tcw/work/resolve.py` now fills `stage_prompts` alongside
the `artifact_templates` C5 put there. One loader, not two. It reads through
`importlib.resources.files("tcw.work")` over
`sorted(set(STAGE_IDS) - {"inbox"})` — the derivation, so a stage added without
its prompt fails here — and raises `ResolveError` naming the stage and the
package path for a file that is missing or empty after `strip()`.
`tcw/work/templates.py` and `ARTIFACT_TEMPLATES` were not moved, renamed, or
edited.

`tests/test_shipped_prompts.py`: exact set equality against the derivation,
`inbox` absent, ≥15 non-blank lines and ≤40 lines per prompt read through the
loader rather than by globbing the source tree, the two condensation greps (no
`tcw work lifecycle --stage`, no `tcw-verifier` / `documentation-sync` /
`tcw-capabilities`), the loud-failure case, and the wheel: `pip wheel --no-deps
--no-build-isolation` then `zipfile.ZipFile`, asserting the
`tcw/work/prompts/*.md` members equal the same six ids with non-empty content.
Default suite, no marker. Nothing in the file invokes `tcw work stage`
(criterion 4).

### 3. The floor — `91c9561`

`resolve_prompts` resolves a stage with **no** prompt bindings as if it bound
`[{builtin: true}]`, appending a real `PlanEntry("builtin", …, matched=True,
executed=False)` so `--no-exec` reports the built-in it is about to print. The
condition is on the binding list, not the resolved text: a stage whose only
binding carries a non-matching `when:` still resolves to `""`, pinned by its
own test. Added to `tests/test_resolve.py`; every existing case in that file
passes unmodified.

### 4. The verb — `7616e19`

`tcw work stage` passes `load_builtins()` instead of `Builtins()`, inside the
existing `except ResolveError` block. `tests/test_stage_verb.py` gains the
end-to-end case over all six stages on a node with no `work.lifecycle` key, and
re-asserts that `inbox` ships no prompt and still exits 1 with its reason.

### 5. `prompt: []` refused, both spellings — `1b5b31d`

`_empty_prompt` appended from both branches of `_parse_stage`: the legacy bare
list and the explicit key. One message naming the position and saying to write
`[{blob: ""}]` instead. Nothing in the model changes. `pre: []` is untouched in
both the stage and transition positions, asserted so the check cannot be
generalized later. `tests/test_lifecycle_validation.py` also asserts that a
policy parsed from `{"stages": {"spec": []}}` still resolves to the built-in —
the parser's problem list is advisory — and loads
`tests/fixtures/lifecycle_baseline/stage_empty.config.yaml` from the corpus by
path to pin the break to a config that demonstrably predates it.

The eleven baseline fixtures pass **unmodified**; `git diff` over
`tests/fixtures/` across the whole item is empty.

### 6. Documentation Sync — `818bf5f`

One pass over the finished diff, at the end. Three of the four entries fire.

- **`README.md`** — `builtin: true` now says TCW ships instructions for the six
  lifecycle stages and a template per document, and that an unconfigured stage
  resolves to them; the `tcw work stage` paragraph says the command is useful
  before any lifecycle configuration exists; and "your existing configuration
  keeps working exactly as it did" gains the empty-prompt-list carve-out. C5's
  drafts paragraph untouched.
- **`docs/release-notes/upcoming.md`** — §"Asking TCW what to do at a stage"
  claimed the instructions were "TCW's own by default", which was false until
  now; it is true, with which six stages and why the inbox has none.
  §"Everything you have configured already keeps working" gains the upgrade
  sentence, including what to write instead.
- **`docs/changelogs/upcoming.md`** — *Added*: the prompt files and the
  package-data key, the loader half, the floor, the test file including the
  wheel case. *Changed*: the verb's argument. *Removed*: `prompt: []` in both
  forms, marked as the back-compat break.
- **`skills/tcw-work/**`** — the trigger **fires and the answer is no edit**.
  The epic assigns the stage documents and `hooks.md` to C7; editing them here
  means editing them twice. Nothing in the skill becomes wrong —
  `hooks.md:31`'s "`builtin: true` is TCW's own default" is made true by this
  change — the six stage documents merely become redundant, which is the state
  C7 resolves. Recorded, not silently skipped.

### 7. Capability ledger — `d87cf34`

`work/run-a-lifecycle-stage` (`cap-f42255`) revised through the
`tcw-capabilities` skill; status stays `Supported`, and the item's
`capabilities.yaml` already carried it under `changed:`. The record now says
that with nothing configured the instructions are TCW's own, for the six stages
that run against an existing item, `inbox` excluded; that a configured stage
replaces them; and that `builtin: true` composes them back in declaration
order. `work/configure-the-work-lifecycle` was not edited — see
`## Notes`.

`tcw capabilities check` → `capabilities OK`; `tcw capabilities drift` → `no
capability drift`; `tcw validate` → `validate OK`. All exit 0.

## Test result

Full suite at every one of the seven boundaries. The last run, after `d87cf34`:

```
1561 passed in 288.10s (0:04:48)
```

C5's baseline was 1510; this item adds 51 tests and edits none.

Run by hand against this repo's own node, whose `tcw-config.yaml` has no
`work.lifecycle` key at all: `tcw work stage implement
2026-08-12-ship-built-in-stage-prompts-with-the-cli` and `tcw work stage spec
2026-08-12-repoint-the-work-skill-and-docs-at-the-cli` each exit 0 and print the
shipped text; `tcw work stage spec` on this item is refused as illegal for
`active`, which is C4's check doing its job.

## What the plan and spec got wrong

1. **The `scaffold` call site was already repointed.** The plan's §Notes gives
   task 2 two jobs — the loader and repointing `tcw work scaffold` — because it
   was written expecting C5 to leave an inline
   `Builtins(artifact_templates=ARTIFACT_TEMPLATES)` behind. C5 landed first and
   did the consolidation itself: `_scaffold` calls `load_builtins()` at
   `tcw/work/cli.py:883`. Task 2 was therefore loader-only. The companion
   assertion the plan asked for also already exists as
   `tests/test_scaffold.py::test_load_builtins_carries_the_templates`, so no
   duplicate was added.
2. **The function is `load_builtins()`, not `shipped_builtins()`.** The plan
   names a function C5 had already introduced under a different name, and
   decorated with `@lru_cache(maxsize=1)` rather than the plan's
   `@functools.cache`. C5's name and decorator were kept; adding a second
   loader is exactly what the spec's §Notes rules out.
3. **The line number for the bare `Builtins()` was `cli.py:804`, not `:801`.**
   The epic amendment, the spec §4, and the plan all say `:801`. C5's changes
   shifted it.
4. **The plan forbids touching §"Binding your own skills and commands to the
   lifecycle" while locating all three README edits inside it.** That section
   runs from `README.md:605` past line 700, so `:637`, `:673`, and `:676` are
   all within it and the instruction contradicts itself. The epic resolves it:
   "Each of C1–C6 has already updated its own command docs, changelog, release
   notes, and ledger. C7 performs only the consolidation that cannot be
   expressed earlier" — C7 rewrites the section coherently *after* each child
   has corrected the sentences it falsified. The three located edits were made
   and nothing else in the section was touched, C5's drafts paragraph included.
5. **The wheel is `tcw_cli-*.whl`.** The distribution is named `tcw-cli`, not
   `tcw`; the spec and plan describe the wheel test without naming the
   artifact, and a `tcw-*.whl` glob finds nothing. The test globs `*.whl` and
   asserts exactly one.
6. **"Returns the shipped text" is the text minus its trailing newline.**
   Criteria 5 and 6 are byte-level, and `_join` rstrips every part it keeps
   (`resolve.py:200`), so an unconfigured stage resolves to
   `stage_prompts[sid].rstrip()` and the composition case to
   `…rstrip() + "\n\n" + "X"`. Asserted in that form rather than the spec's
   looser wording; no code changed for it.

## Notes

- **A contradiction surfaced in `work/configure-the-work-lifecycle`, left
  unedited.** Its line 6 reads "**Everything I configured before this still
  works and still prints the same thing.** A stage id with a plain list under it
  means what it always meant." After task 5 a bare `stages.<id>: []` is a
  `tcw validate` problem. The sentence survives on a narrow reading — resolution
  genuinely is unchanged, since the parser's problem list is advisory, so a node
  with that config still *runs* identically and only `validate` complains — and
  the record was out of scope by both the spec and the implement brief. Raised
  here rather than fixed: it belongs to C7's documentation consolidation, or to
  C8's audit, and the `tcw-capabilities` skill's rule for a semantic
  contradiction is to surface it rather than overwrite.
- **The 40-line ceiling has no margin.** Four of the six prompts are exactly at
  it, so any future edit to `plan`, `postmortem`, `spec`, or `verify` must
  remove a line to add one. That is the ceiling working as §6 intended, but C7
  should know it before it starts moving clauses across the seam: there is no
  room to accept one.
- **`lru_cache` does not memoize a raise.** The loud-failure path therefore
  reports on every call rather than being cached away after the first, which is
  the behaviour a broken install wants. Verified by the test, which clears the
  cache on both sides so it cannot leak into the rest of the suite.
- **The wheel test needs `pip` and `setuptools` present.** With
  `--no-build-isolation` there is no network fetch, but a stripped image without
  `setuptools` fails rather than skips — deliberate, per the plan: a silent skip
  on the one criterion that checks packaging is worse than a red. It costs
  ~3s of the suite's runtime.
- **sdist parity remains untested**, per the spec's Risks. Named, not asserted.
