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

Verified at `aff0cbb` (`tcw 1.0.0`), in a throwaway git repo after `tcw init
--id repro`. Still current at HEAD `1d74cb1`: `git diff --name-only aff0cbb HEAD`
touches only `docs/work/`, so no cited line in `tcw/` or `tests/` has moved. All
output below is real:

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

**The web surface has it too**, against `tcw serve` on the same repo — and the
same pair of calls shows the 422 plumbing already works, so PATCH inherits the
fix with no serve change:

```
$ curl -s -o /dev/null -w '%{http_code}\n' -X PATCH -H 'Content-Type: application/json' \
    -d '{"fields":{"NotAField":"x"}}' http://127.0.0.1:8791/api/capabilities/web%2Fediting
422
   {"error": "unknown field 'NotAField' (not in the locked vocabulary)"}

$ curl -s -o /dev/null -w '%{http_code}\n' -X PATCH -H 'Content-Type: application/json' \
    -d '{"fields":{"Subject":["no-such-term"]}}' http://127.0.0.1:8791/api/capabilities/web%2Fediting
200
   … "Subject": ["no-such-term"] …           # accepted and persisted
```

A `ValueError` out of `_validate_fields` is *already* rendered as 422 with its
message verbatim; a dangling ref is simply never raised.

**POST is not atomic — a defect that exists today, before this change.** The
handler creates the capability and only then applies the fields, so a rejected
field returns 422 with the capability already written. Reproduced at HEAD with
an *unknown field*, which `_validate_fields` already refuses:

```
$ curl -s -o /dev/null -w 'http=%{http_code}\n' -X POST -H 'Content-Type: application/json' \
    -d '{"path":"partial/victim","name":"Victim","fields":{"NotAField":"x"}}' \
    http://127.0.0.1:8792/api/capabilities
http=422
   {"error": "unknown field 'NotAField' (not in the locked vocabulary)"}

$ cat docs/capabilities/partial/victim/meta.yaml
id: cap-3793eb
name: Victim
Status: Missing                  # created anyway, and staged
```

This change does not cause that; it widens the set of inputs that trigger it.
Design §5 fixes it.

Ambiguity is reachable only through federation, so it is grounded at the store
API rather than the shell — the renderer is the same either way:

```
$ python - <<'EOF'
from pathlib import Path
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
(`:1644-1660`, the call at `:1645` carrying the comment "validate before
touching disk"); `update_capability` calls it first thing (`:1915-1917`) and
then writes. So both write surfaces are already funnelled through one function
— that function simply does not know about refs.

**(b) Resolution exists, but only in `check`.** `check`
(`:1716-1801`) resolves all six fields, in one block (`:1776-1782`):
`Superseded by` and `Blocked by` through `_ref_error` (`:1844-1850`), `Roles`
and `When` through `_check_globals` (`:1852-1863`), `Subject` through
`_check_subject` (`:1865-1876`), `Feature` through `_check_feature`
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
fields)` (`:940-942`), so it inherits `set`'s behavior — but as **two** writes,
which is (f).

**(e) `add` accepts no ref today.** `FsCapabilitiesStore.add`
(`:1538-1549`) takes only `identifier`, `name`, `status`, `body`; it writes
`{"id", "name", "Status"}` and never calls `_validate_fields`. No ref can reach
it from the CLI (`tcw/capabilities/cli.py:86-96`, no `--field` flag), so there is
no *missing* validation there. It is nonetheless where the fix for (f) lands.

**(f) `POST /api/capabilities` is not atomic — pre-existing.** `add` writes and
stages before the handler applies any field (`:940-942`), and nothing rolls it
back when `set` refuses. Reproduced above at HEAD with an unknown field: 422
returned, capability created. This item does not introduce the defect, but it
widens what triggers it — every unresolvable ref joins "unknown field" and "bad
Status" — so goal 2's "writes nothing" would otherwise be false on POST.

The cost is the reporter's: `set` exits 0, so a scripted ledger reconciliation
looks clean and the breakage surfaces only at the closing `check` — long after
the run that caused it.

