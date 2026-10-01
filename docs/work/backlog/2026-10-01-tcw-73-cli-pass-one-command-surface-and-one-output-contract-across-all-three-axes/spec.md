# Spec — CLI pass: one command surface and one output contract across all three axes

## Capability changes

This slice changes what users can run, so it changes the ledger. The planned
declaration, in the schema TCW-69 settled (Design 7 of its spec), is below. No
record is written at this stage.

```yaml
new:
  - cli/rely-on-one-output-contract     # stdout/stderr split, exit codes, slug input, --help standard
  - cli/list-connected-projects         # tcw projects list (replaces work/inspect-the-node-topology)
  - cli/validate-a-project              # replaces cli/validate-a-node
changed:
  - cli/declare-a-connected-projects-home-repository   # `projects:` key, no --refresh, "project" wording
  - cli/get-a-suggestion-for-a-mistyped-command        # examples name removed commands; new synonyms
  - cli/host-multiple-projects-in-one-repo             # `projects:` key, wording, Feature rename
  - cli/locate-tcw-storage-folders                     # no `work inbox path`
  - cli/point-tcw-at-a-project-i-already-have          # wording; drops the "publish" paragraph
  - cli/provision-declared-stores                      # --refresh removed; wording
  - cli/read-from-an-upstream-project                  # `projects.upstream`, `tcw projects list`, command list
  - cli/reference-a-tcw-object                         # Feature rename only
  - cli/run-from-a-git-worktree                        # wording; Feature rename
  - cli/scaffold-the-doc-trees                         # no per-axis init, no git requirement, stdout empty
  - taxonomy/add-a-term                                # stdin description, long flags, no git, prints the path
  - taxonomy/browse-the-term-forest                    # one path per line, --json
  - taxonomy/configure-the-taxonomy-store-location     # writes no longer commit or stage; Subject node -> project
  - taxonomy/declare-the-taxonomy-stores-home-repository  # Subject node -> project
  - taxonomy/federate-shared-vocabulary                # Feature rename only
  - taxonomy/read-a-term                               # no shorthand, --json
  - taxonomy/remove-a-local-term                       # `tcw validate` replaces the check commands; no git
  - taxonomy/search-terms                              # one path per line, --json
  - taxonomy/validate-the-taxonomy                     # runs as part of `tcw validate`
  - capabilities/add-a-capability                      # long flags, no git, prints the path; no Planning doc or Tracker field
  - capabilities/browse-capabilities-by-status         # one path per line, --local, --json
  - capabilities/configure-the-capabilities-store-location  # writes no longer commit or stage; Subject node -> project
  - capabilities/declare-the-capabilities-stores-home-repository  # Subject node -> project
  - capabilities/federate                              # `extends add|rm`; Feature rename
  - capabilities/override-inherited                    # no git paragraph; wording
  - capabilities/read-a-capability                     # no shorthand, --json
  - capabilities/remove-a-capability                   # no staging; records gate, not completion
  - capabilities/reset-an-override                     # wording
  - capabilities/search-capabilities                   # one path per line, --json
  - capabilities/set-a-capabilitys-status              # no git paragraph; `tcw validate`; fields list without Planning doc and Tracker
  - capabilities/validate-capabilities                 # runs as part of `tcw validate`
  - work/declare-which-documents-track-which-changes   # Subject node -> project
  - work/inspect-the-lifecycle-contract                # 3.0 flags (Design 2)
  - work/run-a-lifecycle-stage                         # only `stage prompt` remains
  - work/run-a-procedure                               # `tcw work procedure <id>`
  - work/tag-a-work-item                               # wording; `tags list` output
  - work/read-a-work-item                              # `show` prints the request and comments; `--json` layout (TCW-70 writes the record first)
removed:
  - cli/use-shorthand-to-read-an-item
  - cli/validate-a-node
  - work/inspect-the-node-topology
taxonomy:
  new: [project, project-registry]
  changed:
    - cli                                  # description: one command surface and output contract
    - configurable-component-store-location  # vocabulary node -> project
    - configure-skill                      # vocabulary node -> project
    - local-web-app                        # vocabulary node -> project
    - provisioned-component-stores         # vocabulary node -> project
    - setup-skill                          # vocabulary node -> project
    - upstream-project                     # description wording
  removed: [node, connected-project-registry]
```

Two groups of records are touched only by the "node" to "project" sweep and are
not listed path by path, because which of them survive is decided by TCW-70 and
TCW-77 before this slice runs (Design 0):

- `work/` records that TCW-70 keeps and that still say "node", carry `Subject:
  node` or `Feature: connected-project-registry` (today
  `configure-the-work-store-location`, `coordinate-a-cross-node-epic`,
  `declare-capability-changes-in-a-child-nodes-ledger`,
  `declare-the-work-stores-home-repository`, `reconcile-an-epic-rollup`,
  `view-the-board`; `delegate-a-request-to-a-child-node` and
  `escalate-a-request-to-the-parent-node` go with their commands in TCW-70). A surviving record whose **path**
  says "node" is renamed to say "project". The implement stage lists them by
  `grep -rliw node docs/capabilities/work` and records the result in the
  declaration file.
- The taxonomy entries `configurable-work-lifecycle` and `work-item/lifecycle-hook`,
  whose descriptions say "node", if TCW-70 keeps them.

Records owned elsewhere are deliberately absent: `skills/` and `plugin/` (TCW-74),
everything in `web/` (TCW-77), and every `work/` record for a command TCW-70 or
TCW-71 builds or removes (Design 0).

**`web/meta.yaml` cites `Feature: connected-project-registry` today, and that
value is TCW-77's.** TCW-77 sets it to `local-web-app`, the Feature that
describes the viewer, and plans to land before this slice. Removing the
`connected-project-registry` entry depends on that change, because a capability
citing a removed Feature fails `tcw validate`. **[Decision]** If this slice is
implemented first after all, it writes TCW-77's value, `local-web-app`, to that
one field and nothing else in `web/`, so the field never takes a value its owner
did not choose.

**`capabilities/detect-capability-drift` is not listed.** The ticket gives its
rewrite to this slice, but the owner moved it to TCW-70, together with the drift
wiring it describes (epic decision 2). Design 7.6 gives the content this slice's
surface expects the record to describe.

**Which `work/` records survive is not this slice's call.** TCW-70 decides each of
the 46 records under `docs/capabilities/work/`, and TCW-71 takes the tracker ones
if TCW-70 leaves them (epic decision 12). This slice then changes only the
command-surface wording of whichever survive, which is what the `work/` rows above
and the sweep below do.

**Records both slices change.** TCW-70's spec also changes
`cli/locate-tcw-storage-folders`, `cli/provision-declared-stores`,
`cli/scaffold-the-doc-trees`, `cli/get-a-suggestion-for-a-mistyped-command`,
`cli/reference-a-tcw-object`, `cli/validate-a-node`,
`work/run-a-lifecycle-stage`, `work/inspect-the-lifecycle-contract`,
`work/run-a-procedure`, `work/tag-a-work-item` and `work/read-a-work-item`, each for the behavior it
changes. The edits are sequential, not competing: TCW-70 lands first (Design 0),
and this slice then changes each record again for the surface it changes, so the
text after this slice describes the final command.

## Problem

TCW's command line grew one group at a time, and each group made its own choices.
Six problems follow.

1. **stdout and stderr carry the wrong things.**
   - `tcw init` prints its narration ("Scaffolded n dir(s)", "Node marker: …") on
     stdout (`tcw/cli.py:80-90`).
   - `tcw validate` prints "validate OK" on stdout and every problem on stderr
     (`tcw/cli.py:460-465`), so a script cannot capture the findings without also
     capturing the narration.
   - `tcw taxonomy add` prints "Added term …" (`tcw/taxonomy/cli.py:75`),
     `tcw capabilities add` prints "Added capability <path> (<id>)"
     (`tcw/capabilities/cli.py:91`), and `set`, `reset`, `rm` and `extends` each
     print a sentence on stdout (`tcw/capabilities/cli.py:116`, `:129`, `:142`,
     `:162-165`). An agent must parse prose to learn what was created.
   - `taxonomy list` prints an indented tree with markers
     (`tcw/taxonomy/cli.py:56-60`) and `capabilities list` prints
     `[status]\tpath\tname` (`tcw/capabilities/cli.py:54`); neither offers a
     machine-readable form.
2. **Exit codes mean almost nothing.** Outside `tcw work`, every failure is exit 1:
   a missing term (`tcw/taxonomy/cli.py:89-91`), an ambiguous reference
   (`:85-88`), a name collision, a refused removal. In `tcw work`, exit 2 is used
   in four places for misuse (`tcw/work/cli.py:2084`, `:3592`, `:4195`, `:4200`)
   and argparse's own usage errors; everything else is 1. A caller cannot tell
   "you typed it wrong" from "it does not exist" from "it exists but the rules
   refuse".
3. **The command surface is large and inconsistent.** Walking the parser that
   `build_parser()` builds (`tcw/cli.py:482-533`) finds 74 leaf commands, seven of
   them hidden parsers that exist only to print a migration message
   (`tcw/work/cli.py:5064-5073`). Inconsistencies include:
   - `tcw taxonomy extends add|rm <id>` (`tcw/taxonomy/cli.py:217-224`) against
     `tcw capabilities extends <id> [--rm]` (`tcw/capabilities/cli.py:323-326`);
   - `taxonomy list --local` (`tcw/taxonomy/cli.py:184`) against
     `capabilities list --local-only` (`tcw/capabilities/cli.py:284`);
   - short options on some commands (`taxonomy add -s/-p`,
     `capabilities add -s`, `work list -i`) and three spellings of one option
     (`-i`, `--incl-desc`, `--include-descendants`, `tcw/work/cli.py:4971-4973`);
   - option help missing on `capabilities list --status` and `--namespace`
     (`tcw/capabilities/cli.py:282-283`), `capabilities add --status` (`:300`),
     and `work list --status` (`tcw/work/cli.py:4967`);
   - a hidden rewrite that turns `tcw taxonomy <word>` into
     `tcw taxonomy show <word>` whenever the word is not a subcommand
     (`tcw/cli.py:536-543`), so a mistyped subcommand becomes "no such term"
     instead of a suggestion;
   - three commands that repeat `tcw init <axis>` (`tcw/taxonomy/cli.py:179`,
     `tcw/capabilities/cli.py:277`, `tcw/work/cli.py:4602`) and two that repeat
     part of `tcw validate` (`taxonomy check`, `capabilities check`), which already
     runs both checks (`tcw/validate.py:438-446` calling `_run_check`,
     `:242-265`).
