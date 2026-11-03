gate 1: go be203d5141255eeefd13af5229aacb242dbb7331
2026-10-31T22:04:48Z
> Gate 1 go

Release candidate 8 accepted (tarball sha256 d80b20f552a7b76276dc2a37c4da233d51f2f55db867d0b768c3ff70407b6404,
built from A). Both evaluators had passed it with no findings. Next: Step 19, gate 2 asked.

gate 2: go be203d5141255eeefd13af5229aacb242dbb7331
2026-10-31T23:11:47Z
> gate 2 go

Covers Steps 20 and 21 on TCWTEST, Step 23 (4.0 as this machine's shared tcw) and Steps 24-25
(58 tickets' TCW Item converted on the live TCW board). Next: Step 20.

2026-11-02T17:01:46Z, under gate 2: Step 20's scenario passed, but its validate --remote check
failed on 45 leftover 3.x tickets on TCWTEST (TCWTEST-4 to 79, from earlier 3.x live runs). The user chose:
> Convert them with 4.0 (Recommended)

Done on TCWTEST only: a throwaway 3.0.2 project tcw-test-live in tcwtest-cleanup/, then 4.0's
tcw migrate, which edited TCW Item on exactly those 45 tickets (dry-run.txt, migrate.txt). Not counted
as a 4.0 defect. Step 20 is run again unchanged; the first run's output is live-scenario-1.txt.

gate 2: go be203d5141255eeefd13af5229aacb242dbb7331
2026-11-03T14:42:32Z
> It's fine, continue

Step 22. The rehearsal sent no email: the API account is the user's own Jira account and was the only
watcher of TCWTEST-211 to 213 (step-21-record.md). On the live TCW board a second account watches 12
tickets, two of them (TCW-68, TCW-76) among Step 24's 58, so it may get up to two emails. The user
accepted that. The index lag showed no stale lines, so Step 25 needs no extra wait. Next: Step 23.

gate 3: go e902868dfc374098da49485d3cddf6e141c397d2
2026-11-03T15:48:22Z
> gate 3 go

Step 36. Asked with Steps 29-34's results on T (suite 8268 passed, 116 skipped; CI on T success on all
three jobs; validate and validate --remote clean; tarball, config comparison and plugin checks passed).
Files changed since A outside TCW-118's folder, docs/changelogs/ and docs/release-notes/: only
docs/use-cases.md (the review's S-4 requirement). The request said the go covers it only if the user
says so, and asked for "gate 3 go" if they were happy with this, including that change. Covers: the
tag's push, the upload's confirmation, then at once 3.x and main pushed, and later pushes to main
touching only TCW-118's and TCW-99's folders. Next: Step 37.
