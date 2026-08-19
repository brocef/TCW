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
| 10a | Requests carrying a non-loopback `Host` or `Origin` header are rejected. The in-process suite covers this, but the endpoint launches host processes, so it is worth re-proving at the real socket. |
| 11 | Two `tcw serve` instances on the same node both start (each picking its own port) or the second fails cleanly — pin whichever, but not a traceback. |
| 12 | The node subprocess runs with its **stdin closed** — proven by interposition, not inference. Put a fake `node` first on `PATH` that inspects fd 0, records whether it is `/dev/null`, then `exec`s the real interpreter. Assert the recorded value. A child that merely *inherits* a pipe without reading it still serves requests and still exits on signal, so "the server behaved normally" passes with the regression present. |
| 13 | Killing the node child out from under `tcw serve` produces a clean error, not a hang. |

## Refusals asserted

3, 7, 8, 9.

## Explicitly not covered here

The web client's rendering. This scenario is the HTTP API only — a browser test
is a different tool and a different scenario.

## Notes for the implementer

**`POST …/open` launches a real host application.** For a filesystem artifact TCW
runs `open` (macOS) or `xdg-open` (Linux). Left alone, assertion 6 opens a
Markdown file in the developer's editor on every run. Interpose a fake
`open`/`xdg-open` first on `PATH` that records its arguments to a sentinel file
and exits, then assert: a present artifact invokes it exactly once with the
resolved path, and the blank and traversal cases never invoke it at all. Reap the
fake.

**Cleanup must be by process group, not by name or port.** Start `tcw serve` in
its own group/session, record both the parent and the node-child PIDs, and in the
`EXIT` trap send `TERM` to the group, wait with a deadline, then escalate only to
PIDs still alive. Never `pkill node` — that kills the developer's unrelated work.

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
