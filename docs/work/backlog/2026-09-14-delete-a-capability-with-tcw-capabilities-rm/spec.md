# Spec — Delete a capability with `tcw capabilities rm`

## Capability changes

```yaml
new:
    - capabilities/remove-a-capability
changed:
    - capabilities/reset-an-override
    - work/complete-a-work-item
```

- **New — `capabilities/remove-a-capability`** ("Remove a capability",
  `Subject: capability`). The counterpart of `taxonomy/remove-a-local-term`: I run
  `tcw capabilities rm <path>` to delete a local capability, and the tool refuses
  an inherited one, one with capabilities nested under it, and one another
  capability still points at.
- **Changed — `capabilities/reset-an-override`.** Its body says a standalone local
  capability "tells me to use `remove` instead"
  (`docs/capabilities/capabilities/reset-an-override/description.md:1`). `remove`
  is not a command; the body will name `tcw capabilities rm`.
- **Changed — `work/complete-a-work-item`.** Gains one paragraph: a work item can
  declare a capability it deleted under `removed:` in `capabilities.yaml`, and the
  completion gate checks that the path no longer resolves.

## Problem

### Nothing in the CLI deletes a capability

`tcw capabilities` has no `rm` subcommand. `SUBCOMMANDS` is `init, list, show,
path, add, search, check, set, reset, extends, drift`
(`tcw/capabilities/cli.py:12`), and `add_subparser` registers exactly those
(`tcw/capabilities/cli.py:259-310`). The taxonomy has one: `tcw taxonomy rm`
(`tcw/taxonomy/cli.py:104-126`, registered at `:208-210`).

The store operation already exists. `CapabilitiesStore.remove` is declared
abstract with no docstring (`tcw/store/base.py:565-567`), and
`FsCapabilitiesStore.remove` (`tcw/store/fs.py:2481-2488`) resolves the path,
refuses an unknown one and an inherited one, and then runs `git rm -rf` on the
folder (`tcw/store/fs.py:1689-1691`, `:566-568`). Its only callers are tests
(`tests/test_capabilities.py:620`, `tests/test_capabilities_federation.py:143`
and `:392`, `tests/test_non_git_writes.py:265`).

So a user who wants a capability gone has two choices, both wrong: mark it
`Omitted`, which the skill defines as "we deliberately don't have this"
(`skills/tcw-capabilities/SKILL.md:105`), or delete the folder by hand, which is
the filesystem shortcut `docs/lifecycle/abstraction.md` rules out.

### The store operation deletes more than it is asked to

Reproduced on a scratch node built with `python evals/seed_fixture.py`:

1. **It deletes nested capabilities without a word.** Paths nest: `add routes`
   then `add routes/login` gives two capabilities, one inside the other's folder
   (`FsCapabilitiesStore.add` checks only that the new folder is absent,
   `tcw/store/fs.py:2460`). `remove("routes")` runs `git rm -rf` on `routes/`,
   and afterwards `get("routes/login")` returns `None`.
2. **It leaves references dangling.** With `other` carrying
   `Superseded by: routes/login`, removing `routes/login` succeeds, and `other`
   now fails `tcw capabilities check` with
   `Superseded by → dangling identifier`. Four fields hold references to other
   capabilities: `Superseded by` and `Blocked by` (`tcw/store/fs.py:2818-2820`),
   and `Roles` and `When`, whose tokens are `roles/…` and `conditions/…`
   capability paths, optionally prefixed with `!` (`tcw/store/fs.py:2833-2844`).

### A work item cannot declare a deleted capability

The completion gate reads `capabilities.yaml` through `declared_capabilities`
(`tcw/store/base.py:288-321`), which knows only `new:`, `added:` (an old name for
`new:`) and `changed:`. The gate returns early when both lists are empty
(`tcw/work/recursion.py:43`), and fails any `changed:` path that does not resolve
(`tcw/work/recursion.py:62-67`). A deleted capability no longer resolves, so it
cannot be listed under `changed:`, and any other key is ignored. The epic rollup
reads the same function and prints only `new` and `changed`
(`tcw/work/recursion.py:116-127`).

`2026-09-14-consolidate-the-setup-skills-into-a-single-tcw-setup-skill` deletes
nine capabilities and has nowhere to record them (its `spec.md`, "Capabilities").

### Documents name a command that does not exist

- `skills/tcw-capabilities/SKILL.md:107`: "a standalone local capability → use
  `remove`".
- `docs/guide/taxonomy-and-capabilities.md:139`: "a standalone local capability
  (use `remove`)".
- `FsCapabilitiesStore.reset`'s refusal: "(use `remove` to delete it)"
  (`tcw/store/fs.py:2493-2494`), and the abstract docstring (`tcw/store/base.py:573`).
