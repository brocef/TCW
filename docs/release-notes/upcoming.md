# Upcoming

User-facing release notes for the next version. Plain language — no jargon or
internal module names.

## Work items can now sit in review

There is a new status between "being worked on" and "done": **review**. It means
the work is implemented and is waiting for someone to accept it.

```sh
tcw work submit my-item     # active → review
tcw work rework my-item     # review → active, if it didn't pass
```

An item in review is **not finished**. It still blocks anything that depends on
it, and it still keeps its epic open — because a review can reject the work and
send it back. `rework` is the only way to move backwards; nothing ever comes
back out of completed or discarded.

**Review is optional.** A small change can go straight from active to completed
exactly as before. `tcw work complete` will print a one-line note that the
review step was skipped and then complete normally — it does not ask you to
confirm anything extra, and it does not fail.

### One rule worth knowing

If a review rejected the work, `tcw work rework` will refuse while
`refined-outcome.md` is still there. That document says the work was checked and
accepted, which is no longer true. Delete it — and write down what still needs
doing in `rework.md` — and the command will go through. TCW deliberately does
not delete the file for you.

## Record the pull request on a work item

```sh
tcw work edit my-item --pr https://github.com/you/repo/pull/42
```

Shown by `tcw work show`. Nothing depends on it yet; it is there so an item can
carry the link to the branch or PR its code lives on.

## Upgrading

**Existing projects need no migration.** Nothing changes status, and no files
are rewritten. Your projects were set up with four status folders; the `review`
folder is created the first time something moves into it.

**One thing to check: you can no longer name a project `review`.** Project IDs
can't collide with a status name, and `review` is now a status. If you have a
project using that ID, rename it before upgrading — otherwise `tcw validate`
will report the collision.

## Smaller things

- The "phase" field is gone. It was displayed on `tcw work show` and in epic
  rollup tables, but nothing ever set it, so it was always blank. Existing items
  are unaffected.
- Items in review appear on the board directly under active work.


## Work transitions now commit themselves

**This changes what `tcw work` does to your repository, so it is worth reading.**

Previously, moving an item between statuses staged the change and left it for you
to commit. Now `tcw work start`, `submit`, `rework`, and `complete` each make
their own commit recording just that move.

The commit is **scoped to the item that moved**. Other work in progress in your
tree — an edited spec for a different item, uncommitted notes — is left exactly
as it was and is never swept in.

This applies to the local web app too. Changing an item's status in `tcw serve`
now commits it, the same as the command line does.

### Turning it off

```yaml
# tcw-config.yaml
work:
    auto-commit-transitions: false
```

Transitions then behave exactly as they did before: staged, and yours to commit.

One exception: `tcw work start --worktree` always commits, whatever this setting
says. The work branch is created from your current commit, so if the status move
were not committed first the new branch would not contain the very item it was
made for.

### Warning when you are off your main branch

```yaml
# tcw-config.yaml
work:
    trunk-branch: main
```

With this set, transitioning an item while some other branch is checked out
prints a warning and commits where you are. It never switches branches, never
commits somewhere else, and never refuses. Items with their own TCW work branch
do not warn — that is where they are supposed to be.

## Completing work that was merged elsewhere

If you used `tcw work start --worktree` and then merged the branch yourself —
through a pull request, say — TCW's own merge step has nothing left to do and
would only get in the way:

```sh
tcw work complete my-item --resolution done --confirm --already-integrated
```

Everything else still applies: blockers, capability reconciliation, the epic
check, and `--confirm`. Only the merge is skipped.

## Smaller things

- Completed items no longer store a Definition-of-Done list. It was the same five
  lines on every item, so it never recorded anything. The checklist is still
  shown before you confirm. Items completed earlier are untouched.


## Bind your own skills and commands to the lifecycle

TCW's lifecycle has named steps — stages that produce a document, transitions
that move an item's status. You can now attach your own agent skills or shell
commands to any of them, in `tcw-config.yaml`:

```yaml
work:
    lifecycle:
        stages:
            spec: [{ skill: superpowers:brainstorming }]
        transitions:
            complete:
                pre: [{ command: "pytest -q" }]
```

Say `skill:` or `command:` explicitly — a bare string is rejected rather than
guessed at. `tcw validate` will tell you exactly which line is wrong.

**`pre` runs before anything changes.** If it fails, the transition is cancelled
and nothing is written. **`post` runs after**, and if it fails the item has
already moved — TCW reports the failure and exits non-zero, but does not undo
anything.

Your commands run from the project root with `TCW_SLUG`, `TCW_STATUS`,
`TCW_TRANSITION`, and `TCW_NODE_ROOT` available, and are given five minutes
before timing out (`work.lifecycle.timeout` changes that).

Skills are **named, not run** — TCW can't invoke a skill; your agent does that.

Two limits worth knowing up front:

- `tcw-config.yaml` is a file in your own repository, and commands from it run
  with your permissions. It is trusted like a `Makefile`, not sandboxed.
- **The web app does not run hooks.** `tcw serve` still performs and commits the
  transition, but skips anything you've bound to it — a `pre` hook that would
  block a transition will not block it there. The complete dialog says so.

## Seeing what the lifecycle expects

```sh
tcw work lifecycle              # every stage and transition, and what's bound
tcw work lifecycle --json       # the same, for scripts
```

It lists what each step is for, what it reads, what it produces, and what the
tool will refuse past. It changes nothing and runs nothing.


## The work skill is reorganized around the lifecycle

The `tcw-work` skill used to describe the lifecycle in two long documents that
said almost the same thing — and had quietly stopped agreeing with each other, and
with the tool. Both are gone.

In their place there is **one short document per lifecycle step**, each with the
same five headings: what the step is for, what it reads, what it produces, the
steps themselves, and how it ends — including how it ends badly. Your agent loads
only the one it needs.

Every documented step now says **who does it and whether anything enforces it**:
the tool does it automatically, the tool refuses if you get it wrong, the tool
reminds you, or nothing checks at all. Where TCW relies on judgment, it now says
so instead of implying otherwise.

Two new commands: `/tcw-process-inbox` for triaging raw requests, and
`/tcw-verify-work` for the acceptance step. Claude users also get a read-only
`tcw-verifier` agent that assesses finished work against its spec without being
able to change anything. Codex has no custom agents and no slash commands, so
every one of these workflows is also reachable by asking the agent to use the
`tcw-work` skill directly — nothing is available only one way.


## Post-mortems on finished work

When something goes wrong with a work item — verification sends it back, or a
plan turns out to have been built on a wrong assumption — you can now ask for a
post-mortem:

```
/tcw-post-mortem <slug>
```

It reads the item's documents backwards from the outcome and answers one
question: **which step could first have caught this?** It writes `post-mortem.md`
alongside the item's other documents and changes nothing else — it does not
reopen a completed item, and it can be run before or after completion, since the
need for one is often only obvious afterwards.

It is deliberately reluctant to recommend anything. If the cause was a one-off,
or the only available advice is "be more careful", it says so and stops rather
than inventing process.

Codex users get the same thing by asking the agent to use the `tcw-post-mortem`
skill.
