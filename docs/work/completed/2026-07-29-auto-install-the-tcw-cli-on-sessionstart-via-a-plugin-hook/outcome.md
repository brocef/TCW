# Outcome — Auto-install the tcw CLI on SessionStart via a plugin hook

Six commits on `main`, tree clean, suite green at every boundary. The `tcw` CLI
now installs and refreshes itself from the plugin clone at session start, and
`/tcw-init` is gone.

## What shipped

| Task | Commit | Shipped |
|---|---|---|
| 1 — script + tests | `faf200f` | `scripts/session_bootstrap.sh` (committed `100755`); `tests/test_session_bootstrap.py`, 7 tests |
| 2 — hook wiring | `e6fe546` | `hooks/hooks.json`; `"hooks": "./hooks/hooks.json"` in `.claude-plugin/plugin.json`; `test_hooks_manifest_wires_one_executable_session_start_script` |
| 3 — reference collapse | `7046a7e` | `skills/tcw-plugin/references/setup.md` and `references/doctor.md` delegate to the script |
| 4 — retire the command | `ce451ad` | deletes `commands/tcw-init.md` |
| 5–8 — documentation | `44c5ab3` | `skills/tcw-plugin/SKILL.md`, `README.md`, `docs/release-notes/upcoming.md`, `docs/changelogs/upcoming.md` |
| 5 (added) — doctor router | `34d2981` | `commands/tcw-doctor.md` brought in line with the rewritten procedure |

**Interface:** `session_bootstrap.sh [clone-root] [sentinel-path]`, defaulting to
`$CLAUDE_PLUGIN_ROOT` and `$CLAUDE_PLUGIN_DATA/installed-version`. Both arguments
and both variables optional — verified under `env -u CLAUDE_PLUGIN_ROOT -u
CLAUDE_PLUGIN_DATA`. Check order, every branch exiting 0: unresolvable clone root
→ sentinel matches *and* `tcw` on PATH → editable install → `pipx` absent →
`pipx install --force`, then write the sentinel. Silent on success and on every
skip. Only a failed install prints, one line to stdout:

```
tcw: automatic install from <clone-root> failed — run /tcw-doctor (Codex: the tcw-plugin skill) to diagnose.
```

## Test result

`python -m pytest` at `34d2981`, run by the coordinating session:

```
1088 passed in 168.41s (0:02:48)
```

`tests/test_session_bootstrap.py` alone: `7 passed`. Every fixture test runs with
`PATH=<tmp_path>/bin:/usr/bin:/bin`, so the only `pipx`, `tcw`, and `python3`
reachable are stubs the test wrote; the one real-PATH test prepends a *recording*
pipx stub, so a regression logs an invocation instead of rebuilding the
developer's install. Real pipx is never invoked.

`test_real_editable_checkout_is_left_alone` **ran rather than skipped** on this
machine — confirmed with `pytest -v`. The guard is proven against the actual
pyenv shim, not only against a fixture. A mutation check (forcing the editable
condition to `false`) fails exactly the two editable tests and no others, so the
coverage is real rather than incidental.

## What the plan and spec got wrong

Five corrections, all applied to `spec.md` / `plan.md` in place and marked there.

**1. The editable guard, as specified, would have force-installed over the
maintainer's dev setup — silently, every session, in this repo.** The spec copied
`doctor.md`'s recipe (`direct_url.json` → `dir_info.editable`) but a plain
`python3 -c` inherits cwd on `sys.path`, and a SessionStart hook's cwd is the
project. This checkout contains `tcw.egg-info`, which `importlib.metadata` finds
first and which has no `direct_url.json`. Measured from the repo root:

```
unfiltered → found at: .                    direct_url.json: None       → "not editable"
filtered   → found at: …/site-packages      {"dir_info": {"editable": true}, …}
```

The script now strips `""`/`"."`/cwd from `sys.path` before querying, with a
comment naming why. `doctor.md` step 1 carries the same warning, because the
identical trap bites the human procedure (`m.distribution('tcw').locate_file('')`
run inside a checkout answers `.`). This is the single most valuable thing the
stage produced: the highest-stated risk in the spec was real, and the spec's own
mitigation did not work.

