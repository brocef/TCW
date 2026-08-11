As a user who wants the `tcw` command and nothing else, I install it from PyPI
with `pipx install tcw-cli` (or `pip install tcw-cli`) — no agent harness, no
marketplace, no clone. The distribution is named `tcw-cli` because `tcw` on PyPI
belongs to an unrelated project; the installed command is still `tcw` and the
importable package is still `tcw`. This is a peer to
[installing as a plugin](tcw://C/plugin/install-as-a-plugin), not a replacement:
if I use the plugin, it manages its own copy and I should not install this one
as well.
