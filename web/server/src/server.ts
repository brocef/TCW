import Fastify, { type FastifyInstance, type FastifyRequest } from "fastify"
import { createReadStream, existsSync } from "node:fs"
import { stat } from "node:fs/promises"
import { extname, join, normalize } from "node:path"

export interface TServerOptions {
    assetDirectory: string
    sidecarOrigin: string
    sidecarToken: string
}

const contentTypes: Record<string, string> = {
    ".css": "text/css; charset=utf-8",
    ".html": "text/html; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
}

function loopbackAuthority(value: string | undefined): boolean {
    if (!value) return true
    try {
        const url = value.includes("://")
            ? new URL(value)
            : new URL(`http://${value}`)
        return (
            url.hostname === "127.0.0.1" ||
            url.hostname === "localhost" ||
            url.hostname === "[::1]"
        )
    } catch {
        return false
    }
}

function isAllowedRequest(request: FastifyRequest): boolean {
    const origin = request.headers.origin
    const host = request.headers.host
    return loopbackAuthority(origin) && loopbackAuthority(host)
}

export function buildServer(options: TServerOptions): FastifyInstance {
    const app = Fastify({ bodyLimit: 1024 * 1024, logger: false })

    app.addHook("onSend", async (_request, reply, payload) => {
        reply.header("content-security-policy", "default-src 'self'")
        return payload
    })

    app.all("/api/*", async (request, reply) => {
        if (!isAllowedRequest(request))
            return reply.code(403).send({ error: "forbidden origin" })
        const target = new URL(
            request.raw.url ?? request.url,
            options.sidecarOrigin
        )
        const headers = new Headers()
        for (const [name, value] of Object.entries(request.headers)) {
            if (
                value !== undefined &&
                !["connection", "content-length", "host"].includes(name)
            ) {
                headers.set(
                    name,
                    Array.isArray(value) ? value.join(", ") : value
                )
            }
        }
        headers.set("x-tcw-sidecar-token", options.sidecarToken)
        const method = request.method.toUpperCase()
        const body =
            method === "GET" || method === "HEAD"
                ? undefined
                : JSON.stringify(request.body ?? {})
        const upstream = await fetch(target, { method, headers, body })
        reply.code(upstream.status)
        const contentType = upstream.headers.get("content-type")
        if (contentType) reply.header("content-type", contentType)
        return reply.send(Buffer.from(await upstream.arrayBuffer()))
    })

    app.get<{ Params: { "*": string } }>("/*", async (request, reply) => {
        const requested = request.params
        const relative = requested["*"] || "index.html"
        const safe = normalize(relative).replace(/^(\.\.(\/|\\|$))+/, "")
        const candidate = join(options.assetDirectory, safe)
        const file =
            existsSync(candidate) && (await stat(candidate)).isFile()
                ? candidate
                : join(options.assetDirectory, "index.html")
        reply.type(contentTypes[extname(file)] ?? "application/octet-stream")
        return reply.send(createReadStream(file))
    })

    return app
}

export async function startFromEnvironment(): Promise<void> {
    const assetDirectory = process.env.TCW_SERVE_ASSET_DIR
    const sidecarOrigin = process.env.TCW_SERVE_SIDECAR_ORIGIN
    const sidecarToken = process.env.TCW_SERVE_SIDECAR_TOKEN
    const port = Number(process.env.TCW_SERVE_PORT ?? "8765")
    if (
        !assetDirectory ||
        !sidecarOrigin ||
        !sidecarToken ||
        !Number.isInteger(port)
    ) {
        throw new Error("missing or invalid TCW serve environment")
    }
    const app = buildServer({ assetDirectory, sidecarOrigin, sidecarToken })
    await app.listen({ host: "127.0.0.1", port })
    const address = app.server.address()
    const publicPort =
        typeof address === "object" && address ? address.port : port
    process.stdout.write(
        `${JSON.stringify({ type: "ready", port: publicPort })}\n`
    )
    const close = async () => {
        await app.close()
        process.exit(0)
    }
    process.on("SIGINT", close)
    process.on("SIGTERM", close)
}

if (process.env.TCW_SERVE_ASSET_DIR) {
    startFromEnvironment().catch((error: unknown) => {
        process.stderr.write(
            `tcw serve: ${error instanceof Error ? error.message : String(error)}\n`
        )
        process.exit(1)
    })
}
