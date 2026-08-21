# Outcome — key `work.documentation` uniqueness on (path, trigger)

Shipped as planned, four tasks, three code/doc commits. No design change from
the spec.

## What shipped

### Task 1 — the failing tests · `6a81158`

`tests/test_documentation_config.py`, three new tests in a
`one file, several triggers` section, plus a shared `PAIR` fixture holding the
reporter's `README.md` × (`Public-CLI-API`, `Validation-Rules`):

- `test_one_path_may_carry_two_triggers`
- `test_the_same_path_and_trigger_twice_is_still_a_duplicate`
- `test_a_duplicate_names_the_entry_that_first_declared_the_pair`

`test_a_duplicate_path_is_reported` (`:75`) was left untouched, as planned.

**Red, watched:** `3 failed, 33 passed`. The third failed with
`assert 2 == 1` against both `entry 1` and `entry 2` problems — the exact
symptom the pair keying removes.

### Task 2 — key the duplicate check on the pair · `e22af98`

`tcw/store/base.py`, `parse_documentation_entries`:

- `seen: dict[str, int]` → `dict[tuple[str, str], int]`, keyed on
  `(path, trigger)`.
- The problem text names both halves:
  `duplicate 'path' 'README.md' under trigger 'Public-CLI-API', already declared
  by entry 0`. It still opens `work.documentation entry N: duplicate`, so the
  pre-existing test and the README's wording both hold.
- Docstring gains an **Identity is `(path, trigger)`** paragraph citing
  `_parse_bindings`' `(kind, value, when)` decision as the in-file precedent.

Nothing else moved: 13 insertions, 5 deletions, and every earlier shape check
runs in the same order, so a malformed entry still fails on its own check and
never reaches the duplicate guard.

**Green:** `36 passed` on the file.

### Task 3 — Documentation Sync · `760f9a8`

All four entries evaluated against the finished diff; all four fired.

| Entry | Trigger | Fired | What changed |
| --- | --- | --- | --- |
| `README.md` | `Public-API` | yes | The `tcw validate` checklist said "a duplicate path"; now says the same path twice under the *same* trigger, plus a paragraph showing the two-trigger `README.md` case. |
| `docs/release-notes/upcoming.md` | `Public-API` | yes | New **Changed** section, plain language, no module names. |
| `docs/changelogs/upcoming.md` | `Any-Code-Change` | yes | New **Changed** section: the key, the message, the unchanged rejection. |
| `skills/documentation-sync/references/setup.md` | `Skill-Driven-Component` | yes | The setup guide stated the three-key rule and said nothing about uniqueness — the omission that told the reporter the opposite. Now states the pair rule explicitly. |

`skills/tcw-work/references/commands.md:57-68` was checked and left alone: it
describes what `tcw work docs` prints and what `source` means, and makes no
claim about entry shape. `docs/migration-guide-0.21.X-to-1.0.0.md:255-256` was
checked and left alone for the same reason, as the spec's Non-goals predicted.

### Task 4 — manual verification

A scratch work-only node under the session scratchpad, given the reporter's pair
verbatim:

```
$ tcw validate
validate OK                                                    # exit 0

$ tcw work docs
README.md  [Public-CLI-API]    Concepts, usage examples, and CLI sections.
README.md  [Validation-Rules]  The "Invalid Constructions" section. …

$ tcw work docs --json
… "entries": [ {…"Public-CLI-API"…}, {…"Validation-Rules"…} ]     # two objects
```

A third entry copying the first exactly is still rejected, and names entry 0
rather than the entry beside it:

```
$ tcw validate
work check: tcw-config.yaml: work.documentation entry 2: duplicate 'path'
'README.md' under trigger 'Public-CLI-API', already declared by entry 0
1 problem(s).                                                   # exit 1
```

`tcw work docs` in **this** repo, captured before the change and again after,
diffs clean — `IDENTICAL`.

## Acceptance criteria