4. **Taxonomy and capabilities commands change git state.** Every tree-store write
   stages what it wrote: `_stage` (`tcw/store/fs.py:2217-2219`), `_write_staged`
   (`:2221-2273`), `_rm` (`:2276-2278`), `_mv` (`:2280-2282`), and the shared
   config-file write (`:2210-2215`). Each refuses outside a git repository
   (`require_repository`, `tcw/store/fs.py:820-831`, reached through
   `_require_repository`, `:2103-2105`). `tcw init` refuses outside a git
   repository too (`tcw/cli.py:46-50`). The 3.0 rule is that TCW never changes git
   state. `tcw provision --refresh` fetches, checks out and fast-forward merges in
   a provisioned copy (`tcw/store/fs.py:4256-4282`), which is also a git state
   change. Help and messages name git throughout, for example `tcw init`'s help
   "scaffold component doc trees in this git repo" (`tcw/cli.py:487`) and the
   top-level handler's "git command failed" (`tcw/cli.py:574`).
5. **"Node" is still the word for a project.** The project registry, the hook
   variable `TCW_NODE_ROOT` (`tcw/work/hooks.py:64`), the provisioning target
   name `NODE_TARGET = "node"` (`tcw/store/fs.py:3829`), the command
   `tcw work nodes` (`tcw/work/cli.py:4627`) and 557 lines across `tcw/` that
   contain "node" as a whole word, case-insensitively, say "node". The config key `connected-projects`
   (`tcw/store/project.py:599-612`) keeps the other retired term, "connected
   project". The taxonomy has a `node` term and a `connected-project-registry`
   feature, cited in the `Subject` or `Feature` field of 25 capability records.
6. **Drift and validation are wired to the 2.x model.** `capabilities drift`
   follows each capability's `Planning doc` field into the 2.x work store and its
   tombstones (`_shipped_but_missing`, `tcw/capabilities/cli.py:200-254`), which
   the `detect-capability-drift` record describes as never making the
   capabilities axis depend on the work axis. The capability schema still accepts
   `Planning doc` and `Tracker` (`CAP_FIELDS`, `tcw/store/base.py:844-847`), two
   fields that point from the ledger into 2.x work items and tracker tickets.
   `tcw validate` runs the 2.x
   `capability_gate(in_progress=True)` over items in three status folders
   (`tcw/validate.py:268-294`), and has no notion of a warning: any problem is
   exit 1 (`tcw/cli.py:460-464`).

## Goals

1. **One output contract** for every command: stdout is the product, stderr the
   narration, every file written or removed is named on stderr, nothing prompts,
   long text comes from stdin.
2. **One exit-code table** (0–6), with every refusal, absence and misuse in every
   command mapped to it.
3. **One rule for naming a work item**, applied by one function that every command
   taking an item uses.
4. **One command surface** of 43 leaf commands, named `tcw noun [child-noun] verb`,
   with an explicit table from every 2.8 command to its 3.0 form and the slice that
   owns its behavior.
5. **A `--help` standard** that a test checks on every command.
6. **Taxonomy and capabilities on the same contract,** writing files only, with
   their check commands folded into `tcw validate`, and without the `Planning doc`
   and `Tracker` capability fields.
7. **`tcw validate` with one shape**: findings graded by severity and printed as
   the product, the taxonomy and capabilities checks inside it, one project per
   run, and `--remote`.
8. **`capabilities drift` on the same output contract** as `validate`.
9. **"Project" in place of "node"** in commands, config keys, the hook variable,
   code and the ledger.
10. **No git** in help or message strings, and no git state changes from any
    command this slice owns.

## Non-goals

- **The work model.** Stages, slugs, `advance`, gates, drift logic and the exit-code
  constants are TCW-69's. This slice prints what they return.
- **The behavior of the item commands.** What `new`, `list`, `show`, `path`, `edit`,
  `advance`, `discard`, `comment` and `rename` do to items is TCW-70's (filesystem)
  and TCW-71's (Jira); `tickets list` and `tickets adopt` are TCW-71's. This slice
  fixes their arguments and output (Design 1–4) and checks them (Design 10).
- **`tcw config show`** (TCW-72) and **`tcw serve`** (TCW-77) beyond following the
  contract. `tcw/serve/` is excluded from the rename sweep because TCW-77 rewrites
  it.
- **Text of prompts, procedures, skills and guides.** Git and "node" in that text
  belong to TCW-74 (prompts, skills) and TCW-75 (guides, README, and the written
  description of this contract). This slice keeps the documented-surface test
  green only for commands it removes itself (Design 9.4).
- **Suppressing known-unresolvable references** in `tcw validate`, the first ask of
  backlog item `2026-09-01-make-tcw-validate-usable-as-a-gate-suppressible-references-and-graded-exit-codes`.
  This slice delivers that item's second ask in part (a reference to a missing item
  becomes a warning, exit 0), and nothing more.
- **Migration.** The old-to-new command table in Design 2 is the input TCW-76 copies
  into the migration guide; no command translates old spellings.
- **A `--backend` option on `tcw init`.** Jira configuration is written by hand or
  through the `configure` skill (TCW-71, TCW-74).

## Design

### 0. Boundary with the sibling slices

The tickets do not say who builds each command. The owner settled the split
between this slice and TCW-70 (epic decision 2): TCW-70 removes every command
built on the 2.x store, wires `validate`'s work checks and drift, and rewrites
`detect-capability-drift`; this slice owns the surface of every command, the
taxonomy and capabilities commands, `tcw init <axis>`, `tcw projects list`, git
wording, and the "node" to "project" rename. This section applies that split.

**A command's _behavior_ belongs to the slice that gives it its 3.0
meaning; its _surface_ — name, arguments, help, stdout, stderr, exit codes —
belongs to this slice for every command** (epic decision 2). Design 1–4 are the
contract the other slices build to. This slice enforces it with one table-driven
test over every command (Design 10), and fixes any deviation in the command
itself.

| Area | Behavior owner |
| --- | --- |
| `tcw work` `new`, `list`, `show`, `path`, `edit`, `advance`, `discard`, `comment`, `rename` | TCW-70 (filesystem), TCW-71 (Jira mode of each) |
| `tcw work tickets list`, `tickets adopt` | TCW-71 |
| Removing the 2.x work commands that exist only on the 2.x work store (`inbox *`, `start`, `submit`, `rework`, `complete`, `drop`, `delete`, `tombstone add`, `scaffold`, `reconcile`, `delegate`, `escalate`, `stage gate`, `stage validate`) | TCW-70 |
| Re-pointing `stage prompt`, `procedure prompt`, `lifecycle`, `docs` and `tags` at TCW-69's configuration, keeping their current flags | TCW-70 |
| `validate`'s work checks (`reference_problems`, `stage_problems`, `records_problems(finished=False)`, the backend's own checks) and `capabilities drift`'s completed-work half (`drift_problems`), with the `detect-capability-drift` record | TCW-70 (epic decision 2) |
| Removing `tracker *` | TCW-71 |
| `tcw config show`; identity for `--mine` and `--assign-me` (through the backend's `current_user()` in Jira mode, epic decisions 1 and 17) | TCW-72 |
| `tcw serve` | TCW-77 |
| `tests/cli/scenarios/` | **TCW-73** (epic decision 14) |
| `evals/` | TCW-74 (epic decision 14) |
| Everything else: `init` (including `init <axis>`), `provision`, `validate`'s scope, severity and output, `projects list`, every `taxonomy` and `capabilities` command (including dropping the `Planning doc` and `Tracker` fields, epic decision 9), the final surface of the `tcw work` readers `stage prompt`, `lifecycle`, `docs`, `procedure`, `tags`, and `work path --handoff` (epic decision 18) | **TCW-73** |

**Sequencing.** This slice is implemented after TCW-70 and TCW-71 (epic
decision 2). Done earlier, its rename sweep would rename hundreds of "node"
mentions in 2.x code that TCW-70 then deletes (`tcw/store/fs.py` alone has 185
such lines, most in the 2.x work store), and its contract test would have no 3.0
item commands to check.

**The checks built on the 2.x store are TCW-70's** (epic decision 2). The ticket
gave this slice `validate`'s call to `records_problems` and `capabilities drift`'s
use of `drift_problems`; both, and the `detect-capability-drift` record, are
TCW-70's, because the code they replace (`_open_sidecar_problems`,
`tcw/validate.py:268-294`; `_shipped_but_missing`,
`tcw/capabilities/cli.py:200-254`) reads the store TCW-70 deletes. What stays here
is the surface of both commands: scope, severity, where findings are printed, and
the exit codes (Design 6, 7). TCW-71 removes `tracker_problems`
(`tcw/validate.py:384`) and adds the Jira checks.

**Ledger ownership follows behavior.** TCW-70 and TCW-71 update or remove the
records of the commands they build or remove, and TCW-70 decides each of the 46
`work/` records (epic decision 12). This slice rewrites the records in
Capability changes, changes the command-surface wording of every surviving
record, and sweeps "node" out of every record that survives. `tcw/work/templates.py`
and `tcw work scaffold` are deleted by TCW-70 (epic decision 13), so nothing here
touches them.

**Skills, agents and guides are not this slice's** (epic decision 3): TCW-75 owns
all of `skills/configure/`, TCW-74 every other skill and agent. Where this slice
renames a command, those slices update the text that names it (Design 9.4).

### 1. The output contract

1. **stdout is the command's product; stderr is narration.** Narration is what
   happened, which files were written or removed, warnings, and what to do next.
   A command that has no product prints nothing on stdout.
2. **Every file written or removed is named on stderr**, one line each, as
   `wrote <path>` or `removed <path>`, with the path relative to the current
   directory when it is inside it and absolute otherwise. A folder created empty is
   named as `created <path>/`. In another repository (delegation, TCW-70), the
   line also says the file is left uncommitted. This covers every axis, including
   `tcw-config.yaml` edits by `extends` and `tags`.
3. **Errors and warnings.** **[Decision]** An error line starts with
   `tcw <command words>: ` (for example `tcw work advance: `), and a warning line
   with `warning: `. Both go to stderr. One error per failing command.
4. **Nothing prompts.** No module under `tcw/` calls `input()` or reads `sys.stdin`
   except `tcw/stdin.py`, whose bounded read (`tcw/stdin.py:1-33`) already never
   waits on a stdin nobody closes.
