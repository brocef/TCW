# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category, with commit hash ranges so entries trace back to source.

## Fixed

<changes starting-hash="c0974d1" ending-hash="2e59173">
- Refreshed the deterministic packaged React assets so installed distributions
  include the current staged-plan interface.
- Restored the declared plan-stage resource contract: writes to an undeclared
  stage return HTTP 400 while stale revisions continue to return HTTP 409.
</changes>