## Goals

1. `tcw capabilities set` refuses a reference-bearing field whose value does not
   resolve, writes nothing, and exits non-zero, with the same dangling /
   ambiguous / wrong-kind distinction `check` already makes, in the same words.
   For `Subject`/`Feature` this is conditional on the node **having** a taxonomy
   component: with no `docs/taxonomy/` there is nothing to resolve against and
   they pass unvalidated, exactly as `check` treats them today (criterion 10).
   The other four fields resolve against the capabilities store itself and are
   validated unconditionally.
2. The same refusal reaches `tcw serve` (PATCH and POST) as a 422 with the same
   message, through the same seam — not a second implementation — and a refused
   POST leaves **no** capability behind.
3. A capabilities store obtains a taxonomy store at write time by a route a
   non-filesystem adapter can also honor, adding no abstract store method and
   changing no constructor signature. (Goal 2's atomic POST does add one
   optional keyword to the existing abstract `add` — Design §5.)
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
  (`:2772-2813`). Sweep finding, separate item.
- **Ref validation inside `write_sidecar`** for a work item's `capabilities.yaml`
  (`fs.py:3615-3656`, which validates YAML shape only). Those refs are gated at
  `complete` by `capability_gate` (`tcw/work/recursion.py:25-65`); that gate is a
  deliberate different mechanism, not a missing call.
- **Adding any abstract `CapabilitiesStore` method** (`base.py:351-435`). The
  taxonomy *composition* is an adapter private detail, not an interface
  operation, and the ref renderer is private. The one interface change this item
  does make is an optional `fields=None` keyword on the existing `add`
  (`base.py:370-372`), required by Design §5 and backwards-compatible; both are
  judged in the Abstraction litmus test section.
- **Symlink containment.** Owned entirely by the sibling item
  `2026-07-30-resolve-taxonomy-refs-against-symlinks-not-just-lexically`; see
  Design §6.

## Design

### 1. The seam already exists: `_validate_fields`

Both write paths call it before anything touches disk — `set` at `fs.py:1645`,
`update_capability` at `:1917`. It is the only function both share, it already
raises `ValueError` for the other locked-vocabulary rules, and every call site
already translates that into a refusal (`tcw/capabilities/cli.py:115-119` prints
to stderr and exits 1; `tcw/serve/__init__.py:950-952` and `:1120-1122` route
through `_map_store_error`, `:196-216`, which maps a non-"no such" `ValueError`
to **422**).

So no new plumbing is needed to reach either surface. This is what makes the fix
small: **teach `_validate_fields` to resolve refs**, and `set`,
`update_capability`, the CLI and serve PATCH all inherit it — the same reason
fixing the store rather than the CLI gave the taxonomy item its `POST
/api/taxonomy` fix free.

`POST /api/capabilities` is the one surface this does *not* fully cover, because
it is not one write. Design §5 handles it, and that is the only file outside
`tcw/store/fs.py` this item changes.

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
`fs.py:789-792`) and `FsTaxonomyStore` is defined above `FsCapabilitiesStore` in
the same module (`:893` vs `:1332`). No constructor changes, no caller changes,
no new parameter anyone can forget to pass.

The accessor consolidates three sites that answer the same question three
different ways today — the wording matters, because they are not identical:

| Site | Today |
| --- | --- |
| `tcw/capabilities/cli.py:30-32` | one-line conditional on `docs/taxonomy` existing |
| `tcw/validate.py:113-114` | the same conditional, spelled over two lines |
| `tcw/serve/__init__.py:396-402` | opens the taxonomy store **unconditionally** — no existence test at all |

So this is a behavioral unification, not just a de-duplication: serve's variant
would hand a capabilities store a taxonomy rooted at a directory that may not
exist. `_taxonomy()` adopts the conditional form the two validating callers use,
because `None` is what `_check_subject`/`_check_feature` already treat as
"nothing to resolve against" (`fs.py:1867`, `:1880`).

