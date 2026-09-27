# Spec: report malformed keys and unregistered tags in lifecycle config

## Capability changes

None. Configuration mistakes are reported instead of ignored or crashing.

## Problem

1. **Tag conditions compared raw.** `Condition.matches` (`tcw/store/base.py:1080-1095`)
   intersects a binding's `when.tags` / `when.not_tags` with an item's tags as
   written; `_parse_condition` (`base.py:2226-2270`) strips but does not
   normalize. Item tags are always normalized (`normalize_tag`, `base.py:964`),
   so `tags: [CLI]`, `tags: ["cli,docs"]` and a typo `tags: [clii]` never fire,
   and `tcw validate` says nothing.
2. **Other tag readers disagree.** `registered_tags` (`tcw/store/fs.py:5655-5659`)
   returns config values unnormalized; plan-stage declarations
   (`fs.py:4488-4524`) compare against it without normalizing, so a stage
   declaring `Cli` is refused where `--tag Cli` is accepted; `_validate_tags`
   (`fs.py:6104-6117`) raises `AttributeError` on a non-string element (the web
   API's JSON can supply one). A JSON *string* is already refused
   ("tags must be a list or None"). `tcw work list --tags <typo>` exits 0 with
   no rows, indistinguishable from a correct empty result.
3. **Non-string keys crash.** Six "unknown key" messages build their text with
   `', '.join(sorted(keys))` over keys from the config file: `base.py:2240`
   (`when`), `2295` (binding), `2452` (stage), `2668` (documentation entry), `2732`
   (`work.lifecycle`), `2799` (transition). An unquoted number key is an `int`,
   so `sorted` or `join` raises `TypeError` and `tcw validate` prints a traceback.
   (Sweep: every other `join(sorted(` in `tcw/` joins constants or ids.)
4. **`skill:` bindings are never checked** (folded in). `_resolve_one`
   (`tcw/work/resolve.py`) turns any value into "Invoke the <name> skill."

## Goals

1. `when.tags` and `when.not_tags` elements are normalized with `normalize_tag`
   at parse time. An element containing a comma, or one that normalizes to
   nothing, is a parse problem (that binding is dropped, as any malformed binding
   is; it could never fire before either).
2. `tcw validate` reports each condition tag that is not registered, for every
   binding (stages, transitions, artifacts, procedures), as a problem. This check
   is outside the parser, so the policy still loads and a tag can be unregistered
   and the config fixed afterwards.
3. `registered_tags` returns normalized, de-duplicated values and skips an entry
   that cannot be normalized; `tcw validate` reports such an entry. Plan-stage
   tags are normalized before the check and stored normalized. `_validate_tags`
   refuses a non-string element with a `ValueError`.
4. `tcw work list --tags X` for an X registered in none of the listed nodes
   prints a note to stderr (`'X' is not a registered tag; listing items that
   carry it anyway`) and still lists and exits 0.
5. The six join sites stringify before sorting: `sorted(map(str, keys))`.
6. `tcw validate` reports a `skill:` binding whose value is not a skill name:
   empty, containing whitespace, or containing `/` or `\` (a `plugin:skill`
   colon is allowed). Whether the skill exists is not checked; the configure
   documentation says so.

## Non-goals

- Checking that a named skill exists: `tcw` cannot see every harness's skills
  (user-level, other marketplaces), and `tcw validate` has no warning level, so a
  partial search would fail projects that are correct.
- Changing the resolved "Invoke the <name> skill." text.
- `tcw work tags rm <absent>` stays a silent no-op.

## Behavior change, stated

A binding whose condition was written in a non-canonical form (`CLI`) now fires
for items tagged `cli`; for `not_tags` it now **excludes** them. A binding
written in canonical form keeps firing, with two narrow exceptions found in
review: in a first-match artifact list a newly matching earlier condition can
shadow a later one, and an item whose tags were hand-edited into a
non-canonical form no longer matches a condition spelled the same way. The
changelog says so.

## Acceptance criteria

1. A binding `when: {tags: [CLI]}` fires for an item tagged `cli`;
   `when: {not_tags: [CLI]}` excludes it.
2. `when: {tags: ["cli,docs"]}` → `tcw validate` names the element and suggests
   `[cli, docs]`.
3. `when: {tags: [clii]}` with `clii` unregistered → `tcw validate` reports it,
   exit 1; `tcw work list` and `tcw work stage prompt` still work.
4. `work.tags: [Bug]` → `registered_tags()` is `["bug"]`; a plan stage declaring
   `tags: [Bug]` is accepted and stored as `bug`.
5. `update_work(slug, tags=[1])` raises `ValueError`, not `AttributeError`.
6. `tcw work list --tags nope` exits 0 and prints the note to stderr.
7. For each of the six sites, a config with an integer key (`1: x`) and one with
   mixed keys → `tcw validate` names the key, no traceback.
8. `skill: "my skill"`, `skill: "../x"`, `skill: ""` are reported; `skill:
   tcw:work` and `skill: documentation-sync` are not.
9. Full suite passes.

## Risks

- Projects with a non-canonical condition gain firings; stated above.
- A project with an unregistered condition tag turns `tcw validate` red — which
  gates `complete` in this repository's own config. That is the point; the
  message says how to fix it.

## Notes

- Decisions from two advisors (Codex, Opus); see `outcome.md`.
