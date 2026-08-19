# Spec — Serve version-cut instructions from tcw-config.yaml instead of the agent guide

## Capability changes

**New.** One capability record under `docs/capabilities/work/`:

- *Declare how this project cuts a version* — a project names its version-bearing
  files, its cut command, and its guard test in `tcw-config.yaml`; TCW validates
  them and `tcw work versioning` prints them.

**Changed.** None. The lifecycle stages are untouched — unlike the
documentation-entry item, nothing here reaches a stage prompt (see Design).
No records are written at this stage; the ledger is reconciled at completion.

## Problem

`skills/documentation-sync/SKILL.md:124` sends the version-cut path to
`references/cut-version.md`, and that file's **Step 0** says:

> Check the project's `CLAUDE.md` (usually a `## Versioning` section) for a
> documented command or script. If one exists, **use it** — it knows which files
> carry the version and how they must move together.

"Usually a `## Versioning` section" is the whole specification. TCW obtains an
instruction it has to get right by name-matching a Markdown heading in a file it
does not own, in a format nothing validates. Rename the heading, reword the list,
or move the file, and TCW silently stops knowing how the project cuts a version,
falling through to a manual ritual that has to rediscover it. *(An earlier draft
claimed that ritual would bump one file and miss four. It would not — see the
withdrawn argument below. The cost is rediscovery, not corruption.)*

That is the same defect the documentation-entry item fixed, one layer over. It
was deferred out of that item's scope explicitly, with instructions to flag it
rather than fold it in silently. This is the flag.

**The facts this project has, and where they live now** (`AGENTS.md:47`,
`## Versioning`): five version-bearing files, the command
`python scripts/cut_version.py <patch|minor|major|X.Y.Z>`, and the guard
`tests/test_plugin_manifests.py`. All three are verifiable against the tree —
`scripts/cut_version.py:21-28` carries exactly those five paths in
`VERSION_FILES`, and `tests/test_plugin_manifests.py:36`
(`test_five_version_fields_agree`) is the guard.

### The weaker-guarantee objection, and why this proceeds anyway

Recorded because it was raised in the request and overruled, not missed.

The documentation-entry item was argued on the strength of the guarantee: a gate
that must fire at `plan` and `implement` cannot depend on a heading someone might
rename. **That argument does not apply here.** A version cut is always
user-initiated and never automatic; nothing fires on a schedule, and a human is
present at every step.

Three things carry it anyway:

1. ~~**Silent wrongness is worse than silent absence.**~~ **Withdrawn — this was
   the spec's strongest argument and it was false.** Review checked the fallback
   and I confirmed it against the tree: `references/cut-version.md:43-49` does
   **not** bump only `pyproject.toml`. It names `pyproject.toml` *plus a
   `__version__` constant*, and all three plugin manifests by path
   (`.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`,
   `.codex-plugin/plugin.json`) — every one of the five files this repository
   carries — and then says: *"Grep for the current version string before you
   start; projects routinely carry it in more places than their docs admit."*

   So the fallback is careful, not generic, and the desynced-release scenario I
   described is not one the fallback actually produces. It could still go wrong —
   the fallback also has to rediscover the *ordering*, the rotation, the commit
   and the tag that `scripts/cut_version.py` does in one step — but that is a
   claim about effort and repeatability, not about silent corruption. **The
   honest position is that this item does not prevent a bug; it removes a
   rediscovery step and an integration point built on a heading.**
2. **The layering.** `work.lifecycle`, `work.tags`, and now `work.documentation`
   are configuration TCW owns and validates. Version-cut facts are the only
   remaining project-level integration point still obtained by scraping prose.
   This is an argument about consistency, and consistency alone is a weak reason
   to add a schema — stated plainly rather than dressed up.
3. **Structured discovery across harnesses.** The one benefit that is neither
   consistency nor implementation cost: today an agent must open a Markdown file,
   find a heading that "usually" has a particular name, and read prose to learn
   how the project cuts a version. A Codex agent, a CI job, and a human all have
   to do that separately and can each get it wrong differently. `tcw work
   versioning --json` answers it once, the same way, everywhere — which is the harness-parity
   argument this repository already applies to everything that must be reliable.
4. **It is the same shape a second time** — cheaper to reuse than to re-argue.
   True for the plumbing, and *false for the semantics*: documentation entries are
   a homogeneous list where a partial entry is simply invalid, while a version
   policy has three independent optional keys whose partial states need defining
   (see *When config supersedes the fallback*). The similarity is real but
   shallower than the request assumed.

