# Request: compose a lifecycle stage into one skill document

Working a lifecycle stage takes two reads that nothing joins. The stage's own
document — `skills/tcw-work/references/lifecycle/stage-<id>.md` — says how to
work the stage. The instructions the project resolves for it come from the CLI.
An agent has to open one, run the other, and hold both.

Claude Code can close that gap without moving anything into the CLI. Skills take
arguments (`$name` declared in `arguments:` frontmatter) and can inject a shell
command's output into their body with `` !`cmd` ``. A skill taking the stage id
and the work item reference can therefore be exactly:

    <the stage document for that id>

    <the output of `tcw work stage prompt <id> <item>`>

`prompt` is what makes this possible at all. It is the verb that reads without
entering — no legality check, no `pre` bindings — so it can be resolved for an
item the stage is not yet legal for, which is precisely when someone wants to
know what the stage asks for. The verb shipped in the same release; this is its
second caller, and the first that is not its author.

## What this must not become

`prompt` runs no gate. A skill that delivers a stage's instructions and stops
there is a documented route around the legality check and the `pre` bindings the
lifecycle exists to enforce. It has to name `tcw work stage begin` as the verb
that enters, and something has to fail if it stops naming it.

`docs/lifecycle/harness.md` governs the rest: context injection and skill
arguments are Claude-only, and Claude-only features are welcome as enhancements
and never as the sole carrier of a requirement. The seven routers must keep
naming `begin`, so a Codex user runs the two commands and loses the
concatenation and nothing else.

## Consumer impact

Additive. No CLI change, no configuration change, no change to any existing
skill's behaviour — one new skill directory and a row in the command reference.