5. **Long text comes from stdin**: the request on `new`, the text of `comment`, a
   term's description on `taxonomy add`, and a capability's body on
   `capabilities add`. **[Decision]** `taxonomy add` loses its positional
   description (`tcw/taxonomy/cli.py:189-190`), so there is one way in. `comment`
   with nothing on stdin is a usage error (2).
6. **`--json`.** **[Decision]** Where a command offers `--json`, stdout is exactly
   one JSON object with a top-level `"schema": 1`, and nothing else; a list is an
   array under a named key (`"items"`, `"terms"`, `"capabilities"`,
   `"projects"`, `"findings"`). The field set of a work item is TCW-70's, built
   from TCW-69's `Item` with `blocked-by` spelled as in `item.yaml`. Two fields
   follow from epic decision 16: `"priority"` is `null` when the Jira project has
   no priority field, and `"untracked"` is the list of linked parent or blocker
   ticket keys that have no item (always `[]` in filesystem mode).
   **[Decision]** The text form of `show` prints an `untracked:` line only when
   the list is not empty, so filesystem-mode output is unchanged by the field.
7. **Per-command stdout.** The table repeats the ticket's rows for the work
   commands as written, and adds the rest. **[Decision]** The added rows, and the
   `--dry-run` and `tags` details, are this spec's. The owner's output rule (epic
   decision 10) is that a list prints one identifier per stdout line, with details
   only through `--json`:

| Command | stdout |
| --- | --- |
| `work new`, `work tickets adopt`, `work rename` | the full slug; `new` prints a ticket key instead when it stopped after creating a ticket (rule 8) |
| `work advance`, `work discard` | the stage the backend reported after the move; with `--dry-run`, the target stage when the move would be allowed, nothing when refused |
| `work list` | one full slug per line, or `--json` |
| `work tickets list` | one ticket key per line, or `--json` (epic decision 10) |
| `work show` | the item's properties, its request text and its comments, newest first (rule 9), or `--json` |
| `work path` | the path |
| `work stage prompt`, `work procedure`, `work lifecycle`, `work docs`, `config show` | their text (`lifecycle`, `docs`: or `--json`) |
| `work edit`, `work comment`, `work tags add`, `work tags rm` | nothing |
| `work tags list` | one tag per line |
| `taxonomy add`, `capabilities add` | the new entry's qualified path |
| `taxonomy list`, `taxonomy search`, `capabilities list`, `capabilities search` | one qualified path per line, or `--json` |
| `taxonomy show`, `capabilities show` | the record, or `--json` |
| `taxonomy path`, `capabilities path` | the store folder |
| `taxonomy rm`, `taxonomy extends add/rm`, `capabilities set/reset/rm`, `capabilities extends add/rm` | nothing |
| `validate`, `capabilities drift` | one finding per line (Design 6.3, 7.3); nothing when clean |
| `projects list` | one project ID per line, current project first, or `--json` |
| `init`, `provision` | nothing (`provision` narrates its plan and every remote on stderr, `--dry-run` included) |
| `serve` | the URL |
| `--version` | `tcw <version>` |

