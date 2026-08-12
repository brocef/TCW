# Resolve self-qualified tcw:// links in tcw serve

## Origin

GitHub issue [#12](https://github.com/brocef/TCW/issues/12), filed 2026-08-11 by
@brocef. Accepted during a `tcw-triage-issues` sweep.

Reported against `tcw 0.18.2` on macOS 26.5.2, pyenv shim install.

> ### Environment
>
> - tcw version: `tcw 0.18.2`
> - OS / platform: macOS 26.5.2
> - Install method: pyenv shim (`/Users/brian/.pyenv/shims/tcw`)
> - Axis: work
>
> ### Steps to reproduce
>
> At an orchestrator node whose registered id is `proposit-app`:
>
> 1. Create two backlog items in that node, and from one `initial-request.md` link
>    the other with the **qualified** locator form the docs recommend:
>
>    ```markdown
>    [Rewrite the Falls short explanation copy](tcw://W/proposit-app/2026-08-11-rewrite-the-falls-short-explanation-copy)
>    ```
>
> 2. `tcw validate` → clean. No link problem is reported (the 11 problems in my
>    run are all unrelated resolution-placement ones).
> 3. `tcw serve`, open the linking item, click the link.
>
> ### Expected vs. actual
>
> - **Expected:** the viewer navigates to the linked item. It is not a remote
>   item — it is on the very board being served.
> - **Actual:** the link is inert. `POST /api/resolve` answers `{"ok": false}` for
>   that uri, so the SPA renders it as plain text with nothing to click.
>
> The bare form `tcw://W/<slug>` navigates fine. Only the qualified form fails,
> including — and this is the surprising part — when the project it names is the
> node being served.
>
> ### Root cause
>
> `tcw/serve/__init__.py:932`:
>
> ```python
> ok = r.ok and (not r.project or r.project in self._hosted_projects())
> ```
>
> and `_hosted_projects()` at `tcw/serve/__init__.py:399`:
>
> ```python
> if not self.server.include_descendants:
>     return set()
> anchor = self.server.node_root.resolve()
> return {registered_project_id(anchor, root) for root in descendant_nodes(anchor)}
> ```
>
> `descendant_nodes()` is `registry.descendants()` filtered to nodes with a work
> store (`tcw/store/fs.py:161`) — it does not include the anchor. So the anchor's
> own project id is in the hosted set in **neither** mode: without
> `--include-descendants` the set is empty, and with it the set is descendants
> only. A locator naming the served node itself can therefore never resolve.
>
> Bare refs escape only because `not r.project` short-circuits before the
> membership test.
>
> The docstring's reasoning is right about ancestors — "an ancestor's item is a
> valid reference and an unopenable link" — but the anchor is not an ancestor of
> itself, and its items are precisely what the board lists.
>
> ### Why this is easy to walk into
>
> The qualified form is what the docs steer you to. `cross-node-deltas.md` tells
> you to write `[<epic title>](tcw://W/<orchestrator-project-id>/<epic-slug>)`,
> and the fix for #7 made qualified refs resolve in any direction, so `validate`
> now accepts them everywhere. The result is that the recommended, validating
> form is the one the viewer cannot open, with no warning from either tool. I
> wrote four request documents this way before noticing the links did nothing.
>
> ### Remediation
>
> Include the anchor's own registered id in `_hosted_projects()`, in both modes —
> `FsProjectRegistry.open(anchor).require_valid().current.id`, or equivalently
> `registered_project_id(anchor, anchor)`:
>
> ```python
> def _hosted_projects(self) -> set[str]:
>     anchor = self.server.node_root.resolve()
>     hosted = {registered_project_id(anchor, anchor)}
>     if self.server.include_descendants:
>         hosted |= {registered_project_id(anchor, root) for root in descendant_nodes(anchor)}
>     return hosted
> ```
>
> Worth considering alongside it: `validate` currently accepts a locator the
> viewer will render dead. If unopenable-but-valid is the intended state for
> genuinely remote refs, a note in `cross-node-deltas.md` next to the recommended
> link form would save the next person the same detour — the same remedy #7
> suggested for its own case.
>

## Product changes

## Technical changes

## Meta changes
