## Upgrading

- **Moving a 2.8 project to 3.0.0.** A 2.x project does not work with 3.0
  until it is moved over: 3.0 refuses a 2.x `tcw-config.yaml` and does not
  read a 2.x work folder. [The 2.8 to 3.0.0 migration guide](../migration-guide-2.8-to-3.0.0.md)
  walks you and an agent through it, under any agent harness, using only a shell,
  `curl` and `tcw`. It converts the configuration, the board, your own
  scripts and documents, and, for a Jira project, binds every item to its
  ticket. You approve one plan before anything changes, the agent stops only
  where it needs you, and every 2.x name has a row saying what it becomes.
  Its last step goes through the instructions and memories your agents have
  been given and asks you what to do with each one that still describes
  2.x. A project older than 2.8 upgrades to 2.8 first.
- **TCW was moved first.** TCW's own repository was migrated by following
  the guide as written, with its work in the Jira project `TCW`, before
  3.0.0 was released, and the guide was corrected wherever that run found
  it wrong.
