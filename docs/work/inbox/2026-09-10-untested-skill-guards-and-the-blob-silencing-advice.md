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
