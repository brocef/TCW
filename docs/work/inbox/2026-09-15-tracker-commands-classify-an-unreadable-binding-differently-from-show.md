# Tracker commands classify an unreadable binding differently from `show`

Found by the adversarial review of
`2026-09-12-surface-an-item-s-tracker-binding-in-the-board-the-projection-and-the-web-app`,
and judged to need its own change. It was there before that item.

The board read (`FsWorkStore._read_item`) and the tracker commands read `tracker.yaml`
two different ways. The board read catches every way the file can fail to read and
reports it as the item's problem. `tracker link`, `unlink` and `import` go through
`read_sidecar` and `read_binding`, which do not:

- **A directory named `tracker.yaml`:** `show` reports a problem, but `link` and
  `unlink` see no file and treat the item as unbound.
- **A file that is not UTF-8:** `show` says "not a readable text file", but `link`,
  `unlink` and `import` stop with Python's raw decoding error.
- **A named pipe:** `read_sidecar` opens it and blocks.

(A value YAML cannot build, such as `bound: 2026-02-30`, used to crash every reader;
`read_binding` now reports it as malformed.)

**Suggested fix:** give `read_sidecar` (or a binding-specific read beside it) the
same handling as `_read_item`: do not open anything but a regular file, and turn
read errors into a problem the commands report.

**Two more readers of the same kind** were found by the combined review of the tracker
epic's children:

- **Strict-mode `drop`.** `ever_bound` (`tcw/tracker/intake.py`) uses
  `read_sidecar`, which returns nothing for a directory named `tracker.yaml`. So strict
  `tcw work drop` goes through, although the board shows the item as
  `ticket: unreadable` and `commands.md` promises the drop is refused.
- **`tcw work tracker sync <slug>`.** Its single-slug path reads the binding through
  `binding_of`, and prints a raw traceback on text that is not UTF-8.
