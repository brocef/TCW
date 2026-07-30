# Plan — Validate taxonomy `--vocab` refs at write time and define bare-slug resolution

Six tasks. The spec settled every design question; this orders them so the suite
is green at each commit boundary and the riskiest change lands after the shared
helper exists.

Ordering rationale: task 1 (bounding) is independent of the rest and closes the
traversal hole first — it is the highest-severity item here and should not wait
behind refactoring. Task 2 extracts the helper with **no behavior change**, so it
is separately revertable and its diff is reviewable as pure motion. Task 3 adds
the leaf-slug scan to the helper. Task 4 wires `add` to it — the actual reported
fix — which is last among code tasks because it depends on 2 and 3. Docs close.

## Task 1 — bound taxonomy refs to the store root

**Changes:** `tcw/store/fs.py`, `get_local` (`:767-768`).

Route the ref through `_safe_store_id` (`:553-566`) before joining it onto
`self.root`. A rejected ref returns **`None`**, not a raise.

`None` is load-bearing, not a shortcut: `get()` is documented to return `None`
for a ref resolving to nothing (`tcw/store/base.py:169-173`), and `check()`
catches only `AmbiguousRef` (`fs.py:911-915`) — raising here would crash `check`
on any taxonomy that already contains such a ref, turning a reportable problem
into a traceback. With `None`, `check` reports it dangling, `show`/`rm` say "no
such term", and `add` refuses it, with no new exception for any caller to learn.

This closes a read **and delete** escape: `remove()` → `self._rm(self.root /
term.slug)` (`:833-841`) deletes outside `docs/taxonomy/`, and `tcw serve`
reaches the resolver with request input (`tcw/serve/__init__.py:1038`).

**Verified by:** criterion 7 — `tcw taxonomy show ../capabilities` exits non-zero;
`tcw taxonomy rm ../capabilities/<x>` exits non-zero and deletes nothing outside
`docs/taxonomy/`; a `..` ref written directly into a `meta.yaml` is reported
dangling by `check` rather than crashing it. Add a regression test for the `rm`
case specifically — a deletion escape that regresses silently is the worst
failure mode here.

## Task 2 — extract the ref-problem helper (no behavior change)

**Changes:** `tcw/store/fs.py` — new private `FsTaxonomyStore` method; `check()`
(`:916-929`) and `update_term()` (`:1042-1056`) call it.

Returns the resolved `Term` (or `None`) plus a problem string (or `None`),
covering the three distinctions both callers already encode: dangling, ambiguous,
wrong-kind. `FsCapabilitiesStore._ref_error(identifier) -> str | None`
(`:1607-1613`) is the naming and shape precedent.

The two callers differ only in output: `check` appends the string,
`update_term` raises `ValueError`. Keep that difference at the call sites.

> **Correction (implement).** They differ in wording too, and both wordings are
> test-asserted, so the helper returns a **code** (`"dangling"` / `"ambiguous"`
> / `"kind"`) rather than a message; each caller renders it. Only the wrong-kind
> sentence is identical in both, and it is the one thing shared verbatim
> (`_wrong_kind_ref`). See the matching correction in `spec.md` Design §1.

**Message strings must be preserved verbatim** — they are asserted by tests and
quoted in the spec (spec Risks, last bullet). This task is pure motion: the
suite must pass with **no test modified**. If a test needs editing, the
extraction changed behavior and is wrong.

**Verified by:** `python -m pytest tests/test_taxonomy.py -q` green, unmodified.

## Task 3 — leaf-slug fallback inside the helper

**Changes:** same helper.

When a ref does not resolve, scan `_local_slugs()` (`:770-772`) for entries whose
**last segment** equals the ref:

- exactly one match → resolve to it and report the full path back to the caller,
  so `add` can store the path rather than the bare slug;
- more than one → an *ambiguous* problem naming **both** candidate paths;
- none → the existing "does not resolve" problem, unchanged.

**Local terms only.** An inherited tree's leaves stay addressable by
`alias/path`, matching `get_inherited` (`:800-802`), which is path-addressed
against the source store.

**Do not touch `get()`.** The spec's Design §2 table lists nine callers that
would widen, two of them changing meaning rather than merely widening
(federated-repo resolution order, and a new `AmbiguousRef` raise site inside
`get()` that `tcw taxonomy add` does not catch — `tcw/taxonomy/cli.py:80` catches
`ValueError` only, so it would be a traceback). The fallback lives in the helper,
on the write path.

**Verified by:** criteria 2 and 3; and criterion 10 — the existing federation
tests (`tests/test_taxonomy.py:129-166`) pass **unchanged**, which is the proof
`get()`'s semantics did not move.

## Task 4 — `add` fails closed

**Changes:** `tcw/store/fs.py`, `FsTaxonomyStore.add()` (`:811-831`); possibly
`tcw/taxonomy/cli.py` error rendering.

> **Correction (implement).** No CLI change was needed — `_add`
> (`tcw/taxonomy/cli.py:80`) already catches `ValueError` and prints
> `tcw taxonomy add: <message>` to stderr with exit 1. Unlisted fallout instead:
> four tests built a deliberately invalid Feature *through* `add`, which this
> task makes unbuildable, so they had to construct the node another way.

