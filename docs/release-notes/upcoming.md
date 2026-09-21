# Upcoming

User-facing release notes for the next version. Plain language — no jargon or
internal module names.

**This is the release v2.5.0 was meant to be.** v2.5.0 was tagged but never
reached PyPI, because a test that only failed on the build server stopped the
upload. Nothing else changed: everything described in the
[v2.5.0 notes](v2.5.0.md) (making Jira tickets with `tcw work tracker create`,
and moving `extends` into `tcw-config.yaml`) arrives with this version.
**Read those notes before upgrading if you use inheritance**, because that part
needs a migration step.

## Tickets waiting in Triage can be linked, synced and accepted

A Jira ticket sitting in a status before your backlog, such as **Triage**, used to
stop `tcw work tracker link --sync-status`, `tcw work tracker sync`, `tcw work
start` and `tcw work inbox accept` with a conflict, because Triage does not offer
the transition that starts work. You had to move each ticket out by hand first.

Now you can name that status and the transition out of it:

```yaml
work:
    tracker:
        statuses:
            backlog: To Do
        pre-backlog:
            Triage: Accept
```

With that set, TCW moves a ticket from Triage to your backlog status just before
claiming it, and tells you it did. Nothing happens without the setting: accepting
a ticket out of triage can be a deliberate team decision, so TCW leaves it alone and
the refusal tells you which setting would change that. Reported from real use in
the proposit-app project.
