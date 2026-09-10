# Verification findings on the `feat/stage-gate-and-prompt-verbs` branch

Four work items sit at `verify` in `review` status on this branch. All four were
verified on 2026-09-10 against `f355e02` by four read-only agents, with every
finding re-checked by hand against the working tree before being written here.

**No verdict artifact was written.** Neither `refined-outcome.md` nor `rework.md`
exists for any of the four; the acceptance decision is still open. This note is
the durable record of what the verification found, so the findings survive the
session that produced them.

The four items, in the order they landed:

1. `2026-09-01-separate-lifecycle-stage-information-from-stage-prompts-in-the-tcw-work-skill-references`
2. `2026-09-02-split-tcw-work-stage-into-prompt-and-begin-subcommands`
3. `2026-09-09-compose-a-lifecycle-stage-into-one-skill-document`
4. `2026-09-09-make-stage-begin-the-gate-alone-and-bookend-the-prompt-with-its-lifecycle-position`

## What holds

`pytest -q` gives **2450 passed**, zero failed, zero skipped, on this machine.
That refutes item 1's recorded `2184 passed, 5 failed` as a present fact while
confirming its diagnosis: all five named tests pass here, four having been
root-only artifacts of a container running as uid 0 and the fifth a broken
setuptools in that image. `test_the_prompts_are_in_the_built_wheel` passing here
directly verifies the packaging claim item 1 had to check by hand.

`tcw validate` and `tcw capabilities check` both exit 0.

The great majority of acceptance criteria across the four items hold. Where a
criterion names the removed `begin` verb, the underlying guarantee survives under
`gate`. Two criteria that read as unmet are deliberate reversals, each claimed and
justified in item 4's spec with replacement criteria pinning the new behaviour:
the two verbs no longer produce byte-identical stdout, and `prompt` now accepts
`--no-exec` which it previously refused.

`STAGE_NEXT_STEPS` is complete and correct for all seven stages and guarded three
ways. `bookend()` is applied by the CLI at `tcw/work/cli.py:1026` rather than
inside `resolve_prompts`, as item 4's outcome claims, so a stage that resolves to
nothing stays nothing.

## Defects present in the tree

Seven, all small, all still in the working tree at `f355e02`.

### 1. The developer changelog still describes the removed verb

`docs/changelogs/upcoming.md` lines **102, 138, 173, 176, 177** say the release
contains `begin`. This is the changelog for the version about to be cut, not an
archive, so a reader gets a false account of the code they installed. Line 102
contradicts itself inside a single bullet, naming `begin` and then `gate` two
sentences later.

Lines 8 and 48 also name `begin` and must **stay**: both exist in order to say the
verb does not exist.

Three independent sweeps agree on exactly these five lines.

### 2. A published capability statement is false

`docs/capabilities/work/read-the-documentation-gate-for-a-change/description.md`
line 16 reads:

> the version offer *after* an item completes, when `tcw work stage prompt
> implement` is correctly refused because the item is closed.

`prompt` refuses nothing by design. Reproduced on an item in `review`:

```
$ tcw work stage prompt implement <slug> >/dev/null; echo $?
0
tcw work stage prompt: note — 'implement' is not legal for an item in 'review';
it runs in active. Printing its instructions anyway because you asked to read
them, not to enter the stage.

$ tcw work stage gate implement <slug> >/dev/null; echo $?
1
tcw work stage gate: 'implement' is not legal for an item in 'review'; it runs in active
```

The verb should be `gate`. Item 2's commit `67edccd` wrote `begin` there, which
was true at the time; item 4's rename commit `1ecce6a` changed it to `prompt`
where the meaning was the refusal.

The same file also names `prompt` three times (lines 5, 6, 16) and `gate` zero
times, so it fails item 2's criterion 22 requirement to name both verbs. The
sibling description `docs/capabilities/work/run-a-lifecycle-stage/description.md`
is correct throughout.

### 3. The migration guide's silencing advice does not work

`docs/migration-guide-1.X-to-2.0.0.md` line 108:

> A stage you have deliberately silenced with `{blob: ""}` stays silent and is
> not wrapped.

