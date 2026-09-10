# Two defects older or wider than the branch that surfaced them

Both were found verifying the four items on `feat/stage-gate-and-prompt-verbs` on
2026-09-10, and neither belongs to those items. Filed separately so the branch's
own findings — see the companion note,
`2026-09-10-verification-findings-on-the-stage-verb-branch.md` — stay scoped to
what those four items changed.

## 1. `[{blob: ''}]` is advised by an error message and rejected by the parser

`tcw/store/base.py:1362` tells the user, in an error message:

```
… or bind [{blob: ''}] for a stage that should say nothing
```

`_parse_binding` at `tcw/store/base.py:1284` rejects exactly that value:

```python
if not isinstance(value, str) or not value.strip():
    problems.append(f"{where}: binding '{kind}' must be a non-blank string")
    return None
```

Reproduced end to end in a throwaway node:

```
work check: tcw-config.yaml: work.lifecycle.stages.verify.prompt[0]:
  binding 'blob' must be a non-blank string
$ tcw work stage prompt verify | wc -c
2540
```

The binding is dropped during parsing, the stage's binding list empties, and
`resolve_prompts` falls back to TCW's built-in floor — which the CLI then wraps in
both bookends. A user following the advice gets the loudest possible result from
the instruction meant to produce silence.

The advice came in with `1b5b31d`, so it predates this branch. It matters more now
because `1ecce6a` copied it into `docs/migration-guide-1.X-to-2.0.0.md:108`, where
it reaches every user reading how to upgrade to 2.0.0. **Fixing the guide sentence
alone leaves the source of the claim in place**, still ready to be copied
somewhere else.

Two things to decide, which is why this is a request and not a patch:

- **Whether silencing a stage should be supported at all.** If it should, the
  parser is what is wrong and an empty `blob` ought to be accepted as a
  deliberate silence, distinct from an absent binding. If it should not, the
  error message is what is wrong and must stop advising it.
- Today the only way to make a stage resolve to nothing is a `when:` condition
  that never matches, which works but reads as an accident rather than an
  intention.

Whichever way it goes, a test should pin it: nothing currently checks that advice
printed by an error message is accepted by the parser that prints it.

## 2. Neither `|| true` guard on the composing skill is tested

`skills/tcw-work-stage/SKILL.md` injects two commands, at lines 20 and 24, each
ending `|| true`:

```
!`cat "${CLAUDE_PLUGIN_ROOT}/skills/tcw-work/references/lifecycle/stage-$stage.md" || true`
!`tcw work stage prompt $stage $item || true`
```

Item `2026-09-09-compose-a-lifecycle-stage-into-one-skill-document` measured two
independent causes of a silent empty render, and its own outcome calls that
failure *indistinguishable from the skill not existing*:

- an injected command that is not pre-approved, which aborts the invocation with
  `num_turns: 0` and no error;
- a non-zero exit from an injected command, which aborts it the same silent way.

Only the first got a test —
`test_the_composing_skill_declares_the_commands_it_injects` guards the
`allowed-tools` declaration, and it does bite: dropping `Bash(cat *)` fails it.

The second is unguarded. Deleting either `|| true` reproduces the failure, and
nothing in the suite would notice. A stage id with no router file, or any CLI
error from `tcw work stage prompt`, is enough to trigger it in normal use.

A test in the same file as the existing one, asserting both injected commands end
with the fallback, is the obvious shape. It is cheap, and the failure it prevents
is the one the item itself identified as undetectable from the outside.

## Related

A third guard on the same skill was found weakened and **does** belong to the
branch, so it is recorded in the companion note rather than here:
`test_the_composing_skill_reads_with_prompt_and_names_begin_for_entry` stopped
biting once a second copy of the literal it looks for appeared in the skill's
manual-fallback fence.

---

## Resolved, 2026-09-10, on `fix/pre-2.0.0-review-findings`

Both were fixed rather than deferred, once it turned out neither needed the design
decision this note assumed.

**1 — the silencing advice.** Answered, and the design question with it. Rather
than reword four documents to describe a workaround, `{blob: ""}` was made to
mean what all four already said it meant. Four independent descriptions of the
same behaviour is evidence about what the shape should mean.

`prompt: [{blob: ""}]` now validates and silences the stage: it resolves to empty
text, the resolver drops it like any other empty part, and the stage prints
nothing with no bookend. Verified end to end — zero bytes, against an
unconfigured control stage in the same node still printing the built-in floor, so
the opt-out is a choice rather than resolution breaking.

The exception is confined to `blob`. `file`, `generate` and `skill` each name
something to run or read, and a blank one of those keeps the non-blank rule.
`prompt: []` also stays refused, and the distinction is the substance of the
decision: a list with the opt-out written in it states a choice, while an empty
list cannot be told apart after parsing from never writing the key.

The test pins the property rather than the wording — whatever the empty-prompt
error advises has to be a shape this parser accepts — so the class cannot come
back through a rewording. That is the part worth keeping from this note.

**2 — the untested fallbacks.** Six lines, so they were written rather than
tracked. Every injected command in the composing skill is now checked to end with
its `|| true`, closing the second of the two silent-empty-render causes the item
measured.

## Settled: a blank blob is the opt-out

This note originally left the design question open, with three candidate answers
and "doing nothing" among them. It was put to the user and answered: accept a
blank `blob` as deliberate silence.

The reasoning that decided it, recorded because the alternatives were close:

- **It is what people already expect.** Four documents written at different times
  independently described this exact spelling as the way. That is not four copies
  of one mistake; it is four authors reaching for the same shape.
- **It does not reintroduce the ambiguity that got the empty list refused.** The
  empty list is indistinguishable after parsing from an absent key. A list with
  an entry in it is not.
- **It costs one condition in the parser**, against a new schema key with its own
  parse branch, validation rule, and interaction to define with `prompt:`.

Shipped in 2.0.0 rather than tracked as a follow-up, because the migration guide
was already carrying a correction about the old advice and splitting the two
would have told readers the fix existed while making them wait for it.

Nothing further is open here.
