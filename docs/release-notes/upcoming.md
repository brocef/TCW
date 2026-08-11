# Upcoming

User-facing release notes for the next version. Plain language — no jargon or
internal module names.

- Projects can keep their work items in another Git repository with `work.path`
  or the new init flags, without changing project IDs or qualified references.
- Starting an item now records who claimed it and when, reports contention
  clearly, and supports deliberate takeover. Active boards show this ownership.
- You can now print the exact folder used by taxonomy, capabilities, work, or
  the work inbox. Work folder commands follow external storage configuration,
  and each command emits only the resolved path for easy shell use.
- You can now add TCW from the plugin directory in the Claude web and desktop
  apps, not just from the command line. Adding it there used to fail with
  "Marketplace sync failed"; installing from the terminal was unaffected and
  still works the same way.
