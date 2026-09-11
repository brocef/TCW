# Plan — Accept comma-separated tags

Six tasks. Tests first at every step, because the whole item is about what a
command does with one character and the existing suite has no case for it.

## Tasks

### Task 1 — failing tests for the four options

Modifies `tests/test_work_tags.py` only. Adds CLI cases covering spec criteria 1
through 11, in the file's existing style: `node(tmp_path)`, `monkeypatch.chdir`,
`main([...])` for the exit code, `capsys` for output.

Argparse errors raise `SystemExit(2)` rather than returning, so criteria 6, 7
and 8 use `pytest.raises(SystemExit)` and read `capsys.readouterr().err`.
Criterion 11 needs four items — `cli` only, `docs` only, both, neither — so an
AND filter cannot pass.

**Proves it:** every new test fails before Task 2, and the reason each fails is
read, not assumed. Criteria 1 and 3 fail as `unrecognized arguments: --tags`;
criterion 2 fails as `unregistered tag 'cli-docs'`.

### Task 2 — the converter and the four options

Modifies `tcw/work/cli.py` only.

Add `_tags(value) -> list[str]` beside `_split`: split on commas, normalize each
token with `normalize_tag`, raise `argparse.ArgumentTypeError` when the value
yields nothing, echoing the value as typed. Delete `_tag` (`:68-74`), which
becomes unreferenced.

Change four `add_argument` calls to `type=_tags, action="extend"` and a second
spelling: `--tag`/`--tags` at `:1883`, `:1892`, `:2016`, and
`--untag`/`--untags` at `:2017`. `dest` comes from the first long option, so it
stays `tag` and `untag` and no handler changes.

Update each option's `help=` to say a value may be a comma-separated list
(criterion 15).

**Proves it:** Task 1's tests go green. `python -m pytest tests/test_work_tags.py`
passes in full, including the four pre-existing CLI tests, which exercise the
same options through the old spelling.

### Task 3 — failing tests for registration, then the fix

Modifies `tests/test_work_tags.py`, then `tcw/work/cli.py`.

Tests first, for criteria 12 and 13: `tcw work tags add "cli,docs"` registers
two tags and never `cli-docs`; `tcw work tags rm "cli,docs"` unregisters both,
and on a node registering only `cli-docs` unregisters nothing. Both fail before
the fix — `tags add` currently prints `cli-docs` in its output.

Then flatten in the two handlers, `_tags_add` and `_tags_rm`, with the same
`_tags`: `tags = [t for v in args.tag for t in _tags(v)]`. The positionals keep
`nargs="+"` and gain no `type=`, because argparse does not flatten a
list-returning converter under `nargs` — verified: both `store` and `extend`
yield `[['cli','docs'], ['web']]`.

Update both positionals' `help=` (criterion 15).

**Separate from Task 2 deliberately.** These are the two commands that corrupt a
node, and they are the reason the item's priority went from 20 to 35. A separate
commit makes them separately revertable and separately reviewable.

### Task 4 — the regression guard for the non-goal

Modifies `tests/test_work_tags.py` only. One test for criterion 14:
`tcw work new "X" --blocked-by "external: waiting on Acme, Inc."` records one
blocker whose text contains the comma.

This test passes on first run, which the implement stage says is not proof. So
break it deliberately — comma-split `--blocked-by` in a scratch edit — confirm it
goes red naming two blockers, and revert. Record that in `outcome.md`.

**Proves it:** red when `--blocked-by` splits, green when it does not.

### Task 5 — capability revision

Modifies `docs/capabilities/work/tag-a-work-item/description.md` through
`tcw capabilities set` where a field changes, and by editing the body for the
prose.

The body currently says tags are applied with `--tag <tag>` (repeatable) and
filtered with `--tag <tag>` (repeatable = match any). It gains: each value may be
a comma-separated list, `--tags` is accepted everywhere `--tag` is, and the same
holds for `tags add`/`tags rm`. Status stays `Supported`.

**Proves it:** criterion 17 — `tcw capabilities show work/tag-a-work-item`
describes the comma form and `tcw capabilities check` passes.

### Task 6 — documentation

One block at the end, per the plan stage's instruction. Evaluated against every
entry `tcw work docs` reports; all four fire.

- **`README.md` — [Public-API].** Fires: the public CLI surface changes. But the
  README does not mention `--tag` at all — it is the pitch and links out to the
  guide — so the evaluation is recorded and the file is not edited.
- **`docs/release-notes/upcoming.md` — [Public-API].** Fires. A user can now do
  something they could not, and three behaviours change. Plain language, and it
  must name the corruption case rather than only the new spelling.
- **`docs/changelogs/upcoming.md` — [Any-Code-Change].** Fires. Grouped
  `Added` and `Fixed`, and the `--ta` abbreviation loss under `Changed`.
- **`skills/<component>/SKILL.md` — [Skill-Driven-Component].** Fires: `tcw-work`
  drives the component whose CLI surface changed. The drift is in its references,
  not the SKILL body: `skills/tcw-work/references/tags.md` and
  `references/commands.md`.

Also `docs/guide/work.md`, which is not a declared entry but is the prose home
for the work commands and documents the tag registry at `:317-323`.

`skills/tcw-work/references/procedures/audit-backlog.md`,
`references/procedures/search.md` and `skills/tcw-triage-issues/SKILL.md` also
name `--tag`; each is read and either updated or recorded as not needing it.

**Proves it:** criterion 18, and criterion 15's `--help` check run by hand.

## Documentation Sync

Covered by Task 6 above, which is the block the plan stage asks for. All four
declared entries fire; one of them is evaluated and deliberately not edited, and
that is recorded rather than left silent.

## Verification

What the suite cannot check:

- **That the `--ta` abbreviation really is the only casualty.** The suite cannot
  enumerate every prefix a user might have typed. Checked by hand instead:
  `--tag` matches exactly and still works, `--t` is already ambiguous with
  `--title` today, so the loss is exactly `--ta` and `--unta`. Run all four by
  hand after Task 2.
- **That an already-poisoned node is unaffected rather than broken.** Build one —
  register `cli-docs`, tag an item with it — and confirm after the change that
  the item still reads, `tcw validate` still reports OK, and nothing crashes.
  The spec says such a node is not repaired; this confirms it is also not made
  worse.
- **That the help text reads well.** Criterion 15 can be grepped; whether the
  wording helps cannot. Read all six `--help` outputs.

## Notes

- Tasks 1 and 2 are one change split across two commits so the tests are
  committed red-then-green in order. Same for Task 3. That is the repository's
  test-first instruction taken literally, not ceremony.
- No task depends on Task 4, 5 or 6, and the suite is green at every commit
  boundary except the two deliberate red ones, which are immediately followed by
  their green.
- `action="extend"` needs Python 3.8; `pyproject.toml` requires 3.11. Fine.
