# Spec — Add a way to rename a work item's slug

## Capability changes

- **added:** `work/rename-a-work-item` — change an open item's slug, with
  every reference TCW can find rewritten and the old slug pointing at the new.

## Problem

`tcw work edit --title` changes an item's title but not its slug. The folder
name, the branch name and every reference keep the old wording for the rest of
the item's life, and nothing renames a slug. In the real case, an item about
*removing* a participant was widened to cover adding, removing and stepping
down, and retitled to match. Its slug still says removal only, and every
command and cross-reference must use it. Today it can be done by hand, but
only by someone who knows every place a slug is recorded.

## Goals

1. **`tcw work rename <slug> <new>`** renames an open item: `backlog`,
   `active` or `review`.
   - `<new>` is either a full slug or the part after the date. The item keeps
     its original date prefix, because the date records when it was created.
     A full slug with a different date is refused.
   - `<new>` must already be in slug form (`slugify(<new>) == <new>`). It is
     refused otherwise, naming the slug form, rather than silently rewritten.
   - It is refused when the new slug is held by an item, a tombstone or an
     earlier rename, and when it equals the old one.
2. **What moves.**
   - The item folder, in place: the same status folder, or the same parent
     folder for a nested child.
   - Its `tracker.yaml` travels with it.
3. **What is rewritten**, in one commit governed by
   `work.auto-commit-transitions`:
   - on this board: every item's `blocked_by` entries naming it, `parent`, and
     `initiative`;
   - `initiative` in graveyard entries, when the item is an epic, so the epic
     keeps its count of resolved children;
   - for an epic, `initiative` on the other boards that
     `initiative_children` reads;
   - capability `meta.yaml` `Planning doc:` fields on this node that name it.
4. **The old slug is recorded** in a separate `renames.yaml` at the work root
   (`old: new`), not as a tombstone. Every existing tombstone reader treats a
   tombstone as a resolved item: a `blocked_by` naming one counts as resolved,
   so a reference the rename missed would silently unblock.
   - **Reads follow it.** `show` and `path` given the old slug print the item
     with a line `<old> was renamed to <new>`. A blocker naming the old slug,
     including one in another project that this command could not rewrite,
     resolves to the renamed item and its real status.
   - **Writes refuse**, naming the new slug. That covers `start`, `submit`,
     `complete`, `edit` and the others: a mutating command should not act on a
     name the user may not know is stale.
   - Chains (`a → b → c`) are followed to the end, and a loop is refused when
     it is written.
   - `_unique_slug` treats a renamed-away slug as taken.
