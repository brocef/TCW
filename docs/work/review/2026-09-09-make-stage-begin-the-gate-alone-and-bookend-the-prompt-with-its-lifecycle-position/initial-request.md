# Request: make `stage begin` the gate alone

`tcw work stage begin` should stop emitting the prompt and only run the legality
check and the `pre` bindings. `tcw work stage prompt` then becomes the single
source of the instruction text, and the composed view an agent reads becomes:

1. run `tcw work stage begin <id> <ref>` if you have not already;
2. the output of `tcw work stage prompt <id> <ref>`;
3. a closing section saying what to do to continue to the next stage.

## Why

The two verbs currently print byte-identical text — same bytes, same digest, on
any stage `begin` allows. That duplication is why the seven stage documents had
to be reworded to stop promising instructions that were already on screen: any
view composing a stage out of both shows the same text twice, and every wording
around it is an apology for the repetition.

With `begin` silent, each verb has one job. `begin` gates. `prompt` says what to
produce. Nothing has to explain why the same text appeared twice.

It also answers the objection that killed the `pre` verb during the split's
intake — "no CI job, script, hook, config, skill, or test would call it." A
gate-only verb now has callers: the composed skill names it, and the prompt
itself will.

## Why now rather than after 2.0.0

2.0.0 already breaks every `tcw work stage` call site. Changing the same command
twice inside one migration costs a user one edit; deferring makes it a second
major break later.

## The risk this must answer

Once `begin` prints nothing, nothing about wanting the instructions makes anyone
run it — `prompt` answers and never refuses. Today an agent following a stage
document runs one command and is gated on the way. The replacement has to put
that reminder somewhere every reader of the text sees it, in both harnesses,
rather than relying on a skill that only Claude has.
