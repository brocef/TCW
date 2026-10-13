# Settle the Jira live-check questions that need a second account

Raised by TCW-71's live check against `TCWTEST` (2026-10-13; see that item's
`live-check.md`). Two of its questions could not be asked, because only one
Jira account was available, and it is an administrator with an English profile.

1. **Are status names translated for an account whose profile language is not
   English?** TCW 3.0's Jira backend matches statuses by name, so if Jira
   translates them, every stage lookup fails for that person. The spec
   (TCW-71, Notes) says the answer decides whether a fix is needed.
2. **Can a non-administrator read the workflow definition**
   (`POST /rest/api/3/workflows`)? `validate --remote` falls back to sample
   tickets on a 403 or an empty answer, so this only affects how thorough the
   check is, but the fallback has only ever run against the fake.

Needs: a second account on proposit.atlassian.net with a non-English profile
language and no administrator rights. Then run the probes in
`tests/work/jira/scenario.py` (`probe`) with that account's credentials.