8. **A command that stops after creating something still names it.** A refusal
   prints nothing on stdout, with one exception: when a `Refused` error carries a
   ticket key (epic decision 16), the command prints that key on stdout and then
   exits 3. This happens when `new` has created a Jira ticket but finds no single
   route to the request status (TCW-71's spec, Design 4.1 step 3), or when
   delegation into a Jira project cannot place the new ticket at the target's
   inbox (its Design 8 step 3), so the caller learns the name of what now exists.
   Delegation that does land at the target's inbox but stops there is not a
   refusal: it prints the ticket key and exits 0, as the ticket's exit-code table
   says (TCW-71's Design 8 step 4).
9. **`tcw work show` prints the whole item an agent needs to read**: its
   properties, its request, and its comments. The properties are TCW-70's item
   record (TCW-70 spec, Design 7.1), which deliberately leaves out the request
   and the comments; `show` adds them through the backend's `read_request` and
   `read_comments` (TCW-69 spec, Design 5.4), so it reads the same way in both
   modes. The stage prompts rely on this: five of TCW-74's prompts read the
   request or the latest comment through `show`.
   - **[Decision] Text form**, in this order: one `key: value` line per record
     field (`untracked:` only when not empty, rule 6); a blank line and a line
     `request:` followed by the request text indented by two spaces, or `request: none` when
     `read_request` returns `None`; then, when there are comments, a blank line
     and `comments:`, followed by each comment newest first as a line
     `- <at> <author>` (the author left out when `None`, `<at>` in
     `YYYY-MM-DDTHH:MM:SSZ`) and its text indented by two spaces. All comments
     are printed: there is no limit option, because the newest comes first and
     a caller that wants only it reads up to the second unindented `- ` line.
   - **[Decision] `--json`**: `{"schema": 1, "item": <record>, "request":
     <text or null>, "comments": [{"at": …, "author": … or null, "text": …}, …]}`,
     comments newest first. `list --json` carries records only, under `"items"`,
     without request or comments, so listing never makes one request per item
     to read comments in Jira mode.

### 2. The command surface

The 3.0 surface has 43 leaf commands. Naming is `tcw noun [child-noun] verb`;
`lifecycle`, `docs` and `procedure` stand without a verb.

**Old to new.** Every 2.8 command, from the parser walk, and its 3.0 form. "Owner"
is the behavior owner (Design 0).

| 2.8 | 3.0 | Owner |
| --- | --- | --- |
| `tcw --version` | unchanged | 73 |
| `tcw init [component…] --id --work-path --taxonomy-path --capabilities-path` | `tcw init [<axis>…] --id <id> --work-path --taxonomy-path --capabilities-path`; works outside a git repository; stdout empty | 73 (what `work` scaffolds: 70) |
| `tcw provision [--component] [--refresh] [--dry-run]` | `tcw provision [--component <axis>] [--dry-run]` | 73 |
| `tcw validate [path] [--no-recurse]` | `tcw validate [--remote]` | 73 (checks from 69, 70, 71, 72) |
| `tcw serve [--port] [--no-open]` | unchanged | 77 |
| — | `tcw config show [--origin]` | 72 |
| `tcw work nodes` | `tcw projects list [--json]` | 73 |
| `tcw taxonomy <path>`, `tcw capabilities <path>` (rewritten to `show`) | removed | 73 |
| `tcw taxonomy init`, `capabilities init`, `work init` | removed: `tcw init <axis>` | 73 |
| `tcw taxonomy list [--local]` | `tcw taxonomy list [--local] [--json]` | 73 |
| `tcw taxonomy add <name> [<description>] [-s] [-p] [--kind] [--vocab]` | `tcw taxonomy add <name> [--slug] [--parent] [--kind] [--vocab]`, description on stdin | 73 |
| `tcw taxonomy show <path>` | `tcw taxonomy show <path> [--json]` | 73 |
| `tcw taxonomy path`, `rm <path>` | unchanged | 73 |
| `tcw taxonomy search <query>` | `tcw taxonomy search <query> [--json]` | 73 |
| `tcw taxonomy check`, `tcw capabilities check` | removed: `tcw validate` | 73 |
| `tcw taxonomy extends add/rm <id>` | unchanged | 73 |
| `tcw capabilities list [--status] [--namespace] [--local-only]` | `tcw capabilities list [--status] [--namespace] [--local] [--json]` | 73 |
| `tcw capabilities show <path>` | `tcw capabilities show <path> [--json]` | 73 |
| `tcw capabilities path`, `set`, `reset`, `rm` | unchanged in shape | 73 |
| `tcw capabilities add <path> [<name>] [-s/--status]` | `tcw capabilities add <path> [<name>] [--status]`, body on stdin | 73 |
| `tcw capabilities search <query>` | `tcw capabilities search <query> [--json]` | 73 |
| `tcw capabilities extends <id> [--rm]` | `tcw capabilities extends add <id>`, `extends rm <id>` | 73 |
| `tcw capabilities drift` | unchanged in shape; TCW-69's rule (Design 7) | 73 |
| `tcw work inbox list/path/show/accept` | removed: inbox-stage items, `list --stage inbox` (filesystem); `tickets list`, `tickets adopt` (Jira) | 70, 71 |
| `tcw work tracker list/show/import/create/link/claim/release/unlink/sync` | removed; `tcw work tickets list`, `tickets adopt <KEY>` | 71 |
| `tcw work reconcile` | removed: Jira hierarchy, or `list --parent` | 70 |
| `tcw work delegate`, `escalate` | removed: `new --project <id>` | 70, 71 |
| `tcw work tombstone add`, `delete`, `scaffold` | removed | 70 |
| `tcw work start`, `submit`, `rework`, `complete`, `drop` | `tcw work advance <slug> [--to <stage>] [--force --reason <text>] [--dry-run]`; `tcw work discard <slug> --reason <text>` | 70 |
| `tcw work stage gate` | removed: `advance --dry-run` | 70 |
| `tcw work stage validate` | removed | 70 |
| the hidden `tcw work stage <id>` parsers | removed | 73 |
| `tcw work new <title> [--priority N] [--effort] [--complexity] [--blocked-by] [--tag] [--epic] [--parent] [--initiative]` | `tcw work new <title> [--project <id>] [--stage inbox] [--priority <name>] [--effort] [--complexity] [--tag] [--assignee] [--assign-me] [--parent] [--blocked-by]`, request on stdin | 70, 71 (identity: 72) |
| `tcw work list [--status] [--tag] [--all] [-i]` | `tcw work list [--stage <stage>] [--parent <slug>] [--assignee <name>] [--mine] [--all] [--json]` | 70, 71 |
| `tcw work show <slug> [--json]` | unchanged | 70, 71 |
| `tcw work path [<slug>]` | `tcw work path [<slug> [<stage> [--next / --handoff]]]` | 70 (`--handoff`: 73, epic decision 18) |
| `tcw work edit <slug> …` (incl. `--initiative`, `--type`, integer `--priority`) | `tcw work edit <slug> [--title] [--priority <name>] [--effort] [--complexity] [--tag] [--untag] [--assignee] [--assign-me] [--parent] [--blocked-by] [--unblocked-by] [--blocks]` | 70, 71 |
| `tcw work rename <slug> <new-slug>` | `tcw work rename <slug> <new-name>` (the part after the date or key) | 70, 71 |
| — | `tcw work comment <slug>`, text on stdin | 70, 71 |
| `tcw work lifecycle [<slug>] [--json] [--directive] [--phase] [--stage] [--transition]` | `tcw work lifecycle [--stage <stage>] [--json]` | 73 (re-pointed by 70) |
| `tcw work docs [--json]` | unchanged | 73 (re-pointed by 70) |
| `tcw work stage prompt <stage> [<slug>] [--no-exec]` | unchanged | 73 (re-pointed by 70; text: 74) |
| `tcw work procedure prompt <id> [<slug>] [--no-exec]` | `tcw work procedure <id> [<slug>] [--no-exec]` | 73 (re-pointed by 70; text: 74) |
| `tcw work tags list/add/rm` | unchanged | 73 (re-pointed by 70) |

Decisions in this table beyond the ticket, each **[Decision]**:

1. **No hidden parsers for removed commands.** Today's migration parsers
   (`tcw/work/cli.py:5064-5073`) go. A removed word gets argparse's ordinary error
   and, through the existing suggestion table (`tcw/cli_suggest.py`), a pointer:
   `start`, `submit`, `rework` and `complete` suggest `advance`. Removal words
   (`drop`, `delete`) stay unanswered, as the suggestion module already rules.
2. **The `tcw <axis> <path>` shorthand goes** (`tcw/cli.py:536-543`), so a mistyped
   subcommand always reaches the suggestion line. `DEFAULT_SUBCOMMAND` and
   `SUBCOMMANDS` in each module go with it.
3. **`capabilities list --local-only` becomes `--local`**, matching taxonomy.
4. **`lifecycle` drops its slug** (another project's policy is read in that project),
   **`--directive`** (`stage prompt` is the agent's instruction), **`--phase`** and
   **`--transition`** (3.0 has no transitions). It prints the stage table with each
   stage's enabled state and its `prompt`, `pre` and `post` bindings.
5. **`path` keeps its no-slug form**, printing the work folder, so the three axes'
   `path` commands match (`cli/locate-tcw-storage-folders`). It gains
   **`--handoff`**, because TCW-69's `path` returns a handoff path
   (TCW-69 spec, Design 4.10) and the ticket's form has no way to ask for one.
   The owner confirmed `--handoff` as part of this slice's surface (epic
   decision 18).
6. **`list` has no `--tag` filter**, following the ticket and TCW-69's `Query`,
   which has no tag field. This is a reduction from 2.8 (`tcw/work/cli.py:4968`);
   see Notes.
7. **Unknown stage, procedure or axis names** are usage errors (2) whose message
   lists the valid names. The 2.8 behavior of answering an artifact name with the
   stage that writes it goes with the 2.x artifact names.

### 3. Naming a work item

One function, `resolve_item(text, context) -> (Slug, backend)`, is used by every
argument and option that names an item: the `<slug>` positional of `show`, `path`,
`edit`, `advance`, `discard`, `comment`, `rename`, `stage prompt`, `procedure`, and
the values of `--parent`, `--blocked-by`, `--unblocked-by` and `--blocks`.

1. **Jira key first, in Jira mode only.** **[Decision]** When the backend is Jira and
   the text matches `^[A-Z][A-Z0-9_]*-[1-9][0-9]*$`, it is resolved through the
   backend's `lookup` (TCW-69 spec, Design 5.3). A `None` answer is not found (4).
   No folder can collide: a Jira-mode folder is `<KEY>-<title words>` and
   `title_words` never returns an empty string (TCW-69 spec, Design 1.3). In
   filesystem mode a key-shaped text is read as a bare folder name, and is simply
   not found.
2. **Otherwise `Slug.parse(text, current_project)`** (TCW-69 spec, Design 1.2):
   `project/folder` or a bare folder. Anything else is a usage error (2).
3. **Exact match only.** The folder must exist exactly. No prefix matching, no
   old-name aliases, no case folding: anything else is not found (4).
4. **Another project.** **[Decision]** A full slug naming another project is
   resolved through the project registry (`ProjectRegistry`,
   `tcw/store/base.py:191`), the same way 2.8 reaches a project today. An unknown
   project ID, one no registry entry declares, is not found (4). A project that is
   declared but not present on this machine is exit 5, and the message names
   `tcw provision`; delegating into such a project (`new --project`,
   `edit --blocks`) is refused (3), because it is the first delegation condition
   failing (epic decision 4). Reading (`show`, `path`) works
   across projects. **Writing another project's item is refused (3)** and the
   message says to run the command in that project, except where a slice defines
   the write: `new --project` and `edit --blocks` (TCW-70's delegation
   conditions). A value given to `--parent` or `--blocked-by` is a reference stored
   on _this_ item, so it may name another project.
5. **Printing.** Every slug TCW prints is the full `project/folder` form. The same
   holds for the slug handed to hooks: `TCW_SLUG` is the full slug, and hooks and
   generate scripts run with the project root as their working directory (epic
   decision 11). TCW-69 sets both, including the `generate` binding environment
   (TCW-69 spec, Design 6.5 and Design 8's binding lists); this slice only checks
   the result. How 2.x hook variables map onto 3.0's
   is by meaning, not by position, and is TCW-76's mapping.

The function is specified here and built by TCW-70, which is the first slice whose
commands take items; TCW-71 adds the key branch. Design 10's tests check it across
every command.

### 4. Exit codes

TCW-69 puts the codes in `tcw/exit.py` and their exception classes in
`tcw/errors.py` (`UsageError` 2, `Refused` 3, `NotFound` 4, `Unreachable` 5,
`MovedWithoutNote` 6, `BackendError` 1), outside `tcw/work/` from the start so
that the taxonomy and capabilities commands can raise them without importing from
`tcw/work/` (epic decision 8; TCW-69 spec, Design, module list). This slice only
uses them. `Refused` may carry a ticket key (epic decision 16; Design 1.8).

The top-level handler (`tcw/cli.py:546-578`) catches these classes, prints
`tcw <command words>: <message>` and returns the class's code. A bare `ValueError`
or YAML error keeps today's exit 1. The `CalledProcessError` branch
(`tcw/cli.py:563-578`) goes: with the tree stores no longer staging (Design 8),
the git commands left are reads that already handle their own failures and
`provision`'s clone, which reports its own.

The final table:

| Code | Meaning | Includes |
| --- | --- | --- |
| 0 | ok | `validate` with only warnings or unresolved lines; delegation that stopped at the target's inbox; a `--dry-run` that would succeed |
| 1 | error | config errors (including a personal file setting a shared key, TCW-72); no TCW project here; a port already in use; Jira errors other than not-found; `validate` findings at error level; any `capabilities drift` finding; any `provision` failure |
| 2 | usage | argparse errors; an unknown stage, procedure or axis name; a malformed slug; a value outside its scale or registry; an ambiguous reference; a Jira-only command or option in filesystem mode, and a filesystem-only option in Jira mode; empty stdin where text is required |
| 3 | refused | a gate; no stage; a name collision; delegation conditions, including delegating into a declared project that is not on this machine; a move Jira's workflow does not offer, or several transitions into the target status that TCW cannot narrow to one (it prefers the one whose screen has no field other than a comment, and otherwise refuses and lists them; epic decision 5, built by TCW-71); an explicit priority in a Jira project with no priority field; a ticket created but not placed (Design 1.8); a write to another project's item; a removal something still references; `capabilities reset` with no override to drop |
| 4 | not found | an item, term, capability, tag or ticket that does not exist; a project ID nothing declares |
| 5 | unreachable | the Jira backend could not be reached; a project that is declared but not present on this machine (epic decision 4) |
| 6 | the item moved, but something after the move failed | a `post` hook, or recording the trace comment (TCW-69 spec, Design 6) |

**[Decision]** The rows beyond the ticket:

- **No TCW project here** is 1, as a missing config file is a config error.
- **A value that fails validation is 2; a refusal that depends on other records is
  3.** So a `Subject:` reference that does not resolve on `capabilities set` is 2
  (a bad value), and removing a term another term still names is 3.
- **`validate --remote` in filesystem mode is 2**, as a Jira-only option, and
  `new --stage inbox` in Jira mode is 2, as a filesystem-only one.
- **`provision` failures are 1**, whatever the cause. Code 5 is kept for the work
  backend and for a declared project missing from this machine, because telling a
  network failure from refused authentication in a cloning tool's output means
  parsing its text.
- **`validate` does not exit 5 for a missing project.** A declared project that is
  not on this machine is an `unresolved` finding (Design 6.2), because `validate`
  reports what it could not check rather than stopping at it. Exit 5 applies to a
  command that needs to read that project to do its job.
- **Check commands exit 1 on a finding.** `validate` grades its findings
  (Design 6); every `drift` finding counts, as today
  (`tcw/capabilities/cli.py:192-195`).

`advance` already returns an `Outcome` with its code (TCW-69 spec, Design 6). The
command prints the outcome's stage on stdout whenever the item moved, including
exit 6.

### 5. The `--help` standard

Checked by walking the parser `build_parser()` returns, as
`tests/test_cli_help_coverage.py` already does for positionals.

1. Every command and command group has a one-line `help` and a `description`.
2. Every leaf command's description ends with two lines: `Prints: …` (its stdout,
   in the words of Design 1.7) and `Writes: …` (the files or records it changes,
   or `nothing`).
3. Every leaf command has an epilog with at least one example line starting
   `  tcw `, and every example parses through `build_parser()` without error.
4. Every positional and every option has non-empty help.
5. **[Decision]** Options are long-form only, apart from `-h`. Each option has one
   spelling. A repeatable option takes one value per use; comma-separated values
   are not split. Choices are shown in the help.
6. `tcw --help` ends with the exit-code table and one sentence stating the
   stdout/stderr rule, so the contract is discoverable from the command itself.
7. No help text contains a word from the git list (Design 9.1) or the word "node".

### 6. `tcw validate`

**[Decision] Scope: the current project only.** `[path]` and `--no-recurse` go,
and with them the walk over descendant projects (`tcw/cli.py:452-459`). 3.0 shows
one project at a time (TCW-77 serves one project; `list` has no
`--include-descendants`), and a reference into another project is already checked
by resolving it (6.1.6). `validate`'s internal `target` selector stays, because
`tcw serve` calls it (`tcw/serve/__init__.py:171`), and it gains work items
(6.4).

#### 6.1 What runs

Offline (plain `tcw validate`), in this order. Nothing here touches the network.

1. **Configuration.** `tcw-config.yaml` parses; TCW-69's `parse_work_config`
   problems; TCW-72's personal-layer problems and its "local file is tracked"
   warning (TCW-72 owns those checks).
2. **The project graph**, as today (`tcw/cli.py:404-450`). Graph problems are
   errors, and stop the run as today. A `TCW_PROJECT_<ID>` override in effect is
   narration on stderr. A declared project that cannot be reached here is an
   `unresolved` line. A registry warning is a warning.
3. **Files.** YAML well-formedness and `tcw://` link resolution over the stores
   (`tcw/validate.py:386-433`), as today.
4. **Taxonomy and capabilities**: each store's `check()`
   (`TaxonomyStore.check`, `tcw/store/base.py:724`; `CapabilitiesStore.check`,
   `:953`), as `_run_check` already runs them (`tcw/validate.py:242-265`). These
   are the old `taxonomy check` and `capabilities check`.
5. **Work, from the backend** (wired by TCW-70 and TCW-71). Each backend supplies
   one offline check over what it keeps locally (TCW-70: `item.yaml` shape and
   folder names; TCW-71: the key in the folder name against `item.yaml`'s
   `ticket`). **[Decision]** It is a function of the backend module, not a twelfth
   operation on `WorkBackend` (whose eleven are fixed by epic decision 1), because
   only `validate` calls it and it reads only local files.
6. **Work, from the model** (wired by TCW-70, Design 0), in filesystem mode:
   - `reference_problems` over every item (`Query(all=True)`) (TCW-69 spec,
     Design 9);
   - `stage_problems` (TCW-69 spec, Design 9);
   - `records_problems(..., finished=False)` over every item at a non-terminal
     stage (TCW-69 spec, Design 7), in place of `capability_gate(in_progress=True)`
     (`tcw/validate.py:268-294`).

   In Jira mode these three need each item's stage or links, which live in Jira,
   so they run under `--remote` instead.
7. **Verdict rounds.** **[Decision]** Added by this slice: each verdict stage of
   each item whose latest round is `invalid` (`current_verdict`, TCW-69 spec,
   Design 4.7-4.8) gives a warning naming the round file. Rounds are files in
   both modes, so this runs offline in Jira mode too. Older rounds are history and
   are not checked. `advance` already refuses on an invalid latest round; the
   warning says so before anyone tries, and it is what the viewer shows after
   saving a round (6.4).

With `--remote` (Jira mode only; 2 in filesystem mode): everything above, plus the
three model checks of 6.1.6, plus TCW-71's workflow-compatibility and field checks.
A network failure is exit 5. Its output follows 6.3 like every other check: only
findings are printed, never a line per passed check, and a move TCW could not
check (no sample ticket in its source status) is itself a `warning` finding
(epic decision 10). A closing line on stderr may count what was checked.

The 2.x checks for retention (`tcw/validate.py:370-371`) and tracker configuration
(`:384`) are gone by the time this slice runs (Design 0).

#### 6.2 Severity

| Severity | Examples | Exit |
| --- | --- | --- |
| `error` | malformed YAML; a broken `tcw://` link; a taxonomy or capabilities check problem; a config problem; a records problem (TCW-69's mid-work check reports only real faults) | 1 |
| `warning` | an invalid latest verdict round; a reference to a missing item, or to a project nothing declares (TCW-70 spec, Design 10); a stage ahead of its artifacts; a registry warning; a tracked personal file; a `--remote` move that could not be checked; a capability record still carrying `Planning doc` or `Tracker` (Design 8.6) | 0 |
| `unresolved` | a reference into a project not reachable here; a declared project not present here | 0 |

#### 6.3 Output

**[Decision]** Findings are the product of `validate`, so they go to **stdout**, one
per line, as `<severity>: <where>: <message>`, where `<where>` is a file path (with
`:<line>` when known) or a slug. A clean run prints nothing on stdout. stderr
carries the narration (overrides in effect) and a closing count, for example
`2 errors, 1 warning, 0 unresolved`. `--json` is not offered; the line form is
stable and easy to split.

#### 6.4 Validating one object (for `tcw serve`)

Today the internal selector `ValidationTarget(axis, ref)` runs `validate`'s rules
for one taxonomy entry or capability (`tcw/validate.py:311-319`, `:351-355`), and
`tcw serve` calls it after each save (`tcw/serve/__init__.py:168-173`). TCW-77
needs it for item files too. There is no command-line form; it is a library
entry point.

**[Decision]** With `axis="work"` and `ref` an item folder, it runs, for that
item only, the checks of 6.1 that need no network in either mode:

- YAML well-formedness of the item's files, and `tcw://` links in its Markdown
  files (6.1.3);
- the backend's offline check for that folder (6.1.5);
- an invalid latest round in any of its verdict stages (6.1.7);
- the records check on its `capabilities.yaml`, `records_problems(...,
  finished=False)`, when its stage is not terminal (6.1.6);
- the reference check on its `parent` and `blocked-by`, for references within
  this project only (6.1.6).

The stage and references are what the caller passes: the selector takes an
optional `Item`, which the viewer already holds from the read or update it has
just made. Without one, filesystem mode reads `item.yaml`, and Jira mode skips
the two stage- and link-dependent checks and returns an `unresolved` finding
saying so, so that the selector itself never contacts Jira. References into
other projects are left to a full `tcw validate`, because resolving them can need
another project's backend, and so the network. Findings come back as 6.3's lines,
graded as in 6.2; the caller decides what to do with them (TCW-77 shows them and
never undoes the save).

### 7. `tcw capabilities drift`

1. **Two kinds of finding**, both on stdout:
   - **unreviewed**: an inherited capability whose status is the upstream default
     and was never ruled on locally (`unreviewed_inherited`, kept from
     `tcw/capabilities/cli.py:184`). **[Decision]** This half stays; it belongs to
     the capabilities axis alone.
   - **from completed work**: TCW-69's `drift_problems(items)` (TCW-69 spec,
     Design 7) over the items at the completion stage, read with the backend's
     `list` and each item's `<item>/capabilities.yaml`. It reports `drift`,
     `ambiguous` and `unchecked` findings.
2. **Behavior is TCW-70's** (Design 0): it replaces `_shipped_but_missing` and the
   `Planning doc` lookup with `drift_problems`. This slice removes the field from
   the capability schema (Design 8.6) and TCW-76 removes it from existing records
   (epic decision 9). The rest of this section is the surface this slice fixes.
3. **Output**: one finding per line, `<kind>: <path or term>: <message>`, with
   `<kind>` one of `unreviewed`, `drift`, `ambiguous`, `unchecked`. Clean prints
   nothing on stdout. Any finding exits 1.
4. **A project with no work component** reports only the unreviewed kind, and says
   on stderr that completed-work drift was not checked.
5. **Jira mode** reads the completed items from Jira, so it needs the network; an
   unreachable Jira is exit 5. The record says so. **[Decision]** This is
   accepted rather than worked around: in Jira mode Jira alone knows which items
   are completed, and keeping a local copy of that would give the fact a second
   owner. The unreviewed half needs no network, so it is still reported, on
   stdout, before the exit 5.
6. **The `detect-capability-drift` record** (rewritten by TCW-70, Design 0) should
   say: drift compares the
   ledger with the record changes that completed work items declared, newest
   declaration first; it therefore reads the work axis, through whichever backend
   the project uses; same-day disagreements are reported as ambiguous; items
   completed before 3.0, which kept no declaration file, are not covered;
   inherited-but-unreviewed capabilities are still reported.

### 8. Taxonomy and capabilities never touch git

1. **Tree-store writes write files only.** In `FsTreeStore`, `_stage`,
   `_rm` and `_mv` become plain file operations, `_write_staged` keeps its
   rollback of what it created but stages nothing, and the config-file write
   (`tcw/store/fs.py:2210-2215`) writes without staging. `require_repository`,
   `_require_repository` and `NOT_A_REPOSITORY` (`tcw/store/fs.py:818-831`,
   `:2103-2105`) go: nothing needs a repository once nothing is staged.
2. **`taxonomy rm` decides from the disk, not from git.** Today it asks
   `git ls-files` which files under the term's folder are tracked, refuses a
   folder whose files are untracked ("`git add` them first"), and finds nested
   terms among the tracked files (`FsTaxonomyStore.remove`,
   `tcw/store/fs.py:2568-2600`). It was written that way because the removal was a
   `git rm`. With removal a plain delete, nested terms are found by reading the
   term folders on disk, and an untracked term is removed like any other. Reading
   git stays only where it is a check, such as worktree locator anchoring.
3. **`tcw init` works outside a git repository** (`tcw/cli.py:46-50` goes). This also
   matches TCW-72, which has `init` write the `.gitignore` entry "or skip with a
   notice outside a git repository". What `init` writes for the work axis is
   TCW-70's (its status-folder ignore rules, `tcw/cli.py:88-90`, go with the
   status folders).
4. **`tcw provision` loses `--refresh`.** **[Decision]** Bringing an existing copy
   up to date fetches, checks out and merges (`tcw/store/fs.py:4256-4282`), which
   is a git state change; the epic leaves keeping provisioned stores fresh to the
   project's own hooks. Obtaining a missing repository by cloning stays: the epic
   names it as the one thing `provision` still does.
5. **Messages say "files".** "The deletion is staged, not committed" and similar
   sentences in records and messages are rewritten.
6. **The `Planning doc` and `Tracker` capability fields go** (epic decision 9).
   Both point from the ledger into the work axis: `Planning doc` at a 2.x work
   item, which drift followed (Problem 6), and `Tracker` at a tracker ticket,
   which 3.0 replaces with the Jira backend. 3.0 links a capability to work the
   other way, through `<item>/capabilities.yaml` (epic decision 19).
   - Both leave `CAP_FIELDS` (`tcw/store/base.py:844-847`), so
     `capabilities add` and `capabilities set --field` refuse them as unknown
     fields, a usage error (2), through `_validate_fields`
     (`tcw/store/fs.py:3314-3318`). No help text or record names them as
     settable.
   - **[Decision]** `CapabilitiesStore.check` reports a record that still carries
     either field as a **warning**, naming `docs/migration-guide-2.8-to-3.0.0.md`,
     instead of the "unknown field" error every other key outside `CAP_FIELDS`
     gets (`tcw/store/fs.py:3530-3532`). TCW-76 removes the fields from records
     (epic decision 9), and 65 records in this repository carry one today
     (`grep -rlE "^(Planning doc|Tracker):" docs/capabilities`, all
     `meta.yaml`). An error would turn `tcw validate` red in this repository, and
     in every user's, from this slice until each runs the migration. That is not
     only cosmetic here: this repository's own configuration runs `tcw validate`
     as a gate (`tcw-config.yaml:111-114`, the 2.x `complete` transition's `pre`
     command, which TCW-76 carries into 3.0). No test validates this
     repository's own records (the suite builds fixtures in temporary
     folders), so the gate is the thing that would break. A warning keeps it at
     exit 0 and still names every record. So the two fields are **accepted and
     warned about** until TCW-76 removes them, never errors.
   - Reading a record with either field works as before: only writes
     (`_validate_fields`) and `check` consult `CAP_FIELDS`, and a write of other
     fields leaves an existing `Planning doc` or `Tracker` line in place for
     TCW-76 to remove, because `set` merges the given fields into the record's
     existing ones (`_merge_meta`, `tcw/store/fs.py:3420-3428`). After TCW-76 there is nothing left to warn about.
   - `tcw/serve/__init__.py:22` imports `CAP_FIELDS`; TCW-77, which rewrites
     `tcw/serve/`, follows the smaller set.

### 9. Git words and "node" in the code

1. **The git word list** is `git`, `commit`, `push`, `pull`, `worktree`, `trunk`,
   `branch`, matched case-insensitively as whole words (plurals and `-ed` forms
   included), the list TCW-74 uses for prompt text.
2. **[Decision] What is swept**: every help string, and every string literal under
   `tcw/` that a user can see, which the test approximates as every string constant
   containing a space, docstrings and comments excluded. Exceptions:
   - the filename `.gitignore`;
   - `tcw provision`'s messages, because cloning a repository is the one git
     action the epic keeps and its failures must say what failed.

   `tcw/serve/` is excluded (TCW-77 rewrites it).
3. **"Project" replaces "node"** in the project sense, everywhere under `tcw/`
   except `tcw/serve/`:
   - the command (`tcw work nodes` becomes `tcw projects list`, Design 2);
   - **[Decision]** the config key `connected-projects` becomes `projects`, with the
     same `parent`, `children` and `upstream` entries, and the optional `jira`
     block TCW-71 adds to an entry (its Design 8 step 1). The old key is a config error
     (1) whose message names `docs/migration-guide-2.8-to-3.0.0.md`, as TCW-69 does
     for removed `work` keys;
   - the hook variable: no `TCW_NODE_ROOT` remains (TCW-69's runner sets
     `TCW_PROJECT_ROOT`; if TCW-70 kept any 2.x hook code, this slice removes the
     variable from it);
   - the provisioning target name `NODE_TARGET = "node"` (`tcw/store/fs.py:3829`)
     and its user-visible "node at …" text (`:4120`);
   - identifiers: `find_node_root`, `find_node`, `node_root`, `parent_node`,
     `child_nodes`, `descendant_nodes` and the rest become `project` names;
   - **the tree sense**: `FsTreeStore` calls a term or capability folder a "node"
     (`tcw/store/fs.py:2284-2290`); those become "entry", so that a search for
     "node" under `tcw/` finds nothing.
4. **The documented-surface test stays honest.** `tests/test_documented_cli_surface.py`
   fails when live Markdown names a command, or a flag of one, that does not
   exist (`tests/test_documented_cli_surface.py:1`, `:215-217`). TCW-70 gives it
   a temporary allowance: a named list of removed commands and keys, with a guard
   test asserting each entry really is removed (TCW-70 spec, Design 14; epic
   decision 6). This slice adds its own removals and renames to that list rather
   than editing other slices' text: `taxonomy check`, `capabilities check`, the
   three `<axis> init`, `work nodes`, `procedure prompt`,
   `capabilities extends <id> --rm`, `capabilities list --local-only`,
   `provision --refresh`, `validate --no-recurse`, the `tcw <axis> <path>`
   shorthand, and the `connected-projects` key. Each new entry falls under the
   same guard test. TCW-74 and TCW-75 shrink the list as they rewrite skills and guides, and
   TCW-76's "validate clean" step requires it to be empty before 3.0.0 is cut
   (epic decision 6).
5. **Taxonomy.** **[Decision]** The `node` term is replaced by `project`
   (vocabulary), and the `connected-project-registry` feature by `project-registry`.
   Every entry and capability citing either is updated (Capability changes).

### 10. Enforcement: one contract test, and the shell scenarios

`tests/test_cli_contract.py` is table-driven: one row per leaf command naming its
expected stdout shape, the files it may write, and its exit code for a set of
cases. It runs each command as a subprocess in a fixture project built by the
CLI itself, in filesystem mode, and against a stubbed Jira backend for the
Jira-only commands. A command registered without a row fails the test, so a
command added later (TCW-72's `config show`, TCW-77's changes to `serve`) must
add its row.

**`tests/cli/scenarios/` belongs to this slice** (epic decision 14). It holds 14
reviewed but unimplemented black-box scenario specifications whose subject is
exactly this contract: exit codes, which stream a message lands on, and
composing commands in a shell (`tests/cli/README.md`). Most describe 2.x
behavior (status folders, worktree merge-back, cross-node epics). **[Decision]**
The plan gives each scenario a disposition (rewrite to 3.0, or delete),
defaulting to delete where the contract test already covers it or 3.0 removes
its subject. `evals/` is TCW-74's (the same decision), including its use of
commands this slice renames.

### 12. Release notes and changelog

This slice adds its own `docs/release-notes/upcoming/<slug>.md` and
`docs/changelogs/upcoming/<slug>.md`, as every change does (`CLAUDE.md`,
Versioning). Each starts with a `##` heading and has no text before it: only
TCW-75's release-notes entry may open with text before its first `##`, because it
is the 3.0.0 introduction (epic decision 15). The entries say what a 2.8 user
notices: the renamed and removed commands (pointing at the migration guide for the
full table), findings on stdout, the exit-code table, taxonomy and capability
edits no longer staged, `provision --refresh` gone, `connected-projects` renamed
to `projects`, and the two retired capability fields.

### 11. Abstraction litmus test and harness compatibility

| Operation | Verdict |
| --- | --- |
| Output contract, exit codes, `--help` | **CLI layer.** No storage involved. |
| `resolve_item` | **Model plus backend.** `Slug.parse` is the model's; the key branch is the backend's `lookup`, one of the eleven operations (epic decision 1). A non-filesystem store implements both. |
| `--mine`, `--assign-me` | **Backend**: `current_user()`, one of the eleven operations (epic decisions 1 and 17), behind TCW-72's identity resolution. |
| Retired capability fields | **Abstract**: a change to `CAP_FIELDS` and `CapabilitiesStore.check`, which any store implements. |
| Cross-project resolution | **Through `ProjectRegistry`** (`tcw/store/base.py:191`), the existing abstract interface. |
| `validate` 6.1.4 | **Abstract**: `TaxonomyStore.check` and `CapabilitiesStore.check`. |
| `validate` 6.1.5 | **Per backend**, offline. Jira implements it over local folders; a future backend supplies its own. |
| `validate` 6.1.6, 6.1.7, drift | **Model** over the backend's `list` and TCW-69's `RecordsReader`; rounds are shared layout files in both modes. |
| `validate` 6.4 (one object) | **Model plus shared layout**, given the `Item` by its caller, so no backend-specific code and no network in either mode. |
| `validate` 6.1.3 (YAML, `tcw://` scan) | **Filesystem adapter**, as today: the taxonomy and capabilities stores are filesystem-only, and git owns the technical record in both work modes. |
| Removing staging from tree stores | **Filesystem adapter** detail. |

Harness compatibility: every requirement here is carried by the `tcw` CLI, which
behaves the same under Claude and Codex. Nothing depends on a hook, injected
context or a slash command.

## Acceptance criteria

All criteria are pytest tests unless they name a command. "Fixture project" means a
temporary directory initialised with `tcw init --id fx` in filesystem mode; Jira
cases use a stubbed backend whose `lookup`, `list`, `read`, `create` and
`set_stage` are scripted, or TCW-71's fake Jira (`tests/work/jira/fake.py`, TCW-71
spec, Design 15.1) where the case needs Jira's own answers.

