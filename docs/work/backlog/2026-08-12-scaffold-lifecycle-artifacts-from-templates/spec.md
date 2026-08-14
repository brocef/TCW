# Spec — Scaffold lifecycle artifacts from templates

Child **C5**. The initiative's `spec.md` decides the boundaries; this decides how
C5 is built and settles the two decisions it was explicitly assigned.

## Problem

C3 can resolve an artifact template. Nothing writes one, so every lifecycle
document still starts from a blank file and whatever the agent remembers.

The obvious command — "write the artifact from its template" — is the one the
initiative spent a whole review round rejecting. Artifact presence is what
`tcw work list` renders and what "find your place" reads; a command that wrote
`spec.md` would light `S` on the board before any spec existed, which is exactly
the defect C1 needed three verify rounds to remove for the request.

## Goals

1. A command that gives you a starting point for a lifecycle document.
2. It cannot be mistaken for the document itself, by the board or by anyone.
3. Every artifact has a template, and a project can override any of them.
4. Resolve-then-write: a failed hook writes nothing and a retry is clean.

## Non-goals

- Authoring the artifact. The draft is a file to type into; the agent writes the
  real document.
- Scaffolding from `tcw serve`. Decided below, against.
- Removing a draft when the artifact lands. Decided below, against.
- The stage/status legality table — **C4 owns it** by an amendment to the epic,
  and C5 consumes `STAGE_STATUSES`.
- Built-in *stage prompt* content. That is C6's half of `Builtins`.

## Design

### `produces` becomes a tuple, and `--json` does not move

`LifecycleStep.produces` is a prose string today (`"refined-outcome.md
(accepted) or rework.md (rejected)"`). One artifact per stage was never true —
`inbox` produces none and `verify` produces one of two — so templates keyed by
artifact name need the names, not a sentence.

But `--json` ships that sentence under `produces`, and C3's captured baselines
assert `--json` byte-identical for eleven configurations including this
repository's own. Changing the key's value would break them for a reason that
has nothing to do with configuration compatibility, which is what those baselines
exist to protect.

So:

- **`LifecycleStep.produces`** becomes `tuple[str, ...]` of artifact names —
  `()`, `("spec",)`, `("refined-outcome", "rework")`.
- **`LifecycleStep.produces_note`** carries the prose, and is what the human
  renderer and `--json` print, under the key they always used.

The tuple is **not** added to `--json`. Nothing outside TCW needs it, and adding
a key that appears for every configuration would fail C3's criterion 1 for a
change that is not a configuration change. If a consumer ever wants it, that is
its own item with its own reason. `test_skill_lifecycle_parity` moves to the
tuple, which is a strict improvement: it currently regexes filenames out of prose.

### `tcw work scaffold <artifact> <ref>`

1. Resolve the artifact name against `WORK_ARTIFACTS`; unknown → exit 1 naming
   the legal names.
2. Resolve the item; missing or ambiguous → exit 1.
3. **Refuse when the real artifact already exists.** `spec.md` present → exit 1.
   This is the protection that matters, and it is why a draft does not need to be
   cleaned up.
4. Resolve the template through C3's `resolve_artifact` — first match wins.
5. Write `<artifact>.draft.md`.
6. Print the draft's path on stdout.

**Resolve fully, then write.** A hook failure means nothing was written and a
retry is clean. A write failure after successful resolution exits non-zero,
reports to stderr, and puts **nothing** on stdout — so a caller reading stdout for
a path never gets one for a file that does not exist.

### Where a draft lives, abstractly

`<artifact>.draft.md` is a **bounded derived namespace**: exactly one draft per
`WORK_ARTIFACTS` entry, never an open folder glob. Any store can hold "the draft
of artifact N" as a named resource.

That means it goes through a store method, not a composed path.
`WorkStore.write_draft(slug, artifact, text)` and `read_draft(slug, artifact)`
join the ABC beside `write_artifact`. Composing
`store.path(slug) / f"{artifact}.draft.md"` in the CLI would be the same
hardcoded-filesystem-reference defect the rollup had, and it would be the fourth
time this initiative found one.

`artifacts()` looks up `<name>.md` from the registry and never sees a draft, so
presence stays honest with no new machinery — no content hashing, no in-file
marker, no adapter-visible draft state.

### Built-in templates

