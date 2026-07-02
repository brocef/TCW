# Vendored JavaScript

`marked.min.js` provides the tiny `window.marked.parse()` surface used by the
read-only TCW viewer. It is intentionally vendored in-tree so `tcw serve` has no
runtime CDN, npm, or Python markdown dependency.

The file currently implements the minimal Markdown subset TCW needs for local
request previews: headings, paragraphs, and unordered lists. It preserves the
same browser-facing API shape as Marked for a future drop-in replacement.
