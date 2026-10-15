TCW 3.0 describes a project's work with one model. A work item is a folder that
never moves; its stage is a property recorded about it, and one command,
`tcw work advance`, moves it from stage to stage. The work can be kept in the
repository or in Jira: with Jira, people outside engineering read and change the
request, status and assignee there, and the repository keeps the technical
record. Every command follows one output contract, with fixed exit codes, and
TCW never changes git state: committing and pushing are your project's choice.

This is a major release with breaking changes. Commands, configuration keys and
the layout of the work folder have all changed, and TCW 2.x projects do not
work with 3.0 until they are moved over. To move an existing project, follow
[the 2.8 to 3.0.0 migration guide](../migration-guide-2.8-to-3.0.0.md) with
an agent.

## Documentation

- The README describes TCW 3.0: items as folders that never move, the
  filesystem and Jira backends side by side, the stages, moving an item, and a
  new section on why taxonomy and capabilities live in the repository.
- New guide, [The command line](../guide/cli.md): what each command prints,
  how to name an item, and every exit code.
- Rewritten guides: [The Work component](../guide/work.md),
  [Using TCW with Jira](../guide/jira.md),
  [Configuration](../guide/configuration.md) and
  [Working across repositories](../guide/multi-repo.md).
- Updated guides: [Taxonomy and Capabilities](../guide/taxonomy-and-capabilities.md)
  and [Linking and validation](../guide/linking-and-validation.md).
- The configuration guide has an opt-in example, a script your project can add
  to commit each item after it moves; TCW itself never runs it for you.
- The `configure` skill's references cover every 3.0 configuration key, and a
  new one covers personal configuration.