Both halves are false. Reproduced in a throwaway node:

```
work check: tcw-config.yaml: work.lifecycle.stages.verify.prompt[0]:
  binding 'blob' must be a non-blank string
$ tcw work stage prompt verify | wc -c
2540
```

`_parse_binding` rejects the empty string, the binding is dropped, the stage's
binding list empties, and `resolve_prompts` falls back to the built-in floor —
which then gets both bookends. The opposite of silent.

Suggested replacement, which is true:

> A stage whose bindings all carry a `when:` condition that does not match
> resolves to nothing, and nothing is not wrapped.

The sentence is new in `1ecce6a`. Its **root cause is older than this branch** and
is filed separately — see the companion note.

### 4. The old-spelling message misdirects `inbox` users

`tcw/work/cli.py:1089` defaults the reference placeholder to the literal `<slug>`
for every stage id:

```python
ref = args.rest[0] if args.rest else "<slug>"
```

For `inbox`, both branches of the advice it prints are then refused:

```
$ tcw work stage inbox
tcw work stage: 'inbox' is not a subcommand; run `tcw work stage gate inbox <slug>`
to check the stage and run its checks, or `tcw work stage prompt inbox <slug>` for
its instructions

$ tcw work stage gate inbox some-slug
tcw work stage gate: 'inbox' runs before an item exists and takes no work item;
run it with no argument
```

Two wrong turns before a user on the old spelling reaches the working command.
This falls in the gap between item 2's criterion 5, which only requires the
handler to name both verbs and exit 2, and item 4's criterion 6, which tests the
two verbs directly rather than the advice string. A one-line fix in the message
construction: omit the reference for `inbox`.

### 5. A test guard stopped biting, and neither item caused it alone

`tests/test_skill_lifecycle_parity.py:323`,
`test_the_composing_skill_reads_with_prompt_and_names_begin_for_entry`, defends
the one hazard item 3's plan calls out by name: the composing skill becoming a
documented route around the gate, since it is built on the reading verb. It
asserts only that a literal string appears somewhere in the body.

At `a9cc088` that literal occurred **once**, in the prose warning, so deleting the
warning failed the test. Item 4 added the same literal to the manual-fallback code
fence. It now occurs **twice**, in `skills/tcw-work-stage/SKILL.md`:

```
37:**`tcw work stage gate $stage $item` is what refuses.**
46:tcw work stage gate $stage $item        # may it run?
```

Deleting the entire prose warning now leaves the suite green. Verified by
mutation.

This is a combined-effect defect. No single-item review could have produced it,
and it is the highest-value finding of the round.

Smallest fix that restores the bite, scoped to the guard and leaving the skill
file untouched:

```python
prose = re.sub(r"```.*?```", "", body, flags=re.DOTALL)
assert "tcw work stage gate $stage $item" in prose, \
    "the skill names the gate only inside its manual-fallback fence"
```

Preferred over asserting a count of two, which would pass again if someone added
a third fence and deleted the prose.

The function's own name is also stale after the rename: it still says
`names_begin_for_entry` while its docstring says `gate`. It is the only stale
`begin` identifier left in the test suite.

### 6. The Codex plugin manifest undercounts its skills

`.codex-plugin/plugin.json:24` says the plugin ships **eight** skills and names
each one. There are **nine** directories under `skills/`, and `tcw-work-stage` —
the skill item 3 added — is not among those named. No test checks the count, so
nothing caught it.

### 7. The capture script's docstring names the wrong verb

`tests/fixtures/prompt_fallback/capture.py:26` says `tcw work stage` refuses
out-of-status stages. True of `gate`, false of `prompt`, which is the verb the
script now captures.

### The shape of five of these

Findings 2, 3 and 7 are the same error: the rename put the reading verb where the
meaning was the refusal. Counting the two changelog lines that describe the
refusal guarantee, that is **five places**, inside the very change whose commit
message says it set out to name the right one of the two everywhere.

Any fix should sweep for the pattern rather than patch the named lines.

## Records inaccuracies, no code impact

