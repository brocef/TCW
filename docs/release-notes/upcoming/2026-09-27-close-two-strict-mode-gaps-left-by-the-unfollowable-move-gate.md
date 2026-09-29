## Fixes

- In strict tracker mode, an item linked by an older version of TCW with its
  ticket left several statuses behind is now moved one step at a time (for
  example `tcw work submit` before `tcw work complete`), and completing it needs
  the ticket assigned to you. Before, the item could be completed while its
  ticket stayed behind.