**The user was asked and confirmed the item should proceed with the
weaker-guarantee objection standing. That confirmation predates the discovery
that reason 1 was false**, which changes the strength of the case rather than the
decision. Recorded here so the decision can be revisited on accurate grounds
rather than inherited.

## Goals

1. The machine-checkable parts of a project's version-cut process are
   configuration in `tcw-config.yaml`, parsed and validated like every other
   `work.*` block.
2. A read-only verb serves them, because the version cut happens **after**
   `complete` and so has no stage.
3. `skills/documentation-sync/references/cut-version.md` takes its Step 0 from
   that verb, naming the `## Versioning` section only as the fallback.
4. A project that has configured nothing behaves **exactly** as it does today.
5. This repository declares its own five files, its command, and its guard.
6. The change folds into the unpushed v1.0.0.

## Non-goals

- **Running the cut.** `tcw` does not bump versions, rotate files, commit, or
  tag. It reports what the project declared; a human or an agent runs it. Making
  TCW execute a project's release command is a different item with a different
  risk profile, and nothing here requires it.
- **Validating that the declared files actually contain a version**, or that they
  agree. That is what the project's own guard test is for, and this repository's
  guard already does it (`tests/test_plugin_manifests.py:36`). TCW checking it
  too would be a second implementation of someone else's invariant.
- **A stage binding.** Unlike documentation entries, these facts reach no stage
  prompt — see Design.
- Removing the `## Versioning` prose from `AGENTS.md`. The *reasoning* (why five
  files, what drifts if they disagree) is project documentation and stays; only
  the facts move.
- The four earlier migration guides.

## Design

### Where it lives

```yaml
# tcw-config.yaml
work:
    version:
        command: python scripts/cut_version.py {bump}
        files:
            - pyproject.toml
            - tcw/__init__.py
            - .claude-plugin/plugin.json
            - .claude-plugin/marketplace.json
            - .codex-plugin/plugin.json
        guard: python -m pytest tests/test_plugin_manifests.py -q
```

`{bump}` is the one substitution, replaced with `patch` / `minor` / `major` /
an explicit version by whoever runs it — **TCW does not run it**, so the token is
documentation of the command's shape rather than a template TCW expands. A
`command` without `{bump}` is legal and reported as-is; where the bump argument
goes is then the reader's problem, exactly as it is today.

### When config supersedes the fallback

The first draft made all three keys optional *and* reported a single binary
`source`. Review found the hole and it is real: a block declaring only `files`
would report `source: config`, which tells the skill to use the declared
command — and there is none. Valid configuration would suppress a working
fallback and replace it with nothing.

**`command` is what makes a policy authoritative.** Precisely:

| Declared | `source` | What the skill does |
| -------- | -------- | ------------------- |
| `command` (with or without the others) | `config` | Run the declared command; run `guard` after it if declared; `files` is informational. |
| `files` and/or `guard`, no `command` | `agent-guide` | Fall back exactly as today — **and additionally** report the declared `files`/`guard`, which are still true and still useful to a manual ritual. |
| nothing | `agent-guide` | Today's behavior, unchanged. |

So `source` answers one question only — *is there a command to run?* — and the
other keys are additive rather than mode-switching. A partial policy can only
ever add information to the fallback; it can never take the fallback away.

`command` and `guard` must be **non-blank** when present: a blank string is a
declaration that declares nothing, and letting it through would recreate the same
hole one layer down.

`VersionPolicy` (frozen: `command`, `files`, `guard`) and
`parse_version_policy(raw) -> tuple[VersionPolicy, list[str]]` in
`tcw/store/base.py`, beside `DocEntry` and `parse_documentation_entries` and
mirroring both: pure, filesystem-free, never raises, advisory problem list.

`WorkStore.version_policy()` on the ABC, `FsWorkStore.version_policy()` reading
through `_work_config`, `version_problems()` folded into the same `check` path
`tcw validate` already consumes. Identical plumbing to `documentation()`, which
is the point.

**Validation is shape-only**, for the same reason: a non-mapping `version:`, a
non-string `command`/`guard`, a `files` that is not a list of non-empty strings,
a file path that is absolute or escapes the node, a duplicate path. It does
**not** check that a declared file exists — a project may add a version-bearing
file in the same commit that declares it — and does not parse the command.

### The verb

**`tcw work versioning [--json]`**, read-only, prints what the node declared.