- **Item 1's criterion 8 is scored `Pass — 7 of 7` for a sentence that no longer
  exists.** The literal string it required is absent from all seven stage
  documents at HEAD, replaced by `bac46a2` and then `1ecce6a`. The guarantee
  survives under a stronger test than the criterion asked for:
  `test_every_stage_document_names_the_harness_neutral_binding_command` now
  requires **both** verbs in every router. Item 1's "Superseded within the same
  release" section names only the verb change and does not mention this.
- **Item 1's outcome records `2184 passed, 5 failed`**; the suite is clean here.
- **Item 1's outcome records `SKILL.md` at 60 lines**; it is 59. A sibling edit
  reclaimed a line. Still inside budget.
- **Item 3's outcome, criterion 4 row, quotes a line that no longer exists** — the
  one telling the reader to run the removed verb. True for its own commit, stale
  against HEAD.
- **Item 4's spec footer table for `implement` is wrong and the shipped code is
  right.** The spec says the footer should read ``tcw work submit <slug>``, then
  ``tcw work stage gate verify <slug>``; `tcw/store/base.py:1177` ships only the
  second. `verify` is legal from `active` as well as `review`, so naming `submit`
  would move items to `review` for no reason. The test at
  `tests/test_stage_verb.py:136` derives this from `STAGE_STATUSES` and is what
  caught it. Item 4's outcome does not list this among the four decisions it says
  moved during implementation.

## Evidence lost, and how it was reconstructed

`tests/fixtures/prompt_fallback/unconfigured.json` existed to prove a change did
not move the prompt bytes. Item 2 honoured that by hand-editing only the six
`argv` arrays. Item 4 **re-captured** the file, which was correct: the bookends
move that text on purpose, so the frozen bytes would have asserted something the
release makes false. Both events and the rule governing them are recorded in the
capture script's docstring and in `tests/test_prompt_fallback.py`.

The cost is real and documented: **nothing at HEAD asserts that the underlying
prompt text survived the verb split.** What the fixture pins from here is the
bookended text.

That evidence was reconstructed by hand during this verification and it holds —
comparing the `9194b2a~1` baseline against HEAD's fixture with the generated
header and footer stripped, all six recorded stdouts match byte for byte, the
only other difference being the slug normalised to `<slug>`. That reconstruction
is **not** in the suite. It is a fact established once, not a standing guard.

## Version state

All five version-bearing files read `1.3.1`; 2.0.0 has not been cut, which matches
item 1's outcome saying the cut follows the completion of the items on this
branch. Worth noting that `_stage_removed_form`'s docstring already says the old
spelling was "removed in 2.0.0", a release that does not yet exist. That resolves
itself at the cut.

Both `docs/changelogs/upcoming.md` and `docs/release-notes/upcoming.md` are
written and substantial. The release notes are correct on the verbs; the
changelog is not, per finding 1.

---

## Resolved, 2026-09-10, on `fix/pre-2.0.0-review-findings`

All seven defects above are fixed, along with three more found by a multi review
run afterwards. Each fix carries a test that was checked by mutation — the fix
reverted, the test observed to fail, the fix restored — because a guard that has
never failed has not been shown to guard anything.

| Finding | Fixed by |
| --- | --- |
| 1 — stale changelog lines | the three bullets now name `gate`; lines 8 and 48 kept, they exist to say the verb does not exist |
| 2 — false capability statement | names `gate` where the meaning is the refusal, and now names both verbs |
| 3 — the silencing advice | fixed at its source and all five copies; see the companion note |
| 4 — `inbox` advised a refused command | the one stage taking no reference is shown none |
| 5 — the guard that stopped biting | fenced blocks stripped before the assertion |
| 6 — plugin manifest undercount | corrected, and both the count and the enumeration are now checked |
| 7 — capture docstring wrong verb | rewritten, and the third re-capture recorded under the rule the docstring sets |

**The records inaccuracies above are left as they stand.** They describe what the
completed items claimed at their own commits, which is what an outcome is for.

**The lost fixture evidence stays lost**, as recorded. The reconstruction done
during verification is not in the suite and was not added: what the file pins from
here is the bookended text.
