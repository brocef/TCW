## Fixes

- Recovering an interrupted start — `tcw work start <item> --take-over`, or the
  **Recover** button in the web app — no longer takes an item from someone
  whose start was still running. Recovery now waits half a second for the start
  to finish by itself and, if it does, says who holds the item instead of taking
  it. A start that loses the item to a recovery now says so, rather than failing
  with a missing-file error.
