# Spec: `stage gate` is the gate alone; the prompt carries its own bookends

## The shape

`tcw work stage` keeps two verbs. Neither is `begin`, which is renamed rather
than narrowed in place.

| Verb | Does | stdout |
| --- | --- | --- |
| `tcw work stage gate <id> [<ref>]` | status legality check, then the stage's `pre` bindings | **empty** |
| `tcw work stage prompt <id> [<ref>]` | resolves and prints the instructions; no legality check, no `pre` | the instructions |

`begin` is renamed to `gate` because the verb no longer begins anything: it runs
no transition, writes no artifact, and changes no field, so a user who runs it
and sees silence has nothing to tell them whether it did its job. `gate` is the
word the codebase and its documents already use for the thing it runs. The
rename is free — `begin` appears in no released changelog or release note and
has never shipped.

On success `gate` prints one line on **stderr** naming the command that produces
the instructions, and leaves stdout empty so a caller piping it gets nothing
rather than a fragment. On refusal it is unchanged: exit 1, empty stdout, the
reason on stderr.

## The bookends

Every resolved prompt is wrapped, by the resolver, in two generated sections:

- a **header** telling the reader that this text ran no gate, and to run
  `tcw work stage gate <id> <ref>` first if they have not;
- a **footer** naming what to do when the stage's output is written.

They are generated from one table rather than written into the seven prompt
files, for two reasons. The files are capped at 50 lines and `spec.md` is at 49,
so they do not fit. And seven copies of navigation text drift; one table cannot.

The footer's table, keyed by stage id:

| Stage | When it is done |
| --- | --- |
| `inbox` | `tcw work stage gate request <slug>` on the item just accepted |
| `request` | `tcw work stage gate spec <slug>` |
| `spec` | `tcw work stage gate plan <slug>` |
| `plan` | `tcw work start <slug>`, then `tcw work stage gate implement <slug>` |
| `implement` | `tcw work submit <slug>`, then `tcw work stage gate verify <slug>` |
| `verify` | `tcw work complete <slug> --resolution done --confirm` |
| `postmortem` | nothing — it runs out of band and moves no item |

**The bookends wrap a project's own `prompt:` bindings too.** A project that
overrides what a stage *says* has not overridden where the lifecycle goes next,
and a reader of the overridden text needs the gate reminder exactly as much.

## Why the header is not optional

Once `gate` prints nothing, wanting the instructions no longer makes anyone run
it — `prompt` answers and never refuses. Today an agent following a stage
document runs one command and is gated on the way. The header is what replaces
that, and it has to live in the resolved text rather than in the composing skill,
because the skill is Claude-only and the guarantee must reach Codex too.

## `--no-exec`

`gate --no-exec` reports the `pre` checks it would run and nothing else; the
prompt plan is no longer its business.

`prompt` now **accepts** `--no-exec`, which it previously refused. The refusal's
reason was that suppressing `file:` and `generate:` would leave incomplete
instructions on stdout. Under `--no-exec` it prints **no** instructions at all —
stdout is empty and the plan goes to stderr — so the reason does not apply, and
refusing would drop the conditioned matched/skipped diagnostic that this change
otherwise removes from the CLI entirely.

## Acceptance criteria

1. `tcw work stage gate <id> <ref>` on a legal stage whose checks pass exits 0
   with **empty stdout** and one stderr line naming `tcw work stage prompt`.
2. It still refuses an illegal stage: exit 1, empty stdout, the status reason.
3. It still runs the stage's `pre` bindings, and still refuses when one fails —
   proven with a sentinel, so non-execution cannot be mistaken for success.
4. It resolves **no** prompt: a `generate:` binding bound to the stage does not
   run. Proven with a sentinel that `prompt` on the same node does create.
5. `tcw work stage begin …` is gone; the removed-form handler names `gate` and
   `prompt`, and exits 2.
6. `inbox` takes no reference on either verb, and `gate inbox` runs inbox's
   `pre` bindings.
7. Every stage's resolved prompt begins with the gate header naming that stage's
   own `gate` invocation, and ends with the footer for that stage id.
8. The bookends are present when the project configures its own `prompt:`
   bindings, not only on the built-in floor.
9. `postmortem`'s footer says nothing follows, rather than naming a command.
10. The seven prompt files are unchanged and each still under 50 lines.
11. `gate --no-exec` lists the `pre` checks and no prompt entries.
12. `prompt --no-exec` exits 0, prints nothing on stdout, and lists the prompt
    plan with conditioned entries marked, on stderr.
13. The seven stage documents name `gate` for entering and `prompt` for reading;
    the parity test's literal follows.
14. `tests/fixtures/prompt_fallback/unconfigured.json` is **re-captured**, its
    docstring says the text changed deliberately in this release, and the
    six `argv` arrays name `prompt` rather than a gate verb.
15. `docs/migration-guide-1.X-to-2.0.0.md` describes one command becoming two,
    with a runnable before/after, and no longer claims `begin` behaves exactly
    as 1.x did.
16. `tcw validate` and `tcw capabilities check` exit 0; the suite passes.

## Non-goals

- Changing what any stage's instructions **say**. Only the bookends are added.
- A transition. `gate` still moves nothing and writes nothing.
- Deriving the footer from the lifecycle graph. There is no next-stage edge in
  `LIFECYCLE_STEPS`, and inventing one to serve a text footer would put a
  navigation concern into the model every store implements.

## The abstraction litmus test

The bookend table is lifecycle metadata beside `STAGE_STATUSES`, not a store
operation: a non-filesystem store answers `lifecycle_policy()` exactly as before
and never sees it. `gate` asks the same questions of the store it already asked —
`get()`, the policy's `stage_checks()` — and simply stops asking for the prompt.

## Harness compatibility

Both verbs are CLI, so both harnesses get them identically. The header exists
precisely so the gate reminder does not depend on the Claude-only composing
skill.