1. **Surface.** Walking `build_parser()` finds exactly the 43 leaf commands of
   Design 2's 3.0 column, and none of these: any `<axis> init`, `taxonomy check`,
   `capabilities check`, `work nodes`, `work stage gate`, `work stage validate`,
   `work stage <stage-name>`, `work procedure prompt`, `work inbox`, `work tracker`,
   `work start`/`submit`/`rework`/`complete`/`drop`/`delete`, `work tombstone`,
   `work scaffold`, `work reconcile`, `work delegate`/`escalate`.
2. **Shorthand gone.** `tcw taxonomy lst` exits 2 and stderr suggests `list`; it
   does not print "no such term".
3. **Suggestions.** `tcw work start x` exits 2 and stderr names `tcw work advance`.
   `tcw work drop x` exits 2 with no suggestion.
4. **Help standard.** For every leaf command: `help` and `description` are
   non-empty; the description contains a line starting `Prints:` and one starting
   `Writes:`; the epilog has at least one line starting `  tcw ` and each such line
   parses through `build_parser()`; every argument and option has help; no option
   string is a single dash plus one letter other than `-h`; no option has two
   spellings. `tcw --help` contains each of the codes 0–6 and the words "stdout"
   and "stderr".
5. **No git words in help or messages.** No help text matches the git list. A test
   reads every `.py` file under `tcw/` except `tcw/serve/`, collects string
   constants that contain a space (docstrings excluded), and finds no git-list word
   outside `.gitignore` and the provisioner's functions.
