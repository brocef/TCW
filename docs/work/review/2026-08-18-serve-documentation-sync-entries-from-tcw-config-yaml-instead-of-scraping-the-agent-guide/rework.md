# Rework — Serve documentation-sync entries from `tcw-config.yaml`

Sent back at `verify`. The delivered work is sound and the acceptance criteria
are substantively met. Two things are wrong with the **record**, and one small
thing is wrong with the **skill**.

## First: the premise I opened this rework with does not hold

I proposed reworking this item to resolve a "two sources of truth" collision —
that the repository now carries both a `work.documentation` config block *and* a
`## Documentation Sync` heading in its agent guide, which the skill name-matches
as its fallback, so an agent could read the wrong one.

**Checked. There is no collision.** The skill's own control flow forecloses it:

> **Ask `tcw work docs --json` first.** … `"config"` — the entries are declared
> in `tcw-config.yaml` … and the `entries` array is authoritative. **Use it and
> read no Markdown.**
> — `skills/documentation-sync/SKILL.md`

And this node reports exactly that:

```
$ tcw work docs --json
source: config
entries: ['README.md', 'docs/release-notes/upcoming.md',
          'docs/changelogs/upcoming.md', 'skills/<component>/SKILL.md']
```

The Markdown section that remains contains **no entries at all** — only the
directive to invoke the skill and the reasoning for why these four documents
exist. There is nothing for a reader to mistake for a second entry list.

This is the **third** argument in this release built on a failure story I had not
executed, after the version-cut spec's "the fallback would miss four files" and
the stdin rework's "a `pre-commit` hook blocks the transition forever". Recorded
here in the item that it happened in, and again in the post-mortem, because three
is a pattern and not an accident.

## What must actually change

### 1. `skills/documentation-sync/SKILL.md` presents the fallback as the default

Criterion 11a required that no file "instructs a reader to **find** documentation
entries in a Markdown section except as the named fallback". It was met. But the
criterion did not cover instructing a reader to **create** them there, and this
heading does:

> `## The Documentation Sync Section`
> Project owners add this section to their `CLAUDE.md`:

Read cold, that is a recommendation. It contradicts the top of the same file
(config-first) and `references/setup.md`, which already gets this right —
"**Two forms — prefer config in a TCW project**", with the Markdown form labelled
"Fallback, and the only option outside a TCW node".

**Fix:** retitle the section and lead it with the same framing `setup.md` uses, so
the two documents agree about which form is recommended. The bullet-list example
stays — it is the fallback's format reference and is still needed.

### 2. Acceptance criterion 11 is wrong and should be amended, not deviated from

It requires that this repository's `AGENTS.md` have **no** `## Documentation
Sync` section. Implementation kept the section (minus the entries) and recorded a
deviation, with a good argument: the skill's own `setup.md` says to "**always**
include the opening directive line", that directive is not an entry, and it has
nowhere else to live.

The argument is right; leaving it filed as an unmet criterion is what is wrong. A
criterion the work deliberately does not meet, with the reasoning parked in
`outcome.md`, reads at a glance like a gap. **Amend criterion 11** to require what
the item actually wants — the entry *list* gone from the guide, the directive and
reasoning retained — and note the amendment.

## Scope

- `skills/documentation-sync/SKILL.md` — one heading and its opening lines.
- `spec.md` — criterion 11 amended, with the change marked as made at rework.
- `tests/test_documentation_sync_wiring.py` — extend so the skill's recommended
  form is asserted, not just its fallback. Without a test, the framing drifts back.
- No production code. Nothing under `tcw/` changes.

## Not in scope

Removing the Markdown fallback. It is the only option outside a TCW node, and the
skill ships to projects that are not TCW nodes.
