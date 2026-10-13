# Tidy what TCW-72's reviews left for personal configuration

Separate-change findings from TCW-72's verify review (2026-10-13). None blocks
the epic.

1. **A YAML key that is itself a list crashes every command.** `? [a]\n: 1` in
   `tcw-config.yaml` or a personal file raises `TypeError` in
   `tcw/store/yaml_source.py`'s `_no_dup_keys`, which prints a traceback. It
   predates TCW-72. It should be a configuration problem naming the file.
2. **Two layers writing the same empty mapping blame the lower one.** If the
   project writes `completed: {}` and the local file writes `completed: {}`,
   `config show --origin` names the project file. The non-empty guard in
   `_merge` (`tcw/config.py`) keeps the first origin. Cosmetic.
3. **Only the first bad Jira credential key is reported.**
   `parse_jira_credentials` stops at the first one; with both
   `token-env` and `email-env` wrong, `validate` names one.
4. **`tcw work new --stage inbox` in a Jira project reads piped input before
   its usage error** (`tcw/work/cli.py`), so it can wait up to two seconds
   for nothing. TCW-72 moved the `--project` checks first; this one remains.
5. **`config show` writes a `!!binary` or `!!set` value under an unknown key
   over several lines.** Nothing TCW reads takes one.
