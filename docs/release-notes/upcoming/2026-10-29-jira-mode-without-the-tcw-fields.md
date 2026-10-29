## Jira mode without the TCW Project and TCW Item fields

A Jira site that does not allow new custom fields can now be used: leave
`project` and `item` out of `work.jira.fields` (both, or neither). The item
folders, each named with its ticket's key, then say which tickets are the
project's items, and TCW never reads or writes either field. What that loses,
chiefly that an adoption reaches other copies of the repository only through
git and that a parent or blocker in another project is recorded rather than
linked in Jira, is in [the Jira guide](../guide/jira.md#running-without-the-tcw-fields).
Turning the fields on for a project that ran without them is not supported
yet.
