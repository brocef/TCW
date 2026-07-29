# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category.

## Added

- **`docs/work/dod.yaml`** — this node's own Definition of Done: the five
  `DEFAULT_DOD` entries plus `originating GitHub issue answered and closed, if
  the item came from one`. **No code was written for this.**
  `FsWorkStore.dod_checklist` (`tcw/store/fs.py:2012`) has always read the file
  and fallen back to `DEFAULT_DOD` (`tcw/store/base.py:774`); TCW simply never
  had one. Generated from `DEFAULT_DOD` programmatically rather than retyped,
  because the file **replaces** the defaults rather than extending them.
- **`skills/tcw-triage-issues/SKILL.md` §8** — the closeout half of the loop.
  Locates the issue with `tcw work path <slug>` → `initial-request.md` →
  `## Origin`, then maps resolution to reply: `done` / `duplicate` / `wontfix`
  close the issue, `superseded` closes it **only** when the superseding item
  absorbed the request rather than deferring it. Restates the exact-text approval
  rule rather than cross-referencing §6.
- **Capability `work/customize-the-definition-of-done`** (`cap-73460f`) — the
  DoD override, which worked but appeared in no README, skill, or ledger entry.

## Changed

- **`skills/tcw-work/references/transitions.md`** — `complete` documents
  `docs/work/dod.yaml` and its replace-not-extend semantics; `discard` carries
  the closeout pointer. The two are deliberately **not** symmetric:
  `checklist = st.dod_checklist() if shipping else []` (`tcw/work/cli.py:810`)
  means a discard prints no checklist, so three of the four resolutions get no
  prompt from the DoD and the `discard` section is the only prompt they have.
- **`docs/capabilities/work/complete-a-work-item`** — "the same fixed checklist
  on every item" was wrong; the checklist is node-configurable. Corrected, and
  extended with the closeout.
- **`docs/capabilities/plugin/triage-github-issues`** — scope grows from one-way
  intake to include the closeout reply.
- **`README.md`** — documents `docs/work/dod.yaml`: the default list, that it
  replaces rather than extends, and that it never reaches the discard path.

## Internal

- **No `tcw/` diff.** The request asked whether this finally justified a
  `source`/`external-ref` field on the work model. It does not: provenance is
  body content, and body is already one of the four things the abstract model
  says an item has. A field would buy machine-readable lookup for a single grep
  at a single moment, performed by an agent already reading the item.
- The DoD stays `[prompted]`, never `[gated]`. Enforcement would require `tcw`
  to make a network call at completion, which is a non-goal — `tcw work complete`
  must not become able to fail because GitHub was unreachable.
- Verified by running rather than reading: this repo prints six checklist items
  and a throwaway `tcw init` repo prints five (override live, fallback intact); a
  discard prints none; and `self.root / "dod.yaml"` does resolve to
  `docs/work/dod.yaml`, which was the spec's one open assumption.
