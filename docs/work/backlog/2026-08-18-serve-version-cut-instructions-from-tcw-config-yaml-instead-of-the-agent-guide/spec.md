# Spec — Serve version-cut instructions from tcw-config.yaml instead of the agent guide

## Capability changes

**New.** One capability record under `docs/capabilities/work/`:

- *Declare how this project cuts a version* — a project names its version-bearing
  files, its cut command, and its guard test in `tcw-config.yaml`; TCW validates
  them and `tcw work version` prints them.

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
or move the file, and TCW silently stops knowing how the project cuts a version —
and then falls through to a *generic manual ritual* that, for this repository,
would bump `pyproject.toml` and miss four other files.

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

1. **Silent wrongness is worse than silent absence.** When the doc-sync heading
   went missing, the gate did not fire and the omission was visible in a diff.
   When the `## Versioning` heading goes missing, `cut-version.md` does not stop —
   it proceeds to a generic ritual that bumps the wrong set of files and produces
   a *desynced release*, which `references/cut-version.md` itself calls "its own
   kind of bug". The failure is a bad outcome, not a missing one.
2. **The layering.** `work.lifecycle`, `work.tags`, and now `work.documentation`
   are configuration TCW owns and validates. Version-cut facts are the only
   remaining project-level integration point still obtained by scraping prose.
3. **It is the same shape a second time.** The pattern — pure parser, advisory
   problems, a method on `WorkStore`, a read-only verb — exists now and is
   cheaper to reuse than to re-argue.

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

All three keys optional; a block declaring none is the same as no block.
`{bump}` is the one substitution, replaced with `patch` / `minor` / `major` /
an explicit version by whoever runs it — **TCW does not run it**, so the token is
documentation of the command's shape rather than a template TCW expands.

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

**`tcw work version [--json]`**, read-only, prints what the node declared.

```
$ tcw work version
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

**The name collides in appearance with `tcw --version`, and that was weighed.**
They sit at different levels — a global flag reporting *TCW's* version versus a
`work` subcommand reporting *the project's* version-cut configuration — and the
subcommand never prints a bare version string, so a mistaken invocation produces
obviously-not-a-version output rather than a plausible wrong answer. The
alternatives (`version-cut`, `release`) were rejected: the first is the only
hyphenated subcommand in a CLI of twenty single-word verbs, and the second reads
as though it performs a release.

### Why no stage binding

The documentation item put entries into `plan` and `implement` because the gate
fires *during* the lifecycle. This one does not: `SKILL.md`'s own table places
the version offer **after `complete`**, and `tcw work stage <id>` on a completed
item is refused by the status check (`tcw/work/cli.py`), correctly.

So `tcw work version` is the whole delivery surface. No prompt changes, no
`{{tcw:…}}` span, and **no risk to the byte-identity guarantee** the sibling item
established — which is the strongest argument for keeping it out of the prompts,
since that guarantee is now pinned by `tests/fixtures/prompt_fallback/`.

### The skill

`references/cut-version.md` Step 0 is rewritten: ask `tcw work version --json`
first; on `source: config` use the declared command (and the guard after it);
on `source: agent-guide`, or outside a TCW node, fall back to the current
`## Versioning`-section behavior unchanged. `SKILL.md:124`'s parenthetical is
updated to match.

### This repository

`work.version` gets the five files, the command, and the guard. `AGENTS.md`'s
`## Versioning` section keeps its prose and loses the enumerated file list,
pointing at `tcw work version` for it — the same split the documentation entries
took.

### Abstraction litmus test

| Operation | Verdict |
| --------- | ------- |
| Read a node's version-cut configuration | **Model.** `tcw-config.yaml` is node configuration; a tracker-backed node has one exactly as a filesystem node does, precisely as `work.lifecycle`, `work.tags`, and `work.documentation` already do. |
| `tcw work version` | **Model.** Reads node configuration and prints it. Composes no store path and does not touch the work store at all. |

Nothing here is a filesystem trick. **Running** the declared command would be one
— it is a local shell concern, exactly what `lifecycle_policy`'s own docstring
excludes from the interface — and it is a stated non-goal.

### Harness compatibility

Entirely in the `tcw` CLI plus a skill reference both harnesses read. No hooks,
no dynamic context, no slash command.

## Acceptance criteria

1. `tcw validate` reports a problem naming the offending key for each of: a
   non-mapping `version:`, a non-string `command`, a non-string `guard`, a
   non-list `files`, a non-string or blank entry in `files`, an absolute path, a
   path escaping the node, and a duplicate path.
2. `tcw validate` exits 0 on a `version:` block whose declared files do not exist
   on disk, and on a block declaring only one of the three keys.
3. `tcw work version` prints the declared command, guard, and every file.
4. `tcw work version --json` parses and reports `"source": "config"`, with
   `files` in declaration order.
5. On an unconfigured node, `tcw work version --json` reports
   `"source": "agent-guide"` with `command`, `guard` null and `files` empty, and
   exits 0; `tcw work version` writes nothing to stdout and explains on stderr.
6. `tcw work version` writes nothing — asserted by hashing every path under the
   work store and the node config before and after, not by `git status`.
7. **Stage output is untouched.** `tests/test_prompt_fallback.py` and
   `tests/fixtures/lifecycle_baseline/` both pass **without re-capture**. This
   item adds no prompt text, so any movement means something unintended happened.
8. `skills/documentation-sync/references/cut-version.md` Step 0 names
   `tcw work version` and treats the `## Versioning` section as the fallback;
   `SKILL.md:124`'s parenthetical agrees with it.
9. This repository's `tcw-config.yaml` declares all five version-bearing files,
   the command, and the guard; `tcw work version` prints them; and the five paths
   it declares are **exactly** the keys of `VERSION_FILES` in
   `scripts/cut_version.py` — asserted by a test that reads both, so the config
   cannot drift from the script it describes.
10. `AGENTS.md`'s `## Versioning` section keeps its explanation and no longer
    enumerates the five files.
11. `python -m pytest -q` reports more passes than the count at this item's start
    and 0 failures.

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
- **`tcw work version` reads like `tcw --version`.** Weighed above; the mitigation
  is that its output can never be mistaken for a version string.
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
  bump argument goes, which a human or agent reading `tcw work version` needs.
- Every `file:line` above was re-resolved against the tree while writing this:
  `SKILL.md:124`, `AGENTS.md:47`, `scripts/cut_version.py:21-28` (five entries in
  `VERSION_FILES`), and `tests/test_plugin_manifests.py:36`
  (`test_five_version_fields_agree`).
