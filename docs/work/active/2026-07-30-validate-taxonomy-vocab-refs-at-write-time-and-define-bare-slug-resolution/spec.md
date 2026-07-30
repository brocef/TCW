# Spec: validate taxonomy `--vocab` refs at write time and define bare-slug resolution

## Capability changes

No new capability, no removal. One existing entry changes wording; one is
touched by the sweep.

- **changed** — `taxonomy/add-a-term` (`cap-563e2e`, Status `Supported`,
  `Feature: taxonomy-feature-registry`, `Subject: [term]`). Its
  `description.md` currently reads "…repeatable `--vocab <ref>`…" with no
  statement about what a ref may be or what happens when it does not resolve.
  `add` becoming fail-closed and accepting a tree-wide-unique leaf slug is a
  user-visible acceptance change and belongs in that body. Status stays
  `Supported`.
- **changed** — `taxonomy/remove-a-local-term` (`cap-b337dd`, Status
  `Supported`). Its body says `tcw taxonomy rm <path>` "delete[s] a local term";
  Design §3 makes that true, since today the path is not bounded to the store.
  Status stays `Supported`.
- **unchanged** — `taxonomy/validate-the-taxonomy`. `check` reports the same
  problems in the same words; only the population of refs that can reach it
  changes.

Record both as `changed:` in the item's `capabilities.yaml` at plan time. No
capability records are written by this stage.

> **Correction (implement).** Planning never wrote that sidecar — the folder
> held `initial-request.md`, `spec.md`, `plan.md`, `state.yaml` and nothing
> else. Implementation created it (commit `f9fcdcd`) with both entries under
> `changed:`; without it the `complete` gate has no record of this item's
> product delta.

## Problem

Three write-time gaps and one resolver gap, all on the same call path.

**(a) `add` does not resolve `--vocab` refs at all.** `FsTaxonomyStore.add()`
(`tcw/store/fs.py:811-831`) copies `vocabulary` into `meta` verbatim
(`fs.py:828-829`) and writes (`fs.py:830`). Nothing between the kind check
(`fs.py:820-823`) and the write consults the store. Every other TCW write path
of this shape fails closed — `tcw work edit --blocks` resolves each ref before
any write lands (`tcw/work/cli.py:707-710`), and `update_term` resolves every
ref before `_write_node` (`fs.py:1035-1056`).

**(b) A bare leaf slug does not resolve.** `get()` (`fs.py:785-798`) has three
branches: an `extends`-alias prefix (`fs.py:787-788`), a local lookup via
`get_local(ref)` (`fs.py:789-791`), and a probe of each extended store's
`get_local(ref)` (`fs.py:792-797`). `get_local` is path-addressed —
`self.root / slug` (`fs.py:767-768`) — so `alpha/zeta` resolves and `zeta` does
not. The "bare" in "bare-wins-local" (`fs.py:789`) is about *origin*, not
*depth*: it means an unqualified ref prefers the local store, not that a leaf
slug is searched for.

**(c) `add` skips two more of `check`'s rules.** `check()` also requires a
Feature to carry at least one vocabulary ref (`fs.py:917-918`) and requires each
ref to point at a `Vocabulary`, not a `Feature` (`fs.py:927-929`). `add`
enforces neither.

**(d) Sweep: a ref escapes the store root.** `get_local` joins a caller-supplied
ref onto `self.root` with no guard (`fs.py:767-768`), while `add` guards its
`slug`/`parent` with `_safe_store_id` (`fs.py:814-816`) whose own docstring says
"the bounded-input rule in the spec forbids escaping the store root"
(`fs.py:553-558`). So a ref containing `..` reads — and, through
`remove()` → `self._rm(self.root / term.slug)` (`fs.py:833-841`), deletes —
folders outside `docs/taxonomy/`. `tcw serve` reaches this resolver with request
input (`PATCH /api/taxonomy/<ref>` → `update_term` → `get`,
`tcw/serve/__init__.py:1038`).

Reproduced at HEAD (`e0ab9d2`, `tcw 0.17.3`) in a throwaway repo:

```
$ tcw init taxonomy --id repro
$ printf 'parent' | tcw taxonomy add "Alpha"
Added term alpha
$ printf 'child' | tcw taxonomy add "Zeta" --parent alpha
Added term alpha/zeta

--- (a) bare leaf slug ---
Added term some-feature
exit=0
--- (b) nonexistent ref ---
Added term bogus-feature
exit=0
--- (c) full path ---
Added term good-feature
exit=0
--- empty --kind feature ---
Added term empty-feature
exit=0
--- vocab ref pointing at a Feature ---
Added term wrong-kind
exit=0
--- check ---
bogus-feature: dangling vocabulary ref 'this-term-does-not-exist'
empty-feature: Feature requires at least one vocabulary ref
some-feature: dangling vocabulary ref 'zeta'
wrong-kind: vocabulary ref 'good-feature' points to Feature, expected Vocabulary
4 problem(s).
exit=1
```

