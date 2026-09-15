# Plan — Declare and provision the work store's home repository

Six code tasks, then one documentation block. The suite is green at every task
boundary: nothing reads the declaration until Task 3, and nothing invokes the
provisioner until Task 5.

The riskiest change — Task 3, the precedence rule inside `FsWorkStore.open` — is
deliberately third, after both the parser and the provisioner exist and after
their tests are written, so it is the only moving part when it lands.

## Task 1 — The declaration: model, parser, and validation

**Creates/modifies**

- `tcw/store/base.py` — add `StoreNotProvisioned(ValueError)` beside the existing
  exceptions (after `SidecarError`, `:49-52`); add a frozen
  `RepositoryDeclaration` dataclass (`url`, `ref`, `path`, `checkout`) and
  `parse_repository_declaration(raw, where, problems)` following the
  problem-accumulating shape `parse_lifecycle_policy` already uses.
- `tcw/validate.py` — surface declaration problems in the node scan.
- `tests/test_store_provisioning.py` (new) — parser cases only.

**Rules the parser enforces** (spec §1): `url` required and a non-empty string;
`ref` optional string; `path` optional, relative, no `..`, no leading `/`;
`checkout` optional string; any other key under `repository` is a problem.

**Proves it.** New tests: a valid declaration parses with defaults applied; each
of the five rejections above yields exactly one problem naming the offending key;
`tcw validate` on a node with a bad declaration exits non-zero and prints it.
Acceptance criterion 10.

## Task 2 — The FS provisioner

**Creates/modifies**

- `tcw/store/base.py` — `ProvisionResult` (frozen: `available`, `path`, `action`,
  `detail`) and the `StoreProvisioner` ABC (`describe`, `is_available`,
  `ensure_available(*, refresh=False, dry_run=False)`). No signature names a URL,
  a ref, or a directory — spec §5.
- `tcw/store/fs.py` — `FsStoreProvisioner` implementing it: the cache key
  (`<host>-<owner>-<repo>-<12 hex sha256(url + "\n" + ref)>` under
  `${XDG_CACHE_HOME:-~/.cache}/tcw/stores/`), clone-to-temp-then-rename, fetch +
  checkout on an existing working copy, and layout verification reusing the same
  `inbox` + status-folder check as `FsWorkStore.open` (`:2453-2455`). Every Git
  call goes through the module's `_git` so stdin stays closed.
- `tests/test_store_provisioning.py` — provisioner cases.

**Not wired to anything yet.** `FsWorkStore.open` and the CLI are untouched, so
the suite is green with this landed alone.

