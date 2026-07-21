import { mkdtemp, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { buildServer } from "./server";

test("serves the SPA and proxies authenticated API requests", async () => {
  const assets = await mkdtemp(join(tmpdir(), "tcw-assets-"));
  await writeFile(join(assets, "index.html"), "<h1>TCW</h1>");
  const upstream: typeof fetch = vi.fn(async (_input: string | URL | Request, init?: RequestInit) => {
    expect(new Headers(init?.headers).get("x-tcw-sidecar-token")).toBe("secret");
    return new Response(JSON.stringify([{ slug: "item" }]), {
      status: 200,
      headers: { "content-type": "application/json" }
    });
  });
  globalThis.fetch = upstream;
  const app = buildServer({
    assetDirectory: assets,
    sidecarOrigin: "http://127.0.0.1:12345",
    sidecarToken: "secret"
  });
  const shell = await app.inject({ method: "GET", url: "/work/item" });
  expect(shell.statusCode).toBe(200);
  expect(shell.body).toContain("TCW");
  const api = await app.inject({ method: "GET", url: "/api/work", headers: { host: "127.0.0.1:8765" } });
  expect(api.statusCode).toBe(200);
  expect(api.json()).toEqual([{ slug: "item" }]);
  expect(upstream).toHaveBeenCalledOnce();
  await app.close();
});

test("applies browser security policy and rejects foreign origins", async () => {
  const assets = await mkdtemp(join(tmpdir(), "tcw-assets-"));
  await writeFile(join(assets, "index.html"), "<h1>TCW</h1>");
  globalThis.fetch = vi.fn(async () => new Response("[]", { status: 200 }));
  const app = buildServer({
    assetDirectory: assets,
    sidecarOrigin: "http://127.0.0.1:12345",
    sidecarToken: "secret"
  });
  const shell = await app.inject({ method: "GET", url: "/taxonomy/example" });
  expect(shell.headers["content-security-policy"]).toBe("default-src 'self'");
  const rejected = await app.inject({
    method: "GET",
    url: "/api/work",
    headers: { host: "127.0.0.1:8765", origin: "https://attacker.example" }
  });
  expect(rejected.statusCode).toBe(403);
  expect(globalThis.fetch).not.toHaveBeenCalled();
  await app.close();
});

test("enforces the one MiB request limit before proxying", async () => {
  const assets = await mkdtemp(join(tmpdir(), "tcw-assets-"));
  await writeFile(join(assets, "index.html"), "<h1>TCW</h1>");
  globalThis.fetch = vi.fn(async () => new Response("{}", { status: 200 }));
  const app = buildServer({
    assetDirectory: assets,
    sidecarOrigin: "http://127.0.0.1:12345",
    sidecarToken: "secret"
  });
  const response = await app.inject({
    method: "POST",
    url: "/api/work",
    headers: { host: "127.0.0.1:8765", "content-type": "application/json" },
    payload: JSON.stringify({ body: "x".repeat(1024 * 1024) })
  });
  expect(response.statusCode).toBe(413);
  expect(globalThis.fetch).not.toHaveBeenCalled();
  await app.close();
});