```
$ tcw work versioning
command:  python scripts/cut_version.py {bump}
guard:    python -m pytest tests/test_plugin_manifests.py -q
files:    pyproject.toml
          tcw/__init__.py
          .claude-plugin/plugin.json
          .claude-plugin/marketplace.json
          .codex-plugin/plugin.json
```

`--json` emits `{"schema": 1, "source": "config" | "agent-guide", "command":
..., "files": [...], "guard": ...}`. `source` is `agent-guide` when nothing is
declared, exactly as `tcw work docs` does, so a caller branches on a field rather
than on emptiness.

**The verb is `tcw work versioning`, not `tcw work version`.** The first draft
chose `version` and defended it on the grounds that its output could never be
mistaken for a version string. Review pointed out that this addresses only one
failure mode: the ambiguity survives in instructions, search results, shell
completion, and conversation, where "run `tcw work version`" and "run
`tcw --version`" are one word apart and mean entirely different things.

`versioning` is still a single word — so it matches the twenty existing verbs,
unlike the rejected `version-cut` — it names a *process* rather than a number,
and it matches the `## Versioning` heading it replaces. `release` stays rejected:
it reads as though it performs one.

### Why no stage binding

The documentation item put entries into `plan` and `implement` because the gate
fires *during* the lifecycle. This one does not: `SKILL.md`'s own table places
the version offer **after `complete`**, and `tcw work stage <id>` on a completed
item is refused by the status check (`tcw/work/cli.py`), correctly.

So `tcw work versioning` is the whole delivery surface. No prompt changes, no
`{{tcw:…}}` span, and **no risk to the byte-identity guarantee** the sibling item
established — which is the strongest argument for keeping it out of the prompts,
since that guarantee is now pinned by `tests/fixtures/prompt_fallback/`.

### The skill

`references/cut-version.md` Step 0 is rewritten: ask `tcw work versioning --json`
first; on `source: config` use the declared command (and the guard after it);
on `source: agent-guide`, or outside a TCW node, fall back to the current
`## Versioning`-section behavior unchanged. `SKILL.md:124`'s parenthetical is
updated to match.

### This repository

`work.version` gets the five files, the command, and the guard. `AGENTS.md`'s
`## Versioning` section keeps its prose and loses the enumerated file list,
pointing at `tcw work versioning` for it — the same split the documentation entries
took.

### Abstraction litmus test

| Operation | Verdict |
| --------- | ------- |
| Read a node's version-cut configuration | **Model.** `tcw-config.yaml` is node configuration; a tracker-backed node has one exactly as a filesystem node does, precisely as `work.lifecycle`, `work.tags`, and `work.documentation` already do. |
| `tcw work versioning` | **Model.** Reads node configuration and prints it. Composes no store path and does not touch the work store at all. |

Nothing here is a filesystem trick. **Running** the declared command would be one
— it is a local shell concern, exactly what `lifecycle_policy`'s own docstring
excludes from the interface — and it is a stated non-goal.

### Harness compatibility

Entirely in the `tcw` CLI plus a skill reference both harnesses read. No hooks,
no dynamic context, no slash command.

## Acceptance criteria

1. `tcw validate` reports a problem naming the offending key for each of: a
   non-mapping `version:`, a non-string or **blank** `command`, a non-string or
   **blank** `guard`, a non-list `files`, a non-string or blank entry in `files`,
   an absolute path, a path escaping the node, a duplicate path, and an
   **unknown key** under `work.version`.
2. `tcw validate` exits 0 on a `version:` block whose declared files do not exist
   on disk, on a block declaring only one of the three keys, and on a `command`
   containing no `{bump}` token.
3. `tcw work versioning` prints the declared command, guard, and every file.
4. `tcw work versioning --json` parses and reports `"source": "config"`, with
   `files` in declaration order.
5. On an unconfigured node, `tcw work versioning --json` reports
   `"source": "agent-guide"` with `command`, `guard` null and `files` empty, and
   exits 0; `tcw work versioning` writes nothing to stdout and explains on stderr.
5a. **A policy declaring `files` and/or `guard` but no `command` reports
   `"source": "agent-guide"` while still returning those `files` and `guard`.**
   The case that must not suppress a working fallback; it is the whole reason
   `source` answers one question rather than being a mode switch.
6. `tcw work versioning` writes nothing — asserted by hashing every path under the
   work store and the node config before and after, not by `git status`.
