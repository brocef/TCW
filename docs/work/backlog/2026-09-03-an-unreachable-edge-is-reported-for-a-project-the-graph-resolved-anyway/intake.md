Found while verifying the Proposit configuration in a cloud-shaped checkout,
2026-09-03. Reproduced.

`tcw validate` in `proposit-app/apps/server`, with orchestration and core
provisioned:

    …/proposit-core/tcw-config.yaml: connected project 'proposit-app' is
      declared but not reachable in this checkout (…/stores)
    …/proposit-orchestration/tcw-config.yaml: connected project
      'proposit-app-repo' is declared in https://…/proposit-app.git but has not
      been provisioned here; run `tcw provision` to obtain it
    validate OK

Both projects **are** in the graph. `proposit-app` is the provisioned
orchestration node the run just used; `proposit-app-repo` is the repository the
command is being run inside. Each was recorded unreachable because *one*
config's locator did not resolve — a relative path written for a different
machine — while another route reached the same project and put it in the graph.

The record is per edge; the question a reader asks is per project. Telling
someone to `tcw provision` a repository they are standing in is worse than
saying nothing.