Between the kind check (`:820-823`) and the write (`:830`), validate every
`--vocab` ref through the helper. On any problem: raise `ValueError` with a
message naming the ref (and, for an ambiguous leaf slug, both candidates), and
**write nothing** — no folder, no `meta.yaml`, no `description.md`. Confirm the
failure path leaves no partial directory behind; `add` creates directories, so
validate before the first `mkdir`, not after.

Also enforce the two rules `add` skips today and `check` applies:

- a Feature must carry at least one vocabulary ref (`:917-918`);
- a vocabulary ref must point at a `Vocabulary`, not a `Feature` (`:927-929`).

Store the **resolved path** for a ref that only matched by leaf slug. A ref that
already resolved is stored **verbatim** — no qualification is added (criterion 6;
`--vocab Argument` through an `extends` alias keeps storing `Argument`).

Fixing this in the store, not the CLI, is what makes `POST /api/taxonomy`
(`tcw/serve/__init__.py:854-886`) inherit the fix — criterion 8.

**Verified by:** criteria 1, 2, 4, 5, 6, 8.

## Task 5 — capabilities axis

**REQUIRED SUB-SKILL: use `tcw-capabilities`.** Both entries are `changed:` in
this item's `capabilities.yaml` sidecar; neither changes Status.

- `taxonomy/add-a-term` — body states what a `--vocab` ref may be (a path, an
  `alias/path`, or a tree-wide-unique leaf slug stored as its path) and that
  `add` now refuses one that does not resolve.
- `taxonomy/remove-a-local-term` — body says `rm <path>` deletes "a local term";
  task 1 makes that true, since today the path is not bounded to the store.

## Task 6 — documentation sync

One pass over the finished diff, per `stage-implement.md` step 6. Predicted from
spec §7:

| Entry | Trigger | Expected |
| --- | --- | --- |
| `docs/changelogs/upcoming.md` | `Any-Code-Change` | **fires** — `Fixed`: write-time `--vocab` validation; leaf-slug resolution at the write boundary; refs bounded to the store root (read **and** `rm` escape closed); helper extracted to one place. |
| `docs/release-notes/upcoming.md` | `Public-API` | **fires** — behavior change, called out as such: a bootstrap script that piped many `add` calls and only checked at the end will now stop at the first bad ref. Also that `--vocab` accepts a unique leaf slug. |
| `README.md` | `Public-API` | **fires** — `README.md:396-397` says `check` validates these refs; say `add` does too. |
| `skills/tcw-taxonomy/SKILL.md` | `Skill-Driven-Component` | **fires** — `:46` and the quick-reference row at `:79` say `--vocab <term>`/`<ref>` with no form given. State the accepted forms and the new refusal. |
| `skills/tcw-taxonomy/references/init.md` | `Skill-Driven-Component` | **fires** — `:48-51` already emits vocabulary before features; make that ordering a **requirement**, because a bootstrap that adds features first will now fail. |

## Verification

Beyond the suite, run in a throwaway repo under
`/private/tmp/claude-501/-Users-brian-Projects-TCW/aed28ea1-65fe-4658-9f64-7aa452b6b335/scratchpad`
— **never inside `/Users/brian/Projects/TCW`**, since task 1's fixtures involve
`rm` with `..` refs and a mistake there deletes real repo folders. Paste actual
output into `outcome.md`:

1. The spec's Problem-section reproduction, re-run: all five `add` cases that
   exited 0 at HEAD now behave per criteria 1-5.
2. The traversal reproduction, re-run: `show ../capabilities` and
   `rm ../capabilities/thing/do-it` both refuse, and `docs/capabilities/thing/`
   **still exists** afterwards. Capture `ls docs/capabilities/` before and after.
3. Criterion 8 against a running `tcw serve` — a `POST /api/taxonomy` with an
   unresolvable `vocabulary` entry returns 4xx and creates no folder.
4. Criterion 12: `tcw taxonomy check` on **this** repo still exits 0. Note the
   spec's caveat that this is weak evidence on its own (every stored ref here
   points at a root-level term), so criteria 1-8 in the throwaway repo carry the
   weight.

Criterion 9 is a source read: the three-way validation must exist once.

Full `python -m pytest -q` green before `submit`.

## Notes

**Follow-up item to create, not fix here:** `tcw capabilities set --field
Subject=… --field Feature=…` has the identical write-time gap —
`_validate_fields` (`fs.py:1340-1352`) checks field *names* and `Status` values
but never resolves refs, so a dangling ref is accepted and only `check` finds it.
Out of scope because the fix is structurally different: `FsCapabilitiesStore`
holds no taxonomy handle (`check(taxonomy=None)` receives one as a parameter,
`fs.py:1479`), so fixing it means deciding how a capabilities store obtains a
taxonomy store at write time — a store-composition design question, not a missing
call. File it via `tcw work new` before this item completes.

**Task 1 is a security fix riding in a QoL item.** If the batch it belongs to
slips, task 1 is the piece worth landing on its own.

**GitHub issue #10 is not closed at completion** — deferred until the containing
minor version is cut and pushed, per the user's 2026-07-30 decision.

The spec corrects three claims in `initial-request.md`'s Notes; most consequential
is that `relatesTo` write-time validation is **vacuous** — `add` has no
`--relates` flag and hard-codes `relatesTo: []`, so point 4 of the request
resolves to "nothing to do".