The divergence is real and demonstrable, on a node with `docs/capabilities/` and
no `docs/taxonomy/`:

```
$ python -c "…; c.set('x', {'Subject':'ghost'}); print(c.check()); print(c.check(taxonomy=t))"
[]                                       # taxonomy=None — cli.py / validate.py
["x: Subject → dangling ref 'ghost'"]    # taxonomy=<unconditionally opened> — serve
```

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
    taxonomy = taxonomy if taxonomy is not None else self._taxonomy()
```

**`is not None`, not `or`** — this is load-bearing, not style. `taxonomy or
self._taxonomy()` silently discards a falsey injected store, which would
contradict criterion 11's "an explicit taxonomy still overrides". Any adapter
whose store defines `__bool__`/`__len__` (an empty one) hits it, and so does a
deliberately minimal test double.

The parameter stays — it is on the abstract interface (`base.py:405-406`) and
the test suite uses it for injection (`StubTax`/`FeatureTax`/`AmbiguousFeatureTax`,
defined `tests/test_capabilities.py:45-63` and `:92-96`, passed at `:210`,
`:222`, `:235`, `:242`, `:248`, `:255`). It becomes an *override*, not the only
source. With it in place, `_taxonomy_for` (`cli.py:30-32`, its only caller
`cli.py:227`) and the duplicate wiring in `tcw/validate.py:113-117` can both be
deleted: net fewer lines, and one place that decides where a taxonomy comes from.

**The equivalence claim, stated precisely.** `self._taxonomy()` is an equivalent
freshly opened filesystem store **for the normal same-node wiring** — which is
every production caller and every real-federation fixture in the suite.
`FsTaxonomyStore.__init__` (`fs.py:902-910`) rebuilds the `extends` graph from
the node's taxonomy `config.yaml`, so nested and sibling federation reconstruct
faithfully: `tests/test_environment_hardness.py:470-476` (nested monorepo,
`Subject: root/user`), `:563-570` (sibling nodes, `Subject: parent/user`),
`tests/test_multiproject.py:45-54` (sibling subfolders, `Subject:
project-a/account`) all pass exactly `FsTaxonomyStore.open(<the store's node>)`.

It is **not** equivalent for a caller that injects a *different* taxonomy. The
abstract signature (`base.py:405`) explicitly permits one — including a store
from another node — and the write path cannot see it. So `set()` followed by
`check(taxonomy=SomethingElse())` can validate against two different
taxonomies. That is inherent to putting the handle on the store rather than in
the call (option (a) over option (b)) and is accepted: the injecting caller is
choosing a non-default resolver for a *read*, and no production caller does it.
The narrow guarantee this item makes is between the two **write** surfaces and
the **default** `check`, which is what goal 4 asks for.

### 5. `POST /api/capabilities` must become one write

`add` writes and stages the capability (`fs.py:1538-1549`); only *then* does the
handler call `set` with the fields (`tcw/serve/__init__.py:940-942`). A field
rejection therefore returns 422 **with the capability already on disk**. This is
a **pre-existing defect**, not one this change introduces — reproduced above at
HEAD with an unknown field. What the change does is widen the trigger set from
"unknown field / bad Status" to "any unresolvable ref", which makes fixing it
this item's business: goal 2 says a refused write leaves nothing behind, and
"nothing" has to mean nothing.

**Chosen: `add` accepts the fields, so there is one write.**

```python
def add(self, identifier, name=None, status="Missing", body="", fields=None):
    norm = self._validate_fields(fields or {})     # raises before any mkdir
    ...
    meta = {"id": _mint_cap_id(), "name": display, "Status": status}
    meta.update({k: v for k, v in norm.items() if v is not None})
    self._write_node(d, meta, body)
```

and the handler loses two lines:

```python
capabilities.add(cap_path, name=name, status=status, body=body_text, fields=fields)
```

Field values win over the `status` parameter, which is precisely what
add-then-`set` does today, so the happy path is byte-identical — guarded by the
existing `tests/test_serve_write.py:842-851` (`test_create_with_fields`). A
`None` clear-sentinel is skipped rather than written: on a node being created
there is nothing to clear, and `_merge_meta` pops the key today
(`fs.py:1630-1642`), so the resulting `meta.yaml` matches.

The alternatives, and why they lose:

| Option | Verdict |
| --- | --- |
| **validate before `add`** via a new public `validate_fields` on the store | Still **two** writes, so it fixes only the ref case and leaves the same partial write for anything `set` can still refuse. And it puts a new method on the *abstract* `CapabilitiesStore` that every adapter must implement — a larger interface change than one optional keyword — while being **opt-in** from the handler, the same drift shape rejected in §4. |
| **roll back the `add` on failure** in the handler | A compensating delete that can itself fail, after `git add` already staged the folder. Adds a failure mode to fix a failure mode. |
| **`add(..., fields=…)`** (chosen) | One write, one validation, no rollback, no new method. Kills the whole class — unknown field, bad Status, bad ref alike. |

Litmus: an optional `fields` on `add` is *more* natural for a non-filesystem
adapter than create-then-update — a tracker creates an issue with its fields in
one API call, and today's shape forces two. The abstract signature
(`base.py:370-372`) gains one optional keyword; no existing caller changes.

This is the **only** file outside `tcw/store/fs.py` this item touches, and the
serve diff is a net deletion.

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
      `:3475-3476`); `FsWorkStore.check` (`:2772-2813`) has no rule. It *is*
      resolved later, at `start` (`:2107-2110`).

      Recommend one follow-up item covering both: add the `check` rule first,
      then the write-time refusal, in that order.
