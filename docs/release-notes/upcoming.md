# Upcoming

User-facing release notes for the next version. Plain language — no jargon or
internal module names.

## Clearer notes from `tcw work tracker show`

Two notes that `tcw work tracker show` prints were more certain than the situation
allows, and have been reworded.

- **When a ticket doesn't offer your claim transition**, the note used to say that
  either the name is wrong or the ticket is already past that point. There is a
  third possibility: the ticket hasn't reached that point yet, such as one still in
  Triage. The note now names all three.
- **When a ticket is ready to claim**, the note suggested you could find out whether
  a second person would be refused by checking a ticket that has already been
  claimed. On a workflow that does refuse them, that check still says "not
  determined". The note now says so, and points you to the two things that do
  answer it: actually making a claim, or reading the workflow's definition in Jira.