A module-level map, artifact name → text, filling `Builtins.artifact_templates`.
One entry for **every** `WORK_ARTIFACTS` name, asserted as set equality.

**`intake`'s is empty**, deliberately and asserted so: intake has no prescribed
structure because it is whatever someone supplied. `tcw work scaffold intake`
therefore creates an empty `intake.draft.md` — a file to type into — rather than
refusing, so every artifact keeps the same rule with no carve-out. That is also
what replaces `tcw work new`'s old `→ edit:` hint.

### Decision: `tcw serve` does not offer scaffolding

The initiative asked C5 to decide, and to weigh a "safe subset" —
`blob`/`file`/`builtin` are pure text rendering, only `generate` is shell.

**Against.** `serve` runs no hooks, and that is a stated posture rather than an
oversight. A safe subset would mean the same configuration produces a draft in
the CLI and an error in the browser, for reasons a user cannot see from the
config — and the moment a project adds one `generate:` template, the button they
have been using stops working. A capability that silently depends on which kinds
someone happened to configure is worse than one that is absent.

The web app already shows every present artifact and lets you edit it. Creating
one from a template is a CLI operation.

### Decision: landing an artifact does not remove its draft

**Against**, for two reasons. `write_artifact` deleting a sibling file is a
side effect nobody asked that method for, and it would fire from `serve`'s editor
too — a save in the browser silently deleting a file is the kind of surprise this
initiative has been removing, not adding.

The staleness the initiative worried about is real: `spec.draft.md` can sit
beside `spec.md` disagreeing with it. The protection is step 3 — `scaffold`
refuses once the real artifact exists, so a draft can never be *regenerated* into
confusion — plus the name itself, which says what it is. Cleaning up is `rm`, and
a tool that deletes your files to tidy up is a worse trade.

## Acceptance criteria

The initiative's criteria 11 and 17 are the requirement.

1. **`tcw work scaffold spec <ref>` writes `spec.draft.md` with exactly the
   resolved content**, byte-for-byte — not "contains the template".
2. **It does not create `spec.md`**, and **`tcw work list` shows the same string
   for that item before and after**. An implementation that writes nothing fails
   the first clause; one that writes `spec.md` fails the third.
3. **It refuses when `spec.md` already exists**, exit non-zero, naming the file.
4. **A built-in template exists for every `WORK_ARTIFACTS` name**, asserted as
   **exact set equality** rather than "at least one", and each has exactly one
   definition in the codebase.
5. **`intake`'s built-in template is empty**, asserted explicitly so nobody
   helpfully adds headings later, and `tcw work scaffold intake` creates an empty
   `intake.draft.md` rather than refusing.
6. **Resolve-then-write**: with a failing `generate` template, no draft is
   written and a retry after fixing the script succeeds. With an unwritable
   target, exit non-zero, message on stderr, **nothing on stdout**.
7. **The draft goes through the store**, not a composed path: a test asserts
   `write_draft`/`read_draft` exist on the `WorkStore` ABC and that the CLI has
   no `.draft.md` string in it.
8. **`produces` is a tuple for every step**, its union equals the set of artifact
   names any stage produces, and `verify`'s is exactly
   `("refined-outcome", "rework")` — the row prose could not express.
9. **C3's lifecycle baselines still pass**, unmodified, proving `--json` did not
   move.
10. **`artifacts()` never reports a draft**: with every draft present and no real
    artifact, the board string is unchanged and `artifacts()` reports all absent.
11. **A project template overrides the built-in**, and a conditional one selects
    by tag — one `blob` template `when: {tags: [bug]}` and a `builtin` fallback,
    checked both ways.
12. The capability `work/customize-lifecycle-artifact-templates` is **new**,
    declared here and flipped by this item's completion gate.

## Risks

- **A draft that disagrees with its artifact is clutter.** Accepted, with
  `scaffold`'s refusal as the guard rather than deletion.
- **`write_draft` widens the store interface** by two methods for one command.
  Justified by the litmus test — the alternative is a composed path — and the
  namespace is bounded to one draft per registered artifact.
- **The `--json` decision defers a real question.** A consumer that wants the
  artifact names machine-readably has no way to get them. That is a smaller
  problem than breaking a compatibility baseline for a non-compatibility reason,
  and it is one item away from being fixed.
