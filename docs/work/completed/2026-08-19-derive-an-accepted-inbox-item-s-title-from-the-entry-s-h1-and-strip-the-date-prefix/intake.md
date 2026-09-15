# Derive an accepted inbox item's title from the entry's H1 and strip the date prefix

## Origin

GitHub issue [#20](https://github.com/brocef/TCW/issues/20), filed 2026-08-19 by
@brocef. Accepted during a `tcw-triage-issues` sweep.

## Inbox body

The reporter's text, verbatim:

> ### Environment
>
> - tcw version: `tcw 1.0.0`
> - OS / platform: macOS 26.5.2 (darwin)
> - Install method: pip into pyenv 3.14.6 (via the plugin's `SessionStart` installer). Side note: `pip show tcw` in that same env reports stale metadata (`Version: 0.10.3`) while `tcw --version` reports `1.0.0`.
>
> ### Steps to reproduce
>
> In a fresh node:
>
> ```sh
> mkdir tcwtest && cd tcwtest && git init -q .
> printf 'id: tcwtest\n' > tcw-config.yaml
> tcw init work
>
> cat > docs/work/inbox/2026-08-19-another-raw-request.md <<'MD'
> # Another Raw Request
>
> Body.
> MD
>
> tcw work inbox accept 2026-08-19-another-raw-request
> tcw work list
> ```
>
> ### Expected vs. actual
>
> - Expected: slug `2026-08-19-another-raw-request`, title `Another Raw Request` (from the entry's `# ` heading).
> - Actual:
>
> ```
> → now at docs/work/backlog/2026-08-19-2026-08-19-another-raw-request
> 2026-08-19-2026-08-19-another-raw-request
>
> 2026-08-19-2026-08-19-another-raw-request | backlog | i | - | 2026-08-19-another-raw-request
> ```
>
> The title is derived from the entry's *filename* — date prefix and all — and that filename-derived title is then re-dated into the slug, so the date appears twice. The entry's `# Another Raw Request` H1 is ignored, even though `tcw work delegate`/`escalate` write exactly that heading into the entries they create.
>
> For contrast, the same accept with `--title "Clean Title"` behaves correctly:
>
> ```
> → now at docs/work/backlog/2026-08-19-clean-title
> 2026-08-19-clean-title | backlog | i | - | Clean Title
> ```
>
> ### Impact
>
> This is on the documented cross-node epic path. `tcw work delegate` names its inbox entries `<date>-<slug>.md`, so every slice adopted with a bare `accept` gets a double-dated slug and a slug-shaped title. Our workspace's `AGENTS.md` has carried "always pass `--title`" as a standing workaround since 0.18.x, and it is still required on 1.0.0.
>
> ### Remediation
>
> Derive the title from the entry's first `# ` heading when it has one, and strip a leading `YYYY-MM-DD-` from the filename before falling back to it — the date prefix is TCW's own naming convention, so it should not survive into a human-facing title or be re-applied to the slug.
>