6. **No "node".** `grep -rniE "node" tcw --include=*.py --exclude-dir=serve` prints
   nothing, and `grep -rn TCW_NODE_ROOT tcw` prints nothing.
7. **Config key.** A fixture whose `tcw-config.yaml` has `connected-projects:` makes
   `tcw validate` exit 1 with a message naming
   `docs/migration-guide-2.8-to-3.0.0.md`; the same graph under `projects:` passes,
   and `tcw projects list` prints the current project's ID first, then its
   connected projects, one per line.
8. **stdout per command.** In the fixture project:
   - `tcw work new "A b"` prints exactly one line, `fx/<folder>`, matching
     `^fx/[0-9]{4}-[0-9]{2}-[0-9]{2}-a-b$`;
   - `tcw work advance <slug>` prints exactly `spec`;
   - `tcw work advance <slug> --dry-run` prints the target stage and moves nothing;
     refused, it prints nothing and exits 3;
   - `tcw work edit <slug> --priority high` and `echo hi | tcw work comment <slug>`
     print nothing;
   - after `printf 'Need X\n' | tcw work new "A b"` and two comments `one` then
     `two`, `tcw work show <slug>` prints the record lines, then `request:` with
     `Need X`, then `comments:` with `two` before `one`; `tcw work show <slug>
     --json` has a `"request"` containing `Need X` and `"comments"`
     with `two` first; an item created with no stdin shows `request: none` and
     `"request": null`;
   - `tcw work list` prints full slugs only, one per line;
   - `tcw taxonomy add Widget` prints `widget`; `tcw capabilities add ns/do-a-thing`
     prints `ns/do-a-thing`;
   - `tcw taxonomy rm widget`, `tcw capabilities set ns/do-a-thing --status
     Supported`, `tcw init`, and `tcw taxonomy extends add <id>` print nothing;
   - `tcw validate` on a clean fixture prints nothing on stdout and exits 0;
   - every `--json` output parses as one JSON object with `"schema": 1`.
