# Refined outcome: Close the originating GitHub issue when a work item completes

**Accepted** by the user at `verify`, on the assessment as presented.

## Evidence

All 10 acceptance criteria met, each checked rather than assumed.

| # | Criterion | Evidence |
| --- | --- | --- |
| 1 | `dod.yaml` restates all five defaults plus one | Generated from `DEFAULT_DOD`, not retyped — `065727e` |
| 2 | `done` prints the new line | Ran `complete` without `--confirm`: six items |
| 3 | Discard prints **no** checklist | Ran it in a throwaway repo: permanence warning only |
| 4 | §8 covers four resolutions, `superseded` conditional | `32e0201` |
| 5 | `transitions.md` points from `complete` **and** `discard` | `32e0201` |
| 6 | `dod.yaml` documented, incl. replace-not-extend | `f1ab7d9` + `transitions.md` |
| 7 | Ledger: one new, two corrected | `2d3c587`; `check` clean |
| 8 | No `tcw/` diff | `git diff --stat -- tcw/` empty |
| 9 | Suite, validate, capabilities | **1095 passed**; `validate OK`; no drift |
| 10 | Issues #9 and #8 untouched | Both still `OPEN` |

`work/customize-the-definition-of-done` (`cap-73460f`) flipped to `Supported`.

## What this item is actually worth

The request framed two questions as central: whether this finally justified a
`source`/`external-ref` field on the work model, and whether the trigger had to
live in the CLI to be guaranteed under both harnesses.

**Both answers were no, and the diff under `tcw/` is empty.** Provenance is body
content, and body is already one of the four things the abstract model says an
item has — a field would have bought machine-readable lookup for one grep at one
moment, performed by an agent already reading the item. And `dod_checklist()` is
already declared on the abstract store (`tcw/store/base.py:983`) and already
reads `docs/work/dod.yaml` (`tcw/store/fs.py:2012`), so the prompt reaches both
harnesses identically without anything being built.

The by-product is the more durable result: that mechanism appeared in **no**
README, skill, doc, or capability, and `work/complete-a-work-item` positively
asserted the opposite — "the same fixed checklist on every item". A supported
behavior was reachable only by reading `fs.py`. It is now declared, documented,
and corrected.

## Limits, recorded so nothing overclaims

- **A prompt, not a guarantee.** The DoD is `[prompted]`, never `[gated]`
  (`transitions.md:70`). An agent can acknowledge the line without acting and
  nothing detects it. Enforcement would need `tcw` to make a network call at
  completion, which the spec ruled out so `complete` cannot fail because GitHub
  is unreachable. Kept out of the release notes deliberately.
- **Three of four resolutions get no automatic prompt**, since a discard prints
  no checklist. Covered by prose in `transitions.md` and §8 only.
- **§8 is unexercised against a real issue.** Its first genuine run happens when
  the items from #9 or #8 complete, which has not happened.
- **No back-fill.** Items completed before this change were not revisited.

## Follow-ups

None opened. The two backlog items from the earlier sweep
(`…-resolve-relative-connected-projects-paths-…`,
`…-make-the-reconcile-rollup-read-the-canonical-capabilities-yaml-schema`) are
where §8 gets tested; nothing further is needed until then.

## Closeout

- **Originating issue:** none. This item came from a chat request during the
  sibling item's verification, so §8's first branch — no `## Origin` issue,
  nothing to do — is what fires. The new checklist line is correctly a no-op
  here.
- **Merge route:** none. All work committed directly to `main`.
- **Docs:** current as of `f1ab7d9`.
- **Version:** fold into **v0.17.0**, per the user's instruction when the item
  was requested. The tag is local-only.
