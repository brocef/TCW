As a user, I can ask the TCW plugin to plan a request into a work item or drive an existing work item through the remaining SDLC stages. The agent records the lifecycle artifacts in the work item folder and stops for explicit verification before closeout. While writing up the request it asks me what reference material applies — documentation, links, prior work, files in the repo — and records it with my request, so the stage that writes the specification starts from my sources instead of re-finding them.

For complex work, the agent can keep `plan.md` concise while declaring bounded
stage documents. It reads the manifest first and selectively loads the relevant
stage, including its pre- and post-checks. Dependencies communicate ordering and
parallelism without becoming formal lifecycle state.
