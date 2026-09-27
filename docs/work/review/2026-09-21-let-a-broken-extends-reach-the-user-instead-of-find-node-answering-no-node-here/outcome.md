# Outcome: let a broken extends reach the user instead of find_node answering no node here

## What shipped

- **Tasks 1-2** — `2b3039a7`. `find_node` (`tcw/store/fs.py`) catches only
  `StoreLocationUnusable`; any other `ValueError` from opening a store reaches
  `main` and prints as `tcw: <message>`. Tests in
  `tests/test_store_provisioning.py` (unreachable and self `extends`, for both
  tree components; the genuine "no node here" cases; procedure prompt outside a
  work store), and the tightened check in `tests/test_legacy_store_config.py`.
- **Task 3** — filed `2026-09-26-make-tcw-init-honor-a-configured-taxonomy-or-capabilities-path` (`b9089e2c` on main).
- **Documentation** — changelog and release notes.
- **Review fold-in** — `4df9c79d`: changelog names the malformed `extends` list
  and the `procedure prompt` exit-code change; a test pins that change.

## Tests

- New tests went red on the old code with the old "no tcw … node here — run
  `tcw init`" text in stderr; the guard tests passed before and after.
- Full suite: 4481 passed, 3 skipped (before the review fold-in, which added one
  test; that file re-run green).
- Hands-on: scratch node with `taxonomy.extends: [ghost]`. Installed build:
  "no tcw taxonomy node here — run `tcw init`"; worktree build: `tcw: …
  taxonomy.extends: project 'ghost' is not reachable through connected-projects`.

## What the plan or spec got wrong

- The spec listed "a malformed config file" as newly reaching the user; a
  malformed `tcw-config.yaml` was already raised earlier by the registry check.
  Corrected to "a malformed `extends` list".

## Documentation Sync

| Entry | Fired? | Done |
| --- | --- | --- |
| `README.md` | No | — |
| `docs/guide/jira.md` | No | — |
| `docs/guide/<topic>.md` | Checked, no | No guide quotes the "no node here" advice. |
| `docs/release-notes/upcoming.md` | Yes | One line. |
| `docs/changelogs/upcoming.md` | Yes | Fixed entry, including the exit-code change. |
| `skills/<component>/SKILL.md` | Checked, no | `skills/setup` already warns never to run `tcw init` past a declared store. |
| `skills/configure/references/` | No | No key changed. |

## Autonomous decisions

Run unattended on 2026-09-26 (`extras-autonomous-work`).

- **Spec: is catching only `StoreLocationUnusable` right, and should a
  configured-but-missing tree path be folded in?** Codex: yes; separate item —
  a different policy (absence versus unusable configured location). Opus: yes,
  verified by direct opens in a scratch repository; separate item, and noted
  `init` ignores configured tree paths. Chose both; filed the follow-up.
- **Code review** (adversarial-code-reviewer): DONE, merge with notes. Accepted
  both documentation notes and the optional test. Nothing rejected.
- **Verify** (tcw:verifier): accept; all five criteria met on its own runs
  (217 targeted tests; hands-on with the worktree's `tcw` for each message,
  including the `work.path: ''` exit-code change). Decision: accept.
