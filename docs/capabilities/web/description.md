As a user, I browse Work, Taxonomy, and Capabilities in the local `tcw serve`
web app with deep links, browser history, filtering, and editable object
details. `tcw serve` requires Node.js 22.12 or newer; other TCW commands remain
Python-only. The installed app includes its prebuilt server and client and works
offline without pnpm or `node_modules`. Hosted descendant work boards, routes, rollups, and cross-project
navigation use canonical project IDs and are sourced only from the registered
graph. Taxonomy and capability links follow their explicit per-axis inheritance
lists; unknown, unregistered, or dangling foreign targets remain inert. All
three trees share the same row layout, selection treatment, and metadata
presentation at every nesting depth, show each object's last-modified time in
both the tree and the detail header, and tint work rows by lifecycle status.
The Work tree filters by status and tag and sorts by name or last-modified time
in either direction.