| # | Criterion | Evidence |
| --- | --- | --- |
| 1 | Pair accepted: 2 entries, 0 problems | `test_one_path_may_carry_two_triggers` |
| 2 | Same path *and* trigger: 1 entry, 1 problem naming both | `test_the_same_path_and_trigger_twice_is_still_a_duplicate` |
| 3 | `[A,B,C]` reports entry 2 → entry 0, keeps `[A,B]` | `test_a_duplicate_names_the_entry_that_first_declared_the_pair` + the scratch-node run |
| 4 | `test_a_duplicate_path_is_reported` unchanged and passing | unmodified in the diff; green |
| 5 | Suite green | `1955 passed in 388.00s`, exit 0 — final tree at `713e0a2` |
| 6 | Reporter's pair passes `tcw validate` | `validate OK`, exit 0 |
| 7 | Two rows, two JSON objects | above |
| 8 | This repo's `tcw work docs` byte-identical | `diff` empty |
| 9 | README no longer says a bare "duplicate path" | `README.md` in `760f9a8` |

## What the plan and spec got wrong

Little, but not nothing.

- **The first full-suite run predated the documentation commits, and the
  shortcut taken instead was wrong.** `1955 passed` was originally captured
  from a run started right after Task 2 and finishing ~10½ minutes later, by
  which time Task 3's Markdown had landed. Rather than pay another 10½ minutes,
  three suites were re-run against the final tree (`239 passed`) on the claim
  that no test parses `README.md` prose or `skills/**/references/*.md`.
  **That claim was false.** `tests/test_documentation_sync_wiring.py:27-33`
  globs `README.md` and all of `skills/` for stale plugin references, and
  `:127-135` reads the edited `references/setup.md` directly — and it was not
  among the three. Found by the Codex review at `verify`, not by this session.
  Corrected by running both properly against the final tree at `713e0a2`, clean
  working tree: `pytest tests/test_documentation_sync_wiring.py` → `7 passed`,
  and the whole suite → **`1955 passed in 388.00s`, exit 0**. That is the run
  criterion 5 rests on; the earlier one is superseded.
- **Task 1 was committed red**, which the plan permitted in its opening
  paragraph but is still a boundary where the tree is not green. Deliberate: it
  is what makes the red observable in history.
- **The spec's Non-goals held up under implementation.** Neither the migration
  guide nor the `tcw-work` skill needed the edit, and no downstream consumer
  turned out to key on `path` — the sweep was right that nothing else does.

## Notes

- `tcw init` takes `--id` and positional components; there is no `--name`. Cost
  one retry building the scratch node. Nothing to fix — the plan never named a
  flag.
- The ledger gap recorded in `spec.md` (**Capability changes**) is untouched and
  still open: the two capability records the `work.documentation` item planned
  do not exist, and `tcw capabilities drift` reports clean anyway. It belongs to
  its own item — raise at closeout.

## Review round (added at `verify`)

`codex exec --sandbox read-only` over `e4c5b22..760f9a8`, prompted to attack the
duplicate guard, downstream path-keying consumers, the output contract, doc
accuracy, test quality, and the abstraction litmus test.

**One finding, Low, accepted:** the full-suite evidence recorded above was not
from a stable final tree, and the reasoning used to justify skipping a re-run
was factually wrong. Reproduced independently before accepting, and corrected in
place — see the bullet above.

**Explicitly cleared by the review:** index correctness across skipped entries;
`render_documentation`, `substitute_documentation`, `_docs` (table widths and
`--json`), the FS adapter, and the stage consumers all preserve both entries;
the new tests fail against the old parser for the intended reasons and are
non-vacuous; no documentation elsewhere still states the old rule; the error
wording has no exact-string caller; the parser stays pure and storage-neutral.

**Not a finding, checked separately:** `path` remains an exact string, so
`README.md` vs `./README.md`, a trailing slash, case variants, and NFC/NFD
variants are distinct entries. That predates this change and normalizing it
would conflate genuinely different files on a case-sensitive store.
`docs/work/backlog/2026-08-18-serve-version-cut-…/spec.md:188,272` also says
"a duplicate path", but about `work.version.files` — a plain path list with no
trigger — so it is correct as written and was left alone.
