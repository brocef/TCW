As a user, I replace or extend the text of one of TCW's procedures in `tcw-config.yaml` under `work.procedures`, keyed by procedure id, so a TCW skill follows my team's practice — my advisors, my review, my git workflow — rather than one TCW chose for everyone.

`work.procedures` sits beside `work.lifecycle`, not inside it, and each id holds a plain list of bindings in the same grammar a stage's `prompt:` uses: `blob:`, `file:`, `generate:`, `builtin: true` and `skill:`, each optionally carrying `when: {tags, not_tags, type}`. Every binding that applies is used, in the order I wrote them.

```yaml
work:
    procedures:
        autonomous-work:
            - file: docs/procedures/autonomous-work.md
        documentation-sync:
            - builtin: true
            - blob: "Also update docs/guide/ when a CLI flag changes."
```

A `generate:` script runs under the same `work.lifecycle.timeout` and `work.lifecycle.output-cap` as any other, and sees `TCW_HOOK_ROLE=procedure` and `TCW_HOOK_ID=<procedure id>` so one script can serve a stage and a procedure.

`tcw validate` rejects an unknown procedure id, a value that is not a list, an empty list, a bare string, a blank or duplicated reference, `command:` (naming `generate:` instead), a malformed `when:`, and a `file:` that does not exist or resolves outside my project. An empty list is refused because it reads like an opt-out and is not one; to make a procedure say nothing I write `[{blob: ""}]`. A mistake in the block never breaks reading the board — it is reported by `tcw validate` and ignored elsewhere.

I can replace a procedure's text, not add procedures of my own.
