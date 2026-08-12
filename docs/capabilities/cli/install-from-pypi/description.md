As a user who wants the `tcw` command and nothing else, I install it from PyPI
with `pipx install tcw-cli` (or `pip install tcw-cli`) — no agent harness, no
marketplace, no clone. The distribution is named `tcw-cli` because `tcw` on PyPI
belongs to an unrelated project; the installed command is still `tcw` and the
importable package is still `tcw`. This is the same install the plugin performs
for me automatically: [installing as a plugin](tcw://C/plugin/install-as-a-plugin)
runs `pipx install tcw-cli` on my behalf at session start, into the same pipx
package, so the two routes converge instead of competing and there is nothing to
keep in step by hand.
