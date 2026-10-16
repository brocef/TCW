## Added

- `tcw.work.jira.client.TrackerSiteMissing`: a 404 from an endpoint every Jira
  Cloud site has (`/rest/api/3/search/jql`, `/myself`, `/issuelinktype`),
  mapped by `_jira()` to a `BackendError` (exit 1) naming `work.jira.site`.
  `_read_metadata` asks `/myself` after a project 404 to tell the two apart.
- `tcw.store.base.is_slug` and `NotASlug` (a `UsageError`); the taxonomy CLI
  turns it into `--slug ...`.
- `tcw.serve.files.inside_item`: the containment check used by `file_path` and
  the two declaration routes.
- `tcw.validate._declaration_findings`: Jira mode's offline parse of each
  key-named folder's `capabilities.yaml`.
- `tcw.store.fs._no_prompt_env`: the environment `FsStoreProvisioner._run`
  gives git.
- Tests: `tests/config/test_config_edges.py`, `tests/test_doc_vocabulary.py`,
  `tests/test_suite_runs_its_own_tcw.py`, and new cases beside each change.

## Changed

- `JiraBackend._post_note`: a `TrackerUnavailable` is followed by a read of the
  newest `NOTE_WINDOW` comments; found is success, not found is
  `MovedWithoutNote` as before, unreadable is `MovedWithoutNote` saying the
  note may have been posted. `advance`'s suffix is "if it is missing, add it
  with `tcw work comment`".
- `tcw/store/yaml_source.py` `_no_dup_keys`: an unhashable key raises a
  `ConstructorError` at its mark. `tcw/config.py` `_merge`: two empty mappings
  take the higher layer's origin. `tcw/work/jira/config.py` `_credentials`
  reports every bad key. `tcw/config_cli.py` `_scalar` writes `bytes` as
  `!!binary` and sets as `!!set` flow mappings, members sorted by written
  form.
- `tcw work new`: `open_backend` and `creation_stage` run before
  `read_piped_stdin` when `--project` is absent.
- `FsCapabilitiesStore.reset` refuses when `_nested_entries` (shared with
  `remove`) finds a `meta.yaml` below the override folder.
- `FsTaxonomyStore.add` refuses a `slug` that is not `is_slug`, after
  `_safe_store_id`, so `../evil` is still "invalid slug".
- `FsStoreProvisioner._run` passes `GIT_TERMINAL_PROMPT=0`,
  `GCM_INTERACTIVE=never` and an empty `GIT_ASKPASS` (git then skips every
  askpass program, including `core.askPass`), removes `SSH_ASKPASS`, and sets
  `GIT_SSH_COMMAND="ssh -o BatchMode=yes"` unless `GIT_SSH_COMMAND`, `GIT_SSH`
  or `core.sshCommand` is set.
- `refuse_retired_config` names `os.path.relpath(root / SENTINEL)`.
- `open_backend` calls `require_valid()` on the registry when `personal` is
  true.
- `uncommitted_changes`: "the work store of project '<id>'".
- `tcw/validate.py` `round_findings` skips `layout.external` stages;
  `tcw/work/jira/remote.py` `_model_checks` skips a declaration that does not
  parse.
- `tcw/serve/records.py`: both `PATCH` routes require `revision`.
- `web/client/src/ui/content-views.tsx` `Conflict`: only inline text inside
  `Callout.Text`; `tcw/serve/dist` rebuilt.
- `tcw/work/config.py`: the removed-procedure messages build their stage names
  from the stage table.

## Fixed

- `GenerateError` and the `resolve.py` comment name `work.hooks.output-cap` and
  `work.hooks.timeout`.
- Docstrings: `tcw/work/hooks.py` (the viewer runs request `post` hooks on
  adopt), `run_provision` (the only command that clones), `tcw/store/base.py`
  (the work axis has a Jira backend), `tcw/store/project.py` (`_ANCHOR_CACHE`
  lives for a whole `tcw serve` run); `skills/README.md`.

## Internal

- `tests/work/jira/capture.py` writes every `timeZone` as `Etc/UTC` and every
  `locale` as `en_US`; the six recorded files holding them are rewritten. The
  fake gains `drop_after_next_comment` and `site_missing`.
- `tests/work/test_git_write_scan.py`: eight more verbs, value skipping after
  `-c`, `--git-dir`, `--work-tree` and `--namespace`, the allowance keyed on
  `FsStoreProvisioner._obtain`, and a check that every `status` keeps
  `--no-optional-locks`.
- `tests/conftest.py` puts the interpreter's folder first on `PATH` when it
  holds a `tcw`.
- `tests/serve/test_no_stage_names.py` scans `${...}` bodies, member names and
  unquoted keys, and reads a regex after a keyword.
- `tests/doc_vocabulary.py` `blocks`: Markdown's joined lines, used by `scan`
  and by `tests/test_documented_cli_surface.py`'s code-span reader.
