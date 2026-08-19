# Spec — Validate capability Subject and Feature refs at write time

## Capability changes

No new capability, no removal. Two entries change wording; one is touched by the
sweep and does not change.

- **changed** — `capabilities/set-a-capabilitys-status` (`cap-03f1a5`, Status
  `Supported`, `Subject: [capability]`). Its `description.md` says `set` updates
  "any field in the locked vocabulary in place" with no statement about what a
  reference-bearing field may contain or what happens when it does not resolve.
  `set` becoming fail-closed on every ref field is a user-visible acceptance
  change and belongs in that body. Status stays `Supported`.
- **changed** — `web/editing` (`cap-d799b3`, Status `Supported`,
  `Feature: local-web-app`, `Subject: [work-item]`). Its body already promises
  "Every saved object is immediately checked with TCW's standard validation
  rules, with any findings shown as **post-save** warnings." For a capability's
  ref fields that stops being true: a bad ref is now refused **at** save with a
  422, not reported after it. Status stays `Supported`.
- **unchanged** — `capabilities/validate-capabilities` (`cap-eb9744`). `check`
  reports the same problems in the same words; only the population of refs that
  can reach it changes.

Both changed entries are already recorded in this item's `capabilities.yaml`
sidecar. No capability records are written by this stage.

## Reproduction

Verified at HEAD `aff0cbb` (`tcw 1.0.0`), in a throwaway git repo after
`tcw init --id repro`. All output below is real:

```
$ printf 'A thing.' | tcw taxonomy add "Thing"
Added term thing
$ printf 'A real feature.' | tcw taxonomy add "Real Feature" --kind feature --vocab thing
Added term real-feature
$ tcw capabilities add web/editing "Editing"
Added capability web/editing (cap-ceacc1)

--- dangling Subject + dangling Feature ---
$ tcw capabilities set web/editing --field Subject=no-such-term --field Feature=also-bogus
Set web/editing
exit=0
--- Feature pointing at a Vocabulary (wrong kind) ---
$ tcw capabilities set web/editing --field Feature=thing
Set web/editing
exit=0
--- the four other ref-bearing fields ---
$ tcw capabilities set web/editing --field "Superseded by=nope" --field "Blocked by=nope2" \
      --field Roles=roles/admin --field When=conditions/offline --field "Planning doc=no-such-item"
Set web/editing
exit=0

--- check ---
$ tcw capabilities check
web/editing: Superseded by → dangling identifier 'nope'
web/editing: Blocked by → dangling identifier 'nope2'
web/editing: Roles → dangling identifier 'roles/admin'
web/editing: When → dangling identifier 'conditions/offline'
web/editing: Subject → dangling ref 'no-such-term'
web/editing: Feature → ref 'thing' points to Vocabulary, expected Feature
6 problem(s).
exit=1
```

and the stored meta, showing every bad ref persisted:

```yaml
id: cap-ceacc1
name: Editing
Status: Missing
Subject:
- no-such-term
Feature: thing
Superseded by: nope
Blocked by: nope2
Roles: roles/admin
When: conditions/offline
Planning doc: no-such-item
```

**The defect is wider than the report.** The request names `Subject` and
`Feature`; the same `set` call accepts four more fields that `check` resolves
and rejects — `Superseded by`, `Blocked by`, `Roles`, `When`. Six fields, one
missing validation step, one call site. (`Planning doc` also went through
unvalidated, but `check` does not validate it either — see Sweep.)

Ambiguity is reachable only through federation, so it is grounded at the store
API rather than the shell — the renderer is the same either way:

```
$ python - <<'EOF'
from tcw.store.fs import FsCapabilitiesStore
from tcw.store.base import AmbiguousRef
class AmbigTax:
    def get(self, ref): raise AmbiguousRef(ref)
cap = FsCapabilitiesStore.open(Path("."))
print(cap._check_subject("web/editing", {"Subject": ["dup"]}, AmbigTax()))
print(cap._check_feature("web/editing", {"Feature": "dup"}, AmbigTax()))
print(cap.check())                      # taxonomy=None
EOF
["web/editing: Subject → ambiguous ref 'dup'"]
["web/editing: Feature → ambiguous ref 'dup'"]
[]                                      # Subject/Feature not checked at all
```

