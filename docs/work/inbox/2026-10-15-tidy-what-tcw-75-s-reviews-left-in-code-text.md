# Tidy what TCW-75's reviews left in code text

Separate-change findings from TCW-75's round-1 review (2026-10-15). Each is
text in `tcw/` (or a test helper) that TCW-75, a documentation item, does not
own. Most are small enough to fix before TCW-76's code freeze, after which
nothing under `tcw/` changes until the epic merges.

1. **Error messages name removed keys.** `tcw/work/generate.py:180` and `:184`
   name `work.lifecycle.output-cap` and `work.lifecycle.timeout`; the keys are
   `work.hooks.output-cap` and `work.hooks.timeout`. An agent reading the
   message would set a key `tcw validate` refuses.
2. **A doubled quote in a refusal.** `tcw/work/open.py:108` builds
   `who = f"'{project_id}'"` and then appends `'s`, printing `'child''s work
   store is not in a git repository`.
3. **Out-of-date docstrings.**
   - `tcw/work/hooks.py:8-10` says `tcw serve` never runs hooks, but adopting a
     ticket through the viewer runs request `post` hooks
     (`docs/guide/web-viewer.md:86`, `tickets.adopt`).
   - `tcw/cli.py`'s `run_provision` says it is "the only command that reaches
     the network", which stopped being true with the Jira backend.
   - `tcw/store/base.py:5-6` says remote adapters are "possible but unbuilt".
   - `skills/README.md:85` still says "TCW-75 rewrites this skill" (TCW-74's
     file).
4. **An unreachable or missing Jira site is reported as "the tracker has no
   such resource"** by `tcw work list` (the client's message), which reads as
   a missing ticket rather than a missing site.
5. **Offline `tcw validate` in Jira mode skips the item-folder checks.**
   `tcw/validate.py:556-560` returns early for a `JiraBackend`, so references,
   stage-ahead warnings and each item's `capabilities.yaml` are checked only
   under `--remote` (`tcw/work/jira/remote.py:508-533`). The item folders are
   local files in both backends, so at least the `capabilities.yaml` check
   could run offline. TCW-75 documents the current behavior; deciding whether
   the code should change is this entry's question.
6. **The shared vocabulary scan reads one line at a time.**
   `tests/doc_vocabulary.py:61-68` (TCW-74) misses a 2.x phrase split across a
   line wrap (`TCW no` / `longer`). No owned document has one today; scanning
   each paragraph joined onto one line, with hits mapped back to line numbers,
   closes it.
