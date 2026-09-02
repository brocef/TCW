# Upcoming

User-facing release notes for the next version. Plain language — no jargon or
internal module names.

## Instructions for the inbox stage, from the command line

`tcw work stage` now answers for every stage of the lifecycle, including the
inbox — the point where a raw drop becomes a tracked item. It used to answer for
six of the seven and return an error for that one, so the guidance on how to
turn an incoming request into a work item was only available to people who had
installed the agent plugin. Anyone who installed `tcw` on its own got nothing.

Because the inbox stage runs before an item exists, it is the one stage you run
without naming a work item:

```sh
tcw work stage inbox
```

Naming one is reported as a mistake rather than guessed at. Every other stage is
unchanged and still takes its work item, and what they print is unchanged too.

If you have written your own instructions for a stage, nothing about how they
are chosen has changed — the inbox stage now simply has a TCW default to fall
back to, the same as the rest.