**2. The check order contradicted the Risks section.** Design put the editable
check ahead of the sentinel match; Risks promised a hot path of "one `command -v`
plus one `cmp` … no Python starts". As written, every session in every project
paid a `python3` start. Sentinel/PATH now goes first. Semantics are unchanged —
a dev checkout never has a matching sentinel, so the guard still fires.

**3. "Reports 'pipx missing' and stops" contradicted "each exiting 0 and
silently."** Two statements in the same spec. Silence won, matching the decision
recorded at `request`; `setup.md` carries the compensating flow (run the script →
verify `tcw --version` → only then check `command -v pipx` and take the ladder),
so the judgment stays with the agent and the hook stays quiet.

**4. Collapsing `doctor.md` onto the script would have made `/tcw-doctor`
silently no-op.** The plan's "both documents become 'run the script'" missed that
doctor exists precisely for cases where the sentinel can match while the install
is still wrong — a shadowed install, or a re-clone of the same version at a new
path. Step 4 now runs the script, re-checks `tcw`'s source, and falls back to a
direct `pipx install --force` when the script skipped on a matching sentinel.

**5. Acceptance criterion 1 was not runnable as written.** `claude plugin
validate .` validates the **marketplace** manifest when one is present and never
reads `plugin.json`. Exercising the `hooks` key required an isolated plugin dir
with no `marketplace.json`; there it passes, including `--strict`, and a
deliberately bad path errors with `hooks[0]: Path not found` — so the key is
recognized, not silently tolerated, and the schema accepts a string or an array.
The spec's fallback (drop the key, rely on auto-discovery) was not needed.

Also unstated and now defined: if neither `$2` nor `$CLAUDE_PLUGIN_DATA` resolves
(the Codex path when the skill passes only a clone root), the script skips both
the comparison and the write — i.e. it installs. Correct there, since the skill is
invoked exactly when `tcw` is missing or stale.

## Rework pass (rejected at `verify`)

`rework.md` sent two defects back; verification then dropped one of them and added
four more (D1, D3, D4, D5) plus a spec correction. All fixed.

**1. `allowed-tools` now covers what the procedures instruct.** Both
`skills/tcw-plugin/SKILL.md:5` and `commands/tcw-doctor.md:3` carry the identical
list: `Bash(tcw *), Bash(command -v *), Bash(realpath *), Bash(ls *),
Bash(sort *), Bash(pipx *), Bash(python3 *), Bash(node --version),
Bash(*/scripts/session_bootstrap.sh *), Read`. That covers `setup.md` steps 2–5
(script, `tcw --version`, `command -v pipx`, the `pip`/`pipx` ladder, `node`) and
`doctor.md` steps 1–5 (`command -v`/realpath, `pipx list --json`, `python3 -c`,
the `ls | sort -V` sibling scan, the script, `pipx install --force`, `node`).
`Read` was missing from the command file, which opens by telling the agent to
read `references/doctor.md`.

**The script pattern was verified, not assumed.** The rework flagged that a
leading wildcard might not be supported and that the clone root moves on every
plugin update. Claude's permission docs state wildcards may appear at any
position, and an end-to-end check confirms it: a fixture
`session_bootstrap.sh` under a cache-shaped path, invoked exactly as the docs
write it (`"<root>"/scripts/session_bootstrap.sh "<root>"`, quotes and all), ran
under `claude -p … --allowedTools 'Bash(*/scripts/session_bootstrap.sh *)'
--permission-mode default`, and the identical invocation under a deliberately
non-matching rule came back "This command requires approval". So the fallback the
rework asked for was not needed. Anchoring on the path *tail* rather than the
clone root is what survives the update; putting wildcards on both sides is what
makes the embedded quotes irrelevant, since they fall inside the wildcards under
either raw-string or shell-lexed matching.

The pipx-missing ladder's last rung ("a dedicated venv") names no fixed command
and is deliberately left ungranted — a prompt there is the right outcome.

