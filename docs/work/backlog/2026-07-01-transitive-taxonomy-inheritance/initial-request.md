# Transitive taxonomy inheritance

If Project A extends the taxonomy of Project B, and Project B extends that of Project C, then
Project A's taxonomy should include both that of B and C.

Related: capability `taxonomy/federate-shared-vocabulary` is `Supported` only in
part, and its `Gaps` line already names this work — "remote git/URL sources,
version-pinning, and **transitive (multi-level) extends** are deferred to Phase
6; only local sibling-repo paths resolve today." This item is the transitive
half of that gap.

## Product changes

## Technical changes

_Findings from the 2026-07-28 backlog audit, verified against the tree._

- **The origin encoding is the design decision here, and it belongs in the spec.**
  `Term.origin` is a single alias string (`base.py:152`, defaulting to `"local"`)
  and it is used directly as a dict key into one level of extends —
  `self.extends[term.origin]` at `fs.py:863` and `fs.py:893`. A term inherited
  two hops away has **no representable value** for that field today: `extends` is
  keyed by the project IDs this node itself lists (`_extended_component_roots`),
  so a grandparent's ID is not a key in it. `Term.qualified` (`base.py:155-158`)
  renders `origin/slug` on the same assumption.

  So the spec must decide the encoding before anything else — a path-ish alias
  (`b/c`), a resolved-through chain, or a flattened re-key at load — and that
  choice determines what `qualified` prints, what a `tcw://` reference to an
  inherited term looks like, and whether existing single-hop data still reads.
  `Capability.origin` (`base.py:331`) is the same shape, so whatever is decided
  here sets the precedent for the capabilities axis.

- **Cycle-guarding is *not* part of this work — it is already done, at any
  depth.** `FsTaxonomyStore.__init__` threads a `_seen` set of resolved roots
  through nested store construction and skips anything already seen
  (`fs.py:656-664`), and `_cycles` walks the extends graph recursively for
  `check()` (`fs.py:868-884`). Going transitive does not weaken either — both
  already recurse. Do not budget for it.

## Meta changes

- Scope note: the capability Gaps line groups transitive extends with remote
  sources and version-pinning. They are independent — this item is only the
  transitive one, and closing it narrows that Gaps line rather than clearing it.