## Problem

**(a) The write path never resolves a ref.** `_validate_fields`
(`tcw/store/fs.py:1577-1589`) is the one validation step both capability write
paths share. It checks field *names* against `CAP_FIELDS` (`:1580`), `Status`
values against `CAP_STATUSES` (`:1584`), and normalizes `Subject` to a list
(`:1588`). Nothing in it consults any store. `set` calls it and then writes
(`:1644-1662`, the call at `:1645` carrying the comment "validate before
touching disk"); `update_capability` calls it first thing (`:1915-1917`) and
then writes. So both write surfaces are already funnelled through one function
— that function simply does not know about refs.

**(b) Resolution exists, but only in `check`.** `check`
(`:1716-1801`) resolves all six fields, in one block (`:1776-1782`):
`Superseded by` and `Blocked by` through `_ref_error` (`:1844-1850`), `Roles`
and `When` through `_check_globals` (`:1852-1864`), `Subject` through
`_check_subject` (`:1865-1877`), `Feature` through `_check_feature`
(`:1878-1891`, the only one that also checks kind). The first four resolve
against the capabilities store itself; the last two need a taxonomy store, and
`check` is *given* one as a parameter (`:1716`, abstract at
`tcw/store/base.py:405-406`).

**(c) `FsCapabilitiesStore` holds no taxonomy handle** — the reason this was
split out of the taxonomy item rather than folded into it. Every existing caller
composes the pair from the outside and independently:
`tcw/capabilities/cli.py:30-32` (`_taxonomy_for`), `tcw/validate.py:113-114`,
and `tcw/serve/__init__.py:396-402` (`_stores`, which builds a taxonomy store on
every request and hands it to nobody). Three copies of the same wiring, and none
of them is reachable from `_validate_fields`.

**(d) Both public write surfaces are affected, through the same two methods.**
`tcw capabilities set` → `_set` (`tcw/capabilities/cli.py:99-121`) → `set`.
`tcw serve` PATCH `/api/capabilities/<ref>` (`tcw/serve/__init__.py:1095-1125`)
→ `update_capability`. `tcw serve` POST `/api/capabilities`
(`:929-955`) calls `capabilities.add(...)` and then `capabilities.set(cap_path,
fields)` (`:940-942`), so it inherits `set`'s behavior.

**(e) `add` is not a ref write path.** `FsCapabilitiesStore.add`
(`:1538-1549`) takes only `identifier`, `name`, `status`, `body`; it writes
`{"id", "name", "Status"}` and never calls `_validate_fields`. No ref can reach
it, from the CLI (`tcw/capabilities/cli.py:86-96`) or from serve. Nothing to do
there — the same "vacuous" finding the taxonomy item recorded for `--relates`.

The cost is the reporter's: `set` exits 0, so a scripted ledger reconciliation
looks clean and the breakage surfaces only at the closing `check` — long after
the run that caused it.

## Goals

1. `tcw capabilities set` refuses a reference-bearing field whose value does not
   resolve, writes nothing, and exits non-zero, with the same dangling /
   ambiguous / wrong-kind distinction `check` already makes, in the same words.
2. The same refusal reaches `tcw serve` (PATCH and POST) as a 422 with the same
   message, through the same seam — not a second implementation.
3. A capabilities store obtains a taxonomy store at write time by a route a
   non-filesystem adapter can also honor, without changing any abstract store
   interface or any existing constructor signature.
4. `check` and the write path cannot disagree about *what* a problem is (one
   renderer) or about *whether* refs get checked at all (one source of the
   taxonomy handle).
5. Existing invalid data stays repairable: a write that does not supply a bad
   ref is not blocked by one already stored.

## Non-goals

- **Migrating or quarantining existing invalid data.** `check` already finds it.
  Checked as the request required: this repository's own `docs/capabilities/`
  is clean — `tcw capabilities check` at HEAD exits 0 with `capabilities OK` —
  so no repository data forces a migration. Goal 5 is what keeps repair possible.
- **Bare leaf-slug resolution for `Subject`/`Feature`.** The taxonomy item gave
  `--vocab` a leaf-slug fallback (`_resolve_vocab_ref`, `fs.py:1113-1133`) and
  scoped it deliberately as "an input convenience at the write boundary, not a
  stored identity". Extending it here is a separate widening: `_resolve_vocab_ref`
  hard-codes `expect_vocabulary=True`, which is wrong for `Subject` (this repo
  stores `Subject: capability/subject`, a Vocabulary, and `Feature:
  capability-feature-association`, a Feature), so nothing reuses cleanly. Both
  surfaces stay strict together, so no drift is introduced by leaving it out.
- **Validating `Planning doc`.** It is a capability→work pointer that *no*
  surface validates — `check` has no rule for it either (`:1716-1801`). Adding
  one is a new rule, not a write/check divergence. Sweep finding, separate item.
- **Validating a work item's `initiative` back-pointer.** Same shape: written
  unvalidated (`fs.py:3336-3337`, `:3475-3476`) and unchecked by `FsWorkStore.check`
  (`:2772-2812`). Sweep finding, separate item.
- **Ref validation inside `write_sidecar`** for a work item's `capabilities.yaml`
  (`fs.py:3615-3656`, which validates YAML shape only). Those refs are gated at
  `complete` by `capability_gate` (`tcw/work/recursion.py:34-65`); that gate is a
  deliberate different mechanism, not a missing call.
- **Changing the abstract `CapabilitiesStore` interface** (`base.py:351-437`).
  Per the litmus test the *composition* is an adapter detail; see Design §5.
- **Symlink containment.** Owned entirely by the sibling item
  `2026-07-30-resolve-taxonomy-refs-against-symlinks-not-just-lexically`; see
  Design §6.

## Design

### 1. The seam already exists: `_validate_fields`

Both write paths call it before anything touches disk — `set` at `fs.py:1645`,
`update_capability` at `:1917`. It is the only function both share, it already
raises `ValueError` for the other locked-vocabulary rules, and both call sites
already translate that into a refusal (`tcw/capabilities/cli.py:91-93` and
`:117-119` print to stderr and exit 1; `tcw/serve/__init__.py:950-952` and
`:1120-1122` route through `_map_store_error`, `:196-216`, which maps a
non-"no such" `ValueError` to **422**).

So no new plumbing is needed to reach either surface, and no CLI or serve file
needs to change. This is what makes the fix small: **teach `_validate_fields` to
resolve refs**, and both surfaces inherit it, exactly as fixing the store rather
than the CLI is what gave the taxonomy item its `POST /api/taxonomy` fix free.

### 2. One renderer, two callers — the taxonomy item's shape

`check`'s four ref blocks (`:1776-1782`) are the only place a ref problem is
worded today. Extract that block, unprefixed, into a private method:

```python
def _ref_problems(self, fields: dict, taxonomy) -> list[str]:
    """Every cross-object ref problem in `fields`, worded exactly as `check`
    reports it, minus the `<path>: ` location prefix."""
```

- `check` becomes `problems += [f"{where}: {p}" for p in self._ref_problems(f, taxonomy)]`,
  replacing seven lines with one. `_check_globals`, `_check_subject` and
  `_check_feature` lose their `where` parameter and return tails; the emitted
  strings are byte-identical to today's, which is what keeps every existing test
  assertion (`tests/test_capabilities.py:207-256`) passing unmodified.
- `_validate_fields` gains the raising wrapper — the same
  `_ref_problem` / `_require_ref` pairing the taxonomy store already uses
  (`fs.py:1083-1111`):

  ```python
  supplied = {k: v for k, v in out.items() if v is not None}
  if problems := self._ref_problems(supplied, self._taxonomy()):
      raise ValueError("; ".join(problems))
  ```

Three details are load-bearing:

- **`out`, not `fields`** — `Subject` must be resolved after `_as_list`
  normalization (`:1588`), so `Subject=a,b` is checked as two refs.
- **`v is not None`** — `None` is the documented clear sentinel (`:1582-1583`).
  Passing it through would make `_check_globals` stringify it (`f.get(field, "")`
  → `str(None).split(",")`, `:1855-1856`) and invent a problem about a field the
  caller just cleared.
- **All problems, joined with `; `** — not first-wins. `check` reports every
  problem; a write that reports one at a time costs a round trip per bad ref.
  None of the six messages contains the substring `no such`, so
  `_map_store_error` keeps them at 422 rather than 404.

### 3. Only the refs this write supplies

`_ref_problems` is called with the write's own fields, never with the merged
result. A `set --status Omitted` on a capability that already stores a dangling
`Subject` still succeeds.

This is not laziness, it is goal 5: `tcw work complete`'s reconciliation
instructions tell the user to run exactly that command
(`tcw/work/cli.py:1241-1248`), and validating the merged node would make a
capability with one bad ref unrepairable through the CLI that is supposed to
repair it. It is also what keeps "existing invalid data stays reportable by
`check`, migration out of scope" coherent rather than contradictory.

### 4. The composition seam: a private lazy accessor on the store

**Chosen: the capabilities store obtains its own taxonomy handle.**

```python
def _taxonomy(self) -> "FsTaxonomyStore | None":
    """The sibling taxonomy store for this node, or None if it has none.

    The FS adapter's answer to "where does this store's taxonomy live". Another
    adapter answers it from its own connection/config; the abstract interface
    is unchanged either way.
    """
    d = self.node_root / "docs" / "taxonomy"
    return FsTaxonomyStore.open(self.node_root) if d.is_dir() else None
```

`self.node_root` is already on every tree store (`FsTreeStore.__init__`,
`fs.py:789-792`), `FsTaxonomyStore` is defined above `FsCapabilitiesStore` in
the same module (`:893` vs `:1332`), and the expression is byte-for-byte the one
all three existing wiring sites already use
(`tcw/capabilities/cli.py:30-32`, `tcw/validate.py:113-114`,
`tcw/serve/__init__.py:396-402`). No constructor changes, no caller changes, no
new parameter anyone can forget to pass.

The three alternatives, and why they lose:

| Option | Verdict |
| --- | --- |
| **(a) handle obtained by the store** (chosen) | One place. Cannot be forgotten. `set`/`update_capability`/`check` all reach the same handle. Zero signature churn. |
| **(b) pass it through the write call**, as `check` does | Changes the abstract `set` and `update_capability` signatures (`base.py:387`, `:416`) plus two CLI and two serve call sites — and it is **opt-in**: a caller that omits it silently gets the bug back. That is precisely the failure this item exists to remove. Rejected. |
| **(c) a resolver callback** set at wiring time | An interface with one implementation, injected from three places that would all pass the same lambda. Speculative abstraction; the litmus test does not demand it. Rejected. |

`_taxonomy()` returning `None` when the node has no `docs/taxonomy/` is the
existing degradation, not a new one: `check` behaves that way today via
`_taxonomy_for` (`cli.py:30-32`), and a node with no taxonomy component has no
vocabulary to resolve against. `Superseded by` / `Blocked by` / `Roles` / `When`
need no taxonomy at all — they resolve against `self` — so they are validated
even on a taxonomy-less node.

**`check` gets the same handle as a fallback.** `check(taxonomy=None)` today
silently skips `Subject`/`Feature` entirely (reproduced above). Leaving that
alone would let the two surfaces disagree about *whether* a ref is checked even
after they agree about *what* the problem is. One line closes it:

```python
def check(self, taxonomy=None, identifier=None):
    taxonomy = taxonomy or self._taxonomy()
```

The parameter stays — it is on the abstract interface (`base.py:405-406`) and
the test suite uses it for injection (`StubTax`/`FeatureTax`/`AmbiguousFeatureTax`,
`tests/test_capabilities.py:207-256`). It becomes an *override*, not the only
source. With it in place, `_taxonomy_for` (`cli.py:30-32`, its only caller
`cli.py:227`) and the duplicate wiring in `tcw/validate.py:113-117` can both be
deleted: net fewer lines, and one place that decides where a taxonomy comes from.

Note this also means the write path and `check` are validated against *the same
object* in every federated shape the suite already covers: the tests that
compose them by hand pass exactly `FsTaxonomyStore.open(<the store's node>)` —
`tests/test_environment_hardness.py:470-476` (nested monorepo, `Subject:
root/user`), `:563-570` (sibling nodes, `Subject: parent/user`),
`tests/test_multiproject.py:45-54` (sibling subfolders, `Subject:
project-a/account`). `self._taxonomy()` reconstructs that same store.

### 5. Abstraction litmus test

Operations added or changed:

| Operation | Verdict |
| --- | --- |
| "reject a capability write whose refs do not resolve" | **Model.** It is the standing convention every other TCW write path already honors (`tcw work edit --blocks` → `add_blocker`, `base.py:1763-1772`; `taxonomy add --vocab` → `_require_ref`, `fs.py:1102-1111`). A Jira-backed adapter validates an issue link before saving the issue; that it does so over an API rather than a folder is immaterial. No abstract *method* is added: the behavior is a precondition of the existing `set` / `update_capability`. |
| "a capabilities store obtains the taxonomy store for its own project" | **Adapter private detail.** The FS answer is `node_root / "docs" / "taxonomy"`. A remote adapter answers from its own connection and project key. Nothing about the answer appears in `CapabilitiesStore` or `TaxonomyStore`, so no adapter is forced into a filesystem shape. The *requirement* — "a capabilities store must be able to reach its taxonomy at write time" — is abstract and satisfiable by any adapter that can already implement `check(taxonomy=…)`. |
| `_ref_problems` (one renderer for six fields) | **Adapter private detail.** A private method over the already-abstract `get()`/`get_by_id()`. |
| `check(taxonomy=None)` defaulting to the store's own taxonomy | **Model, no signature change.** The parameter keeps its abstract meaning ("validate against this taxonomy"); `None` changes from "skip" to "use mine", which any adapter can implement or decline (returning `None` from its own accessor reproduces today's behavior exactly). |