- The ledger entry `capabilities/reset-an-override`, quoted above.

## Goals

1. `tcw capabilities rm <path>` deletes a local capability, mirroring
   `tcw taxonomy rm`: addressed by path, refuses an unknown, ambiguous or
   inherited path, and writes nothing when it refuses.
2. Deleting a capability never deletes a second one and never leaves another
   capability's reference field pointing at nothing.
3. The rules for deleting live in the abstract store contract, so a store that is
   not a filesystem gets the same refusals.
4. A work item declares a deleted capability under `removed:` in
   `capabilities.yaml`, the completion gate accepts it only once the path no
   longer resolves, and the epic rollup shows it.
5. Every document that says "use `remove`" names the real command.

## Non-goals

- **Changing `tcw taxonomy rm`.** It has the same nested-deletion behavior
  (`FsTaxonomyStore.remove`, `tcw/store/fs.py:1941-1948`, also `git rm -rf`) and
  only warns about relations. Changing it changes a shipped command's behavior,
  which is a separate decision; an inbox note records it.
- **Clearing a reference field from the CLI.** `set --field "Blocked by="` is
  refused today, because the empty string is validated as a reference and fails
  (`tcw/capabilities/cli.py:101-106` passes `""`; `tcw/store/fs.py:2529-2541`
  checks it). That gap matters to a user whose `rm` is refused for a reference
  (see Risks), but it is a change to `set`, not to deletion.
- **Checking prose links.** A `[text](tcw://C/<path>)` link in another
  capability's `description.md` is not checked by `rm`. `tcw validate` already
  resolves every such link node-wide and reports one that dangles
  (`tcw/validate.py:311-319`).
- **Checking open work items.** A work item whose `capabilities.yaml` names the
  deleted path under `new:` or `changed:` is not looked for. Pointers run from
  work to capabilities, never back; the capabilities store does not read the work
  axis, and that item's own completion gate reports the dangling path.
- **Projects that inherit this one.** A project that `extends` this one may hold
  an override of the deleted capability. Inheritance is declared by the child, so
  this project cannot see it; the child's `tcw capabilities check` reports
  `overrides → dangling id`.
- **A `--force` flag, cascading deletion, or a web-app delete route.** `tcw serve`
  has no capability delete route (`tcw/serve/__init__.py:1328-1376`) and gains
  none.
- **Committing.** Like `tcw taxonomy rm`, `rm` stages the deletion and does not
  commit it.

## Design

### The store contract (`tcw/store/base.py`)

`CapabilitiesStore.remove(identifier)` gets a docstring stating the contract every
store must honor. Deleting a capability is a store operation that a tracker or a
database can perform — delete a record, having checked two queries — so it
passes the abstraction litmus test and belongs on the interface. It already is
there; this adds the rules.

`remove` deletes the local capability at `identifier` and refuses, writing
nothing, when:

| Case | Refusal |
| --- | --- |
| nothing resolves | `ValueError`: `no such capability: <path>` |
| a bare path matches more than one inherited store | `AmbiguousRef` |
| the capability is inherited (with or without a local override) | `ValueError`: `cannot remove inherited capability '<qualified>' (edit it at its source; to drop a local override use \`tcw capabilities reset\`)` |
| another capability or override is nested under its path | `ValueError` naming each nested path |
| another local capability or override references it through `Superseded by`, `Blocked by`, `Roles` or `When` | `ValueError` naming each referrer and field |

The `reset` docstring and refusal say `tcw capabilities rm` instead of `remove`.

### The filesystem adapter (`tcw/store/fs.py`)

`FsCapabilitiesStore.remove` keeps its current first two steps and adds three
checks before `_rm`:

- **Listed spelling:** a local capability is deleted only when the identifier is
  exactly its listed path. `get` also resolves `routes/`, `./routes`, and `Routes`
  on a case-insensitive disk, but echoes that spelling back as the path, so every
  later step would work from the wrong one. Any other spelling is
  `no such capability`.
- **Nested:** every `meta.yaml` found inside the target's folder other than its
  own. Asked of the folder itself, not of `_all_meta_dirs()`, which skips
  dot-directories and unreadable nodes that `git rm -rf` would delete anyway. It
  catches capabilities and override folders alike.
- **Referrers:** for every folder `_all_meta_dirs()` returns other than the
  target, read its `meta.yaml` and take the tokens of the four reference fields
  exactly as `check` reads them: `str(value)` for `Superseded by` and
  `Blocked by` (`_ref_problems`); for `Roles` and `When` the list or
  comma-separated tokens, stripped, `!` dropped, and only those under `roles/` or
  `conditions/` respectively (`_check_globals`). A token refers to the target
  when `get(token)` resolves to a local capability **whose folder is the target's
  folder**, compared as the same file on disk rather than the same spelling:
  `a/b/`, `x/../a/b` and `A/B` all resolve, and `set` accepts each. A token that
  does not resolve, or is ambiguous, refers to nothing and is skipped.

