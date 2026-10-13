As a user or agent, I run `tcw work lifecycle` to see my project's stage table: every stage in order, with its kind, whether this project has it enabled (a disabled one is marked `disabled`), and the `pre`, `prompt` and `post` bindings configured for it. A stage with no `prompt` key shows TCW's own text as `builtin`. It changes nothing and runs nothing.

`--stage <stage>` shows one stage; an unknown stage name is a usage error (exit 2) whose message lists the stages. `--json` prints `{"schema": 1, "hooks": {...}, "stages": [...]}`: the hook limits, and for each stage its name, kind, whether it is enabled, and its bindings.

It reads the current project only. To see another project's configuration, I run it in that project. What a stage tells an agent to do is `tcw work stage prompt` — see [Run a lifecycle stage](tcw://C/work/run-a-lifecycle-stage).
