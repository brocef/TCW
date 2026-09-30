## Improvements

- **A mistyped command now suggests what you meant.** When a command word is
  wrong, the error still lists the valid choices, and now adds a line with the
  likely command: `tcw tracker status` suggests `tcw work tracker show`,
  `tcw work status` suggests `tcw work show` or `tcw work list`, and
  `tcw work strat` suggests `tcw work start`. Giving `tcw work stage gate` the
  name of a document, such as `refined-outcome`, says which stage writes it.
