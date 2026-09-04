Found by an adversarial review of the `extends` work, 2026-09-03. Measured and
reproduced.

1. **The second hop rebuilds the nested store with the wrong `node_root`.**
   `_extended_component_roots` now resolves the sibling's store, so `ext` can be
   any path — a configured `<component>.path`, or a provisioned checkout. But
   the callers then reconstruct it as `FsCapabilitiesStore(ext, _seen=seen)`
   with no `node_root`, and `FsTreeStore.__init__` falls back to
   `root.parent.parent`. That is correct only for the `docs/<component>` shape
   this change exists to stop assuming.

   `aa` extends `bb`; `bb` has `capabilities.path: caps` and extends `cc` →
   `extends project 'cc' is not reachable through connected-projects`, because
   the nested store's `node_root` became the tmp parent. With `bb`'s store at
   the default path the same graph works. The one-hop case the change fixed
   works; the transitive case it enabled does not. The `_seen_nodes` chain is
   dropped on that call too, so the node-level cycle guard resets every hop.

2. **Federation is now exponential in chain depth.** `_extended_component_roots`
   constructs the sibling store in full — including its whole `extends` subtree
   — only to read `.root`, and the caller constructs it again. Measured on a
   linear chain: depth 5 → 0.24 s, depth 8 → 1.95 s, depth 11 → 15.7 s. About
   8× per three levels. Before the change the walk was linear.

3. **Every generic `ValueError` from opening the sibling is rewritten as
   "has no <component> component", with `from None`.** A sibling whose own
   config is broken — a legacy `extends` map, a failed `require_valid`, a
   self-extend — is reported as having no store, sending the reader to create
   one that exists. The shape predates this work; opening a whole store inside
   the `try` made it far broader.

4. **An `extends` cycle is not reported.** Three comments say
   `check() reports it`; `FsProjectRegistry.check()` only knows about
   `connected-projects`, and an `extends` cycle between two legitimately
   connected projects is not one. `pp` extends `qq`, `qq` extends `pp` →
   no recursion, no report, and each side gets a different asymmetric federated
   view.