and the traversal half:

```
$ tcw taxonomy show ../capabilities/thing/do-it
Do It  (../capabilities/thing/do-it, local)
kind: Vocabulary

$ printf 'x' | tcw taxonomy add "Escape Feature" --kind feature \
      --vocab ../capabilities/thing/do-it
Added term escape-feature
$ tcw taxonomy check | grep -c escape-feature
0                          # check accepts a ref that points outside the store

$ tcw taxonomy rm ../capabilities/thing/do-it
Removed term ../capabilities/thing/do-it
$ ls docs/capabilities/
.gitkeep                   # docs/capabilities/thing/ is gone
```

The cost is the reporter's: `add` exits 0, so a scripted bootstrap of a large
taxonomy looks clean and the breakage surfaces only at the closing `check`.

## Goals

1. `tcw taxonomy add` refuses a `--vocab` ref that does not resolve, writes
   nothing, and exits non-zero — same three distinctions `check` already makes
   (dangling / ambiguous / wrong kind), plus the empty-Feature rule.
2. A bare leaf slug that is unique among local terms is accepted by `--vocab`
   and stored as the full path, so the term it names is what `check` and every
   read path later resolve. Two local terms sharing a leaf slug is an
   *ambiguous* error naming both candidates.
3. That validation lives in one place, called by `add`, `check`, and
   `update_term`, instead of a third copy.
4. A taxonomy ref cannot address anything outside `docs/taxonomy/`, on read or
   on remove.
5. The `--vocab <ref>` documentation says what a ref may be.

## Non-goals

- **Changing `get()`'s bare-ref semantics for read paths.** `show`, `rm`,
  `check`, `tcw://T/…` and the web viewer keep path-only addressing. Rationale
  under Design.
