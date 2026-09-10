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

**1 — the silencing advice.** The design question does not have to be answered to
stop advising something that does not work. A stage whose every binding is
conditioned out already resolves to nothing, verified end to end: that shape
validates and prints zero bytes where an unconfigured stage prints the 2398-byte
built-in floor. All six places now name it — the error message that originated the
advice, both migration guides, the configuration guide, the capability
description, and the release notes, which asserted the premise without naming the
mechanism. Archived release notes are untouched; they record what was believed
when written.

The new test checks the property rather than the wording: whatever the message
names has to be a shape this parser accepts. That closes the class, not the
instance.

**What is still open** is the narrower question this note actually raised: there
is no first-class way to say "this stage says nothing". Conditioning a binding on
a tag no item carries works, but it reads as a trick rather than an intention.
Whether to accept a blank `blob` as a deliberate silence, or add an explicit
opt-out, is still a design decision nobody has made. Filed on its own below.

**2 — the untested fallbacks.** Six lines, so they were written rather than
tracked. Every injected command in the composing skill is now checked to end with
its `|| true`, closing the second of the two silent-empty-render causes the item
measured.

## Still open: a first-class way to silence a stage

`prompt: [{ blob: "-", when: { tags: [never-applied] } }]` is the documented way
to make a stage say nothing. It works, and it is a trick: the binding exists only
so it can fail to match, and the placeholder text is never read by anyone. A
reader has to be told why it is shaped that way, which is why it now costs three
lines of comment in the migration guide.

Two candidate answers, and this is a decision rather than a defect:

- **Accept a blank `blob` as deliberate silence**, distinguishing it from an
  absent binding. This is what four documents already believed was true, which is
  some evidence about what people expect.
- **Add an explicit opt-out** — a `silent: true` on the stage, or similar — and
  keep rejecting the blank blob.

Doing nothing is also defensible. The trick works and is now documented honestly.