9. **Every written file is named.** For each writing command in criterion 8, every
   path created, changed or removed under the fixture (compared by listing and
   content before and after) appears on stderr.
10. **Exit codes.** In the fixture project:
    - `tcw work show fx/no-such` → 4; `tcw work show a/b/c` → 2;
    - `tcw work show <first 10 characters of a real folder>` → 4 (no prefix
      matching);
    - after `tcw work rename <slug> other`, `tcw work show <old slug>` → 4;
    - `tcw work advance <slug> --to nonsense` → 2;
    - a failing `pre` hook on spec → 3; a failing `post` hook → 6 with the stage on
      stdout; with `advance` run from a subfolder of the fixture, a `pre` hook
      records `TCW_SLUG` as `fx/<folder>` and its working directory as the
      fixture root;
    - `tcw taxonomy add Widget` twice → 3 the second time;
    - `tcw taxonomy show nosuch` → 4; `tcw capabilities show nosuch` → 4;
    - removing a term another term names in `relatesTo` → 3;
    - `tcw capabilities set ns/do-a-thing --field Subject=nosuch` → 2;
    - `tcw capabilities reset ns/do-a-thing` on a local capability → 3;
    - `tcw work tickets list` → 2; `tcw validate --remote` → 2;
    - `tcw work comment <slug>` with empty stdin → 2;
    - any command run in a directory with no `tcw-config.yaml` above it → 1;
    - with the stubbed Jira backend raising `Unreachable`, `tcw work list` → 5, and
      `tcw work new "x" --stage inbox` → 2;
    - `tcw capabilities set ns/do-a-thing --field "Planning doc=x"` → 2, and the
      same with `Tracker=x` → 2.
11. **Slug input and Jira-mode output.** With the stub's `lookup("TCW-9")`
    returning `TCW-9-a-thing`, `tcw work show TCW-9` succeeds and any slug it
    prints is `fx/TCW-9-a-thing`; `tcw work show TCW-10` (lookup returns `None`)
    → 4. With the stub's `create` raising `Refused` that carries the key `TCW-11`,
    `tcw work new "x"` prints exactly `TCW-11` on stdout and exits 3. With the
    stub's item having no priority and one untracked blocker `EXT-4`,
    `tcw work show TCW-9 --json` has `"priority": null` and
    `"untracked": ["EXT-4"]`; in filesystem mode `"untracked"` is `[]`.
    Against TCW-71's fake Jira, `tcw work tickets list` prints one ticket key per
    line and nothing else.
12. **Cross-project.** In a fixture with two projects present and a third
    declared but absent, `tcw work show other/<folder>` succeeds from the first
    project; `tcw work advance other/<folder>` → 3 and the message names the other
    project; `tcw work show ghost/x` (a project nothing declares) → 4;
    `tcw work show absent/x` → 5 and the message names `tcw provision`;
    `tcw work new "x" --project absent` → 3.
13. **Nothing prompts.** No `.py` file under `tcw/` other than `tcw/stdin.py` calls
    `input(` or reads `sys.stdin`.
14. **Folding.** `tcw validate` in a fixture whose taxonomy has a dangling
    `relatesTo` prints an `error:` line naming it and exits 1; one whose capability
    has an unresolvable `Subject` likewise.
15. **Validate severity.**
    - An item whose `blocked-by` names a missing item in this project gives a
      `warning:` line and exit 0.
    - A `blocked-by` into an unreachable project gives an `unresolved:` line and
      exit 0.
    - An item at spec whose `capabilities.yaml` has an unknown key gives an
      `error:` line naming the file, and exit 1.
    - An item at spec declaring a `new:` path that does not exist yet gives no line.
    - A completed item whose `capabilities.yaml` is malformed YAML is reported by the
      file scan, and not by the records check.
    - A declared project absent from this machine gives an `unresolved:` line and
      exit 0, not exit 5.
    - An item at review whose latest round has no `judges` gives a `warning:` line
      naming the round file, and exit 0; an older invalid round under a newer
      valid one gives no line.
    - A capability record carrying `Planning doc:` or `Tracker:` gives a `warning:`
      line naming the record and `docs/migration-guide-2.8-to-3.0.0.md`, and exit 0.
    - In Jira mode against TCW-71's fake Jira, `tcw validate --remote` prints no
      line for a passed check, and a needed move whose source status has no sample
      ticket gives a `warning:` line; exit 0 when that is the only finding.
    - The closing count is on stderr, not stdout.
16. **Drift.**
    - A completed item declaring `new: [x/y]` while `x/y` is absent prints
      `drift: x/y: …` and exits 1.
    - A later completed item declaring `removed: [x/y]` clears it (exit 0, no
      stdout).
    - An inherited capability never ruled on prints `unreviewed: …`.
    - With no work component, only unreviewed findings appear, and stderr says
      completed-work drift was not checked.
    - With the stubbed Jira backend raising `Unreachable`, it exits 5.
    - No code path under `tcw/capabilities/` reads a `Planning doc` field.
17. **No git from taxonomy and capabilities.** Inside a temporary git repository,
    running `taxonomy add`, `taxonomy rm`, `taxonomy extends add` and `rm`,
    `capabilities add`, `set`, `reset`, `rm`, `extends add` and `rm`, and `tcw init`
    leaves `git rev-parse HEAD` unchanged and `git diff --cached --quiet` true.
    `taxonomy rm` removes a term whose files were never added to git. The same
    commands succeed in a directory that is not a git repository.
18. **Provision.** `tcw provision --refresh` exits 2. A declared store already
    present makes `tcw provision` contact nothing (as today) and print nothing on
    stdout.
19. **Readers.** `tcw work procedure create-work` prints the procedure's text;
    `tcw work lifecycle --json` parses with `"schema": 1` and lists the stage table's
    enabled stages; `tcw work lifecycle --directive` exits 2.
20. **Contract test coverage.** `tests/test_cli_contract.py` fails when a leaf
    command exists that has no row (checked by adding a dummy subparser in the
    test).
21. **Ledger and taxonomy.** Each `new` path in Capability changes exists and is not
    `Missing`; each `removed` path and the `node` and `connected-project-registry`
    entries are gone; no capability record's `Subject` or `Feature` names either
    removed entry (`grep -rnwE "node|connected-project-registry"
    docs/capabilities --include=meta.yaml` prints nothing).
22. **The documented-surface test passes**, and the full test suite passes.
23. **Release notes.** This slice's files under `docs/release-notes/upcoming/` and
    `docs/changelogs/upcoming/` exist, and the first non-blank line of each starts
    with `## `.
24. **Validating one item.** `validate(root, target=ValidationTarget("work",
    <folder>))` on a fixture item at spec returns a finding for a broken `tcw://` link in
    its spec, for an invalid latest review round, and for an unknown key in its
    `capabilities.yaml`, and none for a problem in another item. With a Jira-mode
    configuration and no `Item` passed, it returns an `unresolved` finding for the
    skipped checks and contacts nothing (the stub records no call).

### Coverage

| Design rule | Criteria |
| --- | --- |
| 0 Boundary, sequencing | 1, 20 (the table names every command) |
| 1 Output contract | 8, 9, 11, 13, 15 (stdout and stderr split) |
| 2 Surface | 1, 2, 3, 19 |
| 3 Naming an item, `TCW_SLUG` | 10, 11, 12 |
| 4 Exit codes | 10, 11, 12, 16, 18 |
| 5 Help | 4 |
| 6 Validate | 7, 14, 15, 24 |
| 7 Drift | 16 |
| 8 No git in taxonomy and capabilities; retired fields | 10, 15, 17, 18 |
| 9 Git words, node, docs test, taxonomy | 5, 6, 7, 21, 22 |
| 10 Contract test | 20 |
| 12 Release notes | 23 |

## Risks

- **This is large for one item.** It touches every command, the tree stores' write
  path, the surface of `validate` and drift, the project registry, the shell
  scenarios and about 40 ledger records. Mitigation: the plan builds it in three phases,
  each leaving the test suite passing, in this order: (a) contract, help standard, exit-code mapping,
  `resolve_item` checks and the contract test; (b) the taxonomy and capabilities
  pass, including removing staging, and the top-level commands (`init`,
  `provision`, `validate`, `projects list`); (c) the "node" sweep with the taxonomy
  and ledger renames. **[Decision, owner 2026-10-01: phases of one item, not child items]** The plan
  uses these phases, in this order, because each part can be verified on its own and (c) is mostly
  mechanical churn that is easiest to review alone.
- **Other slices build to a contract they do not own.** If TCW-70 or TCW-71
  deviates, this slice finds out late. Mitigation: their specs cite Design 1–4 of
  this one, and the contract test (Design 10) catches any deviation before this
  slice completes.
- **Two slices reshape `validate` and `drift` in turn.** TCW-70 wires their work
  checks with today's output, and this slice then moves findings to stdout and
  grades them. A test written by TCW-70 against stderr breaks here. Mitigation:
  TCW-70's tests assert on the finding text, not the stream, where they can; this
  slice updates the rest.
- **Removing staging changes what users see in `git status`.** 2.8 users got their
  taxonomy and capability edits staged for them; in 3.0 they appear as unstaged
  changes. Mitigation: the release notes say so, and TCW-75's opt-in git example
  shows a `post` hook that commits.