- **A work item's `capabilities.yaml` sidecar** — `write_sidecar`
  (`fs.py:3615-3656`) validates YAML shape only, and a dangling capability path
  is caught at `complete` by `capability_gate` (`tcw/work/recursion.py:25-65`).
  Deliberately a different mechanism (a gate on the transition, not on the file),
  and the sidecar is legitimately edited before its targets exist. No change.

## Abstraction litmus test

Operations added or changed:

| Operation | Verdict |
| --- | --- |
| "reject a capability write whose refs do not resolve" | **Model.** It is the standing convention every other TCW write path already honors (`tcw work edit --blocks` → `add_blocker`, `base.py:1763-1772`; `taxonomy add --vocab` → `_require_ref`, `fs.py:1102-1111`). A Jira-backed adapter validates an issue link before saving the issue; that it does so over an API rather than a folder is immaterial. No abstract *method* is added: the behavior is a precondition of the existing `set` / `update_capability`. |
| "a capabilities store obtains the taxonomy store for its own project" | **Adapter private detail.** The FS answer is `node_root / "docs" / "taxonomy"`. A remote adapter answers from its own connection and project key. Nothing about the answer appears in `CapabilitiesStore` or `TaxonomyStore`, so no adapter is forced into a filesystem shape. The *requirement* — "a capabilities store must be able to reach its taxonomy at write time" — is abstract and satisfiable by any adapter that can already implement `check(taxonomy=…)`. |
| `_ref_problems` (one renderer for six fields) | **Adapter private detail.** A private method over the already-abstract `get()`/`get_by_id()`. |
| `check(taxonomy=None)` defaulting to the store's own taxonomy | **Model, no signature change.** The parameter keeps its abstract meaning ("validate against this taxonomy"); `None` changes from "skip" to "use mine", which any adapter can implement or decline (returning `None` from its own accessor reproduces today's behavior exactly). |
| `add(..., fields=None)` — create a capability with its fields in one write | **Model, one optional keyword.** "Create an object with its initial fields" is the shape a remote adapter prefers: one issue-create call carrying its fields, rather than create-then-update. Today's two-call shape is the filesystem-flavored one, and it is what makes POST non-atomic. Every existing caller keeps working unchanged. |

One abstract signature gains one optional keyword (`add`); no store-interface
method is added, removed, or re-typed.

## Acceptance criteria