7. **Stage output is untouched.** `tests/test_prompt_fallback.py` and
   `tests/test_lifecycle_baseline.py` both pass with **no edit to any file under
   `tests/fixtures/`** — asserted from the diff, since a fixture directory cannot
   itself "pass" and a re-captured fixture would make the tests green while
   proving nothing. This item adds no prompt text, so any movement means
   something unintended happened. Note this repository's live `tcw-config.yaml`
   gains a `work.version` block, and `self.json` records this node's real
   `tcw work lifecycle` output, so the check is not vacuous.
8. `skills/documentation-sync/references/cut-version.md` Step 0 names
   `tcw work versioning` and treats the `## Versioning` section as the fallback;
   `SKILL.md:124`'s parenthetical agrees with it.
9. This repository's `tcw-config.yaml` declares all five version-bearing files,
   the command, and the guard; `tcw work versioning` prints them; and the five paths
   it declares are **exactly** the keys of `VERSION_FILES` in
   `scripts/cut_version.py` — asserted by a test that reads both, so the config
   cannot drift from the script it describes.
10. `AGENTS.md`'s `## Versioning` section keeps its explanation and no longer
    enumerates the five files.
11. `python -m pytest -q` **exits 0** with 0 failures, and the new tests named in
    criteria 1–10 are present and passing. A pass *count* is not an acceptance
    property: it moves for unrelated reasons and has no recorded starting value
    at the time this criterion is read.

Criterion 9 is the one worth writing carefully: it is the only criterion that
catches this item's own failure mode, which is a config block that *looks* right
and describes a script that has moved on.

## Risks

- **The config can drift from the script.** Declaring the five files in
  `tcw-config.yaml` creates a second list, and a sixth version-bearing file added
  to `scripts/cut_version.py` would leave the config wrong. Criterion 9's test
  ties them together for this repository; **a project whose cut command has no
  such introspectable list has no equivalent protection**, and TCW cannot give it
  one. Named rather than solved.
- **A read-only verb about versions is inherently easy to confuse with
  `tcw --version`.** `versioning` reduces it rather than removing it. Accepted.
- **This is the second special-cased `work.*` block in two items.** Named ceiling:
  a *third* project-integration block is the signal to stop adding named keys and
  design a general mechanism, rather than adding a third parser that looks almost
  exactly like the first two.
- **Folding into v1.0.0 rewrites a tag.** Safe only while the tag is local;
  `skills/documentation-sync/scripts/unpushed-version.sh` must exit `0`
  immediately before the fold rather than being assumed from an earlier check.

## Notes

- Blocked by the documentation-entry item, and the block is real rather than
  procedural: this reuses `parse_documentation_entries`' shape, `documentation()`'s
  place on the ABC, and `tcw work docs`' `source` convention. All three now exist.
- **The `{bump}` token is deliberately inert.** TCW never expands it, because TCW
  never runs the command. It is there so the declared string documents where the
  bump argument goes, which a human or agent reading `tcw work versioning` needs.
- **Reviewed by `codex` before planning; twelve findings, and the review changed
  the item rather than decorating it.** Accepted: the withdrawn "silent
  wrongness" argument (High — the fallback names all five of this repo's file
  forms and says to grep, so the desynced-release scenario was invented); the
  partial-policy hole (High — a `files`-only block would have reported
  `source: config` with no command and suppressed a working fallback); blank
  `command`/`guard` and unknown keys going unvalidated; the verb renamed to
  `tcw work versioning`; criterion 7 naming a fixture directory instead of its
  test module; criterion 11 asserting a pass count. Narrowed: "a project without
  an introspectable list has **no** equivalent protection" is too absolute —
  such a project could expose a dry-run manifest or generate both sources from
  one declaration; what TCW cannot give it generically is protection *from shape
  validation alone*. Rejected: that `WorkStore` is the wrong home — the same
  objection applies verbatim to `lifecycle_policy()` and `documentation()`, both
  already there, and splitting node configuration onto a separate abstraction is
  a change to three existing methods, not this item.
- **Reason 1 was the case this item leaned on, and it did not survive contact
  with the file it described.** Worth stating plainly: the remaining case is
  structured discovery across harnesses plus consistency, which is real but
  thinner than the request assumed. If that is not enough, the right outcome is
  to discard this item rather than to build it on an argument already withdrawn.
- Every `file:line` above was re-resolved against the tree while writing this:
  `SKILL.md:124`, `AGENTS.md:47`, `scripts/cut_version.py:21-28` (five entries in
  `VERSION_FILES`), and `tests/test_plugin_manifests.py:36`
  (`test_five_version_fields_agree`).
