# Spec — Tidy three tracker messages left by the binding hardening review

## Capability changes

None. Each fix makes an existing message or check say what happened.

## Reproduction

Read from the code on `bug-run` (2026-09-29); each becomes a failing test first.

1. `tcw/work/cli.py` `_complete`'s merge-back hint: `git diff --cached
   --name-only` split on newlines. With a staged `docs/work/…/tracker.yaml` in a
   node whose folder name is not ASCII, git prints the path quoted
   (`"n\303\266de/…"`), so `(top / path).resolve()` never equals the item's
   record and the "tracker.yaml holds a record of a ticket move" hint is lost.
   With `diff.relative=true` and the node in a subfolder, the path is relative
   to the node and the comparison misses the same way.
2. `tcw/tracker/jira.py` `_json` ends `return _mapping(payload, path)`, so a
   `create_issue` answer of `[]` or `"ok"` raises "unexpected shape" before
   `tcw/tracker/create.py` can say "It may exist; look for a ticket titled…".
   Also, `{"key": null, "id": null}` reads as the key `"None"`.
3. `_create_one` returns `_tracker_link(...)` without adding to `reasons`; the
   filing hook then prints "the binding did not follow (creating it did not
   succeed)" — the opposite of what happened.
4. `_check_issue` checks that `fields`, `status`, `statusCategory` and
   `assignee` are mappings, not what they hold: `{"status": {"name": 5}}` reaches
   `assess(current_status=5)`, which calls `.strip()`.
5. Strict `drop` (CLI `_drop`, web `_strict_refuses`) asks
   `ever_bound`, which answers `True` for an unreadable `tracker.yaml`; both then
   say "is, or was, bound to a ticket".

## Problem

Each message states something that did not happen, or a response shape crashes
a command that should report a tracker problem.

**Sibling sweep** (`grep -rn "\-\-name-only" tcw`; `grep -rn "current_status=" tcw`;
callers of `ever_bound`): `FsWorkStore` reads `git ls-tree -r --name-only` in two
places (`_nested_tree_path`, `_nested_in_commit`) and compares the lines
with paths — the same quoting defect (not `diff.relative`, which `ls-tree` does
not honor). Both are fixed here with `-z`. Every issue a command reads goes
through `_check_issue` (`issue`, `search`), so one check there covers
`tracker show`, `tracker list`, `inbox`, claim and sync.

## Goals

1. The merge-back hint and the three index/tree readers (`_nested_tree_path`,
   `_nested_in_commit`, `_tracked_source`) see real paths: `-z`, split on NUL,
   decoded with `surrogateescape` so a path that is not UTF-8 does not crash,
   and the `diff` run from the repository's top folder. *(Amended at review:
   `_tracked_source`'s `ls-files` was missed by the first sweep, and `-z`
   alone introduced a decoding crash.)*
2. A `create_issue` answer that is not a mapping, or names no string key and
   id, gives `create.py`'s "It may exist" warning.
3. When creation succeeds and binding fails, the filing hook's message gives a
   real reason, not the placeholder.
4. `_check_issue` also refuses, as "unexpected shape", an issue whose `key`,
   `fields.summary`, `status.name`, `statusCategory.key`,
   `assignee.accountId` or `assignee.displayName` is present and not a string.
5. Strict `drop` of an item whose `tracker.yaml` cannot be read says the binding
   cannot be read; a bound item keeps today's wording.

## Non-goals

- `_tracker_link`'s own printed error carries the `tracker create` verb in the
  filing path; unchanged (it is printed once, above the hook's line).
- Type-checking fields no command reads.

## Design

- (1) `cli.py`: `["git", "-C", <repository top>, "diff", "--cached",
  "--name-only", "-z"]`, `.split("\0")`. From the top, `diff.relative` makes
  paths relative to the top, which is what they are compared as — so no
  `--no-relative`, which needs git 2.28. `fs.py`: `ls-tree -r -z --name-only`,
  `.split("\0")` with empty entries dropped.
- (2) `JiraClient._payload(method, path, body)`: the decoded JSON as it came.
  `_json` becomes `_mapping(self._payload(...), path)`; `create_issue` returns
  `_payload`. `create.py` reads `key`/`id` only from a mapping and only as
  non-empty strings; anything else takes the existing "It may exist" branch,
  which prints the answer with `!r`.
- (3) `_create_one`: when `_tracker_link` returns non-zero and `reasons` is
  collecting, append "binding it failed; the reason is printed above".
- (4) `_check_issue`: a helper `_text(value, path)` — `None` or a `str`, else
  `_shape_error` — applied to the six values above.
- (5) `tcw/tracker/intake.py`: `binding_record(store, slug) -> str` answering
  `""` (never bound), `"bound"`, or `"unreadable"`; `ever_bound` becomes
  `binding_record(...) != ""`. Both drop refusals choose their wording from it:
  "{slug}'s tracker.yaml cannot be read, so whether it records a ticket is
  unknown, and dropping would erase it. Fix the file, or discard it instead: …".

## Abstraction litmus test

(1) is filesystem-adapter code reading git, which only a git-backed store does.
(2)–(4) are tracker-client code, not store operations. (5) reads the binding
through `store.read_sidecar`, which any store implements; "cannot be read" is an
answer any store can give.

## Acceptance criteria

1. With a staged, uncommitted `tracker.yaml` holding a `sync` record in a node
   whose folder name is `nöde`, a `complete` whose merge-back fails prints the
   "tracker.yaml holds a record" hint; the same with `diff.relative=true` and
   the node in a subfolder of the repository.
2. A fake tracker answering `create_issue` with `[]` makes `tcw work tracker
   create <slug>` fail with "It may exist; look for a ticket titled"; so does
   `{"key": null, "id": null}`.
3. With creation succeeding and the link step failing on filing, stderr does
   not contain "creating it did not succeed".
4. A fake issue `{"key": "A-1", "fields": {"status": {"name": 5}}}` makes
   `tcw work tracker show A-1` exit 1 with "unexpected shape", no traceback.
5. In strict mode, `tcw work drop <slug> --confirm` with a `tracker.yaml` that
   is not valid UTF-8 exits 1 saying the binding "cannot be read", and not "is,
   or was, bound"; the web drop gate says the same.
6. The full test suite passes.

## Risks

- A tracker that returns a numeric `key` would now be refused as a shape
  problem where it printed before. Jira documents keys as strings.
- The hint's staged list is now printed relative to the repository top
  rather than to the node; that is git's own default without `diff.relative`.