5. **Refused, with the steps to do it by hand:**
   - an item with a worktree or a recorded branch (`git branch -m` and moving
     `.worktrees/<slug>/` are the user's);
   - an item another owner has claimed, or with a claim in progress
     (`.claiming/<slug>-*`);
   - a resolved item, whose folder may be gitignored in other clones and which
     already has a tombstone under its old slug.
6. **What it reports, and does not change:**
   - files in the item that still mention the old slug in prose (`spec.md`,
     `plan.md` and the rest);
   - a tracker ticket whose description links the old slug;
   - `tcw://<project>/<old>` links in other projects, which the renames record
     now resolves.

## Non-goals

- **Rewriting prose, commit messages, or file names outside the store** (such
  as a changelog's `upcoming/<slug>.md`). They are reported where TCW can find
  them, and left alone.
- **The same verb for capabilities and taxonomy.** That is its own item,
  `2026-09-16-add-a-rename-verb-to-tcw-capabilities-and-tcw-taxonomy`, which
  proposes `mv`, since capability and taxonomy paths are hierarchical. A work
  slug is a name, not a path, and the issue asks for `rename`. Those two words
  are not forced to match.
- **Renaming a worktree item.** Refused (goal 5).

## Design

- `WorkStore.rename(slug, new_slug) -> WorkItem` on the base class, with the
  validation shared: `rename_slug` and `WorkStore.rename_refusal` in
  `tcw/store/base.py` hold every refusal that does not depend on storage. A store where the slug is a field changes the field and
  keeps an alias. That passes the litmus.
- `FsWorkStore.rename`, which runs:
  - under the store lock (`_graveyard_lock` today, `_store_lock` once
    `2026-09-29-hold-one-lock-on-the-work-store-for-every-transition-not-only-the-resolving-ones`
    lands);
  - every refusal first: the destination folder must not exist, and
    `renames.yaml`, the graveyard and every file about to be rewritten must
    parse and have no uncommitted changes, nor may the item's own folder;
  - then the `renames.yaml` write, then `git mv` of the folder, then the
    reference rewrites, then one scoped commit. A failure after the first
    write is undone (the move reversed, each file restored to the bytes it
    had), so the command can simply be run again.
    *Corrected at review:* this first said a failure after the record left
    the old slug resolving and a re-run completed the move. A re-run was in
    fact refused, by either slug, so a half-done rename could only be undone
    by hand.
- Lookup: `_find` misses → `renamed(slug)` → follow. Mutating CLI verbs call
  `_resolve`, which refuses on a followed rename. `show` and `path` accept it
  with the note. Blocker evaluation follows it.
- The CLI verb is `rename`, listed in `--help`.

## Acceptance criteria

1. `tcw work rename <slug> widened-scope` on a backlog item: the folder is
   `backlog/<date>-widened-scope/`, `state.yaml` is otherwise unchanged, and
   one commit holds the move and `renames.yaml`.
2. An item blocked by it, and a child with `parent` and `initiative` naming it:
   all rewritten in the same commit.
3. `tcw work show <old>` prints the renamed item and the note.
   `tcw work start <old>` exits 1, naming the new slug.
4. A blocker in a second project naming `tcw://<project>/<old>`: its status
   follows the renamed item. The blocker is still open while the item is open,
   and resolved once it completes.
5. `tcw work new` with a title that slugifies to the old slug gets `-2`, as it
   would for a tombstone.
6. Refused cases, each exiting 1 with nothing changed: a worktree item;
   another owner's claim; a completed item; a new slug that is taken; a new
   slug not in slug form; a different date prefix.
7. An epic renamed: `initiative` in its children on this board, in a child
   board, and in graveyard entries all name the new slug, and its resolved
   children still count.
8. A capability `meta.yaml` with `Planning doc: <old>` is rewritten.
9. The full suite passes as CI runs it.

## Risks

- **References TCW does not know about** stay stale, and are reported where
  they can be found. `renames.yaml` makes the old slug resolve for reads and
  blockers, which covers the rest.
- **A new file at the work root**, `renames.yaml`. It is created only on the
  first rename, and `validate` checks its shape: a mapping of slug to slug,
  with no loops.

## Notes

- Advisors: Opus, and Sonnet in place of Codex (at its usage limit until
  2026-10-03).
- Both chose a separate `rename` verb, not `edit --slug`: open statuses only,
  refused for worktree items and for another owner's claim, keeping the date,
  and one commit.
- **Split on the pointer.**
  - Sonnet wanted a graveyard entry with `renamed_to`.
  - Opus showed that every tombstone reader treats a tombstone as resolved.
    Its list: `base.py` blocker evaluation, `capabilities/cli.py`, `refs.py`,
    `recursion.py`, and several in `work/cli.py` and `fs.py`. So a missed
    reference would silently unblock.
  - I took Opus's separate record.
- **Split on lookups.**
  - Sonnet: refuse, or at most follow for read-only verbs.
  - Opus: reads follow with a note, writes refuse.
  - These agree for reads and writes. Blocker evaluation follows, per Opus,
    because that keeps other projects' blockers correct.
- Opus also supplied: the capability `Planning doc:` field, graveyard
  `initiative` entries, epics' children on other boards, and the stale tracker
  ticket link.