Criteria 1-10 are checkable in a throwaway git repo after `tcw init --id repro`,
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
7. **Per individual problem**, the refusal and `check` agree byte-for-byte. For
   each bad value in criteria 1-4 separately: write it directly into
   `meta.yaml`, run `tcw capabilities check`, and strip the leading
   `web/editing: ` from its line; that string must equal the refusal message
   from the corresponding `set` call, stripped of the `tcw capabilities set: `
   prefix. The multi-problem case (criterion 5) is compared after splitting the
   refusal on `"; "` — the delimiter is the write path's only addition, and the
   set of parts must equal the set of stripped `check` lines.
8. Against a running `tcw serve`, `PATCH /api/capabilities/web%2Fediting` with
   `{"fields": {"Subject": ["no-such-term"]}}` returns **422** (not 200, not
   500) with the same message, and `meta.yaml` is byte-identical to before.
9. `POST /api/capabilities` with `{"path": "new/thing", "fields": {"Feature":
   "also-bogus"}}` returns **422** and `docs/capabilities/new/thing/` **does not
   exist** afterwards — nor is anything staged for it (`git status --porcelain
   docs/capabilities/` is empty). Run the same POST with `{"fields":
   {"NotAField": "x"}}` and with `{"status": "InvalidStatus"}`: both must also
   leave no folder, since Design §5 fixes the class, not one input.
10. `POST /api/capabilities` with a *valid* `fields` object still returns 201 and
    the field is present in the response and in `meta.yaml` — the happy path
    `tests/test_serve_write.py:842-851` already pins, unchanged.
11. A capability that already stores a dangling `Subject` (written directly into
    `meta.yaml`) still accepts `tcw capabilities set <path> --status Omitted`,
    exit 0 — the repair route `tcw work complete` recommends
    (`tcw/work/cli.py:1241-1248`) still works.
12. On a node with `docs/taxonomy/` absent, `tcw capabilities set <path> --field
    Subject=anything` still exits 0 (nothing to resolve against), while
    `--field "Blocked by=nope"` is still refused. This is Goal 1's stated
    qualification, not an oversight; `tests/test_capabilities.py:200-204`
    (`test_set_subject_comma_replaces`, whose `node()` fixture creates no
    `docs/taxonomy/`) depends on it and must pass unmodified.
13. `FsCapabilitiesStore.check()` called with **no** `taxonomy` argument, on a
    node whose `docs/taxonomy/` exists and does not contain the ref, reports
    `Subject → dangling ref …` — the behavior reproduced as `[]` above. An
    explicitly passed `taxonomy=` still wins, **including a falsey one**: a
    stub whose `__bool__` returns `False` must still be consulted, which is
    what pins `is not None` rather than `or`. The suite's `StubTax` tests
    (`tests/test_capabilities.py:210, 222, 235, 242, 248, 255`) pass unmodified.
14. **One renderer, checked behaviorally.** For each of the six fields, with the
    same store and the same bad value: the string `check` produces (minus its
    `<path>: ` prefix) equals the string the refusal produces. Assert it in a
    test that drives both paths over the same fixture, so a future edit to one
    wording fails the test rather than drifting silently. A source-grep for
    duplicated wording is a review aid, not the criterion.
15. `python -m pytest -q` is green. Exactly one existing test is expected to need
    editing: `tests/test_environment_hardness.py:373-380`
    (`test_capability_check_dangling_subject`) builds its fixture by calling
    `caps.set(..., {"Subject": "ghost"})`, which this change makes impossible.
    It must be **rewritten, not deleted** — construct the invalid node directly
    (the `write_cap` helper in `tests/test_capabilities.py`) and keep asserting
    that `check` reports it dangling, since that behavior is unchanged and is
    what proves existing invalid data stays reportable. Any *other* test that
    needs editing is a signal the extraction changed behavior; investigate
    rather than adjust.
16. `tcw capabilities check` on this repo's own `docs/capabilities/` still exits
    0 with `capabilities OK`, and `tcw validate` is clean.
