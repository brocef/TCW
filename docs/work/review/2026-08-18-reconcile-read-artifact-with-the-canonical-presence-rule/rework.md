# Rework — Reconcile `read_artifact` with the canonical presence rule

Rejected at `verify`. The work is not wrong; its **premise** is. The spec decided
that the two presence rules disagree harmlessly and that "no user-facing path
reaches the disagreement". A review pass disproved it, and the disproof was
executed over real HTTP rather than read.

## What must change

**Fix the live 404.** `GET /api/work/<slug>` returns two contradictory presence
answers for the same artifact in one payload:

| Field | Built from | Blank artifact |
| ----- | ---------- | -------------- |
| `item.artifacts` | `artifacts()` → `_present` (`tcw/work/projection.py:149-153`) | `False` |
| top-level `artifacts[]` | `read_artifact` per name (`tcw/serve/__init__.py:658-670`) | **`True`** |

The web client binds to the **second** (`WorkDetail.artifacts: ResourceSummary[]`,
`web/client/src/model/types.ts:84`), filters on `resource.present`, and renders
an **Open** button (`web/client/src/ui/content-views.tsx:395-412`). The
`POST …/artifacts/<name>/open` handler gates on the **first**
(`tcw/serve/__init__.py:1334`). Measured:

```
top-level artifacts[] 'outcome'.present = True    <- what the UI binds to
item.artifacts['outcome']              = False    <- the lifecycle rule
POST .../artifacts/outcome/open -> 404 'artifact is not present'
```

A button the UI drew, which can never work. That is a defect, not an intended
disagreement, and the `## Risks` entry calling it "confusing but correct" is
wrong.

**The fix is one line in the serve layer.** Build the top-level list's `present`
flag from `work.artifacts(slug)` — the lifecycle rule the `/open` gate already
uses — and keep `read_artifact` only for `revision` and `mediaType`. One response
becomes self-consistent, and the button agrees with the gate that guards it.

**Do not touch the store.** Everything the item concluded about `read_artifact`
and `_present` stands and is now better supported: the two rules answer different
questions, and the bug is that *one consumer mixed them*, not that the rules are
wrong. The characterization test stays exactly as it is.

## Scope

- `tcw/serve/__init__.py` — the artifact-list construction.
- A test that fails without the fix: a blank artifact must report `present:
  false` in **both** places in one payload, and the `/open` gate must agree.
- `spec.md` — the "decided: intended" section and the `## Risks` entry are
  rewritten to say a real defect was found and fixed, not deferred.
- `docs/changelogs/upcoming.md` — this is now a behavior change, so the entry
  claiming "no behavior changes" needs correcting.

## Out of scope, still

The affordance question — whether the UI should *show* that a file exists but its
stage has not run — remains a separate concern. Reporting `present: false`
consistently is not the same as explaining why, and this rework only makes the
API tell one story.

## Why this was missed

The spec inherited "nothing today routes a user into the disagreement" from
`initial-request.md:32-35` and re-checked it only against `tcw work scaffold` and
the CLI, both of which route through `artifacts()` and are genuinely clean. It
never checked `tcw serve`, which is the one consumer that mixes the two rules.
The `verify` stage is exactly where that should be caught, and it was.
