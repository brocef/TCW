## Changed

- In Jira mode, the `TCW Project` and `TCW Item` fields
  (`work.jira.fields.project` and `.item`) are optional, given together or
  not at all; one alone is a configuration problem naming the other. Without
  them the item folders alone say which tickets are the project's items:
  `tcw work list` searches by the keys the folders name, the inbox offers
  tickets at the inbox status with no folder here, `tickets adopt` refuses a
  ticket at the request status with no folder here and finishes a stopped
  adoption from its folder, `new`, `move` and `rename` write no field, a
  parent or blocker in another project is recorded in the state file unless
  both projects have the fields, and `tcw validate --remote` checks neither
  field. With the fields configured, `tcw validate --remote` reports a folder
  whose ticket has neither filled in, as when the project ran without them,
  and names the two values to fill in by hand.