- **A `tcw taxonomy set` / `edit` CLI.** Out of scope — reasoning under Design.
  No backlog item covers it today (`docs/work/backlog/` has none; `grep -rl
  "taxonomy set\|taxonomy edit\|update_term" docs/work/backlog/` matches only
  this item's `initial-request.md`).
- **A `--relates` flag on `add`.** `add` has no such flag
  (`tcw/taxonomy/cli.py:191-200`) and hard-codes `relatesTo: []`
  (`fs.py:827`), so there is nothing to validate there; adding the flag is a new
  feature, not this fix.
- **Rewriting refs that already resolve.** `--vocab Argument` resolving through
  an `extends` alias keeps storing `Argument`, not `shared/Argument`.
  Normalization applies only to a ref that would otherwise be rejected.
- **Write-time ref validation for capabilities** (`Subject`, `Feature`). A real
  sibling defect, grounded below, but a different fix — file it separately.
- **Migrating taxonomies that already contain bad refs.** `check` already finds
  them; repairing them is the (out-of-scope) editor's job.

## Design

### 1. One ref-problem helper, three callers

`check()` (`fs.py:916-929`) and `update_term()` (`fs.py:1042-1056`) already
encode the identical three-way distinction, differing only in output shape —
`check` appends a string, `update_term` raises `ValueError`.

> **Correction (implement).** They differ in **wording** as well as in shape:
> `check` says `dangling vocabulary ref '<r>'` / `ambiguous vocabulary ref
> '<r>'`, `update_term` says `vocabulary ref '<r>' does not resolve` /
> `vocabulary ref '<r>' is ambiguous`, and both wordings are asserted by tests
> (`tests/test_taxonomy.py:211`, `tests/test_store_editor.py:564`). So the
> helper cannot return a ready-made message: it returns a **classification
> code** (`"dangling"` / `"ambiguous"` / `"kind"`) that each caller renders.
> Only the wrong-kind sentence is byte-identical in both callers, so that one
> is shared verbatim as `_wrong_kind_ref` — which is what keeps `points to` to
> a single occurrence. `add` needs the same
logic plus the resolved slug. That is the third copy, which is where extraction
earns itself: a private `FsTaxonomyStore` method taking a ref and returning the
resolved `Term` (or `None`) together with a problem string (or `None`).
`FsCapabilitiesStore._ref_error(identifier) -> str | None` (`fs.py:1607-1613`) is
the existing precedent for the shape and the name.

Litmus test: this is a private method of the FS adapter over the already-abstract
`get()`; no store-interface method is added, and any adapter can implement
"resolve this ref before accepting the write". Clean.

### 2. Bare leaf slugs resolve at the write boundary, not in `get()`

**Recommendation: do not change `get()`.** Resolve a bare leaf slug in `add`'s
validation step and store the resolved full path.

What routes through `FsTaxonomyStore.get()` today:

| Caller | Effect of widening `get()` |
| --- | --- |
| `remove()` (`fs.py:834`) | `tcw taxonomy rm zeta` would start deleting `alpha/zeta` — a destructive command silently gaining reach |
| `update_term()` target lookup (`fs.py:986`) | a PATCH would start editing a different term than today |
| `check()` ref validation (`fs.py:912, 921`) | refs previously reported dangling would silently become valid |
| `check(identifier)` selection (`fs.py:942`) | scope of a targeted check widens |
| `_validation_resources()` (`fs.py:971`) | `tcw validate <target>` widens |
| `get_term_detail()` (`fs.py:986`) → `tcw serve` GET/PATCH | web reads/writes widen |
| `FsCapabilitiesStore._check_subject` / `_check_feature` (`fs.py:1635, 1646`) | capability→taxonomy refs widen |
| `resolve_tcw_ref` (`tcw/refs.py:110`) | every `tcw://T/<ref>` link in prose widens |
| `taxonomy show` / `rm` (`tcw/taxonomy/cli.py:92, 109`) | CLI reads widen |

Two of those are not merely wider but *different*: in a federated repo where the
local tree has `alpha/zeta` and an extended project has a root-level `zeta`,
today's `zeta` resolves to the inherited term (`fs.py:792-795`); a local-first
leaf fallback would redirect the same stored ref to the local one. And
`AmbiguousRef` is raised today only across `extends` aliases (`fs.py:797`); a
local-vs-local leaf collision would be a new raise site inside `get()`, which
`tcw taxonomy add` does not catch (`tcw/taxonomy/cli.py:80` catches `ValueError`
only) — a traceback until every call site is audited.

Write-boundary resolution has none of that: `get()` keeps its contract
(`tcw/store/base.py:169-173`), no read path changes, and the stored ref is always
a path that already resolves — so `check` cannot disagree with `add`. Storing the
bare slug verbatim is not an option for the same reason: `add` would succeed and
the very next `check` would call the result dangling.

**The tradeoff, stated:** a bare leaf slug is an *input convenience at write
time*, not a stored identity. `tcw taxonomy show zeta` still fails after
`--vocab zeta` succeeded. That asymmetry is the price of not widening a
destructive resolver, and it is bounded by `add` echoing the path it resolved to.

The reporter's third option ("keep it path-only and say *did you mean
`alpha/zeta`?*") is strictly weaker: the same leaf scan is needed to produce the
suggestion, so accepting the unique match costs nothing extra and saves the user
a round trip. When the scan finds *no* match the error is still just "does not
resolve".

The fallback scans `_local_slugs()` (`fs.py:770-772`) for entries whose last
segment equals the ref. Local terms only — an inherited tree's leaves stay
addressable by `alias/path`, matching the existing rule that inherited lookups
are path-addressed against the source store (`get_inherited`, `fs.py:800-802`).

### 3. Refs are bounded to the store root

Route the ref through `_safe_store_id` (`fs.py:553-566`) inside `get_local`
(`fs.py:767-768`), treating a rejected ref as **unresolvable** (return `None`)
rather than raising. `get()` is documented to return `None` for a ref that
resolves to nothing (`tcw/store/base.py:169-173`), and `check()` catches only
`AmbiguousRef` (`fs.py:911-915`) — a raise there would crash `check` on a
taxonomy that already contains such a ref. Returning `None` makes `check` report
it dangling, `show`/`rm` say "no such term", and `add` refuse it, with no new
exception type for any caller to learn.

### 4. Why the repair command stays out

The reporter names the missing `taxonomy set` as what makes the bug *expensive*,
not as the fix. The underlying operation already exists — `update_term`
(`fs.py:981-1064`) is on the abstract store (`base.py:209-228`) and is reachable
over HTTP (`tcw/serve/__init__.py:1038`); only a CLI verb is missing
(`SUBCOMMANDS` at `tcw/taxonomy/cli.py:10` has no `set`/`edit`). That is a CLI
surface addition with its own flag design, `--core-revision` question, and doc
surface — a separate item. Once `add` fails closed, the `rm` + re-`add` loop it
was meant to shorten does not start.

### 5. Sweep

Repo-wide, for the criterion *a CLI/API write path that accepts a cross-object
reference must resolve it before writing*:

- **`tcw capabilities set --field Subject=… --field Feature=…` — same defect,
  not fixed here.** `_validate_fields` (`fs.py:1340-1352`) checks field *names*
  against `CAP_FIELDS` and `Status` values, never refs; `check` resolves them
  afterwards (`fs.py:1627-1655`). Reproduced at HEAD:

  ```
  $ tcw capabilities set thing/do-it --field Subject=no-such-term --field Feature=also-bogus
  Set thing/do-it
  exit=0
  $ tcw capabilities check
  thing/do-it: Subject → dangling ref 'no-such-term'
  thing/do-it: Feature → dangling ref 'also-bogus'
  2 problem(s).
  ```

  It is out of scope because the fix is structurally different:
  `FsCapabilitiesStore` holds no taxonomy handle — `check(taxonomy=None)`
  receives one as a parameter (`fs.py:1479`) — so fixing it means deciding how a
  capabilities store obtains a taxonomy store at write time, which is a design
  question about store composition, not a missing call. **Recommend a follow-up
  item.**
- **`tcw work edit --blocks/--blocked-by`** already validates before writing
  (`tcw/work/cli.py:707-710`) — no defect; it is the convention this item
  restores.
- **Work → capability refs** (`capabilities.yaml`) have no CLI writer; they are
  authored by hand and gated at `complete` by `capability_gate`
  (`tcw/work/cli.py:848`). No write-path defect.
- **`POST /api/taxonomy`** (`tcw/serve/__init__.py:854-886`) calls the same
  `taxonomy.add()`, so fixing the store fixes the web path with it — nothing
  separate to do, and this is why the fix belongs in the store rather than in
  `tcw/taxonomy/cli.py`.

### 6. Not split

One item. With `get()` untouched, the "resolution semantics" half is a leaf-slug
scan inside the same helper the validation half introduces — the same function,
the same tests, the same doc sentence. Splitting would put two agents in
`FsTaxonomyStore.add()` for one behavior.

### 7. Documentation

- `skills/tcw-taxonomy/SKILL.md:46` and the quick-reference row at
  `SKILL.md:79` say `--vocab <term>` / `<ref>` with no form given; state that a
  ref is a path (`alpha/zeta`) or an `alias/path`, that a tree-wide-unique leaf
  slug is accepted and stored as its path, and that `add` now refuses an
  unresolvable one.
- `skills/tcw-taxonomy/references/init.md:48-51` already lists vocabulary before
  features; make the ordering a requirement rather than a coincidence, since a
  bootstrap that adds features first will now fail.
- `README.md:396-397` says `check` validates those refs; say `add` does too.
- `docs/release-notes/upcoming.md` and `docs/changelogs/upcoming.md` per the
  Documentation Sync section of `CLAUDE.md`.

## Acceptance criteria

Each is checkable in a throwaway git repo after `tcw init taxonomy --id repro`,
`tcw taxonomy add "Alpha"`, `tcw taxonomy add "Zeta" --parent alpha`.

1. `tcw taxonomy add "F" --kind feature --vocab this-does-not-exist` exits
   non-zero, prints an error naming the ref, and `docs/taxonomy/f/` does not
   exist afterwards.
2. `tcw taxonomy add "F" --kind feature --vocab zeta` exits 0 and
   `docs/taxonomy/f/meta.yaml` contains `vocabulary: [alpha/zeta]` — the
   resolved path, not `zeta`. `tcw taxonomy check` exits 0 immediately after.
3. With a second `zeta` elsewhere in the tree (`tcw taxonomy add "Zeta"
   --parent beta`), `tcw taxonomy add "F" --kind feature --vocab zeta` exits
   non-zero, the message contains the word `ambiguous` and both candidate paths
   (`alpha/zeta`, `beta/zeta`), and nothing is written.
4. `tcw taxonomy add "F" --kind feature` (no `--vocab`) exits non-zero with the
   same "Feature requires at least one vocabulary ref" rule `check` applies
   (`fs.py:917-918`), and writes nothing.
5. `tcw taxonomy add "F" --kind feature --vocab <a Feature's slug>` exits
   non-zero, naming the expected kind, and writes nothing.
6. `--vocab alpha/zeta` (full path) and `--vocab <alias>/<path>` against an
   extended project both still exit 0 and still store the ref verbatim — no
   qualification is added to a ref that already resolved.
7. `tcw taxonomy show ../capabilities` exits non-zero with "no such term".
   `tcw taxonomy rm ../capabilities/<anything>` exits non-zero and deletes
   nothing outside `docs/taxonomy/`. A `vocabulary` ref containing `..` written
   directly into a `meta.yaml` is reported by `tcw taxonomy check` as dangling
   (not accepted, not a traceback).
8. `POST /api/taxonomy` with a `vocabulary` entry that does not resolve returns
   a 4xx (not 201, not 500) and creates no folder — the store fix reaches the
   web path (`tcw/serve/__init__.py:854-886`).
9. The three-way ref validation exists once in the source: `grep -c "points to"
   tcw/store/fs.py` within `FsTaxonomyStore` shows one occurrence, and `check`,
   `update_term`, and `add` all reach it.
10. `pytest` passes, including the existing federation-resolution tests
    (`tests/test_taxonomy.py:129-166`) unchanged — proof `get()`'s semantics did
    not move.
11. `skills/tcw-taxonomy/SKILL.md`, `skills/tcw-taxonomy/references/init.md`,
    `README.md`, `docs/release-notes/upcoming.md` and
    `docs/changelogs/upcoming.md` are updated per Design §7, and
    `docs/capabilities/taxonomy/add-a-term/description.md` states the new
    acceptance rule.
12. `tcw taxonomy check` on this repo's own `docs/taxonomy/` still exits 0.

## Risks

- **A previously "successful" bootstrap script now fails.** Intended, but
  user-visible: anything that piped a batch of `add` calls and only checked at
  the end will now stop at the first bad ref. Mitigation: the error names the
  ref and, for a leaf-slug miss, the candidates; release notes call it out as a
  behavior change.
- **Ordering becomes load-bearing.** A `--vocab` ref must exist *before* the
  feature that names it. `references/init.md:48-51` already emits vocabulary
  first, but nothing enforced it. Mitigation: the doc change in §7.
- **Bounding refs could reject a ref some existing taxonomy stores.** Only refs
  with empty, `.`, `..`, backslash or absolute segments are rejected
  (`fs.py:553-566`); such a ref cannot have addressed a term inside the store
  anyway, so it was already broken or already an escape. Low.
- **Two-place resolution is a fork in the vocabulary.** Someone will eventually
  ask why `--vocab zeta` works and `show zeta` does not. Mitigation: the SKILL.md
  sentence says it explicitly; if the read side is wanted later it is a separate,
  deliberate widening with `rm` handled on its own terms.
- **The extracted helper changes `check`'s message strings if done carelessly.**
  `check`'s wording is asserted by tests and quoted in this spec; the helper must
  preserve it verbatim.

## Notes

Three corrections to `initial-request.md`'s `## Notes`:

- "`add` skips validating both [`relatesTo` and `vocabulary`]" is true but
  vacuous: `tcw taxonomy add` has no `--relates` flag
  (`tcw/taxonomy/cli.py:191-200`) and `add()` hard-codes `relatesTo: []`
  (`fs.py:827`), so no `relatesTo` value can reach it. Point 4 of the request
  brief resolves to "nothing to do".
- "inherited-taxonomy `extends` lookups all route through [`get()`]" is
  imprecise. `get_inherited(alias, slug)` calls the source store's `get_local`
  directly (`fs.py:800-802`); it does not re-enter `get()`. The `extends` *probe*
  inside `get()` (`fs.py:792-795`) does, and that is the branch that matters.
- The request treats (a) and (b) as the whole defect. `add` also skips the
  empty-Feature rule and the wrong-kind rule (reproduced above) — same call site,
  same helper, so they are folded in rather than left for a later `check` to
  find.

Two facts found while grounding, recorded rather than acted on:

- `relators()` (`fs.py:876-879`) already matches `relatesTo` refs by leaf slug
  (`r.rsplit("/", 1)[-1] == slug`) when warning on `rm`. So one code path already
  behaves as if a leaf slug is meaningful, inconsistently with `get()`. This spec
  does not change it; it is evidence that "what a bare leaf slug means" was never
  decided, which is what Design §2 decides.
- This repository's own `docs/taxonomy/` is 16 root terms *with* nesting
  (`capability/subject`, `store/adapter`, `work-item/lifecycle-stage`, …), but
  every stored `vocabulary` ref points at a root-level term (`- capability`,
  `- feature`, `- term`, …). So the leaf-slug half never bit while dogfooding by
  luck of the ref set, not by flatness — which is why criterion 12 (`tcw taxonomy
  check` on this repo, currently `taxonomy OK`) is weak on its own and the
  throwaway-repo criteria carry the weight.
