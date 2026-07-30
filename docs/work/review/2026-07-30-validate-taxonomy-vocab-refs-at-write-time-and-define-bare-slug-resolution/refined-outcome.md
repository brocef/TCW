# Refined outcome — Validate taxonomy `--vocab` refs at write time and define bare-slug resolution

**Verdict: accepted**, by the user on 2026-07-30.

Assessment delegated to the read-only `tcw-verifier`, which built every fixture
from scratch and ran a live HTTP server rather than reading verdicts off
`outcome.md`. The coordinating session re-ran the suite and all three checks
itself and independently reproduced the one residual finding.

## Evidence

All 12 acceptance criteria **met**, on real CLI and HTTP output:

| # | Criterion | Evidence |
| --- | --- | --- |
| 1 | dangling ref refused, nothing written | `vocabulary ref '…' does not resolve`, exit 1; target folder absent |
| 2 | leaf slug stored as path; `check` clean | `meta.yaml` → `vocabulary: [alpha/zeta]`; `taxonomy OK` |
| 3 | ambiguous names both candidates | `'zeta' is ambiguous: alpha/zeta, beta/zeta`, exit 1, nothing written |
| 4 | vocab-less Feature refused | `Feature requires at least one vocabulary ref`, exit 1 |
| 5 | wrong-kind ref refused | `points to Feature, expected Vocabulary`, exit 1 |
| 6 | resolving refs stored verbatim | local, `alias/path`, and bare-inherited all unchanged; `check() == []` |
| 7 | refs bounded to the store | see the attack results below |
| 8 | `POST /api/taxonomy` 4xx, no folder | live server: 422 + no folder; valid leaf slug → 201 with resolved path |
| 9 | one implementation | `_ref_problem` is the sole classifier; all three callers reach it |
| 10 | `get()` unmoved | federation tests are **pure addition** — zero removed lines |
| 11 | docs updated | six sites per Design §7 |
| 12 | this repo's taxonomy | `taxonomy OK` |

**Suite:** `1162 passed` at acceptance (`1161` at the verifier's run; +1 from a
fix folded into the sibling item). `capabilities check`, `validate`, and
`taxonomy check` all OK.

## The traversal fix holds

The security-relevant half of this item was attacked rather than confirmed.
Ref shapes tried, on the read path, the delete path, and the HTTP routes:

`../capabilities` · `../capabilities/thing/do-it` · `alpha/../../capabilities/…`
(`..` at depth) · bare `..` · empty string · `/etc` (absolute) · `\..\capabilities`
(backslash) · leading whitespace · trailing slash · `alpha//zeta` (empty segment)
· `./alpha` · `alpha/.` · `alpha/./zeta` · `..%2fcapabilities` ·
`%2e%2e/capabilities` (URL-encoded) · `%252e%252e%252f…` (double-encoded) ·
`shared/../secret` and three more through the `extends` alias branch · and a `..`
ref hand-written directly into a `meta.yaml`.

**Every one resolved to nothing.** Read path returns `no such term`; delete path
refuses and the target folder was verified intact after each. The hand-written
case reports `dangling vocabulary ref` with **no traceback** — the specific
outcome Design §3 had to get right by returning `None` instead of raising.

`update_term` and the `serve` PATCH route demonstrably reach the same guard
(`PATCH /api/taxonomy/..%2Fcapabilities%2Fvictim` → 404; double-encoded → 404, so
no double-decode). There is **no DELETE route for taxonomy terms** at all.

## Deferred follow-ups

**Filed: `2026-07-30-resolve-taxonomy-refs-against-symlinks-not-just-lexically`.**
`_safe_store_id` is a lexical guard and never calls `resolve()`, so a *planted*
directory symlink inside `docs/taxonomy/` still reads outside the store —
reproduced independently in the coordinating session (`SECRET BODY`, exit 0).

Rated low rather than critical, for reasons checked rather than assumed: the
**delete path does not escape** (`git rm` refuses to cross a symlink and the
target survives), the effect is read-only, and planting the symlink requires repo
write access — anyone who can do that can already read the target directly. It is
not a regression. Filed rather than dismissed because "refs are bounded to the
store" is now a stated property, and an unrecorded exception to a security
property is how the property stops being believed. The same item carries the
`CalledProcessError` traceback leak on that path.

**Filed earlier by the implementer:**
`2026-07-30-validate-capability-subject-and-feature-refs-at-write-time` —
`tcw capabilities set` has the identical write-time gap, but the fix is
structurally different because `FsCapabilitiesStore` holds no taxonomy handle.

## Notes carried forward

- **One coverage path is gone, not substituted, and that is the fix working.**
  The taxonomy-specific "saves but fails `check`" warning case no longer exists;
  the verifier tried to construct a replacement and could not, because `add` now
  validates kind, Feature-requires-vocabulary, and every ref. Unreachable by
  construction.
- **The write/read asymmetry is deliberate and documented in three places.**
  `--vocab zeta` resolves a unique leaf slug; `tcw taxonomy show zeta` still does
  not. Widening `get()` would have touched nine call sites, two changing meaning
  rather than reach. Stated in `SKILL.md`, `README.md`, and the release notes
  rather than left to be discovered.
- **A test failure during verification was correctly attributed elsewhere.** The
  verifier's first run hit `test_the_router_stays_within_its_line_budget`
  (`SKILL.md body is 61 lines, budget is 60`) — a concurrent agent on the
  sibling item, breached at `ea965f0` and fixed at `6b53b82`. It reported the
  attribution instead of charging the failure to this item.

## Closeout choices

- **Route:** committed directly on `main`; no worktree, no PR. Commits `ad77395`,
  `75eebdf`, `83b1612`, `fd954ba`, `f9fcdcd`, `b796fb6`, `e1e116f`, `232db8b`.
- **Version:** none cut at closeout; folded into the **minor** bump
  (0.17.3 → 0.18.0) covering this seven-item batch, confirmed by the user on
  2026-07-30. This item contributes one of the release's two breaking behavior
  changes — `tcw taxonomy add` now fails closed, so a bootstrap script that
  batched `add` calls and checked only at the end will now stop at the first bad
  ref. The release notes call it out explicitly.
- **Definition of Done:** `tests pass`, `docs synced`, `capabilities reconciled`,
  `reviewed`, `version offered` all satisfied.

  The sixth entry — *originating GitHub issue answered and closed* — **applies
  and is deliberately deferred, not missed.** This item resolves
  [GitHub #10](https://github.com/brocef/TCW/issues/10). Per the user's
  2026-07-30 decision, an issue is answered only after the containing version is
  cut **and pushed**, so it is never closed while the fix is uninstallable.

Worth carrying into the #10 reply: the reporter's two-part framing was right, but
`add` was skipping two further rules `check` applies (empty-Feature, wrong-kind),
and the fix folded those in. The reporter's point 4 (`relatesTo` validation)
turned out vacuous — `add` has no `--relates` flag and hard-codes `relatesTo: []`.
