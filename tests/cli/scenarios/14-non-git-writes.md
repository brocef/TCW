# 14 — Writes outside a git repository

TCW reads anywhere and writes only inside a repository. This scenario is the
shipped-binary check that the refusal is one sentence, one exit code, and leaves
nothing on disk — the in-process tests drive `main()` and the store API, and
neither of those is the `tcw` a user runs.

## Functionality covered

- The single refusal wording, shared by `tcw init` and every store write
- Fail-closed: no file, and no directory, survives a refused write
- Reads still working outside a repository, byte-for-byte
- The generic `git`-subprocess error boundary

## Fixture

A node scaffolded and committed **inside** a repository, then `rm -rf .git`,
placed where no repository exists above it (`git rev-parse --show-toplevel`
fails). `tcw init` refuses outside a repository, so this is how a node without
one actually arrives: the repository deleted, an export or tarball copy, or a
`docs/` tree vendored into a plain directory.

Seed it with a backlog item, an active item, an item in review, an epic, a raw
inbox entry, one taxonomy term and one capability, and register a sibling child
node (also de-gitted, so `delegate` writes into a non-git store too).

## What is tested

| # | Assertion |
| - | --------- |
| 1 | Every write command exits **1**, prints exactly one line on stderr matching ``tcw…: not inside a git repository. Run `git init` first.``, and prints no `Traceback`. The full list is assertion 2's table. |
| 2 | Take a `path → sha256` manifest of the whole graph — **directories included** — before each command in 1 and after it. They are identical. Directories matter: `tcw work start` creates `docs/work/.claiming/` before it renames anything, and a file-only manifest would call that clean. |
| 2a | The commands: `init` · `work init` · `taxonomy init` · `capabilities init` · `work new` · `work start` · `work start --worktree` · `work start --take-over --owner` · `work edit --title` · `work rework` · `work submit` · `work complete --resolution done --confirm` · `work complete --resolution wontfix --confirm` · `work drop --confirm` · `work tags add` · `work tags rm` · `work scaffold spec` · `work inbox accept` · `work reconcile` · `work delegate` · `work escalate` · `taxonomy add` · `taxonomy rm` · `taxonomy extends add` · `taxonomy extends rm` · `capabilities add` · `capabilities set --status` · `capabilities extends` · `capabilities extends --rm`. |
| 3 | `tcw work start <slug>` leaves the item in `docs/work/backlog/` and creates nothing in `docs/work/active/`. This is the sharpest regression: the claim used to land and the command then died in staging, so the item moved and nothing said so. |
| 4 | `tcw init` outside a repository prints exactly ``tcw init: not inside a git repository. Run `git init` first.`` — the wording every other refusal now shares. Byte-compare it. |
| 5 | Reads exit 0 and print what they printed before the guard existed: `work list`, `work show`, `work nodes`, `validate`, `taxonomy list`, `taxonomy show`, `capabilities list`, `capabilities show`. Compare stdout against the golden files in `tests/fixtures/non_git_reads/`, normalizing only the temp root, the minted `cap-…` id and the claim timestamp. |
| 6 | `tcw serve` against the same node: every write route (`POST /api/work`, `POST /api/work/<slug>/actions/start`, `POST /api/taxonomy`, `POST /api/capabilities`, `PATCH /api/work/<slug>`, `PUT` artifact, `PUT` sidecar, `PUT` plan-stage, `DELETE /api/work/<slug>`) answers **4xx, not 500**, with the refusal in the body, and the manifest is unchanged across the whole sequence. Read routes still answer 200. |
| 7 | Inside a repository, nothing changes: the full scenario-02 happy path runs green against the installed binary. The guard costs one `git rev-parse` per guarded call and must not alter any successful command's output. |
| 8 | A repository that **exists and refuses** — simulate with a `pre-commit`-independent failure, e.g. a `.git/index.lock` held for the duration — produces `tcw: git command failed (exit N): git …` on stderr, a non-zero exit, and no `Traceback`. |

## Refusals asserted

- Every command in 2a, with one wording and exit code 1
- `tcw work start --take-over` specifically, since it reaches `git_stage` by a
  different route than the ordinary claim
- `tcw work delegate` and `tcw work escalate`, which write another node's inbox

## Explicitly not covered here

- `tcw capabilities reset` and the plan-stage `DELETE` route. Both refuse on
  their own terms before any git path — "not an override" and "undeclared plan
  stage" — and reaching their `git rm` needs a federated override or a plan
  manifest built for the occasion. The same `git rm` is covered by
  `taxonomy rm`, `capabilities remove` and `work drop`.
- `git` missing from `PATH` entirely. It reports "not inside a git repository",
  which is misleading but harmless, and detecting it separately would cost a
  second probe on every write.
- Repository states other than "absent": corrupt `.git`, a rejecting hook, a
  `safe.directory` ownership refusal. Assertion 8 covers the shape of all of
  them; classifying git's failure modes is not TCW's job.

## Notes for the implementer

Assertion 2 is the load-bearing one and the easiest to get wrong twice. Walk
directories as well as files, and rebuild the fixture between commands rather
than running them in sequence — several of these commands would otherwise be
refused by an earlier command's legality gate instead of by the repository
guard, which passes for the wrong reason. `tcw work submit` in particular needs
an item that is genuinely `active`, or it refuses with "not a legal transition"
and proves nothing.
