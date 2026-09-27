# Report malformed keys and unregistered tags in lifecycle config

## What is wanted

A mistake in the work configuration of `tcw-config.yaml` should produce a clear
report, never a crash and never a binding that silently does nothing.

1. **Tag conditions that can never match.** A lifecycle binding's `when.tags` is
   compared as raw text against an item's tags, which are always normalized. So
   `tags: [CLI]`, `tags: ["cli,docs"]` and the typo `tags: [clii]` all never fire,
   and `tcw validate` reports the node sound. A project can believe a bug-specific
   template is in force for a year without it ever being used. This repository has a
   live binding of this kind (`when: { tags: [bug] }`) that works only because `bug`
   is already canonical.
2. **Same silence elsewhere.** `tcw work list --tags <typo>` exits 0 with no rows,
   indistinguishable from a correct filter over an empty result. Three other tag
   readers disagree with the rest: `registered_tags` returns config values unnormalized,
   plan-stage declarations check tags against the registry without normalizing (so
   `Cli` is refused there but accepted by `--tag`), and the web API iterates a JSON
   string tag character by character and reports a single letter as unregistered.
3. **Crashes on a non-string key.** An unquoted number key in YAML is an integer, and
   six parsers build their "unknown key" message by sorting and joining the keys, which
   raises `TypeError` and prints a traceback instead of naming the bad key. The
   tracker parser and the project registry already had this fixed.

## Constraints

- **A binding that fires today must keep firing.** Normalizing values that already
  match changes nothing, but newly matching values change behaviour, and for
  `not_tags` a newly matching value newly *excludes* items. The spec must say so.
- **Unregistering a tag then fixing the config must remain possible**, so an
  unregistered tag in a condition may be a warning rather than a refusal to load.
- `tcw work tags rm <absent>` staying a silent no-op is correct and is not part of this.

## Notes

- Merged at triage from two inbox entries, because both are defects in how the work
  configuration is parsed and checked in `tcw/store/base.py`; the "sibling" readers the
  first entry asked about were kept in scope under the maintainer's rule of combining
  changes to the same feature. Both entries kept verbatim in `intake.md`.
- The entry names two decisions as the substance of the item — normalize, validate, or
  both; and whether `not_tags` gets the same treatment. They are left to the spec.
- Checked at triage on `main`: `Condition.matches` and `_parse_condition` still compare
  raw strings; all six `', '.join(sorted(...))` sites are unchanged; `work list --tags`
  on an unregistered tag exits 0 silently.
- Reference material: asked; none provided.

## References

- `docs/work/completed/2026-08-11-accept-comma-separated-tags-on-tcw-work-new/` — fixed
  the same silent-failure class in the tag CLI; its spec states where a comma may be a
  separator, and its outcome explains why grepping for one argparse mechanism missed
  call sites.
- `tests/test_tracker_inheritance.py` (`test_mixed_key_types_*`) — the test pattern
  used for the key-type fix already made.

## Folded in: 2026-09-11-validate-a-skill-prompt-binding-names-something-that-exists

_Merged here during the 2026-09-24 backlog cleanup; the source was closed as superseded._

### Inbox manifest

- `skill-binding-names-are-never-validated.md`

### Inbox body

## A `skill:` prompt binding is never validated, and a typo resolves silently

Found while building the eval harness
(`2026-07-22-evaluate-and-refine-the-plugin-skills-with-an-eval-harness`).
Filed rather than fixed: that item's spec lists "no `tcw` command-surface or
store changes" as a non-goal, and fixing this means editing `tcw/`.

### What happens

`_resolve_one` (`tcw/work/resolve.py:193`) resolves a `skill` binding to the
literal string `Invoke the <name> skill.` and never checks that the named skill
exists. Nothing else checks either.

Reproduced on a scratch node whose `tcw-config.yaml` binds a skill that exists
nowhere on disk or in any plugin:

```
$ grep -A1 'verify:' tcw-config.yaml
        prompt:
        - skill: eval-verify-marker

$ find . -iname '*eval-verify-marker*'          # nothing

$ tcw validate; echo $?
0

$ tcw work stage prompt verify <slug> | grep 'Invoke the'
Invoke the eval-verify-marker skill.
```

So a project can mistype a skill name, `tcw validate` stays green, and every
agent reaching that stage is told to invoke something that does not exist.

### Why it matters more than a typo usually would

The other four prompt kinds all fail loudly on a bad value. A `file` binding
naming a missing path raises, and a `generate` binding whose script fails turns
into a `ResolveError` that exits 1 with no stdout. `skill` is the only kind that
takes an unusable value and resolves as though nothing were wrong.

It is also the kind whose effect is hardest to observe: the resolved text looks
correct in isolation, and only the agent's failure to find the skill reveals it.

### What it is not

Not a request to inline the skill's body. Resolving to a pointer is the right
design under the harness-compatibility rule, since a Codex reader and a Claude
reader both get the same sentence.

### Possible shapes, in rough order of cost

1. `tcw validate` warns when a `skill` binding names something not present in
   any known skill source. Needs a way to enumerate skills, which may not exist.
2. The resolved text names the binding's origin, so a reader who cannot find the
   skill can at least see which config declared it.
3. Documented as intended, and `skill` bindings are declared unvalidatable.

Option 1 is the one that matches how the other kinds behave; option 3 is honest
if enumeration is genuinely out of reach.
