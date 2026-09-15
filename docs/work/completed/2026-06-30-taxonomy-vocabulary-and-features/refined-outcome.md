The user accepted the taxonomy Vocabulary/Feature direction, requested local
review, requested skill-guidance refinements, and selected a minor version cut.

Refinements after initial implementation:

- Local `bllm-review` findings were addressed with a list marker fix and added
  focused tests.
- TCW skill guidance now explains how Vocabulary, Features, Capabilities, and
  Work fit together.
- `skills/tcw-taxonomy/docs/init.md` now bootstraps both Vocabulary and Features.
- Local review logs are ignored via `.gitignore`.

Final verification:

- `pytest` passed with 215 tests after review-driven code/test changes.
- `pytest tests/test_skill_flow.py tests/test_plugin_manifests.py` passed after
  skill-guidance updates.
- `tcw taxonomy check` and `tcw capabilities check` passed after implementation.

Closeout choice:

- Cut a minor release.
