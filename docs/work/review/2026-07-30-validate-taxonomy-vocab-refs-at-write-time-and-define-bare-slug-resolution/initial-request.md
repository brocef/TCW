# Validate taxonomy --vocab refs at write time and define bare-slug resolution

## Origin

GitHub issue [#10](https://github.com/brocef/TCW/issues/10), filed 2026-07-30 by
@brocef. Accepted during the second `tcw-triage-issues` sweep.

Reported against `tcw 0.17.2` on macOS 26.5.2 (darwin), Python 3.14.6, editable
install from a local clone. (The reporter notes `pip show tcw` reports stale
dist metadata — `Version: 0.10.3` — while the running code reports 0.17.2.)

> ### Steps to reproduce
>
> In a fresh git repo:
>
> ```bash
> tcw init taxonomy --id repro
> printf '%s' "parent" | tcw taxonomy add "Alpha"
> printf '%s' "nested child, unique leaf slug in the whole tree" | tcw taxonomy add "Zeta" --parent alpha
>
> # (a) bare leaf slug — unique in the tree — does not resolve
> printf '%s' "x" | tcw taxonomy add "Some Feature" --kind feature --vocab zeta
>
> # (b) a ref to a term that does not exist at all is also accepted
> printf '%s' "x" | tcw taxonomy add "Bogus Feature" --kind feature --vocab this-term-does-not-exist
>
> tcw taxonomy check
> ```
>
> ### Expected vs. actual
>
> - **Expected:** `add` resolves `--vocab` refs the same way `check` does and
>   fails closed on an unresolvable one — non-zero exit, nothing written.
> - **Actual:** both `add` calls print `Added term …` and exit `0`. The bad ref is
>   written verbatim into `meta.yaml`:
>
>   ```yaml
>   name: Bogus Feature
>   kind: Feature
>   relatesTo: []
>   vocabulary:
>   - this-term-does-not-exist
>   ```
>
>   Only a later `check` surfaces it:
>
>   ```
>   bogus-feature: dangling vocabulary ref 'this-term-does-not-exist'
>   some-feature: dangling vocabulary ref 'zeta'
>   2 problem(s).
>   ```
>
>   `--vocab alpha/zeta` (full path) resolves fine, so case (a) is specifically
>   that ref resolution only considers root-level slugs — a nested term's leaf
>   slug is dangling even when it is unique tree-wide.
>
> ### Impact
>
> Hit while bootstrapping a ~70-entry taxonomy via `references/init.md`. Because
> `add` exits 0, a batch of `add` calls looks entirely successful and the
> breakage only appears at the `check` at the end of the bootstrap — at which
> point the fix is `rm` + re-`add` per affected entry, since there is no
> `taxonomy set`-style command to repair a ref in place.
>
> ### Remediation
>
> Two separable fixes:
>
> 1. **Validate at write time** (the important one): resolve `--vocab` refs in
>    `add` using the same resolver `check` uses; on failure exit non-zero and
>    write nothing. This is the fail-closed behavior the rest of TCW follows.
> 2. **Decide what a bare leaf slug means.** `check`'s vocabulary of errors
>    includes *ambiguous* refs, which implies name/slug resolution is intended to
>    be more than root-level-only. Either resolve a tree-wide-unique leaf slug
>    (reporting *ambiguous* when more than one matches), or keep it path-only —
>    but then have the error name the expected form (`did you mean
>    'alpha/zeta'?`). The `tcw-taxonomy` SKILL.md quick-reference reads
>    `--vocab <term>`, which currently reads as "the term", not "the term's full
>    path"; worth tightening either way.
>
> Axis: taxonomy.

## Notes

Accepted as **one item** rather than two: the reporter's fix 1 and fix 2 are
separable in principle, but fix 1's error wording is a direct consequence of
fix 2's answer, and both land on the same resolver call. The `spec` stage may
still split it if the resolution-semantics half turns out to be the larger
change.

Confirmed still present at HEAD (0.17.3), not only the reported 0.17.2, and the
validation code the fix needs already exists:

- `FsTaxonomyStore.add()` (`tcw/store/fs.py:811-831`) writes `vocabulary`
  straight into `meta` with no resolution at all.
- `check()` (`fs.py:916-929`) and the in-place update path (`fs.py:1042-1056`)
  both already resolve every ref and distinguish dangling / ambiguous /
  wrong-kind. Fix 1 is largely a matter of `add` calling what `set` already
  calls — worth checking whether that validation should be factored out rather
  than written a third time.
- `get()` (`fs.py:785-798`) delegates bare refs to `get_local(ref)`, which is
  path-addressed — this is the root-level-only behavior behind case (a).

Three things the `request` stage should settle that the report does not:

- Fix 2 changes `get()`, which is the resolver for **all** ref kinds, not just
  `--vocab`: `relatesTo`, capability→taxonomy refs, and the inherited-taxonomy
  `extends` lookups all route through it. The blast radius is wider than the
  reported symptom, and that is what makes the design half of this item real.
- Whether `relatesTo` gets the same write-time validation as `vocabulary`. The
  report only names `--vocab`, but `add` skips validating both, and `check` and
  the update path validate both.
- Whether the absence of a `taxonomy set`-style repair command is in scope. The
  reporter names it only as what makes the bug expensive, not as a request.

This is TCW's own repo, so reporter and maintainer are the same person. The
quoted text is the report as filed, unedited.
