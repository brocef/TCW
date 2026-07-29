# Upcoming

User-facing release notes for the next version. Plain language — no jargon or
internal module names.

## Turn your project's GitHub issues into tracked work

If your project takes bug reports on GitHub, you have had two lists that never
talked to each other: the issues people file, and the work your agents actually
pick up. `/tcw-triage-issues` connects them.

It reads your open issues, skips the ones it has already handled, and works
through the rest with you. **Most issues should not become work items**, so it
decides before it creates anything — this one is worth doing, that one duplicates
an issue you already have, this one the project already decided against, that one
is too vague to act on. Only the first kind becomes a work item.

Then it offers to reply. An issue that gets read and silently filed away is worse
for the person who wrote it than one nobody read, so every outcome has an answer
that fits: a duplicate closed with a pointer to the original, a real reason when
you are not going to do it, or a request for the one specific detail that is
missing. **Nothing is posted until you approve the exact wording**, one message
at a time — these are public comments on someone else's report.

Issues it accepts keep the reporter's own words, and record the issue they came
from, so the next sweep knows not to raise them again.

Note the direction, since TCW now has a skill pointing each way: `tcw-report`
files an issue **to** the TCW project, `/tcw-triage-issues` reads issues **on
your own** project.

Needs the GitHub CLI (`gh`), signed in. If it is missing or your project does not
use GitHub, the skill says so plainly instead of failing in a confusing way.
