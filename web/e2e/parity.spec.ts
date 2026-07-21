import { expect, test } from "@playwright/test";
import { spawn, spawnSync, type ChildProcess } from "node:child_process";
import { mkdtemp } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

const PUBLIC_PORT = 8891;
const baseUrl = `http://127.0.0.1:${PUBLIC_PORT}`;
let server: ChildProcess;

test.beforeAll(async () => {
  const nodeRoot = await mkdtemp(join(tmpdir(), "tcw-playwright-"));
  spawnSync("git", ["init", "-q"], { cwd: nodeRoot, stdio: "inherit" });
  const initialized = spawnSync("tcw", ["init", "--id", "playwright-node"], {
    cwd: nodeRoot,
    encoding: "utf8"
  });
  if (initialized.status !== 0) throw new Error(initialized.stderr);
  const created = spawnSync(
    "tcw",
    ["work", "new", "Browser parity fixture", "--effort", "low", "--complexity", "low"],
    { cwd: nodeRoot, encoding: "utf8" }
  );
  if (created.status !== 0) throw new Error(created.stderr);
  server = spawn("tcw", ["serve", "--no-open", "--port", String(PUBLIC_PORT)], {
    cwd: nodeRoot,
    stdio: ["ignore", "pipe", "pipe"]
  });
  const deadline = Date.now() + 15_000;
  while (Date.now() < deadline) {
    if (server.exitCode !== null) throw new Error("tcw serve exited before readiness");
    try {
      const response = await fetch(`${baseUrl}/api/work`);
      if (response.ok) return;
    } catch {
      // The listener is not ready yet.
    }
    await new Promise((resolve) => setTimeout(resolve, 100));
  }
  throw new Error("tcw serve did not become ready");
});

test.afterAll(async () => {
  if (!server || server.exitCode !== null) return;
  server.kill("SIGTERM");
  await new Promise<void>((resolve) => server.once("exit", () => resolve()));
});

test("loads the React shell and navigates every axis", async ({ page }) => {
  await page.goto(baseUrl);
  await expect(page).toHaveTitle("TCW");
  await expect(page.getByRole("tree", { name: "Objects" })).toBeVisible();
  await expect(page.getByText("Browser parity fixture", { exact: true })).toBeVisible();

  await page.getByRole("button", { name: "Taxonomy" }).click();
  await expect(page).toHaveURL(`${baseUrl}/taxonomy`);
  await page.getByRole("button", { name: "Capabilities" }).click();
  await expect(page).toHaveURL(`${baseUrl}/capabilities`);
  await page.getByRole("button", { name: "Work" }).click();
  await expect(page).toHaveURL(`${baseUrl}/work`);
});

test("filters work without losing the established tree interaction", async ({ page }) => {
  await page.goto(`${baseUrl}/work`);
  const filter = page.getByPlaceholder("Filter");
  await filter.fill("Browser parity");
  await expect(page.getByText("Browser parity fixture", { exact: true })).toBeVisible();
  await filter.fill("no such work item");
  await expect(page.getByText("Browser parity fixture", { exact: true })).toBeHidden();
});

test("keeps API and SPA routing separate", async ({ request }) => {
  const unknownApi = await request.get(`${baseUrl}/api/not-a-route`);
  expect(unknownApi.status()).toBe(404);
  const deepLink = await request.get(`${baseUrl}/work/browser-parity-fixture`);
  expect(deepLink.status()).toBe(200);
  expect(await deepLink.text()).toContain("<div id=\"root\"></div>");
});
