# Spec: compose a lifecycle stage into one skill document

## Goal

A Claude user invoking one skill with a stage id and a work item reference
receives the stage's working document and the instructions this project resolves
for that stage, in that order, as one document — without the skill becoming a way
to skip the gate.

## Behaviour

`skills/tcw-work-stage/SKILL.md`, named arguments `stage` and `item`:

1. A preamble saying the two blocks are different documents and neither replaces
   the other.
2. `` !`cat "${CLAUDE_PLUGIN_ROOT}/skills/tcw-work/references/lifecycle/stage-$stage.md" || true` ``
3. `` !`tcw work stage prompt $stage $item || true` ``
4. A closing section: the second block came from the reading verb, which runs no
   legality check and no `pre` bindings; `tcw work stage begin $stage $item` is
   what enters the stage; and if a block is missing, run both commands by hand.

`allowed-tools` declares `Bash(tcw *)` and `Bash(cat *)`.

## Acceptance criteria

1. Invoked for a stage that **is** legal for the item, both blocks render with
   real content and no command error.
2. Invoked for a stage that is **not** legal, both blocks render and
   `prompt`'s `not legal … printing anyway` note is visible to the model.
3. Invoked as `inbox` with no item, both blocks render and there is no error.
4. Invoked with an unknown work item, the skill still renders and the CLI's own
   `no such work item` message is visible — not silence.
5. The interpolated router path resolves to an existing file for all seven ids
   in `STAGE_IDS`, checked by a test rather than at runtime.
6. A test fails if the skill stops naming `tcw work stage begin`.
7. A test fails if either injected command leaves `allowed-tools`.
8. The seven routers still name `begin`; `test_skill_lifecycle_parity.py`'s
   harness-neutral check is untouched and passing.
9. `skills/tcw-work/SKILL.md` is unchanged — it is at its 60-line budget and the
   rule on breach is extract, never grow.

## Non-goals

- Any change to the CLI, to `tcw work stage begin`, or to `prompt`.
- A Codex equivalent. There is none; the two commands are the Codex answer.
- Replacing `begin` anywhere, in any document.
- A `commands/` slash-command wrapper. A plugin skill is directly invocable.

## The abstraction litmus test

Nothing here is a store operation. The skill composes two existing commands'
output; both already speak the abstract vocabulary, and this adds no new
question for an adapter to answer.

## Harness compatibility

Claude-only, deliberately, and permitted as such: `docs/lifecycle/harness.md`
names context injection and skill arguments as Claude-only features that are
"welcome as _enhancements_, never as the sole carrier of a requirement." The
requirement — that an agent can find out what a stage asks for — stays carried by
`tcw work stage begin` and `tcw work stage prompt`, which behave identically
under both harnesses. Criterion 8 is what holds that line.