Override folders are read as well as local capabilities because an override's
fields are written by `set` and validated against this store
(`tcw/store/fs.py:2613-2621`), so an override can hold `Blocked by: <local path>`.
Inherited capabilities' own fields are not read: they resolve against their own
store, not this one.

### The command (`tcw/capabilities/cli.py`)

`rm` is added to `SUBCOMMANDS` (so `tcw capabilities rm x` is not rewritten to
`show`) and registered with one positional `path`, help "remove a local
capability". `_rm` calls `st.remove(args.path)`:

- success: prints `Removed capability <path>`, exits 0;
- `ValueError` or `RefError`: `tcw capabilities rm: <message>`, exits 1. An
  `AmbiguousRef` is a `RefError` whose message already reads
  `ambiguous ref '<path>' — qualify it with an alias prefix`.

Like `taxonomy rm`, it does not commit. Outside a git repository the store's
existing `_require_repository` refuses (`tcw/store/fs.py:1690`).

### Declaring a removal (`tcw/store/base.py`, `tcw/work/recursion.py`)

`declared_capabilities` returns a third list, `removed`, read from a `removed:`
key with the same rules as the others: a list of paths, a trailing ` # comment`
stripped, duplicates dropped, anything but a list raising `SidecarError`.

```yaml
new:
    - skills/tcw-setup
changed:
    - work/complete-a-work-item
removed:
    - plugin/work-lifecycle
```

The completion gate (`capability_gate`):

- no longer returns early when `new:` and `changed:` are empty but `removed:` is not;
- for each `removed:` path: a **local** capability still resolving at that path
  is a problem,
  `<path>: declared (removed) but still resolves (delete it with \`tcw capabilities rm\`)`;
  anything else passes. Only a local hit counts because `rm` deletes only local
  capabilities: once a local `auth/login` is gone, the bare path can fall through
  to an inherited `auth/login` (or be ambiguous between two), which `rm` refuses,
  so counting that would leave the item unable to complete.

The epic rollup (`_capability_deltas`) prints `removed <path>` rows alongside
`new` and `changed`, and its "no entries" message names all three keys.

### Decisions on the open questions

1. **An inherited capability is refused.** It lives in another project's store;
   deleting it here has no meaning, and `Status: Omitted` on an override already
   says "we deliberately don't have this". This is today's store behavior
   (`tcw/store/fs.py:2485-2487`), kept.
2. **A local override is not something `rm` deletes.** `rm` on an overridden
   inherited path refuses as inherited, and the message names
   `tcw capabilities reset`, which is the one operation that drops an override.
   One command per meaning: `rm` deletes a capability, `reset` deletes an
   override.
3. **A capability another capability points at is refused**, naming each
   referrer and field. The conservative option: the user repoints the reference
   first. A warning (what `taxonomy rm` does for `relatesTo`) would leave
   `tcw capabilities check` failing after a command that reported success.
4. **A capability with capabilities nested under it is refused**, naming them.
   `git rm -rf` on the folder would delete them all; the user removes the nested
   ones first, deepest first.
5. **The key for a deletion is `removed:`**, matching the existing past-tense
   `changed:` and the "new / changed / removed" wording the skill and the spec
   template already use (`skills/tcw-capabilities/SKILL.md:33`,
   `tcw/work/templates.py:41`). **The gate requires that no local capability
   resolves at that path at completion.**

## Acceptance criteria

Each is checked by a test in the suite unless it says otherwise.

1. On a node with local capability `x` (no nested entries, no referrers),
   `tcw capabilities rm x` exits 0, prints `Removed capability x`; afterwards
   `tcw capabilities show x` exits 1, and `git status --porcelain` lists `x`'s
   `meta.yaml` as deleted in the index (`D `).
2. `tcw capabilities rm nope` exits 1 with `no such capability: nope` on stderr,
   and the capabilities tree is byte-identical before and after.
3. `rm` of an inherited path, bare and `<project-id>/`-qualified, exits 1 with
   `cannot remove inherited capability`; both projects' trees are unchanged.
4. `rm` of an inherited path that has a local override exits 1, the message
   contains `tcw capabilities reset`, and the override folder is still present.
5. `rm` of a bare path present in two inherited stores exits 1 with `ambiguous`
   on stderr and changes nothing.