**2. Backlog cross-reference — made, then withdrawn.** The count was corrected to
"two" and then reverted to the original "three" on the verifier's argument:
`initial-request.md` is a record of what was asked, not a live document, so a fact
that went stale afterwards is not that artifact's to carry; and the count is
rarity color, not load-bearing — the safety argument ("this command carries the
flag because it deletes files; skill references have no equivalent flag") holds
identically at two, and 3 → 2 only makes the flag rarer. That item's `spec.md`
re-derives the count at planning time. For the record, the current answer is two:
`grep -rn "disable-model-invocation" commands/ skills/` → `tcw-consolidate-plans.md:3`
and `tcw-doctor.md:4`.

**3. D1 — the editable guard asked the wrong interpreter.** The same shape as the
defect the first pass found: a guard that looks right and is wrong in a real
configuration. `tcw_is_editable` probed with the `python3` on PATH, which owns the
`tcw` on PATH only by coincidence. After `pipx install -e ~/src/TCW`, or an
editable install into a venv, it is a different interpreter; it raises
`PackageNotFoundError`, `>/dev/null 2>&1` swallows it, the function returns "not
editable", and the script force-installs over the developer's checkout — silently,
every session, until the versions happen to match. Every test passed because this
machine's `tcw` and `python3` are both pyenv shims backed by one interpreter.

The invariant the fix enforces, stated plainly:

> **Only replace a `tcw` whose own interpreter reports a plain, non-editable
> install.** An install whose owner cannot be identified is not ours to replace.

The owner comes from the shebang of `command -v tcw` (`tcw_interpreter`): an
absolute `…/bin/python…` gets questioned; anything else — `#!/usr/bin/env bash`
(a version manager's shim), a wrapper, a binary — is unidentifiable and therefore
untouchable. Measured on this machine: pip-generated console scripts carry
`#!/Users/brian/.pyenv/versions/3.14.6/bin/python3.14`, and the pyenv shim carries
`#!/usr/bin/env bash`.

**On the two routes considered.** The coordinator suggested inverting the guard
via `pipx list --json` (is this `tcw` pipx-owned and non-editable?) and ruled out
the shebang, because a pyenv shim's shebang is `bash` and "learns nothing". That
objection assumes the goal is to *find* the interpreter; the goal is to decide
whether to clobber, and for a shim "no identifiable owner" **is** the answer.
Taking the shebang route buys the same coverage — editable, pipx-editable, venv,
shim, unknown — in a third of the code, with two decisive advantages: it depends
on no pipx JSON schema, and `pipx is not installed on this machine`, so a
schema-dependent probe could not have been verified here at all. An unverifiable
wrong key would mean "never ours" and a hook that silently never installs for
anyone — a worse failure than the one being fixed.

**What the inverse route would have covered and this one does not:** a
*non*-editable `tcw` that pipx did not install (a plain `pip install tcw`). It is
force-installed over, exactly as before this change. `references/setup.md` already
tells users not to keep both, and `/tcw-doctor` diagnoses it.

**Tests.** `test_editable_install_owned_by_another_interpreter_is_left_alone`
(editable owned by a non-PATH interpreter) and
`test_install_we_cannot_identify_is_left_alone` (a `#!/usr/bin/env bash` shim).
Both **fail against the previous probe** — verified by restoring the old script
from `HEAD` and re-running: 3 failed, 6 passed. `test_failed_install_…` now points
its `tcw` stub at a stub interpreter that reports non-editable, so the positive
branch (we *do* install over an identified plain install) stays covered — without
it, a guard that always skipped would pass the file.

**4. D4 — stderr leak on an uncreatable sentinel parent.** `mkdir -p` now has
`2>/dev/null`. Measured with a sentinel whose parent path component is a regular
file: before, `stderr=[mkdir: …/notadir: File exists]`; after, `rc=0 stdout=[]
stderr=[]`.

**5. D3 — hermeticity was assumed, not enforced.** The file's docstring claimed
hermeticity by construction while relying on `/usr/bin:/bin` happening to hold no
`pipx`; a distro-packaged `/usr/bin/pipx` would have made `test_missing_pipx_…`
invoke real pipx against the real `HOME`. `_run` now asserts no `pipx` outside the
fixture bindir resolves on the PATH it builds. That test also drops its `tcw` stub,
so the new provenance guard cannot pre-empt the branch it exists to cover.

**6. D5 — two references described a skip their own invocation cannot take.**
Both prescribe `script "<clone-root>"` with no sentinel argument, and a Bash tool
call does not export `CLAUDE_PLUGIN_DATA`, so the steady-state branch is
unreachable there — yet setup claimed it "skips silently when `tcw` is already
current" and doctor explained a no-op as "its sentinel already matched". Fixed in
the prose, not the invocation: passing a sentinel would mean telling the agent a
path it has no reliable way to know under Codex. Both now say the shortcut is
unavailable without a sentinel and name the skips that can fire.

**7. Found while fixing D5 — `doctor.md` carried the D1 defect too.** Step 1's
fallback recipe was `python3 -c "… locate_file('') …"`, the same wrong-interpreter
question one layer up, in the procedure a human runs *because* the automatic path
failed. Steps 1–2 now read the shebang, locate the owning environment, and read
`direct_url.json` from its site-packages — no interpreter is executed, so the
procedure needs no new grant beyond `Bash(head *)`, which was added to both
`allowed-tools` lists.

**8. `spec.md` criterion 9 corrected.** It required `grep -rn "tcw-init"` over
`docs/capabilities/` to return nothing at review while the same spec's Capability
changes section and plan Task 9 defer that rewrite to `complete`. The grep now
covers `README.md`, `skills/`, and `commands/`; criterion 11 covers the capability
body at the stage that owns it. Design item 3 also carries a second
`*(Corrected at implement)*` note for D1.

**Re-checked rather than assumed:** `python -m pytest -q` → `1091 passed in
150.81s` (1088 at rejection, +2 for D1, +1 from another session's concurrent work
items in `docs/work/`); `pytest tests/test_session_bootstrap.py -v` → 9 passed
with `test_real_editable_checkout_is_left_alone` **PASSED**, not skipped;
`grep -rn "tcw-init" README.md skills/ commands/` → no matches (exit 1);
`bash -n scripts/session_bootstrap.sh` clean.

**Documentation sync, second pass.** `README.md` did not fire — no `tcw` CLI
surface or user-facing behavior changed. `[Skill-Driven-Component]` did not fire
— the component the skill drives is unchanged; only the skill's own grant moved,
and its procedures already match the tool. `docs/changelogs/upcoming.md`
(`[Any-Code-Change]`) fired: a Changed entry with the full list, the pattern
rationale, and the verification. `docs/release-notes/upcoming.md` (`[Public-API]`)
**did** fire, on the merits rather than by reflex: the previously shipped
`/tcw-doctor` grant already failed to cover its own steps 1–3, so a user
upgrading from v0.16 sees a real difference — fewer approval prompts during
install and repair. One plain-language sentence went onto the existing
`/tcw-doctor` bullet. What was *not* written: anything about permission grants or
frontmatter, which is internal vocabulary that file's brief forbids, and any
claim of a fixed regression — the prompt-y intermediate state never shipped.

D1 fires the release-notes trigger on its own terms: the paragraph promising a
`pip install -e` checkout is left alone was true only for one install shape, so
it now says the automatic install replaces an ordinary install and does nothing
when it cannot tell — naming venvs and version managers, not shebangs.
`README.md` still does not fire; it documents no install-provenance behavior.
`[Skill-Driven-Component]` fires this time — the script the `tcw-plugin` skill
drives changed its guard, and `references/doctor.md` and `references/setup.md`
were updated to match (items 6 and 7 above).

## Notes

**Plan Verification items 2 and 4 were not attempted** — the real update round
trip and deleted-command propagation both need a real plugin install from this
branch, which no automated check can stand in for. They are the substance of what
`verify` has to cover. The spec's fallback still holds for 4: a lingering
`/tcw-init` routes to the rewritten `setup.md`, which runs the same script, so the
worst case is redundant-but-correct.

**Delegation shape.** `implement` ran as two subagents — code tasks 1–4, then the
documentation gate over the finished diff — with this session coordinating,
re-reading every artifact, and running the suite and the `sys.path` check itself
rather than accepting the reports. `outcome.md` is written by the coordinator
because no single subagent held the whole stage. Neither agent returned its report
without being asked for it; both did on request.

**Left alone deliberately:** `.claude/settings.local.json:91` holds a stale local
permission entry naming `commands/tcw-init.md`. User-local, harmless, and not this
item's business.

**Unrelated pre-existing condition:** `claude plugin validate --strict .` fails at
the repo root on a missing marketplace `description`. Untouched by this change,
but "strict validation is clean" is not currently true of this repo.

**Cosmetic, not a defect:** the editable dist-info here reads `tcw-0.10.3` while
the repo is `0.16.0` — stale metadata from whenever `pip install -e .` last ran.
It affects neither the guard (only `direct_url.json` is read) nor `tcw --version`
(read from source).