**Proves it.** Tests build a real bare repository in `tmp_path` and use it as the
remote, so nothing touches the network: clone into an empty cache; a second call
reports already-available and issues no Git command (asserted by monkeypatching
the module's `_git` and counting calls); `--refresh` re-fetches; an unknown ref
fails and leaves no directory at the target; `dry_run` issues no Git command.
Acceptance criteria 3, 6, 7.

## Task 3 — Resolution precedence in `FsWorkStore.open`

**Creates/modifies**

- `tcw/store/fs.py` — `FsWorkStore.open` (`:2429-2459`) gains the four-rule
  ladder from spec §2: existing `work.path` store wins; else the provisioned
  location; else `StoreNotProvisioned`; else today's behavior verbatim.
- `tests/test_store_provisioning.py` — precedence cases.

**The invariant to protect.** Rule 1 must keep consulting `work.path` exactly as
today, including the linked-worktree re-anchoring at `:2444-2446`. The rule
ladder wraps that logic; it does not reimplement it.

**Proves it.** New tests: a node with both a valid `work.path` store and a
declaration resolves to the `work.path` store; a node with an absent `work.path`
and a provisioned store resolves to the provisioned one; a node with a
declaration and neither raises `StoreNotProvisioned`; a node with a broken
`work.path` and no declaration raises with today's message verbatim. Plus
`tests/test_external_work_store.py` passing unmodified — acceptance criteria 5, 9.

## Task 4 — Error surfaces

**Creates/modifies**

- `tcw/store/fs.py` — `find_node` (`:157-160`) and `_has_work_store`
  (`:198-202`) re-raise `StoreNotProvisioned` instead of flattening it to
  `None`/`False`.
- `tcw/work/cli.py` — replace the six duplicated
  `"no tcw work node here — run \`tcw init\`…"` strings (`:73`, `:89`, `:144`,
  `:162`, `:177`, `:192`) with one `_require_node()` helper that prints either
  that sentence or, on `StoreNotProvisioned`, the declared remote and
  `run \`tcw provision\``.
- `tcw/validate.py` (`:145-148`) — report the node as declared-but-not-provisioned
  in its own words, naming the command.
- `tests/test_store_provisioning.py` — message cases.

**Sweep, not a spot fix.** The propagating exception reaches two groups of
callers, and every one is visited in this task — each either handles it or is
confirmed to be on a path that cannot raise it:

- `find_node` callers outside `tcw/work/cli.py`: `tcw/capabilities/cli.py:22`,
  `:163`, `:217` and `tcw/taxonomy/cli.py:21` (both pass a non-`work` component,
  which takes the `:155-156` branch and cannot raise — confirm, do not change).
- Direct `FsWorkStore.open` callers: `tcw/serve/__init__.py:399`, `:413`, `:446`;
  `tcw/work/recursion.py:79`, `:201`, `:295`, `:306`; `tcw/validate.py:146`.

This is the task's main risk (spec Risks) and the reason it is its own commit.

**Proves it.** `tcw work list` on an unprovisioned node exits non-zero with
stderr naming the remote and `tcw provision`, and *not* containing "no tcw work
node here"; `tcw validate` likewise; `grep -c` for the old string in
`tcw/work/cli.py` returns 1. Acceptance criteria 1, 4.

## Task 5 — The `tcw provision` verb

**Creates/modifies**

- `tcw/cli.py` — a `provision` subparser beside `init` (`:139`) and `validate`
  (`:146`), with `--component` (repeatable, default: every declared component),
  `--refresh`, `--dry-run`; and `_cmd_provision` driving `FsStoreProvisioner` per
  spec §4, printing the remote before contacting it.
- `tests/test_store_provisioning.py` — CLI-level cases driving `tcw.cli.main`.
  Not `tests/cli/`: that directory currently holds scenario *documents* and its
  `lib.sh` and scripts are explicitly still to be written, so there is no harness
  to add to. A scenario document for provisioning is worth writing when those
  scripts land; it is not this item's to invent.

**Component-generic from the start.** `--component` accepts `work` now and takes
a value rather than being a boolean, so child B adds `taxonomy`/`capabilities` as
values, not as new flags.

**Proves it.** End-to-end against a bare repo in `tmp_path`: provision, then
`tcw work list` prints the board and `tcw work path` prints the provisioned path;
a second provision exits 0 and reports already-available; `--dry-run` contacts
nothing; a node declaring nothing exits 0 saying so. Acceptance criteria 2, 3, 6.

## Task 6 — The no-implicit-network guard

**Creates/modifies**

- `tests/test_store_provisioning.py` — a test in the shape of the package-wide
  rule in `tests/test_subprocess_stdin.py`: with the provisioner's Git entry
  point monkeypatched to fail loudly, every `tcw work` read command against a
  *provisioned* node completes normally, proving none of them provisions
  implicitly.

**Proves it.** Acceptance criteria 3 and 8 (8's stdin half is already enforced
package-wide; this adds the network half).

## Task 7 — Documentation Sync

One pass over the finished diff, after Tasks 1-6 are done and the suite is green.
Every entry below has its trigger fired by this change.

- **`README.md`** [Public-API] — the external-store section (`:201-223`) gains the
  `work.repository` declaration, the precedence rule ("a store that is already
  here keeps being used"), and `tcw provision`. Plain language; no module names.
- **`docs/release-notes/upcoming.md`** [Public-API] — "your work items can live in
  another repository, and one command fetches it" — written for someone who has
  never read this spec.
- **`docs/changelogs/upcoming.md`** [Any-Code-Change] — Added: the declaration,
  `tcw provision`, `StoreNotProvisioned`. Changed: `FsWorkStore.open` precedence,
  `find_node`/`_has_work_store` propagation, the consolidated `tcw work` node
  message.
- **`skills/tcw-work/references/commands.md`** [Skill-Driven-Component] — the
  "Claims and external work stores" section already states the store-location
  rules; it gains the declaration, the precedence rule, and `tcw provision`. Add
  `tcw provision` to the command table.
- **`skills/tcw-plugin/SKILL.md`** [Skill-Driven-Component] — evaluate only: a
  store that is declared but not provisioned is a plausible `/tcw-doctor`
  symptom. Update if it fits; record "evaluated, no change" if not.

## Verification

What the suite cannot check:

- **The reported failure is fixed.** The requester reproduces their own case: a
  cloud session that clones only the code repo, `tcw provision`, then
  `tcw work list`. No test in this repo can stand in for that, and it is the
  check that decides whether the item was worth doing.
- **Codex parity** — every acceptance criterion re-run from a bare shell with no
  hook and no slash command, per `docs/lifecycle/harness.md`.
- **The abstraction seam** — a reviewer reads the `StoreProvisioner` signatures
  and confirms none mentions a URL, a ref, or a directory. Spec §5's table is the
  checklist.
- **Error text read cold** — does someone who has never seen this feature know
  what to run next? The tests assert a substring; only a person can judge that.
- **Supply-chain posture** — a reviewer confirms Task 6's guard actually covers
  the commands a user runs first (`list`, `show`, `path`, `validate`).

## Notes

- Taxonomy and capability records were seeded at this stage, in that order:
  `store/home-repository` and `provisioned-component-stores` first, then the two
  `Missing` capabilities that name the Feature, because `tcw capabilities set`
  refuses a `Feature=` reference that does not resolve. The deltas are recorded in
  this item's `capabilities.yaml` for the completion gate.
- Task 4 folds in the one sibling defect the spec's sweep found — six copies of a
  single string — rather than filing it. It is inside the task's own blast radius
  and fixing it is what makes the message improvable at all.
