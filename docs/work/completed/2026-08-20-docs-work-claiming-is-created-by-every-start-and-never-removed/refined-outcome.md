# Refined outcome — The leftover claiming directory

**Accepted.** One line of production code, five tests, eight criteria met.

## The verification decision

Taken autonomously, on four readings plus my own.

- **Codex** and an **Opus advisor**, before implementation, independently. Both
  rejected the obvious fix — removing the directory — and both supplied reasons I
  did not have. Codex killed my own fallback option by pointing out a single
  retry does not close the race either. The Opus advisor found the consumer that
  made the item worth doing at all.
- **`adversarial-code-reviewer`**, on the combined difference of this item and
  the next. Could not get a store deleted that should survive, through a file,
  a dangling symlink, a symlink to a real directory, or a directory of dotfiles.
- **`tcw-verifier`**, which drove the real `init` over eleven store shapes and
  the whole user story through the CLI.
- **My own**: the original refusal reproduced with the directory as the sole
  change on an otherwise pristine store, and a mutation check proving that
  forgiving the directory's *contents* rather than its name turns the
  claim-in-flight test red.

## What acceptance rests on

That the harm was reproduced and its absence re-reproduced, with one directory as
the only variable. Not on the suite: this item's change is invisible to almost
all of it.

## The one thing worth remembering

**The intake misdescribed both the symptom and the harm, and that is why the item
sat unprioritised for three weeks.** It said the leftover directory makes an
assertion "pass for the wrong reason"; on the node it describes, that assertion
fails. It called the directory "harmless in itself"; it made `tcw init
--work-path` refuse to relocate an otherwise-empty store, telling the user to
move work that does not exist.

A missing item can be filed later. A misdescribed one is worse: it is on the
board, it reads as settled, and nobody can weigh it.

## What was accepted rather than fixed

Each is a decision, recorded so a future reader can disagree with it.

- **The directory is still never removed.** Three independent reasons, in the
  outcome and now in a comment beside the `mkdir` where someone would try again.
- **`.claiming` is forgiven by name, not by contents.** A hole in a safety check,
  sized deliberately and pinned by two criteria and a mutation check.
- **A symlink of that name pointing at an empty directory became deletable.**
  The loss is the symlink; the target survives.
- **A race window opened between the pristine check and the delete**, on exactly
  the nodes that have started items. Accepted because relocating a store is a
  deliberate single-operator act.
- **`graveyard.yaml` still refuses relocation.** Correct — it is real history —
  and the release note now names it, after a first draft claimed the refusal
  "only appears when your store really does hold work".

## Deferred

- **`tcw work start --take-over` cannot recover from the CLI**, to
  `docs/work/inbox/2026-09-11-take-over-cannot-recover-a-claim-from-the-cli.md`.
  Found verifying the companion item, pre-existing, and larger than either.
- **The version cut**, per the run's standing instruction.
- **No originating GitHub issue**; filed by adversarial review.
