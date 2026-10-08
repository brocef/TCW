As a user or agent, I run `tcw work lifecycle [<slug>]` to see my project's enabled stages in order, each with the `prompt`, `pre` and `post` bindings configured for it. A stage with no `prompt` key shows TCW's own text as `builtin`. It changes nothing and runs nothing.

`--json` gives the same for tooling, with the hook limits. `--stage <stage>` shows one stage, and `--phase pre|prompt|post` narrows to one list. `--stage <stage> --directive` prints one instruction line for an agent — the skills to invoke and commands to run — or nothing at all when nothing is bound; an error writes nothing to stdout, so an empty injection can never hide a typo.

With a slug from another project, it reports that project's configuration.