No store-interface method is added, removed, or re-typed. Clean.

### 6. Boundary with the in-flight symlink item

`2026-07-30-resolve-taxonomy-refs-against-symlinks-not-just-lexically` is being
implemented in the same batch. It adds `FsTreeStore._within_store` and applies it
at `FsTaxonomyStore.get_local` / `add` / `_local_slugs` / `_validation_resources`
and `FsCapabilitiesStore.get_local` / `add` / `_all_meta_dirs` /
`_validation_resources` (its plan's call-site walk).

**Function-level overlap: none.** This item touches `_validate_fields`, `set`,
`update_capability`, `check`'s ref block, `_check_globals`, `_check_subject`,
`_check_feature`, and adds `_taxonomy()` and `_ref_problems`. That item touches
`get_local`, `add`, `_local_slugs`, `_all_meta_dirs`, `_validation_resources` and
`FsTreeStore`. The two sets are disjoint; only the file is shared.

**They compose in the right direction.** Its guard makes `taxonomy.get()` return
`None` for a ref that escapes through a symlink; this item's write path then
refuses that ref as *dangling*, which is exactly the wording its own criterion 4
already asserts for `check`. Neither item needs to know about the other. If both
land, `tcw capabilities set <p> --field Subject=alpha/link/victim` is refused —
a bonus, not a requirement of either spec, and not an acceptance criterion here.

Ordering is free; whichever lands first, the other rebases cleanly.

### 7. Documentation

- `skills/tcw-capabilities/SKILL.md:44-47` says `check` verifies that `Feature`
  resolves to a taxonomy entry of kind `Feature`; say `set` does too, and that a
  ref that does not resolve is refused rather than stored. The quick-reference
  rows at `:106-107` are the other place a reader learns the flag.
- `README.md:519` and `:531` describe `check` as the thing that resolves
  `Subject:` pointers; add that `set` now refuses an unresolvable one.
- `docs/changelogs/upcoming.md` and `docs/release-notes/upcoming.md` per the
  Documentation Sync section of `CLAUDE.md` — the release note must call out the
  behavior change (a script that set fields loosely and checked at the end now
  stops at the first bad ref) and that it covers six fields, not two.
- `docs/capabilities/capabilities/set-a-capabilitys-status/description.md` and
  `docs/capabilities/web/editing/description.md` per Capability changes.

### 8. Sweep

Repo-wide, for the criterion *a CLI/API write path that accepts a cross-object
reference, exits 0, and leaves `check` to report it*:

- **`tcw capabilities set` / `PATCH /api/capabilities/<ref>` / `POST
  /api/capabilities` with `fields`** — the defect, on **six** fields, not the two
  reported. Fixed here.
- **`FsCapabilitiesStore.add`** (`:1538-1549`) — accepts no ref-bearing field;
  vacuous, nothing to do (Problem (e)).
- **`tcw taxonomy add --vocab` and `update_term`** — already fail closed via
  `_require_ref` (`:1102-1111`), from the completed precedent item.
- **`tcw work new --parent` / `edit --parent`** — validated before any write
  (`create_work`, `fs.py:3293-3296`; `update_work`, `:3442-3445`).
- **`tcw work edit --blocks/--blocked-by`** — validated (`add_blocker`,
  `base.py:1763-1772`; `create_work`/`update_work` resolve every blocker
  entry before applying). No defect; this is the convention.
- **`tcw taxonomy extends` / `tcw capabilities extends`** — `extends_add`
  (`:1664-1681` and the taxonomy twin) resolves the project through
  `FsProjectRegistry` and refuses an unregistered or component-less target. No
  defect.
- **A capability's `overrides:` meta key** — never caller-supplied: `overrides`
  is not in `CAP_FIELDS` (`base.py:312-315`) so `_validate_fields` rejects it,
  and `_write_target` (`:1597-1628`) derives it from an already-resolved
  capability. `check` validates it via `_override_problem` (`:1827-1842`). No
  defect.
- **Two genuine siblings, both *out of scope because nothing checks them
  either*** — these are missing rules, not write/check divergences:
    - **`Planning doc`** on a capability (`--field "Planning doc=…"`). Written
      unvalidated; `check` has no rule; only `_shipped_but_missing`
      (`tcw/capabilities/cli.py:191-208`) reads it, tolerating a miss. Reproduced
      above.
    - **`initiative`** on a work item (`tcw work new/edit --initiative`, and the
      inbox `initiative` metadata key). Written unvalidated (`fs.py:3336-3337`,
      `:3475-3476`); `FsWorkStore.check` (`:2772-2812`) has no rule. It *is*
      resolved later, at `start` (`:2107-2110`).

      Recommend one follow-up item covering both: add the `check` rule first,
      then the write-time refusal, in that order.
- **A work item's `capabilities.yaml` sidecar** — `write_sidecar`
  (`fs.py:3615-3656`) validates YAML shape only, and a dangling capability path
  is caught at `complete` by `capability_gate` (`tcw/work/recursion.py:34-65`).
  Deliberately a different mechanism (a gate on the transition, not on the file),
  and the sidecar is legitimately edited before its targets exist. No change.

## Acceptance criteria

Criteria 1-8 are checkable in a throwaway git repo after `tcw init --id repro`,
`printf 'A thing.' | tcw taxonomy add "Thing"`, `printf 'x' | tcw taxonomy add
"Real Feature" --kind feature --vocab thing`, `tcw capabilities add web/editing`.

1. `tcw capabilities set web/editing --field Subject=no-such-term` exits
   non-zero, prints a message containing `Subject → dangling ref
   'no-such-term'`, and `docs/capabilities/web/editing/meta.yaml` is
   byte-identical to before the call.
2. `tcw capabilities set web/editing --field Feature=also-bogus` exits non-zero
   with `Feature → dangling ref 'also-bogus'`, and nothing is written.
3. `tcw capabilities set web/editing --field Feature=thing` (a ref that resolves
   to a **Vocabulary**) exits non-zero with `Feature → ref 'thing' points to
   Vocabulary, expected Feature`, and nothing is written.
4. Each of `--field "Superseded by=nope"`, `--field "Blocked by=nope2"`,
   `--field Roles=roles/admin`, `--field When=conditions/offline` is refused on
   its own, each naming its own field, and writes nothing.
5. `tcw capabilities set web/editing --field Subject=no-such-term --field
   Feature=also-bogus` reports **both** problems in one message (not just the
   first) and writes nothing.
6. `tcw capabilities set web/editing --field Subject=thing --field
   Feature=real-feature` exits 0, and `tcw capabilities check` immediately after
   exits 0.
7. For every refusal above, the message text after the command prefix is
   **byte-identical** to what `tcw capabilities check` prints for the same bad
   value minus its leading `web/editing: ` — verified by writing the bad value
   directly into `meta.yaml`, running `check`, and diffing the two strings.
8. Against a running `tcw serve`: `PATCH /api/capabilities/web%2Fediting` with
   `{"fields": {"Subject": ["no-such-term"]}}` returns **422** (not 200, not
   500) with the same message, and `meta.yaml` is unchanged; `POST
   /api/capabilities` with a `fields` object carrying a dangling `Feature`
   returns 422. No file in `tcw/serve/` is modified to achieve either.
9. A capability that already stores a dangling `Subject` (written directly into
   `meta.yaml`) still accepts `tcw capabilities set <path> --status Omitted`,
   exit 0 — the repair route `tcw work complete` recommends
   (`tcw/work/cli.py:1241-1248`) still works.
10. On a node with `docs/taxonomy/` absent, `tcw capabilities set <path> --field
    Subject=anything` still exits 0 (nothing to resolve against), while
    `--field "Blocked by=nope"` is still refused.
11. `FsCapabilitiesStore.check()` called with **no** `taxonomy` argument, on a
    node whose `docs/taxonomy/` exists and does not contain the ref, reports
    `Subject → dangling ref …` — the behavior reproduced as `[]` above.
    Passing an explicit `taxonomy=` still overrides it (the suite's `StubTax`
    tests, `tests/test_capabilities.py:207-256`, pass **unmodified**).
12. The write path adds no second copy of any wording. Run against
    `tcw/store/fs.py` before and after; every count is unchanged:
    `grep -c "dangling ref '"` → 2 (one for `Subject`, one for `Feature`),
    `"ambiguous ref '"` → 2, `"expected Feature"` → 1,
    `"dangling identifier '"` → 1, `"ambiguous identifier '"` → 1. And
    `_validate_fields` reaches all of them through `_ref_problems`, the same
    method `check` calls — verified by reading, since a count alone cannot show
    it.
13. `python -m pytest -q` is green. The one expected casualty is
    `tests/test_environment_hardness.py:373-380`
    (`test_capability_check_dangling_subject`), which builds its fixture by
    calling `caps.set(..., {"Subject": "ghost"})` — a call this change makes
    impossible; it must construct the invalid node directly (the `write_cap`
    helper in `tests/test_capabilities.py`) rather than be deleted, since the
    `check` assertion it makes is still the behavior we want.
14. `tcw capabilities check` on this repo's own `docs/capabilities/` still exits
    0 with `capabilities OK`, and `tcw validate` is clean.
15. `skills/tcw-capabilities/SKILL.md`, `README.md`,
    `docs/changelogs/upcoming.md`, `docs/release-notes/upcoming.md`, and the two
    capability `description.md` bodies are updated per Design §7.

## Risks

- **A previously "successful" reconciliation script now fails.** Intended and
  user-visible: anything that piped a batch of `set` calls and only checked at
  the end will now stop at the first bad ref. The blast radius is wider than the
  request implies — six fields, not two, so `Roles=`/`When=` writers are affected
  too. Mitigation: the error names every bad ref in one message (Design §2), and
  the release note calls it out as a behavior change.
- **Ordering becomes load-bearing.** A `Feature` must exist in the taxonomy
  before the capability that names it, and a `roles/…` capability before the
  capability that lists it. `tcw capabilities init` scaffolds taxonomy first
  already, but nothing enforced it. Mitigation: the SKILL.md sentence in §7.
- **`check(taxonomy=None)` changing meaning could surprise an embedder.** It goes
  from "skip Subject/Feature" to "use my own taxonomy". A caller who genuinely
  wanted the skip must now pass a stub — no in-repo caller does
  (`tcw/capabilities/cli.py:227`, `tcw/validate.py:113-117` both pass a real
  store or `None` on a taxonomy-less node). Low, and it is the change that makes
  goal 4 true rather than half-true.
- **The write path is not injectable.** The suite injects `StubTax` into `check`;
  it cannot inject into `set`, which calls `self._taxonomy()`. New write-path
  tests must build a real taxonomy tree. That is a better test anyway, and
  `_taxonomy()` being a method leaves monkeypatching available if a case needs
  it. Accepted; do **not** add a constructor parameter for testability alone.
- **`_ref_problems` extraction changes `check`'s strings if done carelessly.**
  Every wording is asserted by tests (`tests/test_capabilities.py:207-256`,
  `tests/test_capabilities_federation.py:156-200`) and quoted in this spec's
  Reproduction. The extraction must be pure motion: the suite passes with no test
  edited except the one named in criterion 13.
- **Opening a taxonomy store per write costs something.** `FsTaxonomyStore.open`
  reads `config.yaml` and builds nested `extends` stores. One per `set` call, so
  it is noise next to the git staging the same call performs; if a deeply
  federated tree makes it measurable, memoize on the instance — but do not
  pre-emptively.
- **Merge friction with the symlink item.** Both edit `FsCapabilitiesStore` in
  `tcw/store/fs.py`. Disjoint functions (Design §6), so a textual conflict is the
  worst case, not a semantic one.

## Notes

- The request's framing that this is "the last one that does not [fail closed]"
  is nearly right and worth correcting: after this item, the last *divergences*
  between a write path and `check` are closed, but two fields — a capability's
  `Planning doc` and a work item's `initiative` — are unvalidated **everywhere**.
  Sweep §8 records them; they need a `check` rule before a write-time refusal
  would mean anything.
- The request scoped the fix to `Subject` and `Feature`. The reproduction shows
  four more fields going through the identical unvalidated call. They are folded
  in rather than left for a later `check` to find, on the precedent's reasoning:
  same call site, same helper, and splitting them would put two agents in
  `_validate_fields` for one behavior. This is a scope widening from the request
  and is stated as such.
- Scratch reproduction repo from this stage:
  `/private/tmp/claude-501/-Users-brian-Projects-TCW/984ed1dd-bc79-402a-bc4e-6b908f84283d/scratchpad/repro`.
  Disposable — rebuild from the Reproduction section rather than assuming it
  survives.
