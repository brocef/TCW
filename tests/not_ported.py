"""Tests of 2.x work behavior that TCW-70 did not port, skipped by ID.

TCW-70's plan ported each of these at its Task 10. On 2026-10-08 the owner
chose instead to write only the new 3.0 tests and skip or delete the 2.x ones
that broke, so the epic is not held up porting tests of code it is replacing.
Files that were wholly or almost wholly 2.x were deleted; these are the 2.x
tests inside files whose other tests still pass, so they are skipped one by one
and the rest keep running.

`tests/conftest.py` applies the list. Remove an entry when its test is ported
or deleted. The epic's final full-suite run decides what is left.
"""

REASON = ("2.x work behavior, not ported in TCW-70 (owner's choice, "
          "2026-10-08); see tests/not_ported.py")

NOT_PORTED = frozenset({
    # tests/test_capabilities.py
    'tests/test_capabilities.py::test_cli_drift_active_planning_doc_not_flagged',
    'tests/test_capabilities.py::test_cli_drift_flags_shipped_but_missing',
    'tests/test_capabilities.py::test_cli_drift_gives_the_same_verdict_either_side_of_the_ignore_rule',
    'tests/test_capabilities.py::test_cli_drift_ignores_a_discarded_planning_doc',
    'tests/test_capabilities.py::test_cli_drift_is_silent_when_the_record_kept_no_resolution',
    'tests/test_capabilities.py::test_cli_drift_reads_completed_item_from_external_store[False]',
    'tests/test_capabilities.py::test_cli_drift_reads_completed_item_from_external_store[True]',
    'tests/test_capabilities.py::test_cli_drift_reports_a_shipped_item_whose_folder_is_gone',
    'tests/test_capabilities.py::test_cli_drift_still_ignores_a_discarded_item_whose_folder_is_gone',
    # tests/test_capabilities_rm.py
    'tests/test_capabilities_rm.py::test_gate_removed_ignores_an_inherited_capability_at_the_same_path',
    # tests/test_command_suggestions.py
    'tests/test_command_suggestions.py::test_a_close_spelling_is_suggested',
    'tests/test_command_suggestions.py::test_a_stage_verb_typo_is_offered_gate_and_no_removed_spelling',
    'tests/test_command_suggestions.py::test_a_subcommand_one_level_down_is_named_with_the_verb_meant',
    'tests/test_command_suggestions.py::test_a_transition_given_as_a_stage_names_its_command',
    'tests/test_command_suggestions.py::test_a_valid_word_after_the_missing_level_is_kept',
    'tests/test_command_suggestions.py::test_an_artifact_name_names_the_stage_that_writes_it[initial-request-request]',
    'tests/test_command_suggestions.py::test_an_artifact_name_names_the_stage_that_writes_it[outcome-implement]',
    'tests/test_command_suggestions.py::test_an_artifact_name_names_the_stage_that_writes_it[post-mortem-postmortem]',
    'tests/test_command_suggestions.py::test_an_artifact_name_names_the_stage_that_writes_it[refined-outcome-verify]',
    'tests/test_command_suggestions.py::test_an_artifact_name_names_the_stage_that_writes_it[refined-outcome.md-verify]',
    'tests/test_command_suggestions.py::test_an_option_value_gets_no_hint',
    'tests/test_command_suggestions.py::test_discard_names_the_command_that_discards',
    'tests/test_command_suggestions.py::test_rework_names_its_artifact_and_its_transition',
    'tests/test_command_suggestions.py::test_the_inbox_stage_is_named_without_a_slug',
    'tests/test_command_suggestions.py::test_the_same_component_is_suggested_first',
    # tests/test_config_edit_writers.py
    'tests/test_config_edit_writers.py::test_tags_add_where_work_has_no_tags',
    'tests/test_config_edit_writers.py::test_tags_add_with_a_scalar_work_section_is_refused',
    # tests/test_documentation_config.py
    'tests/test_documentation_config.py::test_a_malformed_block_does_not_break_the_board',
    # tests/test_documentation_prompt.py
    'tests/test_documentation_prompt.py::test_a_span_in_a_project_prompt_binding_is_substituted',
    'tests/test_documentation_prompt.py::test_a_span_in_an_artifact_template_is_left_verbatim',
    # tests/test_environment_hardness.py
    'tests/test_environment_hardness.py::TestCLISmoke::test_lone_project_cli_work_flow',
    'tests/test_environment_hardness.py::TestCLISmoke::test_nested_cli_delegate_subfolder_unsupported_sp2_boundary',
    'tests/test_environment_hardness.py::TestCLISmoke::test_nested_monorepo_cli_child_work',
    'tests/test_environment_hardness.py::test_validate_names_a_corrupt_state_file_the_board_tolerated',
    "tests/test_item_tags_read.py::test_tags_add_and_rm_refuse_while_the_registry_holds_a_non_tag[add-cli,docs-'cli,docs']",
    "tests/test_item_tags_read.py::test_tags_add_and_rm_refuse_while_the_registry_holds_a_non_tag[rm-cli,docs-'cli,docs']",
    "tests/test_lifecycle_config_tags.py::test_an_unregistered_condition_tag_is_reported_wherever_it_is[None-procedures2-work.procedures.unattended-work entry 'blob: x']",
    "tests/test_lifecycle_config_tags.py::test_an_unregistered_condition_tag_is_reported_wherever_it_is[lifecycle0-None-work.lifecycle.transitions.start.pre entry 'command: true']",
    "tests/test_lifecycle_config_tags.py::test_an_unregistered_condition_tag_is_reported_wherever_it_is[lifecycle1-None-work.lifecycle.artifacts.spec entry 'blob: x']",
    'tests/test_lifecycle_config_tags.py::test_listing_by_an_unregistered_tag_says_so',
    # tests/test_override_letter_case.py
    'tests/test_override_letter_case.py::test_completing_an_item_of_a_project_reached_in_other_letter_case',
    # tests/test_procedure_verb.py
    'tests/test_procedure_verb.py::test_a_deleted_file_binding_is_refused_by_name',
    'tests/test_procedure_verb.py::test_an_unknown_id_is_refused_by_name',
    'tests/test_procedure_verb.py::test_an_unknown_slug_is_refused_by_name',
    'tests/test_procedure_verb.py::test_conditional_only_bindings_without_a_slug_say_why_nothing_printed',
    'tests/test_procedure_verb.py::test_outside_a_work_node_a_work_item_still_refuses',
    # tests/test_project_overrides.py
    'tests/test_project_overrides.py::test_the_override_is_honoured_by_every_command',
    # tests/test_refs.py
    'tests/test_refs.py::test_resolve_a_slug_that_never_existed_still_fails_unchanged',
    'tests/test_refs.py::test_resolve_dangling_work_slug',
    'tests/test_refs.py::test_resolve_dangling_work_slug_in_a_registered_project',
    'tests/test_refs.py::test_resolve_unregistered_project_names_the_cause',
    # tests/test_serve_resolve.py
    'tests/test_serve_resolve.py::test_resolve_foreign_and_malformed',
    # tests/test_smoke.py
    'tests/test_smoke.py::test_init_ignores_resolved_work_folders',
    # tests/test_stage_verb.py
    'tests/test_stage_verb.py::test_an_item_whose_artifacts_vanished_mid_read_counts_as_unreadable',
    'tests/test_stage_verb.py::test_an_unknown_stage_names_the_verb_it_was_reached_through',
    'tests/test_stage_verb.py::test_gate_inbox_runs_the_stages_pre_bindings',
    'tests/test_stage_verb.py::test_prompt_reports_its_own_errors_on_stderr_alone',
    'tests/test_stage_verb.py::test_the_removed_form_advises_inbox_without_a_reference',
    # tests/test_stdin_cli.py
    'tests/test_stdin_cli.py::test_a_command_hook_does_not_inherit_stdin',
    'tests/test_stdin_cli.py::test_an_inherited_open_stdin_does_not_hang[argv0-docs/work/backlog]',
    'tests/test_stdin_cli.py::test_piped_intake_still_lands_verbatim',
    # tests/test_store_provisioning.py
    'tests/test_store_provisioning.py::test_a_declared_node_whose_default_store_exists_uses_it',
    'tests/test_store_provisioning.py::test_a_malformed_declaration_never_misdirects_to_tcw_init[argv3]',
    'tests/test_store_provisioning.py::test_a_malformed_declaration_never_misdirects_to_tcw_init[argv4]',
    'tests/test_store_provisioning.py::test_a_malformed_declaration_never_misdirects_to_tcw_init[argv5]',
    'tests/test_store_provisioning.py::test_a_node_without_a_work_store_still_says_so',
    'tests/test_store_provisioning.py::test_an_absent_node_still_gets_the_tcw_init_advice',
    'tests/test_store_provisioning.py::test_every_work_command_says_the_same_actionable_thing[argv3]',
    'tests/test_store_provisioning.py::test_every_work_command_says_the_same_actionable_thing[argv4]',
    'tests/test_store_provisioning.py::test_every_work_command_says_the_same_actionable_thing[argv5]',
    'tests/test_store_provisioning.py::test_no_read_command_provisions_implicitly[argv1]',
    'tests/test_store_provisioning.py::test_no_read_command_provisions_implicitly[argv5]',
    'tests/test_store_provisioning.py::test_procedure_prompt_without_a_work_store_still_prints_the_builtin',
    'tests/test_store_provisioning.py::test_provision_then_the_board_works',
    'tests/test_store_provisioning.py::test_the_work_layout_check_is_not_relaxed_by_the_tree_one',
    # tests/test_upstream_projects.py
    'tests/test_upstream_projects.py::test_a_project_beyond_an_upstream_cannot_be_named',
    'tests/test_upstream_projects.py::test_a_write_into_an_upstream_is_refused_as_read_only[command0-.]',
    'tests/test_upstream_projects.py::test_a_write_into_an_upstream_is_refused_as_read_only[command0-a]',
    'tests/test_upstream_projects.py::test_a_write_into_an_upstream_is_refused_as_read_only[command0-b]',
    'tests/test_upstream_projects.py::test_a_write_into_an_upstream_is_refused_as_read_only[command1-.]',
    'tests/test_upstream_projects.py::test_a_write_into_an_upstream_is_refused_as_read_only[command1-a]',
    'tests/test_upstream_projects.py::test_a_write_into_an_upstream_is_refused_as_read_only[command1-b]',
    'tests/test_upstream_projects.py::test_a_write_into_an_upstream_is_refused_as_read_only[command2-.]',
    'tests/test_upstream_projects.py::test_a_write_into_an_upstream_is_refused_as_read_only[command2-a]',
    'tests/test_upstream_projects.py::test_a_write_into_an_upstream_is_refused_as_read_only[command2-b]',
    'tests/test_upstream_projects.py::test_a_write_into_an_upstream_is_refused_as_read_only[command3-.]',
    'tests/test_upstream_projects.py::test_a_write_into_an_upstream_is_refused_as_read_only[command3-a]',
    'tests/test_upstream_projects.py::test_a_write_into_an_upstream_is_refused_as_read_only[command3-b]',
    'tests/test_upstream_projects.py::test_a_write_into_an_upstream_is_refused_as_read_only[command4-.]',
    'tests/test_upstream_projects.py::test_a_write_into_an_upstream_is_refused_as_read_only[command4-a]',
    'tests/test_upstream_projects.py::test_a_write_into_an_upstream_is_refused_as_read_only[command4-b]',
    'tests/test_upstream_projects.py::test_an_incomplete_tracker_with_a_parent_does_not',
    'tests/test_upstream_projects.py::test_an_incomplete_tracker_with_no_parent_says_so',
    'tests/test_upstream_projects.py::test_delegate_into_an_upstream_is_refused[.]',
    'tests/test_upstream_projects.py::test_delegate_into_an_upstream_is_refused[a]',
    'tests/test_upstream_projects.py::test_reading_an_upstream_item_is_allowed[.]',
    'tests/test_upstream_projects.py::test_reading_an_upstream_item_is_allowed[a]',
    'tests/test_upstream_projects.py::test_reading_an_upstream_item_is_allowed[b]',
    'tests/test_upstream_projects.py::test_serve_reads_an_upstream_item',
    'tests/test_upstream_projects.py::test_serve_refuses_a_write_into_an_upstream[DELETE--None]',
    'tests/test_upstream_projects.py::test_serve_refuses_a_write_into_an_upstream[DELETE-/plan-stages/one-None]',
    'tests/test_upstream_projects.py::test_serve_refuses_a_write_into_an_upstream[PATCH--body1]',
    'tests/test_upstream_projects.py::test_serve_refuses_a_write_into_an_upstream[POST-/actions/start-body0]',
    'tests/test_upstream_projects.py::test_serve_refuses_a_write_into_an_upstream[POST-/plan-stages/one/open-body7]',
    'tests/test_upstream_projects.py::test_serve_refuses_a_write_into_an_upstream[PUT-/artifacts/spec-body2]',
    'tests/test_upstream_projects.py::test_serve_refuses_a_write_into_an_upstream[PUT-/plan-stages/one-body3]',
    'tests/test_upstream_projects.py::test_serve_refuses_a_write_into_an_upstream[PUT-/sidecars/capabilities.yaml-body4]',
    'tests/test_upstream_projects.py::test_the_proposit_migration_passes_through_no_blocked_state',
    'tests/test_upstream_projects.py::test_the_upstream_stays_off_the_familys_lists',
    # tests/test_validate.py
    'tests/test_validate.py::test_a_broken_path_and_an_unprovisioned_declaration_are_two_problems',
    'tests/test_validate.py::test_a_reference_to_resolved_work_validates_where_it_was_resolved',
    'tests/test_validate.py::test_a_top_level_list_in_a_file_tcw_does_not_own_is_fine',
    'tests/test_validate.py::test_a_typo_reference_still_fails_in_both',
    'tests/test_validate.py::test_an_owned_yaml_holding_a_falsy_non_mapping_is_reported',
    'tests/test_validate.py::test_an_owned_yaml_holding_a_truthy_non_mapping_is_reported',
    'tests/test_validate.py::test_every_yaml_name_tcw_writes_is_owned_or_deliberately_not',
    'tests/test_validate.py::test_link_to_unregistered_project_names_the_cause',
    'tests/test_validate.py::test_the_reported_path_is_named_once',
    'tests/test_validate.py::test_the_same_reference_validates_in_a_fresh_clone',
    'tests/test_validate.py::test_upward_epic_link_validates',
    # tests/test_environment_hardness.py (ids with escapes)
    'tests/test_environment_hardness.py::test_a_corrupt_state_file_does_not_take_the_board_down[[]\\n]',
    'tests/test_environment_hardness.py::test_a_corrupt_state_file_does_not_take_the_board_down[- a\\n]',
})
