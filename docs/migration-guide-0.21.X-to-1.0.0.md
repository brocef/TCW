# Migrating from 0.21.x to 1.0.0

> **If you are on 2.0.0 or later, one command below has been renamed.** This
> guide describes 1.0.0, and every `tcw work stage <id> <slug>` in it is written
> as 1.0.0 shipped it. In 2.0.0 that form was removed and split in two:
> `tcw work stage begin <id> <slug>` does what it always did — check the stage is
> legal, run its `pre` checks, then print the instructions — and
> `tcw work stage prompt <id> [<slug>]` prints the same instructions without the
> legality check and without running any checks, with the work item optional.
> Nothing else in this guide changed. The text is left as written because it
> records what 1.0.0 did, and rewriting it would make it describe a release that
> never existed; see
> [the 2.0.0 guide](migration-guide-1.X-to-2.0.0.md) for that migration.

Version 1.0.0 is a large release with a **very small migration**. There is
exactly one thing that can fail on upgrade, and it only fails if you configured
it. Everything else in this guide is either a behavior change you should know
about or a new capability you can ignore until you want it.

If you have never written a `work.lifecycle` block in your `tcw-config.yaml`,
nothing here breaks and you can skip to
[What's new, and optional](#whats-new-and-optional).

## The one break: an empty prompt list

`tcw validate` now **rejects an empty prompt list**, in both spellings:

```yaml
work:
    lifecycle:
        stages:
            spec:
                prompt: [] # rejected
            plan: [] # also rejected — the legacy bare-list form
```

Fix it one of two ways, depending on what you meant:

```yaml
spec:
    prompt: [{ blob: "" }] # "this stage should say nothing" — deliberate
```

...or delete the line entirely, if you meant nothing in particular.

**Nothing stops working while you fix it.** Only `tcw validate` complains; every
other command runs exactly as before. The parser's problem list is advisory, and
the policy loader discards it.

**Why it changed.** An empty list never said anything. Under 0.21.x that was
merely useless. Under 1.0.0 a stage you have configured *nothing* for falls back
to TCW's own built-in instructions — so an empty list now reads like an opt-out,
which it is not: it gets the default too. Rejecting it makes you say which one
you meant.

`pre: []` is untouched, in both the stage and the transition positions. Nothing
is behind `pre:`, so an empty list there means exactly what it says.

## What changed under you

None of these will fail on upgrade. They change what commands *return*, which
matters if you have scripts, agent instructions, or documentation resting on the
old answers.

### `tcw work new` no longer leaves a file to edit

Creating an item used to write a starter `initial-request.md` with three empty
headings, and print its path. It no longer writes anything but `state.yaml`.

**Check for:** any instruction or script of the form "run `tcw work new`, then
open the file it printed". That file does not exist now. The request document
appears when someone writes it.

This is deliberate: the starter document meant every item looked like its request
had already been written, so nothing could distinguish an item somebody had
thought about from one somebody had merely named.

### Piped input goes to `intake.md`

```sh
echo "the thing is broken" | tcw work new "Fix the thing"
```

That text used to become the item's request. It now becomes `intake.md` — raw
input, kept exactly as it arrived, never edited on your behalf.

`tcw work inbox accept` does the same: it writes the entry's own words, a list of
everything it preserved, and where it came from, into `intake.md`. It no longer
wraps them in a half-written request full of `TBD`. Attachments, binary files,
and the rest of what it kept before, it still keeps.

**Check for:** anything that read an accepted inbox entry out of
`initial-request.md`.

### The board's letters mean something different

`tcw work list` column three used to show `R` on every item from the moment it
was created, because creation wrote a request. Now:

| Shows | Means                                                      |
| ----- | ---------------------------------------------------------- |
| `-`   | neither raw intake nor a written request                    |
| `i`   | someone dropped this on us; nobody has written it up        |
| `R`   | came in as a written request                                |
| `iR`  | arrived as raw input and has since been written up          |

**Check for:** anything parsing that column. It will not error — it will quietly
mean something else. An item that would have shown `R` under 0.21.x may now show
`-`, and lowercase `i` is a letter your parser has never seen.

### Reading and editing an item's body

`tcw work show` displays the request when there is one and the raw intake
otherwise, so there is always something to read. An item with neither shows an
empty body rather than failing.

Editing the body **always writes the request, never the intake.** On an item that
has only raw intake, editing creates the request for the first time and says so.
The intake is left exactly as it arrived — raw input that quietly changes is not
raw input any more.

In the local web app, the Initial Request tab now shows only the request. On an
item whose request has not been written, the tab says so and the editor opens
blank. Previously it handed you the raw intake to edit under the request's name,
which copied it into the request the moment you saved.

### An epic's rollup moved out of its request

`tcw work reconcile` used to write its summary into the epic's
`initial-request.md`. It now writes `rollup.md` alongside the epic's other
documents.

**Epics you already have migrate themselves.** The first time you reconcile one
after upgrading, the rollup block moves out of the request and into `rollup.md`;
anything you wrote around it stays where it was. If the rollup was the only thing
in the request, the empty file is removed rather than left behind.

**Check for:** `tcw work show <epic>` no longer prints the rollup, because it
prints the request and the rollup is no longer in it. To read a rollup, run
`tcw work reconcile <epic>` — it prints the current one and changes nothing if
nothing has changed. `tcw work path <epic>` tells you where the file lives.

The web app lists `rollup.md` and marks it generated, with no Edit button:
`reconcile` writes that file and would discard anything you typed there.

### Two JSON details, if you keep unusual values

If you keep a YAML **set** in an item's `capabilities` block, it used to appear
as the string `"{1, 2}"` and now appears as a proper list, `[1, 2]`. Dates,
binary values, and deeply linked structures are all handled properly now rather
than being stringified on the way out.

One case that used to pass silently now **raises**: a mapping whose keys collide
once stringified — `{1: "a", "1": "b"}` — used to drop a value without telling
you. It is now an error.

### The core revision token changes once

Every existing item's core revision token changes on first read after the
upgrade, because the token now hashes which artifact the body resolved from. The
token is compared within a session and never persisted, so this matters only to
something holding one *across* the upgrade itself. In practice: restart it.

## Upgrade ordering: the CLI and the plugin version separately

This one is not in the release notes, and it is the most likely thing to confuse
you.

The `tcw` CLI and the TCW agent plugin are versioned and installed
independently. Upgrading one does not upgrade the other, and a plugin cache
holding the **0.21.1** skills against a **1.0.0** CLI is a state you can easily
end up in.

It matters because the 0.21.1 `tcw-work` skill directs the agent to
`tcw work lifecycle --stage <id>`, which reports what is *bound* and never
resolves a `builtin`. On a project that has configured nothing — which is most
projects — that command prints nothing useful. The command that works is
`tcw work stage <id> <slug>`, and only the 1.0.0 skill names it.

**Check for it:**

```sh
tcw --version
```

...and compare against the plugin version your harness reports. If the CLI says
1.0.0 and the plugin does not, update the plugin, or your agent will keep using
a command that predates the feature it is trying to reach.

## What's new, and optional

None of this is required. It is here so you know what you now have.

**`tcw work stage <id> <slug>`** prints the instructions for a lifecycle stage —
TCW's own by default, yours if you configure them. TCW ships instructions for all
six stages that run against an existing item (`inbox` runs before an item exists,
so it has none), which means this works on a project that has configured nothing
at all. It checks the stage makes sense for the item's status, runs the stage's
`pre` checks, and prints the result to stdout alone so you can pipe it. It writes
nothing — no document, no draft, no status change. `--no-exec` runs nothing at
all, printing what it *would* have run, which is how you read an unfamiliar
project's lifecycle before triggering any of it.

**`tcw work scaffold <artifact> <slug>`** writes `<artifact>.draft.md` from a
template. A draft is a file to type into, not the document: the board still shows
the artifact as unwritten, because it is. It refuses once the real document
exists, and refuses to overwrite a draft you have typed into (`--force` replaces
one deliberately).

**`tcw work show <slug> --json`** prints the item as a machine-readable document
— a version marker, every field under its own name, and an `artifacts` map saying
which lifecycle documents exist, so a script can ask "has the spec been written?"
without looking at files. It is the same shape the local web app's API returns.

**Writing your own stage instructions.** A stage can now carry instructions
written inline (`blob:`), read from a file in your project (`file:`), or produced
by a script you own (`generate:`), composed with TCW's own via `builtin: true`:

```yaml
work:
    lifecycle:
        stages:
            spec:
                prompt:
                    - builtin: true
                    - file: docs/lifecycle/spec-rules.md
```

Prompt lists **concatenate** in the order you wrote them. Templates under
`artifacts:` are **first-match-wins**, so a `builtin` fallback belongs last —
and a template of your own *replaces* TCW's rather than extending it.

Any binding can carry a `when:` condition (`tags:`, `not_tags:`, `type:`). A
stage can carry a `pre:` check that must pass before its instructions are given.

## If you are moving rules out of your agent guide

TCW's own repository did exactly this before 1.0.0 shipped: its `AGENTS.md` went
from 80 lines to 54, with the prime directive, the implementation rules, and the
harness-parity rule moving into `docs/lifecycle/*.md` files bound to the `spec`,
`plan`, and `implement` stages. Five things it learned, in the order they hurt.

**1. Find out what reads your agent guide before you empty it.** A rule another
skill locates *by name* in `CLAUDE.md` cannot move into a stage prompt just by
being copied there — the skill would still go looking for the heading. TCW's own
`documentation-sync` skill did this for a `## Documentation Sync` section, and
its version-cut path still does it for a `## Versioning` section.

**Documentation entries are now configuration, and that is the better answer.**
Declare them in `tcw-config.yaml` under `work.documentation` and `tcw validate`
checks their shape, `tcw work docs` prints them, and `tcw work stage plan` /
`tcw work stage implement` include them in the stage's instructions:

```yaml
work:
    documentation:
        - path: README.md
          trigger: Public-API
          description: >-
              Public-facing overview and CLI usage. Update when the public
              surface or user-facing behavior changes.
        - path: docs/changelogs/upcoming.md
          trigger: Any-Code-Change
          description: Developer changelog; technical, grouped by category.
```

Three required keys, all non-empty strings. A `path` need not exist yet, and a
`trigger` may be any name your project defines — the vocabulary is open. A
project that declares nothing keeps the old behavior exactly: the stage prompts
still tell the agent to read the `## Documentation Sync` section, byte for byte.

The general lesson survives, and still applies to `## Versioning`: **stage prompts
can carry your stage-scoped rules, but not your integration points.** Grep your
skills and tooling for `CLAUDE.md` and `AGENTS.md` before you start — and where an
integration point has a configuration form, prefer it, because a heading someone
renames is not a contract.

**2. A rule your source code cites needs a citable location.** Prefer `file:`
over `blob:` for anything referenced from outside the config. A module docstring
can point at `docs/lifecycle/abstraction.md`; it cannot point at a string buried
in `tcw-config.yaml`. TCW's litmus test was cited from two module docstrings, two
README sections, and six planning documents — ten sites, four of which an initial
review sweep missed because they cited the *rule* without naming it. Grep for the
guide's filename, not for the rule's title.

**3. Templates replace; prompts compose.** Worth repeating because the
asymmetry is easy to trip over. A `prompt:` list led by `builtin: true` extends
TCW's instructions. An `artifacts:` template does **not** — first match wins, so
your template replaces TCW's outright and must restate whatever of the built-in
skeleton you still want. That copy will drift silently when a future release adds
a section, so write a test that asserts every heading in the built-in still
appears in yours. TCW's own is `tests/test_repo_lifecycle.py`.

**4. Don't bind a template you haven't changed.** TCW wrote a `plan` template,
found it byte-identical to the built-in, and deleted it. Binding an unchanged
copy buys nothing and takes on the drift from point 3. Bind a template only where
you are actually adding something.

**5. Stage checks and transition checks have different strength.** A `pre:` under
a **transition** is enforcing: it runs before the store is touched and a non-zero
exit aborts the move. A `pre:` under a **stage** is advisory: it runs only when
someone invokes `tcw work stage`, and neither `tcw work scaffold` nor any
transition consults it. Both are useful — put the rule you must guarantee on a
transition and the rule you want to prompt for on a stage — but do not read a
stage check as a gate.

Two practical notes on the checks themselves. Keep them fast: TCW put
`tcw validate` (0.9s) on its `complete` transition and rejected `pytest -q`,
which takes seven minutes on that repo and would simply have been routed around.
And write a check that asks the CLI rather than the filesystem —
`tcw work show "$TCW_SLUG" --json` reports which artifacts exist, so a check
never has to know your store's directory layout.

Finally, a caveat that is not about migration but will bite here: `tcw serve`
runs **no** hooks, so a `pre` check on `complete` does not block completion from
the local web app.

## What you don't have to do

- **Nothing to your existing lifecycle configuration**, other than the empty
  list. A bare list of skills or commands under a stage id still means "prompt",
  still renders identically, and is checked against recordings of the 0.21.x
  behavior rather than asserted.
- **Nothing to items you already have.** Every existing item has a request
  document, so it reads, displays, and shows on the board exactly as before.
  Nothing is rewritten or backfilled — an item that never had raw input does not
  get an invented one.
- **Nothing to your epics.** They migrate themselves on the next `reconcile`.
- **Nothing to adopt the new commands.** `tcw work stage` and
  `tcw work scaffold` are additions. Not running them costs you nothing you had.