- **Dropping recursion from `validate`** means a monorepo root no longer checks
  every child project in one run. Mitigation: each child is validated in its own
  directory; cross-project references are still checked by resolving them.
- **Renaming taxonomy entries and the config key churns many files** and breaks any
  external `tcw://` link to `cli/validate-a-node` or `work/inspect-the-node-topology`.
  Mitigation: `tcw validate` reports every broken link; TCW-76's guide covers
  rewriting live references.
- **The rename sweep can over-reach** into a "node" that means something else.
  Mitigation: the only other meanings under `tcw/` are the tree folder sense
  (renamed to "entry", Design 9.3) and Node.js (only in `tcw/serve/`, excluded).

## Notes

- Reconciled with the epic's cross-slice decisions on 2026-10-01.
- **Settled by the owner's cross-slice decisions** (numbers refer to the epic's
  decisions record of 2026-10-01):
  - the boundary with TCW-70, the sequencing after TCW-70 and TCW-71, and the move
    of `validate`'s work checks, the drift wiring and the
    `detect-capability-drift` record to TCW-70 (decision 2; Design 0);
  - the backend interface has eleven operations, including `current_user()` for
    `--mine` and `--assign-me`, so `validate`'s offline backend check stays a
    module function (decisions 1 and 17; Design 6.1.5, 11);
  - a declared project not on this machine is exit 5, and delegating into one is
    exit 3 (decision 4; Design 3.4, 4). This was the conflict with TCW-70's
    Decision 2;
  - the exception classes are in `tcw/errors.py` from TCW-69 on (decision 8;
    Design 4);
  - this slice removes `Planning doc` and `Tracker` from the schema, TCW-76 from
    records (decision 9; Design 8.6);
  - output rules are this slice's: `tickets list` prints keys, `validate --remote`
    prints findings only and an unchecked move is a finding, and every finding of
    `validate` is on stdout (decision 10; Design 1.7, 6.1, 6.3). This settles the
    three output conflicts with the TCW-70 and TCW-71 drafts;
  - `TCW_SLUG` is the full slug and hooks run in the project root (decision 11;
    Design 3.5);
  - `tests/cli/scenarios/` is this slice's and `evals/` is TCW-74's
    (decision 14; Design 10);
  - only TCW-75's release-notes entry opens with text before its first `##`
    (decision 15; Design 12);
  - `Item.untracked`, a `priority` that may be `None`, and `Refused` carrying a
    ticket key (decision 16; Design 1.6, 1.8);
  - `work path --handoff` is this slice's surface (decision 18; Design 2);
  - every spec uses `<item>/capabilities.yaml` whatever a ticket says
    (decision 19). This settles the sibling tickets that said
    `spec/capabilities.yaml`;
  - the documented-surface allowance list, its guard test, and who shrinks it
    (decision 6; Design 9.4).
- **Decisions made in this spec, for the owner to confirm.** Each is marked
  **[Decision]** above:
  1. error lines start `tcw <command words>: `, warnings `warning: `;
  2. `taxonomy add` takes its description from stdin only;
  3. every `--json` output is one object with `"schema": 1`;
  4. the stdout rows beyond the ticket (Design 1.7), including `advance --dry-run`
     printing the would-be stage;
  5. `show`'s text form prints `untracked:` only when it is not empty;
  6. no hidden parsers for removed commands; `start`, `submit`, `rework` and
     `complete` suggest `advance`;
  7. the `tcw <axis> <path>` shorthand is removed;
  8. `capabilities list --local-only` becomes `--local`;
  9. `lifecycle` drops its slug, `--directive`, `--phase` and `--transition`;
  10. `work list` has no `--tag` filter (see the owner questions);
  11. unknown stage, procedure and axis names are usage errors listing the valid
      names;
  12. a Jira key is resolved first, in Jira mode only;
  13. another project's item can be read but not written, except `new --project`
      and `edit --blocks`;
  14. the exit-code rows beyond the ticket (Design 4), including `validate`
      reporting a missing project as `unresolved` rather than exiting 5;
  15. options are long-form only with one spelling each;
  16. `validate` checks the current project only. A monorepo root validates each
      child in its own directory; this keeps one project per run, as everywhere
      else in 3.0;
  17. each backend's offline check is a module function, not a twelfth operation;
  18. `validate`'s findings are graded error / warning / unresolved;
  19. drift keeps the unreviewed-inherited kind, and in Jira mode needs the
      network for its completed-work half;
  20. `provision --refresh` is removed;
  21. the git-word sweep's two exceptions (`.gitignore`, `provision` messages);
  22. `connected-projects` becomes `projects` (see the owner questions for the
      name);
  23. the tree sense of "node" becomes "entry";
  24. the `node` term becomes `project`, `connected-project-registry` becomes
      `project-registry`, and capability paths that say "node" are renamed;
  25. a record still carrying `Planning doc` or `Tracker` is accepted with a
      warning, not an error, until TCW-76 migrates it, because this repository's
      own configuration gates on `tcw validate`;
  26. each scenario under `tests/cli/scenarios/` defaults to deletion unless the
      plan finds it covers something the contract test does not;
  27. the plan builds this item in the three phases named under Risks (one item,
      not child items: owner, 2026-10-01);
  28. `tcw work show`'s text and `--json` layout for the request and comments
      (Design 1.9), with no limit option, and `list --json` without them;
  29. `validate`'s one-object selector covers work items with the offline checks
      listed in Design 6.4, takes the `Item` from its caller, and leaves
      cross-project references to the full run (asked for by TCW-77);
  30. a new offline check: an invalid latest verdict round is a warning
      (Design 6.1.7);
  31. if this slice lands before TCW-77, it writes TCW-77's chosen `Feature`
      value, `local-web-app`, to `web/meta.yaml` and touches nothing else in
      `web/` (Capability changes).
- **The ticket's own points**, answered: exit 6 is widened as TCW-69 decided
  (Design 4); `capabilities drift` reads `<item>/capabilities.yaml`, through TCW-69's
  `drift_problems` (Design 7, wired by TCW-70); the `detect-capability-drift`
  record's new content is given in Design 7.6 (written by TCW-70); `validate` calls
  `records_problems(finished=False)` (Design 6.1.6, wired by TCW-70); the rename
  covers commands, the config key, `TCW_NODE_ROOT` and code (Design 9.3).
- **Questions only the owner can answer.**
  1. **`work list --tag`.** 2.8 can filter the list by tag
     (`tcw/work/cli.py:4968`), and TCW-69's `Query` has no tag field, so 3.0
     cannot. Recommendation: ship 3.0.0 without it and add a `tags` field to
     `Query` later if it is missed, since both backends could support it (Jira
     labels) and adding it is not a breaking change.
  2. **Names.** `projects:` replaces the `connected-projects:` key, and
     `project-registry` replaces the `connected-project-registry` Feature; every
     user's config file changes. Recommendation: keep both names; they match the
     word "project" used everywhere else in 3.0.
- **Conflicts with sibling specs that the decisions do not settle.** None
  remain. TCW-70's spec now gives an undeclared project ID exit 4 and a declared
  but absent one exit 5 (its Design 2.2), as Design 3.4 does, and TCW-71's spec
  now prints `tickets list` keys and `validate --remote` findings only. One
  sequencing note:
  - **`procedure prompt`.** TCW-70 keeps today's spelling; this slice renames it to
    `procedure` afterwards. Not a clash, but TCW-70 should not write new docs or
    tests that name `procedure prompt`.
- **Changes other slices need** (nothing has been posted to their tickets):
  - **TCW-70:** build `new`, `list`, `show`, `path`, `edit`, `advance`, `discard`,
    `comment` and `rename` to Design 1–4, including `resolve_item` (Design 3);
    supply the
    filesystem backend's offline check as a module function; list in its
    documented-surface allowance the commands it removes (already planned).
  - **TCW-71:** add the key branch to `resolve_item`; supply the Jira backend's
    offline check; remove `tracker_problems` from `tcw/validate.py`; use
    "project", never "node", in new code.
  - **TCW-72:** its config errors exit 1 and its warnings use the `warning:` form;
    `init` writing `.gitignore` outside git relies on Design 8.3. It owns `--mine`
    and `--assign-me`, through `current_user()` in Jira mode.
  - **TCW-74:** skills, agents, prompts and `evals/` name the 3.0 commands in
    Design 2, and shrink the documented-surface allowance. Prompts that need the
    request or the latest comment read them from `tcw work show` (Design 1.9),
    where the newest comment comes first.
  - **TCW-75:** documents the contract from Design 1, 4 and 5, owns everything in
    `skills/configure/`, and shrinks the allowance.
  - **TCW-76:** the migration guide carries Design 2's old-to-new table, the
    `connected-projects` key, `TCW_NODE_ROOT`, `provision --refresh`,
    `validate [path] --no-recurse`, and removing `Planning doc` and `Tracker` from
    capability records; its "validate clean" step is where the allowance must be
    empty.
  - **TCW-77:** `tcw/serve/` is excluded from the sweep, so its rewrite must say
    "project" only; `validate`'s `target` selector stays for it; `serve` follows
    Design 1 and 4, and its import of `CAP_FIELDS` (`tcw/serve/__init__.py:22`)
    follows the smaller set. It owns all of `docs/capabilities/web/`, including
    `web/meta.yaml`'s `Feature`, which it sets to `local-web-app`; this slice
    removes the `connected-project-registry` entry only once that is done. It
    calls the one-object selector of Design 6.4 for item files, passing the
    `Item` it holds.
- **Related backlog item.**
  `2026-09-01-make-tcw-validate-usable-as-a-gate-suppressible-references-and-graded-exit-codes`
  asked for graded exit codes; Design 6.2 grades findings so that a missing
  reference no longer fails the run. Its suppression ask is untouched.
- **Grounding.** Every `file:line` above was read on the epic branch at commit
  `c6f3ef49`, and re-checked at `ec698d46`, which changes nothing under `tcw/` or
  `tests/`. TCW-69's modules (`tcw/work/model.py` and the rest) are not in the
  tree yet; claims about them cite TCW-69's spec, not code.
- **Driving this item.** This item's implementation edits `tcw/`. From `implement`
  onwards, the repository's board is driven by editing files, per `CLAUDE.md`.
  While TCW-70 to TCW-77 are in flight the 2.x board is edited by hand, and this
  slice's Jira ticket is moved by hand to In Progress, In Review and Done as its
  item moves; read-only views may use a released 2.8 `tcw` installed outside the
  checkout (epic decision 7).