17. Documentation, each with its required assertion:
    `skills/tcw-capabilities/SKILL.md` states that `set` (not only `check`)
    refuses an unresolvable `Feature`/`Subject`; `README.md:519` and `:531` say
    `set` resolves the pointers too; `docs/changelogs/upcoming.md` lists the
    six affected fields and the POST atomicity fix under **Fixed**;
    `docs/release-notes/upcoming.md` states the behavior change in plain
    language (a script that set fields loosely and checked at the end now stops
    at the first bad ref); `set-a-capabilitys-status/description.md` states the
    acceptance rule for ref fields; `web/editing/description.md` reconciles its
    "post-save warnings" sentence with at-save refusal.

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
  already, but nothing enforced it. Mitigation: the SKILL.md sentence in Design §7.
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
  edited except the one named in criterion 15.
- **Opening a taxonomy store per write costs something.** `FsTaxonomyStore.open`
  reads `config.yaml` and builds nested `extends` stores. One per `set` call, so
  it is noise next to the git staging the same call performs; if a deeply
  federated tree makes it measurable, memoize on the instance — but do not
  pre-emptively.
- **`add` gains an optional `fields` keyword on the abstract interface.**
  Backwards-compatible (every existing caller omits it), but it is the one
  signature this item changes, and an out-of-tree adapter subclassing
  `CapabilitiesStore` would need to accept it to stay conformant. Judged worth it
  against the alternative — a *new* abstract `validate_fields` every adapter must
  implement — and it is the shape a remote adapter wants anyway (Design §5).
- **Pulling the POST fix in widens the item.** The partial write is pre-existing
  and reachable today without any of this change (Reproduction). Scoping it out
  would leave goal 2 false on one of the two web surfaces, so it comes in; but it
  is the one place this item fixes a defect it did not surface. If the batch must
  shrink, Design §5 is separable — the rest of the item stands without it, with
  goal 2 narrowed to PATCH.
- **Merge friction with the symlink item.** Both edit `FsCapabilitiesStore` in
  `tcw/store/fs.py`. Disjoint functions (Design §6), so a textual conflict is the
  worst case, not a semantic one.

## Notes

- The request's framing that this is "the last one that does not [fail closed]"
  is nearly right and worth correcting: after this item, the last *divergences*
  between a write path and `check` are closed, but two fields — a capability's
  `Planning doc` and a work item's `initiative` — are unvalidated **everywhere**.
  Design §8 (Sweep) records them; they need a `check` rule before a write-time
  refusal would mean anything.
- The request scoped the fix to `Subject` and `Feature`. The reproduction shows
  four more fields going through the identical unvalidated call. They are folded
  in rather than left for a later `check` to find, on the precedent's reasoning:
  same call site, same helper, and splitting them would put two agents in
  `_validate_fields` for one behavior. This is a scope widening from the request
  and is stated as such.
- Baselines taken at spec time, at `aff0cbb` (and unchanged at HEAD `1d74cb1`
  — no `tcw/` or `tests/` file differs between them), so a regression is
  attributable: `python -m pytest -q` → **1763 passed**; `tcw validate` →
  `validate OK`; `tcw capabilities check` → `capabilities OK`. Criteria 15 and
  16 are those numbers, not aspirations.
- **This spec was revised after an adversarial review** (Codex, against HEAD
  `1d74cb1`). What changed: the POST atomicity defect and its fix (Design §5,
  criteria 9-10); `is not None` rather than `or` for the `check` fallback; the
  equivalence claim in Design §4 narrowed to same-node wiring; the three wiring
  sites shown to *differ* (serve opens unconditionally) rather than being
  identical; Goal 1 qualified for taxonomy-less nodes; criteria 7, 14 and 15
  made mechanically checkable. Rejected nothing material.
- Scratch reproduction repo from this stage:
  `/private/tmp/claude-501/-Users-brian-Projects-TCW/984ed1dd-bc79-402a-bc4e-6b908f84283d/scratchpad/repro`.
  Disposable — rebuild from the Reproduction section rather than assuming it
  survives.
