# 12 — `tcw serve`: the local HTTP API

`tcw serve` is the only long-running process TCW starts, and the only surface
reached over a socket. It is also where a presence-rule contradiction shipped a
button that could only 404.

## Functionality covered

- `tcw serve --no-open`, port selection, startup and shutdown
- `GET /api/work`, `/api/work/<slug>`, `/api/taxonomy`, `/api/capabilities`
- `POST /api/work/<slug>/artifacts/<name>/open`
- The node subprocess (`serve/runtime.py`) and its lifecycle

## What is tested

| # | Assertion |
| - | --------- |
| 1 | `tcw serve --no-open` in a node starts, binds a port, and answers `GET /api/work` with parseable JSON listing the node's items. Started in the background, killed in the trap. |
| 2 | It exits cleanly on `SIGTERM` — and **leaves no orphaned child process**. Assert the node subprocess is gone, not just the parent. |
| 3 | `tcw serve` outside a node exits non-zero and names `tcw init`. |
| 4 | `GET /api/work/<slug>` returns the item with its artifact list. |
| 5 | **The presence contract.** For an artifact that exists but is whitespace-only, `present` is `false` in **every** place it appears in one payload, and `POST …/open` on it returns **404**. The list and the gate agree. This is a regression test for a shipped defect. |
| 6 | For a genuinely written artifact, `present` is `true` everywhere and `POST …/open` returns 204. |
| 7 | `GET /api/does-not-exist` returns 404, not 500. |
| 8 | `POST …/open` with a path-traversal artifact name (`../../etc`) returns 400; with a traversal slug, 404. Neither spawns anything. |
| 9 | `POST …/open` with a non-JSON `Content-Type` is rejected 400 — a cross-origin simple POST must not reach the opener. |
| 10 | The server binds **loopback only**. Assert the listening address is `127.0.0.1`, not `0.0.0.0`. |
| 11 | Two `tcw serve` instances on the same node both start (each picking its own port) or the second fails cleanly — pin whichever, but not a traceback. |
| 12 | The node subprocess runs with its **stdin closed**: a `tcw serve` whose own stdin is a held-open pipe does not have its child compete for it. Assert `/proc`-free: check the parent still responds to input-independent requests and terminates on signal within the timeout. |
| 13 | Killing the node child out from under `tcw serve` produces a clean error, not a hang. |

## Refusals asserted

3, 7, 8, 9.

## Explicitly not covered here

The web client's rendering. This scenario is the HTTP API only — a browser test
is a different tool and a different scenario.

## Notes for the implementer

Everything here needs `curl` and a readiness wait. Poll the port with a bounded
retry loop; never `sleep` a fixed guess. Kill the server in the `EXIT` trap with
the whole process group, or assertion 2 will pass while leaking a node process
into the developer's machine.

Assertion 10 matters more than its one line suggests: this server exposes an
endpoint that launches processes on the host. If it ever binds a routable
address, that is a security finding, not a test failure.

If `node` is unavailable on the machine, the API scenarios that need the child
process must **skip loudly**, naming the missing dependency. A silent skip in a
release gate is worse than a failure.
