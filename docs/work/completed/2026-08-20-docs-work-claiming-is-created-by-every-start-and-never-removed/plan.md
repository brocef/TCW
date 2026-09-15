# Plan — The leftover claiming directory

Three tasks. One line of production code, three tests, one docstring, and the
documentation block.

## Tasks

### Task 1 — failing tests for the pristine check

Modifies `tests/test_non_git_writes.py` only, beside
`test_init_refuses_a_non_pristine_default_store_before_writing_the_sentinel`
(`:642`), which is the existing test for this check and supplies the shape:
`git_init` for both repositories, `init([...], code, "demo", work_path=...)`,
`pytest.raises(ValueError, match="non-pristine")`, and `manifest()` to prove
nothing was written on a refusal.

Four cases, covering spec criteria 1 to 4:

1. A default store holding only the standard entries plus an empty `.claiming`
   relocates successfully. **Fails now**, raising `ValueError: non-pristine`.
2. The same without `.claiming` still relocates. Passes now; it is the
   no-regression half and is worth having beside case 1 so a future reader sees
   both.
3. A store with a real item in `backlog/` is still refused. Passes now — this is
   the existing test's scenario, restated as the guard that case 1 does not
   widen the hole.
4. A store with **both** a real item and `.claiming` is still refused. Fails
   only if the implementation forgives the whole directory rather than the name.

**Proves it:** case 1 fails before Task 2 and the reason is read, not assumed.
Cases 3 and 4 are the ones that matter after; case 4 in particular is what
distinguishes "forgive a name" from "ignore the directory".

### Task 2 — the one-line fix

Modifies `tcw/store/fs.py` only, at `:918`:

```python
actual = {entry.name for entry in default_root.iterdir()} - {".claiming"}
```

With a comment saying why, in one sentence: `.claiming` is adapter-private
staging whose presence says nothing about whether the store holds work.

The `all(...)` clause below it iterates `default_root.iterdir()` separately and
checks each child is a directory containing at most `.gitkeep`. An empty
`.claiming` satisfies that already, so it needs no change — **verify rather than
assume**, because an empty directory passing a `<= {".gitkeep"}` subset test is
exactly the kind of thing that is true until someone puts a file in it.

**Proves it:** Task 1's case 1 goes green and cases 2 to 4 stay green.

### Task 3 — the invariant, written down

Modifies `tcw/store/fs.py` only, extending `_claiming_dirs`'s docstring
(`:3649-3658`) with the invariant from the spec: the directory's contents are
the state, its own existence means nothing, it is created on demand and never
removed. Say that `Path.glob` on a missing directory returns empty, which is why
every reader is already blind to the difference, and name the pristine check as
the one place that was not.

Also corrects the docstring of
`test_start_is_refused_before_it_makes_the_claiming_folder`
(`tests/test_non_git_writes.py:190-197`) where it explains *why* it uses a fresh
node. **The test itself does not change**: it checks that a refused command
creates nothing, so absence is the right assertion and a fresh node is the right
fixture. The docstring currently reads as though it were working around a
defect; it is not, and after this item there is no defect to work around.

**Proves it:** read it. Nothing executable.

## Documentation Sync

Evaluated against every entry `tcw work docs` reports.

- **`README.md` — [Public-API].** Does **not** fire. No CLI surface changes and
  no command gains or loses an option. `tcw init --work-path` starts succeeding
  in a case where it wrongly refused, which is a fix to documented behaviour
  rather than a change to it.
- **`docs/release-notes/upcoming.md` — [Public-API].** **Fires.** A user who
  could not relocate their work store now can, and the old refusal was
  bewildering enough to be worth naming. Plain language, and it should say how
  to recognize that this was the problem they hit.
- **`docs/changelogs/upcoming.md` — [Any-Code-Change].** **Fires.** `Fixed`.
- **`skills/<component>/SKILL.md` — [Skill-Driven-Component].** Does **not**
  fire. No component's CLI surface, model, lifecycle or guardrails changes.
  `.claiming` is an adapter-private detail no skill mentions — verified by grep
  rather than assumed.

Task 4 is those two files, committed separately from the code.

## Verification

What the suite cannot check:

- **That the fix does not widen the safety hole.** The pristine check exists to
  refuse deleting someone's work. Criteria 3 and 4 cover a real item beside the
  directory, but neither covers a real item **inside** `.claiming` — a claim in
  flight. Build that state by hand, the way
  `tests/test_external_work_store.py:1023` does, and confirm `init --work-path`
  still refuses. If it does not, the fix forgives more than a name and the spec's
  stated risk has landed.
- **That `start` really is untouched.** `git diff tcw/store/fs.py` should show
  two hunks, one in `init` and one docstring. Read it rather than trusting the
  test count.
- **The end-to-end user story.** Reproduce the original refusal on a scratch
  node, apply nothing, confirm it refuses; then with the fix confirm it
  relocates and the work store is genuinely at the new path.

## Notes

- No task depends on another except Task 2 on Task 1, and the suite is green at
  every commit boundary but the deliberate red one.
- **This is the first of two items touching claiming.** The next is
  `2026-09-09-validate-a-slug-before-the-claiming-lookup-globs-with-it`. Their
  combined difference gets a separate review pass before either is called done,
  per this repository's rule about interactions only reachable once both land.