6. With `routes` and `routes/login` both capabilities, `rm routes` exits 1,
   stderr names `routes/login`, and both still resolve.
7. For each of `Superseded by`, `Blocked by`, `Roles` (including a `!`-prefixed
   token) and `When`, a local capability referencing the target makes `rm` exit 1
   naming the referrer's path and the field, and the target still resolves. The
   same holds when the reference is held in an override folder, and when the
   reference is spelled loosely (`a/b/`, `./a//b`, `x/../a/b`). A value `check`
   does not resolve to the target (`" a/b "`, `!a/b` or a list under
   `Blocked by`, a `When` token outside `conditions/`) does not block the delete;
   nor does a sibling path such as `routes-v2`, and a capability nested inside a
   dot-directory does block it. (Extended in review round 1.)
8. After the referrer is repointed with `tcw capabilities set`, `rm` of the same
   target succeeds.
9. `rm ../taxonomy/<term>` (a path escaping the store) exits 1 with
   `no such capability` and deletes nothing. So does a loose spelling of a real
   path — `routes/`, `./routes`, `routes/.`, `routes//` — which would otherwise
   slip past the nested check. (Added during implementation: found by probing,
   see `outcome.md`.)
10. Outside a git repository, `FsCapabilitiesStore.remove` refuses and writes
    nothing (the existing `tests/test_non_git_writes.py:265` stays green).
11. `tcw capabilities --help` lists `rm`.
12. `declared_capabilities({"removed": ["a/b # gone"]})` returns
    `{"new": [], "changed": [], "removed": ["a/b"]}`, and `{"removed": "a/b"}`
    raises `SidecarError`.
13. An active item whose `capabilities.yaml` holds only `removed: [ghost/path]`
    (never existed) completes with `tcw work complete --resolution done --confirm`
    (exit 0).
14. An active item whose `capabilities.yaml` holds `removed: [auth/login]` while
    `auth/login` still resolves fails `tcw work complete` (exit 1), stderr contains
    `declared (removed) but still resolves`, and the item stays `active`. An
    inherited capability at the same bare path does not fail it. (Added in review
    round 1.)
15. `tcw work reconcile <epic>` on a child task declaring `removed: [a/b]` renders
    `removed a/b` in the rollup.
16. `grep -rn 'use \`remove\`' skills docs/guide tcw docs/capabilities` finds
    nothing (checked by hand in the plan's verification).
17. `skills/tcw-capabilities/SKILL.md` documents `removed:` in its schema
    paragraph and `tcw capabilities rm` in its quick reference.
18. `python -m pytest` and bare `pytest`, both run from the repository root, pass.

## Risks

- **A typo under `removed:` passes the gate.** "Does not resolve" cannot tell a
  deleted capability from one that never existed, and reading git history to tell
  them apart is ruled out by `docs/lifecycle/abstraction.md` ("state is the
  status; git is archive"). Mitigation: the skill tells agents to copy each path
  from `tcw capabilities list` before deleting it. A capability tombstone like the
  work axis's would close this; not built here.
- **A refused `rm` for a reference can leave a user stuck.** The referrer's field
  can be repointed with `set`, but not cleared from the CLI (see Non-goals). The
  refusal message says to repoint or clear the field; clearing needs the web app
  or an edit to `meta.yaml`. No capability in this repository's ledger holds any
  of the four reference fields today, so the consolidation item is unaffected.
- **Nested refusal forces an order.** Deleting a subtree means deleting the
  deepest entries first. None of the nine capabilities the consolidation item
  deletes has anything nested under it.
- **`git rm -f` discards uncommitted edits** to the deleted capability's own
  tracked files. That is the point of deleting it, and it is what `taxonomy rm`
  already does.
- **A capability whose files git has never seen** (written by hand, never staged)
  makes `git rm` fail. The top-level CLI already turns that into
  `tcw: git command failed (exit 128): …` after git's own `pathspec … did not
  match any files` (`tcw/cli.py:547-558`), and nothing is deleted. Left as is.
- **A downstream project's override dangles** after its upstream capability is
  deleted (see Non-goals); reported by that project's own `check`.

## Notes

- The sibling sweep for "a delete that removes more than its target" covered
  every `_rm` caller in `tcw/store/fs.py` (`:1948`, `:2488`, `:2505`, `:4063`,
  `:5729`, `:5931`, `:6324`). Only `FsTaxonomyStore.remove` shares the shape; the
  work store's deletes act on one item folder or one named file, and `reset`
  deletes exactly one override folder found by id. The taxonomy case is out of
  scope (Non-goals) and gets an inbox note.
- Decisions 3 and 4 (refuse rather than warn or cascade) are the requester's to
  confirm; they were chosen as the conservative option.
