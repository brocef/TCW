# Plan — key `work.documentation` uniqueness on (path, trigger)

Four tasks: one red test, one parser change, one documentation block, one manual
verification pass. The suite is green at every commit boundary except after
Task 1, which is the point of Task 1 — commit it together with Task 2 if a green
tree at every commit matters more than a recorded red.

## Task 1 — the failing tests

**Modifies:** `tests/test_documentation_config.py`

Add a section after `test_a_duplicate_path_is_reported` (`:75-77`), which stays
exactly as it is — it duplicates a whole entry and so still collides on both
halves (AC 4).

Three new tests, using the existing `parse_documentation_entries` / `_problems` /
`_entries` helpers:

1. `test_one_path_may_carry_two_triggers` — the reporter's pair:
   `[{path: "README.md", trigger: "Public-CLI-API", description: "d1"},
     {path: "README.md", trigger: "Validation-Rules", description: "d2"}]`.
   Asserts `problems == []`, `len(entries) == 2`, and that the two triggers come
   back in declaration order. (AC 1)
2. `test_the_same_path_and_trigger_twice_is_still_a_duplicate` — the same pair
   with both triggers set to `Public-CLI-API`. Asserts exactly one problem, that
   it contains `entry 1`, `README.md`, and `Public-CLI-API`, and that one entry
   survives. (AC 2, AC 3's message content)
3. `test_a_duplicate_names_the_entry_that_first_declared_the_pair` — the
   `[A(README/X), B(README/Y), C(README/X)]` case. Asserts a single problem
   naming `entry 2` and `entry 0`, and `[e.trigger for e in entries] == ["X", "Y"]`.
   This is the one that catches a fix that renumbers by list position instead of
   by the stored index. (AC 3)

**Proves:** `pytest tests/test_documentation_config.py` — the three new tests
fail, every pre-existing test in the file passes.

## Task 2 — key the duplicate check on the pair

**Modifies:** `tcw/store/base.py` (`parse_documentation_entries`, `:1079-1154`)

- Change `seen: dict[str, int]` (`:1105`) to a dict keyed on the
  `(path, trigger)` tuple.
- Replace the guard at `:1146-1150` so it looks the pair up and reports both
  halves — e.g. `duplicate 'path' 'README.md' under trigger 'Public-CLI-API',
  already declared by entry 0`. Keep the leading `{where}: duplicate` shape:
  `test_a_duplicate_path_is_reported` matches on the word `duplicate`, and
  `README.md`'s prose calls it a duplicate.
- Extend the docstring's "Shape only, deliberately" paragraph (`:1086-1092`)
  with one sentence on why the identity is the pair, citing `_parse_bindings`'
  `(kind, value, when)` decision at `:975-989` as the in-file precedent.

Nothing else in the function moves: the required-key, unknown-key, newline,
absolute-path, escape, and whitespace-in-trigger checks keep their current order,
so an entry failing one of those still never reaches the duplicate check.

**Proves:** `pytest tests/test_documentation_config.py` fully green, then
`pytest` green across the suite. (AC 1–5)

## Task 3 — Documentation Sync

One pass over the finished diff, all four entries evaluated:

| Entry | Trigger | Fires? |
| --- | --- | --- |
| `README.md` | `Public-API` | **yes** |
| `docs/release-notes/upcoming.md` | `Public-API` | **yes** |
| `docs/changelogs/upcoming.md` | `Any-Code-Change` | **yes** |
| `skills/<component>/SKILL.md` | `Skill-Driven-Component` | **yes** |

**Modifies:**

- `README.md:763-765` — in the list of what `tcw validate` checks, replace
  "a duplicate path" with the pair rule: the same path twice under the *same*
  trigger. Add a sentence, with the reporter's two-trigger `README.md` as the
  example, saying one file may carry several entries when the triggers differ.
  (AC 9)
- `docs/release-notes/upcoming.md` — one bullet, plain language: a file can now
  appear more than once in `work.documentation` when each entry has a different
  trigger, so a large README can have one entry per section.
- `docs/changelogs/upcoming.md` — under **Changed**: documentation-entry
  uniqueness is now keyed on `(path, trigger)` rather than `path`; the duplicate
  message names the trigger; identical `(path, trigger)` pairs are still
  rejected.
- `skills/documentation-sync/references/setup.md:23` — after "Three required
  keys per entry…", one sentence: the same `path` may appear in several entries
  as long as their triggers differ, which is how a README with sections
  answering to different triggers is expressed. This is the file that told the
  reporter the opposite by omission.

**Not touched, and why:** `docs/migration-guide-0.21.X-to-1.0.0.md:255-256`
describes the same three keys but never states the uniqueness rule, so it is not
made wrong (spec: Non-goals). `skills/documentation-sync/SKILL.md` documents the
Markdown fallback and the per-entry loop, neither of which changes.

**Proves:** `pytest tests/test_documented_cli_surface.py` green (it guards
README/CLI agreement), and the README no longer contains the bare phrase
"duplicate path".

## Task 4 — manual verification against a real node

**Creates:** nothing tracked; a throwaway node under the session scratchpad.

Not coverable by the suite: the parser is unit-tested, but AC 6–8 are about
`tcw validate` and `tcw work docs` end to end.

1. `tcw init` a scratch node; give its `tcw-config.yaml` the reporter's pair
   (`README.md` under `Public-CLI-API`, `README.md` under `Validation-Rules`).
2. `tcw validate` → exit 0, no `work.documentation` line. (AC 6)
3. `tcw work docs` → two rows, one per trigger; `tcw work docs --json` → two
   objects in `entries`. (AC 7)
4. In **this** repo, capture `tcw work docs` before and after the change and
   diff them — must be identical. (AC 8)

**Proves:** the four command outputs, pasted into `outcome.md`.

## Verification

- `pytest` — the whole suite, green.
- Task 4's four command runs, which the suite cannot reach.
- The `tcw work docs` before/after diff in this repo, empty.

## Notes

- Coverage check: AC 1 → Task 1.1/2; AC 2 → Task 1.2; AC 3 → Task 1.3; AC 4 →
  Task 1 (test left alone) + Task 2; AC 5 → Task 2; AC 6, 7, 8 → Task 4; AC 9 →
  Task 3. Every task traces to at least one criterion.
- No blockers. Nothing in the backlog touches
  `parse_documentation_entries`.
- Effort is `low` and the estimate holds: one dict key, one message, four
  documentation edits, three tests.
